from __future__ import annotations

import json
import os
import re
from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import httpx

from .config import Settings
from .model_client import ModelClient

_TEMPLATE_REF_RE = re.compile(r"(?:template|extends)\s*:\s*['\"]?([^'\"\n]+)", re.IGNORECASE)
_STAGE_RE = re.compile(r"(?:^|\n)\s*-?\s*stage\s*:\s*['\"]?([^'\"\n]+)", re.IGNORECASE)
_WORKDIR_RE = re.compile(r"workdir\s*:\s*['\"]?([^'\"\n]+)", re.IGNORECASE)
_TERRAFORM_DIR_RE = re.compile(r"(?:terraform\s+)?(?:workingDirectory|working_directory|working-dir|cwd)\s*:\s*['\"]?([^'\"\n]+)", re.IGNORECASE)
_PATH_SPLIT_RE = re.compile(r"[\n,;]+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")

_BUILDER_HISTORY_TAGS = ["openshift-builder", "openshift-delivery", "ado-pipelines"]


@dataclass(slots=True)
class BuilderCatalogEntry:
    id: str
    kind: str
    title: str
    relative_path: str
    source_root: str
    description: str
    stage_names: list[str]
    template_references: list[str]
    workdir: str | None
    content: str

    def as_dict(self, *, include_content: bool = False) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "relative_path": self.relative_path,
            "source_root": self.source_root,
            "description": self.description,
            "stage_names": self.stage_names,
            "template_references": self.template_references,
            "workdir": self.workdir,
            "content_preview": self.content[:1200],
            "content_length": len(self.content),
        }
        if include_content:
            payload["content"] = self.content
        return payload


@dataclass(slots=True)
class BuilderAdoConfig:
    organization_url: str
    project: str
    repository: str | None
    branch: str
    pat: str
    target_directory: str


def get_builder_history_tags() -> list[str]:
    return list(_BUILDER_HISTORY_TAGS)


def discover_builder_catalog() -> dict[str, Any]:
    roots = _discover_source_roots()
    pipelines: list[BuilderCatalogEntry] = []
    templates: list[BuilderCatalogEntry] = []
    variables: list[BuilderCatalogEntry] = []

    for root in roots:
        for path in sorted(_iter_catalog_files(root)):
            if not path.is_file():
                continue
            entry = _build_catalog_entry(root, path)
            if entry.kind == "pipeline":
                pipelines.append(entry)
            elif entry.kind == "variables":
                variables.append(entry)
            else:
                templates.append(entry)

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_roots": [str(root) for root in roots],
        "counts": {
            "pipeline_count": len(pipelines),
            "template_count": len(templates),
            "variable_file_count": len(variables),
        },
        "pipelines": [entry.as_dict() for entry in pipelines],
        "templates": [entry.as_dict() for entry in templates],
        "variables": [entry.as_dict() for entry in variables],
    }


def discover_ado_pipeline_catalog(config: BuilderAdoConfig) -> dict[str, Any]:
    """Return Azure DevOps pipeline definitions as OpenShift Builder catalog entries."""

    _validate_ado_config(config)
    pipelines: list[BuilderCatalogEntry] = []
    repositories_seen: dict[str, dict[str, Any]] = {}
    pipeline_rows: list[dict[str, Any]] = []
    build_definition_entries: list[BuilderCatalogEntry] = []
    discovery_warnings: list[str] = []
    with httpx.Client(timeout=20.0, follow_redirects=False, headers=_ado_auth_headers(config)) as client:
        try:
            pipelines_response = client.get(
                _ado_project_url(config, "_apis/pipelines"),
                params={"api-version": "7.1-preview.1"},
            )
            _raise_for_ado_response(pipelines_response, "pipeline discovery")
            pipelines_response.raise_for_status()
            pipeline_rows = pipelines_response.json().get("value") or []
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise
            discovery_warnings.append(f"Pipelines API discovery returned HTTP {error.response.status_code}; trying build definitions fallback.")

        for row in pipeline_rows:
            detail = _fetch_ado_pipeline_detail(client=client, config=config, pipeline_id=row.get("id")) or row
            configuration = detail.get("configuration") or {}
            repository = configuration.get("repository") or {}
            repository_name = str(repository.get("name") or repository.get("id") or "").strip()
            repository_id = str(repository.get("id") or repository.get("name") or config.repository or "").strip()
            if config.repository and repository_name and not _repository_matches(config.repository, repository_name, repository_id):
                continue

            yaml_path = str(configuration.get("path") or "").strip()
            content = ""
            if yaml_path and (repository_id or config.repository):
                content = _fetch_ado_yaml_content(
                    client=client,
                    config=config,
                    repository=repository_id or config.repository or "",
                    path=yaml_path,
                )

            pipeline_id = str(detail.get("id") or row.get("id") or detail.get("name") or "pipeline")
            title = str(detail.get("name") or row.get("name") or f"Pipeline {pipeline_id}")
            relative_path = yaml_path.lstrip("/") or f"azure-pipelines/{_slugify(title)}.yml"
            source_root = f"azure-devops:{config.project}"
            if repository_name:
                source_root = f"{source_root}/{repository_name}"
                repositories_seen[repository_name] = {"id": repository_id, "name": repository_name}
            description_parts = [f"Azure DevOps pipeline '{title}' from project {config.project}."]
            if repository_name:
                description_parts.append(f"Repository: {repository_name}.")
            if yaml_path:
                description_parts.append(f"YAML path: {yaml_path}.")
            if not content:
                description_parts.append("YAML content was not returned by Azure DevOps for this pipeline definition.")

            pipelines.append(
                BuilderCatalogEntry(
                    id=f"ado-{pipeline_id}-{_slugify(title)}",
                    kind="pipeline",
                    title=title,
                    relative_path=relative_path,
                    source_root=source_root,
                    description=" ".join(description_parts),
                    stage_names=[match.strip() for match in _STAGE_RE.findall(content) if match.strip()],
                    template_references=[match.strip() for match in _TEMPLATE_REF_RE.findall(content) if match.strip()],
                    workdir=_extract_workdir(content),
                    content=content,
                )
            )

        try:
            build_definition_entries, build_repositories_seen = _discover_ado_build_definition_catalog(client=client, config=config)
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise
            build_repositories_seen = {}
            discovery_warnings.append(f"Build definitions discovery returned HTTP {error.response.status_code}.")
        except httpx.HTTPError as error:
            build_repositories_seen = {}
            discovery_warnings.append(f"Build definitions discovery failed: {error}.")
        existing_pipeline_ids = {entry.id for entry in pipelines}
        for entry in build_definition_entries:
            if entry.id in existing_pipeline_ids:
                continue
            existing_pipeline_ids.add(entry.id)
            pipelines.append(entry)
        repositories_seen.update(build_repositories_seen)

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_roots": sorted({entry.source_root for entry in pipelines}),
        "counts": {"pipeline_count": len(pipelines), "template_count": 0, "variable_file_count": 0},
        "pipelines": [entry.as_dict(include_content=bool(entry.content)) for entry in pipelines],
        "templates": [],
        "variables": [],
        "ado": {
            "organization_url": config.organization_url,
            "project": config.project,
            "repository": config.repository,
            "branch": config.branch,
            "repositories": list(repositories_seen.values())[:50],
            "discovery_methods": {
                "pipelines_api_count": len(pipeline_rows),
                "build_definition_count": len(build_definition_entries),
                "total_catalog_count": len(pipelines),
                "warnings": discovery_warnings,
            },
        },
    }


def merge_builder_catalogs(*catalogs: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_roots": [],
        "counts": {"pipeline_count": 0, "template_count": 0, "variable_file_count": 0},
        "pipelines": [],
        "templates": [],
        "variables": [],
    }
    seen_source_roots: set[str] = set()
    seen_entries: set[tuple[str, str]] = set()
    for catalog in catalogs:
        for root in catalog.get("source_roots") or []:
            root_text = str(root)
            if root_text and root_text not in seen_source_roots:
                seen_source_roots.add(root_text)
                merged["source_roots"].append(root_text)
        for group in ("pipelines", "templates", "variables"):
            for item in catalog.get(group) or []:
                item_id = str(item.get("id") or item.get("relative_path") or "")
                key = (group, item_id)
                if not item_id or key in seen_entries:
                    continue
                seen_entries.add(key)
                merged[group].append(item)
    merged["counts"] = {
        "pipeline_count": len(merged["pipelines"]),
        "template_count": len(merged["templates"]),
        "variable_file_count": len(merged["variables"]),
    }
    return merged


def validate_ado_connection(config: BuilderAdoConfig) -> dict[str, Any]:
    _validate_ado_config(config)
    with httpx.Client(timeout=15.0, follow_redirects=False, headers=_ado_auth_headers(config)) as client:
        repositories_response = client.get(
            _ado_project_url(config, "_apis/git/repositories"),
            params={"api-version": "7.1"},
        )
        _raise_for_ado_response(repositories_response, "repository validation")
        repositories_response.raise_for_status()
        repositories_payload = repositories_response.json()

    repositories = repositories_payload.get("value") or []
    repo_names = [repo.get("name") for repo in repositories if repo.get("name")]
    repository = None
    if config.repository:
        repository = next(
            (
                repo
                for repo in repositories
                if _repository_matches(config.repository or "", str(repo.get("name") or ""), str(repo.get("id") or ""))
            ),
            None,
        )
        if repository is None:
            raise ValueError(f"Repository '{config.repository}' was not found in Azure DevOps project '{config.project}'.")

    return {
        "authenticated": True,
        "organization_url": config.organization_url,
        "project": config.project,
        "repository": repository,
        "repository_count": len(repositories),
        "repositories": [
            {"id": repo.get("id"), "name": repo.get("name"), "default_branch": repo.get("defaultBranch")}
            for repo in repositories[:50]
        ],
        "repository_names": repo_names,
        "branch": config.branch,
        "target_directory": config.target_directory,
    }


def plan_builder_implementation(
    *,
    catalog: dict[str, Any],
    design_snapshot: dict[str, Any] | None,
    prompt: str,
    selected_pipeline_ids: list[str],
    settings: Settings,
) -> dict[str, Any]:
    pipelines = catalog.get("pipelines") or []
    selected_ids = _dedupe(selected_pipeline_ids)
    heuristic = _heuristic_pipeline_plan(pipelines=pipelines, design_snapshot=design_snapshot, prompt=prompt)
    llm_plan = _llm_pipeline_plan(
        pipelines=pipelines,
        design_snapshot=design_snapshot,
        prompt=prompt,
        settings=settings,
        heuristic=heuristic,
    )
    resolved = llm_plan or heuristic
    recommended_ids = _dedupe(resolved.get("recommended_pipeline_ids") or [])
    missing_requirements = _dedupe(resolved.get("missing_requirements") or [])
    selected_missing = [item for item in recommended_ids if item not in selected_ids]

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "provider": settings.llm_provider,
        "model_name": settings.effective_model_name,
        "design_loaded": bool(design_snapshot),
        "selected_pipeline_ids": selected_ids,
        "recommended_pipeline_ids": recommended_ids,
        "selected_pipeline_ids_missing_from_recommendation": selected_missing,
        "missing_requirements": missing_requirements,
        "reasoning_summary": resolved.get("reasoning_summary") or "Matched the available OpenShift delivery inventory against the latest Architect context.",
        "recommendation_source": resolved.get("source") or ("llm" if llm_plan else "heuristic"),
    }


def implement_builder_plan(
    *,
    catalog: dict[str, Any],
    design_snapshot: dict[str, Any] | None,
    prompt: str,
    selected_pipeline_ids: list[str],
    settings: Settings,
    ado_config: BuilderAdoConfig | None,
    push_to_ado: bool,
    confirm_generate_missing: bool,
) -> dict[str, Any]:
    index = _catalog_index(catalog)
    selected_ids = _dedupe(selected_pipeline_ids)
    selected_entries = [index[item_id] for item_id in selected_ids if item_id in index]
    unknown_selected = [item_id for item_id in selected_ids if item_id not in index]
    plan = plan_builder_implementation(
        catalog=catalog,
        design_snapshot=design_snapshot,
        prompt=prompt,
        selected_pipeline_ids=selected_ids,
        settings=settings,
    )
    missing_requirements = list(plan.get("missing_requirements") or [])
    generated_files = _generate_missing_pipeline_files(
        missing_requirements=missing_requirements,
        design_snapshot=design_snapshot,
        prompt=prompt,
        settings=settings,
        target_directory=ado_config.target_directory if ado_config else "/pipelines/generated/openshift",
    )

    if missing_requirements and not confirm_generate_missing:
        return {
            "implemented": False,
            "confirmation_required": True,
            "provider": settings.llm_provider,
            "model_name": settings.effective_model_name,
            "selected_pipeline_ids": selected_ids,
            "unknown_selected_pipeline_ids": unknown_selected,
            "selected_pipelines": [entry.as_dict(include_content=True) for entry in selected_entries],
            "missing_requirements": missing_requirements,
            "recommended_pipeline_ids": plan.get("recommended_pipeline_ids") or [],
            "reasoning_summary": plan.get("reasoning_summary"),
            "generation_preview": generated_files,
            "message": "Some required OpenShift delivery pipelines are not present in the catalog. Confirm generation to create new pipeline and variable files.",
        }

    pushed_files: list[dict[str, Any]] = []
    if push_to_ado:
        if ado_config is None:
            raise ValueError("Azure DevOps authentication is required before pushing selected pipelines into a repository.")
        validate_ado_connection(ado_config)
        files_to_push = [
            {"path": _normalize_remote_path(f"/{entry.relative_path}"), "content": entry.content}
            for entry in selected_entries
        ] + [
            {"path": _normalize_remote_path(item["path"]), "content": item["content"]}
            for item in generated_files
        ]
        pushed_files = push_files_to_ado(config=ado_config, files=files_to_push)

    return {
        "implemented": True,
        "confirmation_required": False,
        "provider": settings.llm_provider,
        "model_name": settings.effective_model_name,
        "selected_pipeline_ids": selected_ids,
        "unknown_selected_pipeline_ids": unknown_selected,
        "selected_pipelines": [entry.as_dict(include_content=True) for entry in selected_entries],
        "recommended_pipeline_ids": plan.get("recommended_pipeline_ids") or [],
        "missing_requirements": missing_requirements,
        "generated_files": generated_files,
        "push_to_ado": push_to_ado,
        "ado_push": {
            "performed": push_to_ado,
            "files": pushed_files,
            "repository": ado_config.repository if ado_config else None,
            "branch": ado_config.branch if ado_config else None,
        },
        "reasoning_summary": plan.get("reasoning_summary"),
        "message": "OpenShift Builder assembled the selected delivery pipelines and prepared the implementation payload.",
    }


def push_files_to_ado(*, config: BuilderAdoConfig, files: list[dict[str, str]]) -> list[dict[str, Any]]:
    _validate_ado_config(config, require_repository=True)
    if not files:
        return []

    repository = config.repository or ""
    with httpx.Client(timeout=20.0, follow_redirects=False, headers=_ado_auth_headers(config)) as client:
        refs_response = client.get(
            _ado_project_url(config, f"_apis/git/repositories/{quote(repository, safe='')}/refs"),
            params={"filter": f"heads/{config.branch}", "api-version": "7.1"},
        )
        _raise_for_ado_response(refs_response, "branch lookup")
        refs_response.raise_for_status()
        refs = refs_response.json().get("value") or []
        if not refs:
            raise ValueError(f"Branch '{config.branch}' was not found in Azure DevOps repository '{repository}'.")
        old_object_id = refs[0].get("objectId")
        if not old_object_id:
            raise ValueError(f"Unable to resolve the head commit for branch '{config.branch}'.")

        changes = [
            {
                "changeType": "edit",
                "item": {"path": _normalize_remote_path(item["path"])},
                "newContent": {"content": item["content"], "contentType": "rawtext"},
            }
            for item in files
        ]
        push_response = client.post(
            _ado_project_url(config, f"_apis/git/repositories/{quote(repository, safe='')}/pushes"),
            params={"api-version": "7.1"},
            json={
                "refUpdates": [{"name": f"refs/heads/{config.branch}", "oldObjectId": old_object_id}],
                "commits": [{"comment": "OpenShift Builder pipeline implementation update", "changes": changes}],
            },
        )
        _raise_for_ado_response(push_response, "repository push")
        push_response.raise_for_status()
        push_payload = push_response.json()

    push_id = push_payload.get("pushId")
    return [
        {"path": _normalize_remote_path(item["path"]), "push_id": push_id, "repository": repository, "branch": config.branch}
        for item in files
    ]


def parse_ado_config(payload: dict[str, Any] | None) -> BuilderAdoConfig | None:
    if not payload:
        return None
    organization_url = str(payload.get("organization_url") or "").strip()
    project = str(payload.get("project") or "").strip()
    repository = str(payload.get("repository") or "").strip() or None
    branch = str(payload.get("branch") or "develop").strip() or "develop"
    pat = str(payload.get("pat") or "").strip()
    target_directory = str(payload.get("target_directory") or "/pipelines/generated/openshift").strip() or "/pipelines/generated/openshift"
    organization_url, project = _normalize_ado_org_project(organization_url, project)
    return BuilderAdoConfig(
        organization_url=organization_url,
        project=project,
        repository=repository,
        branch=branch,
        pat=pat,
        target_directory=target_directory,
    )


def _discover_source_roots() -> list[Path]:
    configured = os.getenv("OPENSHIFT_BUILDER_SOURCE_PATHS", "")
    configured_paths = [Path(item).expanduser() for item in _PATH_SPLIT_RE.split(configured) if item.strip()]
    repo_root = Path(__file__).resolve().parents[3]
    default_paths = [
        repo_root / "ipi-method",
        repo_root / "upi-method",
        repo_root / "azure-aro",
        repo_root / "aws-rosa",
        repo_root / "ibm-z",
        repo_root / "openshift-sre",
    ]
    roots: list[Path] = []
    for candidate in [*configured_paths, *default_paths]:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved.exists() and resolved.is_dir() and resolved not in roots:
            roots.append(resolved)
    return roots


def _iter_catalog_files(root: Path) -> list[Path]:
    suffixes = {".yml", ".yaml", ".tfvars"}
    ignored_parts = {".git", ".venv", "node_modules", "site", ".pytest_cache"}
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if any(part in ignored_parts for part in path.parts):
            continue
        paths.append(path)
    return paths


def _build_catalog_entry(root: Path, path: Path) -> BuilderCatalogEntry:
    relative_path = path.relative_to(root).as_posix()
    content = path.read_text(encoding="utf-8", errors="ignore")
    kind = _classify_file(relative_path, content)
    stage_names = [match.strip() for match in _STAGE_RE.findall(content) if match.strip()]
    template_references = [match.strip() for match in _TEMPLATE_REF_RE.findall(content) if match.strip()]
    workdir = _extract_workdir(content)
    title = path.stem.replace("-", " ").replace("_", " ").title()
    description = _describe_entry(kind=kind, relative_path=relative_path, stage_names=stage_names, template_references=template_references, workdir=workdir)
    return BuilderCatalogEntry(
        id=_catalog_entry_id(root=root, relative_path=relative_path),
        kind=kind,
        title=title,
        relative_path=relative_path,
        source_root=str(root),
        description=description,
        stage_names=stage_names,
        template_references=template_references,
        workdir=workdir,
        content=content,
    )


def _classify_file(relative_path: str, content: str) -> str:
    lowered_path = relative_path.lower()
    lowered_content = content.lower()
    if lowered_path.endswith(".tfvars") or "variables" in lowered_path or "tfvars" in lowered_path:
        return "variables"
    if "azure-pipelines" in lowered_path or "trigger:" in lowered_content or "stages:" in lowered_content or "jobs:" in lowered_content:
        return "pipeline"
    return "template"


def _extract_workdir(content: str) -> str | None:
    for pattern in (_WORKDIR_RE, _TERRAFORM_DIR_RE):
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
    return None


def _describe_entry(*, kind: str, relative_path: str, stage_names: list[str], template_references: list[str], workdir: str | None) -> str:
    parts = [f"Discovered OpenShift {kind} file at {relative_path}."]
    if stage_names:
        parts.append(f"Stages: {', '.join(stage_names)}.")
    if template_references:
        parts.append(f"Templates: {', '.join(template_references)}.")
    if workdir:
        parts.append(f"OpenShift/Terraform workdir: {workdir}.")
    return " ".join(parts)


def _catalog_index(catalog: dict[str, Any]) -> dict[str, BuilderCatalogEntry]:
    entries = []
    for group in ("pipelines", "templates", "variables"):
        entries.extend(catalog.get(group) or [])
    index: dict[str, BuilderCatalogEntry] = {}
    for entry in entries:
        catalog_entry = BuilderCatalogEntry(
            id=str(entry.get("id") or ""),
            kind=str(entry.get("kind") or "pipeline"),
            title=str(entry.get("title") or entry.get("relative_path") or "Catalog Entry"),
            relative_path=str(entry.get("relative_path") or ""),
            source_root=str(entry.get("source_root") or ""),
            description=str(entry.get("description") or ""),
            stage_names=list(entry.get("stage_names") or []),
            template_references=list(entry.get("template_references") or []),
            workdir=entry.get("workdir"),
            content=str(entry.get("content") or entry.get("content_preview") or ""),
        )
        if catalog_entry.id:
            index[catalog_entry.id] = catalog_entry
    return index


def _heuristic_pipeline_plan(*, pipelines: list[dict[str, Any]], design_snapshot: dict[str, Any] | None, prompt: str) -> dict[str, Any]:
    design_summary = _build_design_summary(design_snapshot, prompt)
    lowered = design_summary.lower()
    recommended_ids: list[str] = []
    missing_requirements: list[str] = []
    reasons: list[str] = []

    def find_matches(*keywords: str) -> list[str]:
        matches = []
        for item in pipelines:
            haystack = " ".join([
                str(item.get("id") or ""),
                str(item.get("title") or ""),
                str(item.get("relative_path") or ""),
                str(item.get("description") or ""),
                str(item.get("workdir") or ""),
            ]).lower()
            if any(keyword in haystack for keyword in keywords):
                matches.append(str(item.get("id")))
        return _dedupe(matches)

    rules = [
        (("ipi", "installer-provisioned", "baremetal", "bare metal"), ("ipi", "baremetal", "openshiftbaremetal"), "ipi-baremetal-install"),
        (("upi", "user-provisioned", "static ip", "external load balancer"), ("upi", "baremetal", "openshiftbaremetal"), "upi-baremetal-install"),
        (("acm", "advanced cluster management", "multicluster", "governance"), ("acm", "import", "governance"), "acm-governance-import"),
        (("disaster recovery", "dr", "failover", "replication"), ("dr", "disaster", "acm-dr"), "openshift-dr-pipeline"),
        (("gitops", "argocd", "argo cd"), ("gitops", "argocd", "day2"), "openshift-gitops-day2"),
        (("virtualization", "cnv", "vm migration", "openshift virtualization"), ("cnv", "vm-migration", "virtualization"), "openshift-virtualization-cnv"),
        (("migration", "mtc", "application migration"), ("mtc", "migration"), "openshift-migration-mtc"),
        (("ceph", "odf", "rook", "storage"), ("ceph", "odf", "storage"), "openshift-storage-odf"),
        (("aro", "azure red hat openshift"), ("aro", "azure"), "azure-aro-deployment"),
        (("rosa", "red hat openshift service on aws"), ("rosa", "aws"), "aws-rosa-deployment"),
        (("ibm z", "s390x", "z/", "ibmz"), ("ibm", "ibm-z", "s390x"), "ibm-z-openshift-deployment"),
    ]

    for signal_tokens, match_keywords, missing_slug in rules:
        if any(token in lowered for token in signal_tokens):
            matches = find_matches(*match_keywords)
            if matches:
                recommended_ids.extend(matches)
                reasons.append(f"Detected {missing_slug.replace('-', ' ')} requirements in the Architect design.")
            else:
                missing_requirements.append(missing_slug)

    if any(token in lowered for token in ["pipeline", "terraform", "day 2", "day2", "automation", "builder"]):
        matches = find_matches("pipeline", "day2", "terraform", "azure-pipelines")
        if matches:
            recommended_ids.extend(matches)
            reasons.append("Detected OpenShift delivery automation requirements that align with existing Azure Pipeline wrappers.")
        else:
            missing_requirements.append("openshift-delivery-pipeline")

    if not recommended_ids and pipelines:
        recommended_ids.append(str(pipelines[0].get("id")))
        reasons.append("No exact keyword match was found, so OpenShift Builder suggested the first available pipeline as a starting point.")

    if not missing_requirements and any(token in lowered for token in ["new pipeline", "custom pipeline", "missing pipeline", "not present"]):
        missing_requirements.append("custom-openshift-delivery-pipeline")

    return {
        "recommended_pipeline_ids": _dedupe(recommended_ids),
        "missing_requirements": _dedupe(missing_requirements),
        "reasoning_summary": " ".join(reasons) if reasons else "Used the available OpenShift delivery catalog and Architect design summary to determine the best pipeline fit.",
        "source": "heuristic",
    }


def _llm_pipeline_plan(
    *,
    pipelines: list[dict[str, Any]],
    design_snapshot: dict[str, Any] | None,
    prompt: str,
    settings: Settings,
    heuristic: dict[str, Any],
) -> dict[str, Any] | None:
    if not pipelines:
        return None
    try:
        client = ModelClient(settings)
        messages = [
            {
                "role": "system",
                "content": (
                    "You map Red Hat OpenShift architecture designs to an inventory of Azure DevOps delivery pipelines. "
                    "Return strict JSON with keys recommended_pipeline_ids, missing_requirements, and reasoning_summary. "
                    "Only recommend pipeline ids that exist in the supplied inventory. Prefer existing IPI, UPI, ACM, DR, CNV, MTC, Ceph, ARO, ROSA, and IBM Z pipelines before declaring gaps."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "design_summary": _build_design_summary(design_snapshot, prompt),
                        "inventory": [
                            {
                                "id": item.get("id"),
                                "title": item.get("title"),
                                "description": item.get("description"),
                                "workdir": item.get("workdir"),
                                "stage_names": item.get("stage_names"),
                            }
                            for item in pipelines[:30]
                        ],
                        "heuristic": heuristic,
                    }
                ),
            },
        ]
        raw = client.chat(messages, temperature=0.1)
        payload = _extract_json_object(raw)
        if not isinstance(payload, dict):
            return None
        return {
            "recommended_pipeline_ids": [
                item for item in _dedupe(payload.get("recommended_pipeline_ids") or [])
                if any(item == candidate.get("id") for candidate in pipelines)
            ],
            "missing_requirements": _dedupe(payload.get("missing_requirements") or []),
            "reasoning_summary": str(payload.get("reasoning_summary") or "").strip() or heuristic.get("reasoning_summary"),
            "source": "llm",
        }
    except Exception:
        return None


def _generate_missing_pipeline_files(
    *,
    missing_requirements: list[str],
    design_snapshot: dict[str, Any] | None,
    prompt: str,
    settings: Settings,
    target_directory: str,
) -> list[dict[str, Any]]:
    if not missing_requirements:
        return []
    llm_generated = _llm_generated_pipeline_files(
        missing_requirements=missing_requirements,
        design_snapshot=design_snapshot,
        prompt=prompt,
        settings=settings,
        target_directory=target_directory,
    )
    if llm_generated:
        return llm_generated

    design_summary = _build_design_summary(design_snapshot, prompt)
    generated: list[dict[str, Any]] = []
    base_dir = _normalize_remote_path(target_directory)
    for requirement in missing_requirements:
        slug = _slugify(requirement)
        display_name = requirement.replace("-", " ").replace("_", " ").title()
        pipeline_path = f"{base_dir}/{slug}.yml"
        variable_path = f"{base_dir}/{slug}-variables.yml"
        workdir = f"openshift/{slug}"
        pipeline_content = "\n".join(
            [
                "trigger: none",
                "",
                "parameters:",
                "  - name: action",
                "    displayName: Terraform action",
                "    type: string",
                "    default: plan",
                "    values:",
                "      - plan",
                "      - apply",
                "",
                "stages:",
                f"  - stage: deliver_{slug[:40].replace('-', '_')}",
                f"    displayName: Deliver {display_name}",
                "    jobs:",
                "      - job: terraform_openshift_delivery",
                "        displayName: Terraform/OpenShift delivery wrapper",
                "        steps:",
                "          - checkout: self",
                "          - script: |",
                "              set -euo pipefail",
                "              terraform -chdir=$(workdir) init",
                "              terraform -chdir=$(workdir) validate",
                "              terraform -chdir=$(workdir) plan -out=tfplan",
                "            displayName: Terraform validate and plan",
                "          - script: |",
                "              set -euo pipefail",
                "              if [ '${{ parameters.action }}' = 'apply' ]; then terraform -chdir=$(workdir) apply -auto-approve tfplan; fi",
                "            displayName: Approval-gated Terraform apply",
                "            condition: and(succeeded(), eq('${{ parameters.action }}', 'apply'))",
                "",
                "variables:",
                f"  workdir: {workdir}",
                "  openshift_service_connection: replace-with-openshift-service-connection",
                "  terraform_state_backend: replace-with-state-backend",
                "",
                f"# Generated by OpenShift Builder from Architect context: {design_summary[:240]}",
            ]
        )
        variable_content = "\n".join(
            [
                "variables:",
                "  terraform_version: 1.8.5",
                f"  workdir: {workdir}",
                f"  project_name: {slug}",
                "  openshift_cluster: replace-with-cluster-name",
                "  openshift_namespace: openshift-config",
                "  ado_environment: openshift-builder-generated",
                "  oc_service_connection: replace-with-openshift-service-connection",
                "  state_backend: replace-with-terraform-state-backend",
                f"  design_summary: >-\n    {design_summary[:260] or 'Generated from the latest OpenShift Builder request.'}",
            ]
        )
        generated.extend(
            [
                {"requirement": requirement, "path": pipeline_path, "language": "yaml", "kind": "pipeline", "content": pipeline_content},
                {"requirement": requirement, "path": variable_path, "language": "yaml", "kind": "variables", "content": variable_content},
            ]
        )
    return generated


def _llm_generated_pipeline_files(
    *,
    missing_requirements: list[str],
    design_snapshot: dict[str, Any] | None,
    prompt: str,
    settings: Settings,
    target_directory: str,
) -> list[dict[str, Any]] | None:
    try:
        client = ModelClient(settings)
        messages = [
            {
                "role": "system",
                "content": (
                    "Generate Azure DevOps YAML pipeline wrapper files for Red Hat OpenShift delivery automation. "
                    "Return strict JSON with a files array. Each file must have path, kind, language, and content. "
                    "Use safe plan-first Terraform/OpenShift steps and placeholders for secrets/service connections."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "missing_requirements": missing_requirements,
                        "target_directory": target_directory,
                        "design_summary": _build_design_summary(design_snapshot, prompt),
                        "constraints": {
                            "platform": "Red Hat OpenShift",
                            "execution": "plan-first with explicit approval before apply",
                            "secrets": "never hard-code credentials or tokens",
                        },
                    }
                ),
            },
        ]
        raw = client.chat(messages, temperature=0.2)
        payload = _extract_json_object(raw)
        files = payload.get("files") if isinstance(payload, dict) else None
        if not isinstance(files, list):
            return None
        sanitized = []
        for item in files:
            if not isinstance(item, dict):
                continue
            path = _normalize_remote_path(str(item.get("path") or ""))
            content = str(item.get("content") or "")
            if not path or not content:
                continue
            sanitized.append({"path": path, "kind": str(item.get("kind") or "pipeline"), "language": str(item.get("language") or "yaml"), "content": content})
        return sanitized or None
    except Exception:
        return None


def _build_design_summary(design_snapshot: dict[str, Any] | None, prompt: str) -> str:
    if design_snapshot:
        planning = design_snapshot.get("planning") or {}
        diagram = design_snapshot.get("diagram") or {}
        summary = {
            "prompt": design_snapshot.get("prompt") or prompt,
            "pattern_id": planning.get("pattern_id"),
            "pattern_label": planning.get("pattern_label"),
            "reasoning_summary": planning.get("reasoning_summary"),
            "node_count": len(diagram.get("nodes") or []),
            "edge_count": len(diagram.get("edges") or []),
            "cluster_scope": design_snapshot.get("cluster_scope"),
            "openshift_state_included": design_snapshot.get("openshift_state_included"),
        }
        return json.dumps(summary, default=str)
    return str(prompt or "").strip()


def _validate_ado_config(config: BuilderAdoConfig | None, *, require_repository: bool = False) -> None:
    if config is None or not config.organization_url or not config.project or not config.pat:
        raise ValueError("Azure DevOps organization URL, project, and PAT are required.")
    if require_repository and not config.repository:
        raise ValueError("Azure DevOps repository is required for repository push operations.")
    if not config.organization_url.startswith(("https://", "http://")):
        raise ValueError("Azure DevOps organization URL must start with https:// or http://.")


def _normalize_ado_org_project(organization_url: str, project: str) -> tuple[str, str]:
    parsed = urlparse(organization_url)
    if not parsed.scheme or not parsed.netloc:
        return organization_url.rstrip("/"), project.strip("/")
    path_parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    normalized_project = project.strip("/")
    normalized_path_parts = list(path_parts)
    if parsed.netloc.lower() == "dev.azure.com" and len(path_parts) >= 2:
        if not normalized_project:
            normalized_project = path_parts[1]
        normalized_path_parts = path_parts[:1]
    elif parsed.netloc.lower().endswith(".visualstudio.com") and path_parts:
        if not normalized_project:
            normalized_project = path_parts[0]
        normalized_path_parts = []
    normalized_path = "/" + "/".join(quote(part, safe="") for part in normalized_path_parts) if normalized_path_parts else ""
    return parsed._replace(path=normalized_path, params="", query="", fragment="").geturl().rstrip("/"), normalized_project


def _repository_matches(configured_repository: str, repository_name: str, repository_id: str | None = None) -> bool:
    configured = str(configured_repository or "").strip()
    candidates = [str(repository_name or "").strip(), str(repository_id or "").strip()]
    if not configured:
        return True
    if configured in candidates:
        return True
    normalized_configured = _normalize_repo_identity(configured)
    return any(normalized_configured == _normalize_repo_identity(candidate) for candidate in candidates if candidate)


def _normalize_repo_identity(value: str) -> str:
    return _SLUG_RE.sub("", str(value or "").strip().lower())


def _ado_auth_headers(config: BuilderAdoConfig) -> dict[str, str]:
    token = b64encode(f":{config.pat}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _ado_project_url(config: BuilderAdoConfig, path: str) -> str:
    return f"{config.organization_url.rstrip('/')}/{quote(config.project, safe='')}/{path.lstrip('/')}"


def _raise_for_ado_response(response: httpx.Response, operation: str) -> None:
    if response.status_code in {301, 302, 303, 307, 308}:
        location = response.headers.get("location", "")
        if "_signin" in location or "login" in location.lower():
            raise ValueError(
                "Azure DevOps redirected to sign-in during "
                f"{operation}. Check that the PAT was pasted correctly, is not expired, has Code read access "
                "(and Code read/write for pushes), and that the organization URL is the org root like "
                "https://dev.azure.com/Kyndryl-India while Project is entered separately."
            )
        raise ValueError(f"Azure DevOps returned redirect {response.status_code} during {operation}. Check the organization URL and project name.")
    if response.status_code in {401, 403}:
        raise ValueError(
            f"Azure DevOps rejected the PAT during {operation} with HTTP {response.status_code}. "
            "Verify PAT scopes, project access, SSO/organization authorization, and token expiry."
        )


def _fetch_ado_pipeline_detail(*, client: httpx.Client, config: BuilderAdoConfig, pipeline_id: Any) -> dict[str, Any] | None:
    if pipeline_id is None:
        return None
    try:
        response = client.get(
            _ado_project_url(config, f"_apis/pipelines/{pipeline_id}"),
            params={"api-version": "7.1-preview.1"},
        )
        _raise_for_ado_response(response, "pipeline detail lookup")
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except httpx.HTTPStatusError:
        return None


def _discover_ado_build_definition_catalog(*, client: httpx.Client, config: BuilderAdoConfig) -> tuple[list[BuilderCatalogEntry], dict[str, dict[str, Any]]]:
    response = client.get(
        _ado_project_url(config, "_apis/build/definitions"),
        params={"api-version": "7.1", "includeAllProperties": "true"},
    )
    _raise_for_ado_response(response, "build definition discovery")
    response.raise_for_status()
    definition_rows = response.json().get("value") or []
    entries: list[BuilderCatalogEntry] = []
    repositories_seen: dict[str, dict[str, Any]] = {}

    for row in definition_rows:
        detail = _fetch_ado_build_definition_detail(client=client, config=config, definition_id=row.get("id")) or row
        repository = detail.get("repository") or {}
        repository_name = str(repository.get("name") or repository.get("id") or "").strip()
        repository_id = str(repository.get("id") or repository.get("name") or config.repository or "").strip()
        if config.repository and repository_name and not _repository_matches(config.repository, repository_name, repository_id):
            continue

        process = detail.get("process") or {}
        yaml_path = str(
            process.get("yamlFilename")
            or process.get("yamlFileName")
            or process.get("yamlPath")
            or detail.get("yamlFilename")
            or detail.get("yamlFileName")
            or ""
        ).strip()
        content = ""
        if yaml_path and (repository_id or config.repository):
            content = _fetch_ado_yaml_content(
                client=client,
                config=config,
                repository=repository_id or config.repository or "",
                path=yaml_path,
            )

        definition_id = str(detail.get("id") or row.get("id") or detail.get("name") or "definition")
        title = str(detail.get("name") or row.get("name") or f"Build Definition {definition_id}")
        relative_path = yaml_path.lstrip("/") or f"azure-pipelines/build-definitions/{_slugify(title)}.yml"
        source_root = f"azure-devops-build:{config.project}"
        if repository_name:
            source_root = f"{source_root}/{repository_name}"
            repositories_seen[repository_name] = {"id": repository_id, "name": repository_name}

        description_parts = [f"Azure DevOps build definition '{title}' from project {config.project}."]
        if repository_name:
            description_parts.append(f"Repository: {repository_name}.")
        if yaml_path:
            description_parts.append(f"YAML path: {yaml_path}.")
        else:
            description_parts.append("This appears to be a classic build definition or a definition whose YAML path is not exposed by Azure DevOps.")
        if yaml_path and not content:
            description_parts.append("YAML content was not returned for this build definition.")

        entries.append(
            BuilderCatalogEntry(
                id=f"ado-build-{definition_id}-{_slugify(title)}",
                kind="pipeline",
                title=title,
                relative_path=relative_path,
                source_root=source_root,
                description=" ".join(description_parts),
                stage_names=[match.strip() for match in _STAGE_RE.findall(content) if match.strip()],
                template_references=[match.strip() for match in _TEMPLATE_REF_RE.findall(content) if match.strip()],
                workdir=_extract_workdir(content),
                content=content,
            )
        )

    return entries, repositories_seen


def _fetch_ado_build_definition_detail(*, client: httpx.Client, config: BuilderAdoConfig, definition_id: Any) -> dict[str, Any] | None:
    if definition_id is None:
        return None
    try:
        response = client.get(
            _ado_project_url(config, f"_apis/build/definitions/{definition_id}"),
            params={"api-version": "7.1", "includeAllProperties": "true"},
        )
        _raise_for_ado_response(response, "build definition detail lookup")
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except httpx.HTTPStatusError:
        return None


def _fetch_ado_yaml_content(*, client: httpx.Client, config: BuilderAdoConfig, repository: str, path: str) -> str:
    if not repository or not path:
        return ""
    params = {"path": _normalize_remote_path(path), "includeContent": "true", "api-version": "7.1"}
    if config.branch:
        params["versionDescriptor.version"] = config.branch
        params["versionDescriptor.versionType"] = "branch"
    try:
        response = client.get(
            _ado_project_url(config, f"_apis/git/repositories/{quote(repository, safe='')}/items"),
            params=params,
        )
        _raise_for_ado_response(response, "YAML content lookup")
        response.raise_for_status()
        if "application/json" in response.headers.get("content-type", "").lower():
            payload = response.json()
            return str(payload.get("content") or "") if isinstance(payload, dict) else ""
        return response.text
    except httpx.HTTPStatusError:
        return ""


def _extract_json_object(value: str) -> dict[str, Any] | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _slugify(value: str) -> str:
    lowered = str(value or "").strip().lower()
    return _SLUG_RE.sub("-", lowered).strip("-") or "builder-item"


def _catalog_entry_id(*, root: Path, relative_path: str) -> str:
    base_id = _slugify(relative_path.rsplit(".", 1)[0])
    root_label = _source_root_label(root)
    if root_label:
        return _slugify(f"{root_label}-{base_id}")
    return base_id


def _source_root_label(root: Path) -> str | None:
    name = root.name.lower()
    if name in {"ipi-method", "upi-method", "azure-aro", "aws-rosa", "ibm-z", "openshift-sre"}:
        return name
    return None


def _dedupe(values: list[str] | tuple[str, ...] | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _normalize_remote_path(path: str) -> str:
    cleaned = "/" + str(path or "").strip().lstrip("/")
    return cleaned.replace("//", "/")
