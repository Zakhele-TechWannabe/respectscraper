import io

import pytest

from respectscraper import Config, RespectScraper
from respectscraper.cli import EXIT_DECLINED, EXIT_DISALLOWED, EXIT_OK, main

ROBOTS = "User-agent: *\nCrawl-delay: 3\nDisallow: /private/\nAllow: /private/press/\n"


def scraper(no_sleep) -> RespectScraper:
    config = Config(delay_seconds=0, user_agent="RespectScraper/0.2 (+test)")
    return RespectScraper(config, sleep=no_sleep.append)


@pytest.fixture
def civic(site):
    site.add("/robots.txt", ROBOTS, Content_Type="text/plain")
    site.html("/", '<a href="/notices">notices</a><a href="/private/minutes">minutes</a>')
    site.html("/notices", "Public notice")
    site.html("/private/minutes", "SECRET")
    return site


def test_preflight_summarises_the_rules_once(civic, no_sleep) -> None:
    with scraper(no_sleep) as s:
        plan = s.preflight(civic.base + "/", max_depth=1)
        report = s.crawl(civic.base + "/", max_depth=1)

    assert plan.can_crawl and plan.pacing_seconds == 3
    assert plan.robots.status == "found" and plan.robots.agent == "*"
    assert plan.robots.rules == ("line 3: Disallow: /private/", "line 4: Allow: /private/press/")
    assert "Disallow: /private/" in plan.summary() and "still checked" in plan.summary()
    # robots.txt is read once: the preflight's copy is the one the crawl applies...
    assert civic.fetched().count("/robots.txt") == 1
    # ...and every page is still checked against it.
    assert "/private/minutes" not in civic.fetched()
    assert [p.url.removeprefix(civic.base) for p in report.pages] == ["/", "/notices"]


def test_report_keeps_the_robots_txt_it_obeyed(civic, no_sleep) -> None:
    with scraper(no_sleep) as s:
        plan = s.preflight(civic.base + "/")
        report = s.crawl(civic.base + "/")

    assert [r.fingerprint for r in report.robots] == [plan.robots.fingerprint]
    assert report.to_dict()["robots"][0]["rules"][0] == "line 3: Disallow: /private/"


def test_approval_holds_while_robots_txt_is_unchanged(civic, no_sleep) -> None:
    with scraper(no_sleep) as s:
        approved = s.preflight(civic.base + "/").robots.fingerprint
    with scraper(no_sleep) as later:  # e.g. a background worker, hours later
        report = later.crawl(civic.base + "/", approved_fingerprint=approved)

    assert report.ok


def test_changed_robots_txt_voids_the_approval(civic, no_sleep) -> None:
    with scraper(no_sleep) as s:
        approved = s.preflight(civic.base + "/").robots.fingerprint
    civic.add("/robots.txt", "User-agent: *\nDisallow: /\n", Content_Type="text/plain")

    with scraper(no_sleep) as later:
        report = later.crawl(civic.base + "/", approved_fingerprint=approved)

    assert report.pages == [] and report.skipped[0].reason == "robots_changed_since_approval"
    assert civic.fetched().count("/") == 0


def test_missing_and_unreachable_robots_txt_are_explicit(site, no_sleep) -> None:
    site.html("/", "hi")
    with scraper(no_sleep) as s:
        missing = s.preflight(site.base + "/")
    site.add("/robots.txt", "down", status=503)
    with scraper(no_sleep) as s:
        down = s.preflight(site.base + "/")

    assert missing.robots.status == "missing" and missing.can_crawl
    assert down.robots.status == "unreachable" and not down.can_crawl
    assert missing.robots.fingerprint != down.robots.fingerprint
    assert "treated as disallowed" in down.summary()


def test_cli_preflight(civic, capsys) -> None:
    assert main(["preflight", civic.base + "/", "--depth", "1"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "line 3: Disallow: /private/" in out and "depth 1" in out
    assert main(["preflight", civic.base + "/private/minutes"]) == EXIT_DISALLOWED


def interactive(monkeypatch, answer: str) -> None:
    monkeypatch.setattr("respectscraper.cli._interactive", lambda: True)
    monkeypatch.setattr("sys.stdin", io.StringIO(answer + "\n"))


def test_cli_scrape_asks_once_and_respects_no(civic, monkeypatch, capsys) -> None:
    interactive(monkeypatch, "n")

    assert main(["scrape", civic.base + "/", "--depth", "1"]) == EXIT_DECLINED
    assert civic.fetched() == ["/robots.txt"]
    captured = capsys.readouterr()
    assert "Crawl with these rules?" in captured.err and captured.out == ""


def test_cli_scrape_asks_once_then_crawls(civic, monkeypatch, tmp_path, capsys) -> None:
    interactive(monkeypatch, "y")
    config = tmp_path / "c.json"
    config.write_text('{"delay_seconds": 0}', encoding="utf-8")
    monkeypatch.setattr("time.sleep", lambda _: None)  # skip the site's 3s Crawl-delay

    code = main(["scrape", civic.base + "/", "-c", str(config), "--depth", "1", "-q"])

    assert code == EXIT_OK
    captured = capsys.readouterr()
    assert captured.err.count("Crawl with these rules?") == 1
    assert captured.out.startswith("{")  # the report on stdout is pure JSON
    assert civic.fetched().count("/robots.txt") == 1


def test_cli_scrape_does_not_prompt_when_told_yes(civic, monkeypatch, capsys) -> None:
    monkeypatch.setattr("respectscraper.cli._interactive", lambda: True)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))  # any prompt would read nothing

    assert main(["scrape", civic.base + "/", "--yes", "-q"]) == EXIT_OK
    assert "Crawl with these rules?" not in capsys.readouterr().err
