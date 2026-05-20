"""Integration tests for OpenShift SRE toolkit initialization."""
from __future__ import annotations

import pytest

from openshift_sre_agent.config import Settings
from openshift_sre_agent.tools import OpenShiftSreToolkit


def _settings() -> Settings:
    return Settings(
        ollama_base_url="http://localhost:11434",
        local_model_name="test-model",
        cluster_scope="local-cluster",
        kube_context_name=None,
        openshift_api_url_field=None,
        openshift_token_field=None,
        openshift_namespace_field="openshift-monitoring",
        tls_ca_bundle=None,
        verify_ssl=True,
        allow_mutating_actions=False,
        agent_max_steps=8,
    )


def test_toolkit_initialization() -> None:
    """Toolkit should initialize without error even when no cluster is reachable."""
    toolkit = OpenShiftSreToolkit(_settings())
    assert toolkit.tools is not None
    assert len(toolkit.tools) > 0


def test_toolkit_tool_manifest() -> None:
    """Tool manifest should include expected OpenShift inspection tools."""
    toolkit = OpenShiftSreToolkit(_settings())
    manifest = toolkit.tool_manifest()
    tool_names = [t["name"] for t in manifest]
    assert "get_cluster_identity" in tool_names
    assert "list_nodes" in tool_names
    assert "list_pods" in tool_names
    assert "list_cluster_operators" in tool_names


def test_toolkit_read_only_verbs() -> None:
    """Toolkit should enforce read-only verbs."""
    assert "get" in OpenShiftSreToolkit._READ_ONLY_OC_VERBS
    assert "describe" in OpenShiftSreToolkit._READ_ONLY_OC_VERBS
    assert "delete" not in OpenShiftSreToolkit._READ_ONLY_OC_VERBS
    assert "apply" not in OpenShiftSreToolkit._READ_ONLY_OC_VERBS
