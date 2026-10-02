"""robots.txt parsing and decisions, following RFC 9309.

Every decision records why it was made: the robots.txt it came from, the user-agent
group that applied, and the exact rule and line that matched. Nothing here guesses;
an LLM may explain a decision (see ``respectscraper.llm``) but never changes one.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from urllib.parse import quote, urlsplit

import requests

MAX_ROBOTS_BYTES = 500 * 1024  # RFC 9309 2.5: parse at least the first 500 KiB
CACHE_SECONDS = 24 * 60 * 60  # RFC 9309 2.4: a cached copy is good for up to 24 hours
MAX_REDIRECTS = 5  # RFC 9309 2.3.1.2: follow at least five redirects

_UNRESERVED = re.compile(r"%([0-9A-Fa-f]{2})")
_UNRESERVED_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


class Reason(str, Enum):
    """Why a URL was allowed or not."""

    ALLOWED_BY_RULE = "allowed_by_rule"
    DISALLOWED_BY_RULE = "disallowed_by_rule"
    NO_MATCHING_RULE = "no_matching_rule"
    NO_ROBOTS_TXT = "no_robots_txt"
    ROBOTS_UNREACHABLE = "robots_unreachable"
    ROBOTS_TXT_ITSELF = "robots_txt_itself"
    OWNER_OVERRIDE = "owner_override"


@dataclass(frozen=True)
class Rule:
    allow: bool
    pattern: str
    line: int

    @property
    def text(self) -> str:
        return f"{'Allow' if self.allow else 'Disallow'}: {self.pattern}"


@dataclass
class Group:
    agents: list[str]
    rules: list[Rule] = field(default_factory=list)
    crawl_delay: float | None = None


@dataclass(frozen=True)
class Decision:
    """The outcome for one URL, with the evidence behind it."""

    url: str
    allowed: bool
    reason: Reason
    robots_url: str
    rule: str | None = None
    line: int | None = None
    agent: str | None = None
    crawl_delay: float | None = None
    detail: str | None = None

    def explain(self) -> str:
        """One plain sentence saying why."""
        where = f" (line {self.line})" if self.line else ""
        group = f" for user-agent '{self.agent}'" if self.agent else ""
        messages = {
            Reason.ALLOWED_BY_RULE: f"Allowed by '{self.rule}'{where}{group}.",
            Reason.DISALLOWED_BY_RULE: f"Disallowed by '{self.rule}'{where}{group}.",
            Reason.NO_MATCHING_RULE: f"Allowed: no rule{group} matches this path.",
            Reason.NO_ROBOTS_TXT: "Allowed: the site has no robots.txt"
            + (f" ({self.detail})." if self.detail else "."),
            Reason.ROBOTS_UNREACHABLE: "Not fetched: robots.txt could not be retrieved"
            + (f" ({self.detail})" if self.detail else "")
            + ", so the whole site is treated as disallowed.",
            Reason.ROBOTS_TXT_ITSELF: "Allowed: robots.txt itself is always fetchable.",
            Reason.OWNER_OVERRIDE: "Allowed: this host is listed in owner_override_hosts.",
        }
        return messages[self.reason]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["reason"] = self.reason.value
        data["explanation"] = self.explain()
        return data


def _normalize(value: str) -> str:
    """Percent-encode consistently so patterns and paths compare octet for octet."""

    def fix(match: re.Match[str]) -> str:
        char = chr(int(match.group(1), 16))
        return char if char in _UNRESERVED_CHARS else f"%{match.group(1).upper()}"

    encoded = quote(value, safe="/?=&;:@!$'()*+,%-._~[]")
    return _UNRESERVED.sub(fix, encoded)


def _compile(pattern: str) -> re.Pattern[str]:
    anchored = pattern.endswith("$")
    body = _normalize(pattern[:-1] if anchored else pattern)
    regex = ".*".join(re.escape(part) for part in body.split("*"))
    return re.compile(regex + ("$" if anchored else ""))


def _specificity(pattern: str) -> int:
    return len(_normalize(pattern).encode())


class RobotsTxt:
    """A parsed robots.txt."""

    def __init__(self, groups: list[Group], sitemaps: list[str]) -> None:
        self.groups = groups
        self.sitemaps = sitemaps

    @classmethod
    def parse(cls, text: str) -> RobotsTxt:
        groups: list[Group] = []
        sitemaps: list[str] = []
        current: Group | None = None
        last_was_agent = False
        text = text.lstrip("﻿")
        for number, raw in enumerate(text.splitlines(), start=1):
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            key = key.lower().replace(" ", "").replace("_", "-")
            if key in ("user-agent", "useragent"):
                if current is None or not last_was_agent:
                    current = Group(agents=[])
                    groups.append(current)
                current.agents.append(value)
                last_was_agent = True
                continue
            last_was_agent = False
            if key == "sitemap":
                sitemaps.append(value)
            elif current is None:
                continue  # rules before any user-agent line belong to no group
            elif key in ("allow", "disallow"):
                if not value:
                    continue  # an empty rule matches nothing
                if not value.startswith(("/", "*")):
                    value = "/" + value
                current.rules.append(Rule(allow=key == "allow", pattern=value, line=number))
            elif key == "crawl-delay":
                try:
                    delay = float(value)
                except ValueError:
                    continue
                if delay >= 0:
                    current.crawl_delay = delay
        return cls(groups, sitemaps)

    def _groups_for(self, product_token: str) -> tuple[list[Group], str | None]:
        token = product_token.lower()
        named = [
            g
            for g in self.groups
            if any(agent.split("/", 1)[0].strip().lower() == token for agent in g.agents)
        ]
        if named:
            return named, product_token
        star = [g for g in self.groups if any(agent.strip() == "*" for agent in g.agents)]
        return star, ("*" if star else None)

    def check(
        self, url: str, product_token: str
    ) -> tuple[bool, Rule | None, str | None, float | None]:
        """Returns (allowed, matching rule, agent group used, crawl delay)."""
        parts = urlsplit(url)
        path = _normalize((parts.path or "/") + (f"?{parts.query}" if parts.query else ""))
        groups, agent = self._groups_for(product_token)
        best: Rule | None = None
        for rule in (rule for group in groups for rule in group.rules):
            if not _compile(rule.pattern).match(path):
                continue
            if best is None:
                best = rule
                continue
            mine, theirs = _specificity(rule.pattern), _specificity(best.pattern)
            # The longest match wins; on a tie, allow wins (RFC 9309 2.2.2).
            if mine > theirs or (mine == theirs and rule.allow and not best.allow):
                best = rule
        delays = [g.crawl_delay for g in groups if g.crawl_delay is not None]
        return (best is None or best.allow), best, agent, (max(delays) if delays else None)


@dataclass
class _Entry:
    fetched_at: float
    robots: RobotsTxt | None = None  # None with no failure: allow everything
    failure: str | None = None  # set when robots.txt was unreachable
    detail: str | None = None


class RobotsPolicy:
    """Fetches robots.txt once per origin, caches it, and decides per URL."""

    def __init__(
        self,
        session: requests.Session,
        user_agent: str,
        *,
        timeout: float = 20,
        owner_override_hosts: tuple[str, ...] = (),
        clock=time.time,
    ) -> None:
        self.session = session
        self.user_agent = user_agent
        self.product_token = user_agent.split("/", 1)[0].split()[0]
        self.timeout = timeout
        self.owner_override_hosts = {host.lower() for host in owner_override_hosts}
        self.clock = clock
        self._cache: dict[str, _Entry] = {}
        self.texts: dict[str, str] = {}

    @staticmethod
    def robots_url(url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}/robots.txt"

    def decide(self, url: str) -> Decision:
        parts = urlsplit(url)
        robots_url = self.robots_url(url)
        host = (parts.hostname or "").lower()
        if host in self.owner_override_hosts:
            return Decision(url, True, Reason.OWNER_OVERRIDE, robots_url)
        if parts.path == "/robots.txt":
            return Decision(url, True, Reason.ROBOTS_TXT_ITSELF, robots_url)

        entry = self._entry(robots_url)
        if entry.failure:
            return Decision(url, False, Reason.ROBOTS_UNREACHABLE, robots_url, detail=entry.detail)
        if entry.robots is None:
            return Decision(url, True, Reason.NO_ROBOTS_TXT, robots_url, detail=entry.detail)
        allowed, rule, agent, delay = entry.robots.check(url, self.product_token)
        if rule is None:
            return Decision(
                url, True, Reason.NO_MATCHING_RULE, robots_url, agent=agent, crawl_delay=delay
            )
        return Decision(
            url,
            allowed,
            Reason.ALLOWED_BY_RULE if allowed else Reason.DISALLOWED_BY_RULE,
            robots_url,
            rule=rule.text,
            line=rule.line,
            agent=agent,
            crawl_delay=delay,
        )

    def crawl_delay(self, url: str) -> float | None:
        entry = self._entry(self.robots_url(url))
        if entry.robots is None:
            return None
        return entry.robots.check(url, self.product_token)[3]

    def _entry(self, robots_url: str) -> _Entry:
        cached = self._cache.get(robots_url)
        if cached and self.clock() - cached.fetched_at < CACHE_SECONDS:
            return cached
        entry = self._fetch(robots_url)
        self._cache[robots_url] = entry
        return entry

    def _fetch(self, robots_url: str) -> _Entry:
        now = self.clock()
        try:
            response = self.session.get(
                robots_url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                stream=True,
            )
            body = response.raw.read(MAX_ROBOTS_BYTES, decode_content=True) if response.ok else b""
            response.close()
        except requests.RequestException as exc:
            return _Entry(now, failure="network", detail=type(exc).__name__)

        status = response.status_code
        if 200 <= status < 300:
            text = body.decode("utf-8", errors="replace")  # RFC 9309 2.3: UTF-8
            self.texts[robots_url] = text
            return _Entry(now, robots=RobotsTxt.parse(text))
        if status == 429 or status >= 500:
            # Unreachable: RFC 9309 2.3.1.4 says assume complete disallow.
            return _Entry(now, failure="status", detail=f"HTTP {status}")
        # Any other 4xx means unavailable: RFC 9309 2.3.1.3 allows crawling.
        return _Entry(now, detail=f"HTTP {status}")
