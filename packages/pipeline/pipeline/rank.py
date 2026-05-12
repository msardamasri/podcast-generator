"""Ranking stage: score and pick the best articles for a user's interests.

Pipeline:
1. Embed interests, exclusions, and article texts.
2. For each article, compute a relevance score against interests (weighted).
3. Subtract a penalty if the article is also similar to any exclusion.
4. Apply MMR to select top-K articles that are both relevant and diverse.
"""
from __future__ import annotations

import asyncio
import math
from typing import Iterable

from openai import AsyncOpenAI

from ._openai import get_openai_client
from .config import Interest, Settings
from .types import Article

from datetime import datetime, timezone


EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dims, $0.02 / 1M tokens
EMBEDDING_BATCH_SIZE = 100  # OpenAI accepts up to 2048 but smaller batches log better


# -----------------------------
# Math helpers
# -----------------------------

def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors, in [-1, 1]."""
    na, nb = _norm(a), _norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return _dot(a, b) / (na * nb)


# -----------------------------
# Embedding
# -----------------------------

async def _embed_batch(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts in a single API call."""
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    # OpenAI returns embeddings in the same order as input
    return [item.embedding for item in response.data]


async def embed_texts(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """Embed many texts, batching by EMBEDDING_BATCH_SIZE."""
    if not texts:
        return []
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        out.extend(await _embed_batch(client, batch))
    return out


def _article_text(article: Article) -> str:
    """Build the text to embed for an article: title + truncated content.

    Title carries the most signal but content disambiguates. Truncating to
    ~500 chars keeps embedding cost predictable and the title-heavy weighting
    means a long article doesn't drown out the headline meaning.
    """
    snippet = (article.content or "")[:500]
    return f"{article.title}\n\n{snippet}".strip()


# -----------------------------
# Scoring
# -----------------------------

def score_article(
    article: Article,
    interest_vecs: list[list[float]],
    interest_weights: list[float],
    exclusion_vecs: list[list[float]],
    exclusion_penalty: float = 0.5,
    recency_weight: float = 0.15,
) -> float:
    """Score = weighted interest similarity - exclusion penalty + recency bonus.

    Recency bonus: linear from +recency_weight (just now) to 0 (48h+ old).
    Caps at 48h so older-but-relevant stories still surface.
    """
    if not interest_vecs or not article.embedding:
        return 0.0

    article_vec = article.embedding

    total_weight = sum(interest_weights) or 1.0
    norm_weights = [w / total_weight for w in interest_weights]

    interest_score = sum(
        w * cosine_similarity(article_vec, iv)
        for w, iv in zip(norm_weights, interest_vecs)
    )

    exclusion_score = 0.0
    if exclusion_vecs:
        max_excl_sim = max(cosine_similarity(article_vec, ev) for ev in exclusion_vecs)
        if max_excl_sim > 0.3:
            exclusion_score = exclusion_penalty * (max_excl_sim - 0.3)

    recency_bonus = 0.0
    if article.published_at:
        age_hours = (datetime.now(timezone.utc) - article.published_at).total_seconds() / 3600
        if age_hours < 48:
            recency_bonus = recency_weight * (1 - age_hours / 48)

    return interest_score - exclusion_score + recency_bonus


# -----------------------------
# MMR — diversity-aware selection
# -----------------------------

def mmr_select(
    article_vecs: list[list[float]],
    relevance_scores: list[float],
    k: int,
    lambda_: float = 0.7,
) -> list[int]:
    """Maximal Marginal Relevance.

    Iteratively pick the article that maximizes:
        lambda * relevance - (1 - lambda) * max_similarity_to_already_picked

    lambda=1.0 → pure relevance (likely to pick near-duplicates)
    lambda=0.0 → pure diversity (might pick irrelevant outliers)
    lambda=0.7 → tilted toward relevance with diversity nudge

    Returns indices into article_vecs.
    """
    if not article_vecs or k <= 0:
        return []

    n = len(article_vecs)
    selected: list[int] = []
    candidates = set(range(n))

    # First pick: highest relevance
    first = max(candidates, key=lambda i: relevance_scores[i])
    selected.append(first)
    candidates.remove(first)

    while len(selected) < k and candidates:
        def mmr_score(i: int) -> float:
            max_sim_to_picked = max(
                cosine_similarity(article_vecs[i], article_vecs[j]) for j in selected
            )
            return lambda_ * relevance_scores[i] - (1 - lambda_) * max_sim_to_picked

        next_pick = max(candidates, key=mmr_score)
        selected.append(next_pick)
        candidates.remove(next_pick)

    return selected


# -----------------------------
# Orchestrator
# -----------------------------

async def rank_articles(
    articles: list[Article],
    interests: list[Interest],
    exclusions: list[str],
    top_k: int = 8,
    settings: Settings | None = None,
) -> list[Article]:
    """Rank candidates and return the top K, diverse and relevant.

    Mutates articles in place to set the `.embedding` and `.score` fields,
    then returns the selected subset sorted by score descending.
    """
    if not articles or not interests:
        return articles[:top_k]

    client = get_openai_client(settings)

    # Embed interests, exclusions, and articles in parallel.
    # asyncio.gather here lets the three batches overlap on the network.
    interest_labels = [i.label for i in interests]
    article_texts = [_article_text(a) for a in articles]

    interest_vecs, exclusion_vecs, article_vecs = await asyncio.gather(
        embed_texts(client, interest_labels),
        embed_texts(client, exclusions),
        embed_texts(client, article_texts),
    )

    interest_weights = [i.weight for i in interests]

    # Cache embeddings back onto the articles (useful for future caching/persistence)
    for article, vec in zip(articles, article_vecs):
        article.embedding = vec

    # Relevance score per article
    scores = [
        score_article(a, interest_vecs, interest_weights, exclusion_vecs)
        for a in articles
    ]
    for article, score in zip(articles, scores):
        article.score = score

    # MMR over the top-N relevant candidates (don't run MMR on all 170 — wasteful)
    top_n = min(len(articles), top_k * 4)
    top_indices_by_relevance = sorted(range(len(articles)), key=lambda i: -scores[i])[:top_n]
    pool_vecs = [article_vecs[i] for i in top_indices_by_relevance]
    pool_scores = [scores[i] for i in top_indices_by_relevance]

    mmr_indices = mmr_select(pool_vecs, pool_scores, k=top_k, lambda_=0.7)

    selected = [articles[top_indices_by_relevance[i]] for i in mmr_indices]
    print(f"[rank] {len(articles)} candidates → top {len(selected)} after MMR")
    return selected