import json
import logging
from typing import Any, Dict, Optional

import requests


class LLMClient:
    """Configurable LLM client supporting multiple providers."""

    def __init__(self, config: Dict):
        self.config = config["llm"]
        self.logger = logging.getLogger(__name__)
        self.provider = self.config["provider"].lower()
        self.api_key = self.config["api_key"]

        if not self.api_key:
            self.logger.warning(
                "No LLM API key provided. LLM features will be disabled."
            )

        self._setup_provider()

    def _setup_provider(self) -> None:
        """Setup provider-specific configurations."""
        if self.provider == "openai":
            self.base_url = self.config.get("base_url", "https://api.openai.com/v1")
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        elif self.provider == "anthropic":
            self.base_url = self.config.get("base_url", "https://api.anthropic.com/v1")
            self.headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }
        else:
            self.base_url = self.config.get("base_url", "")
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

    def query(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Send a query to the LLM and return the response.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Dict containing the parsed JSON response, or None if failed
        """
        if not self.api_key:
            self.logger.error("No API key configured for LLM")
            return None

        try:
            if self.provider == "openai":
                return self._query_openai(prompt)
            elif self.provider == "anthropic":
                return self._query_anthropic(prompt)
            else:
                return self._query_generic(prompt)

        except Exception as e:
            self.logger.error(f"LLM query failed: {e}")
            return None

    def _query_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Query OpenAI API."""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.config["model"],
            "messages": [
                {
                    "role": "system",
                    "content": """
                    You are a helpful assistant that analyzes robots.txt files.
                    Always respond with valid JSON.""",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            try:
                return json.loads(content)  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                return self._extract_json_from_text(content)

        except requests.RequestException as e:
            self.logger.error(f"OpenAI API request failed: {e}")
            return None

    def _query_anthropic(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Query Anthropic Claude API."""
        url = f"{self.base_url}/messages"

        payload = {
            "model": self.config["model"],
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
            "messages": [
                {
                    "role": "user",
                    "content": f"""
                    You are a helpful assistant that analyzes robots.txt files.
                    Always respond with valid JSON.
                    {prompt}""",
                }
            ],
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            content = data["content"][0]["text"]

            try:
                return json.loads(content)  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                return self._extract_json_from_text(content)

        except requests.RequestException as e:
            self.logger.error(f"Anthropic API request failed: {e}")
            return None

    def _query_generic(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Query a generic/custom LLM API."""
        if not self.base_url:
            self.logger.error("Base URL required for generic provider")
            return None

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.config["model"],
            "messages": [
                {
                    "role": "system",
                    "content": """
                    You are a helpful assistant that analyzes robots.txt files.
                    Always respond with valid JSON.
                    """,
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()

            data = response.json()

            content = None
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
            elif "content" in data:
                content = data["content"]
            elif "text" in data:
                content = data["text"]

            if content:
                try:
                    return json.loads(content)  # type: ignore[no-any-return]
                except json.JSONDecodeError:
                    return self._extract_json_from_text(content)

            self.logger.error("Failed to extract content from LLM response")
            return None

        except requests.RequestException as e:
            self.logger.error(f"Generic LLM API request failed: {e}")
            return None

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to extract JSON from text that may contain:
        1. Markdown or other formatting."""
        import re

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                pass

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                pass

        self.logger.warning("Could not parse JSON, using fallback")
        return {
            "allowed": False,
            "reason": "Could not parse LLM response",
            "confidence": 0.0,
        }

    def test_connection(self) -> bool:
        """Test the connection to the LLM provider."""
        if not self.api_key:
            return False

        test_prompt = "Please respond with a JSON object containing 'status': 'ok'"

        try:
            response = self.query(test_prompt)
            return response is not None and isinstance(response, dict)
        except Exception as e:
            self.logger.error(f"LLM connection test failed: {e}")
            return False
