from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import io
import ipaddress
import json
from pathlib import Path
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

try:
    from pgvector import Vector as PgVector
except ImportError:  # pragma: no cover
    PgVector = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None
    dict_row = None

from .config import Settings

MAX_TRAINING_FILE_BYTES = 10 * 1024 * 1024
MAX_URL_DOWNLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 180
SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".yaml", ".yml", ".csv", ".log", ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".htm", ".xml", ".svg", ".drawio"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = (data or "").strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)


@dataclass(slots=True)
class RetrievedKnowledgeItem:
    title: str
    source_uri: str
    source_type: str
    excerpt: str
    score: float
    metadata: dict[str, Any]


class ArchitectRagStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.architect_rag_enabled and self.settings.architect_vector_database_url)

    def status(self) -> dict[str, Any]:
        payload = {
            "enabled": self.enabled,
            "vector_backend": "pgvector",
            "embedding_model": self.settings.architect_embedding_model,
            "database_url_configured": bool(self.settings.architect_vector_database_url),
            "top_k": self.settings.architect_rag_top_k,
            "stats": {"document_count": 0, "chunk_count": 0, "last_trained_at": None, "source_types": []},
            "healthy": False,
            "message": "OpenShift architect knowledge training is disabled.",
        }
        if not self.enabled:
            return payload
        try:
            self.ensure_schema()
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT source_uri) AS document_count,
                           COUNT(*) AS chunk_count,
                           MAX(created_at) AS last_trained_at,
                           COALESCE(json_agg(DISTINCT source_type) FILTER (WHERE source_type IS NOT NULL), '[]'::json) AS source_types
                    FROM architect_rag_chunks
                    """
                )
                row = cursor.fetchone() or {}
            payload["healthy"] = True
            payload["message"] = "OpenShift architect knowledge training is ready."
            payload["stats"] = {
                "document_count": int(row.get("document_count") or 0),
                "chunk_count": int(row.get("chunk_count") or 0),
                "last_trained_at": row.get("last_trained_at").isoformat() if row.get("last_trained_at") else None,
                "source_types": list(row.get("source_types") or []),
            }
        except Exception as error:  # noqa: BLE001
            payload["message"] = f"OpenShift architect knowledge store is configured but unavailable: {error}"
        return payload

    def require_available(self) -> None:
        if not self.enabled:
            raise RuntimeError("Architect knowledge training is disabled. Set ARCHITECT_RAG_ENABLED=true and configure the pgvector database connection.")

    def ensure_schema(self) -> None:
        if not self.enabled:
            return
        with self._connect(autocommit=True) as connection, connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS architect_rag_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    title TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    excerpt TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    content_hash TEXT NOT NULL,
                    embedding vector NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (source_uri, chunk_index)
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS architect_rag_chunks_source_uri_idx ON architect_rag_chunks (source_uri)")
            cursor.execute("CREATE INDEX IF NOT EXISTS architect_rag_chunks_created_at_idx ON architect_rag_chunks (created_at DESC)")

    def list_sources(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        self.ensure_schema()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT ON (source_uri)
                    source_uri,
                    source_type,
                    title,
                    metadata,
                    created_at AS last_trained_at,
                    COUNT(*) OVER (PARTITION BY source_uri) AS chunk_count
                FROM architect_rag_chunks
                ORDER BY source_uri ASC, created_at DESC, chunk_index DESC
                """
            )
            rows = cursor.fetchall() or []
        return [
            {
                "source_uri": str(row.get("source_uri") or "unknown"),
                "source_type": str(row.get("source_type") or "knowledge"),
                "title": str(row.get("title") or "Untitled knowledge"),
                "chunk_count": int(row.get("chunk_count") or 0),
                "last_trained_at": row.get("last_trained_at").isoformat() if row.get("last_trained_at") else None,
                "metadata": dict(row.get("metadata") or {}),
            }
            for row in rows
        ]

    def train_url(self, url: str) -> dict[str, Any]:
        self.require_available()
        normalized_url = self._validate_training_url(url)
        response = httpx.get(normalized_url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
        content = response.content[:MAX_URL_DOWNLOAD_BYTES]
        title = Path(urlparse(normalized_url).path or "knowledge-source").name or urlparse(normalized_url).netloc or "knowledge-source"
        text = self._extract_text(content, source_name=title, content_type=response.headers.get("content-type"), source_type="url")
        return self._store_document(source_type="url", source_uri=normalized_url, title=title, text=text, metadata={"content_type": response.headers.get("content-type") or "", "status_code": response.status_code})

    def train_file(self, *, filename: str, content: bytes, content_type: str | None = None) -> dict[str, Any]:
        self.require_available()
        safe_name = Path(filename or "uploaded-document.txt").name
        if len(content) > MAX_TRAINING_FILE_BYTES:
            raise ValueError(f"{safe_name} is larger than the 10 MB training limit.")
        text = self._extract_text(content, source_name=safe_name, content_type=content_type, source_type="file")
        return self._store_document(source_type="file", source_uri=f"upload://{safe_name}", title=safe_name, text=text, metadata={"content_type": content_type or "application/octet-stream", "filename": safe_name})

    def delete_sources(self, *, source_uris: list[str] | None = None, clear_all: bool = False) -> dict[str, Any]:
        self.require_available()
        self.ensure_schema()
        indexed_sources = self.list_sources()
        source_lookup = {str(item.get("source_uri") or ""): item for item in indexed_sources}
        normalized_source_uris = [str(item).strip() for item in (source_uris or []) if str(item).strip()]
        if clear_all:
            selected_sources = indexed_sources
        else:
            if not normalized_source_uris:
                raise ValueError("Select at least one trained knowledge source to clear, or set clear_all=true.")
            selected_sources = [source_lookup[source_uri] for source_uri in normalized_source_uris if source_uri in source_lookup]
            if not selected_sources:
                raise ValueError("None of the requested trained knowledge sources exist in the architect pgvector store.")
        deleted_source_uris = [str(item.get("source_uri") or "") for item in selected_sources if str(item.get("source_uri") or "")]
        deleted_chunk_count = sum(int(item.get("chunk_count") or 0) for item in selected_sources)
        with self._connect(autocommit=True) as connection, connection.cursor() as cursor:
            if clear_all:
                cursor.execute("DELETE FROM architect_rag_chunks")
            else:
                cursor.execute("DELETE FROM architect_rag_chunks WHERE source_uri = ANY(%s)", (deleted_source_uris,))
        return {"cleared_all": bool(clear_all), "deleted_document_count": len(selected_sources), "deleted_chunk_count": deleted_chunk_count, "deleted_source_uris": deleted_source_uris}

    def retrieve(self, *, query: str, top_k: int | None = None) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "used": False, "vector_backend": "pgvector", "embedding_model": self.settings.architect_embedding_model, "items": [], "prompt_guidance": ""}
        self.ensure_schema()
        prompt = (query or "").strip()
        if not prompt:
            return {"enabled": True, "used": False, "vector_backend": "pgvector", "embedding_model": self.settings.architect_embedding_model, "items": [], "prompt_guidance": ""}
        embedding = self._embed_texts([prompt])[0]
        limit = max(1, min(int(top_k or self.settings.architect_rag_top_k), 8))
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT title, source_uri, source_type, excerpt, metadata, 1 - (embedding <=> %s::vector) AS score
                FROM architect_rag_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (self._vector_value(embedding), self._vector_value(embedding), limit),
            )
            rows = cursor.fetchall() or []
        items = [RetrievedKnowledgeItem(title=str(row.get("title") or "Untitled knowledge"), source_uri=str(row.get("source_uri") or "unknown"), source_type=str(row.get("source_type") or "knowledge"), excerpt=str(row.get("excerpt") or "").strip(), score=float(row.get("score") or 0.0), metadata=dict(row.get("metadata") or {})) for row in rows]
        return {
            "enabled": True,
            "used": bool(items),
            "vector_backend": "pgvector",
            "embedding_model": self.settings.architect_embedding_model,
            "items": [{"title": item.title, "source_uri": item.source_uri, "source_type": item.source_type, "excerpt": item.excerpt, "score": round(item.score, 4), "metadata": item.metadata} for item in items],
            "prompt_guidance": self._build_prompt_guidance(items),
        }

    def _build_prompt_guidance(self, items: list[RetrievedKnowledgeItem]) -> str:
        if not items:
            return ""
        lines = ["Retrieved OpenShift architect knowledge base context:"]
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. {item.title} [{item.source_type}] ({item.source_uri}) score={item.score:.3f}: {item.excerpt}")
        lines.append("Use this retrieved knowledge to ground OpenShift topology decisions, component boundaries, and HLD/LLD implementation detail when it is relevant to the request.")
        return "\n".join(lines)

    def _store_document(self, *, source_type: str, source_uri: str, title: str, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        normalized_text = self._normalize_text(text)
        if len(normalized_text) < 80:
            raise ValueError("The supplied training source did not contain enough readable text to index.")
        chunks = self._chunk_text(normalized_text)
        if not chunks:
            raise ValueError("The supplied training source did not contain any indexable text chunks.")
        embeddings = self._embed_texts(chunks)
        content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        with self._connect(autocommit=True) as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM architect_rag_chunks WHERE source_uri = %s", (source_uri,))
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False), start=1):
                cursor.execute(
                    """
                    INSERT INTO architect_rag_chunks (source_type, source_uri, title, chunk_index, content, excerpt, metadata, content_hash, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::vector)
                    """,
                    (source_type, source_uri, title, index, chunk, chunk[:320], json.dumps(metadata, sort_keys=True), content_hash, self._vector_value(embedding)),
                )
        return {"source_type": source_type, "source_uri": source_uri, "title": title, "chunk_count": len(chunks), "content_hash": content_hash}

    def _connect(self, *, autocommit: bool = False):
        if psycopg is None or dict_row is None:
            raise RuntimeError("Architect knowledge training requires the optional psycopg dependency to be installed.")
        return psycopg.connect(self.settings.architect_vector_database_url, autocommit=autocommit, row_factory=dict_row)

    def _vector_value(self, embedding: list[float]) -> Any:
        return "[" + ",".join(f"{float(value):.12g}" for value in embedding) + "]"

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        base_url = self.settings.ollama_base_url.rstrip("/")
        payload = {"model": self.settings.architect_embedding_model, "input": texts}
        try:
            response = httpx.post(f"{base_url}/api/embed", json=payload, timeout=60.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            message = self._ollama_error_message(error.response)
            if error.response.status_code == 404:
                if self._is_missing_embedding_model_error(message):
                    raise RuntimeError(self._missing_embedding_model_message()) from error
                return self._embed_texts_legacy(texts)
            raise RuntimeError(message or f"Ollama embeddings request failed with status {error.response.status_code}.") from error
        except httpx.HTTPError as error:
            raise RuntimeError(f"Unable to reach Ollama for embeddings at {base_url}: {error}") from error
        data = response.json()
        embeddings = data.get("embeddings") or []
        if not embeddings and isinstance(data.get("embedding"), list):
            embeddings = [data["embedding"]]
        if len(embeddings) != len(texts):
            raise RuntimeError(f"Ollama returned {len(embeddings)} embedding vector(s) for {len(texts)} text chunk(s).")
        return [[float(value) for value in embedding] for embedding in embeddings]

    def _embed_texts_legacy(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        base_url = self.settings.ollama_base_url.rstrip("/")
        for text in texts:
            try:
                response = httpx.post(f"{base_url}/api/embeddings", json={"model": self.settings.architect_embedding_model, "prompt": text}, timeout=60.0)
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                message = self._ollama_error_message(error.response)
                if error.response.status_code == 404:
                    if self._is_missing_embedding_model_error(message):
                        raise RuntimeError(self._missing_embedding_model_message()) from error
                    raise RuntimeError(self._unsupported_embedding_api_message()) from error
                raise RuntimeError(message or f"Ollama legacy embeddings request failed with status {error.response.status_code}.") from error
            except httpx.HTTPError as error:
                raise RuntimeError(f"Unable to reach Ollama for embeddings at {base_url}: {error}") from error
            data = response.json()
            embedding = data.get("embedding")
            if not isinstance(embedding, list):
                raise RuntimeError("Ollama legacy embeddings endpoint did not return an embedding vector.")
            embeddings.append([float(value) for value in embedding])
        return embeddings

    def _ollama_error_message(self, response: httpx.Response | None) -> str:
        if response is None:
            return ""
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            payload = None
        if isinstance(payload, dict):
            message = payload.get("error") or payload.get("message")
            if message:
                return str(message).strip()
        try:
            return (response.text or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    def _is_missing_embedding_model_error(self, message: str) -> bool:
        normalized = (message or "").strip().lower()
        model_name = self.settings.architect_embedding_model.strip().lower()
        return bool(normalized and model_name and model_name in normalized and "not found" in normalized and "pull" in normalized)

    def _missing_embedding_model_message(self) -> str:
        return (
            f'Architect embedding model "{self.settings.architect_embedding_model}" is not available in Ollama at '
            f'{self.settings.ollama_base_url.rstrip("/")}. Pull it first on the host with '
            f'`ollama pull {self.settings.architect_embedding_model}` and retry the knowledge training or preview request.'
        )

    def _unsupported_embedding_api_message(self) -> str:
        return (
            f"The configured Ollama server at {self.settings.ollama_base_url.rstrip('/')} did not expose a supported "
            "embeddings API. Ensure the URL points to a running Ollama instance and supports either /api/embed or /api/embeddings."
        )

    def _extract_text(self, content: bytes, *, source_name: str, content_type: str | None, source_type: str) -> str:
        suffix = Path(source_name).suffix.lower()
        guessed_type = (content_type or "").split(";", 1)[0].strip().lower()
        if suffix == ".pdf" or guessed_type == "application/pdf":
            if PdfReader is None:
                raise ValueError("PDF training requires the optional pypdf dependency to be installed.")
            reader = PdfReader(io.BytesIO(content))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        text = content.decode("utf-8", errors="ignore")
        if suffix in {".html", ".htm", ".xml", ".svg", ".drawio"} or guessed_type in {"text/html", "application/xml", "image/svg+xml"}:
            parser = _TextExtractor()
            parser.feed(text)
            return parser.text()
        if suffix in SUPPORTED_TEXT_EXTENSIONS or guessed_type.startswith("text/") or guessed_type in {"application/json", "application/yaml", "application/x-yaml"}:
            return text
        if source_type == "url":
            parser = _TextExtractor()
            parser.feed(text)
            extracted = parser.text()
            return extracted or text
        return text

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "")).strip()

    def _chunk_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        start = 0
        text = text.strip()
        while start < len(text):
            end = min(len(text), start + DEFAULT_CHUNK_SIZE)
            if end < len(text):
                boundary = text.rfind(" ", start + 400, end)
                if boundary > start:
                    end = boundary
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(end - DEFAULT_CHUNK_OVERLAP, start + 1)
        return chunks

    def _validate_training_url(self, raw_url: str) -> str:
        candidate = (raw_url or "").strip()
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http:// and https:// training links are supported.")
        host = (parsed.hostname or "").strip().lower()
        if not host:
            raise ValueError("A valid training URL host is required.")
        if host in {"localhost", "127.0.0.1", "0.0.0.0", "host.containers.internal"} or host.endswith(".local"):
            raise ValueError("Local-only URLs are blocked for architect link training. Upload the file instead.")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and (address.is_private or address.is_loopback or address.is_link_local):
            raise ValueError("Private-address URLs are blocked for architect link training. Upload the file instead.")
        return candidate
