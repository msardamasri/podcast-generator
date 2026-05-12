"""Firecrawl source.

Used in two modes:
1. As a fallback when an article only has a snippet — we crawl the URL
   to get full text before passing to the LLM.
2. (Future) As a discovery tool for outlets without RSS feeds.

For the take-home, we use mode 1 only.
"""
from __future__ import annotations

import asyncio

import httpx

from .._http import DEFAULT_HEADERS, DEFAULT_TIMEOUT, retry_http


FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


@retry_http()
async def _scrape_one(client: httpx.AsyncClient, api_key: str, url: str) -> str | None:
    """Scrape a single URL, return clean markdown text."""
    response = await client.post(
        f"{FIRECRAWL_BASE}/scrape",
        json={
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,  # strips nav, sidebars, footers
        },
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=10.0),
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        return None
    return (data.get("data") or {}).get("markdown")


async def enrich_with_firecrawl(
    api_key: str, urls: list[str], concurrency: int = 3
) -> dict[str, str]:
    """Scrape multiple URLs concurrently, with a concurrency cap.

    Returns {url: markdown_text}. Failed URLs are simply omitted.
    """
    if not api_key or not urls:
        return {}

    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_scrape(client, url):
        async with semaphore:
            try:
                return url, await _scrape_one(client, api_key, url)
            except Exception as e:
                print(f"[firecrawl] {url} failed: {e}")
                return url, None

    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT) as client:
        results = await asyncio.gather(
            *[bounded_scrape(client, url) for url in urls]
        )

    return {url: text for url, text in results if text}