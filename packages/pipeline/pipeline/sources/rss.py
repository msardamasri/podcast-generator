"""RSS / Atom feed fetcher.

RSS is the cheapest, most reliable source. We curate a list of feeds
per topic category and pull all of them concurrently.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

import feedparser
import httpx

from .._http import DEFAULT_HEADERS, DEFAULT_TIMEOUT, retry_http
from ..types import Article


FEEDS_BY_CATEGORY: dict[str, list[tuple[str, str]]] = {
    "tech": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ],
    "business": [
        ("CNBC Business", "https://www.cnbc.com/id/10001147/device/rss/rss.html"),
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
        ("MarketWatch Top Stories", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ],
    "science": [
        ("Nature", "https://www.nature.com/nature.rss"),
        ("Quanta Magazine", "https://api.quantamagazine.org/feed/"),
        ("NASA Breaking News", "https://www.nasa.gov/news-release/feed/"),
    ],
    "sports": [
        ("ESPN Top Headlines", "https://www.espn.com/espn/rss/news"),
        ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml"),
    ],
    "world": [
        ("BBC World News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("NPR World News", "https://feeds.npr.org/1004/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
}


@retry_http()
async def _fetch_feed(client: httpx.AsyncClient, outlet: str, url: str) -> list[Article]:
    """Fetch and parse a single RSS feed.

    Returns a list of Articles. Errors are caught upstream so one
    broken feed doesn't kill the whole batch.
    """
    response = await client.get(url)
    response.raise_for_status()

    # feedparser is sync — but parsing is CPU work, not I/O,
    # so blocking the event loop briefly is fine here.
    parsed = feedparser.parse(response.content)

    articles: list[Article] = []
    for entry in parsed.entries[:15]:  # cap per feed to avoid one source dominating
        published = _parse_date(entry)
        articles.append(
            Article(
                url=entry.get("link", ""),
                title=entry.get("title", "").strip(),
                outlet=outlet,
                # RSS often only gives a summary, not full text.
                # Firecrawl can fill in full content later if this article ranks high.
                content=entry.get("summary", "") or entry.get("description", ""),
                published_at=published,
            )
        )
    return articles


def _parse_date(entry) -> datetime | None:
    """RSS dates come in many formats. Try the parsed struct first, fall back to string parsing."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "published"):
        try:
            return parsedate_to_datetime(entry.published)
        except (TypeError, ValueError):
            return None
    return None


async def fetch_rss(categories: Iterable[str]) -> list[Article]:
    """Fetch all RSS feeds for the given categories, concurrently.

    Errors in individual feeds are logged but don't stop the batch.
    """
    feeds: list[tuple[str, str]] = []
    for cat in categories:
        feeds.extend(FEEDS_BY_CATEGORY.get(cat, []))

    if not feeds:
        return []

    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT, follow_redirects=True
    ) as client:
        # gather with return_exceptions=True so one failure doesn't cancel the rest
        results = await asyncio.gather(
            *[_fetch_feed(client, outlet, url) for outlet, url in feeds],
            return_exceptions=True,
        )

    articles: list[Article] = []
    for feed, result in zip(feeds, results):
        if isinstance(result, Exception):
            # In production, log this. For now, print so you see it during dev.
            print(f"[rss] {feed[0]} failed: {result}")
            continue
        articles.extend(result)
    return articles