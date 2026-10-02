import json
import warnings

import pytest

from respectscraper import Config, ConfigError
from respectscraper.cli import EXIT_DISALLOWED, EXIT_OK, EXIT_USAGE, main


def legacy(**general) -> dict:
    return {
        "general": {"user_agent": "Old/1.0", "timeout": 10, "brute_force": False, **general},
        "crawling": {"nested_links": True, "max_depth": 2, "delay_between_requests": 0.5},
        "file_extraction": {"download_files": True, "supported_extensions": [".pdf", ".doc"]},
        "llm": {"provider": "openai", "model": "x", "api_key": ""},
        "api": {"enabled": False, "endpoint": "", "method": "POST", "headers": {}},
        "logging": {"level": "INFO"},
    }


def test_legacy_config_files_still_load() -> None:
    with pytest.warns(DeprecationWarning):
        config = Config.from_dict(legacy())

    assert (config.user_agent, config.max_depth, config.delay_seconds) == ("Old/1.0", 2, 0.5)
    assert config.file_types == (".pdf",)  # .doc was never supported


def test_removed_bypasses_are_rejected_with_guidance() -> None:
    with pytest.raises(ConfigError, match="owner_override_hosts"):
        Config.from_dict(legacy(brute_force=True))
    data = legacy()
    data["llm"]["api_key"] = "sk-test"
    with pytest.raises(ConfigError, match="RESPECTSCRAPER_LLM_API_KEY"):
        Config.from_dict(data)


def test_invalid_settings_are_rejected() -> None:
    with pytest.raises(ConfigError, match="max_pages"):
        Config(max_pages=0)
    with pytest.raises(ConfigError, match="unsupported file types"):
        Config(file_types=(".exe",))
    with pytest.raises(ConfigError, match="unknown settings"):
        Config.from_dict({"brute_force": True})


def test_cli_check_reports_the_rule_and_exit_code(site, capsys) -> None:
    site.add("/robots.txt", "User-agent: *\nDisallow: /private/\n", Content_Type="text/plain")

    assert main(["check", site.base + "/private/x"]) == EXIT_DISALLOWED
    out = capsys.readouterr().out
    assert "NOT ALLOWED" in out and "Disallow: /private/" in out and "line 2" in out
    assert main(["check", site.base + "/public", "--json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["reason"] == "no_matching_rule"


def test_cli_scrape_writes_a_report(site, tmp_path) -> None:
    site.add("/robots.txt", "", Content_Type="text/plain")
    site.html("/", "<p>hi</p>")
    config = tmp_path / "c.json"
    config.write_text(json.dumps({"delay_seconds": 0}))
    out = tmp_path / "report.json"

    assert main(["scrape", site.base + "/", "-c", str(config), "-o", str(out), "-q"]) == EXIT_OK
    assert json.loads(out.read_text())["pages"][0]["text"] == "hi"


@pytest.mark.parametrize("flag", ["--brute-force", "--user-owns-site", "--ssl-bypass"])
def test_removed_cli_flags_explain_the_replacement(flag, capsys) -> None:
    assert main(["scrape", "https://example.com", flag]) == EXIT_USAGE
    assert "removed in 0.2.0" in capsys.readouterr().err


def test_webscraper_import_still_works_with_a_warning(site, tmp_path) -> None:
    site.add("/robots.txt", "", Content_Type="text/plain")
    site.html("/", "<p>legacy</p>")
    config = tmp_path / "config.json"
    data = legacy()
    data["crawling"]["delay_between_requests"] = 0
    config.write_text(json.dumps(data))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import importlib

        import webscraper

        importlib.reload(webscraper)
        scraper = webscraper.WebScraper(str(config))
    assert any("deprecated" in str(w.message) for w in caught)

    result = scraper.scrape_url(site.base + "/")
    assert result["success"] and result["data"]["text_content"] == "legacy"
    with pytest.raises(ValueError, match="owner_override_hosts"):
        scraper.scrape_url(site.base + "/", brute_force=True)
