"""RespectScraper: crawl websites within their robots.txt, with a reason for every request.

from respectscraper import RespectScraper

with RespectScraper() as scraper:
    plan = scraper.preflight("https://example.com", max_depth=1)
    print(plan.summary())  # approve once, then crawl; every URL is still checked
    report = scraper.crawl("https://example.com", max_depth=1)
"""

from ._version import __version__
from .config import APIConfig, Config, ConfigError, LLMConfig
from .crawler import CrawlReport, Document, Page, Preflight, RespectScraper, Skipped
from .extract import ExtractionError, normalize_url
from .robots import Decision, Reason, RobotsPolicy, RobotsSnapshot, RobotsTxt

__all__ = [
    "APIConfig",
    "Config",
    "ConfigError",
    "CrawlReport",
    "Decision",
    "Document",
    "ExtractionError",
    "LLMConfig",
    "Page",
    "Preflight",
    "Reason",
    "RespectScraper",
    "RobotsPolicy",
    "RobotsSnapshot",
    "RobotsTxt",
    "Skipped",
    "__version__",
    "normalize_url",
]
