"""Configuration with safe defaults.

A config can be built in code, from a dict, or from a JSON file. Files written for
0.1.x (sections "general", "crawling", "file_extraction", "llm", "api") still load;
settings that bypassed robots.txt for every site were removed and are rejected with
an explanation.
"""

from __future__ import annotations

import json
import os
import warnings
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from ._version import __version__

DEFAULT_USER_AGENT = (
    f"RespectScraper/{__version__} (+https://github.com/Zakhele-TechWannabe/respectscraper)"
)
SUPPORTED_FILE_TYPES = (".pdf", ".docx", ".xlsx", ".txt", ".csv")


class ConfigError(ValueError):
    """The configuration is invalid."""


@dataclass
class LLMConfig:
    """Optional model used only to explain decisions in plain language."""

    provider: str = "openai"  # openai, anthropic, or an OpenAI-compatible base_url
    model: str = ""
    api_key_env: str = "RESPECTSCRAPER_LLM_API_KEY"
    base_url: str = ""
    timeout: float = 30

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


@dataclass
class APIConfig:
    """Optional endpoint that receives each crawl report as JSON."""

    enabled: bool = False
    endpoint: str = ""
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30


@dataclass
class Config:
    user_agent: str = DEFAULT_USER_AGENT
    timeout: float = 20
    max_retries: int = 2
    delay_seconds: float = 1.0
    max_depth: int = 0
    max_pages: int = 50
    same_site_only: bool = True
    download_files: bool = False
    file_types: tuple[str, ...] = SUPPORTED_FILE_TYPES
    max_file_mb: float = 25
    verify_ssl: bool = True
    owner_override_hosts: tuple[str, ...] = ()
    llm: LLMConfig = field(default_factory=LLMConfig)
    api: APIConfig = field(default_factory=APIConfig)

    def __post_init__(self) -> None:
        self.file_types = tuple(ext.lower() for ext in self.file_types)
        self.owner_override_hosts = tuple(h.lower() for h in self.owner_override_hosts)
        errors = []
        if self.timeout <= 0:
            errors.append("timeout must be greater than 0")
        if self.max_retries < 0:
            errors.append("max_retries must be 0 or more")
        if self.delay_seconds < 0:
            errors.append("delay_seconds must be 0 or more")
        if self.max_depth < 0:
            errors.append("max_depth must be 0 or more")
        if self.max_pages < 1:
            errors.append("max_pages must be at least 1")
        if self.max_file_mb <= 0:
            errors.append("max_file_mb must be greater than 0")
        unsupported = [ext for ext in self.file_types if ext not in SUPPORTED_FILE_TYPES]
        if unsupported:
            errors.append(
                f"unsupported file types {unsupported}; supported: {list(SUPPORTED_FILE_TYPES)}"
            )
        if self.api.enabled and not self.api.endpoint.startswith(("https://", "http://localhost")):
            errors.append("api.endpoint must be an https:// URL when the API is enabled")
        if self.api.method.upper() not in ("POST", "PUT", "PATCH"):
            errors.append("api.method must be POST, PUT, or PATCH")
        if errors:
            raise ConfigError("; ".join(errors))

    @property
    def max_file_bytes(self) -> int:
        return int(self.max_file_mb * 1024 * 1024)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        if any(key in data for key in ("general", "crawling", "file_extraction")):
            data = _from_legacy(data)
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ConfigError(f"unknown settings: {unknown}")
        values = dict(data)
        if isinstance(values.get("llm"), dict):
            values["llm"] = LLMConfig(**values["llm"])
        if isinstance(values.get("api"), dict):
            values["api"] = APIConfig(**values["api"])
        for key in ("file_types", "owner_override_hosts"):
            if key in values:
                values[key] = tuple(values[key])
        return cls(**values)

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> Config:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigError(f"configuration file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["file_types"] = list(self.file_types)
        data["owner_override_hosts"] = list(self.owner_override_hosts)
        return data


def _from_legacy(data: dict[str, Any]) -> dict[str, Any]:
    """Map a 0.1.x config file onto the current settings."""
    general = data.get("general", {})
    crawling = data.get("crawling", {})
    files = data.get("file_extraction", {})
    llm = data.get("llm", {})
    if general.get("brute_force") or general.get("allow_ssl_bypass"):
        raise ConfigError(
            "brute_force and allow_ssl_bypass were removed in 0.2.0. To crawl a site you "
            "own regardless of its robots.txt, list it in owner_override_hosts."
        )
    if llm.get("api_key"):
        raise ConfigError(
            "llm.api_key no longer belongs in the config file. Set the "
            "RESPECTSCRAPER_LLM_API_KEY environment variable instead."
        )
    warnings.warn(
        "This is a 0.1.x configuration file; run `respectscraper config --create` for "
        "the current format.",
        DeprecationWarning,
        stacklevel=3,
    )
    nested = crawling.get("nested_links", False)
    result: dict[str, Any] = {
        "user_agent": general.get("user_agent", DEFAULT_USER_AGENT),
        "timeout": general.get("timeout", 20),
        "max_retries": general.get("max_retries", 2),
        "verify_ssl": general.get("verify_ssl", True),
        "delay_seconds": crawling.get("delay_between_requests", 1.0),
        "max_depth": crawling.get("max_depth", 3) if nested else 0,
        "same_site_only": crawling.get("same_domain_only", True),
        "download_files": files.get("download_files", False),
        "file_types": [
            ext
            for ext in files.get("supported_extensions", SUPPORTED_FILE_TYPES)
            if ext in SUPPORTED_FILE_TYPES
        ],
        "max_file_mb": files.get("max_file_size_mb", 25),
    }
    if llm:
        result["llm"] = {k: v for k, v in llm.items() if k in ("provider", "model", "base_url")}
    if "api" in data:
        result["api"] = {
            k: v
            for k, v in data["api"].items()
            if k in ("enabled", "endpoint", "method", "headers", "timeout")
        }
    return result
