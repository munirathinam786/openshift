# IBM Z Terraform Code Reference

This page explains the Terraform implementation added under the repository's `ibm-z/` folder.

## Module relationship

![IBM Z Terraform Modules](../diagrams/ibm-z/03-ibm-z-terraform-modules.svg){: .drawio-diagram }

???+ note "Draw.io Source: IBM Z Terraform Modules"
    [:material-download: Download .drawio file](../diagrams/ibm-z/03-ibm-z-terraform-modules.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Root module structure

```text
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
```

## `main.tf` orchestration

The root module composes the IBM Z workflow in four parts:

1. `install-config` — renders the OpenShift cluster definition
2. `agent-config` — renders IBM Z host inventory and static network config
3. `zvm-guests` — optionally generates and runs guest provisioning commands
4. `cluster-install` — copies assets to the bastion host and launches the installer

This is not a placeholder layout with empty submodules. The implementation renders real OpenShift install assets and executable IBM Z handoff scripts, while leaving site-specific z/VM and bastion execution boundaries explicit.

### Key orchestration excerpt

```hcl
module "install_config" {
  source = "./modules/install-config"

  cluster_name         = var.cluster_name
  base_domain          = var.base_domain
  architecture         = var.architecture
  machine_network_cidr = var.machine_network_cidr
}

module "agent_config" {
  source = "./modules/agent-config"

  rendezvous_ip       = var.rendezvous_ip
  dns_servers         = var.dns_servers
  gateway             = var.gateway
  control_plane_nodes = local.control_plane_nodes
}

module "zvm_guests" {
  source = "./modules/zvm-guests"
  count  = var.enable_zvm_guest_provisioning ? 1 : 0
}

module "cluster_install" {
  source = "./modules/cluster-install"
  auto_launch_install  = var.auto_launch_install
  auto_approve_install = var.auto_approve_install
  depends_on = [
    module.install_config,
    module.agent_config,
    module.zvm_guests,
  ]
}
```

### Why the installer handoff is script-driven

IBM Z deployments in this repository are intentionally split across Terraform, platform automation, and a bastion/helper node:

- Terraform renders the OpenShift YAML assets.
- Optional z/VM provisioning is executed through a site-owned wrapper script.
- The bastion host runs `openshift-install agent create image` and optionally waits for completion.

That separation is the real implementation model for many IBM Z environments, not a missing feature.

## `variables.tf`

The IBM Z variables intentionally model platform-specific concerns that do not exist in the x86 code path, including:

- `architecture = "s390x"`
- `rendezvous_ip`
- `zvm_host`, `zvm_user`, and `zvm_guest_script_path`
- node-level `install_device` values such as DASD devices
- static interface naming such as `enc600`

### Example control plane node object

```hcl
{
  name        = "ocp-z-master-0"
  ipv4        = "10.154.10.21"
  mac_address = "02:00:00:00:10:21"
  zvm_userid  = "OCPZM01"
  zvm_network = "VSW1"
}
```

## `modules/install-config`

This module writes `install-config.yaml` with:

- `platform: none`
- IBM Z machine pool architecture
- disconnected image digest sources
- optional trust bundle

It is the cleanest place to extend if your standards require proxy settings, FIPS, or additional OpenShift install tuning.

## `modules/agent-config`

This module translates node inventory into `agent-config.yaml`. Each node includes:

- host role (`master` or `worker`)
- boot MAC address
- static IP configuration
- DNS and default route
- root device hint

This is the IBM Z heart of the workflow because it replaces a large portion of the x86-oriented provisioning assumptions.

## `modules/zvm-guests`

This module produces two assets:

- `zvm-guests.csv`
- `provision-zvm-guests.sh`

The generated script is intentionally a wrapper around a site-defined command such as `/opt/ibmz/provision-guest.sh`. That keeps the Terraform code reusable while giving infrastructure teams a safe place to plug in approved automation.

## `modules/cluster-install`

This module creates a launcher script that:

1. copies the generated YAML files to the bastion host
2. runs `openshift-install agent create image`
3. optionally waits for bootstrap and install completion

That allows the bastion host to remain the execution point for OpenShift installation while Terraform remains the orchestration layer.

When `auto_launch_install=false`, Terraform still renders the launcher script so teams can execute it manually under change control.

## Outputs

The IBM Z module exposes the most useful deployment references:

- generated assets directory
- `install-config.yaml` path
- `agent-config.yaml` path
- optional z/VM guest manifest path
- expected API URL
- expected console URL

These outputs are meant to make hand-off and troubleshooting easier for the platform team.
