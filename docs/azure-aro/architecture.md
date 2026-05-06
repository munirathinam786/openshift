# Azure Red Hat OpenShift (ARO) Architecture

This architecture adapts the repository's Terraform style to **Azure Red Hat OpenShift (ARO)**. Instead of provisioning all control-plane components directly, Terraform prepares the **Azure network boundary**, the **identity and RBAC scaffolding**, and the **managed ARO cluster resource**, then renders helper assets for day-0.5 operator tasks.

## High-level topology

![Azure Red Hat OpenShift Architecture Overview](../diagrams/azure-aro/01-azure-aro-architecture.svg){: .drawio-diagram }

???+ note "Draw.io Source: Azure Red Hat OpenShift Architecture Overview"
    [:material-download: Download .drawio file](../diagrams/azure-aro/01-azure-aro-architecture.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Deployment flow

![Azure Red Hat OpenShift Deployment Flow](../diagrams/azure-aro/02-azure-aro-deployment-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: Azure Red Hat OpenShift Deployment Flow"
    [:material-download: Download .drawio file](../diagrams/azure-aro/02-azure-aro-deployment-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Component mapping

| Layer | ARO component | Role in the design |
| --- | --- | --- |
| Management plane | Azure Red Hat OpenShift service | Provisions and manages the OpenShift control plane |
| Customer network | Azure VNet, control-plane subnet, worker subnet | Hosts the cluster's Azure networking footprint |
| Identity | Microsoft Entra application + service principal | Allows ARO to create and manage Azure resources in the cluster scope |
| Azure RBAC | Contributor and Network Contributor role assignments | Grants the cluster SP and ARO RP the permissions they need |
| Cluster operations | Azure CLI + `oc` helper assets | Fetches kubeconfig, validates prerequisites, updates DNS, and deletes the cluster |
| DNS | Azure DNS (optional) | Creates API and `*.apps` records for the custom domain |

## Architecture differences from ROSA and bare metal

### Managed Azure resource model

ARO provisions managed resources in a separate Azure-managed resource group. Terraform still matters, but it focuses on:

- resource group and VNet creation
- empty subnet design for control plane and worker nodes
- service principal lifecycle and RBAC
- cluster visibility and network profile settings
- post-create operational assets

### Subnet and address planning

ARO requires two empty subnets and non-overlapping OpenShift pod and service CIDRs. The sample Terraform defaults align with Microsoft guidance:

- one control-plane subnet
- one worker subnet
- pod CIDR `10.128.0.0/14`
- service CIDR `172.30.0.0/16`

Keep those ranges away from on-prem, peered VNet, and ExpressRoute-connected address spaces.

### Visibility options

The blueprint exposes both of ARO's network visibility controls:

- **API visibility** — `Public` or `Private`
- **Ingress visibility** — `Public` or `Private`

That lets the same codebase support internet-facing lab environments and more locked-down enterprise footprints.

## Practical deployment notes

1. Confirm subscription quota and regional availability before running `apply`.
2. Ensure the Azure resource providers are registered before pipeline or local execution.
3. If Terraform creates the service principal, protect the Terraform state because the secret is stored there.
4. Only run the kubeconfig helper after the cluster reaches a ready state.
5. Use the generated Azure DNS helper only when the DNS zone already exists and is delegated correctly.
