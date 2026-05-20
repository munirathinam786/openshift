"""Tests for new cross-cutting features: logging, middleware, model client, confidence, caching."""
from __future__ import annotations

import json
import time

from openshift_sre_agent.agent import OpenShiftSreAgent
from openshift_sre_agent.config import get_llm_provider_defaults
from openshift_sre_agent.logging_config import JsonFormatter, get_request_id, set_request_id
from openshift_sre_agent.model_client import ModelClient, _CircuitBreaker
from openshift_sre_agent.tools import _ToolResultCache


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def test_json_formatter_produces_valid_json() -> None:
    import logging

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"
    assert "timestamp" in parsed


def test_request_id_thread_local() -> None:
    assert get_request_id() is None
    set_request_id("abc-123")
    assert get_request_id() == "abc-123"
    set_request_id(None)
    assert get_request_id() is None


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

def test_circuit_breaker_opens_after_threshold() -> None:
    cb = _CircuitBreaker(threshold=2, reset_seconds=0.1)
    assert not cb.is_open
    cb.record_failure()
    assert not cb.is_open
    cb.record_failure()
    assert cb.is_open
    # After reset_seconds it should half-open
    time.sleep(0.15)
    assert not cb.is_open


def test_circuit_breaker_resets_on_success() -> None:
    cb = _CircuitBreaker(threshold=2, reset_seconds=60)
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    assert not cb.is_open  # success reset the counter


# ---------------------------------------------------------------------------
# Tool-result cache
# ---------------------------------------------------------------------------

def test_tool_cache_hit_and_miss() -> None:
    cache = _ToolResultCache(ttl_seconds=1.0)
    assert cache.get("foo", {"a": 1}) is None
    cache.put("foo", {"a": 1}, {"result": 42})
    assert cache.get("foo", {"a": 1}) == {"result": 42}
    assert cache.get("foo", {"a": 2}) is None  # different args


def test_tool_cache_expires() -> None:
    cache = _ToolResultCache(ttl_seconds=0.05)
    cache.put("bar", {}, {"x": 1})
    assert cache.get("bar", {}) == {"x": 1}
    time.sleep(0.1)
    assert cache.get("bar", {}) is None


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def test_confidence_with_successful_tool_call() -> None:
    steps = [
        {"step": 1, "tool_call": {"name": "t"}, "tool_result": {"count": 1}},
        {"step": 2, "final_answer": "done"},
    ]
    score = OpenShiftSreAgent._compute_confidence(steps)
    assert 0.5 <= score <= 1.0


def test_confidence_all_errors() -> None:
    steps = [
        {"step": 1, "tool_call": {"name": "t"}, "tool_error": "boom"},
        {"step": 2, "tool_error": "again"},
    ]
    score = OpenShiftSreAgent._compute_confidence(steps)
    assert score == 0.0


def test_confidence_empty_steps() -> None:
    assert OpenShiftSreAgent._compute_confidence([]) == 0.0


# ---------------------------------------------------------------------------
# Conversation memory injection
# ---------------------------------------------------------------------------

def test_conversation_context_injected() -> None:
    from openshift_sre_agent.config import Settings

    settings = Settings(
        ollama_base_url="http://localhost:11434",
        local_model_name="test-model",
        cluster_scope="us-east-1",
        kube_context_name=None,
        openshift_api_url_field=None,
        openshift_token_field=None,
        openshift_namespace_field=None,
        tls_ca_bundle=None,
        verify_ssl=True,
        allow_mutating_actions=False,
        agent_max_steps=2,
    )
    agent = OpenShiftSreAgent(settings)
    agent.set_conversation_context([
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ])
    assert len(agent._conversation_context) == 2
    assert agent._conversation_context[0]["role"] == "user"


def test_gemini_defaults_use_supported_flash_model() -> None:
    defaults = get_llm_provider_defaults("gemini")

    assert defaults["default_model"] == "gemini-2.0-flash"
    assert "gemini-2.0-flash" in defaults["suggested_models"]


def test_gemini_requests_use_header_api_key_not_query_param() -> None:
    from openshift_sre_agent.config import Settings

    settings = Settings(
        ollama_base_url="http://localhost:11434",
        local_model_name="test-model",
        cluster_scope="us-east-1",
        llm_provider="gemini",
        llm_model_name="gemini-2.0-flash",
        llm_base_url="https://generativelanguage.googleapis.com/v1beta",
        llm_api_key="AIza-test",
        kube_context_name=None,
        openshift_api_url_field=None,
        openshift_token_field=None,
        openshift_namespace_field=None,
        tls_ca_bundle=None,
        verify_ssl=True,
        allow_mutating_actions=False,
        agent_max_steps=2,
    )
    model = ModelClient(settings)

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "candidates": [{"content": {"parts": [{"text": "Gemini response"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 12,
                    "candidatesTokenCount": 8,
                    "totalTokenCount": 20,
                },
            }

    class FakeClient:
        def __init__(self) -> None:
            self.called = None

        def post(self, url: str, *, headers=None, params=None, json=None):
            self.called = {
                "url": url,
                "headers": headers,
                "params": params,
                "json": json,
            }
            return FakeResponse()

    client = FakeClient()
    content, usage = model._chat_gemini(
        client,
        "gemini-2.0-flash",
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Summarize cost forecast."},
        ],
        temperature=0.1,
    )

    assert content == "Gemini response"
    assert usage.total_tokens == 20
    assert client.called is not None
    assert client.called["headers"] == {"x-goog-api-key": "AIza-test"}
    assert client.called["params"] is None
    assert client.called["url"].endswith("/models/gemini-2.0-flash:generateContent")
