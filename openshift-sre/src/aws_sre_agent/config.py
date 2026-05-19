"""Runtime configuration and provider metadata for the OpenShift SRE agent.

This module keeps the existing provider-catalog support while shifting the
platform runtime from AWS to Red Hat OpenShift / Kubernetes access patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


LLM_PROVIDER_METADATA: dict[str, dict[str, Any]] = {
    "ollama": {
        "id": "ollama",
        "label": "Local Ollama",
        "category": "local",
        "description": "Use the local Ollama runtime already supported by the stack.",
        "default_base_url": "http://localhost:11434",
        "default_model": "gpt-oss:20b",
        "supports_catalog_refresh": True,
        "suggested_models": ["gpt-oss:20b", "qwen3:8b", "llama3.1:8b"],
        "credential_fields": [],
    },
    "openai": {
        "id": "openai",
        "label": "OpenAI",
        "category": "external",
        "description": "Use OpenAI-hosted chat models through the Chat Completions API.",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4.1-mini",
        "supports_catalog_refresh": False,
        "suggested_models": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
        "credential_fields": [
            {"key": "llm_api_key", "label": "API key", "input_type": "password", "required": True, "placeholder": "sk-..."},
            {"key": "llm_organization", "label": "Organization", "input_type": "text", "required": False, "placeholder": "Optional org ID"},
            {"key": "llm_base_url", "label": "Base URL", "input_type": "url", "required": False, "placeholder": "https://api.openai.com/v1"},
        ],
    },
    "azure-openai": {
        "id": "azure-openai",
        "label": "Azure OpenAI",
        "category": "external",
        "description": "Use an Azure OpenAI deployment with endpoint, API key, and API version overrides.",
        "default_base_url": "https://your-resource-name.openai.azure.com",
        "default_model": "gpt-4.1-mini",
        "default_api_version": "2024-06-01",
        "supports_catalog_refresh": False,
        "suggested_models": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
        "credential_fields": [
            {"key": "llm_api_key", "label": "API key", "input_type": "password", "required": True, "placeholder": "Azure OpenAI API key"},
            {"key": "llm_base_url", "label": "Endpoint", "input_type": "url", "required": True, "placeholder": "https://your-resource-name.openai.azure.com"},
            {"key": "llm_api_version", "label": "API version", "input_type": "text", "required": False, "placeholder": "2024-06-01"},
        ],
    },
    "anthropic": {
        "id": "anthropic",
        "label": "Anthropic",
        "category": "external",
        "description": "Use Anthropic Claude models through the Messages API.",
        "default_base_url": "https://api.anthropic.com",
        "default_model": "claude-3-5-sonnet-latest",
        "default_api_version": "2023-06-01",
        "supports_catalog_refresh": False,
        "suggested_models": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
        "credential_fields": [
            {"key": "llm_api_key", "label": "API key", "input_type": "password", "required": True, "placeholder": "sk-ant-..."},
            {"key": "llm_base_url", "label": "Base URL", "input_type": "url", "required": False, "placeholder": "https://api.anthropic.com"},
            {"key": "llm_api_version", "label": "Anthropic version", "input_type": "text", "required": False, "placeholder": "2023-06-01"},
        ],
    },
    "gemini": {
        "id": "gemini",
        "label": "Google Gemini",
        "category": "external",
        "description": "Use Google Gemini models through the Generative Language API.",
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.0-flash",
        "supports_catalog_refresh": False,
        "suggested_models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "credential_fields": [
            {"key": "llm_api_key", "label": "API key", "input_type": "password", "required": True, "placeholder": "AIza..."},
            {"key": "llm_base_url", "label": "Base URL", "input_type": "url", "required": False, "placeholder": "https://generativelanguage.googleapis.com/v1beta"},
        ],
    },
    "openrouter": {
        "id": "openrouter",
        "label": "OpenRouter",
        "category": "external",
        "description": "Use OpenRouter-hosted models through its OpenAI-compatible API.",
        "default_base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4.1-mini",
        "supports_catalog_refresh": False,
        "suggested_models": ["openai/gpt-4.1-mini", "anthropic/claude-3.5-sonnet", "google/gemini-1.5-pro"],
        "credential_fields": [
            {"key": "llm_api_key", "label": "API key", "input_type": "password", "required": True, "placeholder": "sk-or-..."},
            {"key": "llm_base_url", "label": "Base URL", "input_type": "url", "required": False, "placeholder": "https://openrouter.ai/api/v1"},
        ],
    },
}


def normalize_llm_provider(value: str | None) -> str:
    provider = (value or "ollama").strip().lower()
    return provider if provider in LLM_PROVIDER_METADATA else "ollama"


def get_llm_provider_defaults(provider: str) -> dict[str, Any]:
    return LLM_PROVIDER_METADATA.get(normalize_llm_provider(provider), LLM_PROVIDER_METADATA["ollama"])


@dataclass(slots=True)
class Settings:
    """Normalized runtime settings for provider, OpenShift access, persistence, and UI behavior."""

    ollama_base_url: str
    local_model_name: str
    aws_region: str
    llm_provider: str = "ollama"
    llm_model_name: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_api_version: str | None = None
    llm_organization: str | None = None
    aws_regions: str | None = None
    aws_profile: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    aws_assume_role_arn: str | None = None
    aws_assume_role_external_id: str | None = None
    aws_role_session_name: str = "openshift-sre-local-agent"
    aws_ca_bundle: str | None = None
    aws_verify_ssl: bool = True
    allow_mutating_actions: bool = False
    agent_max_steps: int = 8
    fallback_models: str | None = None
    log_level: str = "INFO"
    database_enabled: bool = False
    database_url: str | None = None
    db_host: str | None = None
    db_port: int = 3306
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    api_key: str | None = None
    auth_enabled: bool = False
    data_retention_days: int = 90
    prompt_template: str = "default"
    enable_prometheus: bool = False
    context_window_tokens: int = 4096
    temperature_override: float | None = None
    openshift_cluster: str = "local-cluster"
    openshift_namespace: str = "openshift-monitoring"
    openshift_projects: str | None = None
    openshift_api_url: str | None = None
    openshift_token: str | None = None
    kubeconfig_path: str | None = None
    kube_context: str | None = None
    oc_cli_path: str = "oc"
    openshift_verify_ssl: bool = True

    @classmethod
    def load(cls) -> "Settings":
        llm_provider = normalize_llm_provider(getenv("LLM_PROVIDER", "ollama"))
        provider_defaults = get_llm_provider_defaults(llm_provider)
        database_url = getenv("DATABASE_URL") or None
        db_host = getenv("DB_HOST") or None
        db_port = int(getenv("DB_PORT", "3306"))
        db_name = getenv("DB_NAME") or None
        db_user = getenv("DB_USER") or None
        db_password = getenv("DB_PASSWORD") or None
        database_enabled = getenv("DATABASE_ENABLED", "false").lower() == "true" or bool(database_url)
        if database_enabled and not database_url and db_host and db_name and db_user and db_password:
            encoded_password = quote_plus(db_password)
            database_url = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

        openshift_cluster = getenv("OPENSHIFT_CLUSTER", getenv("AWS_REGION", "local-cluster"))
        openshift_namespace = getenv("OPENSHIFT_NAMESPACE", "openshift-monitoring")
        openshift_projects = getenv("OPENSHIFT_PROJECTS") or getenv("AWS_SWEEP_REGIONS") or None
        kube_context = getenv("KUBECONFIG_CONTEXT") or getenv("AWS_PROFILE") or None
        openshift_api_url = getenv("OPENSHIFT_API_URL") or None
        openshift_token = getenv("OPENSHIFT_TOKEN") or None
        openshift_verify_ssl = getenv("OPENSHIFT_VERIFY_SSL", getenv("AWS_VERIFY_SSL", "true")).lower() != "false"
        kubeconfig_path = getenv("KUBECONFIG_PATH") or None
        oc_cli_path = getenv("OC_CLI_PATH", "oc")

        fallback_models = getenv("FALLBACK_MODELS") or None
        log_level = getenv("LOG_LEVEL", "INFO")
        api_key = getenv("API_KEY") or None
        auth_enabled = getenv("AUTH_ENABLED", "false").lower() == "true" or bool(api_key)
        data_retention_days = int(getenv("DATA_RETENTION_DAYS", "90"))
        prompt_template = getenv("PROMPT_TEMPLATE", "default")
        enable_prometheus = getenv("ENABLE_PROMETHEUS", "false").lower() == "true"
        context_window_tokens = int(getenv("CONTEXT_WINDOW_TOKENS", "4096"))
        llm_model_name = getenv("LLM_MODEL_NAME") or None
        llm_base_url = getenv("LLM_BASE_URL") or None
        llm_api_key = getenv("LLM_API_KEY") or None
        llm_api_version = getenv("LLM_API_VERSION") or provider_defaults.get("default_api_version")
        llm_organization = getenv("LLM_ORGANIZATION") or None
        temperature_raw = getenv("TEMPERATURE_OVERRIDE")
        temperature_override = float(temperature_raw) if temperature_raw else None

        return cls(
            ollama_base_url=getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
            local_model_name=getenv("LOCAL_MODEL_NAME", "gpt-oss:20b"),
            aws_region=openshift_cluster,
            llm_provider=llm_provider,
            llm_model_name=llm_model_name,
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            llm_api_version=llm_api_version,
            llm_organization=llm_organization,
            aws_regions=openshift_projects,
            aws_profile=kube_context,
            aws_access_key_id=openshift_api_url,
            aws_secret_access_key=openshift_token,
            aws_session_token=openshift_namespace,
            aws_assume_role_arn=None,
            aws_assume_role_external_id=None,
            aws_role_session_name=getenv("AWS_ROLE_SESSION_NAME", "openshift-sre-local-agent"),
            aws_ca_bundle=None,
            aws_verify_ssl=openshift_verify_ssl,
            allow_mutating_actions=getenv("ALLOW_MUTATING_ACTIONS", "false").lower() == "true",
            agent_max_steps=int(getenv("AGENT_MAX_STEPS", "8")),
            fallback_models=fallback_models,
            log_level=log_level,
            database_enabled=database_enabled,
            database_url=database_url,
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            api_key=api_key,
            auth_enabled=auth_enabled,
            data_retention_days=data_retention_days,
            prompt_template=prompt_template,
            enable_prometheus=enable_prometheus,
            context_window_tokens=context_window_tokens,
            temperature_override=temperature_override,
            openshift_cluster=openshift_cluster,
            openshift_namespace=openshift_namespace,
            openshift_projects=openshift_projects,
            openshift_api_url=openshift_api_url,
            openshift_token=openshift_token,
            kubeconfig_path=kubeconfig_path,
            kube_context=kube_context,
            oc_cli_path=oc_cli_path,
            openshift_verify_ssl=openshift_verify_ssl,
        )

    def with_overrides(
        self,
        *,
        llm_provider: str | None = None,
        llm_model_name: str | None = None,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        llm_api_version: str | None = None,
        llm_organization: str | None = None,
        ollama_base_url: str | None = None,
        local_model_name: str | None = None,
        aws_region: str | None = None,
        aws_regions: str | None = None,
        aws_profile: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        aws_assume_role_arn: str | None = None,
        aws_assume_role_external_id: str | None = None,
        aws_role_session_name: str | None = None,
        aws_ca_bundle: str | None = None,
        aws_verify_ssl: bool | None = None,
        agent_max_steps: int | None = None,
        database_enabled: bool | None = None,
        database_url: str | None = None,
        db_host: str | None = None,
        db_port: int | None = None,
        db_name: str | None = None,
        db_user: str | None = None,
        db_password: str | None = None,
        fallback_models: str | None = None,
        log_level: str | None = None,
        openshift_cluster: str | None = None,
        openshift_namespace: str | None = None,
        openshift_projects: str | None = None,
        openshift_api_url: str | None = None,
        openshift_token: str | None = None,
        kubeconfig_path: str | None = None,
        kube_context: str | None = None,
        oc_cli_path: str | None = None,
        openshift_verify_ssl: bool | None = None,
    ) -> "Settings":
        normalized_provider = normalize_llm_provider(llm_provider or self.llm_provider)
        normalized_ollama_url = (ollama_base_url or self.ollama_base_url).rstrip("/")
        resolved_cluster = openshift_cluster or aws_region or self.openshift_cluster
        resolved_projects = openshift_projects if openshift_projects not in (None, "") else aws_regions
        if resolved_projects in (None, ""):
            resolved_projects = self.openshift_projects
        resolved_namespace = openshift_namespace or aws_session_token or self.openshift_namespace
        resolved_context = kube_context or aws_profile or self.kube_context
        resolved_api_url = openshift_api_url or aws_access_key_id or self.openshift_api_url
        resolved_token = openshift_token or aws_secret_access_key or self.openshift_token
        resolved_verify_ssl = self.openshift_verify_ssl
        if openshift_verify_ssl is not None:
            resolved_verify_ssl = openshift_verify_ssl
        elif aws_verify_ssl is not None:
            resolved_verify_ssl = aws_verify_ssl

        return Settings(
            ollama_base_url=normalized_ollama_url,
            local_model_name=local_model_name or self.local_model_name,
            aws_region=resolved_cluster,
            llm_provider=normalized_provider,
            llm_model_name=llm_model_name if llm_model_name not in (None, "") else self.llm_model_name,
            llm_base_url=llm_base_url if llm_base_url not in (None, "") else self.llm_base_url,
            llm_api_key=llm_api_key if llm_api_key not in (None, "") else self.llm_api_key,
            llm_api_version=llm_api_version if llm_api_version not in (None, "") else self.llm_api_version,
            llm_organization=llm_organization if llm_organization not in (None, "") else self.llm_organization,
            aws_regions=resolved_projects,
            aws_profile=resolved_context,
            aws_access_key_id=resolved_api_url,
            aws_secret_access_key=resolved_token,
            aws_session_token=resolved_namespace,
            aws_assume_role_arn=aws_assume_role_arn if aws_assume_role_arn not in (None, "") else self.aws_assume_role_arn,
            aws_assume_role_external_id=(
                aws_assume_role_external_id if aws_assume_role_external_id not in (None, "") else self.aws_assume_role_external_id
            ),
            aws_role_session_name=aws_role_session_name or self.aws_role_session_name,
            aws_ca_bundle=aws_ca_bundle if aws_ca_bundle not in (None, "") else self.aws_ca_bundle,
            aws_verify_ssl=resolved_verify_ssl,
            allow_mutating_actions=self.allow_mutating_actions,
            agent_max_steps=agent_max_steps or self.agent_max_steps,
            fallback_models=fallback_models if fallback_models not in (None, "") else self.fallback_models,
            log_level=log_level or self.log_level,
            database_enabled=self.database_enabled if database_enabled is None else database_enabled,
            database_url=database_url if database_url not in (None, "") else self.database_url,
            db_host=db_host if db_host not in (None, "") else self.db_host,
            db_port=db_port or self.db_port,
            db_name=db_name if db_name not in (None, "") else self.db_name,
            db_user=db_user if db_user not in (None, "") else self.db_user,
            db_password=db_password if db_password not in (None, "") else self.db_password,
            api_key=self.api_key,
            auth_enabled=self.auth_enabled,
            data_retention_days=self.data_retention_days,
            prompt_template=self.prompt_template,
            enable_prometheus=self.enable_prometheus,
            context_window_tokens=self.context_window_tokens,
            temperature_override=self.temperature_override,
            openshift_cluster=resolved_cluster,
            openshift_namespace=resolved_namespace,
            openshift_projects=resolved_projects,
            openshift_api_url=resolved_api_url,
            openshift_token=resolved_token,
            kubeconfig_path=kubeconfig_path if kubeconfig_path not in (None, "") else self.kubeconfig_path,
            kube_context=resolved_context,
            oc_cli_path=oc_cli_path if oc_cli_path not in (None, "") else self.oc_cli_path,
            openshift_verify_ssl=resolved_verify_ssl,
        )

    @property
    def effective_model_name(self) -> str:
        if self.llm_provider == "ollama":
            return self.local_model_name
        if self.llm_model_name:
            return self.llm_model_name
        provider_defaults = get_llm_provider_defaults(self.llm_provider)
        return str(provider_defaults.get("default_model") or self.local_model_name)

    @property
    def effective_llm_base_url(self) -> str:
        if self.llm_provider == "ollama":
            return self.ollama_base_url.rstrip("/")
        provider_defaults = get_llm_provider_defaults(self.llm_provider)
        return str(self.llm_base_url or provider_defaults.get("default_base_url") or "").rstrip("/")

    @property
    def platform_scope(self) -> str:
        return self.openshift_cluster or self.aws_region
