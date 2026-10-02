import requests

from respectscraper.robots import Reason, RobotsPolicy

UA = "RespectScraper/0.2 (+test)"


def policy(**kwargs) -> RobotsPolicy:
    return RobotsPolicy(requests.Session(), UA, timeout=5, **kwargs)


def test_decisions_cite_the_matching_rule_and_line(site) -> None:
    site.add("/robots.txt", "User-agent: *\nDisallow: /private/\n", Content_Type="text/plain")
    p = policy()

    blocked = p.decide(site.base + "/private/report.html")
    open_page = p.decide(site.base + "/public")

    assert (blocked.allowed, blocked.reason, blocked.rule, blocked.line) == (
        False,
        Reason.DISALLOWED_BY_RULE,
        "Disallow: /private/",
        2,
    )
    assert "Disallow: /private/" in blocked.explain() and "line 2" in blocked.explain()
    assert (open_page.allowed, open_page.reason) == (True, Reason.NO_MATCHING_RULE)


def test_robots_txt_is_fetched_once_per_origin_with_our_user_agent(site) -> None:
    site.add("/robots.txt", "User-agent: *\nDisallow:\n", Content_Type="text/plain")
    p = policy()
    for path in ("/a", "/b", "/c"):
        p.decide(site.base + path)

    assert site.requests == [("/robots.txt", UA)]


def test_missing_robots_txt_allows_crawling(site) -> None:
    decision = policy().decide(site.base + "/page")

    assert (decision.allowed, decision.reason, decision.detail) == (
        True,
        Reason.NO_ROBOTS_TXT,
        "HTTP 404",
    )


def test_server_errors_mean_disallow_everything(site) -> None:
    site.add("/robots.txt", "oops", status=503)

    decision = policy().decide(site.base + "/page")

    assert (decision.allowed, decision.reason) == (False, Reason.ROBOTS_UNREACHABLE)
    assert "treated as disallowed" in decision.explain()


def test_rate_limiting_robots_txt_means_disallow(site) -> None:
    site.add("/robots.txt", "slow down", status=429)

    assert policy().decide(site.base + "/page").allowed is False


def test_unreachable_host_means_disallow() -> None:
    decision = policy().decide("http://127.0.0.1:9/page")  # discard port: nothing listens

    assert (decision.allowed, decision.reason) == (False, Reason.ROBOTS_UNREACHABLE)


def test_robots_txt_is_always_fetchable(site) -> None:
    site.add("/robots.txt", "User-agent: *\nDisallow: /\n", Content_Type="text/plain")

    assert policy().decide(site.base + "/robots.txt").reason == Reason.ROBOTS_TXT_ITSELF


def test_owner_override_is_per_host_and_recorded(site) -> None:
    site.add("/robots.txt", "User-agent: *\nDisallow: /\n", Content_Type="text/plain")
    p = policy(owner_override_hosts=("127.0.0.1",))

    decision = p.decide(site.base + "/page")

    assert (decision.allowed, decision.reason) == (True, Reason.OWNER_OVERRIDE)
    assert site.requests == []  # robots.txt is not even consulted for the owner's host
