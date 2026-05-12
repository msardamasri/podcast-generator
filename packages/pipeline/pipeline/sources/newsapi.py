"""NewsAPI source.

Free tier: 100 requests/day, 24h delayed results.
We use the /everything endpoint with topic keywords from user interests.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from .._http import DEFAULT_HEADERS, DEFAULT_TIMEOUT, retry_http
from ..types import Article


NEWSAPI_BASE = "https://newsapi.org/v2"

# Reputable English-language news sources. Whitelist > blacklist
# because the long tail of junk is infinite.
TRUSTED_DOMAINS = ",".join([
    "techcrunch.com", "theverge.com", "arstechnica.com", "wired.com",
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com", "economist.com",
    "bbc.com", "bbc.co.uk", "npr.org", "apnews.com", "axios.com",
    "theguardian.com", "nytimes.com", "washingtonpost.com",
    "cnbc.com", "marketwatch.com", "businessinsider.com",
    "nature.com", "sciencemag.org", "newscientist.com",
    "espn.com", "theathletic.com", "skysports.com",
    "thenextweb.com", "venturebeat.com", "engadget.com",
])


@retry_http()
async def _search(client: httpx.AsyncClient, api_key: str, query: str, since_hours: int) -> list[Article]:
    """Run one /everything query against trusted domains only."""
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    response = await client.get(
        f"{NEWSAPI_BASE}/everything",
        params={
            "q": query,
            "from": since,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "domains": TRUSTED_DOMAINS,
        },
        headers={"X-Api-Key": api_key},
    )
    response.raise_for_status()
    data = response.json()

    articles: list[Article] = []
    for item in data.get("articles", []):
        articles.append(
            Article(
                url=item.get("url", ""),
                title=(item.get("title") or "").strip(),
                outlet=(item.get("source") or {}).get("name", "Unknown"),
                content=item.get("description") or item.get("content") or "",
                published_at=_parse_iso(item.get("publishedAt")),
            )
        )
    return articles


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        # NewsAPI returns ISO 8601 with Z. fromisoformat needs +00:00 on older pythons.
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


async def fetch_newsapi(api_key: str, queries: list[str], since_hours: int = 24) -> list[Article]:
    """Run multiple keyword searches against NewsAPI in parallel.

    `queries` should be 2-5 short keyword phrases derived from user interests.
    More than that and you'll burn through the daily rate limit fast.
    """
    if not api_key or not queries:
        return []

    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT
    ) as client:
        results = await asyncio.gather(
            *[_search(client, api_key, q, since_hours) for q in queries],
            return_exceptions=True,
        )

    articles: list[Article] = []
    for query, result in zip(queries, results):
        if isinstance(result, Exception):
            print(f"[newsapi] '{query}' failed: {result}")
            continue
        articles.extend(result)
    return articles