"""
Basic tests for the Advanced Web Scraper.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from webscraper import WebScraper, create_default_config, validate_config
from webscraper.file_extractor import FileExtractor
from webscraper.robots_checker import RobotsChecker
from webscraper.utils import get_file_extension, is_same_domain, is_valid_url


class TestUtils:
    """Test utility functions."""

    def test_is_same_domain(self) -> None:
        """Test domain comparison."""
        assert is_same_domain("https://example.com", "https://example.com/page")
        assert is_same_domain("https://www.example.com", "https://example.com")
        assert not is_same_domain("https://example.com", "https://google.com")
        assert not is_same_domain("https://sub.example.com", "https://example.com")

    def test_get_file_extension(self) -> None:
        """Test file extension extraction."""
        assert get_file_extension("https://example.com/file.pdf") == ".pdf"
        assert get_file_extension("https://example.com/file.xlsx") == ".xlsx"
        assert get_file_extension("https://example.com/file") == ""
        assert get_file_extension("https://example.com/file.pdf?param=1") == ".pdf"

    def test_is_valid_url(self) -> None:
        """Test URL validation."""
        assert is_valid_url("https://example.com")
        assert is_valid_url("http://example.com")
        assert not is_valid_url("ftp://example.com")
        assert not is_valid_url("invalid-url")
        assert not is_valid_url("")


class TestConfiguration:
    """Test configuration management."""

    def test_create_default_config(self) -> None:
        """Test default config creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.json")
            assert create_default_config(config_path)
            assert Path(config_path).exists()

            with open(config_path) as f:
                config = json.load(f)

            required_sections = [
                "general",
                "crawling",
                "file_extraction",
                "llm",
                "api",
                "logging",
            ]
            for section in required_sections:
                assert section in config

    def test_validate_config_valid(self) -> None:
        """Test config validation with valid config."""
        valid_config = {
            "general": {
                "user_agent": "Test Bot",
                "timeout": 30,
                "max_retries": 3,
                "respect_robots_txt": True,
                "brute_force": False,
                "allow_user_override": True,
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
                "supported_extensions": [".pdf", ".xlsx"],
                "max_file_size_mb": 50,
                "extract_content": True,
            },
            "llm": {"provider": "openai", "api_key": "", "model": "gpt-3.5-turbo"},
            "api": {"enabled": False, "endpoint": "", "method": "POST"},
            "logging": {"level": "INFO", "format": "%(message)s"},
        }

        errors = validate_config(valid_config)
        assert len(errors) == 0

    def test_validate_config_invalid(self) -> None:
        """Test config validation with invalid config."""
        invalid_config = {"general": {"timeout": -1, "max_retries": "not a number"}}

        errors = validate_config(invalid_config)
        assert len(errors) > 0


class TestRobotsChecker:
    """Test robots.txt checking functionality."""

    def test_get_robots_url(self) -> None:
        """Test robots.txt URL generation."""
        config = {
            "general": {"user_agent": "TestBot", "timeout": 30},
            "llm": {"api_key": ""},
        }
        checker = RobotsChecker(config)

        robots_url = checker._get_robots_url("https://example.com/page")
        assert robots_url == "https://example.com/robots.txt"

        robots_url = checker._get_robots_url("https://sub.example.com/deep/path")
        assert robots_url == "https://sub.example.com/robots.txt"

    @patch("requests.get")
    def test_fetch_robots_txt_success(self, mock_get: MagicMock) -> None:
        """Test successful robots.txt fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin/"
        mock_get.return_value = mock_response

        config = {
            "general": {"user_agent": "TestBot", "timeout": 30},
            "llm": {"api_key": ""},
        }
        checker = RobotsChecker(config)

        content = checker._fetch_robots_txt("https://example.com/robots.txt")
        assert content == "User-agent: *\nDisallow: /admin/"

    @patch("requests.get")
    def test_fetch_robots_txt_not_found(self, mock_get: MagicMock) -> None:
        """Test robots.txt not found (404)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        config = {
            "general": {"user_agent": "TestBot", "timeout": 30},
            "llm": {"api_key": ""},
        }
        checker = RobotsChecker(config)

        content = checker._fetch_robots_txt("https://example.com/robots.txt")
        assert content is None


class TestFileExtractor:
    """Test file content extraction."""

    def test_extract_from_text(self) -> None:
        """Test text file extraction."""
        config = {"file_extraction": {"supported_extensions": [".txt"]}}
        extractor = FileExtractor(config)

        text_content = b"Hello, world!\nThis is a test."
        result = extractor._extract_from_text(text_content)
        assert result == "Hello, world!\nThis is a test."

    def test_extract_from_text_encoding(self) -> None:
        """Test text extraction with different encodings."""
        config = {"file_extraction": {"supported_extensions": [".txt"]}}
        extractor = FileExtractor(config)

        utf8_content = "Hello, 世界!".encode("utf-8")
        result = extractor._extract_from_text(utf8_content)
        assert "Hello, 世界!" in result

    def test_unsupported_file_type(self) -> None:
        """Test handling of unsupported file types."""
        config = {"file_extraction": {"supported_extensions": [".pdf"]}}
        extractor = FileExtractor(config)

        result = extractor.extract_content(b"dummy content", ".xyz")
        assert "Unsupported file type" in result


class TestWebScraper:
    """Test main WebScraper functionality."""

    def test_load_config_file_not_found(self) -> None:
        """Test handling of missing config file."""
        with pytest.raises(FileNotFoundError):
            WebScraper("nonexistent_config.json")

    def test_load_config_invalid_json(self) -> None:
        """Test handling of invalid JSON config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            f.flush()
            file_name = f.name

            try:
                with pytest.raises(ValueError):
                    WebScraper(file_name)
            finally:
                os.unlink(file_name)

    @patch("webscraper.core.WebScraper._make_request")
    def test_scrape_url_request_failure(self, mock_request: MagicMock) -> None:
        """Test handling of request failures."""
        mock_request.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            create_default_config(config_path)

            scraper = WebScraper(config_path)
            result = scraper.scrape_url("https://example.com", brute_force=True)

            assert not result["success"]
            assert "request_failed" in result["reason"]

            scraper.close()


class TestIntegration:
    """Integration tests."""

    @patch("requests.Session.get")
    @patch("webscraper.robots_checker.requests.get")
    def test_end_to_end_scraping(
        self, mock_robots_get: MagicMock, mock_session_get: MagicMock
    ) -> None:
        """Test end-to-end scraping process."""
        mock_robots_response = MagicMock()
        mock_robots_response.status_code = 404
        mock_robots_get.return_value = mock_robots_response

        mock_page_response = MagicMock()
        mock_page_response.status_code = 200
        mock_page_response.headers = {"content-type": "text/html"}
        mock_page_response.content = b"""
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome to Test Page</h1>
                <p>This is a test page for scraping.</p>
            </body>
        </html>
        """
        mock_page_response.raise_for_status = MagicMock()
        mock_session_get.return_value = mock_page_response

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            create_default_config(config_path)

            scraper = WebScraper(config_path)
            result = scraper.scrape_url("https://example.com")

            assert result["success"]
            assert "data" in result
            assert "title" in result["data"]
            assert "text_content" in result["data"]
            assert result["data"]["title"] == "Test Page"

            scraper.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
