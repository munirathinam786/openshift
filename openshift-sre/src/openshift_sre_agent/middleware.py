"""FastAPI middleware: request tracing, rate limiting, auth, security headers, and input guard."""
from __future__ import annotations

import logging
import re
import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import set_request_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request-ID tracing middleware
# ---------------------------------------------------------------------------

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Inject and propagate ``X-Request-Id`` on every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        set_request_id(request_id)
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            status_code = getattr(response, "status_code", 500)
            logger.info(
                "%s %s %s %dms",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                extra={"duration_ms": duration_ms, "status_code": status_code},
            )
            set_request_id(None)
        if response is None:
            raise RuntimeError("Request pipeline completed without producing a response.")
        response.headers["X-Request-Id"] = request_id
        return response


# ---------------------------------------------------------------------------
# Simple token-bucket rate limiter
# ---------------------------------------------------------------------------

class _TokenBucket:
    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP token-bucket rate limiter with bounded memory.

    Defaults: 60 requests/minute capacity, refills at 1 req/s.
    Only applied to non-static paths. Evicts coldest IPs when bucket count exceeds *max_buckets*.
    """

    def __init__(self, app: FastAPI, *, capacity: int = 60, refill_rate: float = 1.0, max_buckets: int = 10_000) -> None:
        super().__init__(app)
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._max_buckets = max_buckets
        self._buckets: dict[str, _TokenBucket] = defaultdict(lambda: _TokenBucket(capacity, refill_rate))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path.startswith("/guide") or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        # Evict coldest buckets when memory grows beyond bound
        if len(self._buckets) >= self._max_buckets:
            oldest_ip = min(self._buckets, key=lambda ip: self._buckets[ip].last_refill)
            del self._buckets[oldest_ip]
        bucket = self._buckets[client_ip]
        if not bucket.consume():
            logger.warning("Rate limit exceeded for %s on %s", client_ip, path)
            return JSONResponse({"detail": "Rate limit exceeded. Try again shortly."}, status_code=429)
        return await call_next(request)


# ---------------------------------------------------------------------------
# Input sanitization constants
# ---------------------------------------------------------------------------

MAX_PROMPT_LENGTH = 4000
"""Hard cap on prompt length to prevent abuse."""


# ---------------------------------------------------------------------------
# CORS helper
# ---------------------------------------------------------------------------

def add_cors(app: FastAPI, *, allow_origins: list[str] | None = None) -> None:
    """Attach CORSMiddleware with a sensible allow-list."""
    origins = allow_origins or [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )


# ---------------------------------------------------------------------------
# API key / bearer token authentication middleware — v0.3.0
# ---------------------------------------------------------------------------

_PUBLIC_PATHS = frozenset({"/health", "/healthz", "/readyz", "/docs", "/openapi.json", "/redoc", "/metrics"})


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce bearer-token authentication on non-public endpoints."""

    def __init__(self, app: FastAPI, *, api_key: str) -> None:
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in _PUBLIC_PATHS or path.startswith("/guide") or path.startswith("/docs") or request.method == "OPTIONS":
            return await call_next(request)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        else:
            token = request.query_params.get("api_key", "")
        if not token or token != self._api_key:
            logger.warning("Auth rejected for %s %s from %s", request.method, path, request.client.host if request.client else "unknown")
            return JSONResponse({"detail": "Invalid or missing API key."}, status_code=401)
        return await call_next(request)


# ---------------------------------------------------------------------------
# HSTS / security headers — v0.3.0
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add HSTS and common security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# ---------------------------------------------------------------------------
# Prompt injection detector — v0.3.0
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|rules?|prompts?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\b", re.IGNORECASE),
    re.compile(r"system:\s*override", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"disregard\s+(your|the|all)\s+(instructions?|constraints?|rules?)", re.IGNORECASE),
    re.compile(r"enable\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"bypass\s+(all\s+)?filters?", re.IGNORECASE),
    re.compile(r"\bDAN\b.*\bjailbreak\b", re.IGNORECASE),
    re.compile(r"<\|im_start\|>|<\|im_end\|>", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> str | None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None
