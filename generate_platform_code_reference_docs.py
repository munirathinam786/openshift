#!/usr/bin/env python3
"""Generate full-code platform reference pages for AWS ROSA, Azure ARO, and IBM Z."""

from __future__ import annotations

import pathlib
import textwrap
from typing import Iterable

BASE = pathlib.Path(__file__).parent


def read_src(path: str) -> str:
    return (BASE / path).read_text().rstrip() + "\n"


def fence(language: str, content: str) -> str:
    return f"```{language}\n{content.rstrip()}\n```"


def bullets(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


PLATFORMS = [
    {
        "doc_path": "docs/aws-rosa/code-reference.md",
        "title": "AWS ROSA Terraform Code Reference",
        "intro": "This page explains the Terraform implementation under the repository's `aws-rosa/` folder and includes the full source for every top-level Terraform file, the sample `terraform.tfvars`, the delivery pipeline, and each module entry point.",
        "diagram_alt": "AWS ROSA Terraform Modules",
        "diagram_svg": "../diagrams/aws-rosa/03-aws-rosa-terraform-modules.svg",
        "diagram_drawio": "../diagrams/aws-rosa/03-aws-rosa-terraform-modules.drawio",
        "tree": textwrap.dedent(
            """\
            aws-rosa/
            ├── main.tf
            ├── variables.tf
            ├── outputs.tf
            ├── versions.tf
            ├── terraform.tfvars
            ├── azure-pipelines-rosa.yml
            └── modules/
                ├── networking/
                ├── vpc-endpoints/
                ├── rosa-automation/
                └── alb-operator/
            """
        ).rstrip(),
        "sections": [
            {
                "heading": "`main.tf` orchestration",
                "body": [
                    "The root module composes the ROSA workflow in four parts:",
                    bullets([
                        "`networking` — creates the VPC, subnets, route tables, NAT, and security groups",
                        "`vpc-endpoints` — creates AWS interface and gateway endpoints for private worker access",
                        "`rosa-automation` — renders preflight, cluster create, Route 53, and delete scripts",
                        "`alb-operator` — creates the IAM policy and install assets for ALB-backed ingress",
                    ]),
                    "This is not a placeholder layout with empty modules. The root module wires concrete Terraform resources together and emits executable operational assets for the pieces that must be driven by the ROSA CLI.",
                ],
                "source": "aws-rosa/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`variables.tf`",
                "body": [
                    "The ROSA variables model AWS-specific concerns, including VPC layout, ROSA STS cluster settings, Route 53 integration, CLI paths, ALB defaults, and tagging.",
                ],
                "source": "aws-rosa/variables.tf",
                "language": "hcl",
            },
            {
                "heading": "`outputs.tf`",
                "body": [
                    "The outputs surface the infrastructure IDs and generated helper assets operators need after `terraform apply`.",
                ],
                "source": "aws-rosa/outputs.tf",
                "language": "hcl",
            },
            {
                "heading": "`versions.tf`",
                "body": [
                    "Provider and Terraform version constraints for the ROSA blueprint.",
                ],
                "source": "aws-rosa/versions.tf",
                "language": "hcl",
            },
            {
                "heading": "`terraform.tfvars`",
                "body": [
                    "Sample input values for the AWS ROSA deployment. Replace the example account, DNS, and credential-related values to match your environment.",
                ],
                "source": "aws-rosa/terraform.tfvars",
                "language": "hcl",
            },
            {
                "heading": "`azure-pipelines-rosa.yml`",
                "body": [
                    "Azure DevOps pipeline for validating the ROSA Terraform, rendering helper assets, and optionally executing the generated ROSA and ALB scripts.",
                ],
                "source": "aws-rosa/azure-pipelines-rosa.yml",
                "language": "yaml",
            },
            {
                "heading": "`modules/networking`",
                "body": [
                    "This module creates the AWS primitives ROSA depends on in the customer account: VPC, public/private subnets, internet gateway, route tables, optional NAT gateways, and the security groups used by worker nodes and interface endpoints.",
                ],
                "source": "aws-rosa/modules/networking/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/vpc-endpoints`",
                "body": [
                    "This module turns the ROSA network into a private-service-aware VPC by creating interface endpoints such as STS, EC2, ECR, ELB, and CloudWatch plus gateway endpoints such as S3.",
                ],
                "source": "aws-rosa/modules/vpc-endpoints/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/rosa-automation`",
                "body": [
                    "This module renders the operational hand-off files under `aws-rosa/generated/<cluster>/`, including preflight, create, Route 53, delete, and summary assets. When `auto_execute_rosa=true`, Terraform can also execute the generated preflight and cluster creation scripts during apply.",
                ],
                "source": "aws-rosa/modules/rosa-automation/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/alb-operator`",
                "body": [
                    "This module adds the application ingress extension path by creating the AWS IAM policy, writing the policy JSON to disk, rendering `install-alb-operator.sh`, and rendering a sample `sample-alb-ingress.yaml` manifest.",
                ],
                "source": "aws-rosa/modules/alb-operator/main.tf",
                "language": "hcl",
            },
        ],
    },
    {
        "doc_path": "docs/azure-aro/code-reference.md",
        "title": "Azure Red Hat OpenShift (ARO) Terraform Code Reference",
        "intro": "This page explains the Terraform implementation under the repository's `azure-aro/` folder and includes the full source for the top-level Terraform files, the sample `terraform.tfvars`, the Azure DevOps pipeline, and each module entry point.",
        "diagram_alt": "Azure Red Hat OpenShift Terraform Modules",
        "diagram_svg": "../diagrams/azure-aro/03-azure-aro-terraform-modules.svg",
        "diagram_drawio": "../diagrams/azure-aro/03-azure-aro-terraform-modules.drawio",
        "tree": textwrap.dedent(
            """\
            azure-aro/
            ├── main.tf
            ├── variables.tf
            ├── outputs.tf
            ├── versions.tf
            ├── terraform.tfvars
            ├── azure-pipelines-aro.yml
            └── modules/
                ├── networking/
                ├── identity/
                ├── cluster/
                └── cluster-assets/
            """
        ).rstrip(),
        "sections": [
            {
                "heading": "`main.tf` orchestration",
                "body": [
                    "The root module composes the ARO workflow in four parts:",
                    bullets([
                        "`networking` — creates the resource group, VNet, and the two required subnets",
                        "`identity` — creates or reuses a Microsoft Entra service principal and assigns Azure RBAC roles",
                        "`cluster` — provisions the managed ARO cluster resource",
                        "`cluster-assets` — renders preflight, kubeconfig, DNS, delete, and summary files",
                    ]),
                ],
                "source": "azure-aro/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`variables.tf`",
                "body": [
                    "The ARO variables model Azure-specific concerns such as networking, visibility, cluster sizing, service principal strategy, pull secret input, and DNS helper configuration.",
                ],
                "source": "azure-aro/variables.tf",
                "language": "hcl",
            },
            {
                "heading": "`outputs.tf`",
                "body": [
                    "The outputs expose the Azure resource IDs, cluster connection details, and helper script paths produced by the deployment.",
                ],
                "source": "azure-aro/outputs.tf",
                "language": "hcl",
            },
            {
                "heading": "`versions.tf`",
                "body": [
                    "Provider and Terraform version constraints for the ARO blueprint.",
                ],
                "source": "azure-aro/versions.tf",
                "language": "hcl",
            },
            {
                "heading": "`terraform.tfvars`",
                "body": [
                    "Sample input values for the ARO deployment, including cluster size, network CIDRs, and the default service principal strategy.",
                ],
                "source": "azure-aro/terraform.tfvars",
                "language": "hcl",
            },
            {
                "heading": "`azure-pipelines-aro.yml`",
                "body": [
                    "Azure DevOps pipeline for validating the ARO Terraform, provisioning the Azure foundation and ARO cluster, and optionally fetching the admin kubeconfig.",
                ],
                "source": "azure-aro/azure-pipelines-aro.yml",
                "language": "yaml",
            },
            {
                "heading": "`modules/networking`",
                "body": [
                    "This module creates the Azure primitives ARO depends on: the resource group, virtual network, required control-plane and worker subnets, and Azure service endpoints for Storage and Container Registry.",
                ],
                "source": "azure-aro/modules/networking/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/identity`",
                "body": [
                    "This module handles the identity boundary ARO needs by creating or reusing a Microsoft Entra service principal and assigning the required Contributor, Network Contributor, and Reader roles.",
                ],
                "source": "azure-aro/modules/identity/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/cluster`",
                "body": [
                    "This module wraps `azurerm_redhat_openshift_cluster` and captures the main ARO settings such as version, cluster domain, networking, VM profiles, visibility, FIPS, and host-based encryption toggles.",
                ],
                "source": "azure-aro/modules/cluster/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/cluster-assets`",
                "body": [
                    "This module renders the operational hand-off files under `azure-aro/generated/<cluster>/`, including preflight, kubeconfig, DNS, delete, and environment summary assets.",
                ],
                "source": "azure-aro/modules/cluster-assets/main.tf",
                "language": "hcl",
            },
        ],
    },
    {
        "doc_path": "docs/ibm-z/code-reference.md",
        "title": "IBM Z Terraform Code Reference",
        "intro": "This page explains the Terraform implementation under the repository's `ibm-z/` folder and includes the full source for the top-level Terraform files, the sample `terraform.tfvars`, the Azure DevOps pipeline, and each module entry point.",
        "diagram_alt": "IBM Z Terraform Modules",
        "diagram_svg": "../diagrams/ibm-z/03-ibm-z-terraform-modules.svg",
        "diagram_drawio": "../diagrams/ibm-z/03-ibm-z-terraform-modules.drawio",
        "tree": textwrap.dedent(
            """\
            ibm-z/
            ├── main.tf
            ├── variables.tf
            ├── outputs.tf
            ├── versions.tf
            ├── terraform.tfvars
            ├── azure-pipelines-ibm-z.yml
            └── modules/
                ├── install-config/
                ├── agent-config/
                ├── zvm-guests/
                └── cluster-install/
            """
        ).rstrip(),
        "sections": [
            {
                "heading": "`main.tf` orchestration",
                "body": [
                    "The root module composes the IBM Z workflow in four parts:",
                    bullets([
                        "`install-config` — renders the OpenShift cluster definition",
                        "`agent-config` — renders IBM Z host inventory and static network config",
                        "`zvm-guests` — optionally generates and runs guest provisioning commands",
                        "`cluster-install` — copies assets to the bastion host and launches the installer",
                    ]),
                    "This is not a placeholder layout with empty submodules. The implementation renders real OpenShift install assets and executable IBM Z handoff scripts while leaving site-specific z/VM and bastion execution boundaries explicit.",
                ],
                "source": "ibm-z/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`variables.tf`",
                "body": [
                    "The IBM Z variables intentionally model platform-specific concerns such as `s390x` architecture, rendezvous IP planning, z/VM automation, DASD/root-device hints, and static interface naming.",
                ],
                "source": "ibm-z/variables.tf",
                "language": "hcl",
            },
            {
                "heading": "`outputs.tf`",
                "body": [
                    "The outputs expose the generated asset paths, bastion hand-off directory, and expected API and console URLs for the cluster.",
                ],
                "source": "ibm-z/outputs.tf",
                "language": "hcl",
            },
            {
                "heading": "`versions.tf`",
                "body": [
                    "Provider and Terraform version constraints for the IBM Z blueprint.",
                ],
                "source": "ibm-z/versions.tf",
                "language": "hcl",
            },
            {
                "heading": "`terraform.tfvars`",
                "body": [
                    "Sample input values for an IBM Z / LinuxONE agent-based OpenShift deployment, including mirrored release sources, bastion settings, and node inventories.",
                ],
                "source": "ibm-z/terraform.tfvars",
                "language": "hcl",
            },
            {
                "heading": "`azure-pipelines-ibm-z.yml`",
                "body": [
                    "Azure DevOps pipeline for validating the IBM Z Terraform, rendering install assets, optionally provisioning z/VM guests, and optionally launching the remote installer on the bastion.",
                ],
                "source": "ibm-z/azure-pipelines-ibm-z.yml",
                "language": "yaml",
            },
            {
                "heading": "`modules/install-config`",
                "body": [
                    "This module writes `install-config.yaml` for the disconnected, `platform: none`, agent-based IBM Z installation path.",
                ],
                "source": "ibm-z/modules/install-config/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/agent-config`",
                "body": [
                    "This module translates node inventory into `agent-config.yaml`, including roles, boot MAC addresses, static network configuration, DNS, and default routes.",
                ],
                "source": "ibm-z/modules/agent-config/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/zvm-guests`",
                "body": [
                    "This module produces `zvm-guests.csv` and `provision-zvm-guests.sh`, giving site-owned z/VM automation an explicit inventory and execution wrapper.",
                ],
                "source": "ibm-z/modules/zvm-guests/main.tf",
                "language": "hcl",
            },
            {
                "heading": "`modules/cluster-install`",
                "body": [
                    "This module creates the bastion launcher script that copies the generated YAML files, runs `openshift-install agent create image`, and can optionally wait for installation completion.",
                ],
                "source": "ibm-z/modules/cluster-install/main.tf",
                "language": "hcl",
            },
        ],
    },
]


def render_page(platform: dict) -> str:
    lines = [
        f"# {platform['title']}",
        "",
        platform["intro"],
        "",
        "## Module relationship",
        "",
        f"![{platform['diagram_alt']}]({platform['diagram_svg']}){{: .drawio-diagram }}",
        "",
        f"???+ note \"Draw.io Source: {platform['diagram_alt']}\"",
        f"    [:material-download: Download .drawio file]({platform['diagram_drawio']}){{ .md-button }} — Open in [draw.io](https://app.diagrams.net) for interactive editing.",
        "",
        "## Root module structure",
        "",
        fence("text", platform["tree"]),
    ]

    for section in platform["sections"]:
        lines.extend([
            "",
            f"## {section['heading']}",
            "",
        ])
        for paragraph in section["body"]:
            lines.extend([paragraph, ""])
        lines.extend([
            f"### Source for {section['heading']}",
            "",
            fence(section["language"], read_src(section["source"])),
        ])

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    created = []
    for platform in PLATFORMS:
        doc_path = BASE / platform["doc_path"]
        doc_path.write_text(render_page(platform))
        created.append(str(doc_path.relative_to(BASE)))

    print(f"Generated {len(created)} platform code-reference pages:")
    for path in created:
        print(f"  ✓ {path}")


if __name__ == "__main__":
    main()
