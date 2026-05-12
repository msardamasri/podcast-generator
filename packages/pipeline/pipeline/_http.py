"""Shared HTTP client with retries and sensible defaults."""
from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# Shared client config: 10s connect, 20s read.
# We do NOT share a single AsyncClient instance across the whole pipeline
# because each fetcher manages its own lifecycle (async with).
DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
DEFAULT_HEADERS = {
    "User-Agent": "PodcastGenerator/0.1 (+https://github.com/msardamasri/podcast-generator)"
}


def retry_http(max_attempts: int = 3):
    """Decorator: retry on transient HTTP errors with exponential backoff.

    Retries on connect errors, timeouts, and 5xx responses.
    Does NOT retry on 4xx (those are our fault — bad key, bad query).
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)
        ),
        reraise=True,
    )