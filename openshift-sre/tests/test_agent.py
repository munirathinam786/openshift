from __future__ import annotations

from openshift_sre_agent.agent import AgentEnvelope, OpenShiftSreAgent
from openshift_sre_agent.config import Settings
from openshift_sre_agent.tools import OpenShiftSreToolkit


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ollama_base_url": "http://localhost:11434",
        "local_model_name": "test-model",
        "cluster_scope": "local-cluster",
        "kube_context_name": None,
        "openshift_api_url_field": None,
        "openshift_token_field": None,
        "openshift_namespace_field": None,
        "tls_ca_bundle": None,
        "verify_ssl": True,
        "allow_mutating_actions": False,
        "agent_max_steps": 6,
    }
    defaults.update(overrides)
    return Settings(**defaults)


class StubModel:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._index = 0

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.1) -> str:
        response = self._responses[self._index]
        self._index += 1
        return response


class FilterableToolkit:
    def __init__(self, manifest: list[dict], responses: dict[str, dict] | None = None, errors: dict[str, Exception | str] | None = None) -> None:
        self._manifest = manifest
        self._responses = responses or {}
        self._errors = errors or {}

    def tool_manifest(self, names=None) -> list[dict]:
        if names is None:
            return list(self._manifest)
        selected = set(names)
        return [tool for tool in self._manifest if tool["name"] in selected]

    def invoke(self, name: str, arguments: dict) -> dict:
        error = self._errors.get(name)
        if error is not None:
            raise error if isinstance(error, Exception) else RuntimeError(error)
        if name not in self._responses:
            raise KeyError(f"Unknown tool: {name}")
        return self._responses[name]


def test_parse_envelope() -> None:
    envelope = OpenShiftSreAgent._parse_envelope(
        '{"thought":"inspect","tool_call":null,"final_answer":"all good"}'
    )
    assert isinstance(envelope, AgentEnvelope)
    assert envelope.final_answer == "all good"


def test_parse_envelope_recovers_json_from_chatty_response() -> None:
    envelope = OpenShiftSreAgent._parse_envelope(
        """Hello operator, here's the result.

```json
{
    "thought": "Inspect cluster operators",
    "tool_call": {
        "name": "list_cluster_operators",
        "arguments": {}
    },
    "final_answer": ""
}
```

Please let me know if you'd like to continue.
"""
    )

    assert isinstance(envelope, AgentEnvelope)
    assert envelope.tool_call is not None
    assert envelope.tool_call.name == "list_cluster_operators"


def test_parse_envelope_normalizes_model_specific_aliases() -> None:
    envelope = OpenShiftSreAgent._parse_envelope(
        '{"reasoning":"Need routes","tool":{"tool_name":"list_routes","parameters":{"project":"payments"}},"answer":""}'
    )

    assert isinstance(envelope, AgentEnvelope)
    assert envelope.thought == "Need routes"
    assert envelope.tool_call is not None
    assert envelope.tool_call.name == "list_routes"
    assert envelope.tool_call.arguments == {"project": "payments"}


def test_parse_envelope_normalizes_stringified_tool_arguments() -> None:
    envelope = OpenShiftSreAgent._parse_envelope(
        '{"thought":"Need events","function_call":{"name":"list_events","arguments":"{\\"project\\": \\"payments\\"}"},"final_answer":""}'
    )

    assert isinstance(envelope, AgentEnvelope)
    assert envelope.tool_call is not None
    assert envelope.tool_call.name == "list_events"
    assert envelope.tool_call.arguments == {"project": "payments"}


def test_agent_recovers_from_unknown_tool() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=4))
    agent.model = StubModel(
        [
            '{"thought":"Need a nonexistent check","tool_call":{"name":"list_nonexistent_tool","arguments":{}},"final_answer":""}',
            '{"thought":"Fallback after error","tool_call":null,"final_answer":"Use the documented OpenShift inventory tools only; the requested tool name is unavailable."}',
        ]
    )
    agent.toolkit = FilterableToolkit([
        {"name": "list_projects", "description": "test tool", "arguments": {}},
    ])

    result = agent.ask("Inspect the cluster")

    assert "unavailable" in result.answer
    assert result.steps[0]["tool_error"] == "'Unknown tool: list_nonexistent_tool'"


def test_agent_completes_tool_loop() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=4))
    agent.model = StubModel(
        [
            '{"thought":"Need project inventory","tool_call":{"name":"list_projects","arguments":{}},"final_answer":""}',
            '{"thought":"Summarize findings","tool_call":null,"final_answer":"2 projects found; no immediate namespace hygiene risk."}',
        ]
    )
    agent.toolkit = FilterableToolkit(
        [{"name": "list_projects", "description": "test tool", "arguments": {}}],
        responses={"list_projects": {"count": 2, "projects": [{"project": "default"}, {"project": "openshift-ingress"}]}}
    )

    result = agent.ask("List projects")

    assert "2 projects found" in result.answer
    assert len(result.steps) == 2
    assert result.steps[0]["tool_result"]["count"] == 2


def test_agent_accepts_gpt_oss_style_envelope_aliases() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=4))
    agent.model = StubModel(
        [
            '{"reasoning":"Need operator health","tool":{"tool_name":"list_cluster_operators","parameters":{}},"answer":""}',
            '{"analysis":"Summarize findings","response":"Cluster operators inspected successfully."}',
        ]
    )
    agent.toolkit = FilterableToolkit(
        [{"name": "list_cluster_operators", "description": "test tool", "arguments": {}}],
        responses={"list_cluster_operators": {"count": 3, "degraded_count": 0, "progressing_count": 0, "cluster_operators": []}}
    )

    result = agent.ask("Review cluster operators")

    assert "Cluster operators inspected successfully" in result.answer
    assert len(result.steps) == 2
    assert result.steps[0]["tool_call"]["name"] == "list_cluster_operators"


def test_agent_augments_final_answer_with_platform_state_summary() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=4))
    agent.model = StubModel(
        [
            '{"thought":"Check cluster operators","tool_call":{"name":"list_cluster_operators","arguments":{}},"final_answer":""}',
            '{"thought":"Check events","tool_call":{"name":"list_events","arguments":{}},"final_answer":""}',
            '{"thought":"Summarize","tool_call":null,"final_answer":"Investigation complete."}',
        ]
    )
    agent.toolkit = FilterableToolkit(
        [
            {"name": "list_cluster_operators", "description": "test tool", "arguments": {}},
            {"name": "list_events", "description": "test tool", "arguments": {}},
        ],
        responses={
            "list_cluster_operators": {"count": 4, "degraded_count": 1, "progressing_count": 1, "cluster_operators": []},
            "list_events": {"count": 6, "warning_count": 2, "events": []},
        },
    )

    result = agent.ask("Review degraded operators and recent warnings.")

    assert "Observed platform states:" in result.answer
    assert "Cluster Operators: returned 4 operator row(s), with 1 degraded and 1 progressing." in result.answer
    assert "Events: returned 6 event row(s), with 2 warning event(s)." in result.answer


def test_agent_augments_final_answer_with_auth_summary() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=4))
    agent.model = StubModel(
        [
            '{"thought":"Check operators","tool_call":{"name":"list_cluster_operators","arguments":{}},"final_answer":""}',
            '{"thought":"Check events","tool_call":{"name":"list_events","arguments":{}},"final_answer":""}',
            '{"thought":"Summarize","tool_call":null,"final_answer":"Please verify your cluster credentials before retrying."}',
        ]
    )
    agent.toolkit = FilterableToolkit(
        [
            {"name": "list_cluster_operators", "description": "test tool", "arguments": {}},
            {"name": "list_events", "description": "test tool", "arguments": {}},
        ],
        errors={
            "list_cluster_operators": "Unauthorized: invalid bearer token",
            "list_events": "Unauthorized: token has expired",
        },
    )

    result = agent.ask("Review degraded operators and recent warnings.")

    assert "credentials or cluster authentication were rejected." in result.answer
    assert "Cluster Operators" in result.answer
    assert "Events" in result.answer


def test_classify_error_message_distinguishes_auth_from_not_enabled() -> None:
    auth_message = "Unauthorized: invalid bearer token"
    not_enabled_message = "the server could not find the requested resource"

    assert OpenShiftSreAgent._classify_error_message(auth_message) == "credentials or cluster authentication were rejected."
    assert OpenShiftSreAgent._classify_error_message(not_enabled_message) == "required cluster API or extension is not available on this cluster."


def test_required_tools_for_platform_review_prompt() -> None:
    required_tools = OpenShiftSreAgent._required_tools_for_prompt(
        "Review cluster version, degraded operators, route exposure, warning events, and build failures."
    )

    assert "list_cluster_version" in required_tools
    assert "list_cluster_operators" in required_tools
    assert "list_routes" in required_tools
    assert "list_ingresses" in required_tools
    assert "list_events" in required_tools
    assert "list_builds" in required_tools


def test_required_tools_for_capacity_prompt() -> None:
    required_tools = OpenShiftSreAgent._required_tools_for_prompt(
        "Inspect node pressure, pods, workload health, storage classes, and resource quotas."
    )

    assert "list_nodes" in required_tools
    assert "list_node_pressure" in required_tools
    assert "list_pods" in required_tools
    assert "list_workload_health" in required_tools
    assert "list_storage_classes" in required_tools
    assert "list_resource_quotas" in required_tools


def test_system_prompt_limits_manifest_to_required_tools() -> None:
    agent = OpenShiftSreAgent(make_settings())

    class PromptToolkit:
        def tool_manifest(self, names=None) -> list[dict]:
            manifest = [
                {"name": "get_cluster_identity", "description": "identity", "arguments": {}},
                {"name": "list_projects", "description": "projects", "arguments": {}},
                {"name": "list_builds", "description": "builds", "arguments": {}},
            ]
            if names is None:
                return manifest
            return [tool for tool in manifest if tool["name"] in set(names)]

    agent.toolkit = PromptToolkit()

    prompt = agent._system_prompt(required_tools=("get_cluster_identity", "list_projects"))

    assert '"get_cluster_identity"' in prompt
    assert '"list_projects"' in prompt
    assert '"list_builds"' not in prompt


def test_summarize_tool_result_for_platform_outputs() -> None:
    operator_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_cluster_operators",
        "Cluster Operators",
        {"count": 5, "degraded_count": 1, "progressing_count": 2, "cluster_operators": []},
    )
    route_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_routes",
        "Routes",
        {"count": 4, "insecure_count": 1, "routes": []},
    )
    quota_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_resource_quotas",
        "Resource Quotas",
        {"quota_count": 3, "cluster_quota_count": 1, "resource_quotas": [], "cluster_resource_quotas": []},
    )

    assert "5 operator row(s)" in operator_summary
    assert "1 degraded and 2 progressing" in operator_summary
    assert "4 route row(s)" in route_summary
    assert "1 lacking TLS configuration" in route_summary
    assert "3 resource quota row(s) and 1 cluster resource quota row(s)" in quota_summary


def test_summarize_tool_result_for_pressure_and_build_outputs() -> None:
    pressure_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_node_pressure",
        "Node Pressure",
        {"count": 3, "pressure_counts": {"memory": 1, "disk": 2, "pid": 0, "not_ready": 1}, "nodes": []},
    )
    build_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_builds",
        "Builds",
        {"count": 7, "failed_count": 2, "builds": []},
    )

    assert "memory=1, disk=2, pid=0, not_ready=1" in pressure_summary
    assert "7 build row(s), with 2 failed or cancelled" in build_summary


def test_agent_recovers_when_model_returns_empty_turn() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=4))
    agent.model = StubModel(
        [
            '{"thought":"","tool_call":null,"final_answer":""}',
            '{"thought":"Recovered after retry","tool_call":null,"final_answer":"Recovered successfully after an empty model turn."}',
        ]
    )
    agent.toolkit = FilterableToolkit([{"name": "list_projects", "description": "test tool", "arguments": {}}])

    result = agent.ask("Investigate the platform")

    assert "Recovered successfully" in result.answer
    assert result.steps[0]["tool_error"] == "Model did not produce a tool call or a final answer"
    assert len(result.steps) == 2


def test_agent_recovers_when_model_returns_invalid_json() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=4))
    agent.model = StubModel(
        [
            "thinking... maybe I should inspect something first",
            '{"thought":"Recovered after schema reminder","tool_call":null,"final_answer":"Recovered successfully after invalid JSON."}',
        ]
    )
    agent.toolkit = FilterableToolkit([{"name": "list_projects", "description": "test tool", "arguments": {}}])

    result = agent.ask("Investigate the platform")

    assert "Recovered successfully after invalid JSON." in result.answer
    assert "Model response was not valid JSON" in result.steps[0]["tool_error"]
    assert len(result.steps) == 2


def test_agent_requires_requested_service_check_before_finalizing() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=4))
    agent.model = StubModel(
        [
            '{"thought":"I can summarize immediately","tool_call":null,"final_answer":"No critical findings detected."}',
            '{"thought":"Now summarize","tool_call":null,"final_answer":"Cluster operators returned no degraded components."}',
        ]
    )
    agent.toolkit = FilterableToolkit(
        [{"name": "list_cluster_operators", "description": "test tool", "arguments": {}}],
        responses={"list_cluster_operators": {"count": 3, "degraded_count": 0, "progressing_count": 0, "cluster_operators": []}},
    )

    result = agent.ask("Check degraded operators and summarize briefly.")

    assert result.steps[0]["tool_error"].startswith("You have not yet checked all explicitly requested platform areas.")
    assert result.steps[1]["auto_recovery"] is True
    assert result.steps[1]["tool_call"]["name"] == "list_cluster_operators"
    assert "Cluster operators returned no degraded components." in result.answer


def test_agent_requires_all_requested_services_for_multi_service_prompt() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=6))
    agent.model = StubModel(
        [
            '{"thought":"Start with operators","tool_call":{"name":"list_cluster_operators","arguments":{}},"final_answer":""}',
            '{"thought":"That should be enough","tool_call":null,"final_answer":"No critical findings detected overall."}',
            '{"thought":"Need events too","tool_call":{"name":"list_events","arguments":{}},"final_answer":""}',
            '{"thought":"Now finalize","tool_call":null,"final_answer":"Cluster operators and warning events were both reviewed."}',
        ]
    )
    agent.toolkit = FilterableToolkit(
        [
            {"name": "list_cluster_operators", "description": "test tool", "arguments": {}},
            {"name": "list_events", "description": "test tool", "arguments": {}},
        ],
        responses={
            "list_cluster_operators": {"count": 3, "degraded_count": 0, "progressing_count": 0, "cluster_operators": []},
            "list_events": {"count": 4, "warning_count": 1, "events": []},
        },
    )

    result = agent.ask("Review degraded operators and warning events for a quick platform check.")

    assert result.steps[1]["tool_error"].startswith("You have not yet checked all explicitly requested platform areas.")
    assert result.steps[2]["tool_call"]["name"] == "list_events"
    assert "Cluster operators and warning events were both reviewed." in result.answer


def test_agent_blocks_unprompted_cli_detour_for_platform_prompt() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=8))
    agent.model = StubModel(
        [
            '{"thought":"try cli first","tool_call":{"name":"run_read_only_oc_cli","arguments":{"command":"oc get pods -A"}},"final_answer":""}',
            '{"thought":"check operators instead","tool_call":{"name":"list_cluster_operators","arguments":{}},"final_answer":""}',
            '{"thought":"check events","tool_call":{"name":"list_events","arguments":{}},"final_answer":""}',
            '{"thought":"finalize","tool_call":null,"final_answer":"Platform review completed."}',
        ]
    )
    agent.toolkit = FilterableToolkit(
        [
            {"name": "run_read_only_oc_cli", "description": "test tool", "arguments": {}},
            {"name": "list_cluster_operators", "description": "test tool", "arguments": {}},
            {"name": "list_events", "description": "test tool", "arguments": {}},
        ],
        responses={
            "list_cluster_operators": {"count": 2, "degraded_count": 0, "progressing_count": 0, "cluster_operators": []},
            "list_events": {"count": 2, "warning_count": 0, "events": []},
        },
    )

    result = agent.ask("Review degraded operators and warning events.")

    assert "Platform review completed." in result.answer
    assert result.steps[0]["tool_error"].startswith("Use the named OpenShift inspection tools")
    assert result.steps[1]["tool_call"]["name"] == "list_cluster_operators"


def test_agent_returns_fallback_answer_when_step_limit_is_reached() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=3))
    agent.model = StubModel(
        [
            '{"thought":"","tool_call":null,"final_answer":""}',
            '{"thought":"","tool_call":null,"final_answer":""}',
            '{"thought":"","tool_call":null,"final_answer":""}',
        ]
    )
    agent.toolkit = FilterableToolkit([{"name": "list_projects", "description": "test tool", "arguments": {}}])

    result = agent.ask("Investigate the platform")

    assert "configured maximum number of reasoning steps" in result.answer
    assert "Model did not produce a tool call or a final answer" in result.answer
    assert len(result.steps) == 3
    assert result.steps[-1]["tool_error"] == "Model did not produce a tool call or a final answer"


def test_agent_auto_invokes_missing_required_tool_after_repeated_invalid_turns() -> None:
    agent = OpenShiftSreAgent(make_settings(agent_max_steps=6))
    agent.model = StubModel(
        [
            "thinking... maybe summarize later",
            '{"thought":"","tool_call":null,"final_answer":""}',
            '{"thought":"Wrap up too early","tool_call":null,"final_answer":"Security posture review progressed after auto-recovery."}',
            '{"thought":"Finalize after recovery","tool_call":null,"final_answer":"Security posture review progressed after auto-recovery."}',
        ]
    )
    agent.toolkit = FilterableToolkit(
        [{"name": "list_security_context_constraints", "description": "test tool", "arguments": {}}],
        responses={"list_security_context_constraints": {"count": 2, "privileged_count": 1, "security_context_constraints": []}},
    )

    result = agent.ask("Review SCC posture.")

    auto_recovery_steps = [step for step in result.steps if step.get("auto_recovery")]
    assert any(step["tool_call"]["name"] == "list_security_context_constraints" for step in auto_recovery_steps)
    assert "Security posture review progressed after auto-recovery." in result.answer
    assert "Security Context Constraints: returned 2 SCC row(s), with 1 allowing privileged containers." in result.answer


def test_prompt_allows_cli_only_when_explicit() -> None:
    assert OpenShiftSreAgent._prompt_allows_cli("Run a read-only oc CLI command to inspect pods.") is True
    assert OpenShiftSreAgent._prompt_allows_cli("Review degraded operators and warnings.") is False


def test_tool_manifest_filters_selected_names() -> None:
    toolkit = OpenShiftSreToolkit(make_settings())
    manifest = toolkit.tool_manifest(("get_cluster_identity", "list_projects"))

    assert {tool["name"] for tool in manifest} == {"get_cluster_identity", "list_projects"}


def test_list_cluster_proxy_config_returns_proxy_summary() -> None:
    toolkit = OpenShiftSreToolkit(make_settings())
    toolkit._list_custom = lambda **kwargs: [
        {
            "metadata": {"name": "cluster"},
            "spec": {
                "httpProxy": "http://proxy.internal:8080",
                "httpsProxy": "https://proxy.internal:8443",
                "noProxy": "svc,.cluster.local",
                "trustedCA": {"name": "proxy-ca"},
                "readinessEndpoints": ["https://www.redhat.com/healthz"],
            },
            "status": {},
        }
    ]

    result = toolkit.list_cluster_proxy_config()

    assert result["count"] == 1
    assert result["cluster_proxies"][0]["http_proxy_configured"] is True
    assert result["cluster_proxies"][0]["https_proxy_configured"] is True
    assert result["cluster_proxies"][0]["no_proxy_entry_count"] == 2
    assert result["cluster_proxies"][0]["trusted_ca_name"] == "proxy-ca"


def test_list_feature_gate_config_returns_feature_set_summary() -> None:
    toolkit = OpenShiftSreToolkit(make_settings())
    toolkit._list_custom = lambda **kwargs: [
        {
            "metadata": {"name": "cluster"},
            "spec": {
                "featureSet": "TechPreviewNoUpgrade",
                "customNoUpgrade": {
                    "enabled": ["NodeSwap"],
                    "disabled": ["ExampleFeature"],
                },
            },
        }
    ]

    result = toolkit.list_feature_gate_config()

    assert result["count"] == 1
    assert result["feature_gates"][0]["feature_set"] == "TechPreviewNoUpgrade"
    assert result["feature_gates"][0]["enabled_custom_feature_count"] == 1
    assert result["feature_gates"][0]["disabled_custom_feature_count"] == 1


def test_list_machine_health_checks_returns_remediation_summary() -> None:
    toolkit = OpenShiftSreToolkit(make_settings())
    toolkit._list_custom_any_version = lambda **kwargs: [
        {
            "metadata": {"name": "workers-health"},
            "spec": {
                "selector": {"matchLabels": {"machine.openshift.io/cluster-api-machineset": "workers"}},
                "maxUnhealthy": "40%",
                "nodeStartupTimeout": "10m",
                "unhealthyConditions": [{"type": "Ready", "status": "False", "timeout": "5m"}],
                "remediationTemplate": {"name": "self-node-remediation"},
            },
            "status": {"currentHealthy": 3, "expectedMachines": 4, "remediationsAllowed": 1},
        }
    ]

    result = toolkit.list_machine_health_checks()

    assert result["count"] == 1
    assert result["remediation_enabled_count"] == 1
    assert result["machine_health_checks"][0]["remediations_allowed"] == 1


def test_list_cluster_autoscaling_returns_scaler_summary() -> None:
    toolkit = OpenShiftSreToolkit(make_settings())

    def fake_list_custom_any_version(**kwargs):
        plural = kwargs["plural"]
        if plural == "clusterautoscalers":
            return [
                {
                    "metadata": {"name": "default"},
                    "spec": {
                        "scaleDown": {"enabled": True, "delayAfterAdd": "10m", "unneededTime": "5m"},
                        "resourceLimits": {"cores": {"min": 4, "max": 64}},
                    },
                }
            ]
        if plural == "machineautoscalers":
            return [
                {
                    "metadata": {"name": "workers-east"},
                    "spec": {
                        "scaleTargetRef": {"kind": "MachineSet", "name": "workers-east"},
                        "minReplicas": 3,
                        "maxReplicas": 9,
                    },
                }
            ]
        return []

    toolkit._list_custom_any_version = fake_list_custom_any_version

    result = toolkit.list_cluster_autoscaling()

    assert result["cluster_autoscaler_count"] == 1
    assert result["machine_autoscaler_count"] == 1
    assert result["machine_autoscaler_enabled_count"] == 1
    assert result["cluster_autoscalers"][0]["scale_down_enabled"] is True
    assert result["machine_autoscalers"][0]["max_replicas"] == 9


def test_settings_with_overrides_prefers_request_values() -> None:
    base = make_settings(
        local_model_name="base-model",
        cluster_scope="local-cluster",
        kube_context_name="default",
    )

    overridden = base.with_overrides(
        ollama_base_url="http://host.containers.internal:11434",
        local_model_name="qwen3:8b",
        cluster_scope="edge-cluster",
        openshift_api_url_field="https://api.edge.example.com:6443",
        openshift_token_field="test-token",
        openshift_namespace_field="payments",
        tls_ca_bundle="/tmp/test-ca.pem",
        verify_ssl=False,
    )

    assert overridden.ollama_base_url == "http://host.containers.internal:11434"
    assert overridden.local_model_name == "qwen3:8b"
    assert overridden.cluster_scope == "edge-cluster"
    assert overridden.openshift_cluster == "edge-cluster"
    assert overridden.kube_context is None
    assert overridden.openshift_api_url == "https://api.edge.example.com:6443"
    assert overridden.openshift_token == "test-token"
    assert overridden.openshift_namespace == "payments"
    assert overridden.tls_ca_bundle == "/tmp/test-ca.pem"
    assert overridden.openshift_verify_ssl is False
