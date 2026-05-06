# Documentation Tooling — MkDocs Generation and Local Preview

This repository contains not only Terraform and pipeline code, but also the tooling that builds and refreshes the documentation site. This page explains the files that make the docs reproducible and the simplest workflow for keeping the site synchronized with the live sources.

## What this tooling covers

The documentation workflow is driven by five repository files:

| File | Purpose |
| --- | --- |
| `generate_agent_builder_docs.py` | Generates Agent Builder code-reference pages from live Terraform and pipeline source files. |
| `generate_platform_code_reference_docs.py` | Generates the AWS ROSA, Azure ARO, and IBM Z platform code-reference pages from live Terraform and pipeline source files. |
| `compose.yaml` | Preferred local container workflow for serving the docs with Podman. |
| `Containerfile` | Container image definition for local MkDocs preview. |
| `requirements.txt` | Python package versions for MkDocs and related plugins. |

Together, these files ensure the docs are not maintained by hand alone. They let the repo regenerate documentation pages from source code, build a containerized preview environment, and serve the site locally on port `8000`.

## Documentation generation flow

```text
Terraform / pipeline source files
        │
        ├── generate_agent_builder_docs.py
        │       └── writes markdown pages under docs/code/...
        │
        ├── generate_platform_code_reference_docs.py
        │       └── writes full-code platform pages under docs/aws-rosa/, docs/azure-aro/, and docs/ibm-z/
        │
        ├── mkdocs.yml
        │       └── defines navigation and site structure
        │
        └── compose.yaml + Containerfile
                └── build and run local docs preview with Podman
```

## `generate_agent_builder_docs.py`

This script reads live source files from the Agent Builder environments and writes Markdown code-reference pages into `docs/code/...`.

### Why the Agent Builder generator matters

- keeps Agent Builder code-reference docs synchronized with the real Terraform and pipeline files
- avoids manually duplicating large source blocks into documentation pages
- ensures IPI DR and UPI Agent Builder pages can be regenerated from source instead of being edited by hand

## `generate_platform_code_reference_docs.py`

This script reads the live sources for `aws-rosa/`, `azure-aro/`, and `ibm-z/` and rewrites the platform `code-reference.md` pages so they contain the full source instead of only excerpts and prose summaries.

### Why the platform generator matters

- keeps the platform reference pages synchronized with the real Terraform and pipeline files
- fixes excerpt-only docs where sections like `modules/networking` looked incomplete in the rendered site
- makes the MkDocs pages usable as a true code reference without forcing readers to jump back and forth to the repository tree

## Local preview files

The remaining files handle the actual preview environment:

- `compose.yaml` starts the documentation stack with Podman Compose
- `Containerfile` defines the image used for local preview and MkDocs execution
- `requirements.txt` pins the MkDocs and plugin dependencies

## Typical refresh workflow

When Terraform, pipeline, or documentation structure changes, use this flow:

```bash
python3 generate_agent_builder_docs.py
python3 generate_platform_code_reference_docs.py
podman compose up -d
```

After the container starts, review the site at `http://localhost:8000/terraform-iac/`.

## Notes

- If Podman Compose fails with a stale network label mismatch, remove `terraform-iac-docs_default` and rerun the compose command.
- The generated pages are intended to be derived artifacts. Prefer changing the source Terraform or pipeline files first, then regenerating the docs.
- The `mkdocs.yml` file remains the source of truth for site navigation.

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
