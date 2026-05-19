"""Provider-aware chat client adapters used by the agent reasoning loop."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

import httpx

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TokenUsage:
    """Normalized token accounting shared across all supported providers."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True)
class ChatStats:
    """Summary of the most recent provider call, including retries and token usage."""

    model: str = ""
    duration_ms: int = 0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    retries: int = 0


class CircuitOpen(Exception):
    """Raised when the circuit breaker is open and calls are blocked."""


class _CircuitBreaker:
    """Simple circuit breaker protecting repeated provider failures.

    The breaker opens after ``threshold`` consecutive failures and blocks new calls
    until ``reset_seconds`` elapses, at which point it returns to a half-open state.
    """

    __slots__ = ("threshold", "reset_seconds", "_failures", "_opened_at")

    def __init__(self, threshold: int = 3, reset_seconds: float = 30.0) -> None:
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.reset_seconds:
            self._half_open()
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = time.monotonic()

    def _half_open(self) -> None:
        self._failures = 0
        self._opened_at = None


class ModelClient:
    """Provider-aware chat client with retry, circuit breaker, fallback models, and token tracking.

    Supported providers currently include:

    - local Ollama
    - OpenAI and OpenAI-compatible APIs
    - Azure OpenAI deployments
    - Anthropic Claude via the Messages API
    - Google Gemini via the Generative Language API
    """

    _MAX_RETRIES = 3
    _BACKOFF_BASE = 1.5  # seconds

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider = settings.llm_provider
        self._breaker = _CircuitBreaker(threshold=3, reset_seconds=30.0)
        self._fallback_models: list[str] = [
            m.strip()
            for m in (settings.fallback_models or "").split(",")
            if m.strip() and m.strip() != settings.effective_model_name
        ]
        self._cumulative_tokens = TokenUsage()
        self._last_stats: ChatStats | None = None

    @property
    def cumulative_tokens(self) -> TokenUsage:
        return self._cumulative_tokens

    @property
    def last_stats(self) -> ChatStats | None:
        return self._last_stats

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.1) -> str:
        """Send *messages* to the configured provider and return the final text response."""

        effective_temp = self._settings.temperature_override if self._settings.temperature_override is not None else temperature
        models_to_try = [self._settings.effective_model_name] + self._fallback_models
        last_error: Exception | None = None
        for model in models_to_try:
            try:
                return self._chat_with_retry(model, messages, temperature=effective_temp)
            except (httpx.HTTPError, CircuitOpen) as exc:
                logger.warning("Model %s via %s unavailable: %s — trying next fallback", model, self._provider, exc)
                last_error = exc
        raise last_error or RuntimeError("All configured models failed")

    def ping(self) -> bool:
        """Return True if the configured provider is reachable or minimally configured."""
        if self._provider != "ollama":
            return self._has_external_provider_configuration()
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self._settings.ollama_base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _chat_with_retry(self, model: str, messages: list[dict[str, str]], *, temperature: float) -> str:
        if self._breaker.is_open:
            raise CircuitOpen(f"Circuit breaker open for {self._provider}")

        last_error: Exception | None = None
        retries_used = 0
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                start_ms = int(time.monotonic() * 1000)
                content, usage = self._perform_chat_request(model, messages, temperature=temperature)
                elapsed_ms = int(time.monotonic() * 1000) - start_ms
                self._breaker.record_success()
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens
                total_tokens = usage.total_tokens
                self._cumulative_tokens.prompt_tokens += prompt_tokens
                self._cumulative_tokens.completion_tokens += completion_tokens
                self._cumulative_tokens.total_tokens += total_tokens
                self._last_stats = ChatStats(
                    model=f"{self._provider}:{model}",
                    duration_ms=elapsed_ms,
                    tokens=TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                    ),
                    retries=retries_used,
                )
                logger.info(
                    "LLM call: provider=%s model=%s tokens=%d duration=%dms",
                    self._provider, model, total_tokens, elapsed_ms,
                    extra={"provider_name": self._provider, "model_name": model, "token_count": total_tokens, "duration_ms": elapsed_ms},
                )
                return content.strip()
            except httpx.HTTPError as exc:
                last_error = exc
                retries_used = attempt
                self._breaker.record_failure()
                if attempt < self._MAX_RETRIES:
                    wait = self._BACKOFF_BASE ** attempt
                    logger.info("LLM retry %d/%d for %s via %s after %.1fs", attempt, self._MAX_RETRIES, model, self._provider, wait)
                    time.sleep(wait)
        raise last_error or RuntimeError(f"Failed after {self._MAX_RETRIES} retries")

    def _perform_chat_request(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float,
    ) -> tuple[str, TokenUsage]:
        with httpx.Client(timeout=120.0) as client:
            if self._provider == "ollama":
                return self._chat_ollama(client, model, messages, temperature=temperature)
            if self._provider in {"openai", "openrouter"}:
                return self._chat_openai_compatible(client, model, messages, temperature=temperature)
            if self._provider == "azure-openai":
                return self._chat_azure_openai(client, model, messages, temperature=temperature)
            if self._provider == "anthropic":
                return self._chat_anthropic(client, model, messages, temperature=temperature)
            if self._provider == "gemini":
                return self._chat_gemini(client, model, messages, temperature=temperature)
        raise RuntimeError(f"Unsupported LLM provider: {self._provider}")

    def _chat_ollama(
        self,
        client: httpx.Client,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float,
    ) -> tuple[str, TokenUsage]:
        """Send a non-streaming chat request to the local Ollama API."""

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        response = client.post(f"{self._settings.ollama_base_url}/api/chat", json=payload)
        response.raise_for_status()
        body = response.json()
        return (
            body.get("message", {}).get("content", ""),
            TokenUsage(
                prompt_tokens=body.get("prompt_eval_count", 0) or 0,
                completion_tokens=body.get("eval_count", 0) or 0,
                total_tokens=(body.get("prompt_eval_count", 0) or 0) + (body.get("eval_count", 0) or 0),
            ),
        )

    def _chat_openai_compatible(
        self,
        client: httpx.Client,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float,
    ) -> tuple[str, TokenUsage]:
        """Send a Chat Completions request to an OpenAI-compatible endpoint."""

        headers = {"Authorization": f"Bearer {self._require_api_key()}"}
        if self._settings.llm_organization and self._provider == "openai":
            headers["OpenAI-Organization"] = self._settings.llm_organization
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        response = client.post(f"{self._settings.effective_llm_base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()
        message = ((body.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        usage = body.get("usage") or {}
        return (
            self._normalize_response_text(message),
            TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                completion_tokens=usage.get("completion_tokens", 0) or 0,
                total_tokens=usage.get("total_tokens", 0) or 0,
            ),
        )

    def _chat_azure_openai(
        self,
        client: httpx.Client,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float,
    ) -> tuple[str, TokenUsage]:
        """Send a deployment-scoped chat request to Azure OpenAI."""

        api_version = self._settings.llm_api_version or "2024-06-01"
        encoded_model = quote_plus(model)
        url = f"{self._settings.effective_llm_base_url}/openai/deployments/{encoded_model}/chat/completions?api-version={api_version}"
        response = client.post(
            url,
            headers={"api-key": self._require_api_key()},
            json={"messages": messages, "temperature": temperature},
        )
        response.raise_for_status()
        body = response.json()
        message = ((body.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        usage = body.get("usage") or {}
        return (
            self._normalize_response_text(message),
            TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                completion_tokens=usage.get("completion_tokens", 0) or 0,
                total_tokens=usage.get("total_tokens", 0) or 0,
            ),
        )

    def _chat_anthropic(
        self,
        client: httpx.Client,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float,
    ) -> tuple[str, TokenUsage]:
        """Send a Messages API request to Anthropic and normalize the response."""

        system_parts = [message.get("content", "") for message in messages if message.get("role") == "system"]
        anthropic_messages = [
            {
                "role": "assistant" if message.get("role") == "assistant" else "user",
                "content": [{"type": "text", "text": message.get("content", "")}],
            }
            for message in messages
            if message.get("role") in {"user", "assistant"}
        ]
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max(1024, min(4096, self._settings.context_window_tokens // 2)),
            "temperature": temperature,
            "messages": anthropic_messages,
        }
        if system_parts:
            payload["system"] = "\n\n".join(part for part in system_parts if part)
        response = client.post(
            f"{self._settings.effective_llm_base_url}/v1/messages",
            headers={
                "x-api-key": self._require_api_key(),
                "anthropic-version": self._settings.llm_api_version or "2023-06-01",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
        content = self._normalize_response_text(body.get("content") or [])
        usage = body.get("usage") or {}
        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0
        return (
            content,
            TokenUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
        )

    def _chat_gemini(
        self,
        client: httpx.Client,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float,
    ) -> tuple[str, TokenUsage]:
        """Send a ``generateContent`` request to the Gemini API."""

        system_text = "\n\n".join(message.get("content", "") for message in messages if message.get("role") == "system")
        contents = [
            {
                "role": "model" if message.get("role") == "assistant" else "user",
                "parts": [{"text": message.get("content", "")}],
            }
            for message in messages
            if message.get("role") in {"user", "assistant"}
        ]
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        response = client.post(
            f"{self._settings.effective_llm_base_url}/models/{model}:generateContent",
            headers={"x-goog-api-key": self._require_api_key()},
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
        candidates = body.get("candidates") or [{}]
        candidate_content = (candidates[0].get("content") or {}).get("parts") or []
        usage = body.get("usageMetadata") or {}
        prompt_tokens = usage.get("promptTokenCount", 0) or 0
        completion_tokens = usage.get("candidatesTokenCount", 0) or 0
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
        return (
            self._normalize_response_text(candidate_content),
            TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    def _require_api_key(self) -> str:
        """Return the configured API key or raise when the provider requires one."""

        api_key = self._settings.llm_api_key
        if not api_key:
            raise RuntimeError(f"LLM provider {self._provider} requires an API key")
        return api_key

    def _has_external_provider_configuration(self) -> bool:
        """Return ``True`` when the hosted provider has the minimum required settings."""

        if self._provider == "ollama":
            return True
        if not self._settings.effective_model_name:
            return False
        if not self._settings.effective_llm_base_url:
            return False
        return bool(self._settings.llm_api_key)

    @staticmethod
    def _normalize_response_text(value: Any) -> str:
        """Coerce provider-native content payloads into a plain text string."""

        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                    elif isinstance(item.get("content"), str):
                        parts.append(str(item["content"]))
            return "\n".join(part for part in parts if part)
        if isinstance(value, dict):
            if isinstance(value.get("text"), str):
                return value["text"]
            parts = value.get("parts")
            if isinstance(parts, list):
                return ModelClient._normalize_response_text(parts)
        return str(value or "")


OllamaClient = ModelClient
