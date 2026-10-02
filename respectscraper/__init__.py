"""RespectScraper: crawl websites within their robots.txt, with a reason for every request.

from respectscraper import RespectScraper

with RespectScraper() as scraper:
    print(scraper.check("https://example.com/private/").explain())
    report = scraper.crawl("https://example.com", max_depth=1)
"""

from ._version import __version__
from .config import APIConfig, Config, ConfigError, LLMConfig
from .crawler import CrawlReport, Document, Page, RespectScraper, Skipped
from .extract import ExtractionError, normalize_url
from .robots import Decision, Reason, RobotsPolicy, RobotsTxt

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
    "Reason",
    "RespectScraper",
    "RobotsPolicy",
    "RobotsTxt",
    "Skipped",
    "__version__",
    "normalize_url",
]
