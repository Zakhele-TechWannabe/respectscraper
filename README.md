# RespectScraper

An ethical Python web scraping library that prioritizes robots.txt compliance, features AI-powered interpretation of ambiguous rules, and provides comprehensive content extraction capabilities.

## 🚀 Features

- **Robots.txt Compliance**: Automatically checks and respects robots.txt files with intelligent parsing
- **AI-Powered Interpretation**: Uses configurable LLM providers (OpenAI, Anthropic, Custom) to interpret ambiguous robots.txt files
- **Nested Link Crawling**: Crawls nested links with configurable depth limits and domain restrictions
- **Comprehensive File Extraction**: Downloads and extracts content from PDFs, Excel files, Word documents, and text files
- **Respectful Rate Limiting**: Built-in rate limiting to prevent overwhelming target servers
- **API Integration**: Configurable API endpoints to seamlessly send scraped data
- **Flexible Configuration**: JSON-based configuration for all settings and behaviors
- **Command Line Interface**: Intuitive CLI for common scraping tasks
- **Ethical Override Options**: Support for user-owned sites and brute force mode with clear disclaimers

## 📦 Installation

### From PyPI (when published)
```bash
pip install respectscraper
```

### From Source
```bash
git clone https://github.com/Zakhele-TechWannabe/respectscraper.git
cd respectscraper
pip install -e .
```

### Dependencies
The package requires Python 3.8+ and the following libraries:
- requests
- beautifulsoup4
- lxml
- PyPDF2
- openpyxl
- python-docx
- openai (optional, for LLM features)
- anthropic (optional, for LLM features)
- ratelimit
- aiohttp
- aiofiles

## 🎯 Quick Start

### 1. Create Configuration
```bash
respectscraper config --create
```

### 2. Basic Scraping
```python
from webscraper import WebScraper

scraper = WebScraper('config.json')
result = scraper.scrape_url('https://example.com')
print(result)
scraper.close()
```

### 3. Command Line Usage
```bash
# Basic scraping
respectscraper scrape https://example.com

# With nested links and file extraction
respectscraper scrape https://example.com --nested --download

# Ignore robots.txt (use responsibly)
respectscraper scrape https://example.com --brute-force

# Save results to file
respectscraper scrape https://example.com --output results.json --pretty
```

## ⚙️ Configuration

The scraper uses a JSON configuration file. Create a default one with:

```bash
respectscraper config --create
```

### Key Configuration Sections

#### General Settings
```json
{
  "general": {
    "user_agent": "AdvancedWebScraper/1.0 (Respectful Bot)",
    "timeout": 30,
    "max_retries": 3,
    "respect_robots_txt": true,
    "brute_force": false,
    "allow_user_override": true
  }
}
```

#### LLM Integration (for robots.txt interpretation)
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "api_key": "your-api-key-here",
    "max_tokens": 500,
    "temperature": 0.1
  }
}
```

#### API Integration
```json
{
  "api": {
    "enabled": true,
    "endpoint": "https://your-api-endpoint.com/data",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer YOUR_API_KEY"
    }
  }
}
```

## 📖 Usage Examples

### Basic Website Scraping
```python
from webscraper import WebScraper

scraper = WebScraper('config.json')
result = scraper.scrape_url('https://example.com')

if result['success']:
    data = result['data']
    print(f"Title: {data['title']}")
    print(f"Content: {data['text_content'][:500]}...")
else:
    print(f"Failed: {result['reason']}")

scraper.close()
```

### Nested Link Crawling
```python
result = scraper.scrape_url(
    'https://example.com',
    nested=True  # Enable nested crawling
)

if result['success'] and 'nested_pages' in result['data']:
    for page in result['data']['nested_pages']:
        print(f"Found page: {page['url']}")
        if page['success']:
            print(f"  Title: {page['data']['title']}")
```

### File Extraction
```python
result = scraper.scrape_url(
    'https://example.com/documents',
    download=True  # Enable file downloading
)

if result['success'] and 'extracted_files' in result['data']:
    for file_data in result['data']['extracted_files']:
        print(f"Extracted: {file_data['url']}")
        print(f"Type: {file_data['data']['file_type']}")
        print(f"Content: {file_data['data']['content'][:200]}...")
```

### Handling Robots.txt Restrictions
```python
# Respect robots.txt (default)
result = scraper.scrape_url('https://example.com')

# User claims site ownership (with disclaimer)
result = scraper.scrape_url('https://example.com', user_owns_site=True)

# Brute force mode (ignore robots.txt - use responsibly)
result = scraper.scrape_url('https://example.com', brute_force=True)
```

### Quick Scraping Function
```python
from webscraper import quick_scrape

result = quick_scrape(
    url='https://example.com',
    nested=True,
    download=False
)
```

## 🤖 LLM Integration

The scraper can use AI to interpret ambiguous robots.txt files. Supported providers:

### OpenAI
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "api_key": "your-openai-api-key"
  }
}
```

### Anthropic Claude
```json
{
  "llm": {
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "api_key": "your-anthropic-api-key"
  }
}
```

### Custom Provider
```json
{
  "llm": {
    "provider": "custom",
    "model": "your-model",
    "api_key": "your-api-key",
    "base_url": "https://your-llm-endpoint.com"
  }
}
```

## 🔧 CLI Commands

### Scraping
```bash
# Basic scraping
respectscraper scrape https://example.com

# Advanced options
respectscraper scrape https://example.com \
  --nested \
  --download \
  --config custom_config.json \
  --output results.json \
  --pretty

# Ignore robots.txt
respectscraper scrape https://example.com --brute-force

# User owns site
respectscraper scrape https://example.com --user-owns-site

# Bypass SSL certificate verification (for problematic sites)
respectscraper scrape https://example.com --ssl-bypass
```

### Configuration
```bash
# Create default config
respectscraper config --create

# Create config at custom path
respectscraper config --create --path my_config.json

# Validate existing config
respectscraper config --validate --path config.json
```

### Validation and Info
```bash
# Validate installation
respectscraper validate

# Show package info
respectscraper info
```

## 🔒 Handling SSL Certificate Issues

Some websites have SSL certificate problems that prevent scraping. RespectScraper provides several ways to handle this:

### Quick Solution (CLI)
```bash
# Bypass SSL verification for a single scrape
respectscraper scrape https://problematic-site.com --ssl-bypass
```

### Configuration Solution
Edit your `config.json`:
```json
{
  "general": {
    "verify_ssl": false,
    "allow_ssl_bypass": true
  }
}
```

### Python API Solution
```python
scraper = WebScraper('config.json')
# Temporarily disable SSL verification
scraper.session.verify = False
result = scraper.scrape_url('https://problematic-site.com')
```

### ⚠️ Security Warning
Disabling SSL verification reduces security. Only use this for:
- Trusted websites with known certificate issues
- Internal/development servers
- When you understand the security implications

## 📁 File Extraction Support

The scraper can extract content from various file types:

- **PDF**: Text extraction from all pages with metadata
- **Excel**: Cell data from all sheets with sheet names
- **Word**: Text and tables with document metadata
- **Text**: Auto-encoding detection for text files

## 🛡️ Ethical Usage

This tool is designed for **responsible web scraping**:

### ✅ Good Practices
- Always respect robots.txt files
- Use appropriate delays between requests
- Don't overload servers with too many concurrent requests
- Only scrape public, non-copyrighted content
- Respect terms of service
- Use the `user_owns_site` flag only for sites you actually own

### ❌ Don't Use For
- Scraping content behind login walls without permission
- Violating website terms of service
- Overloading servers with aggressive scraping
- Collecting personal or private data
- Copyright infringement

### Robots.txt Override Options

The scraper provides override options but use them responsibly:

1. **User Owns Site**: Use `user_owns_site=True` only if you actually own the website
2. **Brute Force**: Use `brute_force=True` only with explicit permission or for testing
3. **Both options show disclaimers about responsible usage**

## 🔍 API Integration

Send scraped data automatically to your API:

```python
# Configure in config.json
{
  "api": {
    "enabled": true,
    "endpoint": "https://your-api.com/scraped-data",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer YOUR_TOKEN"
    }
  }
}
```

The scraper will automatically send structured data:
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "url": "https://example.com",
    "title": "Example Title",
    "content": "Scraped content...",
    "word_count": 500,
    "nested_pages": [...],
    "extracted_files": [...]
  }
}
```

## 🧪 Testing Installation

```bash
# Validate installation
respectscraper validate

# Test with a simple page
respectscraper scrape https://httpbin.org/html --pretty
```

## 📚 Advanced Usage

### Custom User Agent
```python
# Modify config.json
{
  "general": {
    "user_agent": "MyRespectfulBot/1.0 (+https://mysite.com/bot-info)"
  }
}
```

### Rate Limiting Configuration
```python
{
  "crawling": {
    "delay_between_requests": 2.0,  # 2 seconds between requests
    "max_concurrent_requests": 3    # Max 3 concurrent requests
  }
}
```

### File Size Limits
```python
{
  "file_extraction": {
    "max_file_size_mb": 100,  # Don't download files larger than 100MB
    "supported_extensions": [".pdf", ".xlsx", ".docx", ".txt"]
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **"Configuration file not found"**
   ```bash
   respectscraper config --create
   ```

2. **"LLM API key not configured"**
   - Edit `config.json` and add your API key in the `llm` section

3. **"Robots.txt blocks scraping"**
   - Check the robots.txt file manually
   - Use `--user-owns-site` if you own the site
   - Use `--brute-force` only if you have permission

4. **"SSL Certificate verification failed"**
   - Try with SSL bypass: `respectscraper scrape URL --ssl-bypass`
   - Or edit config.json: `"allow_ssl_bypass": true, "verify_ssl": false`
   - ⚠️ **Warning**: Only bypass SSL for trusted sites

5. **"Rate limited"**
   - Increase `delay_between_requests` in config
   - Reduce `max_concurrent_requests`

6. **"File extraction failed"**
   - Check if the file type is supported
   - Verify file isn't corrupted
   - Check file size limits

### Debug Mode
```python
# Enable debug logging
{
  "logging": {
    "level": "DEBUG",
    "file": "debug.log"
  }
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

**Why Apache 2.0?** It provides better patent protection, trademark protection, and clearer legal terms for enterprise use while maintaining the same freedoms as MIT. See [LICENSE_COMPARISON.md](LICENSE_COMPARISON.md) for details.

## 🔗 Links

- [Documentation](https://github.com/Zakhele-TechWannabe/respectscraper/wiki)
- [Issue Tracker](https://github.com/Zakhele-TechWannabe/respectscraper/issues)
- [Changelog](CHANGELOG.md)

## ⚖️ Disclaimer

This tool is provided for educational and legitimate scraping purposes. Users are responsible for ensuring their usage complies with applicable laws, regulations, and website terms of service. The developers are not responsible for any misuse of this software.

Always scrape responsibly and ethically!