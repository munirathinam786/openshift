# Terraform Automation — DC Primary Workload Cluster

This section provides the **Terraform IaC** for the **DC Primary** workload cluster — OpenShift Container Platform on bare metal with Red Hat OpenShift AI, NVIDIA GPU support, and all required operators.

!!! info "Multi-Cluster Architecture"
    This is one of **four cluster environments**. See also:
    [DR Secondary](terraform-dr-secondary.md) |
    [Management DC](terraform-mgmt-dc.md) |
    [Management DR](terraform-mgmt-dr.md) |
    [ADO Pipeline](../pipeline/terraform-ado-pipeline.md)

## Overview

The Terraform project automates the full deployment lifecycle:

![DC Primary Deployment Overview](../diagrams/clusters/01-dc-primary-deployment-overview.svg){: .drawio-diagram }

???+ note "Draw.io Source: DC Primary Deployment Overview"
    [:material-download: Download .drawio file](../diagrams/clusters/01-dc-primary-deployment-overview.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Project Structure

```
ipi-method/openshiftbaremetal/
├── main.tf                  # Main orchestration — module wiring & dependencies
├── variables.tf             # All variable declarations with types & defaults
├── terraform.tfvars         # Your environment-specific values (edit this)
├── outputs.tf               # Cluster URLs, kubeconfig path
├── versions.tf              # Provider version constraints
└── modules/
    ├── dns/                 # DNS record generation & validation
    ├── haproxy/             # HAProxy load balancer deployment
    ├── quay-mirror/         # Local Quay mirror registry (disconnected install)
    ├── ocp-baremetal/       # OCP install-config.yaml generation & installer
    ├── nfd-operator/        # Node Feature Discovery operator
    ├── gpu-operator/        # NVIDIA GPU Operator + ClusterPolicy
    ├── odf-operator/        # OpenShift Data Foundation (Ceph storage)
    ├── servicemesh/         # OpenShift Service Mesh + Kiali
    ├── serverless/          # OpenShift Serverless (KnativeServing)
    ├── openshift-ai/        # Red Hat OpenShift AI + DataScienceCluster
    ├── gpu-monitoring/      # NVIDIA DCGM Exporter dashboard
    ├── metallb-operator/    # MetalLB load balancer (optional)
    ├── sriov-operator/      # SR-IOV Network Operator (optional)
    ├── cluster-autoscaler/  # GPU-aware Cluster Autoscaler
    ├── etcd-backup/         # Nightly etcd backup CronJob
    ├── submariner/          # Submariner cross-cluster networking (DC↔DR)
    ├── odf-dr/              # ODF DR replication (async/sync mirroring)
    ├── acm/                 # Red Hat ACM (management clusters)
    ├── acs/                 # Red Hat ACS/StackRox (management clusters)
    ├── quay-enterprise/     # Red Hat Quay on-cluster registry (management clusters)
    ├── ldap-oauth/          # LDAP/OAuth identity provider + group sync
    ├── cluster-logging/     # Cluster Logging with ElasticSearch/Fluentd
    ├── oadp/                # OADP Backup & Recovery
    ├── openshift-gitops/    # ArgoCD GitOps operator
    ├── openshift-pipelines/ # Tekton CI/CD Pipelines
    ├── acm-cluster-import/  # ACM managed cluster import (mgmt clusters)
    ├── acm-dr-applications/ # ACM DR application failover (mgmt clusters)
    ├── compliance-operator/     # OpenSCAP compliance scanning (CIS/NIST/PCI-DSS)
    ├── file-integrity-operator/ # AIDE file integrity monitoring
    ├── cert-manager/            # TLS certificate lifecycle management
    ├── gatekeeper/              # OPA Gatekeeper policy enforcement
    ├── network-policies/        # Default-deny network policies with allowlists
    ├── nmstate-operator/        # NMState node network configuration
    ├── external-dns/            # Automated DNS record management
    ├── ingress-controller/      # Custom ingress controller tuning
    ├── multus-networks/         # Multus secondary CNI networks
    ├── network-observability/   # eBPF Network Observability with FlowCollector
    ├── alertmanager-config/     # Alertmanager routing (Slack/PagerDuty/Email)
    ├── custom-grafana-dashboards/ # Grafana dashboards (capacity/GPU/namespace)
    ├── opentelemetry-collector/ # OpenTelemetry distributed tracing with Tempo
    ├── loki-logging/            # LokiStack log aggregation
    ├── thanos-ruler/            # Thanos long-term metrics storage
    ├── node-tuning-profiles/    # Performance tuning (hugepages/RT kernel/sysctl)
    ├── image-registry/          # Internal image registry with pruning
    ├── custom-catalogsource/    # Private operator catalog sources
    ├── machine-config-pools/    # Custom MachineConfigPools for worker groups
    ├── node-maintenance/        # Node Maintenance Operator for controlled drain
    ├── cost-management/         # Red Hat Cost Management metrics
    ├── devspaces/               # Eclipse Che / OpenShift Dev Spaces
    ├── web-terminal/            # Browser-based web terminal
    ├── image-streams/           # Custom ImageStreams and S2I refresh
    ├── kuberay-operator/        # KubeRay for Ray cluster orchestration
    ├── training-operator/       # Kubeflow Training Operator (PyTorch/TF)
    ├── model-registry/          # ML model versioning registry
    ├── nvidia-nim/              # NVIDIA NIM inference microservices
    ├── mig-manager/             # NVIDIA MIG GPU partitioning
    ├── global-load-balancer/    # Cross-cluster global load balancing
    ├── velero-schedule/         # Velero backup schedules
    └── dr-runbook-automation/   # DR failover/failback automation
```

## Cross-Cluster Connectivity — DC Primary

The DC Primary cluster has connections to all three other clusters:

![DC Primary Connectivity](../diagrams/clusters/02-dc-primary-connectivity.svg){: .drawio-diagram }

???+ note "Draw.io Source: DC Primary Connectivity"
    [:material-download: Download .drawio file](../diagrams/clusters/02-dc-primary-connectivity.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| # | Connection | Direction | Protocol | Purpose |
|---|------------|-----------|----------|----------|
| 1 | DR Agent → DC Broker | Inbound | TCP 6443 | Submariner agent registers with broker |
| 2 | DC Gateway ↔ DR Gateway | Bidirectional | UDP 4500 + ESP | Encrypted pod-to-pod tunnel |
| 3 | DC Ceph ↔ DR Ceph | Bidirectional | TCP 6789, 3300 | RBD mirroring (async/sync) |
| 4 | ACM Hub → DC API | Inbound | TCP 6443 | Klusterlet agent, policy delivery |
| 5 | ACS Central → DC | Inbound | TCP 443 | SecuredCluster sensor deployment |

## Prerequisites

Before running Terraform, ensure the following are in place:

| Requirement | Details |
|-------------|---------|
| **Terraform** | >= 1.9.0 |
| **Bastion/Provisioner Node** | RHEL 8.x/9.x with `kni` user, libvirt, qemu-kvm, `oc` CLI, `openshift-baremetal-install` |
| **Pull Secret** | Downloaded from [console.redhat.com](https://console.redhat.com/openshift/downloads#tool-pull-secret) |
| **DNS** | A records for `api.<cluster>.<domain>`, `*.apps.<cluster>.<domain>`, master/worker nodes, etcd SRV records |
| **DHCP** | MAC-based IP reservations for all cluster nodes |
| **BMC Access** | iDRAC/iLO/XCC Redfish API accessible from provisioner node |
| **SSH Key Pair** | Ed25519 or RSA key pair for `core` user access |
| **Local Quay** (disconnected) | Quay server with 2TB+ storage, CA certificate, admin credentials |
| **NVIDIA NGC** (GPU nodes) | NGC API key for vGPU driver images |
| **NLS License Token** (GPU nodes) | NVIDIA License Server client token file |
| **Red Hat Entitlement PEM** | For cluster-wide entitlement (vGPU driver builds) |

### Firewall Port Requirements

The following ports must be opened in the firewall between the relevant network zones:

#### Cluster Communication Ports

| Port | Protocol | Source | Destination | Purpose |
|------|----------|--------|-------------|---------|
| 6443 | TCP | Clients / Load Balancer | API VIP / Control Plane | Kubernetes API Server |
| 22623 | TCP | Cluster Nodes | API VIP / Control Plane | Machine Config Server |
| 443 | TCP | Clients / Load Balancer | Apps VIP / Workers | HTTPS Ingress (Router) |
| 80 | TCP | Clients / Load Balancer | Apps VIP / Workers | HTTP Ingress (Router) |
| 2379-2380 | TCP | Control Plane | Control Plane | etcd peer and client |
| 10250 | TCP | Control Plane | All Nodes | Kubelet API |
| 10257 | TCP | Control Plane | Control Plane | kube-controller-manager |
| 10259 | TCP | Control Plane | Control Plane | kube-scheduler |
| 9000-9999 | TCP/UDP | All Nodes | All Nodes | Host-level services (node exporter, etc.) |
| 30000-32767 | TCP/UDP | All Nodes | All Nodes | NodePort Services (Kubernetes) |
| 4789 | UDP | All Nodes | All Nodes | VXLAN (OVN-Kubernetes overlay) |
| 6081 | UDP | All Nodes | All Nodes | Geneve (OVN-Kubernetes overlay) |
| 500 | UDP | All Nodes | All Nodes | IPsec IKE (if encryption enabled) |
| 4500 | UDP | All Nodes | All Nodes | IPsec NAT-T (if encryption enabled) |

#### Infrastructure Services Ports

| Port | Protocol | Source | Destination | Purpose |
|------|----------|--------|-------------|---------|
| 53 | TCP/UDP | All Nodes | DNS Server | DNS resolution |
| 123 | UDP | All Nodes | NTP Server | Time synchronization |
| 22 | TCP | Bastion | All Nodes / BMC | SSH access |
| 443 | TCP | Bastion | BMC (iDRAC/iLO/XCC) | Redfish API (bare metal provisioning) |
| 5000 | TCP | Bastion | Provisioning Network | RHCOS image HTTP server |
| 67-69 | UDP | DHCP/TFTP Server | Provisioning Network | DHCP/TFTP (PXE boot — UPI) |

#### Quay Registry & Operator Mirroring Ports

| Port | Protocol | Source | Destination | Purpose |
|------|----------|--------|-------------|---------|
| 443 | TCP | Local Quay | cdn.redhat.com / quay.io | Pull operator images from Red Hat CDN |
| 8443 | TCP | Bastion / Cluster Nodes | Local Quay (internet-facing) | Pull mirrored images from local Quay |
| 443 | TCP | Bastion | Quay Enterprise Route (mgmt clusters) | Push replicated images to Quay Enterprise |
| 443 | TCP | Workload Cluster Nodes | Quay Enterprise Route (mgmt clusters) | Pull operator images from Quay Enterprise |

#### Storage (ODF/Ceph) Ports

| Port | Protocol | Source | Destination | Purpose |
|------|----------|--------|-------------|---------|
| 6789 | TCP | ODF Nodes | ODF Nodes | Ceph Monitor |
| 3300 | TCP | ODF Nodes | ODF Nodes | Ceph Monitor (v2) |
| 6800-7300 | TCP | ODF Nodes | ODF Nodes | Ceph OSD / MDS / RGW |

#### Submariner (Multi-Cluster Networking) Ports

| Port | Protocol | Source | Destination | Purpose |
|------|----------|--------|-------------|---------|
| 4500 | UDP | Gateway Nodes (all clusters) | Gateway Nodes (all clusters) | Submariner IPsec NAT-T |
| 500 | UDP | Gateway Nodes (all clusters) | Gateway Nodes (all clusters) | Submariner IPsec IKE |
| ESP (IP 50) | IP | Gateway Nodes | Gateway Nodes | Submariner IPsec ESP |
| 4800 | UDP | All Nodes (all clusters) | All Nodes (all clusters) | Submariner VXLAN tunnel |
| 8080 | TCP | All Nodes | Submariner Gateway | Submariner health check |

#### GPU & AI/ML Ports

| Port | Protocol | Source | Destination | Purpose |
|------|----------|--------|-------------|---------|
| 443 | TCP | GPU Nodes | nls.nvidia.com | NVIDIA License Server (cloud) |
| 443 | TCP | GPU Nodes | NGC Container Registry | NVIDIA GPU Operator images |

!!! warning "Disconnected / Air-Gapped Environments"
    In air-gapped deployments, the only system with internet access should be the **Local Quay** (internet-facing mirror). All other cluster nodes must pull images from local Quay or Quay Enterprise. Ensure the firewall blocks direct internet access from cluster nodes.

### Secrets & Credentials — Files on the Bastion Host

Download and place the following files on the bastion node before running Terraform:

| File | Bastion Path | Download Source | Terraform Variable |
|------|-------------|----------------|-------|
| **Pull Secret** | `/home/kni/pull-secret.json` | [console.redhat.com/openshift/downloads](https://console.redhat.com/openshift/downloads#tool-pull-secret) — requires Red Hat account | `pull_secret_file` |
| **SSH Private Key** | `/home/kni/.ssh/id_ed25519` | Generate: `ssh-keygen -t ed25519 -f /home/kni/.ssh/id_ed25519 -N ''` | `ssh_private_key_file` |
| **SSH Public Key** | `/home/kni/.ssh/id_ed25519.pub` | Generated with private key | `ssh_public_key_file` |
| **Quay CA Certificate** | `/home/kni/quay-ca.crt` | Export from your Quay mirror server's TLS CA chain | `quay_ca_cert_file` |
| **NLS License Token** | `/home/kni/nls-client-token.tok` | [NVIDIA Licensing Portal](https://ui.licensing.nvidia.com/) → Service Instances → Client Token | `nls_token_file` |
| **Entitlement PEM** | `/home/kni/entitlement.pem` | Red Hat Subscription Manager: `subscription-manager register && subscription-manager attach` | `entitlement_pem_file` |

!!! info "File Permissions"
    All secret files should be owned by the `kni` user with restricted permissions:
    ```bash
    chmod 600 /home/kni/pull-secret.json
    chmod 600 /home/kni/.ssh/id_ed25519
    chmod 600 /home/kni/nls-client-token.tok
    chmod 644 /home/kni/quay-ca.crt
    ```

### Secrets & Credentials — ADO Variable Group

Create a Variable Group named **`ocp-baremetal-secrets`** in Azure DevOps (**Project Settings → Pipelines → Library → + Variable Group**):

| Secret Name | Source | Used By | Description |
|-------------|--------|---------|-------------|
| `quay-admin-password` | Your Quay mirror admin password | All clusters | Quay mirror registry authentication |
| `ngc-api-key` | [NVIDIA NGC Portal](https://ngc.nvidia.com/setup/api-key) → Generate API Key | DC, DR | Pull vGPU driver images from `nvcr.io` |
| `submariner-broker-token` | From DC Primary after Submariner broker install:<br/>`oc get secret -n submariner-k8s-broker` | DR | Cross-cluster Submariner tunnel |
| `odf-dr-s3-access-key` | S3-compatible storage (MinIO, AWS, etc.) for ODF DR metadata store | DR | ODF DR async replication |
| `odf-dr-s3-secret-key` | Same S3 storage provider | DR | ODF DR async replication |
| `acs-central-admin-password` | Choose a strong password (min 12 chars) | Mgmt DC | ACS StackRox Central initial admin |
| `acm-s3-access-key` | S3-compatible storage for ACM Observability Thanos store | Mgmt DC, Mgmt DR | ACM Hub Observability |
| `acm-s3-secret-key` | Same S3 storage provider | Mgmt DC, Mgmt DR | ACM Hub Observability |

!!! warning "Security Best Practices"
    - Mark all secrets as **🔒 secret** (padlock icon) in ADO to mask them in pipeline logs
    - **Never** commit secrets to Git — use ADO Variable Groups or HashiCorp Vault
    - Rotate `ngc-api-key` and S3 keys periodically
    - Use separate S3 buckets for ODF DR and ACM Observability

### Secrets Flow — How Secrets Reach Terraform (IPI)

![Secrets Flow (IPI)](../diagrams/clusters/03-dc-primary-secrets-flow-ipi.svg){: .drawio-diagram }

???+ note "Draw.io Source: Secrets Flow (IPI)"
    [:material-download: Download .drawio file](../diagrams/clusters/03-dc-primary-secrets-flow-ipi.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Day 1 vs Day 2 Separation

| Phase | Var File | Pipeline | Scope |
|---|---|---|---|
| Day 1 — Install | `terraform.tfvars` | `azure-pipelines.yml` | Cluster install, core operators, networking |
| Day 2 — Post-Install | `day2-terraform.tfvars` | `azure-pipelines-day2.yml` | Logging, OADP backup, LDAP/OAuth, GitOps (ArgoCD), Pipelines (Tekton) |

Day 2 operations are applied separately after cluster installation completes:

```bash
terraform apply -var-file=terraform.tfvars -var-file=day2-terraform.tfvars
```

See the [Day 2 Pipeline documentation](../pipeline/terraform-ado-pipeline-day2.md) for details.

## Module Details

### 1. DNS (`modules/dns/`)

Generates the required DNS records reference file and validates resolution from the bastion node.

**Required DNS Records:**

| Record | Type | Target |
|--------|------|--------|
| `api.<cluster>.<domain>` | A | API VIP |
| `*.apps.<cluster>.<domain>` | A (wildcard) | Ingress VIP |
| `etcd-{0,1,2}.<cluster>.<domain>` | A | Master node IPs |
| `_etcd-server-ssl._tcp.<cluster>.<domain>` | SRV | etcd hosts |
| Forward + reverse (PTR) | A/PTR | All node IPs |

### 2. HAProxy (`modules/haproxy/`)

Deploys HAProxy load balancer configuration on designated infrastructure nodes. Configures frontends/backends for:

- **API Server** (port 6443) → Master nodes
- **Machine Config Server** (port 22623) → Master nodes
- **Ingress HTTPS** (port 443) → Worker nodes
- **Ingress HTTP** (port 80) → Worker nodes

!!! note
    Skip this module if using an F5 or external load balancer by leaving `haproxy_hosts = []`.

### 3. Quay Mirror Registry (`modules/quay-mirror/`)

For **disconnected/air-gapped installs**, the local Quay (internet-facing) serves as the initial download point for all operator and OCP release images.

![Quay Mirror Distribution](../diagrams/clusters/04-quay-mirror-distribution.svg){: .drawio-diagram }

???+ note "Draw.io Source: Quay Mirror Distribution"
    [:material-download: Download .drawio file](../diagrams/clusters/04-quay-mirror-distribution.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

This module:

1. Trusts the local Quay CA certificate on the bastion
2. Merges Quay credentials into the pull-secret
3. Generates an `ImageSetConfiguration` with all required operators
4. Runs `oc mirror` to populate the local Quay with OCP release images and operator catalogs
5. Stages the RHCOS boot image on the bastion HTTP server

!!! info "Image Distribution Architecture"
    The **local Quay** is the only system with internet access. After mirroring, the **quay-mirror-replicate** module (on management clusters) replicates all images from local Quay to the on-cluster Quay Enterprise instances. Workload clusters then pull images from their respective Quay Enterprise registry.

**Mirrored Operators:**

| Operator | Channel | Catalog |
|----------|---------|---------|
| NFD | stable | redhat-operators |
| GPU Operator | v26.3 | certified-operators |
| ODF | stable-4.20 | redhat-operators |
| NMState | stable | redhat-operators |
| MetalLB | stable | redhat-operators |
| SR-IOV | stable | redhat-operators |
| Serverless | stable | redhat-operators |
| Service Mesh | stable | redhat-operators |
| Kiali | stable | redhat-operators |
| Pipelines | latest | redhat-operators |
| RHOAI | stable | redhat-operators |
| Cluster Logging | stable | redhat-operators |
| Elasticsearch | stable | redhat-operators |
| Submariner | stable-0.20 | redhat-operators |
| OADP (redhat-oadp-operator) | stable-1.6 | redhat-operators |
| ODR (odr-cluster-operator) | stable-4.20 | redhat-operators |

### 4. OCP Baremetal Install (`modules/ocp-baremetal/`)

Generates `install-config.yaml` and runs `openshift-baremetal-install` on the bastion node.

**Key Configuration:**

- **Network Type**: OVNKubernetes (mandatory OCP 4.20+)
- **Bond Interface**: `bond0` — 802.3ad LACP, MTU 9000
- **BMC Protocol**: Redfish Virtual Media (`idrac-virtualmedia://` or `redfish-virtualmedia://`)
- **Boot Mode**: UEFI
- **Provisioning Network**: Disabled (uses machine network)

### 5. Node Feature Discovery (`modules/nfd-operator/`)

Installs the NFD operator and creates a `NodeFeatureDiscovery` CR that detects:

- NVIDIA GPU PCI devices (class `0300`, `0302`)
- Labels nodes with `feature.node.kubernetes.io/pci-10de.present=true`

### 6. NVIDIA GPU Operator (`modules/gpu-operator/`)

Handles the full GPU stack:

1. **Cluster-Wide Entitlement** — MachineConfig with Red Hat entitlement PEM
2. **GPU Operator Subscription** — From certified-operators catalog
3. **NGC Image Pull Secret** — For `nvcr.io/nvidia/vgpu` registry
4. **NLS Licensing ConfigMap** — Client license token
5. **ClusterPolicy CR** — vGPU driver, DCGM exporter, device plugin, toolkit, optional RDMA

### 7. OpenShift Data Foundation (`modules/odf-operator/`)

Deploys ODF with a 3-node Ceph storage cluster:

- Labels designated ODF worker nodes
- Creates `StorageCluster` with configurable capacity (default: 2Ti)
- Enables ODF console plugin

### 8. Service Mesh & Serverless (`modules/servicemesh/`, `modules/serverless/`)

Prerequisite operators for KServe model serving:

- **Service Mesh**: Istio-based with Kiali visualization
- **Serverless**: KnativeServing for scale-to-zero inference endpoints

### 9. Red Hat OpenShift AI (`modules/openshift-ai/`)

Installs OpenShift Pipelines (Tekton) + RHOAI operator and creates the `DataScienceCluster` CR with configurable components:

| Component | Default | Description |
|-----------|---------|-------------|
| Dashboard | Managed | RHOAI web dashboard |
| Workbenches | Managed | Jupyter notebook environments |
| Data Science Pipelines | Managed | Kubeflow Pipelines 2.0 |
| ModelMesh Serving | Managed | Multi-model serving |
| KServe | Managed | Single-model serving |
| CodeFlare | Managed | Distributed workload SDK |
| Ray | Managed | KubeRay for distributed compute |
| TrustyAI | Managed | Model bias/explainability |

Optional **NVIDIA NIM** integration can be enabled for GPU-accelerated LLM inference.

### 10. GPU Monitoring (`modules/gpu-monitoring/`)

Deploys the NVIDIA DCGM Exporter Grafana dashboard into the OCP console:

- Available in **Observe → Dashboards → NVIDIA DCGM Exporter Dashboard**
- Visible in both Admin and Developer perspectives

### 11. Cluster Autoscaler (`modules/cluster-autoscaler/`)

Configures GPU-aware cluster auto-scaling:

- Max nodes, CPU cores, memory, and GPU limits
- Scale-down policies with utilization thresholds

### 12. etcd Backup (`modules/etcd-backup/`)

Creates a nightly CronJob for etcd snapshots:

- Default schedule: `56 23 * * *` (11:56 PM daily)
- Backup location: `/home/core/backup/` on master nodes
- Automatic cleanup of backups older than 2 days

### 13. MetalLB (`modules/metallb-operator/`) — Optional

Deploys the MetalLB Operator for bare metal LoadBalancer service support. Useful when no external load balancer (F5) is available for application services beyond the API/Ingress VIPs.

!!! note
    MetalLB is **disabled by default** (`enable_metallb = false`). Enable it only if you need LoadBalancer-type Services on bare metal.

**What it deploys:**

1. **MetalLB Operator** — from `redhat-operators` catalog, `stable` channel, in `metallb-system` namespace
2. **MetalLB instance** — the controller and speaker daemonset
3. **IPAddressPool** — configurable IP ranges for LoadBalancer services
4. **L2Advertisement** — announces pool addresses via ARP/NDP (Layer 2 mode)

**Example configuration:**

```hcl
enable_metallb = true

metallb_address_pools = [
  {
    name        = "default-pool"
    addresses   = ["10.142.41.200-10.142.41.250"]
    auto_assign = true
  },
]

metallb_l2_advertisements = [
  {
    name       = "default-l2"
    pool_names = ["default-pool"]
  },
]
```

### 14. SR-IOV (`modules/sriov-operator/`) — Optional

Deploys the SR-IOV Network Operator for high-performance networking via Single Root I/O Virtualization. Essential for **GPUDirect RDMA** and data-plane acceleration workloads.

!!! note
    SR-IOV is **disabled by default** (`enable_sriov = false`). Enable it only if your NICs support SR-IOV and you need VF-level networking.

**What it deploys:**

1. **SR-IOV Network Operator** — from `redhat-operators` catalog, `stable` channel, in `openshift-sriov-network-operator` namespace
2. **SriovNetworkNodePolicy** — configures Virtual Functions (VFs) on specified physical NICs
3. **SriovNetwork** — creates NetworkAttachmentDefinitions for pods to consume VFs

**Example configuration:**

```hcl
enable_sriov = true

sriov_network_devices = [
  {
    name          = "gpu-sriov-policy"
    pf_names      = ["ens2f0", "ens2f1"]
    num_vfs       = 8
    resource_name = "gpusriovnic"
    device_type   = "netdevice"     # or "vfio-pci" for DPDK
  },
]

sriov_networks = [
  {
    name             = "gpu-sriov-network"
    resource_name    = "gpusriovnic"
    target_namespace = "default"
    vlan             = 100
    ipam             = "{\"type\": \"dhcp\"}"
  },
]
```

**Pod usage:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    k8s.v1.cni.cncf.io/networks: gpu-sriov-network
spec:
  containers:
  - name: gpu-workload
    resources:
      requests:
        openshift.io/gpusriovnic: "1"
      limits:
        openshift.io/gpusriovnic: "1"
```

### 15. Submariner (`modules/submariner/`) — Optional

Deploys Submariner for **cross-cluster networking** between DC Primary and DR Secondary. The DC Primary cluster acts as the **broker**.

!!! note
    Submariner is **disabled by default** (`enable_submariner = false`). Enable it when deploying DC+DR with cross-cluster service discovery.

**What it deploys:**

1. **Submariner Operator** — from `redhat-operators` catalog, `stable-0.20` channel
2. **Gateway node labels** — marks worker nodes as Submariner gateways
3. **Broker CR** — establishes the broker (DC Primary only)
4. **Submariner CR** — configures IPsec tunnel, service discovery, cluster CIDR registration

**Example configuration:**

```hcl
enable_submariner              = true
submariner_cable_driver        = "libreswan"    # libreswan, wireguard, vxlan
submariner_gateway_count       = 1
submariner_globalnet_enabled   = false           # enable for overlapping CIDRs
```

### 16. ODF DR Replication (`modules/odf-dr/`) — Optional

Configures ODF storage replication between DC and DR clusters for disaster recovery.

!!! note
    ODF DR is **disabled by default** (`enable_odf_dr = false`). Requires both ODF and Submariner to be enabled.

**Supports two modes:**

| Mode | Type | RPO | Use Case |
|------|------|-----|----------|
| `regional-dr` | Async | Minutes (configurable) | Cross-datacenter, high latency |
| `metro-dr` | Sync | Zero | Same metro, low latency |

**What it deploys:**

1. **ODF DR Operator** (`odr-cluster-operator`)
2. **Ceph RBD Mirroring** — enables mirroring on the StorageCluster
3. **S3 metadata secret** — for DR metadata store
4. **MirrorPeer CR** — links the two ODF clusters

**Example configuration:**

```hcl
enable_odf_dr               = true
odf_dr_mode                 = "regional-dr"
odf_dr_replication_schedule  = "*/5 * * * *"
odf_dr_peer_cluster_name    = "ocp-ai-dr"
```

## Quick Start

### Step 1: Configure Variables

Edit `terraform.tfvars` with your environment values. All fields marked `REPLACE_*` must be updated:

```hcl
cluster_name = "ocp-ai"
base_domain  = "example.com"
api_vip      = "10.142.41.30"
ingress_vip  = "10.142.41.31"
bastion_host = "10.142.41.10"

master_nodes = [
  {
    name             = "master-0"
    bmc_address      = "idrac-virtualmedia://10.142.41.100/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "your-password"
    boot_mac_address = "aa:bb:cc:dd:ee:01"
    ip               = "10.142.41.101"
  },
  # ... master-1, master-2
]

worker_nodes = [
  {
    name       = "worker-gpu-0"
    # ...
    gpu_worker = true
    odf_worker = false
  },
  {
    name       = "worker-odf-0"
    # ...
    gpu_worker = false
    odf_worker = true
  },
]
```

### Step 2: Initialize & Deploy

```bash
cd ipi-method/openshiftbaremetal/
terraform init
terraform plan
terraform apply
```

### Step 3: Access the Cluster

After deployment completes:

```bash
export KUBECONFIG=modules/ocp-baremetal/generated/kubeconfig
oc get nodes
oc get co              # Cluster operators
oc get csv -A          # Installed operators
```

| Endpoint | URL |
|----------|-----|
| API | `https://api.<cluster>.<domain>:6443` |
| Console | `https://console-openshift-console.apps.<cluster>.<domain>` |
| OpenShift AI | `https://rhods-dashboard-redhat-ods-applications.apps.<cluster>.<domain>` |

## Variable Reference

### Cluster & Networking

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `cluster_name` | string | — | OCP cluster name |
| `base_domain` | string | — | Base DNS domain |
| `ocp_version` | string | `4.20` | OpenShift version |
| `machine_network_cidr` | string | — | Machine network CIDR |
| `cluster_network_cidr` | string | `10.128.0.0/14` | Pod network CIDR |
| `service_network_cidr` | string | `172.30.0.0/16` | Service network CIDR |
| `api_vip` | string | — | API virtual IP |
| `ingress_vip` | string | — | Ingress virtual IP |
| `gateway` | string | — | Default gateway |
| `dns_servers` | list(string) | — | DNS server IPs |

### Node Definitions

| Variable | Type | Description |
|----------|------|-------------|
| `master_nodes` | list(object) | Master node BMC/network config (min 3) |
| `worker_nodes` | list(object) | Worker node config with `gpu_worker` and `odf_worker` flags |
| `haproxy_hosts` | list(object) | HAProxy LB hosts (optional) |

### Local Quay Mirror

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_quay_mirror` | bool | `false` | Enable local Quay mirror |
| `quay_host` | string | — | Quay server IP/FQDN |
| `quay_port` | number | `8443` | Quay HTTPS port |
| `quay_admin_user` | string | `quayadmin` | Quay admin user |
| `quay_admin_password` | string | — | Quay admin password |
| `quay_ca_cert_file` | string | — | Quay CA certificate PEM |
| `mirror_operators` | list(object) | All required | Operators to mirror |

### GPU / NVIDIA

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ngc_api_key` | string | — | NVIDIA NGC API key |
| `nls_token_file` | string | — | NLS license token file path |
| `vgpu_driver_version` | string | `560.35.03` | vGPU driver version |
| `gpu_rdma_enabled` | bool | `false` | Enable GPUDirect RDMA |
| `entitlement_pem_file` | string | — | Red Hat entitlement PEM |

### Feature Toggles

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_odf` | bool | `true` | Deploy ODF storage |
| `enable_openshift_ai` | bool | `true` | Deploy RHOAI |
| `enable_servicemesh` | bool | `true` | Deploy Service Mesh |
| `enable_serverless` | bool | `true` | Deploy Serverless |
| `enable_gpu_monitoring` | bool | `true` | Deploy DCGM dashboard |
| `enable_cluster_autoscaler` | bool | `false` | Deploy Cluster Autoscaler |
| `enable_etcd_backup` | bool | `true` | Deploy etcd backup CronJob |
| `enable_metallb` | bool | `false` | Deploy MetalLB Operator (optional) |
| `enable_sriov` | bool | `false` | Deploy SR-IOV Network Operator (optional) |
| `enable_submariner` | bool | `false` | Deploy Submariner broker (DC↔DR) |
| `enable_odf_dr` | bool | `false` | Enable ODF DR replication |
| `enable_nim` | bool | `false` | Enable NVIDIA NIM |
| `enable_ldap` | bool | `false` | Enable LDAP/OAuth identity provider |

### Submariner (DC Broker)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_submariner` | bool | `false` | Deploy Submariner broker |
| `submariner_cable_driver` | string | `libreswan` | Tunnel driver |
| `submariner_gateway_count` | number | `1` | Number of gateway nodes |
| `submariner_globalnet_enabled` | bool | `false` | Enable Globalnet for overlapping CIDRs |

### ODF DR Replication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_odf_dr` | bool | `false` | Enable ODF DR replication |
| `odf_dr_mode` | string | `regional-dr` | `regional-dr` (async) or `metro-dr` (sync) |
| `odf_dr_replication_schedule` | string | `*/5 * * * *` | Cron schedule for async mirroring |
| `odf_dr_peer_cluster_name` | string | — | Name of the DR peer cluster |
| `odf_dr_s3_endpoint` | string | — | S3 endpoint for DR metadata |
| `odf_dr_s3_bucket` | string | `odf-dr-metadata` | S3 bucket name |

### MetalLB

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_metallb` | bool | `false` | Deploy MetalLB Operator for bare metal load balancing |
| `metallb_address_pools` | list(object) | `[]` | IPAddressPool definitions for LoadBalancer services |
| `metallb_l2_advertisements` | list(object) | `[]` | L2Advertisement definitions |

#### `metallb_address_pools` object

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | — | Pool name (e.g. `default-pool`) |
| `addresses` | list(string) | — | IP ranges (e.g. `["192.168.10.100-192.168.10.120"]`) |
| `auto_assign` | bool | `true` | Automatically assign IPs from this pool |

#### `metallb_l2_advertisements` object

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | — | Advertisement name |
| `pool_names` | list(string) | — | Pools to advertise via L2 |

### SR-IOV

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_sriov` | bool | `false` | Deploy SR-IOV Network Operator |
| `sriov_network_devices` | list(object) | `[]` | SR-IOV network device policies (PF names, VF counts) |
| `sriov_networks` | list(object) | `[]` | SR-IOV network attachment definitions |

#### `sriov_network_devices` object

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | — | Policy name |
| `pf_names` | list(string) | — | Physical Function NIC names (e.g. `["ens8f0"]`) |
| `num_vfs` | number | — | Number of Virtual Functions to create |
| `resource_name` | string | — | SR-IOV resource name (e.g. `sriov_gpu_nic`) |
| `device_type` | string | `netdevice` | Device type: `netdevice` or `vfio-pci` |
| `root_devices` | list(string) | `[]` | Root device PCI addresses (optional filter) |

#### `sriov_networks` object

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | — | Network attachment name |
| `resource_name` | string | — | Matches `resource_name` from device policy |
| `target_namespace` | string | — | Namespace where the network is available |
| `vlan` | number | `0` | VLAN tag (0 = untagged) |
| `ipam` | string | `"{}"` | IPAM configuration JSON string |

### LDAP / OAuth Integration

The **LDAP/OAuth module** configures OpenShift to authenticate users against a corporate LDAP directory (e.g. Active Directory). It deploys:

1. **OAuth CR** — Adds an LDAP identity provider to the cluster OAuth configuration
2. **LDAP Group Sync CronJob** — Periodically syncs LDAP groups into OpenShift Group objects
3. **RBAC ClusterRoleBindings** — Maps LDAP groups to OpenShift ClusterRoles (e.g. `cluster-admin`, `edit`, `view`)
4. **Optional kubeadmin removal** — Removes the default `kubeadmin` user after LDAP is configured (irreversible)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_ldap` | bool | `false` | Enable LDAP identity provider |
| `ldap_provider_name` | string | `"LDAP"` | Display name in OpenShift login |
| `ldap_url` | string | `""` | LDAP URL (`ldaps://host:636/...`) |
| `ldap_bind_dn` | string | `""` | Service account DN for LDAP bind |
| `ldap_bind_password` | string | `""` | Bind password (sensitive) |
| `ldap_ca_cert_file` | string | `""` | CA certificate path on bastion |
| `ldap_insecure` | string | `"false"` | Allow insecure LDAP connections |
| `ldap_attr_id` | string | `"dn"` | LDAP attribute for identity |
| `ldap_attr_email` | string | `"mail"` | LDAP attribute for email |
| `ldap_attr_name` | string | `"cn"` | LDAP attribute for display name |
| `ldap_attr_preferred_username` | string | `"sAMAccountName"` | LDAP attribute for username |
| `enable_ldap_group_sync` | bool | `true` | Enable LDAP group sync CronJob |
| `ldap_group_base_dn` | string | `""` | Group search base DN |
| `ldap_group_filter` | string | `"(objectClass=group)"` | Group search filter |
| `ldap_group_sync_schedule` | string | `"*/30 * * * *"` | Cron schedule for group sync |
| `ldap_group_role_bindings` | list(object) | `[]` | Group-to-ClusterRole mappings |
| `disable_kubeadmin` | bool | `false` | Remove kubeadmin user (irreversible) |

## Day 1 vs Day 2 Separation

| Phase | Var File | Pipeline | Scope |
|---|---|---|---|
| Day 1 — Install | `terraform.tfvars` | `azure-pipelines.yml` | Cluster install, core operators, networking |
| Day 2 — Post-Install | `day2-terraform.tfvars` | `azure-pipelines-day2.yml` | Logging, OADP backup, LDAP/OAuth, GitOps (ArgoCD), Pipelines (Tekton) |

Day 2 operations are applied separately after cluster installation completes:

```bash
terraform apply -var-file=terraform.tfvars -var-file=day2-terraform.tfvars
```

See the [IPI Day 2 Pipeline documentation](../pipeline/terraform-ado-pipeline-day2.md) for details.
