from __future__ import annotations

from unittest.mock import MagicMock, patch

from aws_sre_agent.config import Settings
from aws_sre_agent.model_client import ModelClient


def test_model_client_openai_chat_request() -> None:
    settings = Settings(
        ollama_base_url="http://localhost:11434",
        local_model_name="gpt-oss:20b",
        aws_region="us-east-1",
        llm_provider="openai",
        llm_model_name="gpt-4.1-mini",
        llm_base_url="https://api.openai.com/v1",
        llm_api_key="sk-test",
    )
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"message": {"content": "external answer"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }

    with patch("aws_sre_agent.model_client.httpx.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.post.return_value = response

        model_client = ModelClient(settings)
        result = model_client.chat([
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ])

    assert result == "external answer"
    client.post.assert_called_once()
    _, kwargs = client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
    assert kwargs["json"]["model"] == "gpt-4.1-mini"
    assert model_client.cumulative_tokens.total_tokens == 20


def test_model_client_gemini_chat_request() -> None:
    settings = Settings(
        ollama_base_url="http://localhost:11434",
        local_model_name="gpt-oss:20b",
        aws_region="us-east-1",
        llm_provider="gemini",
        llm_model_name="gemini-2.0-flash",
        llm_base_url="https://generativelanguage.googleapis.com/v1beta",
        llm_api_key="AIza-test",
    )
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}],
        "usageMetadata": {"promptTokenCount": 9, "candidatesTokenCount": 5, "totalTokenCount": 14},
    }

    with patch("aws_sre_agent.model_client.httpx.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.post.return_value = response

        model_client = ModelClient(settings)
        result = model_client.chat([
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ])

    assert result == "gemini answer"
    client.post.assert_called_once()
    _, kwargs = client.post.call_args
    assert kwargs["headers"]["x-goog-api-key"] == "AIza-test"
    assert kwargs.get("params") is None
    assert kwargs["json"]["contents"][0]["role"] == "user"
    assert model_client.cumulative_tokens.total_tokens == 14
