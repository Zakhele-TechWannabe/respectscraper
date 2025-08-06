"""
RespectScraper

An ethical web scraping library with robots.txt compliance,
AI-powered interpretation, nested link crawling, and comprehensive file extraction.

Example usage:
    from webscraper import WebScraper

    scraper = WebScraper('config.json')
    result = scraper.scrape_url('https://example.com', nested=True, download=True)
    print(result)
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = """
Ethical web scraper with robots.txt compliance.
AI-powered interpretation, and comprehensive content extraction
"""

from typing import Dict, List, TypedDict

from .api_client import APIClient
from .core import WebScraper
from .file_extractor import FileExtractor
from .llm_client import LLMClient
from .robots_checker import RobotsChecker
from .utils import (
    clean_text,
    extract_domain,
    format_file_size,
    get_content_type,
    get_file_extension,
    is_same_domain,
    is_valid_url,
    normalize_url,
    sanitize_filename,
    validate_config,
)

__all__ = [
    "WebScraper",
    "RobotsChecker",
    "FileExtractor",
    "LLMClient",
    "APIClient",
    "is_same_domain",
    "get_file_extension",
    "is_valid_url",
    "normalize_url",
    "sanitize_filename",
    "get_content_type",
    "extract_domain",
    "clean_text",
    "format_file_size",
    "validate_config",
]


class ValidationResults(TypedDict):
    valid: bool
    missing_packages: List[str]
    version_info: Dict[str, str]
    recommendations: List[str]


def create_default_config(output_path: str = "config.json") -> bool:
    """
    Create a default configuration file.

    Args:
        output_path: Path where to save the config file

    Returns:
        True if successful, False otherwise
    """
    import json

    default_config = {
        "general": {
            "user_agent": "RespectScraper/1.0 (Ethical Bot)",
            "timeout": 30,
            "max_retries": 3,
            "respect_robots_txt": True,
            "brute_force": False,
            "allow_user_override": True,
            "verify_ssl": True,
            "allow_ssl_bypass": False,
        },
        "crawling": {
            "nested_links": False,
            "max_depth": 3,
            "same_domain_only": True,
            "delay_between_requests": 1.0,
            "max_concurrent_requests": 5,
        },
        "file_extraction": {
            "download_files": False,
            "supported_extensions": [".pdf", ".xlsx", ".xls", ".docx", ".doc", ".txt"],
            "max_file_size_mb": 50,
            "extract_content": True,
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "api_key": "",
            "base_url": "",
            "max_tokens": 500,
            "temperature": 0.1,
        },
        "api": {
            "enabled": False,
            "endpoint": "https://your-api-endpoint.com/data",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer YOUR_API_KEY",
            },
            "timeout": 30,
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "webscraper.log",
        },
    }

    try:
        with open(output_path, "w") as f:
            json.dump(default_config, f, indent=2)
        return True
    except Exception:
        return False


def quick_scrape(
    url: str,
    config_path: str = "config.json",
    nested: bool = False,
    download: bool = False,
    brute_force: bool = False,
) -> dict:
    """
    Quick scraping function for simple use cases.

    Args:
        url: URL to scrape
        config_path: Path to configuration file
        nested: Enable nested link crawling
        download: Enable file downloading
        brute_force: Ignore robots.txt

    Returns:
        Scraping results dictionary
    """
    try:
        scraper = WebScraper(config_path)
        result = scraper.scrape_url(
            url=url, nested=nested, download=download, brute_force=brute_force
        )
        scraper.close()
        return result
    except Exception as e:
        return {
            "url": url,
            "success": False,
            "error": "quick_scrape_failed",
            "reason": str(e),
            "data": None,
        }


def validate_installation() -> ValidationResults:
    """
    Validate that all dependencies are properly installed.

    Returns:
        ValidationResults: Dictionary with validation results
    """

    results: ValidationResults = {
        "valid": True,
        "missing_packages": [],
        "version_info": {},
        "recommendations": [],
    }

    required_packages = {
        "requests": "requests",
        "beautifulsoup4": "bs4",
        "lxml": "lxml",
        "PyPDF2": "PyPDF2",
        "openpyxl": "openpyxl",
        "python-docx": "docx",
        "openai": "openai",
        "anthropic": "anthropic",
        "ratelimit": "ratelimit",
    }

    for package_name, import_name in required_packages.items():
        try:
            module = __import__(import_name)
            if hasattr(module, "__version__"):
                results["version_info"][package_name] = module.__version__
            else:
                results["version_info"][package_name] = "unknown"
        except ImportError:
            results["valid"] = False
            results["missing_packages"].append(package_name)

    if results["missing_packages"]:
        results["recommendations"].append(
            f"Missing packages: pip install {' '.join(results['missing_packages'])}"
        )

    if not results["missing_packages"]:
        results["recommendations"].append("All dependencies are properly installed!")

    return results


def get_version() -> str:
    """Get package version."""
    return __version__


def get_info() -> dict:
    """Get package information."""
    return {
        "name": "respectscraper",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": __description__,
    }
