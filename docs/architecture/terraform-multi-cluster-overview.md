# Multi-Cluster Architecture — Overview

This section covers the **complete multi-cluster OpenShift deployment** spanning DC and DR sites with dedicated management clusters, automated via Terraform and Azure DevOps.

## High-Level Architecture

![High-Level Architecture (IPI)](../diagrams/architecture/01-high-level-architecture-ipi.svg){: .drawio-diagram }

???+ note "Draw.io Source: High-Level Architecture (IPI)"
    [:material-download: Download .drawio file](../diagrams/architecture/01-high-level-architecture-ipi.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## UPI Architecture Variant

The same 4-cluster architecture is also available via **UPI (User Provisioned Infrastructure)**. UPI adds a **bastion host**, **external HAProxy load balancer**, and a **temporary bootstrap VM** to each cluster — the operator controls node lifecycle instead of BMC/iDRAC automation.

![UPI Architecture Variant](../diagrams/architecture/02-upi-architecture-variant.svg){: .drawio-diagram }

???+ note "Draw.io Source: UPI Architecture Variant"
    [:material-download: Download .drawio file](../diagrams/architecture/02-upi-architecture-variant.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### UPI Install Flow Per Cluster

Each UPI cluster follows this phased install sequence. The **bootstrap node is a temporary VM** that is automatically cleaned up once the control plane becomes self-hosted:

![UPI Install Flow](../diagrams/architecture/03-upi-install-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: UPI Install Flow"
    [:material-download: Download .drawio file](../diagrams/architecture/03-upi-install-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### IPI vs UPI — Infrastructure Comparison

| Component | IPI | UPI |
|-----------|-----|-----|
| **Bastion Host** | Optional (convenience) | **Required** — runs `openshift-install`, serves ignition, PXE/TFTP |
| **Bootstrap VM** | Managed by installer, auto-removed | **Operator-provisioned** — explicit `bootstrap_cleanup` module |
| **Load Balancer** | Installer-managed keepalived VIPs | **External HAProxy** — must be pre-configured |
| **Node Boot** | Automated via BMC/iDRAC virtual media | Manual: PXE, ISO, or operator-driven boot |
| **CSR Approval** | Automatic | **Explicit** — `oc adm certificate approve` |
| **install-config** | `platform: baremetal` + BMC credentials | `platform: none` — no hardware management |
| **Installer Binary** | `openshift-baremetal-install` | `openshift-install` |
| **Node Definitions** | Include BMC address, user, password | **No BMC fields** — only name, MAC, IP |

## Cluster Roles & Responsibilities

| Cluster | IPI Folder | UPI Folder | Site | Role | Key Components |
|---------|-----------|-----------|------|------|----------------|
| **DC Primary** | `ipi-method/openshiftbaremetal/` | `upi-method/openshiftbaremetal/` | DC | Production workload | OCP + OpenShift AI + GPU + ODF + Submariner Broker |
| **DR Secondary** | `ipi-method/openshiftbaremetal-dr/` | `upi-method/openshiftbaremetal-dr/` | DR | Standby workload | OCP + OpenShift AI + GPU + ODF + Submariner Agent + ODF DR |
| **Management DC** | `ipi-method/mgmt-dc/` | `upi-method/mgmt-dc/` | DC | Cluster management hub | OCP + ACM Hub + ACS Central + Quay Enterprise |
| **Management DR** | `ipi-method/mgmt-dr/` | `upi-method/mgmt-dr/` | DR | Management standby | OCP + ACM Standby + ACS SecuredCluster + Quay Enterprise |

## Network Architecture

Each cluster uses **non-overlapping CIDRs** to support Submariner cross-cluster routing without Globalnet:

![Network Architecture](../diagrams/architecture/04-network-architecture.svg){: .drawio-diagram }

???+ note "Draw.io Source: Network Architecture"
    [:material-download: Download .drawio file](../diagrams/architecture/04-network-architecture.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## How It Works

### 1. Deployment Flow — IPI

The IPI ADO pipeline deploys clusters in dependency order (installer manages node lifecycle via BMC):

![Submariner Cross-Cluster Networking](../diagrams/architecture/05-submariner-networking.svg){: .drawio-diagram }

???+ note "Draw.io Source: Submariner Cross-Cluster Networking"
    [:material-download: Download .drawio file](../diagrams/architecture/05-submariner-networking.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### 1b. Deployment Flow — UPI

The UPI ADO pipeline adds **bastion-driven ignition**, **manual/PXE/ISO node boot**, and **bootstrap cleanup** phases:

![ODF DR Replication](../diagrams/architecture/06-odf-dr-replication.svg){: .drawio-diagram }

???+ note "Draw.io Source: ODF DR Replication"
    [:material-download: Download .drawio file](../diagrams/architecture/06-odf-dr-replication.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### 2. Submariner Cross-Cluster Networking

Submariner establishes an encrypted IPsec tunnel between DC and DR for **pod-to-pod** and **service-to-service** communication:

![Submariner Pipeline](../diagrams/pipeline/14-submariner-pipeline.svg){: .drawio-diagram }

???+ note "Draw.io Source: Submariner Pipeline"
    [:material-download: Download .drawio file](../diagrams/pipeline/14-submariner-pipeline.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

![Management Cluster Architecture](../diagrams/architecture/07-management-cluster-architecture.svg){: .drawio-diagram }

???+ note "Draw.io Source: Management Cluster Architecture"
    [:material-download: Download .drawio file](../diagrams/architecture/07-management-cluster-architecture.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

**How it works:**

1. DC Primary deploys Submariner as **broker** — creates the `Broker` CR and `Submariner` CR
2. DR Secondary deploys Submariner as **agent** — connects to DC broker using API URL + token
3. Gateway nodes on each side establish IPsec tunnels using the configured cable driver (`libreswan`, `wireguard`, or `vxlan`)
4. `ServiceDiscovery` enables DNS-based cross-cluster service resolution (`<svc>.<ns>.svc.clusterset.local`)

### 3. ODF Disaster Recovery Replication

ODF DR enables **Ceph RBD mirroring** between the DC and DR storage clusters:

![ODF Replication Pipeline](../diagrams/pipeline/15-odf-replication-pipeline.svg){: .drawio-diagram }

???+ note "Draw.io Source: ODF Replication Pipeline"
    [:material-download: Download .drawio file](../diagrams/pipeline/15-odf-replication-pipeline.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

![ACM Import/DR Management](../diagrams/architecture/08-acm-import-dr-management.svg){: .drawio-diagram }

???+ note "Draw.io Source: ACM Import/DR Management"
    [:material-download: Download .drawio file](../diagrams/architecture/08-acm-import-dr-management.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Mode | Replication | RPO | Latency Requirement | Use Case |
|------|-------------|-----|---------------------|----------|
| **Regional DR** (async) | Scheduled (cron) | Minutes | Tolerant (cross-DC WAN) | Multi-datacenter, 100+ km apart |
| **Metro DR** (sync) | Real-time | Zero | < 10ms RTT (metro-area) | Same metro region, < 100 km |

### 4. Management Cluster Architecture

The management clusters provide centralized operations across all workload clusters:

![DR Failover Workflow](../diagrams/architecture/09-dr-failover-workflow.svg){: .drawio-diagram }

???+ note "Draw.io Source: DR Failover Workflow"
    [:material-download: Download .drawio file](../diagrams/architecture/09-dr-failover-workflow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

**Management DC** runs:

- **ACM Hub** — imports and manages all clusters, deploys policies, handles governance
- **ACS Central** — centralized security scanning, vulnerability management, compliance reporting
- **Quay Enterprise** — on-cluster container registry with Clair image scanning

**Management DR** runs:

- **ACM Standby** — passive MultiClusterHub, promotable to active during DC failure
- **ACS SecuredCluster** — sensor + collector only, reports back to ACS Central in DC
- **Quay Enterprise** — geo-replicated registry for DR availability

### 4b. ACM Cluster Import & DR Application Management

In addition to the core management services, two dedicated modules and pipelines handle **workload cluster import** and **application-level DR**:

![Inter-Cluster Connection Map](../diagrams/architecture/10-inter-cluster-connection-map.svg){: .drawio-diagram }

???+ note "Draw.io Source: Inter-Cluster Connection Map"
    [:material-download: Download .drawio file](../diagrams/architecture/10-inter-cluster-connection-map.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Capability | Module | Var File | Pipeline | Description |
|------------|--------|----------|----------|-------------|
| **Cluster Import** | `acm-cluster-import` | `acm-import.tfvars` | `azure-pipelines-acm-import.yml` | Import workload clusters into ACM Hub |
| **DR Applications** | `acm-dr-applications` | `acm-dr.tfvars` | `azure-pipelines-acm-dr.yml` | DRPolicy + failover/failback/relocate |

!!! note "Mirror Operators"
    The `odr-hub-operator` (stable-4.20) has been added to `mirror_operators` in all management cluster `terraform.tfvars` files to support disconnected ODR Hub deployment.

### 5. Disaster Recovery Failover Workflow

![ADO Pipeline Scope](../diagrams/architecture/11-ado-pipeline-scope.svg){: .drawio-diagram }

???+ note "Draw.io Source: ADO Pipeline Scope"
    [:material-download: Download .drawio file](../diagrams/architecture/11-ado-pipeline-scope.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Folder Structure

![Terraform File Structure](../diagrams/code/06-terraform-file-structure.svg){: .drawio-diagram }

???+ note "Draw.io Source: Terraform File Structure"
    [:material-download: Download .drawio file](../diagrams/code/06-terraform-file-structure.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### IPI Method

```
ipi-method/
├── openshiftbaremetal/           # DC Primary — workload cluster
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── outputs.tf
│   ├── versions.tf
│   └── modules/                  # Shared modules (referenced by all clusters)
│       ├── dns/
│       ├── haproxy/
│       ├── quay-mirror/
│       ├── ocp-baremetal/
│       ├── nfd-operator/
│       ├── gpu-operator/
│       ├── odf-operator/
│       ├── servicemesh/
│       ├── serverless/
│       ├── openshift-ai/
│       ├── gpu-monitoring/
│       ├── metallb-operator/
│       ├── sriov-operator/
│       ├── cluster-autoscaler/
│       ├── etcd-backup/
│       ├── submariner/
│       ├── odf-dr/
│       ├── acm/
│       ├── acs/
│       └── quay-enterprise/
│
├── openshiftbaremetal-dr/        # DR Secondary — workload cluster
│   ├── main.tf                   # References ../openshiftbaremetal/modules/
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── outputs.tf
│   └── versions.tf
│
├── mgmt-dc/                     # Management DC — ACM Hub + ACS Central + Quay
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── outputs.tf
│   └── versions.tf
│
├── mgmt-dr/                     # Management DR — ACM Standby + ACS Secured + Quay
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── outputs.tf
│   └── versions.tf
│
└── azure-pipelines.yml           # ADO pipeline with deployment scope selection
```

### UPI Method

```
upi-method/
├── openshiftbaremetal/           # DC Primary — workload cluster (UPI)
│   ├── main.tf                   # UPI phases: ignition → bootstrap → cleanup → workers
│   ├── variables.tf              # No BMC fields — boot_method, bootstrap_ip/mac
│   ├── terraform.tfvars
│   ├── outputs.tf
│   ├── versions.tf
│   └── modules/                  # Shared UPI modules (referenced by all UPI clusters)
│       ├── dns/
│       ├── haproxy/              # External HAProxy LB (required for UPI)
│       ├── quay-mirror/
│       ├── install-config/       # platform: none
│       ├── ignition/             # openshift-install create ignition-configs
│       ├── ignition-server/      # HTTP server on bastion :8080
│       ├── bootstrap/            # Boot temporary bootstrap VM
│       ├── control-plane/        # PXE/ISO/manual boot masters
│       ├── bootstrap-complete/   # wait-for bootstrap-complete
│       ├── bootstrap-cleanup/    # Remove bootstrap from LB + power off
│       ├── compute-nodes/        # PXE/ISO/manual boot workers
│       ├── cluster-complete/     # CSR approval + wait-for install-complete
│       ├── nfd-operator/
│       ├── gpu-operator/
│       ├── odf-operator/
│       ├── servicemesh/
│       ├── serverless/
│       ├── openshift-ai/
│       ├── gpu-monitoring/
│       ├── metallb-operator/
│       ├── sriov-operator/
│       ├── cluster-autoscaler/
│       ├── etcd-backup/
│       ├── submariner/
│       ├── odf-dr/
│       ├── acm/
│       ├── acs/
│       └── quay-enterprise/
│
├── openshiftbaremetal-dr/        # DR Secondary (UPI)
│   ├── main.tf                   # References ../openshiftbaremetal/modules/
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── outputs.tf
│   └── versions.tf
│
├── mgmt-dc/                     # Management DC (UPI)
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── outputs.tf
│   └── versions.tf
│
├── mgmt-dr/                     # Management DR (UPI)
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── outputs.tf
│   └── versions.tf
│
└── azure-pipelines-upi.yml      # ADO pipeline with UPI phases + deployment scope
```

### Key UPI Module Differences

| IPI Module | UPI Equivalent | Difference |
|------------|---------------|------------|
| `ocp-baremetal/` | `install-config/` + `ignition/` + `ignition-server/` + `bootstrap/` + `control-plane/` + `bootstrap-complete/` + `bootstrap-cleanup/` + `compute-nodes/` + `cluster-complete/` | Single IPI module → 9 UPI modules for phased install |
| (none) | `bootstrap-cleanup/` | New — removes temporary bootstrap VM after control plane is self-hosted |
| `haproxy/` (optional) | `haproxy/` (**required**) | HAProxy is mandatory in UPI as there's no installer-managed keepalived |

## ADO Pipeline — Deployment Scope Selection

The Azure DevOps pipeline provides granular control over which clusters to deploy:

![IPI vs UPI Comparison](../diagrams/architecture/12-ipi-vs-upi-comparison.svg){: .drawio-diagram }

???+ note "Draw.io Source: IPI vs UPI Comparison"
    [:material-download: Download .drawio file](../diagrams/architecture/12-ipi-vs-upi-comparison.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Parameter | Values | Description |
|-----------|--------|-------------|
| `deploymentScope` | `dc-only`, `dr-only`, `dc-and-dr`, `mgmt-dc-only`, `mgmt-dr-only`, `mgmt-clusters`, `all-dc`, `all-dr`, `all` | Which clusters to deploy |
| `enableSubmariner` | `true` / `false` | Enable Submariner cross-cluster networking |
| `enableOdfReplication` | `true` / `false` | Enable ODF storage replication |
| `odfDrMode` | `regional-dr` / `metro-dr` | Async (RPO: minutes) or sync (RPO: zero) |
| `terraformAction` | `plan` / `apply` / `destroy` | Terraform operation to run |

## Quick Start — Full Multi-Cluster Deployment

### Step 1: Configure Each Cluster

Edit the `terraform.tfvars` in each folder:

```bash
# IPI Method
# DC Primary (workload)
vi ipi-method/openshiftbaremetal/terraform.tfvars

# DR Secondary (workload)
vi ipi-method/openshiftbaremetal-dr/terraform.tfvars

# Management DC (ACM + ACS + Quay)
vi ipi-method/mgmt-dc/terraform.tfvars

# Management DR (ACM standby + ACS secured + Quay)
vi ipi-method/mgmt-dr/terraform.tfvars

# UPI Method
vi upi-method/openshiftbaremetal/terraform.tfvars
vi upi-method/openshiftbaremetal-dr/terraform.tfvars
vi upi-method/mgmt-dc/terraform.tfvars
vi upi-method/mgmt-dr/terraform.tfvars
```

### Step 2: Deploy via ADO Pipeline

1. Navigate to **Azure DevOps → Pipelines**
2. Select **OpenShift Multi-Cluster Deployment**
3. Click **Run pipeline**
4. Choose your parameters:

    | Setting | Recommended for Full Deploy |
    |---------|---------------------------|
    | Deployment Scope | `all` |
    | Enable Submariner | `true` |
    | Enable ODF Replication | `true` |
    | ODF DR Mode | `regional-dr` |
    | Terraform Action | `plan` (review first, then `apply`) |

### Step 3: Verify Deployment

```bash
# DC Primary
export KUBECONFIG=ipi-method/openshiftbaremetal/modules/ocp-baremetal/generated/kubeconfig
oc get nodes
oc get csv -A | grep -E "gpu|odf|rhods|submariner"

# DR Secondary
export KUBECONFIG=ipi-method/openshiftbaremetal-dr/modules/ocp-baremetal/generated/kubeconfig
oc get gateways.submariner.io -n submariner-operator    # Submariner status
oc get mirrorpeer -A                                     # ODF DR status

# Management DC
export KUBECONFIG=ipi-method/mgmt-dc/modules/ocp-baremetal/generated/kubeconfig
oc get multiclusterhub -n open-cluster-management       # ACM status
oc get central -n stackrox                               # ACS status
oc get quayregistry -n quay-enterprise                   # Quay status
```

## Complete Inter-Cluster Connection Map

Every connection between all four clusters at the protocol and port level:

![Protocol Port Map](../diagrams/architecture/13-protocol-port-map.svg){: .drawio-diagram }

???+ note "Draw.io Source: Protocol Port Map"
    [:material-download: Download .drawio file](../diagrams/architecture/13-protocol-port-map.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### Connection Details

| # | Source | Destination | Protocol / Port | Purpose | Direction |
|---|--------|-------------|-----------------|---------|----------|
| 1 | DC Gateway Node | DR Gateway Node | UDP 4500, 500 + ESP | Submariner IPsec tunnel for pod-to-pod and service-to-service traffic | Bidirectional |
| 2 | DC ODF Ceph | DR ODF Ceph | TCP 6789, 3300 | Ceph RBD mirroring (async every 5 min or sync real-time) | Bidirectional |
| 3 | ACM Hub (Mgmt DC) | DC Primary API | TCP 443 → 6443 | Klusterlet agent import, policy delivery, observability metrics | Hub → Managed |
| 4 | ACM Hub (Mgmt DC) | DR Secondary API | TCP 443 → 6443 | Klusterlet agent import, policy delivery, observability metrics | Hub → Managed |
| 5 | ACS SecuredCluster (Mgmt DR) | ACS Central (Mgmt DC) | TCP 443 (gRPC) | Sensor telemetry, vulnerability reports, compliance results | Sensor → Central |
| 6 | Quay Enterprise (Mgmt DC) | Quay Enterprise (Mgmt DR) | TCP 443 (S3 API) | Image geo-replication via shared S3 backend | Bidirectional |
| 7 | ACM Hub (Mgmt DC) | ACM Standby (Mgmt DR) | TCP 443 | DR failover promotion (manual trigger) | Failover |
| 8 | DR Submariner Agent | DC Submariner Broker | TCP 6443 | Agent registration, tunnel negotiation, service discovery sync | Agent → Broker |

### Firewall Rules Required

| From | To | Ports | Notes |
|------|----|-------|-------|
| DC Gateway Nodes | DR Gateway Nodes | UDP 4500, 500 + ESP | Submariner IPsec — both directions |
| DC Ceph MON/OSD | DR Ceph MON/OSD | TCP 6789, 3300 | RBD mirroring — both directions |
| Mgmt DC | DC Primary API VIP | TCP 6443 | ACM Klusterlet |
| Mgmt DC | DR Secondary API VIP | TCP 6443 | ACM Klusterlet |
| Mgmt DR | Mgmt DC ACS Route | TCP 443 | ACS Sensor → Central |
| Mgmt DC Quay | Mgmt DR Quay | TCP 443 | Geo-replication S3 sync |
| DR Gateway Nodes | DC API VIP | TCP 6443 | Submariner broker registration |
| Local Quay (internet) | cdn.redhat.com / quay.io | TCP 443 | Pull operators from Red Hat CDN |
| Bastion | Local Quay | TCP 8443 | `oc mirror` push and pull mirrored images |
| Bastion | Mgmt DC Quay Enterprise Route | TCP 443 | Replicate mirrored content to DC Quay Enterprise |
| Bastion | Mgmt DR Quay Enterprise Route | TCP 443 | Replicate mirrored content to DR Quay Enterprise |
| All Cluster Nodes | Local Quay / Quay Enterprise | TCP 443/8443 | Pull container images |
| All Nodes | DNS Server | TCP/UDP 53 | DNS resolution |
| All Nodes | NTP Server | UDP 123 | Time synchronization |
| Bastion | All BMC (iDRAC/iLO/XCC) | TCP 443 | Redfish API bare metal provisioning |
| Submariner Gateway DC | Submariner Gateway DR | UDP 4800 | VXLAN tunnel |

## Endpoints Summary

| Cluster | Endpoint | URL |
|---------|----------|-----|
| DC Primary | Console | `https://console-openshift-console.apps.ocp-ai.example.com` |
| DC Primary | OpenShift AI | `https://rhods-dashboard-redhat-ods-applications.apps.ocp-ai.example.com` |
| DR Secondary | Console | `https://console-openshift-console.apps.ocp-ai-dr.dr.example.com` |
| DR Secondary | OpenShift AI | `https://rhods-dashboard-redhat-ods-applications.apps.ocp-ai-dr.dr.example.com` |
| Mgmt DC | ACM Hub | `https://multicloud-console.apps.mgmt-dc.example.com` |
| Mgmt DC | ACS Central | `https://central-stackrox.apps.mgmt-dc.example.com` |
| Mgmt DC | Quay | `https://central-quay-quay-enterprise.apps.mgmt-dc.example.com` |
| Mgmt DR | ACM Standby | `https://multicloud-console.apps.mgmt-dr.dr.example.com` |
| Mgmt DR | Quay | `https://central-quay-quay-enterprise.apps.mgmt-dr.dr.example.com` |
