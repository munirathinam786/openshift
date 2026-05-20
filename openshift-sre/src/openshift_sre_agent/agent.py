from __future__ import annotations

import json
import re
from dataclasses import dataclass
from json import JSONDecodeError, JSONDecoder
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .config import Settings
from .model_client import OllamaClient
from .prompts import get_system_prompt
from .tools import OpenShiftSreToolkit


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentEnvelope(BaseModel):
    thought: str = ""
    tool_call: ToolCall | None = None
    final_answer: str = ""


@dataclass(slots=True)
class AgentResult:
    answer: str
    steps: list[dict[str, Any]]
    confidence: float | None = None
    token_usage: dict[str, int] | None = None
    tags: list[str] | None = None


class OpenShiftSreAgent:
    """Reasoning loop for OpenShift SRE analysis using guarded read-only tools."""

    _RETRY_PROMPT = (
        "Your previous response was invalid for the required JSON contract. "
        "Reply with valid JSON only and include either a non-null tool_call or a non-empty final_answer. "
        "Do not leave both tool_call and final_answer empty."
    )
    _CLI_ALLOWED_PROMPT_PATTERN = re.compile(r"\b(oc\s+command|read[-\s]*only\s+oc|cli\s+command|kubectl\s+command)\b", re.IGNORECASE)
    _AUTO_INVOKE_MISSING_TOOL_AFTER_FAILURES = 2
    _FINDINGS_TOOL_NAMES = {
        "list_cluster_operators",
        "list_security_context_constraints",
        "list_network_policies",
        "list_routes",
        "list_events",
    }
    _FINOPS_TOOL_NAMES: set[str] = set()
    _PROMPT_TOOL_REQUIREMENTS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
        (re.compile(r"cluster\s+identity|who\s+am\s+i|current\s+cluster|active\s+context", re.IGNORECASE), ("get_cluster_identity",)),
        (re.compile(r"projects?|namespaces?", re.IGNORECASE), ("list_projects",)),
        (re.compile(r"cluster\s+version|upgrade\s+channel|clusterversion", re.IGNORECASE), ("list_cluster_version",)),
        (re.compile(r"cluster\s+operators?|degraded\s+operators?|operators?\s+health", re.IGNORECASE), ("list_cluster_operators",)),
        (re.compile(r"nodes?|node\s+health|worker\s+nodes?|control\s+plane", re.IGNORECASE), ("list_nodes",)),
        (re.compile(r"pressure|memory\s+pressure|disk\s+pressure|pid\s+pressure|not\s+ready\s+nodes?", re.IGNORECASE), ("list_nodes", "list_node_pressure")),
        (re.compile(r"pods?|crashloop|pending\s+pods?|restart\s+count", re.IGNORECASE), ("list_pods",)),
        (re.compile(r"deployment|statefulset|daemonset|rollout|workload\s+health|job\s+fail", re.IGNORECASE), ("list_workload_health",)),
        (re.compile(r"services?|clusterip|loadbalancer\s+service", re.IGNORECASE), ("list_services",)),
        (re.compile(r"routes?|ingress\s+host|tls\s+termination|exposed\s+apps?", re.IGNORECASE), ("list_routes", "list_ingresses")),
        (re.compile(r"events?|warnings?|recent\s+failures?", re.IGNORECASE), ("list_events",)),
        (re.compile(r"storage|pvc|pv|persistent\s+volume|persistent\s+storage", re.IGNORECASE), ("list_persistent_storage", "list_storage_classes")),
        (re.compile(r"storage\s+classes?|default\s+storage\s+class", re.IGNORECASE), ("list_storage_classes",)),
        (re.compile(r"machine\s+config\s+pools?|mcp\b", re.IGNORECASE), ("list_machine_config_pools",)),
        (re.compile(r"machine\s+sets?|machine-api", re.IGNORECASE), ("list_machine_sets",)),
        (re.compile(r"operator\s+subscriptions?|olm\s+subscriptions?", re.IGNORECASE), ("list_operator_subscriptions",)),
        (re.compile(r"csvs?|cluster\s+service\s+versions?", re.IGNORECASE), ("list_cluster_service_versions",)),
        (re.compile(r"scc|security\s+context\s+constraints?|privileged\s+containers?", re.IGNORECASE), ("list_security_context_constraints",)),
        (re.compile(r"network\s+polic(y|ies)|ingress\s+isolation|egress\s+isolation", re.IGNORECASE), ("list_network_policies",)),
        (re.compile(r"resource\s+quotas?|cluster\s+resource\s+quotas?|quota\s+pressure", re.IGNORECASE), ("list_resource_quotas",)),
        (re.compile(r"image\s+streams?|imagestreams?", re.IGNORECASE), ("list_image_streams",)),
        (re.compile(r"builds?|buildconfigs?|pipeline\s+failures?", re.IGNORECASE), ("list_builds",)),
    )

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.load()
        self.model = OllamaClient(self.settings)
        self.toolkit = OpenShiftSreToolkit(self.settings)
        self._conversation_context: list[dict[str, str]] = []
        self._tags: list[str] = []

    def set_conversation_context(self, turns: list[dict[str, str]]) -> None:
        self._conversation_context = list(turns or [])

    def set_tags(self, tags: list[str]) -> None:
        self._tags = list(tags or [])

    def ask(self, prompt: str) -> AgentResult:
        required_tools = self._required_tools_for_prompt(prompt)
        max_steps = max(self.settings.agent_max_steps, (len(required_tools) * 3) + 4 if required_tools else self.settings.agent_max_steps)
        cli_allowed = self._prompt_allows_cli(prompt)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt(required_tools=required_tools, include_cli_tool=cli_allowed)}
        ]
        messages.extend(self._conversation_context)
        messages.append({"role": "user", "content": prompt})
        steps: list[dict[str, Any]] = []
        consecutive_unproductive_turns = 0

        for _ in range(max_steps):
            raw_response = self.model.chat(messages)
            try:
                envelope = self._parse_envelope(raw_response)
            except ValueError as error:
                steps.append({"step": len(steps) + 1, "thought": "", "tool_call": None, "final_answer": "", "tool_error": str(error)})
                consecutive_unproductive_turns += 1
                missing_tools = self._missing_required_tools(required_tools, steps)
                auto_step = self._auto_invoke_missing_required_tool(
                    missing_tools,
                    steps,
                    force=False,
                    reason="the model returned invalid JSON",
                    consecutive_unproductive_turns=consecutive_unproductive_turns,
                )
                if auto_step is not None:
                    steps.append(auto_step)
                    consecutive_unproductive_turns = 0
                    messages.extend([
                        {"role": "assistant", "content": raw_response},
                        {"role": "user", "content": self._build_auto_recovery_prompt(auto_step)},
                    ])
                    continue
                messages.extend([
                    {"role": "assistant", "content": raw_response},
                    {"role": "user", "content": f"{self._RETRY_PROMPT}\n\nValidation error: {error}"},
                ])
                continue

            step_record: dict[str, Any] = {
                "step": len(steps) + 1,
                "thought": envelope.thought,
                "tool_call": envelope.tool_call.model_dump() if envelope.tool_call else None,
                "final_answer": envelope.final_answer,
            }

            if envelope.tool_call is None:
                if not envelope.final_answer:
                    step_record["tool_error"] = "Model did not produce a tool call or a final answer"
                    steps.append(step_record)
                    consecutive_unproductive_turns += 1
                    messages.extend([
                        {"role": "assistant", "content": raw_response},
                        {"role": "user", "content": self._RETRY_PROMPT},
                    ])
                    continue
                missing_tools = self._missing_required_tools(required_tools, steps)
                if missing_tools:
                    step_record["tool_error"] = self._build_missing_tools_message(missing_tools)
                    steps.append(step_record)
                    consecutive_unproductive_turns += 1
                    auto_step = self._auto_invoke_missing_required_tool(
                        missing_tools,
                        steps,
                        force=True,
                        reason="the model tried to finalize before all explicitly requested checks were complete",
                        consecutive_unproductive_turns=consecutive_unproductive_turns,
                    )
                    if auto_step is not None:
                        steps.append(auto_step)
                        consecutive_unproductive_turns = 0
                        messages.extend([
                            {"role": "assistant", "content": raw_response},
                            {"role": "user", "content": self._build_auto_recovery_prompt(auto_step)},
                        ])
                        continue
                steps.append(step_record)
                missing_tools = self._missing_required_tools(required_tools, steps)
                return AgentResult(
                    answer=self._augment_final_answer(envelope.final_answer, steps, missing_tools),
                    steps=steps,
                    confidence=self._compute_confidence(steps),
                    token_usage=self._get_token_usage(),
                    tags=self._tags or None,
                )

            if envelope.tool_call.name == "run_read_only_oc_cli" and not cli_allowed:
                step_record["tool_error"] = (
                    "Use the named OpenShift inspection tools for this workflow. "
                    "Do not switch to run_read_only_oc_cli unless the operator explicitly asked for an oc command."
                )
                steps.append(step_record)
                messages.extend([
                    {"role": "assistant", "content": raw_response},
                    {"role": "user", "content": "Do not call run_read_only_oc_cli for this request. Use one of the named platform tools from the manifest, or provide a final answer when allowed."},
                ])
                continue

            try:
                tool_result = self.toolkit.invoke(envelope.tool_call.name, envelope.tool_call.arguments)
                step_record["tool_result"] = tool_result
                next_prompt = (
                    "Tool output for the previous step:\n"
                    f"{json.dumps(tool_result, indent=2, default=str)}\n\n"
                    "Continue and either call another tool or provide the final answer."
                )
            except Exception as error:  # noqa: BLE001
                step_record["tool_error"] = str(error)
                next_prompt = (
                    "The previous tool call failed.\n"
                    f"Error: {error}\n\n"
                    "Choose one of the available tools exactly as named in the tool list, or provide a final answer without using a tool."
                )
            steps.append(step_record)
            consecutive_unproductive_turns = 0
            messages.extend([
                {"role": "assistant", "content": raw_response},
                {"role": "user", "content": next_prompt},
            ])

        missing_tools = self._missing_required_tools(required_tools, steps)
        answer = self._build_step_limit_answer(steps, missing_tools)
        return AgentResult(
            answer=self._augment_final_answer(answer, steps, missing_tools),
            steps=steps,
            confidence=self._compute_confidence(steps),
            token_usage=self._get_token_usage(),
            tags=self._tags or None,
        )

    def _auto_invoke_missing_required_tool(
        self,
        missing_tools: list[str],
        steps: list[dict[str, Any]],
        *,
        force: bool,
        reason: str,
        consecutive_unproductive_turns: int,
    ) -> dict[str, Any] | None:
        if not missing_tools:
            return None
        if not force and consecutive_unproductive_turns < self._AUTO_INVOKE_MISSING_TOOL_AFTER_FAILURES:
            return None
        tool_name = missing_tools[0]
        step_record: dict[str, Any] = {
            "step": len(steps) + 1,
            "thought": f"Auto-recovery invoked {self._humanize_tool_name(tool_name)} because {reason}.",
            "tool_call": {"name": tool_name, "arguments": {}},
            "final_answer": "",
            "auto_recovery": True,
        }
        try:
            step_record["tool_result"] = self.toolkit.invoke(tool_name, {})
        except Exception as error:  # noqa: BLE001
            step_record["tool_error"] = str(error)
        return step_record

    @classmethod
    def _build_auto_recovery_prompt(cls, step_record: dict[str, Any]) -> str:
        tool_name = ((step_record.get("tool_call") or {}).get("name")) or "required tool"
        label = cls._humanize_tool_name(tool_name)
        if step_record.get("tool_result") is not None:
            return (
                f"The previous model turn stalled while {label} was still required, so I automatically ran that check to keep the investigation moving.\n"
                "Tool output for the recovery step:\n"
                f"{json.dumps(step_record.get('tool_result'), indent=2, default=str)}\n\n"
                "Continue from this evidence and either call the next missing required tool or provide the final answer once all explicitly requested checks have been completed."
            )
        return (
            f"The previous model turn stalled while {label} was still required, and the auto-recovery attempt for that tool failed.\n"
            f"Error: {step_record.get('tool_error', 'Unknown error')}\n\n"
            "Continue by calling the next appropriate required tool exactly as named, or explain the blocking platform error clearly in the final answer if no more progress is possible."
        )

    def _get_token_usage(self) -> dict[str, int]:
        cu = getattr(self.model, "cumulative_tokens", None)
        if cu is None:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        return {
            "prompt_tokens": int(getattr(cu, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(cu, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(cu, "total_tokens", 0) or 0),
        }

    def _system_prompt(
        self,
        *,
        required_tools: tuple[str, ...] | None = None,
        include_cli_tool: bool = False,
    ) -> str:
        manifest_names: tuple[str, ...] | None = required_tools
        if required_tools:
            selected_names = list(dict.fromkeys(required_tools))
            if include_cli_tool and "run_read_only_oc_cli" not in selected_names:
                selected_names.append("run_read_only_oc_cli")
            manifest_names = tuple(selected_names)
        manifest = self.toolkit.tool_manifest(manifest_names)
        return f"{get_system_prompt(self.settings.prompt_template)}\n\nAvailable tools:\n{json.dumps(manifest, indent=2)}"

    @staticmethod
    def _compute_confidence(steps: list[dict[str, Any]]) -> float:
        if not steps:
            return 0.0
        total = len(steps)
        successful_tool_calls = sum(1 for step in steps if step.get("tool_result") and not step.get("tool_error"))
        errors = sum(1 for step in steps if step.get("tool_error"))
        has_final = any(step.get("final_answer") for step in steps)
        score = (successful_tool_calls / max(1, total)) * 0.7
        score -= (errors / max(1, total)) * 0.3
        if has_final:
            score += 0.3
        return round(max(0.0, min(1.0, score)), 2)

    @classmethod
    def _required_tools_for_prompt(cls, prompt: str) -> tuple[str, ...]:
        required: list[str] = []
        for pattern, tool_names in cls._PROMPT_TOOL_REQUIREMENTS:
            if pattern.search(prompt):
                for tool_name in tool_names:
                    if tool_name not in required:
                        required.append(tool_name)
        return tuple(required)

    @classmethod
    def _prompt_allows_cli(cls, prompt: str) -> bool:
        return bool(cls._CLI_ALLOWED_PROMPT_PATTERN.search(prompt))

    @staticmethod
    def _missing_required_tools(required_tools: tuple[str, ...], steps: list[dict[str, Any]]) -> list[str]:
        if not required_tools:
            return []
        used_tools = {
            tool_call.get("name")
            for step in steps
            for tool_call in [step.get("tool_call") or {}]
            if tool_call.get("name")
        }
        return [tool_name for tool_name in required_tools if tool_name not in used_tools]

    @classmethod
    def _build_missing_tools_message(cls, missing_tools: list[str]) -> str:
        labels = ", ".join(cls._humanize_tool_name(tool_name) for tool_name in missing_tools)
        return f"You have not yet checked all explicitly requested platform areas. Still required: {labels}."

    @classmethod
    def _build_step_limit_answer(cls, steps: list[dict[str, Any]], missing_tools: list[str]) -> str:
        parts = ["Agent reached the configured maximum number of reasoning steps before producing a valid tool call or final answer."]
        if missing_tools:
            parts.append(cls._build_missing_tools_message(missing_tools))
        last_error = next((str(step.get("tool_error")) for step in reversed(steps) if step.get("tool_error")), "")
        if last_error:
            parts.append(f"Last issue encountered: {last_error}")
        if any("tool_result" in step for step in steps):
            parts.append("The collected platform evidence is summarized below.")
        return " ".join(parts)

    @staticmethod
    def _parse_envelope(raw_response: str) -> AgentEnvelope:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        payload = OpenShiftSreAgent._normalize_payload(OpenShiftSreAgent._decode_json_payload(cleaned))
        try:
            return AgentEnvelope.model_validate(payload)
        except ValidationError as error:
            raise ValueError(f"Model response did not match the expected schema: {payload}") from error

    @classmethod
    def _normalize_payload(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        normalized = dict(payload)
        if "thought" not in normalized:
            for key in ("reasoning", "analysis", "summary"):
                value = normalized.get(key)
                if isinstance(value, str):
                    normalized["thought"] = value
                    break
        if "final_answer" not in normalized:
            for key in ("answer", "response", "result", "final"):
                value = normalized.get(key)
                if isinstance(value, str):
                    normalized["final_answer"] = value
                    break
        if "tool_call" not in normalized or normalized.get("tool_call") is None:
            for key in ("tool", "function_call", "call"):
                if key in normalized:
                    normalized["tool_call"] = normalized.get(key)
                    break
            else:
                top_level_tool_name = next(
                    (
                        value
                        for key in ("tool_name", "tool", "action")
                        for value in [normalized.get(key)]
                        if isinstance(value, str)
                    ),
                    None,
                )
                if top_level_tool_name:
                    normalized["tool_call"] = {
                        "name": top_level_tool_name,
                        "arguments": normalized.get("arguments") or normalized.get("args") or normalized.get("parameters") or {},
                    }
        normalized["tool_call"] = cls._normalize_tool_call(normalized.get("tool_call"))
        if not isinstance(normalized.get("thought"), str):
            normalized["thought"] = ""
        if not isinstance(normalized.get("final_answer"), str):
            normalized["final_answer"] = ""
        return normalized

    @classmethod
    def _normalize_tool_call(cls, tool_call: Any) -> Any:
        if tool_call is None:
            return None
        if isinstance(tool_call, str):
            return {"name": tool_call, "arguments": {}}
        if not isinstance(tool_call, dict):
            return tool_call
        name = next(
            (
                value
                for key in ("name", "tool_name", "tool", "function", "action")
                for value in [tool_call.get(key)]
                if isinstance(value, str)
            ),
            None,
        )
        arguments = cls._normalize_tool_arguments(
            tool_call.get("arguments") or tool_call.get("args") or tool_call.get("parameters") or tool_call.get("kwargs") or tool_call.get("input") or {}
        )
        normalized = dict(tool_call)
        if name is not None:
            normalized["name"] = name
        normalized["arguments"] = arguments
        return normalized

    @staticmethod
    def _normalize_tool_arguments(arguments: Any) -> Any:
        if isinstance(arguments, str):
            stripped = arguments.strip()
            if not stripped:
                return {}
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    return parsed
            except JSONDecodeError:
                return {"input": arguments}
            return {"input": arguments}
        if arguments is None:
            return {}
        return arguments

    @staticmethod
    def _decode_json_payload(cleaned: str) -> Any:
        decoder = JSONDecoder()
        candidates = [cleaned]
        if "```json" in cleaned:
            candidates.append(cleaned.split("```json", 1)[1].split("```", 1)[0].strip())
        elif "```" in cleaned:
            candidates.append(cleaned.split("```", 1)[1].split("```", 1)[0].strip())
        first_brace = cleaned.find("{")
        if first_brace != -1:
            candidates.append(cleaned[first_brace:])
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except JSONDecodeError:
                pass
            for index, char in enumerate(candidate):
                if char != "{":
                    continue
                try:
                    payload, _ = decoder.raw_decode(candidate[index:])
                    if isinstance(payload, dict):
                        return payload
                except JSONDecodeError:
                    continue
        raise ValueError(f"Model response was not valid JSON: {cleaned}")

    @classmethod
    def _augment_final_answer(
        cls,
        final_answer: str,
        steps: list[dict[str, Any]],
        missing_tools: list[str] | None = None,
    ) -> str:
        base = final_answer.strip() or "Investigation complete."
        if "Observed platform states:" in base:
            return base
        lines = cls._build_service_state_lines(steps)
        if lines:
            base = f"{base}\n\nObserved platform states:\n" + "\n".join(f"- {line}" for line in lines)
        if missing_tools:
            labels = ", ".join(cls._humanize_tool_name(tool_name) for tool_name in missing_tools)
            base = f"{base}\n\nRemaining requested checks: {labels}."
        return base

    @classmethod
    def _build_service_state_lines(cls, steps: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        seen: set[str] = set()
        for step in steps:
            tool_call = step.get("tool_call") or {}
            tool_name = tool_call.get("name")
            if not tool_name:
                continue
            label = cls._humanize_tool_name(tool_name)
            if "tool_result" in step:
                line = cls._summarize_tool_result(tool_name, label, step["tool_result"])
            elif "tool_error" in step:
                line = f"{label}: {cls._classify_error_message(str(step['tool_error']))}"
            else:
                line = ""
            if line and line not in seen:
                seen.add(line)
                lines.append(line)
        return lines

    @classmethod
    def _summarize_tool_result(cls, tool_name: str, label: str, result: dict[str, Any]) -> str:
        error = result.get("error")
        if isinstance(error, str) and error.strip():
            return f"{label}: {cls._classify_error_message(error)}"
        count = cls._safe_int(result.get("count"))
        if tool_name == "get_cluster_identity":
            return f"{label}: active cluster {result.get('cluster', 'unknown')} via context {result.get('kube_context', 'unknown')}."
        if tool_name == "list_cluster_version":
            versions = result.get("cluster_versions") or []
            if not versions:
                return f"{label}: reachable, but no cluster version data was returned."
            item = versions[0]
            return f"{label}: cluster version {item.get('version')} on channel {item.get('channel')}, available={item.get('available')}, progressing={item.get('progressing')}, failing={item.get('failing')}."
        if tool_name == "list_cluster_operators":
            return f"{label}: returned {count} operator row(s), with {cls._safe_int(result.get('degraded_count'))} degraded and {cls._safe_int(result.get('progressing_count'))} progressing."
        if tool_name == "list_nodes":
            return f"{label}: returned {count} node row(s), with {cls._safe_int(result.get('not_ready_count'))} not ready."
        if tool_name == "list_node_pressure":
            pressure = result.get("pressure_counts") or {}
            return f"{label}: pressure summary memory={cls._safe_int(pressure.get('memory'))}, disk={cls._safe_int(pressure.get('disk'))}, pid={cls._safe_int(pressure.get('pid'))}, not_ready={cls._safe_int(pressure.get('not_ready'))}."
        if tool_name == "list_pods":
            return f"{label}: returned {count} pod row(s), with {cls._safe_int(result.get('risky_pod_count'))} risky pod(s)."
        if tool_name == "list_workload_health":
            return f"{label}: returned {count} workload row(s), with {cls._safe_int(result.get('degraded_count'))} showing rollout or readiness gaps."
        if tool_name == "list_routes":
            return f"{label}: returned {count} route row(s), with {cls._safe_int(result.get('insecure_count'))} lacking TLS configuration."
        if tool_name == "list_events":
            return f"{label}: returned {count} event row(s), with {cls._safe_int(result.get('warning_count'))} warning event(s)."
        if tool_name == "list_persistent_storage":
            return f"{label}: returned {cls._safe_int(result.get('pv_count'))} PV row(s) and {cls._safe_int(result.get('pvc_count'))} PVC row(s), with {cls._safe_int(result.get('pending_pvc_count'))} PVC(s) not bound."
        if tool_name == "list_storage_classes":
            return f"{label}: returned {count} storage class row(s), with {cls._safe_int(result.get('default_count'))} marked default."
        if tool_name == "list_machine_config_pools":
            return f"{label}: returned {count} machine config pool row(s), with {cls._safe_int(result.get('degraded_count'))} degraded."
        if tool_name == "list_operator_subscriptions":
            return f"{label}: returned {count} subscription row(s), with {cls._safe_int(result.get('unhealthy_count'))} needing follow-up."
        if tool_name == "list_cluster_service_versions":
            return f"{label}: returned {count} CSV row(s), with {cls._safe_int(result.get('failed_count'))} not in a healthy phase."
        if tool_name == "list_security_context_constraints":
            return f"{label}: returned {count} SCC row(s), with {cls._safe_int(result.get('privileged_count'))} allowing privileged containers."
        if tool_name == "list_resource_quotas":
            return f"{label}: returned {cls._safe_int(result.get('quota_count'))} resource quota row(s) and {cls._safe_int(result.get('cluster_quota_count'))} cluster resource quota row(s)."
        if tool_name == "list_builds":
            return f"{label}: returned {count} build row(s), with {cls._safe_int(result.get('failed_count'))} failed or cancelled."
        if count == 0 and "count" in result:
            return f"{label}: reachable, but no resources were returned."
        if count > 0:
            return f"{label}: returned {count} item(s)."
        return ""

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _humanize_tool_name(tool_name: str) -> str:
        name = tool_name.removeprefix("list_").removeprefix("get_").removeprefix("run_")
        label = name.replace("_", " ").strip().title()
        replacements = {
            "Scc": "SCC",
            "Csv": "CSV",
            "Oc": "oc",
            "Pvc": "PVC",
            "Pv": "PV",
            "Api": "API",
            "Olm": "OLM",
            "Mcp": "MCP",
        }
        for source, target in replacements.items():
            label = label.replace(source, target)
        return label

    @staticmethod
    def _classify_error_message(error: str) -> str:
        classification = OpenShiftSreAgent._error_classification(error)
        if classification == "auth":
            return "credentials or cluster authentication were rejected."
        if classification == "access_denied":
            return "access denied while querying the cluster."
        if classification == "not_enabled":
            return "required cluster API or extension is not available on this cluster."
        if classification == "unsupported":
            return "unsupported or unavailable in this cluster."
        return error.strip()

    @staticmethod
    def _error_classification(error: str) -> str:
        lowered = error.lower()
        if any(token in lowered for token in ["unauthorized", "authentication", "forbidden: user \"system:anonymous\"", "token has expired", "invalid bearer token"]):
            return "auth"
        if any(token in lowered for token in ["forbidden", "permission denied", "cannot list resource", "rbac"]):
            return "access_denied"
        if any(token in lowered for token in ["the server could not find the requested resource", "404", "no matches for kind", "not found in groupversion"]):
            return "not_enabled"
        if any(token in lowered for token in ["unsupported", "not implemented"]):
            return "unsupported"
        return "other"