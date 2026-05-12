"""Fetch orchestrator.

Calls all configured sources concurrently, dedupes results,
and optionally enriches top candidates with full article text via Firecrawl.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlparse, urlunparse

from .config import Interest, Settings
from .sources.firecrawl import enrich_with_firecrawl
from .sources.newsapi import fetch_newsapi
from .sources.rss import fetch_rss
from .types import Article


# Map user interest labels to RSS categories.
# In production this would be more sophisticated (embeddings, taxonomy).
# For the take-home, a simple keyword map gets us 80% there.
INTEREST_TO_CATEGORIES = {
    "ai": ["tech"], "ml": ["tech"], "startups": ["tech", "business"],
    "cloud": ["tech"], "space": ["science", "tech"], "biotech": ["science"],
    "macro": ["business"], "vc": ["business", "tech"], "funding": ["business"],
    "crypto": ["business", "tech"], "real estate": ["business"],
    "football": ["sports"], "f1": ["sports"], "nba": ["sports"],
    "books": ["world"], "film": ["world"],
}


def _categories_for_interests(interests: list[Interest]) -> set[str]:
    """Resolve user interests to RSS feed categories."""
    cats: set[str] = set()
    for interest in interests:
        label = interest.label.lower()
        for key, mapped in INTEREST_TO_CATEGORIES.items():
            if key in label:
                cats.update(mapped)
    # Default fallback if nothing matched
    return cats or {"tech", "world"}


def _queries_for_interests(interests: list[Interest], max_queries: int = 4) -> list[str]:
    """Pick the top N interests by weight for NewsAPI keyword search."""
    sorted_interests = sorted(interests, key=lambda i: -i.weight)
    return [i.label for i in sorted_interests[:max_queries]]


def _canonical_url(url: str) -> str:
    """Strip tracking params and fragments so the same article from
    different sources dedupes correctly."""
    try:
        parsed = urlparse(url)
        # Drop query string and fragment — utm_*, gclid, etc. all live there
        return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", "", ""))
    except Exception:
        return url


def _dedupe(articles: list[Article]) -> list[Article]:
    """Dedupe by canonical URL, keeping the first occurrence (preserves source order)."""
    seen: set[str] = set()
    out: list[Article] = []
    for article in articles:
        key = _canonical_url(article.url)
        if not key or key in seen:
            continue
        if not article.title or len(article.title) < 10:
            continue  # malformed entries
        seen.add(key)
        out.append(article)
    return out


async def fetch_articles(
    interests: list[Interest],
    since_hours: int = 24,
    settings: Settings | None = None,
) -> list[Article]:
    """Top-level: fetch articles from all sources, dedupe, return.

    The result is the candidate pool that ranking will score against
    the user's interest embeddings.
    """
    settings = settings or Settings()  # loads from .env
    categories = _categories_for_interests(interests)
    queries = _queries_for_interests(interests)

    # Fire RSS and NewsAPI concurrently. Firecrawl runs later, only for top candidates.
    rss_task = fetch_rss(categories)
    newsapi_task = fetch_newsapi(settings.newsapi_key or "", queries, since_hours)

    rss_articles, newsapi_articles = await asyncio.gather(rss_task, newsapi_task)

    all_articles = _dedupe(rss_articles + newsapi_articles)
    print(f"[fetch] {len(rss_articles)} RSS + {len(newsapi_articles)} NewsAPI "
          f"→ {len(all_articles)} after dedup")
    return all_articles


async def enrich_top_articles(
    articles: list[Article],
    top_n: int = 10,
    settings: Settings | None = None,
) -> list[Article]:
    """For the top-N articles (by rank), replace snippet with full text via Firecrawl.

    Called AFTER ranking — no point spending Firecrawl credits on articles
    we're going to discard. This is a key cost optimization.
    """
    settings = settings or Settings()
    if not settings.firecrawl_api_key:
        return articles  # Firecrawl optional — fall back to snippets

    top = articles[:top_n]
    urls = [a.url for a in top if len(a.content) < 500]  # only enrich short snippets

    if not urls:
        return articles

    full_text_map = await enrich_with_firecrawl(settings.firecrawl_api_key, urls)

    # Replace content where we got full text, keep snippet otherwise
    for article in top:
        if article.url in full_text_map:
            article.content = full_text_map[article.url]
    return articles