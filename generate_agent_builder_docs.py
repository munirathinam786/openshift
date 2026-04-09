#!/usr/bin/env python3
"""Generate documentation pages for Agent Builder DR (IPI) and Agent Builder (UPI DC/DR)."""

import os
import pathlib

BASE = pathlib.Path(__file__).parent

# ============================================================================
# Helper: read source file
# ============================================================================
def read_src(path):
    return (BASE / path).read_text()


# ============================================================================
# Environment definitions
# ============================================================================
ENVS = [
    {
        "id": "ipi-dr",
        "label": "IPI DR Secondary",
        "nav_label": "IPI Agent Builder DR (ipi-method/agent-builder-dr)",
        "src_dir": "ipi-method/agent-builder-dr",
        "doc_dir": "docs/code/ipi-method/agent-builder-dr",
        "cluster": "ocp-ai-dr",
        "bastion": "10.143.41.10",
        "domain": "dr.example.com",
        "main_header": "DR Secondary Deployment on OpenShift Baremetal (IPI)",
        "tfvars_header": "terraform.tfvars (IPI DR Secondary)",
        "has_pipelines": False,
    },
    {
        "id": "upi-dc",
        "label": "UPI DC Primary",
        "nav_label": "UPI Agent Builder DC (upi-method/agent-builder)",
        "src_dir": "upi-method/agent-builder",
        "doc_dir": "docs/code/upi-method/agent-builder",
        "cluster": "ocp-ai-upi",
        "bastion": "10.142.41.10",
        "domain": "example.com",
        "main_header": "Deployment on OpenShift Baremetal (UPI DC Primary)",
        "tfvars_header": "terraform.tfvars (UPI DC Primary)",
        "has_pipelines": True,
    },
    {
        "id": "upi-dr",
        "label": "UPI DR Secondary",
        "nav_label": "UPI Agent Builder DR (upi-method/agent-builder-dr)",
        "src_dir": "upi-method/agent-builder-dr",
        "doc_dir": "docs/code/upi-method/agent-builder-dr",
        "cluster": "ocp-ai-upi-dr",
        "bastion": "10.143.41.10",
        "domain": "dr.example.com",
        "main_header": "DR Secondary Deployment on OpenShift Baremetal (UPI)",
        "tfvars_header": "terraform.tfvars (UPI DR Secondary)",
        "has_pipelines": False,
    },
]


def generate_main_md(env):
    src = read_src(f"{env['src_dir']}/main.tf")
    return f"""# Agent Builder Factory — main.tf ({env['label']})

Main orchestration file for the Agent Builder Factory platform (`{env['src_dir']}/`).
Deploys 14 microservices on OpenShift Baremetal including PostgreSQL, MongoDB, Redis, Temporal, Ollama (local LLM), LiteLLM Proxy, and all application services.

!!! info "Environment: {env['label']}"
    **Cluster:** `{env['cluster']}` | **Bastion:** `{env['bastion']}` | **Domain:** `{env['domain']}`

## Module Dependency Chain

```
namespace
├── postgresql ──┬── temporal ──┬── temporal_workers
│                │              ├── litellm ──── agent_builder_api ──── agent_builder_ui
│                │              └── agent_deployment_service
├── mongodb ─────┤              └── agent_registry ──── a2a_gateway
├── redis ───────┘
├── ollama (conditional: enable_ollama)
└── tool_catalog
```

## Source Code

```hcl
{src}```
"""


def generate_variables_md(env):
    src = read_src(f"{env['src_dir']}/variables.tf")
    return f"""# Agent Builder Factory — variables.tf ({env['label']})

All input variables for the Agent Builder Factory platform. Organized by functional area: bastion connection, platform configuration, database credentials, LLM settings (cloud + local), authentication, and GitHub integration.

## Source Code

```hcl
{src}```
"""


def generate_tfvars_md(env):
    src = read_src(f"{env['src_dir']}/terraform.tfvars")
    return f"""# Agent Builder Factory — terraform.tfvars ({env['label']})

Default variable values for the Agent Builder Factory deployment on the **{env['label']}** environment. Customize for your environment — replace all `REPLACE_*` placeholders with actual secrets.

!!! info "Key Values"
    | Variable | Value |
    |----------|-------|
    | `bastion_host` | `{env['bastion']}` |
    | `cluster_name` | `{env['cluster']}` |
    | `base_domain` | `{env['domain']}` |

## Source Code

```hcl
{src}```
"""


def generate_outputs_md(env):
    src = read_src(f"{env['src_dir']}/outputs.tf")
    return f"""# Agent Builder Factory — outputs.tf ({env['label']})

Terraform outputs for the Agent Builder Factory platform on the **{env['label']}** environment. Provides URLs for all deployed services.

## Source Code

```hcl
{src}```
"""


def generate_versions_md(env):
    src = read_src(f"{env['src_dir']}/versions.tf")
    return f"""# Agent Builder Factory — versions.tf ({env['label']})

Terraform and provider version constraints for the Agent Builder Factory platform.

## Source Code

```hcl
{src}```
"""


def generate_pipeline_md(env, day):
    if day == 1:
        filename = "azure-pipelines-agent-builder.yml"
        title = "Azure DevOps Pipeline (Day 1 — UPI)"
        desc = "Azure DevOps Pipeline for Day 1 deployment of the Agent Builder Factory platform on OpenShift Baremetal (UPI). Features 6 stages: container image build, data layer (PostgreSQL/MongoDB/Redis), infrastructure (Temporal/Ollama/LiteLLM), application services, validation, and summary."
    else:
        filename = "azure-pipelines-agent-builder-day2.yml"
        title = "Azure DevOps Pipeline (Day 2 — UPI)"
        desc = "Azure DevOps Pipeline for Day 2 operations of the Agent Builder Factory platform on OpenShift Baremetal (UPI). Supports scaling, LLM model changes, laptop Ollama connectivity, container image updates, secret rotation, and rolling restarts."

    # Pipeline YAMLs live at method root, not inside agent-builder/
    method_dir = env['src_dir'].split('/')[0]  # e.g. "upi-method"
    src = read_src(f"{method_dir}/{filename}")
    return f"""# Agent Builder Factory — {title}

{desc}

## Source Code

```yaml
{src}```
"""


def main():
    created = []

    for env in ENVS:
        doc_dir = BASE / env["doc_dir"]
        doc_dir.mkdir(parents=True, exist_ok=True)

        files = {
            "main.md": generate_main_md(env),
            "variables.md": generate_variables_md(env),
            "tfvars.md": generate_tfvars_md(env),
            "outputs.md": generate_outputs_md(env),
            "versions.md": generate_versions_md(env),
        }

        if env["has_pipelines"]:
            files["azure-pipelines-agent-builder.md"] = generate_pipeline_md(env, 1)
            files["azure-pipelines-agent-builder-day2.md"] = generate_pipeline_md(env, 2)

        for fname, content in files.items():
            path = doc_dir / fname
            path.write_text(content)
            created.append(str(path.relative_to(BASE)))

    print(f"Created {len(created)} documentation files:")
    for f in created:
        print(f"  ✓ {f}")


if __name__ == "__main__":
    main()
