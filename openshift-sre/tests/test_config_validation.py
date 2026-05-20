from __future__ import annotations

import pytest

from openshift_sre_agent.config import Settings


def test_settings_reject_invalid_ollama_url() -> None:
    with pytest.raises(ValueError, match=r"ollama_base_url must be a valid http\(s\) URL"):
        Settings(
            ollama_base_url="not-a-url",
            local_model_name="gpt-oss:20b",
            cluster_scope="local-cluster",
        )


def test_settings_require_complete_database_configuration_when_enabled() -> None:
    with pytest.raises(ValueError, match="database_enabled requires database_url or a complete"):
        Settings(
            ollama_base_url="http://localhost:11434",
            local_model_name="gpt-oss:20b",
            cluster_scope="local-cluster",
            database_enabled=True,
            db_host="db.example.internal",
            db_name="openshift_sre",
            db_user="agent",
            db_password=None,
        )


def test_settings_normalize_urls_and_log_level() -> None:
    settings = Settings(
        ollama_base_url="http://localhost:11434/",
        local_model_name="gpt-oss:20b",
        cluster_scope="local-cluster",
        log_level="debug",
        llm_base_url="https://api.openai.com/v1/",
    )

    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.llm_base_url == "https://api.openai.com/v1"
    assert settings.log_level == "DEBUG"
