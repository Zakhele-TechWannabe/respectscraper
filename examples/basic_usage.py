"""RespectScraper examples. Run: python examples/basic_usage.py https://example.com"""

import json
import sys

from respectscraper import RespectScraper


def main(url: str) -> None:
    with RespectScraper({"max_depth": 1, "max_pages": 10}) as scraper:
        # 1. Preflight: read robots.txt once and show what the crawl may do.
        plan = scraper.preflight(url)
        print(plan.summary())
        if not plan.can_crawl:
            return

        # 2. Crawl. Every page, file and skip carries its own decision.
        report = scraper.crawl(url)
        for page in report.pages:
            print(f"page  {page.url}  {page.title!r}  {page.word_count} words")
        for skipped in report.skipped:
            print(f"skip  {skipped.url}  {skipped.reason}")

        # 3. The whole report as JSON, the same shape the CLI prints.
        summary = report.to_dict()
        print(json.dumps({k: summary[k] for k in ("start_url", "ok")}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "https://example.com")
