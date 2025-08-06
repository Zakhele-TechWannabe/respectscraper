import logging
from datetime import datetime
from typing import Any, Dict, List

import requests


class APIClient:
    """Handles sending scraped data to external APIs."""

    def __init__(self, config: Dict):
        self.config = config["api"]
        self.logger = logging.getLogger(__name__)

        if not self.config["enabled"]:
            self.logger.info("API client disabled")
            return

        if not self.config["endpoint"]:
            self.logger.error("API endpoint not configured")
            return

        self.session = requests.Session()
        self.session.headers.update(self.config.get("headers", {}))

        self.logger.info(
            f"API client initialized for endpoint: {self.config['endpoint']}"
        )

    def send_data(self, data: Dict[str, Any]) -> bool:
        """
        Send scraped data to the configured API endpoint.

        Args:
            data: The scraped data to send

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config["enabled"]:
            self.logger.debug("API client disabled, not sending data")
            return True

        try:
            payload = self._prepare_payload(data)

            method = self.config.get("method", "POST").upper()

            if method == "POST":
                response = self.session.post(
                    self.config["endpoint"],
                    json=payload,
                    timeout=self.config.get("timeout", 30),
                )
            elif method == "PUT":
                response = self.session.put(
                    self.config["endpoint"],
                    json=payload,
                    timeout=self.config.get("timeout", 30),
                )
            elif method == "PATCH":
                response = self.session.patch(
                    self.config["endpoint"],
                    json=payload,
                    timeout=self.config.get("timeout", 30),
                )
            else:
                self.logger.error(f"Unsupported HTTP method: {method}")
                return False

            response.raise_for_status()

            self.logger.info(
                f"Successfully sent data to API. Status: {response.status_code}"
            )

            try:
                response_data = response.json()
                if "id" in response_data or "message" in response_data:
                    self.logger.info(f"API response: {response_data}")
            except (ValueError, KeyError):
                pass

            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending data to API: {e}")
            return False

    def _prepare_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare the payload for the API request.

        Args:
            data: Raw scraped data

        Returns:
            Dict formatted for API consumption
        """
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "scraper_version": "1.0.0",
            "data": data,
        }

        if data.get("success"):
            scraped_content = data.get("data", {})

            api_data = {
                "url": data["url"],
                "success": data["success"],
                "scraped_at": payload["timestamp"],
                "content": {},
            }

            if "title" in scraped_content:
                api_data["content"]["title"] = scraped_content["title"]

            if "meta_description" in scraped_content:
                api_data["content"]["description"] = scraped_content["meta_description"]

            if "text_content" in scraped_content:
                api_data["content"]["text"] = scraped_content["text_content"]
                api_data["content"]["word_count"] = scraped_content.get("word_count", 0)

            if "depth" in scraped_content:
                api_data["crawl_depth"] = scraped_content["depth"]

            if "nested_pages" in scraped_content and scraped_content["nested_pages"]:
                api_data["nested_pages"] = []
                for nested_page in scraped_content["nested_pages"]:
                    if nested_page.get("success") and nested_page.get("data"):
                        nested_data = {
                            "url": nested_page["url"],
                            "title": nested_page["data"].get("title", ""),
                            "text": nested_page["data"].get("text_content", ""),
                            "word_count": nested_page["data"].get("word_count", 0),
                            "depth": nested_page["data"].get("depth", 0),
                        }
                        api_data["nested_pages"].append(nested_data)

            if (
                "extracted_files" in scraped_content
                and scraped_content["extracted_files"]
            ):
                api_data["extracted_files"] = []
                for file_data in scraped_content["extracted_files"]:
                    if file_data.get("success") and file_data.get("data"):
                        file_info = {
                            "url": file_data["url"],
                            "file_type": file_data["data"].get("file_type", ""),
                            "content": file_data["data"].get("content", ""),
                            "size_bytes": file_data["data"].get("size_bytes", 0),
                        }
                        api_data["extracted_files"].append(file_info)

            payload["data"] = api_data
        else:
            payload["data"] = {
                "url": data["url"],
                "success": False,
                "error": data.get("error", "unknown"),
                "reason": data.get("reason", "No reason provided"),
                "scraped_at": payload["timestamp"],
            }

        return payload

    def test_connection(self) -> bool:
        """
        Test the API connection with a simple ping.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        if not self.config["enabled"]:
            self.logger.info("API client disabled")
            return True

        try:
            test_payload = {
                "test": True,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connection test from webscraper",
            }

            response = self.session.post(
                self.config["endpoint"],
                json=test_payload,
                timeout=self.config.get("timeout", 30),
            )

            if 200 <= response.status_code < 300:
                self.logger.info(
                    f"API connection test successful. Status: {response.status_code}"
                )
                return True
            else:
                self.logger.warning(
                    f"API connection test returned status: {response.status_code}"
                )
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API connection test failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during API connection test: {e}")
            return False

    def send_batch_data(self, data_list: List[Dict[str, Any]]) -> bool:
        """
        Send multiple scraped data entries in a single batch request.

        Args:
            data_list: List of scraped data dictionaries

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config["enabled"]:
            self.logger.debug("API client disabled, not sending batch data")
            return True

        if not data_list:
            self.logger.warning("No data to send in batch")
            return True

        try:
            batch_payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "scraper_version": "1.0.0",
                "batch_size": len(data_list),
                "data": [self._prepare_payload(data)["data"] for data in data_list],
            }

            method = self.config.get("method", "POST").upper()

            if method == "POST":
                response = self.session.post(
                    self.config["endpoint"],
                    json=batch_payload,
                    timeout=self.config.get("timeout", 60),
                )
            else:
                self.logger.error(
                    f"Batch operations only support POST method, got: {method}"
                )
                return False

            response.raise_for_status()

            self.logger.info(
                f"""Successfully sent batch data to API.
                Items: {len(data_list)}, Status: {response.status_code}"""
            )
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Batch API request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending batch data to API: {e}")
            return False
