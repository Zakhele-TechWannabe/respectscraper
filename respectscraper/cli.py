"""respectscraper command line."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import replace
from pathlib import Path

from ._version import __version__
from .config import Config, ConfigError
from .crawler import RespectScraper
from .extract import normalize_url

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_DISALLOWED = 0, 1, 2, 3

REMOVED_FLAGS = {
    "--brute-force": "was removed in 0.2.0; to crawl a site you own, use --owner HOST",
    "--user-owns-site": "was removed in 0.2.0; use --owner HOST to name the site you own",
    "--ssl-bypass": "was removed in 0.2.0; use --insecure, which affects only this run",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="respectscraper",
        description="Crawl websites within their robots.txt, with a reason for every request.",
    )
    parser.add_argument("--version", action="version", version=f"respectscraper {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="log each request")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="say whether robots.txt allows a URL, and why")
    check.add_argument("url")
    check.add_argument("--config", "-c", help="configuration file")
    check.add_argument("--user-agent", help="check as this user agent instead")
    check.add_argument(
        "--explain",
        action="store_true",
        help="add a plain-language explanation from the configured LLM",
    )
    check.add_argument("--json", action="store_true", help="print the decision as JSON")

    scrape = commands.add_parser("scrape", help="crawl from a URL and print a JSON report")
    scrape.add_argument("url")
    scrape.add_argument("--config", "-c", help="configuration file")
    scrape.add_argument("--depth", type=int, help="link depth to follow (0 = only this page)")
    scrape.add_argument(
        "--max-pages", type=int, help="stop after keeping this many pages and files"
    )
    scrape.add_argument("--download", action="store_true", help="download and extract linked files")
    scrape.add_argument(
        "--owner",
        action="append",
        default=[],
        metavar="HOST",
        help="a host you own; its robots.txt is not applied (repeatable)",
    )
    scrape.add_argument(
        "--insecure", action="store_true", help="skip TLS certificate checks for this run only"
    )
    scrape.add_argument("--output", "-o", help="write the report to this file")
    scrape.add_argument("--pretty", action="store_true", help="indent the JSON report")
    scrape.add_argument("--quiet", "-q", action="store_true", help="print only the report")

    config = commands.add_parser("config", help="write a default configuration file")
    config.add_argument("--create", action="store_true", required=True)
    config.add_argument("--path", default="respectscraper.json")
    config.add_argument("--force", action="store_true", help="overwrite an existing file")

    commands.add_parser("info", help="show version and defaults")
    return parser


def _load(path: str | None) -> Config:
    return Config.from_file(path) if path else Config()


def run_check(args: argparse.Namespace) -> int:
    config = _load(args.config)
    if args.user_agent:
        config = replace(config, user_agent=args.user_agent)
    with RespectScraper(config) as scraper:
        decision = scraper.check(args.url)
        explanation = None
        if args.explain:
            from .llm import LLMError, explain_decision

            try:
                text = scraper.robots.texts.get(decision.robots_url)
                explanation = explain_decision(config.llm, decision, text)
            except LLMError as exc:
                print(f"Explanation unavailable: {exc}", file=sys.stderr)
    if args.json:
        data = decision.to_dict()
        if explanation:
            data["llm_explanation"] = explanation
        print(json.dumps(data, indent=2))
    else:
        verdict = "ALLOWED" if decision.allowed else "NOT ALLOWED"
        print(f"{verdict}  {decision.url}")
        print(f"  {decision.explain()}")
        print(f"  robots.txt: {decision.robots_url}")
        if decision.crawl_delay:
            print(f"  crawl-delay: {decision.crawl_delay}s")
        if explanation:
            print(f"  explanation (advisory, from the LLM): {explanation}")
    return EXIT_OK if decision.allowed else EXIT_DISALLOWED


def run_scrape(args: argparse.Namespace) -> int:
    config = _load(args.config)
    if args.owner or args.insecure:
        config = replace(
            config,
            owner_override_hosts=(*config.owner_override_hosts, *args.owner),
            verify_ssl=config.verify_ssl and not args.insecure,
        )
    with RespectScraper(config) as scraper:
        report = scraper.crawl(
            args.url,
            max_depth=args.depth,
            max_pages=args.max_pages,
            download_files=args.download or None,
        )
    text = json.dumps(report.to_dict(), indent=2 if args.pretty else None, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)
    if not args.quiet:
        print(
            f"Kept {len(report.pages)} pages and {len(report.files)} files; "
            f"skipped {len(report.skipped)}.",
            file=sys.stderr,
        )
    if report.ok:
        return EXIT_OK
    start = normalize_url(args.url)
    blocked = any(s.url == start and s.decision and not s.decision.allowed for s in report.skipped)
    return EXIT_DISALLOWED if blocked else EXIT_ERROR


def run_config(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if path.exists() and not args.force:
        print(f"{path} already exists; use --force to overwrite it.", file=sys.stderr)
        return EXIT_ERROR
    path.write_text(json.dumps(Config().to_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}. Set RESPECTSCRAPER_LLM_API_KEY to enable explanations.")
    return EXIT_OK


def run_info() -> int:
    config = Config()
    print(f"respectscraper {__version__}")
    print(f"user agent:   {config.user_agent}")
    print("robots.txt:   RFC 9309, checked for every URL and every redirect hop")
    print(f"pacing:       {config.delay_seconds}s per host, or the site's Crawl-delay if longer")
    print(f"file types:   {', '.join(config.file_types)} (up to {config.max_file_mb:g} MB)")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    for flag, message in REMOVED_FLAGS.items():
        if flag in argv:
            print(f"respectscraper: {flag} {message}", file=sys.stderr)
            return EXIT_USAGE
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if getattr(args, "verbose", False) else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.command == "check":
            return run_check(args)
        if args.command == "scrape":
            return run_scrape(args)
        if args.command == "config":
            return run_config(args)
        return run_info()
    except ConfigError as exc:
        print(f"respectscraper: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
