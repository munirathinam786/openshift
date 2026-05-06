# Documentation Tooling — MkDocs Generation and Local Preview

This repository contains not only Terraform and pipeline code, but also the **code that builds and generates the documentation site itself**. That tooling was previously under-documented in MkDocs, so this page explains the files that make the docs reproducible.

## What this tooling covers

The documentation workflow is driven by four repository files:

| File | Purpose |
|---|---|
| `generate_agent_builder_docs.py` | Generates Agent Builder code-reference pages from live Terraform and pipeline source files |
| `compose.yaml` | Preferred local container workflow for serving the docs with Podman |
| `Containerfile` | Container image definition for local MkDocs preview |
| `requirements.txt` | Python package versions for MkDocs and related plugins |

Together, these files ensure the docs are not maintained by hand alone. They let the repo regenerate documentation pages from source code, build a containerized preview environment, and serve the site locally on port `8000`.

## Documentation generation flow

```text
Terraform / pipeline source files
        │
        ├── generate_agent_builder_docs.py
        │       └── writes markdown pages under docs/code/...
        │
        ├── mkdocs.yml
        │       └── defines navigation and site structure
        │
        └── compose.yaml + Containerfile
                └── build and run local docs preview with Podman
```

## `generate_agent_builder_docs.py`

This script reads live source files from the Agent Builder environments and writes Markdown code-reference pages into `docs/code/...`.

### Why it matters

- keeps Agent Builder code-reference docs synchronized with the real Terraform and pipeline files
- avoids manually duplicating large source blocks into documentation pages
- ensures IPI DR and UPI Agent Builder pages can be regenerated from source instead of being edited by hand

### Source code

```python
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
```

## `compose.yaml`

This file defines the preferred local container workflow for serving the documentation site with Podman.

### Why it matters

- standardizes local preview on `podman compose up -d --build`
- mounts the repository into the container so edits are reflected without maintaining a separate copy
- exposes the MkDocs server on port `8000`

### Source code

```yaml
# Author: Sathishkumar Munirathinam

# Preferred local container workflow: Podman
# Build and start with:
#   podman compose up -d --build

services:
  terraform-iac-docs:
    restart: always
    image: "localhost/terraform-iac-docs:local.1.0.0"
    build:
      context: ./
      dockerfile: ./Containerfile
    hostname: terraform-iac-docs
    container_name: terraform-iac-docs
    tty: true
    volumes:
      - ./:/docs:Z
    ports:
      - "8000:8000"
```

## `Containerfile`

This file defines the local documentation image used by the compose workflow.

### Why it matters

- starts from `squidfunk/mkdocs-material`
- installs additional packages the site needs beyond the base image
- provides a reproducible local preview environment for documentation validation

### Source code

```dockerfile
FROM squidfunk/mkdocs-material:9.5.24

# Set working directory
WORKDIR /docs

# Update pip version
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --upgrade pip

# Install missing packages
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org regex mkdocs-glightbox mkdocs-material-extensions

# mkdocs port
EXPOSE 8000
```

## `requirements.txt`

This file pins the Python packages needed for the MkDocs toolchain when running outside the container image.

### Source code

```text
mkdocs==1.6.0
mkdocs-material==9.5.24
jinja2==3.1.3
mkdocs-glightbox==0.4.0
```

## Practical usage

### Regenerate generated docs

```bash
python3 generate_agent_builder_docs.py
```

### Preview docs locally

```bash
podman compose up -d --build
```

Then open:

```text
http://localhost:8000/terraform-iac/
```

## What this page fixes in coverage

Before this page existed, the repo already documented the Terraform platforms and pipelines, but the **documentation-generation code itself** was mostly invisible in the published site navigation. This page closes that gap and makes the repository's docs workflow part of the documented codebase.

## Related pages

- [Home](../index.md)
- [Agent Builder Deployment Guide](../clusters/terraform-agent-builder.md)
- [Terraform Code Walkthrough](terraform-code-walkthrough.md)