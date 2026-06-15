"""Shared HTTP plumbing for INE integrations.

A thin, synchronous httpx wrapper with timeouts and bounded retries. Synchronous
is intentional: FastAPI runs sync route handlers in a threadpool, and the
ingestion CLI is sync too.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.logging import get_logger
from app.integrations.ine import config

logger = get_logger("agora.ine")


class IneSourceError(RuntimeError):
    """Raised when an INE source cannot be reached or returns an error."""


def build_client(timeout: float | None = None) -> httpx.Client:
    """Construct an httpx client with sane defaults for INE endpoints."""
    return httpx.Client(
        timeout=timeout or config.DEFAULT_TIMEOUT,
        headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def request(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    retries: int | None = None,
    expect_json: bool = True,
    client: httpx.Client | None = None,
) -> Any:
    """Perform an HTTP request with bounded retries.

    Returns parsed JSON when ``expect_json`` is true, else raw bytes.
    """
    attempts = (retries if retries is not None else config.DEFAULT_RETRIES) + 1
    owns_client = client is None
    client = client or build_client()
    last_exc: Exception | None = None
    try:
        for attempt in range(1, attempts + 1):
            try:
                resp = client.request(method, url, params=params)
                resp.raise_for_status()
                return resp.json() if expect_json else resp.content
            except (httpx.HTTPError, ValueError) as exc:  # network or JSON decode
                last_exc = exc
                if attempt < attempts:
                    backoff = 0.5 * attempt
                    logger.warning(
                        "INE request failed (%s/%s) %s: %s; retrying in %.1fs",
                        attempt,
                        attempts,
                        url,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
    finally:
        if owns_client:
            client.close()

    raise IneSourceError(f"Request to {url} failed after {attempts} attempts: {last_exc}")


def get_json(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
    """GET returning parsed JSON."""
    return request("GET", url, params=params, expect_json=True, **kwargs)


def get_bytes(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> bytes:
    """GET returning raw bytes (downloads)."""
    return request("GET", url, params=params, expect_json=False, **kwargs)
