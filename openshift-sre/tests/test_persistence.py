from datetime import datetime, timedelta, timezone

from openshift_sre_agent.persistence import HistoryStore
from openshift_sre_agent.config import Settings


def build_settings(database_url: str) -> Settings:
    return Settings(
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
        database_enabled=True,
        database_url=database_url,
        db_host=None,
        db_port=0,
        db_name=None,
        db_user=None,
        db_password=None,
    )


def test_history_store_records_runs_and_metrics(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history.db'}")
    store = HistoryStore(settings)

    run_id = store.record_chat(
        prompt="Run a FinOps drilldown.",
        answer="FinOps drilldown completed.",
        model_name="test-model",
        cluster_scope="us-east-1",
        duration_ms=1234,
        steps=[
            {
                "step": 1,
                "thought": "Check cost summary",
                "tool_call": {"name": "list_cost_and_usage_summary", "arguments": {}},
                "final_answer": "",
                "tool_result": {
                    "count": 1,
                    "days": 30,
                    "total_unblended_cost": {"amount": 125.5, "unit": "USD"},
                },
            },
            {
                "step": 2,
                "thought": "Check Security Hub findings",
                "tool_call": {"name": "list_securityhub_findings", "arguments": {}},
                "final_answer": "",
                "tool_result": {
                    "count": 2,
                    "severity_counts": {"HIGH": 1, "MEDIUM": 1},
                },
            },
        ],
    )

    assert run_id is not None

    overview = store.get_overview(run_limit=5, point_limit=5, series_limit=5)

    assert overview["enabled"] is True
    assert overview["summary"]["total_runs"] == 1
    assert overview["summary"]["metrics_recorded"] >= 4
    assert overview["recent_runs"][0]["run_id"] == run_id
    assert any(metric["metric_key"] == "list_cost_and_usage_summary.total_unblended_cost" for metric in overview["latest_metrics"])
    assert any(metric["metric_key"].startswith("list_securityhub_findings.severity_counts") for metric in overview["latest_metrics"])


def test_history_store_applies_time_range_filters(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-filtered.db'}")
    store = HistoryStore(settings)

    store.record_chat(
        prompt="Older run",
        answer="Older answer",
        model_name="test-model",
        cluster_scope="us-east-1",
        duration_ms=200,
        created_at=datetime.now(timezone.utc) - timedelta(days=45),
        steps=[
            {
                "step": 1,
                "thought": "Older check",
                "tool_call": {"name": "list_cost_and_usage_summary", "arguments": {}},
                "final_answer": "",
                "tool_result": {"count": 2},
            }
        ],
    )
    recent_run_id = store.record_chat(
        prompt="Recent run",
        answer="Recent answer",
        model_name="test-model",
        cluster_scope="us-east-1",
        duration_ms=300,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        steps=[
            {
                "step": 1,
                "thought": "Recent check",
                "tool_call": {"name": "list_securityhub_findings", "arguments": {}},
                "final_answer": "",
                "tool_result": {"count": 1, "severity_counts": {"HIGH": 1}},
            }
        ],
    )

    filtered = store.get_overview(time_range="30d", run_limit=10, point_limit=10, series_limit=10)
    unfiltered = store.get_overview(time_range="all", run_limit=10, point_limit=10, series_limit=10)

    assert filtered["filters"]["time_range"] == "30d"
    assert filtered["summary"]["total_runs"] == 1
    assert filtered["recent_runs"][0]["run_id"] == recent_run_id
    assert all(row["tool_name"] != "list_cost_and_usage_summary" for row in filtered["tool_usage"])
    assert unfiltered["summary"]["total_runs"] == 2


def test_history_store_supports_model_and_region_filters_and_breakdowns(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-breakdown.db'}")
    store = HistoryStore(settings)

    store.record_chat(
        prompt="Model A east success",
        answer="ok",
        model_name="llama3:8b",
        cluster_scope="us-east-1",
        duration_ms=210,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
        steps=[{"step": 1, "thought": "a", "tool_call": {"name": "list_cost_and_usage_summary", "arguments": {}}, "tool_result": {"count": 1}}],
    )
    store.record_chat(
        prompt="Model A west fail",
        answer="",
        model_name="llama3:8b",
        cluster_scope="us-west-2",
        duration_ms=410,
        status="failed",
        error_message="timed out",
        created_at=datetime.now(timezone.utc) - timedelta(hours=12),
        steps=[],
    )
    store.record_chat(
        prompt="Model B east success",
        answer="ok",
        model_name="gpt-oss:20b",
        cluster_scope="us-east-1",
        duration_ms=305,
        created_at=datetime.now(timezone.utc) - timedelta(hours=6),
        steps=[{"step": 1, "thought": "b", "tool_call": {"name": "list_securityhub_findings", "arguments": {}}, "tool_result": {"count": 2}}],
    )

    filtered = store.get_overview(
        time_range="all",
        model_name="llama3:8b",
        cluster_scope="us-east-1",
        run_limit=20,
        point_limit=20,
        series_limit=20,
    )
    unfiltered = store.get_overview(time_range="all", run_limit=20, point_limit=20, series_limit=20)

    assert filtered["filters"]["model_name"] == "llama3:8b"
    assert filtered["filters"]["cluster_scope"] == "us-east-1"
    assert filtered["summary"]["total_runs"] == 1
    assert filtered["recent_runs"][0]["model_name"] == "llama3:8b"
    assert filtered["recent_runs"][0]["cluster_scope"] == "us-east-1"
    assert sorted(unfiltered["filter_options"]["models"]) == ["gpt-oss:20b", "llama3:8b"]
    assert sorted(unfiltered["filter_options"]["regions"]) == ["us-east-1", "us-west-2"]
    assert {row["model_name"] for row in unfiltered["model_breakdown"]} == {"llama3:8b", "gpt-oss:20b"}
    assert {row["cluster_scope"] for row in unfiltered["region_breakdown"]} == {"us-east-1", "us-west-2"}
    llama_row = next(row for row in unfiltered["model_breakdown"] if row["model_name"] == "llama3:8b")
    assert llama_row["failed_runs"] == 1
    assert llama_row["completed_runs"] == 1
    assert llama_row["success_rate"] == 50.0


def test_history_store_supports_multi_value_tool_filters(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-multi.db'}")
    store = HistoryStore(settings)

    store.record_chat(
        prompt="Run one",
        answer="ok",
        model_name="llama3:8b",
        cluster_scope="us-east-1",
        duration_ms=111,
        steps=[
            {"step": 1, "thought": "cost", "tool_call": {"name": "list_cost_and_usage_summary", "arguments": {}}, "tool_result": {"count": 1}},
            {"step": 2, "thought": "forecast", "tool_call": {"name": "get_cost_forecast", "arguments": {}}, "tool_result": {"months": 1}},
        ],
    )
    store.record_chat(
        prompt="Run two",
        answer="ok",
        model_name="gpt-oss:20b",
        cluster_scope="us-west-2",
        duration_ms=222,
        steps=[
            {"step": 1, "thought": "security", "tool_call": {"name": "list_securityhub_findings", "arguments": {}}, "tool_result": {"count": 2}},
        ],
    )

    overview = store.get_overview(
        time_range="all",
        model_names=["llama3:8b", "gpt-oss:20b"],
        cluster_scopes=["us-east-1"],
        tool_names=["get_cost_forecast"],
        run_limit=20,
        point_limit=20,
        series_limit=20,
    )

    assert overview["summary"]["total_runs"] == 1
    assert overview["filters"]["tool_names"] == ["get_cost_forecast"]
    assert overview["filters"]["model_names"] == ["llama3:8b", "gpt-oss:20b"]
    assert overview["filters"]["cluster_scopes"] == ["us-east-1"]
    assert overview["recent_runs"][0]["model_name"] == "llama3:8b"
    assert overview["tool_usage"][0]["tool_name"] == "get_cost_forecast"
    assert "get_cost_forecast" in overview["filter_options"]["tools"]


def test_history_store_returns_storytelling_analytics_in_overview(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-storytelling.db'}")
    store = HistoryStore(settings)

    now = datetime.now(timezone.utc)
    current_week_run = store.record_chat(
        prompt="Current week success",
        answer="ok",
        model_name="llama3:8b",
        cluster_scope="us-east-1",
        duration_ms=120,
        created_at=now - timedelta(days=1),
        steps=[
            {"step": 1, "thought": "cost", "tool_call": {"name": "list_cost_and_usage_summary", "arguments": {}}, "tool_result": {"count": 1}},
        ],
    )
    assert current_week_run is not None

    store.record_chat(
        prompt="Current week failure",
        answer="",
        model_name="llama3:8b",
        cluster_scope="us-east-1",
        duration_ms=360,
        created_at=now - timedelta(days=2),
        status="failed",
        error_message="timeout while calling tool",
        steps=[],
    )
    store.record_chat(
        prompt="Last week baseline",
        answer="ok",
        model_name="llama3:8b",
        cluster_scope="us-east-1",
        duration_ms=180,
        created_at=now - timedelta(days=8),
        steps=[
            {"step": 1, "thought": "security", "tool_call": {"name": "list_securityhub_findings", "arguments": {}}, "tool_result": {"count": 2}},
        ],
    )

    overview = store.get_overview(time_range="30d", run_limit=20, point_limit=20, series_limit=20)

    percentiles = overview["summary"]["latency_percentiles_ms"]
    assert percentiles["p50"] == 180.0
    assert percentiles["p95"] == 342.0

    comparison = overview["time_window_comparison"]
    assert comparison["mode"] == "this_week_vs_last_week"
    assert comparison["current"]["total_runs"] == 2
    assert comparison["previous"]["total_runs"] == 1
    assert comparison["delta"]["total_runs"] == 1.0
    assert comparison["delta"]["success_rate"] == -50.0

    exceptions = overview["executive_exception_rollup"]
    assert any(item["title"] == "Run failures require review" for item in exceptions)
    assert any("timeout while calling tool" in item["detail"] for item in exceptions)


def test_history_store_returns_run_detail_and_tool_detail(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-detail.db'}")
    store = HistoryStore(settings)

    run_id = store.record_chat(
        prompt="Investigate cost posture",
        answer="Forecast is steady.",
        model_name="gpt-oss:20b",
        cluster_scope="us-east-1",
        duration_ms=333,
        steps=[
            {
                "step": 1,
                "thought": "Fetch forecast",
                "tool_call": {"name": "get_cost_forecast", "arguments": {"months": 1}},
                "final_answer": "",
                "tool_result": {"forecast_total": {"amount": 120.0, "unit": "USD"}, "months": 1},
            },
            {
                "step": 2,
                "thought": "Summarize",
                "tool_call": {},
                "final_answer": "Forecast is steady.",
            },
        ],
    )

    detail = store.get_run_detail(run_id or -1)
    tool_detail = store.get_tool_detail("get_cost_forecast", time_range="all")

    assert detail is not None
    assert detail["run_id"] == run_id
    assert detail["prompt"] == "Investigate cost posture"
    assert detail["steps"][0]["tool_name"] == "get_cost_forecast"
    assert detail["metrics"][0]["metric_key"].startswith("get_cost_forecast")

    assert tool_detail is not None
    assert tool_detail["tool_name"] == "get_cost_forecast"
    assert tool_detail["summary"]["invocation_count"] == 1
    assert tool_detail["summary"]["distinct_runs"] == 1
    assert tool_detail["recent_invocations"][0]["run_id"] == run_id
    assert tool_detail["latest_metrics"][0]["metric_key"].startswith("get_cost_forecast")


def test_history_store_returns_metric_detail_with_source_collection(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-metric-detail.db'}")
    store = HistoryStore(settings)

    run_id = store.record_chat(
        prompt="Check savings plan coverage",
        answer="Coverage is flat.",
        model_name="gpt-oss:20b",
        cluster_scope="us-east-1",
        duration_ms=444,
        steps=[
            {
                "step": 1,
                "thought": "Fetch savings plans coverage",
                "tool_call": {"name": "list_savings_plans_coverage", "arguments": {"days": 30}},
                "tool_result": {
                    "count": 0,
                    "days": 30,
                    "average_coverage_percentage": 0,
                    "periods": [
                        {"start": "2026-05-01", "coverage_percentage": 0},
                        {"start": "2026-05-02", "coverage_percentage": 0},
                    ],
                },
            }
        ],
    )

    metric_detail = store.get_metric_detail(
        "list_savings_plans_coverage.average_coverage_percentage",
        time_range="all",
        model_names=["gpt-oss:20b"],
        cluster_scopes=["us-east-1"],
        record_limit=10,
    )

    assert metric_detail is not None
    assert metric_detail["metric_key"] == "list_savings_plans_coverage.average_coverage_percentage"
    assert metric_detail["tool_name"] == "list_savings_plans_coverage"
    assert metric_detail["summary"]["sample_count"] == 1
    assert metric_detail["summary"]["distinct_runs"] == 1
    assert metric_detail["records"][0]["run_id"] == run_id
    assert metric_detail["records"][0]["tool_arguments"] == {"days": 30}
    assert metric_detail["records"][0]["tool_result"]["periods"][0]["start"] == "2026-05-01"
    assert metric_detail["points"][0]["metric_value"] == 0


def test_history_store_returns_disabled_payload_when_not_configured() -> None:
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

    store = HistoryStore(settings)
    overview = store.get_overview()

    assert overview["enabled"] is False
    assert overview["summary"]["total_runs"] == 0


def test_history_store_persists_finops_queue_items_and_stage_transitions(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-finops-queue.db'}")
    store = HistoryStore(settings)

    run_id = store.record_chat(
        prompt="Run a FinOps drilldown.",
        answer="Done.",
        model_name="test-model",
        cluster_scope="us-east-1",
        duration_ms=123,
        steps=[],
    )

    created = store.create_finops_queue_item(
        opportunity_key="compute-rightsize-demo",
        title="Rightsize demo workload",
        category="compute",
        estimated_monthly_savings=42.5,
        unit="USD",
        risk="medium",
        confidence="high",
        action="Review and rightsize the workload.",
        basis="Direct rightsizing recommendation",
        evidence="Projected savings from observed utilization.",
        execution_plan="Validate, approve, schedule, and rollback if needed.",
        run_id=run_id,
        auto_approve=True,
    )

    assert created is not None
    assert created["execution_stage"] == "approved"
    assert created["run_id"] == run_id

    queue_payload = store.list_finops_queue()
    assert queue_payload["enabled"] is True
    assert queue_payload["stage_counts"]["approved"] == 1
    assert queue_payload["items"][0]["title"] == "Rightsize demo workload"

    updated = store.update_finops_queue_item_stage(created["id"], "ready_for_change_window")
    assert updated is not None
    assert updated["execution_stage"] == "ready_for_change_window"

    deleted = store.delete_finops_queue_item(created["id"])
    assert deleted is True
    assert store.list_finops_queue()["items"] == []


def test_history_store_rejects_invalid_finops_stage(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-finops-stage.db'}")
    store = HistoryStore(settings)

    created = store.create_finops_queue_item(
        opportunity_key="idle-cleanup-demo",
        title="Clean up idle demo resources",
        category="idle",
        estimated_monthly_savings=12.0,
    )

    assert created is not None

    try:
        store.update_finops_queue_item_stage(created["id"], "launch_missiles")
    except ValueError as error:
        assert "Unsupported FinOps execution stage" in str(error)
    else:
        raise AssertionError("Unsupported stage should be rejected")


def test_history_store_returns_database_observability_for_sqlite(tmp_path) -> None:
    settings = build_settings(f"sqlite:///{tmp_path / 'history-observability.db'}")
    store = HistoryStore(settings)

    store.record_chat(
        prompt="Inspect persisted run schema.",
        answer="Stored.",
        model_name="test-model",
        cluster_scope="us-east-1",
        duration_ms=250,
        steps=[
            {
                "step": 1,
                "thought": "Persist one metric",
                "tool_call": {"name": "list_cost_and_usage_summary", "arguments": {}},
                "tool_result": {"count": 1},
            }
        ],
    )

    telemetry = store.get_database_observability()

    assert telemetry["enabled"] is True
    assert telemetry["dialect"] == "sqlite"
    assert telemetry["database_name"] == "history-observability.db"
    assert telemetry["utilization"]["table_count"] >= 4
    agent_runs = next(table for table in telemetry["tables"] if table["table_name"] == "agent_runs")
    assert agent_runs["row_count"] == 1
    assert "id" in agent_runs["primary_key"]
    assert any(column["name"] == "prompt" for column in agent_runs["columns"])
