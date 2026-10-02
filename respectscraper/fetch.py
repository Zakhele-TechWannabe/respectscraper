"""Polite HTTP fetching: per-host pacing, bounded retries, and hard size limits."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

RETRY_STATUSES = {429, 502, 503, 504}
MAX_RETRY_AFTER = 60.0


@dataclass
class FetchResult:
    url: str
    status: int | None = None
    headers: dict[str, str] | None = None
    content: bytes = b""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status is not None and 200 <= self.status < 300

    @property
    def is_redirect(self) -> bool:
        return self.status in (301, 302, 303, 307, 308) and bool(self.location)

    @property
    def location(self) -> str | None:
        return (self.headers or {}).get("location")

    @property
    def content_type(self) -> str:
        return (self.headers or {}).get("content-type", "").split(";")[0].strip().lower()


class Fetcher:
    """Fetches one URL at a time, never faster than each host allows."""

    def __init__(
        self,
        session: requests.Session,
        *,
        timeout: float,
        delay_seconds: float,
        max_retries: int,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.session = session
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.sleep = sleep
        self.clock = clock
        self._last_request: dict[str, float] = {}

    def _wait_turn(self, host: str, crawl_delay: float | None) -> None:
        delay = max(self.delay_seconds, crawl_delay or 0.0)
        last = self._last_request.get(host)
        if last is not None:
            remaining = last + delay - self.clock()
            if remaining > 0:
                self.sleep(remaining)
        self._last_request[host] = self.clock()

    def get(self, url: str, *, max_bytes: int, crawl_delay: float | None = None) -> FetchResult:
        """GET without following redirects (the caller checks robots.txt for each hop)."""
        host = urlsplit(url).netloc.lower()
        attempt = 0
        while True:
            self._wait_turn(host, crawl_delay)
            try:
                response = self.session.get(
                    url, timeout=self.timeout, allow_redirects=False, stream=True
                )
            except requests.RequestException as exc:
                if attempt < self.max_retries and isinstance(
                    exc, (requests.ConnectionError, requests.Timeout)
                ):
                    attempt += 1
                    self.sleep(min(2.0**attempt, MAX_RETRY_AFTER))
                    continue
                return FetchResult(url, error=f"{type(exc).__name__}: {exc}")

            if response.status_code in RETRY_STATUSES and attempt < self.max_retries:
                wait = _retry_after(response.headers.get("retry-after"))
                response.close()
                attempt += 1
                self.sleep(wait if wait is not None else min(2.0**attempt, MAX_RETRY_AFTER))
                continue
            return _read(url, response, max_bytes)


def _read(url: str, response: requests.Response, max_bytes: int) -> FetchResult:
    headers = {key.lower(): value for key, value in response.headers.items()}
    result = FetchResult(url, status=response.status_code, headers=headers)
    declared = headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        response.close()
        result.error = f"too_large: {int(declared)} bytes declared, limit {max_bytes}"
        return result
    chunks: list[bytes] = []
    size = 0
    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            size += len(chunk)
            if size > max_bytes:
                result.error = f"too_large: over {max_bytes} bytes"
                return result
            chunks.append(chunk)
    except requests.RequestException as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        return result
    finally:
        response.close()
    result.content = b"".join(chunks)
    return result


def _retry_after(value: str | None) -> float | None:
    """Seconds to wait from a Retry-After header, capped to stay reasonable."""
    if not value:
        return None
    try:
        return min(max(float(value), 0.0), MAX_RETRY_AFTER)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value).timestamp()
    except (TypeError, ValueError):
        return None
    return min(max(when - time.time(), 0.0), MAX_RETRY_AFTER)
