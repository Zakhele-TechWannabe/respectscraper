import pytest

from respectscraper import Config, RespectScraper
from respectscraper.robots import Reason


def scraper(site, no_sleep, **settings) -> RespectScraper:
    config = Config(delay_seconds=0, user_agent="RespectScraper/0.2 (+test)", **settings)
    return RespectScraper(config, sleep=no_sleep.append)


@pytest.fixture
def small_site(site):
    site.add("/robots.txt", "User-agent: *\nDisallow: /private/\n", Content_Type="text/plain")
    site.html(
        "/",
        '<p>Hello</p><p>World</p><a href="/two#top">two</a><a href="/two">again</a>'
        '<a href="/private/secret">secret</a><a href="/private/report.txt">report</a>'
        '<a href="/files/guide.txt">guide</a><a href="https://elsewhere.example/">off</a>',
    )
    site.html("/two", '<a href="/three">three</a>')
    site.html("/three", "deep")
    site.html("/private/secret", "SECRET")
    site.add("/private/report.txt", "private report", Content_Type="text/plain")
    site.add("/files/guide.txt", "the guide", Content_Type="text/plain")
    return site


def test_robots_txt_applies_to_every_nested_page_and_file(small_site, no_sleep) -> None:
    report = scraper(small_site, no_sleep).crawl(
        small_site.base + "/", max_depth=2, download_files=True
    )

    assert "/private/secret" not in small_site.fetched()
    assert "/private/report.txt" not in small_site.fetched()
    blocked = {
        s.url.rsplit("/", 1)[1]: s
        for s in report.skipped
        if s.reason == Reason.DISALLOWED_BY_RULE.value
    }
    assert set(blocked) == {"secret", "report.txt"}
    assert blocked["secret"].decision.rule == "Disallow: /private/"
    assert [p.url.removeprefix(small_site.base) for p in report.pages] == ["/", "/two", "/three"]
    assert [f.text for f in report.files] == ["the guide"]


def test_text_keeps_word_boundaries(small_site, no_sleep) -> None:
    page = scraper(small_site, no_sleep).crawl(small_site.base + "/").pages[0]

    assert page.text.startswith("Hello World")
    assert page.word_count == len(page.text.split())


def test_fragments_and_duplicates_are_fetched_once(small_site, no_sleep) -> None:
    scraper(small_site, no_sleep).crawl(small_site.base + "/", max_depth=1)

    assert small_site.fetched().count("/two") == 1


def test_depth_zero_fetches_only_the_start_page(small_site, no_sleep) -> None:
    report = scraper(small_site, no_sleep).crawl(small_site.base + "/")

    assert len(report.pages) == 1 and report.files == []


def test_links_off_site_are_never_requested(small_site, no_sleep) -> None:
    report = scraper(small_site, no_sleep).crawl(small_site.base + "/", max_depth=1)

    off_site = [s for s in report.skipped if "elsewhere" in s.url]
    assert [s.reason for s in off_site] == ["outside_site"]  # recorded, never requested
    assert all(p.final_url.startswith(small_site.base) for p in report.pages)


def test_max_pages_stops_the_crawl(small_site, no_sleep) -> None:
    report = scraper(small_site, no_sleep).crawl(small_site.base + "/", max_depth=2, max_pages=2)

    assert len(report.pages) == 2
    assert any(s.reason == "max_pages_reached" for s in report.skipped)


def test_redirects_are_checked_against_robots_txt(site, no_sleep) -> None:
    site.add("/robots.txt", "User-agent: *\nDisallow: /private/\n", Content_Type="text/plain")
    site.add("/go", status=302, Location="/private/landing")
    site.html("/private/landing", "hidden")

    report = scraper(site, no_sleep).crawl(site.base + "/go")

    assert report.pages == []
    assert report.skipped[0].reason == "disallowed_by_rule"
    assert "/private/landing" not in site.fetched()


def test_crawl_delay_paces_requests_to_the_host(site, no_sleep) -> None:
    site.add("/robots.txt", "User-agent: *\nCrawl-delay: 3\nDisallow:\n", Content_Type="text/plain")
    site.html("/", '<a href="/b">b</a>')
    site.html("/b", "b")

    scraper(site, no_sleep).crawl(site.base + "/", max_depth=1)

    assert no_sleep and max(no_sleep) > 2.5


def test_meta_noindex_and_nofollow_are_honoured(site, no_sleep) -> None:
    site.add("/robots.txt", "", Content_Type="text/plain")
    site.html("/", '<meta name="robots" content="noindex, nofollow"><a href="/next">next</a>')
    site.html("/next", "next")

    report = scraper(site, no_sleep).crawl(site.base + "/", max_depth=1)

    assert report.pages == [] and report.skipped[0].reason == "noindex"
    assert "/next" not in site.fetched()


def test_x_robots_tag_header_is_honoured(site, no_sleep) -> None:
    site.add("/robots.txt", "", Content_Type="text/plain")
    site.html("/", "content", X_Robots_Tag="noindex")

    report = scraper(site, no_sleep).crawl(site.base + "/")

    assert report.pages == [] and report.skipped[0].reason == "noindex"


def test_oversized_downloads_are_refused_before_reading(site, no_sleep) -> None:
    site.add("/robots.txt", "", Content_Type="text/plain")
    site.add("/big.txt", b"x" * 300_000, Content_Type="text/plain")

    report = scraper(site, no_sleep, max_file_mb=0.1).crawl(site.base + "/big.txt")

    assert report.files == [] and report.skipped[0].reason == "too_large"


def test_server_errors_are_reported_not_raised(site, no_sleep) -> None:
    site.add("/robots.txt", "", Content_Type="text/plain")
    site.add("/broken", "boom", status=500)

    report = scraper(site, no_sleep, max_retries=0).crawl(site.base + "/broken")

    assert report.ok is False and report.skipped[0].reason == "http_500"


def test_report_serialises_with_decisions(small_site, no_sleep) -> None:
    data = scraper(small_site, no_sleep).crawl(small_site.base + "/").to_dict()

    assert data["ok"] is True
    assert data["pages"][0]["decision"]["reason"] == "no_matching_rule"
    assert "explanation" in data["pages"][0]["decision"]
