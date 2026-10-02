"""Deprecated import name for respectscraper.

0.1.x code that does ``from webscraper import WebScraper`` keeps working through this
shim, which warns and returns results in the old shape. New code should use
``from respectscraper import RespectScraper``.
"""

from __future__ import annotations

import warnings
from typing import Any

from respectscraper import *  # noqa: F403
from respectscraper import Config, CrawlReport, RespectScraper, __version__  # noqa: F401

warnings.warn(
    "The 'webscraper' import name is deprecated; use 'respectscraper' instead.",
    DeprecationWarning,
    stacklevel=2,
)


class WebScraper(RespectScraper):
    """0.1.x-compatible wrapper around RespectScraper."""

    def __init__(self, config_path: str = "config.json") -> None:
        super().__init__(config_path)

    def scrape_url(
        self,
        url: str,
        nested: bool | None = None,
        download: bool | None = None,
        brute_force: bool | None = None,
        user_owns_site: bool = False,
    ) -> dict[str, Any]:
        if brute_force or user_owns_site:
            raise ValueError(
                "brute_force and user_owns_site were removed in 0.2.0. List hosts you own "
                "in owner_override_hosts instead."
            )
        depth = (self.config.max_depth or 1) if nested else 0
        report = self.crawl(url, max_depth=depth, download_files=download)
        return _legacy(report)


def _legacy(report: CrawlReport) -> dict[str, Any]:
    if not report.ok or not report.pages:
        reason = report.skipped[0] if report.skipped else None
        return {
            "url": report.start_url,
            "success": False,
            "error": reason.reason if reason else "scraping_failed",
            "reason": (reason.detail or reason.reason) if reason else "nothing fetched",
            "data": None,
        }
    first, *rest = report.pages

    def page(p: Any) -> dict[str, Any]:
        return {
            "url": p.url,
            "success": True,
            "data": {
                "title": p.title,
                "meta_description": p.description,
                "text_content": p.text,
                "word_count": p.word_count,
                "depth": p.depth,
            },
        }

    data = page(first)
    data["data"]["nested_pages"] = [page(p) for p in rest]
    data["data"]["extracted_files"] = [
        {
            "url": f.url,
            "success": True,
            "data": {"file_type": f.file_type, "content": f.text, "size_bytes": f.size_bytes},
        }
        for f in report.files
    ]
    return data
