# Changelog

All notable changes to the RespectScraper project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-02

A rewrite focused on correctness, safety and test coverage. The package is now imported as `respectscraper`, matching its install name.

### Security
- robots.txt is now checked for every URL the crawler fetches: nested pages, linked files and each redirect hop. Before this, only the start URL was checked.
- Removed `brute_force` and `user_owns_site`, which turned robots.txt off for every site. They are replaced by `owner_override_hosts` / `--owner HOST`, which applies to named hosts only and is recorded in each decision.
- Removed the process-wide TLS bypass and the automatic retry without certificate checks. `--insecure` now applies to a single run's session only.
- Downloads are capped while streaming, and Office files are checked for zip bombs before they are opened.
- LLM API keys are read from the environment only. A config file containing one is rejected.

### Changed
- robots.txt handling follows RFC 9309:
  - longest match wins, with Allow winning ties
  - `*` and `$` wildcards
  - percent-encoding normalisation
  - merged agent groups
  - a 500 KiB limit and a 24-hour cache
- A robots.txt that cannot be fetched (5xx, 429 or a network error) now means disallow, not allow.
- Every decision records its rule, line number, user-agent group and a reason code.
- The LLM no longer makes decisions. It can only explain one (`check --explain`), and robots.txt is passed to it as data.
- Requests honour `Crawl-delay` and `Retry-After`, with per-host pacing and bounded retries.
- `noindex` and `nofollow` are honoured from meta tags, `X-Robots-Tag` and `rel="nofollow"`.
- URLs are normalised, so fragments and duplicates are fetched once.
- Extracted HTML text keeps the spaces between words.
- Extraction errors are reported as skip reasons instead of being returned as page text.
- The library no longer writes `webscraper.log` or configures logging. Only the CLI does.
- PDF extraction uses `pypdf`, replacing the deprecated PyPDF2. Unused dependencies have been dropped.
- The CLI has `check`, `scrape`, `config` and `info` commands with documented exit codes. `scrape` prints one JSON report.
- Configuration is validated, and unknown keys are rejected.

### Removed
- `.doc` and `.xls` support, which was listed but never worked.
- The flags `--brute-force`, `--user-owns-site` and `--ssl-bypass`. Each now prints what to use instead.

### Deprecated
- `import webscraper` still works, with a warning, through a compatibility shim. 0.1.x config files load with a warning.

### Infrastructure
- New test suite: RFC 9309 conformance cases, plus crawler, policy, extraction, CLI and compatibility tests run against a local HTTP server.
- CI now fails on lint, type or test errors. It runs on Python 3.10 to 3.13, Windows and macOS, smoke-tests the built wheel and audits dependencies.
- Releases check that the tag matches the package version before publishing through trusted publishing.

## [0.1.0] - 2024-01-01

### Added
- Initial release of RespectScraper
- **Robots.txt Compliance**: Automatic robots.txt checking and compliance
- **AI-Powered Interpretation**: Configurable LLM integration (OpenAI, Anthropic, Custom) for ambiguous robots.txt files
- **Nested Link Crawling**: Recursive link following with depth control and domain restrictions
- **File Extraction**: Content extraction from PDF, Excel, Word, and text files
- **Rate Limiting**: Built-in respectful rate limiting with configurable delays
- **API Integration**: Configurable API endpoints for sending scraped data
- **JSON Configuration**: Comprehensive configuration system
- **Command Line Interface**: Full CLI with multiple commands and options
- **User Override Options**: Support for brute force mode and user-owned site declarations
- **Comprehensive Logging**: Configurable logging with file and console output
- **Error Handling**: Robust error handling and reporting
- **Installation Validation**: Built-in dependency and configuration validation

#### Core Features
- `WebScraper` class for main scraping functionality
- `RobotsChecker` for robots.txt compliance
- `FileExtractor` for content extraction from various file types
- `LLMClient` for AI-powered robots.txt interpretation
- `APIClient` for external API integration
- Comprehensive utility functions for URL handling and validation

#### CLI Commands
- `webscraper scrape` - Main scraping command with multiple options
- `webscraper config` - Configuration management (create, validate)
- `webscraper validate` - Installation and dependency validation
- `webscraper info` - Package information display

#### Configuration Options
- General settings (user agent, timeouts, retries)
- Crawling settings (nested links, depth limits, delays)
- File extraction settings (supported types, size limits)
- LLM integration (multiple provider support)
- API integration (endpoint configuration)
- Logging configuration (levels, formats, file output)

#### Supported File Types
- PDF documents (text extraction with metadata)
- Excel spreadsheets (.xlsx, .xls) (cell data from all sheets)
- Word documents (.docx, .doc) (text and tables with metadata)
- Plain text files (auto-encoding detection)

#### LLM Providers Supported
- OpenAI GPT models
- Anthropic Claude models
- Custom/Generic providers with configurable endpoints

#### Ethical Features
- Robots.txt respect by default
- Rate limiting to prevent server overload
- User ownership verification for overrides
- Clear disclaimers for responsibility
- Brute force mode warnings

### Documentation
- Comprehensive README with usage examples
- Inline code documentation
- CLI help system
- Configuration examples
- Best practices guide

### Testing
- Unit tests for core functionality
- Integration tests for end-to-end workflows
- Mock-based testing for external dependencies
- Configuration validation tests

### Developer Features
- Type hints throughout codebase
- Modular architecture for easy extension
- Proper package structure with setuptools
- Development requirements (pytest, black, flake8, mypy)
- Git ignore file for clean repository

---

## Version History

- **v0.1.0** (2024-01-01): Initial release with full feature set
- **Future versions**: Will be documented here as they are released

---

## Migration Guide

### From Pre-1.0 Versions
This is the initial release, so no migration is needed.

### Configuration Changes
- No configuration changes in this release

---

## Notes

- This changelog follows semantic versioning
- All notable changes are documented
- Breaking changes are clearly marked
- Security issues are highlighted in the Security section
- Each version includes date of release
- Links to issues and pull requests will be added when available
