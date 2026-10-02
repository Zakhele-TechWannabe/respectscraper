# RespectScraper

[![CI](https://github.com/Zakhele-TechWannabe/respectscraper/actions/workflows/ci.yml/badge.svg)](https://github.com/Zakhele-TechWannabe/respectscraper/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/respectscraper)](https://pypi.org/project/respectscraper/)
[![Python](https://img.shields.io/pypi/pyversions/respectscraper)](https://pypi.org/project/respectscraper/)
[![License](https://img.shields.io/pypi/l/respectscraper)](LICENSE)

A Python crawler that follows a site's robots.txt (RFC 9309) on every request it makes and records the reason for each one.

Every page and file it fetches, and every one it refuses, comes with a decision that cites the robots.txt rule, line number and user-agent group behind it. The decision comes from a parser, never a model, so the same input always gives the same answer.

```console
$ respectscraper check https://example.com/private/report.pdf
NOT ALLOWED  https://example.com/private/report.pdf
  Disallowed by 'Disallow: /private/' (line 3) for user-agent '*'.
  robots.txt: https://example.com/robots.txt
  crawl-delay: 2.0s
```

## Install

```bash
pip install respectscraper
```

Requires Python 3.10 or later.

## What it does

- **robots.txt per request.** Each URL is checked before it is fetched, including pages found while crawling, linked files and every redirect hop. A redirect into a disallowed path is not followed.
- **RFC 9309 semantics.**
  - The longest matching rule wins, and Allow wins a tie.
  - `*` and `$` wildcards are supported, and percent-encoding is normalised.
  - Groups that name the same agent are merged.
  - A robots.txt that returns 4xx means no restrictions. One that returns 5xx or 429, or fails to fetch, means the site is treated as disallowed until it can be read.
  - robots.txt is fetched once per origin and cached for 24 hours.
  - The parser is tested against 38 conformance cases in [tests/conformance](tests/conformance/robots_cases.json).
- **Polite by default.**
  - Requests to one host are spaced by `delay_seconds`, or by the site's `Crawl-delay` if that is longer.
  - Retries are bounded, and `Retry-After` is honoured (capped at 60s).
  - The crawler identifies itself with a user agent that links back to this repository.
- **Page-level directives.** `noindex` and `nofollow` in `<meta name="robots">` or the `X-Robots-Tag` header are honoured, as are `rel="nofollow"` links.
- **Bounded downloads.** Size limits apply while streaming, not after the download finishes. Office files are checked for zip bombs before they are opened.
- **Text extraction** from HTML, PDF, DOCX, XLSX, TXT and CSV.

## Command line

```bash
respectscraper check URL                 # is this URL allowed, and why (exit code 3 if not)
respectscraper check URL --json          # the same decision as JSON
respectscraper scrape URL                # fetch one page, print a JSON report
respectscraper scrape URL --depth 2 --max-pages 100 --download -o report.json
respectscraper config --create           # write respectscraper.json with the defaults
respectscraper info                      # version and defaults
```

Exit codes: `0` success, `1` error, `2` usage or configuration problem, `3` disallowed by robots.txt.

## Python

```python
from respectscraper import RespectScraper

with RespectScraper({"max_depth": 1, "download_files": True}) as scraper:
    decision = scraper.check("https://example.com/private/")
    print(decision.allowed, decision.explain())

    report = scraper.crawl("https://example.com/")
    for page in report.pages:
        print(page.url, page.title, page.word_count)
    for skipped in report.skipped:
        print("skipped", skipped.url, skipped.reason)
```

`crawl` returns a `CrawlReport` with `pages`, `files` and `skipped`. Every entry carries its `Decision`, and `report.to_dict()` gives the JSON the CLI prints. Skip reasons include:

- `disallowed_by_rule`, `robots_unreachable`, `noindex`, `outside_site`
- `too_large`, `files_disabled`, `unsupported_content`, `extraction_failed`
- `http_<status>`, `fetch_failed`, `too_many_redirects`, `max_pages_reached`

## Configuration

Pass a dict, a `Config`, or a path to a JSON file. Unknown keys are rejected, so a typo cannot silently change behaviour.

```json
{
  "user_agent": "RespectScraper/0.2.0 (+https://github.com/Zakhele-TechWannabe/respectscraper)",
  "timeout": 20,
  "max_retries": 2,
  "delay_seconds": 1.0,
  "max_depth": 0,
  "max_pages": 50,
  "same_site_only": true,
  "download_files": false,
  "file_types": [".pdf", ".docx", ".xlsx", ".txt", ".csv"],
  "max_file_mb": 25,
  "verify_ssl": true,
  "owner_override_hosts": [],
  "llm": { "provider": "openai", "model": "", "api_key_env": "RESPECTSCRAPER_LLM_API_KEY" },
  "api": { "enabled": false, "endpoint": "", "method": "POST", "headers": {} }
}
```

**Sites you own.** To crawl a site you own, list its host in `owner_override_hosts` or pass `--owner HOST`. The override applies only to that host and shows as `owner_override` in every decision it affects.

**Plain-language explanations (optional).** `respectscraper check URL --explain` asks a model to explain the decision in a sentence or two.
- It supports OpenAI, Anthropic, or any OpenAI-compatible `base_url`.
- The key is read from the environment variable named in `api_key_env`, never from the config file.
- The explanation is advisory only and never changes a decision. The robots.txt text is sent to the model as data, not as instructions.

**Report delivery (optional).** With `api.enabled`, each crawl report is sent as JSON to an HTTPS endpoint you control.

## Upgrading from 0.1.x

0.2.0 is a rewrite. The main changes:

| 0.1.x | 0.2.0 |
| --- | --- |
| `from webscraper import WebScraper` | `from respectscraper import RespectScraper` (the old import still works for now, with a deprecation warning) |
| robots.txt checked for the start URL only | checked for every page, file and redirect |
| an LLM could decide ambiguous robots.txt files | the parser decides; an LLM can only explain |
| `brute_force`, `--brute-force` | removed |
| `user_owns_site`, `--user-owns-site` | `owner_override_hosts`, `--owner HOST` |
| `allow_ssl_bypass`, `--ssl-bypass` | `--insecure`, for one run only |
| `llm.api_key` in the config file | `RESPECTSCRAPER_LLM_API_KEY` in the environment |
| `.doc` and `.xls` listed as supported | removed (they were never extracted) |

Old configuration files still load, with a warning, unless they enable a removed bypass or contain an API key. In those cases loading fails with a message saying what to change. See the [changelog](CHANGELOG.md) for the full list.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest                      # runs against a local HTTP server; no network needed
ruff check . && ruff format --check . && mypy respectscraper webscraper
```

CI runs lint, type checks and the test suite on Python 3.10 to 3.13 and on Windows and macOS. It also builds the package and smoke-tests the installed wheel. Publishing a GitHub release tagged `vX.Y.Z` uploads to PyPI through trusted publishing, after the same checks pass and the tag is confirmed to match the package version.

## License

Apache 2.0. See [LICENSE](LICENSE).
