from datetime import datetime, timedelta, timezone

from openshift_sre_agent.agent import AgentEnvelope, OpenShiftSreAgent
from openshift_sre_agent.config import Settings
from openshift_sre_agent.tools import OpenShiftSreToolkit


class StubModel:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._index = 0

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.1) -> str:
        response = self._responses[self._index]
        self._index += 1
        return response


class StubToolkit:
    def tool_manifest(self) -> list[dict]:
        return [{"name": "list_ec2_instances", "description": "test tool", "arguments": {}}]

    def invoke(self, name: str, arguments: dict) -> dict:
        assert name == "list_ec2_instances"
        assert arguments == {"state_filter": "running"}
        return {"count": 1, "instances": [{"instance_id": "i-123", "state": "running"}]}


class UnknownToolStubToolkit:
    def tool_manifest(self) -> list[dict]:
        return [{"name": "list_ec2_instances", "description": "test tool", "arguments": {}}]

    def invoke(self, name: str, arguments: dict) -> dict:
        raise KeyError(f"Unknown tool: {name}")


class CoverageToolkit:
    def tool_manifest(self) -> list[dict]:
        return [
            {"name": "list_securityhub_findings", "description": "test tool", "arguments": {}},
            {"name": "list_guardduty_findings", "description": "test tool", "arguments": {}},
        ]

    def invoke(self, name: str, arguments: dict) -> dict:
        if name == "list_securityhub_findings":
            return {"count": 0, "severity_counts": {}, "findings": []}
        if name == "list_guardduty_findings":
            return {"count": 0, "severity_counts": {}, "findings": []}
        raise AssertionError(f"Unexpected tool: {name}")


class SecurityCoverageToolkit:
    def tool_manifest(self) -> list[dict]:
        return [
            {"name": "list_cloudtrail_trails", "description": "test tool", "arguments": {}},
            {"name": "list_securityhub_standards", "description": "test tool", "arguments": {}},
            {"name": "list_securityhub_findings", "description": "test tool", "arguments": {}},
            {"name": "list_config_compliance_summary", "description": "test tool", "arguments": {}},
            {"name": "list_cloudtrail_event_selectors", "description": "test tool", "arguments": {}},
            {"name": "list_kms_keys", "description": "test tool", "arguments": {}},
            {"name": "list_iam_roles", "description": "test tool", "arguments": {}},
            {"name": "list_iam_credential_report", "description": "test tool", "arguments": {}},
        ]

    def invoke(self, name: str, arguments: dict) -> dict:
        responses = {
            "list_cloudtrail_trails": {"count": 0, "trails": []},
            "list_securityhub_standards": {"count": 0, "enabled_standard_count": 0},
            "list_securityhub_findings": {"count": 0, "severity_counts": {}, "findings": []},
            "list_config_compliance_summary": {"count": 0, "compliance_type_counts": {}},
            "list_cloudtrail_event_selectors": {"count": 0, "selectors": []},
            "list_kms_keys": {"count": 0, "keys": []},
            "list_iam_roles": {"count": 0, "stale_role_count": 0, "roles": []},
            "list_iam_credential_report": {"count": 0, "users": []},
        }
        if name not in responses:
            raise AssertionError(f"Unexpected tool: {name}")
        return responses[name]


class FinopsCoverageToolkit:
    def tool_manifest(self) -> list[dict]:
        return [
            {"name": "list_cost_and_usage_summary", "description": "test tool", "arguments": {}},
            {"name": "list_cost_by_service", "description": "test tool", "arguments": {}},
            {"name": "list_cost_by_tag", "description": "test tool", "arguments": {}},
            {"name": "get_cost_forecast", "description": "test tool", "arguments": {}},
            {"name": "list_savings_plans_coverage", "description": "test tool", "arguments": {}},
            {"name": "list_rightsizing_recommendations", "description": "test tool", "arguments": {}},
        ]

    def invoke(self, name: str, arguments: dict) -> dict:
        responses = {
            "list_cost_and_usage_summary": {"total_unblended_cost": {"amount": 100, "unit": "USD"}, "days": 30},
            "list_cost_by_service": {"total_unblended_cost": {"amount": 100, "unit": "USD"}, "service_costs": []},
            "list_cost_by_tag": {"total_unblended_cost": {"amount": 100, "unit": "USD"}, "tag_key": "Environment", "tag_costs": []},
            "get_cost_forecast": {"forecast_total": {"amount": 120, "unit": "USD"}, "months": 1},
            "list_savings_plans_coverage": {"average_coverage_percentage": 72.5, "count": 30},
            "list_rightsizing_recommendations": {"count": 1, "estimated_total_monthly_savings": {"amount": 25, "unit": "USD"}},
        }
        if name not in responses:
            raise AssertionError(f"Unexpected tool: {name}")
        return responses[name]


class CliDetourToolkit:
    def tool_manifest(self) -> list[dict]:
        return [
            {"name": "run_read_only_oc_cli", "description": "test tool", "arguments": {}},
            {"name": "list_cost_and_usage_summary", "description": "test tool", "arguments": {}},
            {"name": "list_cost_by_service", "description": "test tool", "arguments": {}},
            {"name": "list_cost_by_tag", "description": "test tool", "arguments": {}},
            {"name": "get_cost_forecast", "description": "test tool", "arguments": {}},
            {"name": "list_savings_plans_coverage", "description": "test tool", "arguments": {}},
            {"name": "list_rightsizing_recommendations", "description": "test tool", "arguments": {}},
        ]

    def invoke(self, name: str, arguments: dict) -> dict:
        if name == "run_read_only_oc_cli":
            raise AssertionError("CLI fallback should have been blocked before invocation")
        return {"count": 1}


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
    "thought": "Initial platform inventory inspection",
    "tool_call": {
        "name": "list_vpc_inventory",
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
    assert envelope.tool_call.name == "list_vpc_inventory"


def test_parse_envelope_normalizes_model_specific_aliases() -> None:
    envelope = OpenShiftSreAgent._parse_envelope(
        '{"reasoning":"Need EC2 state","tool":{"tool_name":"list_ec2_instances","parameters":{"state_filter":"running"}},"answer":""}'
    )

    assert isinstance(envelope, AgentEnvelope)
    assert envelope.thought == "Need EC2 state"
    assert envelope.tool_call is not None
    assert envelope.tool_call.name == "list_ec2_instances"
    assert envelope.tool_call.arguments == {"state_filter": "running"}


def test_parse_envelope_normalizes_stringified_tool_arguments() -> None:
    envelope = OpenShiftSreAgent._parse_envelope(
        '{"thought":"Need EC2 state","function_call":{"name":"list_ec2_instances","arguments":"{\\"state_filter\\": \\"running\\"}"},"final_answer":""}'
    )

    assert isinstance(envelope, AgentEnvelope)
    assert envelope.tool_call is not None
    assert envelope.tool_call.name == "list_ec2_instances"
    assert envelope.tool_call.arguments == {"state_filter": "running"}


def test_agent_recovers_from_unknown_tool() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"Need subnet data","tool_call":{"name":"list_nonexistent_tool","arguments":{}},"final_answer":""}',
            '{"thought":"Fallback after error","tool_call":null,"final_answer":"Use the documented inventory tools only; the requested tool name is unavailable."}',
        ]
    )
    agent.toolkit = UnknownToolStubToolkit()

    result = agent.ask("Inspect the network")

    assert "unavailable" in result.answer
    assert result.steps[0]["tool_error"] == "'Unknown tool: list_nonexistent_tool'"


def test_agent_completes_tool_loop() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"Need EC2 state","tool_call":{"name":"list_ec2_instances","arguments":{"state_filter":"running"}},"final_answer":""}',
            '{"thought":"Summarize findings","tool_call":null,"final_answer":"1 running instance found; no immediate fleet health risk."}',
        ]
    )
    agent.toolkit = StubToolkit()

    result = agent.ask("Investigate running instances")

    assert "1 running instance" in result.answer
    assert len(result.steps) == 2
    assert result.steps[0]["tool_result"]["count"] == 1


def test_agent_accepts_gpt_oss_style_envelope_aliases() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"reasoning":"Need EC2 state","tool":{"tool_name":"list_ec2_instances","parameters":{"state_filter":"running"}},"answer":""}',
            '{"analysis":"Summarize findings","response":"1 running instance found; no immediate fleet health risk."}',
        ]
    )
    agent.toolkit = StubToolkit()

    result = agent.ask("Investigate running instances")

    assert "1 running instance" in result.answer
    assert len(result.steps) == 2
    assert result.steps[0]["tool_call"]["name"] == "list_ec2_instances"


def test_agent_augments_final_answer_with_service_state_summary() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"Check Security Hub findings","tool_call":{"name":"list_securityhub_findings","arguments":{}},"final_answer":""}',
            '{"thought":"Check GuardDuty findings","tool_call":{"name":"list_guardduty_findings","arguments":{}},"final_answer":""}',
            '{"thought":"Summarize","tool_call":null,"final_answer":"Investigation complete."}',
        ]
    )

    class SummaryToolkit:
        def tool_manifest(self) -> list[dict]:
            return [
                {"name": "list_securityhub_findings", "description": "test tool", "arguments": {}},
                {"name": "list_guardduty_findings", "description": "test tool", "arguments": {}},
            ]

        def invoke(self, name: str, arguments: dict) -> dict:
            if name == "list_securityhub_findings":
                return {
                    "count": 0,
                    "findings": [],
                    "error": "An error occurred (InvalidAccessException) when calling the GetFindings operation: Account is not subscribed to OpenShift Security",
                }
            if name == "list_guardduty_findings":
                return {"count": 0, "severity_counts": {}, "findings": []}
            raise AssertionError(f"Unexpected tool: {name}")

    agent.toolkit = SummaryToolkit()

    result = agent.ask("Run a findings drilldown")

    assert "Observed service states:" in result.answer
    assert "not enabled or unsubscribed" in result.answer
    assert "no findings were returned" in result.answer


def test_agent_augments_final_answer_with_auth_summary() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"Check Security Hub findings","tool_call":{"name":"list_securityhub_findings","arguments":{}},"final_answer":""}',
            '{"thought":"Check GuardDuty findings","tool_call":{"name":"list_guardduty_findings","arguments":{}},"final_answer":""}',
            '{"thought":"Summarize","tool_call":null,"final_answer":"Please verify your cluster credentials before retrying."}',
        ]
    )

    class AuthSummaryToolkit:
        def tool_manifest(self) -> list[dict]:
            return [
                {"name": "list_securityhub_findings", "description": "test tool", "arguments": {}},
                {"name": "list_guardduty_findings", "description": "test tool", "arguments": {}},
            ]

        def invoke(self, name: str, arguments: dict) -> dict:
            if name == "list_securityhub_findings":
                return {
                    "count": 0,
                    "findings": [],
                    "error": "An error occurred (UnrecognizedClientException) when calling the GetFindings operation: The security token included in the request is invalid.",
                }
            if name == "list_guardduty_findings":
                raise RuntimeError(
                    "An error occurred (UnrecognizedClientException) when calling the ListDetectors operation: The security token included in the request is invalid."
                )
            raise AssertionError(f"Unexpected tool: {name}")

    agent.toolkit = AuthSummaryToolkit()

    result = agent.ask("Summarize Security Hub findings and GuardDuty findings.")

    assert "cluster credentials or the security token were rejected" in result.answer
    assert "credentials or the token were rejected by the cluster" in result.answer
    assert "Securityhub Findings" in result.answer
    assert "Guardduty Findings" in result.answer
    assert "Approve follow-up" in result.answer


def test_classify_error_message_distinguishes_auth_from_not_enabled() -> None:
    auth_message = (
        "An error occurred (UnrecognizedClientException) when calling the GetFindings operation: "
        "The security token included in the request is invalid."
    )
    not_enabled_message = (
        "An error occurred (InvalidAccessException) when calling the GetFindings operation: "
        "Account is not subscribed to OpenShift Security"
    )

    assert OpenShiftSreAgent._classify_error_message(auth_message) == (
        "credentials or the token were rejected by the cluster (UnrecognizedClientException)."
    )
    assert OpenShiftSreAgent._classify_error_message(not_enabled_message) == (
        "not enabled or unsubscribed in this account/region (InvalidAccessException)."
    )


def test_required_tools_for_finops_prompt() -> None:
    required_tools = OpenShiftSreAgent._required_tools_for_prompt(
        "Run a FinOps drilldown with cost and usage summary, cost by service, cost by tag for Environment, cost forecast, Savings Plans coverage, and rightsizing recommendations."
    )

    assert "list_cost_and_usage_summary" in required_tools
    assert "list_cost_by_service" in required_tools
    assert "list_cost_by_tag" in required_tools
    assert "get_cost_forecast" in required_tools
    assert "list_savings_plans_coverage" in required_tools
    assert "list_rightsizing_recommendations" in required_tools


def test_system_prompt_limits_manifest_to_required_tools() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)

    class PromptToolkit:
        def tool_manifest(self, names=None) -> list[dict]:
            manifest = [
                {"name": "get_caller_identity", "description": "identity", "arguments": {}},
                {"name": "list_enabled_regions", "description": "regions", "arguments": {}},
                {"name": "list_cost_by_service", "description": "cost", "arguments": {}},
            ]
            if names is None:
                return manifest
            return [tool for tool in manifest if tool["name"] in set(names)]

    agent.toolkit = PromptToolkit()

    prompt = agent._system_prompt(required_tools=("get_caller_identity", "list_enabled_regions"))

    assert '"get_caller_identity"' in prompt
    assert '"list_enabled_regions"' in prompt
    assert '"list_cost_by_service"' not in prompt


def test_required_tools_for_firewall_governance_prompt() -> None:
    required_tools = OpenShiftSreAgent._required_tools_for_prompt(
        "Review OpenShift Network Policy, Network Policy Manager, Platform Control, and Platform Governance posture."
    )

    assert "list_network_firewalls" in required_tools
    assert "list_firewall_manager_policies" in required_tools
    assert "list_controltower_controls" in required_tools
    assert "list_organization_accounts" in required_tools


def test_required_tools_for_container_runtime_prompt() -> None:
    required_tools = OpenShiftSreAgent._required_tools_for_prompt(
        "Investigate ECS service degradation with pending tasks and review EKS nodegroups and cluster addons for workload readiness."
    )

    assert "list_ecs_clusters" in required_tools
    assert "list_ecs_services" in required_tools
    assert "list_eks_clusters" in required_tools
    assert "list_eks_nodegroups" in required_tools


def test_required_tools_for_failover_and_target_health_prompts() -> None:
    required_tools = OpenShiftSreAgent._required_tools_for_prompt(
        "Review RDS failover posture, Aurora replica readiness, ALB target health, and EKS workload readiness with Fargate profiles and cluster insights."
    )

    assert "list_rds_instances" in required_tools
    assert "list_rds_failover_posture" in required_tools
    assert "list_load_balancers" in required_tools
    assert "list_target_groups" in required_tools
    assert "list_alb_target_health" in required_tools
    assert "list_eks_workload_readiness" in required_tools


def test_summarize_tool_result_for_finops_outputs() -> None:
    cost_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_cost_by_service",
        "Cost By Service",
        {
            "total_unblended_cost": {"amount": 123.45, "unit": "USD"},
            "service_costs": [
                {"service": "Amazon EC2", "unblended_cost": {"amount": 70.0, "unit": "USD"}},
                {"service": "Amazon S3", "unblended_cost": {"amount": 20.0, "unit": "USD"}},
            ],
        },
    )
    rightsizing_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_rightsizing_recommendations",
        "Rightsizing Recommendations",
        {
            "count": 3,
            "estimated_total_monthly_savings": {"amount": 45.67, "unit": "USD"},
            "recommendations": [
                {"resource_id": "i-123", "estimated_monthly_savings": 20.0},
            ],
        },
    )

    assert "123.45 USD" in cost_summary
    assert "Amazon EC2=70.00 USD" in cost_summary
    assert "3 recommendation(s)" in rightsizing_summary
    assert "45.67 USD" in rightsizing_summary


def test_summarize_tool_result_for_container_runtime_outputs() -> None:
    ecs_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_ecs_services",
        "ECS Services",
        {
            "count": 2,
            "services": [
                {"service_name": "orders", "desired_count": 4, "running_count": 2, "pending_count": 2},
                {"service_name": "payments", "desired_count": 2, "running_count": 2, "pending_count": 0},
            ],
        },
    )
    eks_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_eks_nodegroups",
        "EKS Nodegroups",
        {
            "nodegroup_count": 2,
            "addon_count": 2,
            "nodegroups": [
                {"nodegroup_name": "blue", "status": "ACTIVE", "health_issue_count": 0},
                {"nodegroup_name": "green", "status": "DEGRADED", "health_issue_count": 1},
            ],
            "addons": [
                {"addon_name": "vpc-cni", "status": "ACTIVE", "health_issue_count": 0},
                {"addon_name": "coredns", "status": "DEGRADED", "health_issue_count": 1},
            ],
        },
    )

    assert "2 ECS service row(s)" in ecs_summary
    assert "1 service(s)" in ecs_summary
    assert "2 node group row(s)" in eks_summary
    assert "1 add-on(s) needing attention" in eks_summary


def test_summarize_tool_result_for_failover_and_target_health_outputs() -> None:
    alb_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_alb_target_health",
        "ALB Target Health",
        {
            "count": 2,
            "unhealthy_target_group_count": 1,
            "target_groups": [
                {"target_group_name": "blue", "unhealthy_target_count": 2},
                {"target_group_name": "green", "unhealthy_target_count": 0},
            ],
        },
    )
    rds_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_rds_failover_posture",
        "RDS Failover Posture",
        {
            "instance_count": 3,
            "cluster_count": 1,
            "at_risk_instance_count": 1,
            "at_risk_cluster_count": 1,
        },
    )
    eks_workload_summary = OpenShiftSreAgent._summarize_tool_result(
        "list_eks_workload_readiness",
        "EKS Workload Readiness",
        {
            "fargate_profile_count": 2,
            "insight_count": 3,
            "unhealthy_insight_count": 1,
        },
    )

    assert "2 target group health row(s)" in alb_summary
    assert "2 target(s) in a non-healthy state" in alb_summary
    assert "3 DB instance row(s) and 1 Aurora/RDS cluster row(s)" in rds_summary
    assert "1 instance(s) and 1 cluster(s) lacking stronger failover posture" in rds_summary
    assert "2 Fargate profile row(s) and 3 cluster insight row(s)" in eks_workload_summary
    assert "1 insight(s) needing follow-up" in eks_workload_summary


def test_agent_recovers_when_model_returns_empty_turn() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"","tool_call":null,"final_answer":""}',
            '{"thought":"Recovered after retry","tool_call":null,"final_answer":"Recovered successfully after an empty model turn."}',
        ]
    )
    agent.toolkit = StubToolkit()

    result = agent.ask("Investigate the platform")

    assert "Recovered successfully" in result.answer
    assert result.steps[0]["tool_error"] == "Model did not produce a tool call or a final answer"
    assert len(result.steps) == 2


def test_agent_recovers_when_model_returns_invalid_json() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            'thinking... maybe I should inspect something first',
            '{"thought":"Recovered after schema reminder","tool_call":null,"final_answer":"Recovered successfully after invalid JSON."}',
        ]
    )
    agent.toolkit = StubToolkit()

    result = agent.ask("Investigate the platform")

    assert "Recovered successfully after invalid JSON." in result.answer
    assert "Model response was not valid JSON" in result.steps[0]["tool_error"]
    assert len(result.steps) == 2


def test_agent_requires_requested_service_check_before_finalizing() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"I can summarize immediately","tool_call":null,"final_answer":"No critical findings detected."}',
            '{"thought":"Need to actually check Security Hub","tool_call":{"name":"list_securityhub_findings","arguments":{}},"final_answer":""}',
            '{"thought":"Now summarize","tool_call":null,"final_answer":"Security Hub returned no sampled findings."}',
        ]
    )
    agent.toolkit = CoverageToolkit()

    result = agent.ask("Check Security Hub findings and summarize the result briefly.")

    assert result.steps[0]["tool_error"].startswith("You have not yet checked all explicitly requested services.")
    assert result.steps[1]["tool_call"]["name"] == "list_securityhub_findings"
    assert "Security Hub returned no sampled findings." in result.answer


def test_agent_requires_all_requested_services_for_multi_service_prompt() -> None:
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
        agent_max_steps=6,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"Start with Security Hub","tool_call":{"name":"list_securityhub_findings","arguments":{}},"final_answer":""}',
            '{"thought":"That should be enough","tool_call":null,"final_answer":"No critical findings detected overall."}',
            '{"thought":"Need GuardDuty too","tool_call":{"name":"list_guardduty_findings","arguments":{}},"final_answer":""}',
            '{"thought":"Now finalize","tool_call":null,"final_answer":"Security Hub and GuardDuty both returned no sampled findings."}',
        ]
    )
    agent.toolkit = CoverageToolkit()

    result = agent.ask("Summarize Security Hub findings and GuardDuty findings for a quick security review.")

    assert result.steps[1]["tool_error"].startswith("You have not yet checked all explicitly requested services.")
    assert result.steps[2]["tool_call"]["name"] == "list_guardduty_findings"
    assert "Security Hub and GuardDuty" in result.answer


def test_agent_adapts_step_budget_for_finops_drilldown() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"summary first","tool_call":null,"final_answer":"Done early."}',
            '{"thought":"cost summary","tool_call":{"name":"list_cost_and_usage_summary","arguments":{}},"final_answer":""}',
            '{"thought":"cost by service","tool_call":{"name":"list_cost_by_service","arguments":{}},"final_answer":""}',
            '{"thought":"cost by tag","tool_call":{"name":"list_cost_by_tag","arguments":{"tag_key":"Environment"}},"final_answer":""}',
            '{"thought":"forecast","tool_call":{"name":"get_cost_forecast","arguments":{}},"final_answer":""}',
            '{"thought":"coverage","tool_call":{"name":"list_savings_plans_coverage","arguments":{}},"final_answer":""}',
            '{"thought":"rightsizing","tool_call":{"name":"list_rightsizing_recommendations","arguments":{}},"final_answer":""}',
            '{"thought":"finalize","tool_call":null,"final_answer":"FinOps drilldown completed."}',
        ]
    )
    agent.toolkit = FinopsCoverageToolkit()

    result = agent.ask(
        "Run a FinOps drilldown with cost and usage summary, cost by service, cost by tag for Environment, cost forecast, Savings Plans coverage, and rightsizing recommendations."
    )

    assert result.answer.startswith("FinOps drilldown completed.")
    assert any((step.get("tool_call") or {}).get("name") == "list_rightsizing_recommendations" for step in result.steps)


def test_agent_blocks_unprompted_cli_detour_for_finops_prompt() -> None:
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
        agent_max_steps=8,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"try cli first","tool_call":{"name":"run_read_only_oc_cli","arguments":{"command":"oc get pods"}},"final_answer":""}',
            '{"thought":"cost summary instead","tool_call":{"name":"list_cost_and_usage_summary","arguments":{}},"final_answer":""}',
            '{"thought":"cost by service","tool_call":{"name":"list_cost_by_service","arguments":{}},"final_answer":""}',
            '{"thought":"cost by tag","tool_call":{"name":"list_cost_by_tag","arguments":{}},"final_answer":""}',
            '{"thought":"forecast","tool_call":{"name":"get_cost_forecast","arguments":{}},"final_answer":""}',
            '{"thought":"coverage","tool_call":{"name":"list_savings_plans_coverage","arguments":{}},"final_answer":""}',
            '{"thought":"rightsizing","tool_call":{"name":"list_rightsizing_recommendations","arguments":{}},"final_answer":""}',
            '{"thought":"finalize","tool_call":null,"final_answer":"FinOps done."}',
        ]
    )
    agent.toolkit = CliDetourToolkit()

    result = agent.ask(
        "Run a FinOps drilldown with cost and usage summary, cost by service, cost by tag for Environment, cost forecast, Savings Plans coverage, and rightsizing recommendations."
    )

    assert "FinOps done." in result.answer
    assert result.steps[0]["tool_error"].startswith("Use the named OpenShift inspection tools")
    assert result.steps[1]["tool_call"]["name"] == "list_cost_and_usage_summary"


def test_agent_returns_fallback_answer_when_step_limit_is_reached() -> None:
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
        agent_max_steps=3,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"","tool_call":null,"final_answer":""}',
            '{"thought":"","tool_call":null,"final_answer":""}',
            '{"thought":"","tool_call":null,"final_answer":""}',
        ]
    )
    agent.toolkit = StubToolkit()

    result = agent.ask("Investigate the platform")

    assert "configured maximum number of reasoning steps" in result.answer
    assert "invalid or incomplete responses" in result.answer
    assert "What I can do next:" in result.answer
    assert "Approve follow-up" in result.answer
    assert len(result.steps) == 3
    assert result.steps[-1]["tool_error"] == "Model did not produce a tool call or a final answer"


def test_agent_step_limit_answer_mentions_missing_required_tools() -> None:
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
    agent.model = StubModel(
        [
            '{"thought":"Summarize immediately","tool_call":null,"final_answer":"No issues found."}',
            '{"thought":"Still summarizing","tool_call":null,"final_answer":"No issues found."}',
            '{"thought":"unused","tool_call":null,"final_answer":"unused"}',
            '{"thought":"unused","tool_call":null,"final_answer":"unused"}',
            '{"thought":"unused","tool_call":null,"final_answer":"unused"}',
            '{"thought":"unused","tool_call":null,"final_answer":"unused"}',
            '{"thought":"unused","tool_call":null,"final_answer":"unused"}',
            '{"thought":"unused","tool_call":null,"final_answer":"unused"}',
            '{"thought":"unused","tool_call":null,"final_answer":"unused"}',
            '{"thought":"unused","tool_call":null,"final_answer":"unused"}',
        ]
    )
    agent.toolkit = CoverageToolkit()

    result = agent.ask("Check Security Hub findings and summarize the result briefly.")

    assert "No issues found." in result.answer
    assert "Securityhub Findings: reachable, but no findings were returned in the current sample." in result.answer
    assert result.steps[0]["tool_error"].startswith("You have not yet checked all explicitly requested services.")
    assert result.steps[1]["auto_recovery"] is True
    assert result.steps[1]["tool_call"]["name"] == "list_securityhub_findings"
    assert len(result.steps) == 3
    assert result.steps[0]["tool_error"].startswith("You have not yet checked all explicitly requested services.")


def test_agent_auto_invokes_missing_required_tool_after_premature_final_answer() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"I can summarize now","tool_call":null,"final_answer":"No major issues detected yet."}',
            '{"thought":"Now finalize","tool_call":null,"final_answer":"Security Hub returned no sampled findings after the required check completed."}',
        ]
    )
    agent.toolkit = CoverageToolkit()

    result = agent.ask("Check Security Hub findings and summarize the result briefly.")

    assert result.steps[0]["tool_error"].startswith("You have not yet checked all explicitly requested services.")
    assert result.steps[1]["auto_recovery"] is True
    assert result.steps[1]["tool_call"]["name"] == "list_securityhub_findings"
    assert result.steps[1]["tool_result"]["count"] == 0
    assert "Security Hub returned no sampled findings" in result.answer


def test_agent_auto_invokes_missing_required_security_tool_after_repeated_invalid_turns() -> None:
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
        agent_max_steps=8,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"Start with CloudTrail trails","tool_call":{"name":"list_cloudtrail_trails","arguments":{}},"final_answer":""}',
            '{"thought":"Check Security Hub standards","tool_call":{"name":"list_securityhub_standards","arguments":{}},"final_answer":""}',
            'thinking... maybe summarize later',
            '{"thought":"","tool_call":null,"final_answer":""}',
            '{"thought":"Wrap up","tool_call":null,"final_answer":"The required security checks progressed after auto-recovery."}',
        ]
    )
    agent.toolkit = SecurityCoverageToolkit()

    result = agent.ask(
        "Perform an OpenShift security review covering CloudTrail trails, Security Hub standards, and Security Hub findings."
    )

    auto_recovery_steps = [step for step in result.steps if step.get("auto_recovery")]

    assert any(step["tool_call"]["name"] == "list_securityhub_findings" for step in auto_recovery_steps)
    assert "required security checks progressed after auto-recovery" in result.answer
    assert "Securityhub Findings: reachable, but no findings were returned in the current sample." in result.answer


def test_agent_augments_finops_recommendations_with_fix_plan_and_execution_approval() -> None:
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
        agent_max_steps=4,
    )
    agent = OpenShiftSreAgent(settings)
    agent.model = StubModel(
        [
            '{"thought":"Need rightsizing data","tool_call":{"name":"list_rightsizing_recommendations","arguments":{}},"final_answer":""}',
            '{"thought":"Summarize findings","tool_call":null,"final_answer":"Rightsizing opportunities were found for EC2."}',
        ]
    )

    class RightsizingToolkit:
        def tool_manifest(self) -> list[dict]:
            return [
                {"name": "list_rightsizing_recommendations", "description": "test tool", "arguments": {}},
            ]

        def invoke(self, name: str, arguments: dict) -> dict:
            assert name == "list_rightsizing_recommendations"
            return {
                "count": 2,
                "estimated_total_monthly_savings": {"amount": 88.5, "unit": "USD"},
                "recommendations": [
                    {"resource_id": "i-123", "estimated_monthly_savings": 44.25},
                    {"resource_id": "i-456", "estimated_monthly_savings": 44.25},
                ],
            }

    agent.toolkit = RightsizingToolkit()

    result = agent.ask("Review rightsizing recommendations and summarize the next steps.")

    assert "Rightsizing opportunities were found for EC2." in result.answer
    assert "Approve fix plan" in result.answer
    assert "Approve supported execution plan" in result.answer
    assert "approval-ready optimization plan" in result.answer


def test_prompt_allows_cli_only_when_explicit() -> None:
    assert OpenShiftSreAgent._prompt_allows_cli("Run a read-only oc CLI command to inspect S3.") is True
    assert OpenShiftSreAgent._prompt_allows_cli("Run a FinOps drilldown with cost by service.") is False


def test_list_cost_by_tag_defaults_environment_tag() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeCeClient:
        def __init__(self) -> None:
            self.kwargs = None

        def get_cost_and_usage(self, **kwargs):
            self.kwargs = kwargs
            return {
                "ResultsByTime": [
                    {
                        "Groups": [
                            {
                                "Keys": ["Environment$prod"],
                                "Metrics": {"UnblendedCost": {"Amount": "12.34", "Unit": "USD"}},
                            }
                        ]
                    }
                ]
            }

    fake_client = FakeCeClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_cost_by_tag()

    assert fake_client.kwargs["GroupBy"] == [{"Type": "TAG", "Key": "Environment"}]
    assert result["tag_key"] == "Environment"
    assert result["tag_costs"][0]["tag_value"] == "prod"


def test_list_rightsizing_recommendations_uses_supported_api_shape() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeCeClient:
        def __init__(self) -> None:
            self.kwargs = None

        def get_rightsizing_recommendation(self, **kwargs):
            self.kwargs = kwargs
            return {
                "RightsizingRecommendations": [],
                "Summary": {},
            }

    fake_client = FakeCeClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    toolkit.list_rightsizing_recommendations()

    assert "LookbackPeriodInDays" not in fake_client.kwargs
    assert fake_client.kwargs["Configuration"]["RecommendationTarget"] == "SAME_INSTANCE_FAMILY"


def test_get_cost_forecast_uses_current_day_as_start() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeCeClient:
        def __init__(self) -> None:
            self.kwargs = None

        def get_cost_forecast(self, **kwargs):
            self.kwargs = kwargs
            return {
                "Total": {"Amount": "123.45", "Unit": "USD"},
                "MeanValue": {"Amount": "123.45", "Unit": "USD"},
                "PredictionIntervalLowerBound": {"Amount": "100.00", "Unit": "USD"},
                "PredictionIntervalUpperBound": {"Amount": "150.00", "Unit": "USD"},
            }

    fake_client = FakeCeClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.get_cost_forecast(months=2)

    today = datetime.now(timezone.utc).date()
    assert fake_client.kwargs["TimePeriod"]["Start"] == today.isoformat()
    assert fake_client.kwargs["TimePeriod"]["End"] == (today + timedelta(days=64)).isoformat()
    assert result["start"] == today.isoformat()
    assert result["forecast_total"]["amount"] == 123.45


def test_list_network_firewalls_returns_inventory_summary() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeNetworkFirewallClient:
        def list_firewalls(self, **kwargs):
            assert kwargs["MaxResults"] == 50
            return {"Firewalls": [{"FirewallName": "corp-egress", "FirewallArn": "openshift:network-policy:::firewall/corp-egress"}]}

        def list_firewall_policies(self, **kwargs):
            assert kwargs["MaxResults"] == 50
            return {"FirewallPolicies": [{"Name": "corp-policy", "Arn": "openshift:network-policy:::policy/corp-policy"}]}

        def describe_firewall(self, **kwargs):
            assert kwargs["FirewallArn"] == "openshift:network-policy:::firewall/corp-egress"
            return {
                "Firewall": {
                    "FirewallName": "corp-egress",
                    "FirewallId": "fw-123",
                    "VpcId": "vpc-123",
                    "FirewallPolicyArn": "openshift:network-policy:::policy/corp-policy",
                    "SubnetMappings": [{"SubnetId": "subnet-1"}, {"SubnetId": "subnet-2"}],
                    "DeleteProtection": True,
                    "FirewallPolicyChangeProtection": True,
                    "NumberOfAssociations": 2,
                },
                "FirewallStatus": {"Status": "READY"},
            }

    fake_client = FakeNetworkFirewallClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_network_firewalls()

    assert result["count"] == 1
    assert result["firewall_policy_count"] == 1
    assert result["firewalls"][0]["status"] == "READY"
    assert result["firewalls"][0]["subnet_mapping_count"] == 2


def test_list_firewall_manager_policies_returns_policy_summary() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeFmsClient:
        def list_policies(self, **kwargs):
            assert kwargs["MaxResults"] == 50
            return {
                "PolicyList": [
                    {
                        "PolicyId": "policy-123",
                        "PolicyArn": "openshift:policy:::policy/policy-123",
                        "PolicyName": "global-waf-policy",
                        "ResourceType": "Route",
                        "SecurityServiceType": "WAFV2",
                        "RemediationEnabled": True,
                        "PolicyStatus": "ACTIVE",
                        "DeleteUnusedFMManagedResources": False,
                    }
                ]
            }

        def get_policy(self, **kwargs):
            assert kwargs["PolicyId"] == "policy-123"
            return {
                "Policy": {
                    "PolicyId": "policy-123",
                    "ResourceTypeList": ["Route"],
                    "SecurityServicePolicyData": {"Type": "WAFV2"},
                    "PolicyStatus": "ACTIVE",
                }
            }

    fake_client = FakeFmsClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_firewall_manager_policies()

    assert result["count"] == 1
    assert result["policies"][0]["security_service_type"] == "WAFV2"
    assert result["policies"][0]["remediation_enabled"] is True


def test_list_controltower_controls_returns_landing_zone_and_controls() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeControlTowerClient:
        def list_landing_zones(self, **kwargs):
            assert kwargs["maxResults"] == 20
            return {"landingZones": [{"arn": ""openshift:resource/placeholder"}]}

        def get_landing_zone(self, **kwargs):
            assert kwargs["landingZoneIdentifier"] == ""openshift:resource/placeholder"
            return {
                "landingZone": {
                    "arn": ""openshift:resource/placeholder",
                    "status": "ACTIVE",
                    "driftStatus": "IN_SYNC",
                    "version": "3.3",
                    "latestAvailableVersion": "3.3",
                }
            }

        def list_enabled_controls(self, **kwargs):
            assert kwargs["targetIdentifier"] == ""openshift:resource/placeholder"
            assert kwargs["maxResults"] == 50
            return {
                "enabledControls": [
                    {
                        "arn": ""openshift:resource/placeholder",
                        "controlIdentifier": "OCP-ETCD-ENCRYPTION",
                        "targetIdentifier": ""openshift:resource/placeholder",
                        "statusSummary": {"status": "SUCCEEDED"},
                        "driftStatusSummary": {"driftStatus": "IN_SYNC"},
                    }
                ]
            }

    fake_client = FakeControlTowerClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_controltower_controls()

    assert result["landing_zone_count"] == 1
    assert result["enabled_control_count"] == 1
    assert result["landing_zones"][0]["status"] == "ACTIVE"
    assert result["enabled_controls"][0]["status"] == "SUCCEEDED"


def test_list_ecs_services_returns_runtime_health_summary() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeEcsClient:
        def list_clusters(self):
            return {"clusterArns": [""openshift:resource/placeholder"]}

        def list_services(self, **kwargs):
            assert kwargs["cluster"] == ""openshift:resource/placeholder"
            return {
                "serviceArns": [
                    ""openshift:resource/placeholder",
                    ""openshift:resource/placeholder",
                ]
            }

        def describe_services(self, **kwargs):
            assert kwargs["cluster"] == ""openshift:resource/placeholder"
            return {
                "services": [
                    {
                        "serviceName": "orders",
                        "status": "ACTIVE",
                        "launchType": "FARGATE",
                        "schedulingStrategy": "REPLICA",
                        "desiredCount": 4,
                        "runningCount": 2,
                        "pendingCount": 2,
                        "taskDefinition": "orders:17",
                        "deployments": [{"status": "PRIMARY", "rolloutState": "IN_PROGRESS"}],
                        "events": [{"message": "service orders has started 2 tasks"}],
                    },
                    {
                        "serviceName": "payments",
                        "status": "ACTIVE",
                        "launchType": "EC2",
                        "schedulingStrategy": "REPLICA",
                        "desiredCount": 2,
                        "runningCount": 2,
                        "pendingCount": 0,
                        "taskDefinition": "payments:33",
                        "deployments": [{"status": "PRIMARY", "rolloutState": "COMPLETED"}],
                        "events": [],
                    },
                ]
            }

    fake_client = FakeEcsClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_ecs_services()

    assert result["count"] == 2
    assert result["services"][0]["cluster_name"] == "prod-cluster"
    assert result["services"][0]["primary_deployment_rollout_state"] == "IN_PROGRESS"
    assert result["services"][0]["latest_event"] == "service orders has started 2 tasks"


def test_list_eks_nodegroups_returns_nodegroup_and_addon_posture() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeEksClient:
        def list_clusters(self):
            return {"clusters": ["prod-eks"]}

        def list_nodegroups(self, **kwargs):
            assert kwargs["clusterName"] == "prod-eks"
            return {"nodegroups": ["blue-workers"]}

        def describe_nodegroup(self, **kwargs):
            assert kwargs["clusterName"] == "prod-eks"
            assert kwargs["nodegroupName"] == "blue-workers"
            return {
                "nodegroup": {
                    "status": "DEGRADED",
                    "capacityType": "ON_DEMAND",
                    "amiType": "AL2_x86_64",
                    "instanceTypes": ["m6i.large"],
                    "version": "1.30",
                    "releaseVersion": "1.30.0-20241010",
                    "scalingConfig": {"desiredSize": 4, "minSize": 2, "maxSize": 6},
                    "health": {"issues": [{"code": "AutoScalingGroupNotFound"}]},
                }
            }

        def list_addons(self, **kwargs):
            assert kwargs["clusterName"] == "prod-eks"
            return {"addons": ["vpc-cni"]}

        def describe_addon(self, **kwargs):
            assert kwargs["clusterName"] == "prod-eks"
            assert kwargs["addonName"] == "vpc-cni"
            return {
                "addon": {
                    "status": "DEGRADED",
                    "addonVersion": "v1.18.0-eksbuild.1",
                    "serviceAccountRoleArn": ""openshift:resource/placeholder",
                    "health": {"issues": [{"code": "InsufficientNumberOfReplicas"}]},
                }
            }

    fake_client = FakeEksClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_eks_nodegroups()

    assert result["cluster_count"] == 1
    assert result["nodegroup_count"] == 1
    assert result["addon_count"] == 1
    assert result["nodegroups"][0]["health_issues"] == ["AutoScalingGroupNotFound"]
    assert result["addons"][0]["health_issues"] == ["InsufficientNumberOfReplicas"]


def test_list_alb_target_health_returns_unhealthy_target_summary() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeElbv2Client:
        def describe_target_groups(self):
            return {
                "TargetGroups": [
                    {
                        "TargetGroupName": "orders-blue",
                        "TargetGroupArn": ""openshift:resource/placeholder",
                        "TargetType": "ip",
                        "Protocol": "HTTP",
                        "Port": 80,
                        "HealthCheckProtocol": "HTTP",
                        "HealthCheckPath": "/healthz",
                        "LoadBalancerArns": [""openshift:resource/placeholder"],
                    }
                ]
            }

        def describe_target_health(self, **kwargs):
            assert kwargs["TargetGroupArn"].endswith("orders-blue/abc")
            return {
                "TargetHealthDescriptions": [
                    {"TargetHealth": {"State": "healthy"}},
                    {"TargetHealth": {"State": "unhealthy", "Reason": "Target.ResponseCodeMismatch"}},
                    {"TargetHealth": {"State": "draining", "Reason": "Target.DeregistrationInProgress"}},
                ]
            }

    fake_client = FakeElbv2Client()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_alb_target_health()

    assert result["count"] == 1
    assert result["unhealthy_target_group_count"] == 1
    assert result["target_groups"][0]["unhealthy_target_count"] == 2
    assert result["target_groups"][0]["unhealthy_reasons"]["Target.ResponseCodeMismatch"] == 1


def test_list_rds_failover_posture_returns_instance_and_cluster_summary() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeRdsClient:
        def describe_db_instances(self):
            return {
                "DBInstances": [
                    {
                        "DBInstanceIdentifier": "orders-db",
                        "DBInstanceArn": ""openshift:resource/placeholder",
                        "Engine": "postgres",
                        "DBInstanceStatus": "available",
                        "MultiAZ": False,
                        "AvailabilityZone": "us-east-1a",
                        "SecondaryAvailabilityZone": None,
                        "ReadReplicaDBInstanceIdentifiers": [],
                        "BackupRetentionPeriod": 7,
                        "StorageEncrypted": True,
                        "DeletionProtection": True,
                        "PerformanceInsightsEnabled": True,
                    }
                ]
            }

        def describe_db_clusters(self):
            return {
                "DBClusters": [
                    {
                        "DBClusterIdentifier": "orders-aurora",
                        "Engine": "aurora-postgresql",
                        "Status": "available",
                        "MultiAZ": True,
                        "DBClusterMembers": [
                            {"DBInstanceIdentifier": "orders-aurora-writer", "IsClusterWriter": True},
                        ],
                        "AvailabilityZones": ["us-east-1a", "us-east-1b"],
                        "BackupRetentionPeriod": 7,
                        "DeletionProtection": True,
                        "StorageEncrypted": True,
                        "IAMDatabaseAuthenticationEnabled": True,
                    }
                ]
            }

        def describe_pending_maintenance_actions(self):
            return {
                "PendingMaintenanceActions": [
                    {
                        "ResourceIdentifier": ""openshift:resource/placeholder",
                        "PendingMaintenanceActionDetails": [{"Action": "system-update"}],
                    }
                ]
            }

    fake_client = FakeRdsClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_rds_failover_posture()

    assert result["instance_count"] == 1
    assert result["cluster_count"] == 1
    assert result["at_risk_instance_count"] == 1
    assert result["at_risk_cluster_count"] == 1
    assert result["instances"][0]["pending_maintenance_actions"] == ["system-update"]


def test_list_eks_workload_readiness_returns_fargate_profiles_and_insights() -> None:
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
        agent_max_steps=8,
    )
    toolkit = OpenShiftSreToolkit(settings)

    class FakeEksWorkloadClient:
        def list_clusters(self):
            return {"clusters": ["prod-eks"]}

        def list_fargate_profiles(self, **kwargs):
            assert kwargs["clusterName"] == "prod-eks"
            return {"fargateProfileNames": ["payments-fargate"]}

        def describe_fargate_profile(self, **kwargs):
            assert kwargs["clusterName"] == "prod-eks"
            assert kwargs["fargateProfileName"] == "payments-fargate"
            return {
                "fargateProfile": {
                    "status": "ACTIVE",
                    "podExecutionRoleArn": ""openshift:resource/placeholder",
                    "subnets": ["subnet-1", "subnet-2"],
                    "selectors": [{"namespace": "payments"}, {"namespace": "checkout"}],
                }
            }

        def list_insights(self, **kwargs):
            assert kwargs["clusterName"] == "prod-eks"
            return {
                "insights": [
                    {
                        "id": "insight-1",
                        "name": "IPv4 exhaustion risk",
                        "category": "NETWORKING",
                        "kubernetesVersion": "1.30",
                        "insightStatus": {"status": "WARNING"},
                        "description": "Subnet IP availability is getting tight.",
                    }
                ]
            }

    fake_client = FakeEksWorkloadClient()
    toolkit._client = lambda service_name: fake_client  # type: ignore[method-assign]

    result = toolkit.list_eks_workload_readiness()

    assert result["cluster_count"] == 1
    assert result["fargate_profile_count"] == 1
    assert result["insight_count"] == 1
    assert result["unhealthy_insight_count"] == 1
    assert result["fargate_profiles"][0]["namespaces"] == ["payments", "checkout"]
    assert result["insights"][0]["insight_status"] == "WARNING"


def test_settings_with_overrides_prefers_request_values() -> None:
    base = Settings(
        ollama_base_url="http://localhost:11434",
        local_model_name="base-model",
        cluster_scope="us-east-1",
        kube_context_name="default",
        openshift_api_url_field=None,
        openshift_token_field=None,
        openshift_namespace_field=None,
        tls_ca_bundle=None,
        verify_ssl=True,
        allow_mutating_actions=False,
        agent_max_steps=8,
    )

    overridden = base.with_overrides(
        ollama_base_url="http://host.containers.internal:11434",
        local_model_name="qwen3:8b",
        cluster_scope="eu-west-1",
        openshift_api_url_field="test-access-key",
        openshift_token_field="test-secret",
        openshift_namespace_field="test-token",
        tls_ca_bundle="/tmp/test-ca.pem",
        verify_ssl=False,
    )

    assert overridden.ollama_base_url == "http://host.containers.internal:11434"
    assert overridden.local_model_name == "qwen3:8b"
    assert overridden.cluster_scope == "eu-west-1"
    assert overridden.kube_context_name is None
    assert overridden.openshift_api_url_field == "test-access-key"
    assert overridden.openshift_token_field == "test-secret"
    assert overridden.openshift_namespace_field == "test-token"
    assert overridden.tls_ca_bundle == "/tmp/test-ca.pem"
    assert overridden.verify_ssl is False
