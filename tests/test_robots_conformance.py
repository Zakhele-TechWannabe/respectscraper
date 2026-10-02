import json
from pathlib import Path

import pytest

from respectscraper.robots import RobotsTxt

SPEC = json.loads((Path(__file__).parent / "conformance" / "robots_cases.json").read_text())


@pytest.mark.parametrize("case", SPEC["cases"], ids=[c["name"] for c in SPEC["cases"]])
def test_conformance(case: dict) -> None:
    robots = RobotsTxt.parse(case["robots_txt"])
    allowed, rule, _, _ = robots.check(
        "https://example.com" + case["path"], SPEC["user_agent_token"]
    )

    assert allowed is case["allowed"]
    assert (rule.text if rule else None) == case["rule"]


def test_rules_record_their_line_numbers() -> None:
    robots = RobotsTxt.parse("# header\nUser-agent: *\n\nDisallow: /a\nAllow: /a/b\n")
    _, rule, agent, _ = robots.check("https://example.com/a/x", "RespectScraper")

    assert (rule.text, rule.line, agent) == ("Disallow: /a", 4, "*")


def test_crawl_delay_comes_from_the_applicable_group() -> None:
    robots = RobotsTxt.parse(
        "User-agent: *\nCrawl-delay: 1\n\nUser-agent: RespectScraper\nCrawl-delay: 4.5\nDisallow:"
    )

    assert robots.check("https://example.com/", "RespectScraper")[3] == 4.5
    assert robots.check("https://example.com/", "OtherBot")[3] == 1.0


def test_sitemaps_are_collected() -> None:
    robots = RobotsTxt.parse("Sitemap: https://example.com/sitemap.xml\nUser-agent: *\nDisallow:")

    assert robots.sitemaps == ["https://example.com/sitemap.xml"]
