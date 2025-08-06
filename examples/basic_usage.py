"""
Basic usage examples for RespectScraper.
"""

import json
from pathlib import Path

from webscraper import WebScraper, create_default_config, quick_scrape


def example_basic_scraping() -> None:
    """Example: Basic website scraping."""
    print("=== Basic Website Scraping ===")

    config_path = "config.json"
    if not Path(config_path).exists():
        create_default_config(config_path)
        print(f"Created default configuration: {config_path}")

    scraper = WebScraper(config_path)

    result = scraper.scrape_url("https://httpbin.org/html")

    print(f"Success: {result['success']}")
    if result["success"]:
        data = result["data"]
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"Word count: {data.get('word_count', 0)}")
        print(f"Content preview: {data.get('text_content', '')[:200]}...")
    else:
        print(f"Error: {result.get('reason', 'Unknown error')}")

    scraper.close()
    print()


def example_nested_scraping() -> None:
    """Example: Nested link crawling."""
    print("=== Nested Link Crawling ===")

    scraper = WebScraper("config.json")

    result = scraper.scrape_url("https://httpbin.org/links/3", nested=True)

    print(f"Success: {result['success']}")
    if result["success"] and "nested_pages" in result["data"]:
        nested_pages = result["data"]["nested_pages"]
        print(f"Found {len(nested_pages)} nested pages")

        for i, page in enumerate(nested_pages[:3]):
            if page["success"]:
                print(f"  Page {i+1}: {page['url']}")
                print(f"    Title: {page['data'].get('title', 'N/A')}")
                print(f"    Words: {page['data'].get('word_count', 0)}")

    scraper.close()
    print()


def example_file_extraction() -> None:
    """Example: File downloading and content extraction."""
    print("=== File Extraction ===")

    scraper = WebScraper("config.json")

    print("Note: This example shows the structure for file extraction.")
    print("Replace with a real URL containing downloadable files.")

    mock_result = {
        "success": True,
        "url": "https://example.com/document.pdf",
        "data": {
            "file_type": ".pdf",
            "content": "This is the extracted text content from the PDF...",
            "size_bytes": 1024000,
        },
    }

    print("Example file extraction result:")
    print(json.dumps(mock_result, indent=2))

    scraper.close()
    print()


def example_robots_txt_checking() -> None:
    """Example: Robots.txt compliance checking."""
    print("=== Robots.txt Checking ===")

    scraper = WebScraper("config.json")

    result = scraper.scrape_url("https://www.google.com")

    print(f"Google scraping result: {result['success']}")
    print(f"Reason: {result.get('reason', 'N/A')}")

    result_brute = scraper.scrape_url("https://www.google.com", brute_force=True)

    print(f"Brute force result: {result_brute['success']}")

    scraper.close()
    print()


def example_api_integration() -> None:
    """Example: API integration configuration."""
    print("=== API Integration Setup ===")

    print("To enable API integration, modify your config.json:")

    api_config = {
        "api": {
            "enabled": True,
            "endpoint": "https://your-api-endpoint.com/scraped-data",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer YOUR_API_KEY",
            },
            "timeout": 30,
        }
    }

    print(json.dumps(api_config, indent=2))
    print("\nWhen enabled, scraped data will be automatically sent to your API.")
    print()


def example_llm_integration() -> None:
    """Example: LLM integration for robots.txt interpretation."""
    print("=== LLM Integration Setup ===")

    print("To enable LLM integration for robots.txt interpretation:")

    llm_configs = {
        "OpenAI": {
            "llm": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "your-openai-api-key",
                "max_tokens": 500,
                "temperature": 0.1,
            }
        },
        "Anthropic Claude": {
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "api_key": "your-anthropic-api-key",
                "max_tokens": 500,
                "temperature": 0.1,
            }
        },
        "Custom Provider": {
            "llm": {
                "provider": "custom",
                "model": "your-model",
                "api_key": "your-api-key",
                "base_url": "https://your-llm-endpoint.com",
                "max_tokens": 500,
                "temperature": 0.1,
            }
        },
    }

    for provider, config in llm_configs.items():
        print(f"\n{provider} configuration: ")
        print(json.dumps(config, indent=2))

    print()


def example_quick_scrape() -> None:
    """Example: Using the quick scrape function."""
    print("=== Quick Scrape Function ===")

    result = quick_scrape(url="https://httpbin.org/html", nested=False, download=False)

    print(f"Quick scrape success: {result['success']}")
    if result["success"]:
        print(f"Title: {result['data'].get('title', 'N/A')}")
        print(f"Word count: {result['data'].get('word_count', 0)}")

    print()


def example_error_handling() -> None:
    """Example: Proper error handling."""
    print("=== Error Handling ===")

    try:
        scraper = WebScraper("config.json")

        result = scraper.scrape_url("https://this-domain-does-not-exist-12345.com")

        if not result["success"]:
            print(f"Scraping failed: {result['error']}")
            print(f"Reason: {result['reason']}")

        scraper.close()

    except FileNotFoundError:
        print("Configuration file not found. Create one with:")
        print("from webscraper import create_default_config")
        print("create_default_config('config.json')")

    except Exception as e:
        print(f"Unexpected error: {e}")

    print()


def main() -> None:
    """Run all examples."""
    print("RespectScraper - Usage Examples")
    print("=" * 50)
    print()

    try:
        example_basic_scraping()
        example_nested_scraping()
        example_file_extraction()
        example_robots_txt_checking()
        example_api_integration()
        example_llm_integration()
        example_quick_scrape()
        example_error_handling()

        print("All examples completed!")
        print("\nNext steps:")
        print("1. Edit config.json to configure LLM API keys")
        print("2. Edit config.json to configure API endpoints")
        print("3. Try scraping your target websites")
        print("4. Use the CLI: respectscraper scrape https://example.com")

    except Exception as e:
        print(f"Error running examples: {e}")


if __name__ == "__main__":
    main()
