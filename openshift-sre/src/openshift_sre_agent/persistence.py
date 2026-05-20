"""Persistence layer for run history, metrics, watchlists, and FinOps queue state."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from pathlib import Path
from time import sleep
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, case, create_engine, desc, func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import Settings


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base for all persistence models."""

    pass


class AgentRunRecord(Base):
    """Top-level persisted chat run including prompt, answer, timing, and token usage."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    model_name: Mapped[str] = mapped_column(String(255))
    cluster_scope: Mapped[str] = mapped_column(String(64))
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_prompt: Mapped[int] = mapped_column(Integer, default=0)
    token_completion: Mapped[int] = mapped_column(Integer, default=0)
    token_total: Mapped[int] = mapped_column(Integer, default=0)

    steps: Mapped[list["AgentStepRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    metrics: Mapped[list["MetricSnapshotRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    finops_queue_items: Mapped[list["FinopsQueueRecord"]] = relationship(back_populates="run")


class AgentStepRecord(Base):
    """Persisted reasoning step linked to a parent run and optional tool call."""

    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    step_number: Mapped[int] = mapped_column(Integer)
    thought: Mapped[str] = mapped_column(Text, default="")
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    tool_arguments_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_answer: Mapped[str] = mapped_column(Text, default="")
    tool_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    run: Mapped[AgentRunRecord] = relationship(back_populates="steps")


class MetricSnapshotRecord(Base):
    """Metric sample extracted from a tool result for historical dashboards and drilldowns."""

    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metric_key: Mapped[str] = mapped_column(String(255), index=True)
    metric_label: Mapped[str] = mapped_column(String(255))
    metric_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dimensions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    run: Mapped[AgentRunRecord] = relationship(back_populates="metrics")


class FinopsQueueRecord(Base):
    """Persisted FinOps recommendation queued for approval and staged execution planning."""

    __tablename__ = "finops_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    opportunity_key: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), index=True)
    estimated_monthly_savings: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(32), default="USD")
    execution_stage: Mapped[str] = mapped_column(String(64), default="planned", index=True)
    risk: Mapped[str] = mapped_column(String(32), default="unknown")
    confidence: Mapped[str] = mapped_column(String(32), default="unknown")
    action: Mapped[str] = mapped_column(Text, default="")
    basis: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    execution_plan: Mapped[str] = mapped_column(Text, default="")
    auto_approved: Mapped[bool] = mapped_column(default=False)
    execution_mode: Mapped[str] = mapped_column(String(128), default="future-safe-execution-plan-only")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    run: Mapped[AgentRunRecord | None] = relationship(back_populates="finops_queue_items")


class SavedInvestigationRecord(Base):
    """Reusable saved prompt definition with optional default regions, tags, and tools."""

    __tablename__ = "saved_investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="general", index=True)
    prompt: Mapped[str] = mapped_column(Text)
    default_regions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_tools_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class WatchlistRecord(Base):
    """Saved investigation bound to a repeatable regional or cross-account execution scope."""

    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    investigation_id: Mapped[int | None] = mapped_column(
        ForeignKey("saved_investigations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    schedule_hint: Mapped[str] = mapped_column(String(128), default="manual")
    regions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_arns_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ExtractedMetric:
    """Normalized metric extracted from a tool payload before persistence."""

    step_number: int | None
    tool_name: str | None
    metric_key: str
    metric_label: str
    metric_value: float
    unit: str | None = None
    dimensions: dict[str, Any] | None = None


class HistoryStore:
    """Database-backed store for runs, metrics, saved investigations, and watchlists."""

    FINOPS_QUEUE_STAGES = (
        "planned",
        "approved",
        "precheck_passed",
        "ready_for_change_window",
        "executed",
        "rolled_back",
        "deferred",
    )

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.enabled = settings.database_enabled and bool(settings.database_url)
        self._session_factory: sessionmaker | None = None
        self._engine: Engine | None = None
        self.error: str | None = None
        if not self.enabled:
            return
        self._engine = self._build_engine(settings.database_url or "")
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        try:
            self._initialize_database()
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            self.enabled = False

    @property
    def database_url(self) -> str | None:
        return self._settings.database_url

    def _build_engine(self, database_url: str) -> Engine:
        connect_args: dict[str, Any] = {}
        pool_kwargs: dict[str, Any] = {"pool_pre_ping": True, "pool_use_lifo": True}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            connect_args["timeout"] = 10
        else:
            connect_args["connect_timeout"] = 10
            pool_kwargs.update({"pool_size": 5, "max_overflow": 10, "pool_recycle": 1800, "pool_timeout": 10})
        return create_engine(database_url, connect_args=connect_args, **pool_kwargs)

    def _initialize_database(self) -> None:
        assert self._engine is not None
        last_error: Exception | None = None
        retries = 1 if (self.database_url or "").startswith("sqlite") else 15
        for attempt in range(1, retries + 1):
            try:
                Base.metadata.create_all(self._engine)
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == retries:
                    break
                sleep(min(2.0, attempt * 0.5))
        if last_error is not None:
            raise last_error

    def get_conversation_turns(self, conversation_id: str, *, limit: int = 5) -> list[dict[str, str]]:
        """Return the last *limit* prompt/answer pairs for a conversation as chat messages."""
        if not self.enabled or self._session_factory is None or not conversation_id:
            return []
        with self._session_factory() as session:
            rows = session.scalars(
                select(AgentRunRecord)
                .where(AgentRunRecord.conversation_id == conversation_id)
                .where(AgentRunRecord.status == "completed")
                .order_by(desc(AgentRunRecord.created_at))
                .limit(limit)
            ).all()
        turns: list[dict[str, str]] = []
        for run in reversed(rows):
            turns.append({"role": "user", "content": self._trim_text(run.prompt, 500)})
            turns.append({"role": "assistant", "content": self._trim_text(run.answer, 500)})
        return turns

    def record_chat(
        self,
        *,
        prompt: str,
        answer: str,
        steps: list[dict[str, Any]],
        model_name: str,
        cluster_scope: str,
        duration_ms: int,
        status: str = "completed",
        error_message: str | None = None,
        created_at: datetime | None = None,
        conversation_id: str | None = None,
        token_usage: dict[str, int] | None = None,
        tags: list[str] | None = None,
    ) -> int | None:
        if not self.enabled or self._session_factory is None:
            return None

        normalized_created_at = created_at or datetime.now(timezone.utc)
        tu = token_usage or {}
        with self._session_factory() as session:
            run = AgentRunRecord(
                prompt=prompt,
                answer=answer,
                status=status,
                model_name=model_name,
                cluster_scope=cluster_scope,
                step_count=len(steps),
                duration_ms=duration_ms,
                created_at=normalized_created_at,
                error_message=error_message,
                conversation_id=conversation_id,
                tags_json=self._json_dump(tags) if tags else None,
                token_prompt=tu.get("prompt_tokens", 0),
                token_completion=tu.get("completion_tokens", 0),
                token_total=tu.get("total_tokens", 0),
            )
            session.add(run)
            session.flush()

            for step in steps:
                tool_call = step.get("tool_call") or {}
                session.add(
                    AgentStepRecord(
                        run_id=run.id,
                        step_number=int(step.get("step") or 0),
                        thought=str(step.get("thought") or ""),
                        tool_name=tool_call.get("name"),
                        tool_arguments_json=self._json_dump(tool_call.get("arguments")),
                        final_answer=str(step.get("final_answer") or ""),
                        tool_result_json=self._json_dump(step.get("tool_result")),
                        tool_error=str(step.get("tool_error")) if step.get("tool_error") else None,
                        created_at=normalized_created_at,
                    )
                )

            for metric in self.extract_metrics(steps):
                session.add(
                    MetricSnapshotRecord(
                        run_id=run.id,
                        step_number=metric.step_number,
                        tool_name=metric.tool_name,
                        metric_key=metric.metric_key,
                        metric_label=metric.metric_label,
                        metric_value=metric.metric_value,
                        unit=metric.unit,
                        dimensions_json=self._json_dump(metric.dimensions),
                        recorded_at=normalized_created_at,
                    )
                )

            session.commit()
            return run.id

    def get_overview(
        self,
        *,
        time_range: str = "all",
        model_name: str | None = None,
        model_names: list[str] | None = None,
        cluster_scope: str | None = None,
        cluster_scopes: list[str] | None = None,
        tool_names: list[str] | None = None,
        run_limit: int = 15,
        point_limit: int = 12,
        series_limit: int = 10,
    ) -> dict[str, Any]:
        if not self.enabled or self._session_factory is None:
            return {
                "enabled": False,
                "reason": self.error or "Historical storage is not configured.",
                "recent_runs": [],
                "tool_usage": [],
                "metric_series": [],
                "latest_metrics": [],
                "summary": {
                    "total_runs": 0,
                    "failed_runs": 0,
                    "metrics_recorded": 0,
                },
            }

        since = self._resolve_since(time_range)
        normalized_model_names = self._normalize_filter_values(model_names)
        if not normalized_model_names:
            legacy_model_name = self._normalize_filter_value(model_name)
            if legacy_model_name is not None:
                normalized_model_names = [legacy_model_name]

        normalized_regions = self._normalize_filter_values(cluster_scopes)
        if not normalized_regions:
            legacy_region = self._normalize_filter_value(cluster_scope)
            if legacy_region is not None:
                normalized_regions = [legacy_region]

        normalized_tool_names = self._normalize_filter_values(tool_names)
        base_run_conditions = []
        if since is not None:
            base_run_conditions.append(AgentRunRecord.created_at >= since)

        selected_run_conditions = list(base_run_conditions)
        if normalized_model_names:
            selected_run_conditions.append(AgentRunRecord.model_name.in_(normalized_model_names))
        if normalized_regions:
            selected_run_conditions.append(AgentRunRecord.cluster_scope.in_(normalized_regions))
        if normalized_tool_names:
            selected_run_conditions.append(
                AgentRunRecord.id.in_(
                    select(AgentStepRecord.run_id).where(AgentStepRecord.tool_name.in_(normalized_tool_names))
                )
            )

        tool_option_conditions = list(base_run_conditions)
        if normalized_model_names:
            tool_option_conditions.append(AgentRunRecord.model_name.in_(normalized_model_names))
        if normalized_regions:
            tool_option_conditions.append(AgentRunRecord.cluster_scope.in_(normalized_regions))

        with self._session_factory() as session:
            total_runs_query = select(func.count(AgentRunRecord.id)).where(*selected_run_conditions)
            failed_runs_query = (
                select(func.count(AgentRunRecord.id))
                .where(*selected_run_conditions)
                .where(AgentRunRecord.status != "completed")
            )
            average_duration_query = select(func.avg(AgentRunRecord.duration_ms)).where(*selected_run_conditions)
            metrics_recorded_query = (
                select(func.count(MetricSnapshotRecord.id))
                .join(AgentRunRecord, MetricSnapshotRecord.run_id == AgentRunRecord.id)
                .where(*selected_run_conditions)
            )

            recent_runs_query = select(AgentRunRecord).where(*selected_run_conditions)
            tool_usage_query = (
                select(AgentStepRecord.tool_name, func.count(AgentStepRecord.id))
                .join(AgentRunRecord, AgentStepRecord.run_id == AgentRunRecord.id)
                .where(AgentStepRecord.tool_name.is_not(None))
                .where(*selected_run_conditions)
            )
            metric_rows_query = (
                select(MetricSnapshotRecord)
                .join(AgentRunRecord, MetricSnapshotRecord.run_id == AgentRunRecord.id)
                .where(*selected_run_conditions)
            )
            filter_models_query = (
                select(AgentRunRecord.model_name)
                .where(*base_run_conditions)
                .group_by(AgentRunRecord.model_name)
                .order_by(AgentRunRecord.model_name)
            )
            filter_regions_query = (
                select(AgentRunRecord.cluster_scope)
                .where(*base_run_conditions)
                .group_by(AgentRunRecord.cluster_scope)
                .order_by(AgentRunRecord.cluster_scope)
            )
            filter_tools_query = (
                select(AgentStepRecord.tool_name)
                .join(AgentRunRecord, AgentStepRecord.run_id == AgentRunRecord.id)
                .where(AgentStepRecord.tool_name.is_not(None))
                .where(*tool_option_conditions)
                .group_by(AgentStepRecord.tool_name)
                .order_by(AgentStepRecord.tool_name)
            )
            model_breakdown_query = (
                select(
                    AgentRunRecord.model_name.label("group_value"),
                    func.count(AgentRunRecord.id).label("total_runs"),
                    func.sum(case((AgentRunRecord.status != "completed", 1), else_=0)).label("failed_runs"),
                    func.avg(AgentRunRecord.duration_ms).label("average_duration_ms"),
                    func.max(AgentRunRecord.created_at).label("last_run_at"),
                )
                .where(*selected_run_conditions)
                .group_by(AgentRunRecord.model_name)
                .order_by(desc(func.count(AgentRunRecord.id)), AgentRunRecord.model_name)
            )
            region_breakdown_query = (
                select(
                    AgentRunRecord.cluster_scope.label("group_value"),
                    func.count(AgentRunRecord.id).label("total_runs"),
                    func.sum(case((AgentRunRecord.status != "completed", 1), else_=0)).label("failed_runs"),
                    func.avg(AgentRunRecord.duration_ms).label("average_duration_ms"),
                    func.max(AgentRunRecord.created_at).label("last_run_at"),
                )
                .where(*selected_run_conditions)
                .group_by(AgentRunRecord.cluster_scope)
                .order_by(desc(func.count(AgentRunRecord.id)), AgentRunRecord.cluster_scope)
            )

            if normalized_tool_names:
                tool_usage_query = tool_usage_query.where(AgentStepRecord.tool_name.in_(normalized_tool_names))
                metric_rows_query = metric_rows_query.where(MetricSnapshotRecord.tool_name.in_(normalized_tool_names))

            total_runs = session.scalar(total_runs_query) or 0
            failed_runs = session.scalar(failed_runs_query) or 0
            average_duration_ms = session.scalar(average_duration_query)
            metrics_recorded = session.scalar(metrics_recorded_query) or 0

            recent_runs = session.scalars(
                recent_runs_query.order_by(desc(AgentRunRecord.created_at)).limit(run_limit)
            ).all()

            selected_run_rows = session.execute(
                select(
                    AgentRunRecord.duration_ms,
                    AgentRunRecord.status,
                    AgentRunRecord.error_message,
                    AgentRunRecord.created_at,
                    AgentRunRecord.model_name,
                    AgentRunRecord.cluster_scope,
                )
                .where(*selected_run_conditions)
                .order_by(desc(AgentRunRecord.created_at))
            ).all()

            comparison_reference = selected_run_rows[0].created_at if selected_run_rows else None
            week_windows = self._resolve_week_windows(comparison_reference)

            tool_usage_rows = session.execute(
                tool_usage_query
                .group_by(AgentStepRecord.tool_name)
                .order_by(desc(func.count(AgentStepRecord.id)), AgentStepRecord.tool_name)
                .limit(20)
            ).all()

            metric_rows = session.scalars(
                metric_rows_query
                .order_by(desc(MetricSnapshotRecord.recorded_at), desc(MetricSnapshotRecord.id))
                .limit(max(series_limit * point_limit * 6, 300))
            ).all()

            available_models = [row[0] for row in session.execute(filter_models_query).all() if row[0]]
            available_regions = [row[0] for row in session.execute(filter_regions_query).all() if row[0]]
            available_tools = [row[0] for row in session.execute(filter_tools_query).all() if row[0]]
            model_breakdown_rows = session.execute(model_breakdown_query).all()
            region_breakdown_rows = session.execute(region_breakdown_query).all()
            current_week_stats = self._collect_window_stats(
                session,
                start=week_windows["current_week"]["start"],
                end=week_windows["current_week"]["end"],
                model_names=normalized_model_names,
                cluster_scopes=normalized_regions,
                tool_names=normalized_tool_names,
                label="This week",
            )
            previous_week_stats = self._collect_window_stats(
                session,
                start=week_windows["previous_week"]["start"],
                end=week_windows["previous_week"]["end"],
                model_names=normalized_model_names,
                cluster_scopes=normalized_regions,
                tool_names=normalized_tool_names,
                label="Last week",
            )

        grouped_metrics: dict[str, list[MetricSnapshotRecord]] = defaultdict(list)
        for row in metric_rows:
            grouped_metrics[row.metric_key].append(row)

        latency_percentiles = self._calculate_duration_percentiles(
            [int(row.duration_ms or 0) for row in selected_run_rows if row.duration_ms is not None]
        )
        comparison = self._build_window_comparison(current_week_stats, previous_week_stats)

        def latest_metric_sort_key(item: tuple[str, list[MetricSnapshotRecord]]) -> tuple[datetime, str]:
            latest = max(item[1], key=lambda record: record.recorded_at)
            return latest.recorded_at, item[0]

        selected_metric_groups = sorted(grouped_metrics.items(), key=latest_metric_sort_key, reverse=True)[:series_limit]

        metric_series = []
        latest_metrics = []
        for metric_key, records in selected_metric_groups:
            ordered = sorted(records, key=lambda record: record.recorded_at)
            trimmed = ordered[-point_limit:]
            if not trimmed:
                continue
            latest = trimmed[-1]
            previous_value = trimmed[-2].metric_value if len(trimmed) > 1 else None
            latest_metrics.append(
                {
                    "metric_key": latest.metric_key,
                    "metric_label": latest.metric_label,
                    "tool_name": latest.tool_name,
                    "metric_value": latest.metric_value,
                    "unit": latest.unit,
                    "dimensions": self._json_load(latest.dimensions_json),
                    "recorded_at": latest.recorded_at.isoformat(),
                    "delta_from_previous": None if previous_value is None else round(latest.metric_value - previous_value, 2),
                }
            )
            metric_series.append(
                {
                    "metric_key": metric_key,
                    "metric_label": trimmed[-1].metric_label,
                    "tool_name": trimmed[-1].tool_name,
                    "unit": trimmed[-1].unit,
                    "points": [
                        {
                            "run_id": row.run_id,
                            "recorded_at": row.recorded_at.isoformat(),
                            "metric_value": row.metric_value,
                            "dimensions": self._json_load(row.dimensions_json),
                        }
                        for row in trimmed
                    ],
                }
            )

        return {
            "enabled": True,
            "filters": {
                "time_range": time_range,
                "model_name": normalized_model_names[0] if len(normalized_model_names) == 1 else None,
                "model_names": normalized_model_names,
                "cluster_scope": normalized_regions[0] if len(normalized_regions) == 1 else None,
                "cluster_scopes": normalized_regions,
                "tool_names": normalized_tool_names,
                "applied_since": since.isoformat() if since is not None else None,
                "run_limit": run_limit,
                "point_limit": point_limit,
                "series_limit": series_limit,
            },
            "filter_options": {
                "models": available_models,
                "regions": available_regions,
                "tools": available_tools,
            },
            "summary": {
                "total_runs": total_runs,
                "failed_runs": failed_runs,
                "metrics_recorded": metrics_recorded,
                "average_duration_ms": None if average_duration_ms is None else round(float(average_duration_ms), 2),
                "last_run_at": recent_runs[0].created_at.isoformat() if recent_runs else None,
                "latency_percentiles_ms": latency_percentiles,
            },
            "recent_runs": [
                {
                    "run_id": run.id,
                    "created_at": run.created_at.isoformat(),
                    "status": run.status,
                    "model_name": run.model_name,
                    "cluster_scope": run.cluster_scope,
                    "step_count": run.step_count,
                    "duration_ms": run.duration_ms,
                    "prompt_excerpt": self._trim_text(run.prompt, 120),
                    "answer_excerpt": self._trim_text(run.answer, 140),
                    "error_message": run.error_message,
                }
                for run in recent_runs
            ],
            "tool_usage": [
                {
                    "tool_name": tool_name,
                    "count": count,
                    "label": self._humanize_tool_name(tool_name or "step"),
                }
                for tool_name, count in tool_usage_rows
            ],
            "model_breakdown": [
                self._serialize_breakdown_row("model_name", row.group_value, row.total_runs, row.failed_runs, row.average_duration_ms, row.last_run_at)
                for row in model_breakdown_rows
            ],
            "region_breakdown": [
                self._serialize_breakdown_row("cluster_scope", row.group_value, row.total_runs, row.failed_runs, row.average_duration_ms, row.last_run_at)
                for row in region_breakdown_rows
            ],
            "time_window_comparison": comparison,
            "executive_exception_rollup": self._build_exception_rollup(
                total_runs=total_runs,
                failed_runs=failed_runs,
                latency_percentiles=latency_percentiles,
                comparison=comparison,
                selected_run_rows=selected_run_rows,
                model_breakdown=[
                    self._serialize_breakdown_row("model_name", row.group_value, row.total_runs, row.failed_runs, row.average_duration_ms, row.last_run_at)
                    for row in model_breakdown_rows
                ],
                region_breakdown=[
                    self._serialize_breakdown_row("cluster_scope", row.group_value, row.total_runs, row.failed_runs, row.average_duration_ms, row.last_run_at)
                    for row in region_breakdown_rows
                ],
            ),
            "latest_metrics": latest_metrics,
            "metric_series": metric_series,
        }

    def _collect_window_stats(
        self,
        session,
        *,
        start: datetime,
        end: datetime,
        model_names: list[str] | None,
        cluster_scopes: list[str] | None,
        tool_names: list[str] | None,
        label: str,
    ) -> dict[str, Any]:
        conditions = [AgentRunRecord.created_at >= start, AgentRunRecord.created_at < end]
        if model_names:
            conditions.append(AgentRunRecord.model_name.in_(model_names))
        if cluster_scopes:
            conditions.append(AgentRunRecord.cluster_scope.in_(cluster_scopes))
        if tool_names:
            conditions.append(
                AgentRunRecord.id.in_(select(AgentStepRecord.run_id).where(AgentStepRecord.tool_name.in_(tool_names)))
            )

        rows = session.execute(
            select(
                AgentRunRecord.duration_ms,
                AgentRunRecord.status,
                AgentRunRecord.error_message,
                AgentRunRecord.created_at,
            ).where(*conditions)
        ).all()
        total_runs = len(rows)
        failed_runs = sum(1 for row in rows if row.status != "completed")
        durations = [int(row.duration_ms or 0) for row in rows if row.duration_ms is not None]
        average_duration_ms = round(sum(durations) / len(durations), 2) if durations else None
        completed_runs = max(0, total_runs - failed_runs)
        success_rate = round((completed_runs / max(1, total_runs)) * 100, 2) if total_runs else 0.0
        last_run_at = max((row.created_at for row in rows), default=None)
        return {
            "label": label,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "success_rate": success_rate,
            "average_duration_ms": average_duration_ms,
            "latency_percentiles_ms": self._calculate_duration_percentiles(durations),
            "last_run_at": last_run_at.isoformat() if last_run_at is not None else None,
        }

    @staticmethod
    def _calculate_duration_percentiles(durations: list[int]) -> dict[str, float | None]:
        ordered = sorted(value for value in durations if value is not None)
        if not ordered:
            return {"p50": None, "p90": None, "p95": None, "p99": None}

        def percentile(percent: int) -> float:
            if len(ordered) == 1:
                return round(float(ordered[0]), 2)
            position = (percent / 100) * (len(ordered) - 1)
            lower_index = int(position)
            upper_index = min(len(ordered) - 1, ceil(position))
            if lower_index == upper_index:
                return round(float(ordered[lower_index]), 2)
            lower_value = float(ordered[lower_index])
            upper_value = float(ordered[upper_index])
            weight = position - lower_index
            return round(lower_value + ((upper_value - lower_value) * weight), 2)

        return {
            "p50": percentile(50),
            "p90": percentile(90),
            "p95": percentile(95),
            "p99": percentile(99),
        }

    @staticmethod
    def _resolve_week_windows(now: datetime | None = None) -> dict[str, dict[str, datetime]]:
        reference = now or datetime.now(timezone.utc)
        current_week_end = reference + timedelta(microseconds=1)
        current_week_start = (reference - timedelta(days=7)) + timedelta(microseconds=1)
        previous_week_start = current_week_start - timedelta(days=7)
        return {
            "current_week": {"start": current_week_start, "end": current_week_end},
            "previous_week": {"start": previous_week_start, "end": current_week_start},
        }

    @staticmethod
    def _build_window_comparison(current_week: dict[str, Any], previous_week: dict[str, Any]) -> dict[str, Any]:
        def delta(current_value: float | int | None, previous_value: float | int | None) -> float | None:
            if current_value is None or previous_value is None:
                return None
            return round(float(current_value) - float(previous_value), 2)

        return {
            "mode": "this_week_vs_last_week",
            "current": current_week,
            "previous": previous_week,
            "delta": {
                "total_runs": delta(current_week.get("total_runs"), previous_week.get("total_runs")),
                "failed_runs": delta(current_week.get("failed_runs"), previous_week.get("failed_runs")),
                "success_rate": delta(current_week.get("success_rate"), previous_week.get("success_rate")),
                "average_duration_ms": delta(current_week.get("average_duration_ms"), previous_week.get("average_duration_ms")),
                "p95_duration_ms": delta(
                    current_week.get("latency_percentiles_ms", {}).get("p95"),
                    previous_week.get("latency_percentiles_ms", {}).get("p95"),
                ),
            },
        }

    @classmethod
    def _build_exception_rollup(
        cls,
        *,
        total_runs: int,
        failed_runs: int,
        latency_percentiles: dict[str, float | None],
        comparison: dict[str, Any],
        selected_run_rows: list[Any],
        model_breakdown: list[dict[str, Any]],
        region_breakdown: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rollups: list[dict[str, Any]] = []
        failure_rate = round((failed_runs / max(1, total_runs)) * 100, 2) if total_runs else 0.0
        if failed_runs > 0:
            top_error_counts: dict[str, int] = defaultdict(int)
            for row in selected_run_rows:
                if row.error_message:
                    top_error_counts[str(row.error_message).strip() or "Unknown error"] += 1
            top_error, top_error_count = next(
                iter(sorted(top_error_counts.items(), key=lambda item: item[1], reverse=True)),
                (None, 0),
            )
            rollups.append(
                {
                    "title": "Run failures require review",
                    "severity": "critical" if failure_rate >= 20 else "warning",
                    "summary": f"{failed_runs} failed runs in the current selection ({failure_rate}%).",
                    "detail": top_error and top_error_count > 0
                        and f"Most common error: {cls._trim_text(top_error, 120)} ({top_error_count} occurrence(s))."
                        or "Review the failed run drilldown to isolate the root cause.",
                }
            )

        p50 = latency_percentiles.get("p50")
        p95 = latency_percentiles.get("p95")
        if p50 and p95 and p50 > 0 and p95 >= p50 * 1.75:
            rollups.append(
                {
                    "title": "Latency tail widened",
                    "severity": "warning",
                    "summary": f"p95 latency is {round(p95 / p50, 2)}× the p50 baseline.",
                    "detail": f"p50 is {round(p50, 2)} ms while p95 is {round(p95, 2)} ms across the visible runs.",
                }
            )

        comparison_delta = comparison.get("delta", {})
        if (comparison_delta.get("success_rate") or 0) < -5 or (comparison_delta.get("average_duration_ms") or 0) > 5000:
            rollups.append(
                {
                    "title": "Week-over-week regression",
                    "severity": "warning" if (comparison_delta.get("success_rate") or 0) >= -10 else "critical",
                    "summary": (
                        f"Success rate moved {comparison_delta.get('success_rate', 0)} points and average duration moved "
                        f"{comparison_delta.get('average_duration_ms', 0)} ms versus last week."
                    ),
                    "detail": "Use the weekly comparison block to confirm whether reliability or latency shifted more materially.",
                }
            )

        hotspot = next((row for row in model_breakdown + region_breakdown if row.get("failed_runs", 0) > 0), None)
        if hotspot is not None:
            rollups.append(
                {
                    "title": "Hotspot cohort detected",
                    "severity": "warning",
                    "summary": f"{hotspot.get('label')} shows {hotspot.get('failed_runs')} failed runs across {hotspot.get('total_runs')} executions.",
                    "detail": f"Success rate for this cohort is {hotspot.get('success_rate')}% with average duration {hotspot.get('average_duration_ms') or '—'} ms.",
                }
            )

        if not rollups:
            rollups.append(
                {
                    "title": "No major exceptions in the selected window",
                    "severity": "ok",
                    "summary": "Reliability, latency, and cohort posture are within the current observable baseline.",
                    "detail": "Use the comparison and percentile panels to confirm whether you still want to call out smaller movements.",
                }
            )

        return rollups[:4]

    def get_run_detail(self, run_id: int) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None

        with self._session_factory() as session:
            run = session.get(AgentRunRecord, run_id)
            if run is None:
                return None

            steps = sorted(run.steps, key=lambda row: (row.step_number, row.id))
            metrics = sorted(run.metrics, key=lambda row: (row.recorded_at, row.id))

        return {
            "run_id": run.id,
            "created_at": run.created_at.isoformat(),
            "status": run.status,
            "model_name": run.model_name,
            "cluster_scope": run.cluster_scope,
            "duration_ms": run.duration_ms,
            "step_count": run.step_count,
            "tags": self._json_load(run.tags_json) or [],
            "prompt": run.prompt,
            "answer": run.answer,
            "error_message": run.error_message,
            "steps": [
                {
                    "step_number": step.step_number,
                    "thought": step.thought,
                    "tool_name": step.tool_name,
                    "tool_label": self._humanize_tool_name(step.tool_name or "step") if step.tool_name else None,
                    "tool_arguments": self._json_load(step.tool_arguments_json),
                    "tool_result": self._json_load(step.tool_result_json),
                    "tool_error": step.tool_error,
                    "final_answer": step.final_answer,
                    "created_at": step.created_at.isoformat(),
                }
                for step in steps
            ],
            "metrics": [
                {
                    "metric_key": metric.metric_key,
                    "metric_label": metric.metric_label,
                    "tool_name": metric.tool_name,
                    "metric_value": metric.metric_value,
                    "unit": metric.unit,
                    "dimensions": self._json_load(metric.dimensions_json),
                    "recorded_at": metric.recorded_at.isoformat(),
                }
                for metric in metrics
            ],
        }

    def get_tool_detail(
        self,
        tool_name: str,
        *,
        time_range: str = "all",
        model_names: list[str] | None = None,
        cluster_scopes: list[str] | None = None,
        run_limit: int = 20,
        point_limit: int = 24,
    ) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None

        normalized_tool_name = self._normalize_filter_value(tool_name)
        if normalized_tool_name is None:
            return None

        since = self._resolve_since(time_range)
        normalized_model_names = self._normalize_filter_values(model_names)
        normalized_regions = self._normalize_filter_values(cluster_scopes)

        base_run_conditions = []
        if since is not None:
            base_run_conditions.append(AgentRunRecord.created_at >= since)
        if normalized_model_names:
            base_run_conditions.append(AgentRunRecord.model_name.in_(normalized_model_names))
        if normalized_regions:
            base_run_conditions.append(AgentRunRecord.cluster_scope.in_(normalized_regions))

        with self._session_factory() as session:
            invocation_rows = session.execute(
                select(AgentStepRecord, AgentRunRecord)
                .join(AgentRunRecord, AgentStepRecord.run_id == AgentRunRecord.id)
                .where(AgentStepRecord.tool_name == normalized_tool_name)
                .where(*base_run_conditions)
                .order_by(desc(AgentStepRecord.created_at), desc(AgentStepRecord.id))
                .limit(run_limit)
            ).all()

            if not invocation_rows:
                return None

            count_query = (
                select(
                    func.count(AgentStepRecord.id),
                    func.count(func.distinct(AgentStepRecord.run_id)),
                    func.sum(case((AgentStepRecord.tool_error.is_not(None), 1), else_=0)),
                    func.avg(AgentRunRecord.duration_ms),
                    func.max(AgentStepRecord.created_at),
                )
                .join(AgentRunRecord, AgentStepRecord.run_id == AgentRunRecord.id)
                .where(AgentStepRecord.tool_name == normalized_tool_name)
                .where(*base_run_conditions)
            )
            metric_rows = session.scalars(
                select(MetricSnapshotRecord)
                .join(AgentRunRecord, MetricSnapshotRecord.run_id == AgentRunRecord.id)
                .where(MetricSnapshotRecord.tool_name == normalized_tool_name)
                .where(*base_run_conditions)
                .order_by(desc(MetricSnapshotRecord.recorded_at), desc(MetricSnapshotRecord.id))
                .limit(max(point_limit * 8, 200))
            ).all()
            available_models = [
                row[0]
                for row in session.execute(
                    select(AgentRunRecord.model_name)
                    .join(AgentStepRecord, AgentStepRecord.run_id == AgentRunRecord.id)
                    .where(AgentStepRecord.tool_name == normalized_tool_name)
                    .where(*( [AgentRunRecord.created_at >= since] if since is not None else [] ))
                    .group_by(AgentRunRecord.model_name)
                    .order_by(AgentRunRecord.model_name)
                ).all()
                if row[0]
            ]
            available_regions = [
                row[0]
                for row in session.execute(
                    select(AgentRunRecord.cluster_scope)
                    .join(AgentStepRecord, AgentStepRecord.run_id == AgentRunRecord.id)
                    .where(AgentStepRecord.tool_name == normalized_tool_name)
                    .where(*( [AgentRunRecord.created_at >= since] if since is not None else [] ))
                    .group_by(AgentRunRecord.cluster_scope)
                    .order_by(AgentRunRecord.cluster_scope)
                ).all()
                if row[0]
            ]

            invocation_count, distinct_runs, failed_invocations, average_duration_ms, last_invoked_at = session.execute(count_query).one()

        grouped_metrics: dict[str, list[MetricSnapshotRecord]] = defaultdict(list)
        for row in metric_rows:
            grouped_metrics[row.metric_key].append(row)

        metric_series = []
        latest_metrics = []
        for metric_key, records in sorted(grouped_metrics.items(), key=lambda item: max(record.recorded_at for record in item[1]), reverse=True):
            ordered = sorted(records, key=lambda record: record.recorded_at)
            trimmed = ordered[-point_limit:]
            if not trimmed:
                continue
            latest = trimmed[-1]
            latest_metrics.append(
                {
                    "metric_key": latest.metric_key,
                    "metric_label": latest.metric_label,
                    "metric_value": latest.metric_value,
                    "unit": latest.unit,
                    "dimensions": self._json_load(latest.dimensions_json),
                    "recorded_at": latest.recorded_at.isoformat(),
                }
            )
            metric_series.append(
                {
                    "metric_key": metric_key,
                    "metric_label": latest.metric_label,
                    "unit": latest.unit,
                    "points": [
                        {
                            "run_id": record.run_id,
                            "recorded_at": record.recorded_at.isoformat(),
                            "metric_value": record.metric_value,
                            "dimensions": self._json_load(record.dimensions_json),
                        }
                        for record in trimmed
                    ],
                }
            )

        return {
            "tool_name": normalized_tool_name,
            "tool_label": self._humanize_tool_name(normalized_tool_name),
            "filters": {
                "time_range": time_range,
                "model_names": normalized_model_names,
                "cluster_scopes": normalized_regions,
                "applied_since": since.isoformat() if since is not None else None,
            },
            "filter_options": {
                "models": available_models,
                "regions": available_regions,
            },
            "summary": {
                "invocation_count": int(invocation_count or 0),
                "distinct_runs": int(distinct_runs or 0),
                "failed_invocations": int(failed_invocations or 0),
                "average_duration_ms": None if average_duration_ms is None else round(float(average_duration_ms), 2),
                "last_invoked_at": last_invoked_at.isoformat() if last_invoked_at is not None else None,
            },
            "recent_invocations": [
                {
                    "run_id": run.id,
                    "created_at": step.created_at.isoformat(),
                    "run_created_at": run.created_at.isoformat(),
                    "status": run.status,
                    "model_name": run.model_name,
                    "cluster_scope": run.cluster_scope,
                    "duration_ms": run.duration_ms,
                    "thought": step.thought,
                    "tool_arguments": self._json_load(step.tool_arguments_json),
                    "tool_result": self._json_load(step.tool_result_json),
                    "tool_error": step.tool_error,
                    "prompt_excerpt": self._trim_text(run.prompt, 120),
                }
                for step, run in invocation_rows
            ],
            "latest_metrics": latest_metrics,
            "metric_series": metric_series,
        }

    def get_metric_detail(
        self,
        metric_key: str,
        *,
        time_range: str = "all",
        model_names: list[str] | None = None,
        cluster_scopes: list[str] | None = None,
        record_limit: int = 40,
    ) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None

        normalized_metric_key = self._normalize_filter_value(metric_key)
        if normalized_metric_key is None:
            return None

        since = self._resolve_since(time_range)
        normalized_model_names = self._normalize_filter_values(model_names)
        normalized_regions = self._normalize_filter_values(cluster_scopes)

        base_run_conditions = []
        if since is not None:
            base_run_conditions.append(AgentRunRecord.created_at >= since)
        if normalized_model_names:
            base_run_conditions.append(AgentRunRecord.model_name.in_(normalized_model_names))
        if normalized_regions:
            base_run_conditions.append(AgentRunRecord.cluster_scope.in_(normalized_regions))

        with self._session_factory() as session:
            metric_rows = session.execute(
                select(MetricSnapshotRecord, AgentRunRecord)
                .join(AgentRunRecord, MetricSnapshotRecord.run_id == AgentRunRecord.id)
                .where(MetricSnapshotRecord.metric_key == normalized_metric_key)
                .where(*base_run_conditions)
                .order_by(desc(MetricSnapshotRecord.recorded_at), desc(MetricSnapshotRecord.id))
                .limit(max(record_limit * 3, 120))
            ).all()

            if not metric_rows:
                return None

            latest_metric = metric_rows[0][0]
            run_ids = {metric.run_id for metric, _ in metric_rows}
            step_numbers = {metric.step_number for metric, _ in metric_rows if metric.step_number is not None}
            step_query = select(AgentStepRecord).where(AgentStepRecord.run_id.in_(run_ids))
            if latest_metric.tool_name is not None:
                step_query = step_query.where(AgentStepRecord.tool_name == latest_metric.tool_name)
            if step_numbers:
                step_query = step_query.where(AgentStepRecord.step_number.in_(step_numbers))
            step_rows = session.scalars(step_query).all()

        exact_step_map = {(step.run_id, step.step_number): step for step in step_rows}
        fallback_step_map: dict[int, AgentStepRecord] = {}
        for step in step_rows:
            fallback_step_map.setdefault(step.run_id, step)

        recent_records = []
        values: list[float] = []
        distinct_runs: set[int] = set()
        ascending_points: list[dict[str, Any]] = []
        for metric, run in metric_rows:
            values.append(metric.metric_value)
            distinct_runs.add(run.id)
            step = exact_step_map.get((metric.run_id, metric.step_number)) or fallback_step_map.get(metric.run_id)
            serialized_record = {
                "run_id": run.id,
                "step_number": metric.step_number,
                "recorded_at": metric.recorded_at.isoformat(),
                "metric_value": metric.metric_value,
                "dimensions": self._json_load(metric.dimensions_json),
                "status": run.status,
                "model_name": run.model_name,
                "cluster_scope": run.cluster_scope,
                "duration_ms": run.duration_ms,
                "prompt_excerpt": self._trim_text(run.prompt, 120),
                "tool_arguments": self._json_load(step.tool_arguments_json) if step is not None else None,
                "tool_result": self._json_load(step.tool_result_json) if step is not None else None,
                "tool_error": step.tool_error if step is not None else None,
                "thought": step.thought if step is not None else None,
            }
            if len(recent_records) < record_limit:
                recent_records.append(serialized_record)
            ascending_points.append(serialized_record)

        ascending_points.reverse()
        min_value = min(values)
        max_value = max(values)
        average_value = round(sum(values) / len(values), 2) if values else None

        return {
            "metric_key": normalized_metric_key,
            "metric_label": latest_metric.metric_label,
            "tool_name": latest_metric.tool_name,
            "tool_label": self._humanize_tool_name(latest_metric.tool_name) if latest_metric.tool_name else None,
            "unit": latest_metric.unit,
            "filters": {
                "time_range": time_range,
                "model_names": normalized_model_names,
                "cluster_scopes": normalized_regions,
                "applied_since": since.isoformat() if since is not None else None,
                "record_limit": record_limit,
            },
            "summary": {
                "sample_count": len(metric_rows),
                "distinct_runs": len(distinct_runs),
                "min_value": min_value,
                "max_value": max_value,
                "average_value": average_value,
                "latest_value": latest_metric.metric_value,
                "latest_recorded_at": latest_metric.recorded_at.isoformat(),
            },
            "records": recent_records,
            "points": [
                {
                    "run_id": record["run_id"],
                    "recorded_at": record["recorded_at"],
                    "metric_value": record["metric_value"],
                    "dimensions": record["dimensions"],
                }
                for record in ascending_points[-record_limit:]
            ],
        }

    def list_finops_queue(self) -> dict[str, Any]:
        if not self.enabled or self._session_factory is None:
            return {
                "enabled": False,
                "reason": self.error or "Historical storage is not configured.",
                "items": [],
                "stage_counts": {},
            }

        with self._session_factory() as session:
            rows = session.scalars(
                select(FinopsQueueRecord).order_by(desc(FinopsQueueRecord.updated_at), desc(FinopsQueueRecord.id))
            ).all()

        stage_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            stage_counts[row.execution_stage] += 1

        return {
            "enabled": True,
            "stage_counts": dict(stage_counts),
            "items": [self._serialize_finops_queue_item(row) for row in rows],
        }

    def create_finops_queue_item(
        self,
        *,
        opportunity_key: str,
        title: str,
        category: str,
        estimated_monthly_savings: float,
        unit: str = "USD",
        risk: str = "unknown",
        confidence: str = "unknown",
        action: str = "",
        basis: str = "",
        evidence: str = "",
        execution_plan: str = "",
        run_id: int | None = None,
        auto_approve: bool = False,
        execution_mode: str = "future-safe-execution-plan-only",
    ) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None

        now = datetime.now(timezone.utc)
        execution_stage = "approved" if auto_approve else "planned"

        with self._session_factory() as session:
            if run_id is not None and session.get(AgentRunRecord, run_id) is None:
                raise LookupError(f"Run not found: {run_id}")

            record = FinopsQueueRecord(
                run_id=run_id,
                opportunity_key=opportunity_key,
                title=title,
                category=category,
                estimated_monthly_savings=float(estimated_monthly_savings or 0.0),
                unit=unit or "USD",
                execution_stage=execution_stage,
                risk=risk or "unknown",
                confidence=confidence or "unknown",
                action=action or "",
                basis=basis or "",
                evidence=evidence or "",
                execution_plan=execution_plan or "",
                auto_approved=auto_approve,
                execution_mode=execution_mode or "future-safe-execution-plan-only",
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._serialize_finops_queue_item(record)

    def update_finops_queue_item_stage(self, item_id: int, execution_stage: str) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None

        normalized_stage = self._normalize_filter_value(execution_stage)
        if normalized_stage not in self.FINOPS_QUEUE_STAGES:
            raise ValueError(f"Unsupported FinOps execution stage: {execution_stage}")

        with self._session_factory() as session:
            record = session.get(FinopsQueueRecord, item_id)
            if record is None:
                return None
            record.execution_stage = normalized_stage or "planned"
            record.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(record)
            return self._serialize_finops_queue_item(record)

    def delete_finops_queue_item(self, item_id: int) -> bool:
        if not self.enabled or self._session_factory is None:
            return False

        with self._session_factory() as session:
            record = session.get(FinopsQueueRecord, item_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True

    def list_saved_investigations(self) -> dict[str, Any]:
        if not self.enabled or self._session_factory is None:
            return {"enabled": False, "reason": self.error or "Historical storage is not configured.", "items": []}

        with self._session_factory() as session:
            rows = session.scalars(
                select(SavedInvestigationRecord).order_by(SavedInvestigationRecord.category, SavedInvestigationRecord.name)
            ).all()
        return {"enabled": True, "items": [self._serialize_saved_investigation(row) for row in rows]}

    def create_saved_investigation(
        self,
        *,
        name: str,
        prompt: str,
        description: str = "",
        category: str = "general",
        default_regions: list[str] | None = None,
        default_tags: list[str] | None = None,
        default_tools: list[str] | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            record = SavedInvestigationRecord(
                name=name,
                prompt=prompt,
                description=description or "",
                category=category or "general",
                default_regions_json=self._json_dump(default_regions),
                default_tags_json=self._json_dump(default_tags),
                default_tools_json=self._json_dump(default_tools),
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._serialize_saved_investigation(record)

    def update_saved_investigation(self, investigation_id: int, **changes: Any) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None
        with self._session_factory() as session:
            record = session.get(SavedInvestigationRecord, investigation_id)
            if record is None:
                return None
            if "name" in changes and changes["name"] is not None:
                record.name = str(changes["name"])
            if "prompt" in changes and changes["prompt"] is not None:
                record.prompt = str(changes["prompt"])
            if "description" in changes and changes["description"] is not None:
                record.description = str(changes["description"])
            if "category" in changes and changes["category"] is not None:
                record.category = str(changes["category"])
            if "default_regions" in changes:
                record.default_regions_json = self._json_dump(changes.get("default_regions"))
            if "default_tags" in changes:
                record.default_tags_json = self._json_dump(changes.get("default_tags"))
            if "default_tools" in changes:
                record.default_tools_json = self._json_dump(changes.get("default_tools"))
            record.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(record)
            return self._serialize_saved_investigation(record)

    def delete_saved_investigation(self, investigation_id: int) -> bool:
        if not self.enabled or self._session_factory is None:
            return False
        with self._session_factory() as session:
            record = session.get(SavedInvestigationRecord, investigation_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True

    def list_watchlists(self) -> dict[str, Any]:
        if not self.enabled or self._session_factory is None:
            return {"enabled": False, "reason": self.error or "Historical storage is not configured.", "items": []}

        with self._session_factory() as session:
            rows = session.scalars(select(WatchlistRecord).order_by(desc(WatchlistRecord.updated_at), desc(WatchlistRecord.id))).all()
            investigations = {
                row.id: row
                for row in session.scalars(select(SavedInvestigationRecord)).all()
            }
        return {
            "enabled": True,
            "items": [self._serialize_watchlist(row, investigations.get(row.investigation_id)) for row in rows],
        }

    def create_watchlist(
        self,
        *,
        name: str,
        investigation_id: int | None = None,
        notes: str = "",
        schedule_hint: str = "manual",
        regions: list[str] | None = None,
        role_arns: list[str] | None = None,
        tags: list[str] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            if investigation_id is not None and session.get(SavedInvestigationRecord, investigation_id) is None:
                raise LookupError(f"Saved investigation not found: {investigation_id}")
            record = WatchlistRecord(
                name=name,
                investigation_id=investigation_id,
                notes=notes or "",
                schedule_hint=schedule_hint or "manual",
                regions_json=self._json_dump(regions),
                role_arns_json=self._json_dump(role_arns),
                tags_json=self._json_dump(tags),
                enabled=bool(enabled),
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            investigation = session.get(SavedInvestigationRecord, record.investigation_id) if record.investigation_id else None
            return self._serialize_watchlist(record, investigation)

    def update_watchlist(self, watchlist_id: int, **changes: Any) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None
        with self._session_factory() as session:
            record = session.get(WatchlistRecord, watchlist_id)
            if record is None:
                return None
            if "investigation_id" in changes and changes["investigation_id"] is not None:
                if session.get(SavedInvestigationRecord, int(changes["investigation_id"])) is None:
                    raise LookupError(f"Saved investigation not found: {changes['investigation_id']}")
                record.investigation_id = int(changes["investigation_id"])
            elif "investigation_id" in changes:
                record.investigation_id = None
            if "name" in changes and changes["name"] is not None:
                record.name = str(changes["name"])
            if "notes" in changes and changes["notes"] is not None:
                record.notes = str(changes["notes"])
            if "schedule_hint" in changes and changes["schedule_hint"] is not None:
                record.schedule_hint = str(changes["schedule_hint"])
            if "regions" in changes:
                record.regions_json = self._json_dump(changes.get("regions"))
            if "role_arns" in changes:
                record.role_arns_json = self._json_dump(changes.get("role_arns"))
            if "tags" in changes:
                record.tags_json = self._json_dump(changes.get("tags"))
            if "enabled" in changes and changes["enabled"] is not None:
                record.enabled = bool(changes["enabled"])
            record.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(record)
            investigation = session.get(SavedInvestigationRecord, record.investigation_id) if record.investigation_id else None
            return self._serialize_watchlist(record, investigation)

    def delete_watchlist(self, watchlist_id: int) -> bool:
        if not self.enabled or self._session_factory is None:
            return False
        with self._session_factory() as session:
            record = session.get(WatchlistRecord, watchlist_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True

    def touch_watchlist_run(self, watchlist_id: int, run_id: int | None) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None
        with self._session_factory() as session:
            record = session.get(WatchlistRecord, watchlist_id)
            if record is None:
                return None
            record.last_run_id = run_id
            record.last_run_at = datetime.now(timezone.utc)
            record.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(record)
            investigation = session.get(SavedInvestigationRecord, record.investigation_id) if record.investigation_id else None
            return self._serialize_watchlist(record, investigation)

    def get_watchlist(self, watchlist_id: int) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None
        with self._session_factory() as session:
            record = session.get(WatchlistRecord, watchlist_id)
            if record is None:
                return None
            investigation = session.get(SavedInvestigationRecord, record.investigation_id) if record.investigation_id else None
            return self._serialize_watchlist(record, investigation)

    def get_database_observability(self) -> dict[str, Any]:
        """Return database utilization, table inventory, and schema details for console telemetry."""

        if not self.enabled or self._engine is None:
            return {
                "enabled": False,
                "reason": self.error or "Historical storage is not configured.",
                "tables": [],
                "utilization": {
                    "table_count": 0,
                    "database_size_bytes": None,
                    "free_bytes": None,
                },
            }

        pool = self._engine.pool
        pool_snapshot = {
            "class_name": pool.__class__.__name__,
            "size": pool.size() if hasattr(pool, "size") else None,
            "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else None,
            "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else None,
            "overflow": pool.overflow() if hasattr(pool, "overflow") else None,
        }

        with self._engine.connect() as connection:
            dialect = connection.dialect.name
            inspector = inspect(connection)
            table_names = inspector.get_table_names()
            identifier_preparer = connection.dialect.identifier_preparer
            mysql_table_meta: dict[str, Any] = {}
            runtime_stats: dict[str, Any] = {}
            database_name: str | None = None
            version: str | None = None
            storage_path: str | None = None
            database_size_bytes: int | None = None
            free_bytes: int | None = None

            if dialect == "sqlite":
                parsed = urlparse(self.database_url or "")
                if parsed.path:
                    storage_path = parsed.path
                    database_name = Path(parsed.path).name
                    if Path(parsed.path).exists():
                        database_size_bytes = Path(parsed.path).stat().st_size
                version = connection.execute(text("select sqlite_version()")) .scalar_one_or_none()
                page_size = connection.execute(text("PRAGMA page_size")).scalar_one_or_none()
                page_count = connection.execute(text("PRAGMA page_count")).scalar_one_or_none()
                freelist_count = connection.execute(text("PRAGMA freelist_count")).scalar_one_or_none()
                if database_size_bytes is None and page_size is not None and page_count is not None:
                    database_size_bytes = int(page_size) * int(page_count)
                if page_size is not None and freelist_count is not None:
                    free_bytes = int(page_size) * int(freelist_count)
                runtime_stats = {
                    "page_size_bytes": page_size,
                    "page_count": page_count,
                    "free_page_count": freelist_count,
                }
            else:
                database_name = connection.execute(text("SELECT DATABASE()")) .scalar_one_or_none() or self._settings.db_name
                version = connection.execute(text("SELECT VERSION()")) .scalar_one_or_none()
                mysql_rows = connection.execute(
                    text(
                        """
                        SELECT
                            table_name,
                            engine,
                            table_rows,
                            data_length,
                            index_length,
                            data_free,
                            auto_increment,
                            create_time,
                            update_time
                        FROM information_schema.tables
                        WHERE table_schema = DATABASE()
                        ORDER BY (data_length + index_length) DESC, table_name
                        """
                    )
                ).mappings().all()
                mysql_table_meta = {row["table_name"]: dict(row) for row in mysql_rows}
                size_row = connection.execute(
                    text(
                        """
                        SELECT
                            COALESCE(SUM(data_length + index_length), 0) AS database_size_bytes,
                            COALESCE(SUM(data_free), 0) AS free_bytes
                        FROM information_schema.tables
                        WHERE table_schema = DATABASE()
                        """
                    )
                ).mappings().first()
                if size_row is not None:
                    database_size_bytes = int(size_row.get("database_size_bytes") or 0)
                    free_bytes = int(size_row.get("free_bytes") or 0)
                try:
                    status_rows = connection.execute(
                        text(
                            """
                            SHOW GLOBAL STATUS WHERE Variable_name IN (
                                'Threads_connected',
                                'Threads_running',
                                'Uptime',
                                'Questions',
                                'Queries',
                                'Bytes_received',
                                'Bytes_sent'
                            )
                            """
                        )
                    ).all()
                    runtime_stats = {
                        row[0].lower(): int(row[1]) if str(row[1]).isdigit() else row[1]
                        for row in status_rows
                    }
                except Exception:
                    runtime_stats = {}

            tables: list[dict[str, Any]] = []
            for table_name in table_names:
                quoted_name = identifier_preparer.quote_identifier(table_name)
                row_count = connection.execute(text(f"SELECT COUNT(*) FROM {quoted_name}")).scalar_one()
                columns = [
                    {
                        "name": column.get("name"),
                        "type": str(column.get("type")),
                        "nullable": bool(column.get("nullable", True)),
                        "default": None if column.get("default") is None else str(column.get("default")),
                    }
                    for column in inspector.get_columns(table_name)
                ]
                indexes = [
                    {
                        "name": index.get("name"),
                        "unique": bool(index.get("unique", False)),
                        "columns": list(index.get("column_names") or []),
                    }
                    for index in inspector.get_indexes(table_name)
                ]
                primary_key = list((inspector.get_pk_constraint(table_name) or {}).get("constrained_columns") or [])
                table_payload = {
                    "table_name": table_name,
                    "row_count": int(row_count or 0),
                    "columns": columns,
                    "indexes": indexes,
                    "primary_key": primary_key,
                    "size_bytes": None,
                    "data_size_bytes": None,
                    "index_size_bytes": None,
                    "free_bytes": None,
                    "engine": None,
                    "created_at": None,
                    "updated_at": None,
                    "auto_increment": None,
                }
                if dialect == "sqlite":
                    try:
                        approx_size = connection.execute(
                            text("SELECT COALESCE(SUM(pgsize), 0) FROM dbstat WHERE name = :table_name"),
                            {"table_name": table_name},
                        ).scalar_one_or_none()
                    except Exception:
                        approx_size = None
                    if approx_size is not None:
                        table_payload["size_bytes"] = int(approx_size)
                else:
                    meta = mysql_table_meta.get(table_name, {})
                    data_length = int(meta.get("data_length") or 0)
                    index_length = int(meta.get("index_length") or 0)
                    table_payload.update(
                        {
                            "engine": meta.get("engine"),
                            "row_count_estimate": int(meta.get("table_rows") or 0),
                            "data_size_bytes": data_length,
                            "index_size_bytes": index_length,
                            "size_bytes": data_length + index_length,
                            "free_bytes": int(meta.get("data_free") or 0),
                            "created_at": meta.get("create_time").isoformat() if meta.get("create_time") else None,
                            "updated_at": meta.get("update_time").isoformat() if meta.get("update_time") else None,
                            "auto_increment": meta.get("auto_increment"),
                        }
                    )
                tables.append(table_payload)

        run_table = next((table for table in tables if table["table_name"] == "agent_runs"), None)
        latest_run_count = run_table["row_count"] if run_table is not None else 0
        tables.sort(key=lambda table: ((table.get("size_bytes") or 0), table["row_count"], table["table_name"]), reverse=True)
        return {
            "enabled": True,
            "dialect": dialect,
            "database_name": database_name,
            "version": version,
            "storage_path": storage_path,
            "utilization": {
                "table_count": len(tables),
                "database_size_bytes": database_size_bytes,
                "free_bytes": free_bytes,
                "tracked_run_count": latest_run_count,
                "runtime_stats": runtime_stats,
                "pool": pool_snapshot,
            },
            "tables": tables,
        }

    def compare_runs(self, left_run_id: int, right_run_id: int) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None
        left = self.get_run_detail(left_run_id)
        right = self.get_run_detail(right_run_id)
        if left is None or right is None:
            return None

        def numeric_metrics(detail: dict[str, Any]) -> dict[str, float]:
            return {
                metric["metric_key"]: float(metric["metric_value"])
                for metric in detail.get("metrics", [])
                if isinstance(metric.get("metric_value"), (int, float))
            }

        left_metrics = numeric_metrics(left)
        right_metrics = numeric_metrics(right)
        metric_deltas = []
        for metric_key in sorted(set(left_metrics) | set(right_metrics)):
            left_value = left_metrics.get(metric_key)
            right_value = right_metrics.get(metric_key)
            metric_deltas.append(
                {
                    "metric_key": metric_key,
                    "left_value": left_value,
                    "right_value": right_value,
                    "delta": None if left_value is None or right_value is None else round(right_value - left_value, 2),
                }
            )

        left_tools = [step.get("tool_name") for step in left.get("steps", []) if step.get("tool_name")]
        right_tools = [step.get("tool_name") for step in right.get("steps", []) if step.get("tool_name")]
        return {
            "left": {
                "run_id": left["run_id"],
                "created_at": left["created_at"],
                "status": left["status"],
                "model_name": left["model_name"],
                "cluster_scope": left["cluster_scope"],
                "duration_ms": left["duration_ms"],
                "step_count": left["step_count"],
            },
            "right": {
                "run_id": right["run_id"],
                "created_at": right["created_at"],
                "status": right["status"],
                "model_name": right["model_name"],
                "cluster_scope": right["cluster_scope"],
                "duration_ms": right["duration_ms"],
                "step_count": right["step_count"],
            },
            "summary": {
                "duration_delta_ms": round((right.get("duration_ms") or 0) - (left.get("duration_ms") or 0), 2),
                "step_delta": int(right.get("step_count") or 0) - int(left.get("step_count") or 0),
                "tool_added": sorted(set(right_tools) - set(left_tools)),
                "tool_removed": sorted(set(left_tools) - set(right_tools)),
                "tag_delta": {
                    "added": sorted(set(right.get("tags") or []) - set(left.get("tags") or [])),
                    "removed": sorted(set(left.get("tags") or []) - set(right.get("tags") or [])),
                },
            },
            "metric_deltas": metric_deltas,
        }

    @staticmethod
    def _resolve_since(time_range: str) -> datetime | None:
        normalized = (time_range or "all").strip().lower()
        if normalized == "all":
            return None
        windows = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
        }
        delta = windows.get(normalized)
        if delta is None:
            return None
        return datetime.now(timezone.utc) - delta

    @staticmethod
    def _normalize_filter_value(value: str | None) -> str | None:
        normalized = (value or "").strip()
        if normalized == "" or normalized.lower() in {"all", "any"}:
            return None
        return normalized

    @classmethod
    def _normalize_filter_values(cls, values: list[str] | None) -> list[str]:
        normalized: list[str] = []
        for value in values or []:
            item = cls._normalize_filter_value(value)
            if item and item not in normalized:
                normalized.append(item)
        return normalized

    @staticmethod
    def _serialize_breakdown_row(
        key_name: str,
        key_value: str | None,
        total_runs: int,
        failed_runs: int,
        average_duration_ms: float | None,
        last_run_at: datetime | None,
    ) -> dict[str, Any]:
        completed_runs = max(0, int(total_runs or 0) - int(failed_runs or 0))
        safe_total = max(1, int(total_runs or 0))
        return {
            key_name: key_value,
            "label": key_value or "Unknown",
            "total_runs": int(total_runs or 0),
            "completed_runs": completed_runs,
            "failed_runs": int(failed_runs or 0),
            "success_rate": round((completed_runs / safe_total) * 100, 2) if total_runs else 0.0,
            "average_duration_ms": None if average_duration_ms is None else round(float(average_duration_ms), 2),
            "last_run_at": last_run_at.isoformat() if last_run_at is not None else None,
        }

    @classmethod
    def _serialize_saved_investigation(cls, row: SavedInvestigationRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "category": row.category,
            "prompt": row.prompt,
            "default_regions": cls._json_load(row.default_regions_json) or [],
            "default_tags": cls._json_load(row.default_tags_json) or [],
            "default_tools": cls._json_load(row.default_tools_json) or [],
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @classmethod
    def _serialize_watchlist(
        cls,
        row: WatchlistRecord,
        investigation: SavedInvestigationRecord | None,
    ) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "investigation_id": row.investigation_id,
            "investigation": cls._serialize_saved_investigation(investigation) if investigation else None,
            "notes": row.notes,
            "schedule_hint": row.schedule_hint,
            "regions": cls._json_load(row.regions_json) or [],
            "role_arns": cls._json_load(row.role_arns_json) or [],
            "tags": cls._json_load(row.tags_json) or [],
            "enabled": row.enabled,
            "last_run_id": row.last_run_id,
            "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @classmethod
    def extract_metrics(cls, steps: list[dict[str, Any]]) -> list[ExtractedMetric]:
        metrics: list[ExtractedMetric] = []
        for step in steps:
            tool_call = step.get("tool_call") or {}
            tool_name = tool_call.get("name")
            result = step.get("tool_result")
            step_number = step.get("step")
            if not tool_name or not isinstance(result, dict):
                continue
            metrics.extend(cls._extract_from_payload(tool_name, int(step_number) if step_number else None, result))
        return metrics

    @classmethod
    def _extract_from_payload(
        cls,
        tool_name: str,
        step_number: int | None,
        payload: dict[str, Any],
    ) -> list[ExtractedMetric]:
        metrics: list[ExtractedMetric] = []
        for key, value in payload.items():
            metric_base = f"{tool_name}.{key}"
            label_base = f"{cls._humanize_tool_name(tool_name)} · {key.replace('_', ' ')}"
            if cls._is_numeric(value):
                metrics.append(
                    ExtractedMetric(
                        step_number=step_number,
                        tool_name=tool_name,
                        metric_key=metric_base,
                        metric_label=label_base.title(),
                        metric_value=float(value),
                    )
                )
                continue
            if isinstance(value, dict):
                metrics.extend(cls._extract_from_mapping(tool_name, step_number, metric_base, label_base, value))
                continue
            if isinstance(value, list):
                metrics.extend(cls._extract_from_rows(tool_name, step_number, metric_base, label_base, value))
        return metrics

    @classmethod
    def _extract_from_mapping(
        cls,
        tool_name: str,
        step_number: int | None,
        metric_base: str,
        label_base: str,
        mapping: dict[str, Any],
    ) -> list[ExtractedMetric]:
        metrics: list[ExtractedMetric] = []
        if cls._looks_like_money(mapping):
            metrics.append(
                ExtractedMetric(
                    step_number=step_number,
                    tool_name=tool_name,
                    metric_key=metric_base,
                    metric_label=label_base.title(),
                    metric_value=float(mapping.get("amount") or 0.0),
                    unit=str(mapping.get("unit") or ""),
                )
            )
            return metrics

        numeric_items = {key: value for key, value in mapping.items() if cls._is_numeric(value)}
        if numeric_items and len(numeric_items) == len(mapping):
            for dimension_key, dimension_value in numeric_items.items():
                metrics.append(
                    ExtractedMetric(
                        step_number=step_number,
                        tool_name=tool_name,
                        metric_key=f"{metric_base}.{dimension_key}",
                        metric_label=f"{label_base.title()} · {dimension_key}",
                        metric_value=float(dimension_value),
                        dimensions={"bucket": dimension_key},
                    )
                )
        return metrics

    @classmethod
    def _extract_from_rows(
        cls,
        tool_name: str,
        step_number: int | None,
        metric_base: str,
        label_base: str,
        rows: list[Any],
    ) -> list[ExtractedMetric]:
        metrics: list[ExtractedMetric] = []
        for row in rows[:20]:
            if not isinstance(row, dict):
                continue
            dimension_key, dimension_value = cls._pick_dimension(row)
            for key, value in row.items():
                if cls._is_numeric(value):
                    metric_key = f"{metric_base}.{key}"
                    dimensions = {dimension_key: dimension_value} if dimension_key and dimension_value else None
                    label = f"{label_base.title()} · {key.replace('_', ' ')}"
                    metrics.append(
                        ExtractedMetric(
                            step_number=step_number,
                            tool_name=tool_name,
                            metric_key=metric_key,
                            metric_label=label.title(),
                            metric_value=float(value),
                            dimensions=dimensions,
                        )
                    )
                elif isinstance(value, dict) and cls._looks_like_money(value):
                    metric_key = f"{metric_base}.{key}"
                    dimensions = {dimension_key: dimension_value} if dimension_key and dimension_value else None
                    label = f"{label_base.title()} · {key.replace('_', ' ')}"
                    metrics.append(
                        ExtractedMetric(
                            step_number=step_number,
                            tool_name=tool_name,
                            metric_key=metric_key,
                            metric_label=label.title(),
                            metric_value=float(value.get("amount") or 0.0),
                            unit=str(value.get("unit") or ""),
                            dimensions=dimensions,
                        )
                    )
        return metrics

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def _looks_like_money(value: dict[str, Any]) -> bool:
        return set(value.keys()) >= {"amount", "unit"} and isinstance(value.get("amount"), (int, float))

    @staticmethod
    def _pick_dimension(row: dict[str, Any]) -> tuple[str | None, str | None]:
        preferred_keys = (
            "service",
            "tag_value",
            "resource_id",
            "config_rule_name",
            "timestamp",
            "start",
            "name",
            "id",
        )
        for key in preferred_keys:
            value = row.get(key)
            if value not in (None, ""):
                return key, str(value)
        for key, value in row.items():
            if isinstance(value, str) and value.strip():
                return key, value
        return None, None

    @staticmethod
    def _trim_text(value: str, limit: int) -> str:
        normalized = (value or "").strip()
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 1].rstrip()}…"

    @staticmethod
    def _json_dump(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, default=str)

    @staticmethod
    def _json_load(value: str | None) -> Any:
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    def _humanize_tool_name(tool_name: str) -> str:
        name = tool_name.removeprefix("list_").removeprefix("get_").removeprefix("run_")
        label = name.replace("_", " ").strip().title()
        label = label.replace("Scc", "SCC").replace("Pvc", "PVC").replace("Mcp", "MCP")
        label = label.replace("Api", "API").replace("Csv", "CSV").replace("Olm", "OLM")
        label = label.replace("Oc", "OC").replace("Tls", "TLS")
        return label

    @staticmethod
    def _serialize_finops_queue_item(record: FinopsQueueRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "run_id": record.run_id,
            "opportunity_key": record.opportunity_key,
            "title": record.title,
            "category": record.category,
            "estimated_monthly_savings": record.estimated_monthly_savings,
            "unit": record.unit,
            "execution_stage": record.execution_stage,
            "risk": record.risk,
            "confidence": record.confidence,
            "action": record.action,
            "basis": record.basis,
            "evidence": record.evidence,
            "execution_plan": record.execution_plan,
            "auto_approved": record.auto_approved,
            "execution_mode": record.execution_mode,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Data retention — v0.3.0
    # ------------------------------------------------------------------

    def enforce_retention(self, retention_days: int) -> int:
        if not self.enabled or self._session_factory is None or retention_days <= 0:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        with self._session_factory() as session:
            old_runs = session.scalars(
                select(AgentRunRecord).where(AgentRunRecord.created_at < cutoff)
            ).all()
            count = len(old_runs)
            for run in old_runs:
                session.delete(run)
            session.commit()
        return count

    # ------------------------------------------------------------------
    # History export — v0.3.0
    # ------------------------------------------------------------------

    def export_runs_csv(self, *, time_range: str = "all", limit: int = 500) -> str:
        if not self.enabled or self._session_factory is None:
            return "run_id,created_at,status,model_name,cluster_scope,duration_ms,step_count,prompt_excerpt\n"
        since = self._resolve_since(time_range)
        conditions = []
        if since is not None:
            conditions.append(AgentRunRecord.created_at >= since)
        with self._session_factory() as session:
            rows = session.scalars(
                select(AgentRunRecord).where(*conditions).order_by(desc(AgentRunRecord.created_at)).limit(limit)
            ).all()
        lines = ["run_id,created_at,status,model_name,cluster_scope,duration_ms,step_count,tokens,tags,prompt_excerpt"]
        for r in rows:
            excerpt = self._trim_text(r.prompt, 80).replace('"', '""')
            tags_str = (self._json_load(r.tags_json) if r.tags_json else "") or ""
            if isinstance(tags_str, list):
                tags_str = ";".join(tags_str)
            lines.append(
                f'{r.id},{r.created_at.isoformat()},{r.status},{r.model_name},{r.cluster_scope},'
                f'{r.duration_ms},{r.step_count},{r.token_total},"{tags_str}","{excerpt}"'
            )
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Run tagging — v0.3.0
    # ------------------------------------------------------------------

    def tag_run(self, run_id: int, tags: list[str]) -> dict[str, Any] | None:
        if not self.enabled or self._session_factory is None:
            return None
        with self._session_factory() as session:
            run = session.get(AgentRunRecord, run_id)
            if run is None:
                return None
            existing = self._json_load(run.tags_json) or []
            merged = list(dict.fromkeys(existing + tags))
            run.tags_json = self._json_dump(merged)
            session.commit()
            return {"run_id": run.id, "tags": merged}

    def delete_run(self, run_id: int) -> bool:
        if not self.enabled or self._session_factory is None:
            return False
        with self._session_factory() as session:
            run = session.get(AgentRunRecord, run_id)
            if run is None:
                return False
            session.delete(run)
            session.commit()
            return True
