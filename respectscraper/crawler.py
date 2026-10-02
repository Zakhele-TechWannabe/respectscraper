"""The crawler: robots.txt decides every request, and every result carries its evidence."""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests

from .config import Config
from .extract import (
    ExtractionError,
    extract_file,
    file_type,
    normalize_url,
    parse_html,
    robots_directives,
)
from .fetch import Fetcher, FetchResult
from .robots import MAX_REDIRECTS, Decision, RobotsPolicy

logger = logging.getLogger(__name__)
HTML_TYPES = ("text/html", "application/xhtml+xml")


@dataclass
class Page:
    url: str
    final_url: str
    depth: int
    status: int
    title: str
    description: str
    text: str
    word_count: int
    decision: Decision


@dataclass
class Document:
    url: str
    final_url: str
    depth: int
    file_type: str
    size_bytes: int
    text: str
    decision: Decision


@dataclass
class Skipped:
    url: str
    depth: int
    reason: str
    detail: str | None = None
    decision: Decision | None = None


@dataclass
class CrawlReport:
    start_url: str
    user_agent: str
    started_at: str
    finished_at: str = ""
    pages: list[Page] = field(default_factory=list)
    files: list[Document] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when the start URL itself was fetched and kept."""
        start = normalize_url(self.start_url)
        kept: list[Page | Document] = [*self.pages, *self.files]
        return any(normalize_url(item.url) == start for item in kept)

    def to_dict(self) -> dict[str, Any]:
        def convert(item: Any) -> dict[str, Any]:
            data = asdict(item)
            if getattr(item, "decision", None) is not None:
                data["decision"] = item.decision.to_dict()
            return data

        return {
            "start_url": self.start_url,
            "user_agent": self.user_agent,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "ok": self.ok,
            "pages": [convert(page) for page in self.pages],
            "files": [convert(doc) for doc in self.files],
            "skipped": [convert(skip) for skip in self.skipped],
        }


def _site(host: str) -> str:
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


class RespectScraper:
    """Crawls a site within its robots.txt, recording why each URL was or wasn't fetched.

    >>> with RespectScraper() as scraper:
    ...     report = scraper.crawl("https://example.com", max_depth=1)
    """

    def __init__(
        self,
        config: Config | dict[str, Any] | str | os.PathLike[str] | None = None,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if config is None:
            config = Config()
        elif isinstance(config, dict):
            config = Config.from_dict(config)
        elif not isinstance(config, Config):
            config = Config.from_file(config)
        self.config = config
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = config.user_agent
        if not config.verify_ssl:
            # Scoped to this scraper's session; nothing process-wide changes.
            self.session.verify = False
            logger.warning("TLS certificate verification is OFF for this scraper's session.")
        self.robots = RobotsPolicy(
            self.session,
            config.user_agent,
            timeout=config.timeout,
            owner_override_hosts=config.owner_override_hosts,
        )
        self.fetcher = Fetcher(
            self.session,
            timeout=config.timeout,
            delay_seconds=config.delay_seconds,
            max_retries=config.max_retries,
            sleep=sleep,
            clock=clock,
        )

    def __enter__(self) -> RespectScraper:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.session.close()

    def check(self, url: str) -> Decision:
        """Whether robots.txt lets this scraper fetch the URL, and why."""
        return self.robots.decide(normalize_url(url))

    def crawl(
        self,
        url: str,
        *,
        max_depth: int | None = None,
        max_pages: int | None = None,
        download_files: bool | None = None,
    ) -> CrawlReport:
        """Crawl breadth-first from ``url``.

        ``max_depth`` 0 fetches only ``url`` (plus its linked files when downloading).
        """
        depth_limit = self.config.max_depth if max_depth is None else max_depth
        page_limit = self.config.max_pages if max_pages is None else max_pages
        downloads = self.config.download_files if download_files is None else download_files
        start = normalize_url(url)
        site = _site(urlsplit(start).hostname or "")
        report = CrawlReport(start, self.config.user_agent, datetime.now(timezone.utc).isoformat())

        queue: deque[tuple[str, int]] = deque([(start, 0)])
        seen = {start}
        kept = 0
        while queue:
            current, depth = queue.popleft()
            if kept >= page_limit:
                report.skipped.append(Skipped(current, depth, "max_pages_reached"))
                continue
            outcome = self._fetch(current, depth, site)
            if isinstance(outcome, Skipped):
                report.skipped.append(outcome)
                continue
            final_url, result, decision = outcome
            noindex, nofollow = robots_directives((result.headers or {}).get("x-robots-tag", ""))

            if result.content_type in HTML_TYPES:
                page = parse_html(result.content, final_url, _charset(result))
                noindex = noindex or page.noindex
                nofollow = nofollow or page.nofollow
                if noindex:
                    report.skipped.append(Skipped(current, depth, "noindex", decision=decision))
                else:
                    kept += 1
                    report.pages.append(
                        Page(
                            current,
                            final_url,
                            depth,
                            result.status or 0,
                            page.title,
                            page.description,
                            page.text,
                            len(page.text.split()),
                            decision,
                        )
                    )
                if nofollow:
                    continue
                for link in page.links:
                    if link in seen:
                        continue
                    kind = file_type(link)
                    if kind in self.config.file_types:
                        if downloads:  # linked files are fetched at any depth
                            seen.add(link)
                            queue.append((link, depth + 1))
                    elif depth < depth_limit:
                        seen.add(link)
                        queue.append((link, depth + 1))
                continue

            kind = file_type(final_url, result.content_type)
            if kind not in self.config.file_types or not (downloads or current == start):
                reason = (
                    "files_disabled" if kind in self.config.file_types else "unsupported_content"
                )
                report.skipped.append(
                    Skipped(current, depth, reason, result.content_type or None, decision)
                )
                continue
            if noindex:
                report.skipped.append(Skipped(current, depth, "noindex", decision=decision))
                continue
            try:
                text = extract_file(result.content, kind, max_bytes=self.config.max_file_bytes)
            except ExtractionError as exc:
                report.skipped.append(
                    Skipped(current, depth, "extraction_failed", str(exc), decision)
                )
                continue
            kept += 1
            report.files.append(
                Document(current, final_url, depth, kind, len(result.content), text, decision)
            )

        report.finished_at = datetime.now(timezone.utc).isoformat()
        if self.config.api.enabled:
            from .api import send_report

            send_report(self.config.api, report)
        return report

    def _fetch(
        self, url: str, depth: int, site: str
    ) -> tuple[str, FetchResult, Decision] | Skipped:
        """Fetch a URL, checking robots.txt and the site boundary on every redirect hop."""
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            host = urlsplit(current).hostname or ""
            if self.config.same_site_only and _site(host) != site:
                return Skipped(url, depth, "outside_site", current)
            decision = self.robots.decide(current)
            if not decision.allowed:
                return Skipped(url, depth, decision.reason.value, decision.explain(), decision)
            result = self.fetcher.get(
                current, max_bytes=self.config.max_file_bytes, crawl_delay=decision.crawl_delay
            )
            if result.error:
                reason = "too_large" if result.error.startswith("too_large") else "fetch_failed"
                return Skipped(url, depth, reason, result.error, decision)
            if result.is_redirect:
                current = normalize_url(urljoin(current, result.location or ""))
                continue
            if not result.ok:
                return Skipped(url, depth, f"http_{result.status}", None, decision)
            return current, result, decision
        return Skipped(url, depth, "too_many_redirects")


def _charset(result: FetchResult) -> str | None:
    content_type = (result.headers or {}).get("content-type", "")
    for part in content_type.split(";")[1:]:
        key, _, value = part.strip().partition("=")
        if key.lower() == "charset" and value:
            return value.strip('"')
    return None
