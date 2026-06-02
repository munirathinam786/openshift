from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from openshift_sre_agent.architect_rag import ArchitectRagStore
from openshift_sre_agent.config import Settings


def _settings(ollama_base_url: str = "http://localhost:11434") -> Settings:
    return Settings(
        ollama_base_url=ollama_base_url,
        local_model_name="gpt-oss:20b",
        cluster_scope="local-cluster",
    )


def test_embed_texts_falls_back_to_container_host_alias_for_localhost() -> None:
    store = ArchitectRagStore(_settings("http://localhost:11434"))

    def fake_post(url, json, timeout):  # noqa: ANN001
        request = httpx.Request("POST", url)
        if url.startswith("http://localhost:11434"):
            raise httpx.ConnectError("connection refused", request=request)
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
        return response

    with patch.object(store, "_running_in_container", return_value=True), patch("openshift_sre_agent.architect_rag.httpx.post", side_effect=fake_post) as mock_post:
        embeddings = store._embed_texts(["hello world"])

    assert embeddings == [[0.1, 0.2, 0.3]]
    requested_urls = [call.args[0] for call in mock_post.call_args_list]
    assert requested_urls[0] == "http://localhost:11434/api/embed"
    assert requested_urls[1] == "http://host.containers.internal:11434/api/embed"


def test_embed_texts_uses_short_connect_timeout_and_reports_attempted_urls() -> None:
    store = ArchitectRagStore(_settings("http://host.containers.internal:11434"))
    request = httpx.Request("POST", "http://host.containers.internal:11434/api/embed")

    def fake_post(url, json, timeout):  # noqa: ANN001
        assert timeout.connect == 5.0
        assert timeout.read == 120.0
        raise httpx.ConnectTimeout("timed out", request=request)

    with patch.object(store, "_running_in_container", return_value=True), patch("openshift_sre_agent.architect_rag.httpx.post", side_effect=fake_post):
        try:
            store._embed_texts(["timeout path"])
        except RuntimeError as error:
            message = str(error)
        else:  # pragma: no cover
            raise AssertionError("Expected Ollama connectivity failure")

    assert "Tried http://host.containers.internal:11434, http://host.docker.internal:11434" in message
    assert "timed out" in message