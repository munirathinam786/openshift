# IBM Z — OpenShift `s390x` Deployment

This section adds an **IBM Z / LinuxONE deployment path** alongside the existing x86-oriented IPI and UPI content in this repository. The design focuses on **OpenShift on `s390x`** using the **agent-based installer**, optional **z/VM guest provisioning**, and a **bastion-driven disconnected workflow**.

![IBM Z Architecture Overview](../diagrams/ibm-z/01-ibm-z-architecture.svg){: .drawio-diagram }

???+ note "Draw.io Source: IBM Z Architecture Overview"
    [:material-download: Download .drawio file](../diagrams/ibm-z/01-ibm-z-architecture.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Why IBM Z needs its own implementation

The existing repository content under `ipi-method/` and `upi-method/` is tailored to **x86 bare-metal** workflows. IBM Z differs in several important ways:

| Area | x86 content in this repo | IBM Z implementation |
| --- | --- | --- |
| CPU architecture | `amd64` / x86_64 | `s390x` |
| Provisioning model | IPI or UPI bare metal | Agent-based installer with z/VM or LPAR nodes |
| Node lifecycle | BMC/Redfish, PXE, ISO | z/VM automation or platform operations teams |
| Storage profile | Bare-metal local disks, Ceph-heavy patterns | DASD / FCP-backed guests or LPAR-attached storage |
| Networking | NICs, VIPs, HAProxy, Redfish | OSA-Express, HiperSockets, VSWITCH / VLAN-aware networks |
| Accelerators | NVIDIA GPU and AI-heavy examples | General-purpose enterprise Linux workloads on IBM Z |

## New repo assets

The IBM Z code lives in the repository root under:

```text
ibm-z/
├── README.md
├── versions.tf
├── variables.tf
├── terraform.tfvars
├── main.tf
├── outputs.tf
├── azure-pipelines-ibm-z.yml
└── modules/
    ├── install-config/
    ├── agent-config/
    ├── zvm-guests/
    └── cluster-install/
```

## Actual implementation, not a skeleton

This IBM Z content is backed by working Terraform and executable handoff assets:

- `modules/install-config` renders a real `install-config.yaml` for `platform: none`, `s390x`, mirrored content, and trust settings.
- `modules/agent-config` renders a real `agent-config.yaml` with static network definitions, DNS, default routes, boot MACs, and root device hints.
- `modules/zvm-guests` renders an inventory CSV and an executable provisioning wrapper for site-specific z/VM guest automation.
- `modules/cluster-install` renders an executable bastion launch script for `openshift-install agent create image` and optional install tracking.

The implementation intentionally stops short of pretending IBM Z node lifecycle can be fully abstracted inside generic Terraform resources. Instead, it renders and optionally executes the real handoff steps that IBM Z platform teams and helper hosts actually use.

## Deployment flow at a glance

1. Terraform renders `install-config.yaml` with `platform: none` and `s390x` machine pools.
2. Terraform renders `agent-config.yaml` with static node definitions for IBM Z hosts.
3. Optional z/VM automation generates and runs guest provisioning commands.
4. The bastion host runs `openshift-install agent create image`.
5. The resulting ISO/PXE artifacts are attached to IBM Z guests or LPARs.
6. OpenShift bootstrap and install completion are monitored from the helper host.

## Prerequisites

| Requirement | Details |
| --- | --- |
| **OpenShift release mirror** | Mirrored `s390x` release payload and operator catalogs |
| **Bastion/helper node** | RHEL host with `openshift-install`, `oc`, SSH access, and CA trust for mirror registry |
| **IBM Z platform access** | z/VM management endpoint or LPAR operations workflow |
| **Static addressing** | Fixed IPs, DNS, gateway, NTP, and MAC-to-host mapping |
| **Storage plan** | DASD or FCP-backed root disks available to each node |
| **Security material** | Pull secret, SSH public key, optional trust bundle |

## Recommended usage

- Start with `ibm-z/terraform.tfvars` and replace placeholder hostnames, IP addresses, and mirror values.
- Keep the generated install assets under `ibm-z/generated/<cluster>/` under version control **excluded** from Git.
- Treat `modules/zvm-guests` as a site-adaptation point: the Terraform side is generic, while your local `provision-guest.sh` can integrate with SMAPI, DirMaint, or internal automation.
- Keep `auto_launch_install=false` when you want Terraform to render the bastion handoff without immediately starting the installer.
- For local documentation preview, use the repository's Podman workflow with `podman compose up -d --build` from the repo root.

## Where to go next

- [IBM Z Architecture](architecture.md)
- [IBM Z Code Reference](code-reference.md)
- [IBM Z Pipeline](pipeline.md)
