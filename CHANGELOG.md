# Changelog

All notable changes to the RespectScraper project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet

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
