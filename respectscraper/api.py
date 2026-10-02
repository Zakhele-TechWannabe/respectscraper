"""Optional delivery of crawl reports to an HTTP endpoint."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

from ._version import __version__
from .config import APIConfig

if TYPE_CHECKING:
    from .crawler import CrawlReport

logger = logging.getLogger(__name__)


def send_report(config: APIConfig, report: CrawlReport) -> bool:
    """POST (or PUT/PATCH) the report as JSON. Returns False instead of raising."""
    payload = {"scraper": "respectscraper", "version": __version__, "report": report.to_dict()}
    try:
        response = requests.request(
            config.method.upper(),
            config.endpoint,
            json=payload,
            headers=config.headers,
            timeout=config.timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Could not deliver the crawl report: %s", type(exc).__name__)
        return False
    return True
