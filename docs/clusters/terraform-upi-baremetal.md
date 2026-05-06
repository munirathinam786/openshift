# Terraform Automation — UPI (User Provisioned Infrastructure) Baremetal

This section provides the **Terraform IaC** for deploying OpenShift Container Platform on bare metal using the **UPI (User Provisioned Infrastructure)** method with Red Hat OpenShift AI, NVIDIA GPU support, and all required operators.

!!! info "IPI vs UPI"
    The existing DC Primary cluster uses **IPI** (Installer Provisioned Infrastructure).
    This UPI method gives you **full control** over infrastructure provisioning — no BMC/iDRAC management required.
    See also:
    [DC Primary (IPI)](terraform-ocp-baremetal.md) |
    [DR Secondary](terraform-dr-secondary.md) |
    [UPI ADO Pipeline](../pipeline/terraform-upi-ado-pipeline.md)

## UPI vs IPI — Key Differences

| Aspect | IPI | UPI |
|--------|-----|-----|
| **Platform type** | `platform: baremetal` | `platform: none` |
| **BMC management** | Installer controls hardware via iDRAC/Redfish | No BMC — operator boots nodes manually |
| **Load balancer** | Installer-managed keepalived (VIPs) | External HAProxy load balancer required |
| **Node booting** | Automated via virtual media | Manual PXE, ISO, or operator-driven boot |
| **CSR approval** | Automatic | Explicit approval required for worker nodes |
| **Bootstrap node** | Managed by installer | Operator provisions and removes manually |
| **Install command** | `openshift-baremetal-install create cluster` | `openshift-install create ignition-configs` |
| **Installer binary** | `openshift-baremetal-install` | `openshift-install` |

## Overview

The UPI Terraform project automates the full deployment lifecycle in distinct phases:

![UPI Deployment Overview](../diagrams/clusters/05-upi-deployment-overview.svg){: .drawio-diagram }

???+ note "Draw.io Source: UPI Deployment Overview"
    [:material-download: Download .drawio file](../diagrams/clusters/05-upi-deployment-overview.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## UPI Deployment Phases

![UPI Deployment Phases](../diagrams/clusters/06-upi-deployment-phases.svg){: .drawio-diagram }

???+ note "Draw.io Source: UPI Deployment Phases"
    [:material-download: Download .drawio file](../diagrams/clusters/06-upi-deployment-phases.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Project Structure

```
upi-method/
├── openshiftbaremetal/           # DC Primary — workload cluster (UPI)
│   ├── main.tf                   # UPI orchestration — multi-phase install + day-2 ops
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── outputs.tf
│   ├── versions.tf
│   └── modules/                  # Shared modules (referenced by all UPI clusters)
│       ├── dns/                  # DNS record generation & validation
│       ├── haproxy/              # External HAProxy load balancer (required for UPI)
│       ├── quay-mirror/          # Local Quay mirror registry (disconnected)
│       ├── install-config/       # install-config.yaml generation (platform: none)
│       ├── ignition/             # Manifest customization + ignition generation
│       ├── ignition-server/      # HTTP server for serving ignition configs
│       ├── bootstrap/            # Bootstrap node provisioning
│       ├── control-plane/        # Control plane node boot orchestration
│       ├── bootstrap-complete/   # Wait for bootstrap completion
│       ├── bootstrap-cleanup/    # Remove bootstrap node from LB + power off
│       ├── compute-nodes/        # Worker node boot orchestration
│       ├── cluster-complete/     # CSR approval + install completion
│       ├── nfd-operator/         # Node Feature Discovery operator
│       ├── gpu-operator/         # NVIDIA GPU Operator + ClusterPolicy
│       ├── odf-operator/         # OpenShift Data Foundation (Ceph storage)
│       ├── servicemesh/          # OpenShift Service Mesh + Kiali
│       ├── serverless/           # OpenShift Serverless (KnativeServing)
│       ├── openshift-ai/         # Red Hat OpenShift AI + DataScienceCluster
│       ├── gpu-monitoring/       # NVIDIA DCGM Exporter dashboard
│       ├── metallb-operator/     # MetalLB load balancer (optional)
│       ├── sriov-operator/       # SR-IOV Network Operator (optional)
│       ├── cluster-autoscaler/   # GPU-aware Cluster Autoscaler
│       ├── etcd-backup/          # Nightly etcd backup CronJob
│       ├── submariner/           # Submariner cross-cluster networking
│       ├── odf-dr/               # ODF DR replication
│       ├── acm/                  # Advanced Cluster Management
│       ├── acs/                  # Advanced Cluster Security
│       ├── quay-enterprise/      # Quay Enterprise Registry
│       ├── ldap-oauth/           # LDAP/OAuth identity provider + group sync
│       ├── cluster-logging/      # Cluster Logging with ElasticSearch/Fluentd
│       ├── oadp/                 # OADP Backup & Recovery
│       ├── openshift-gitops/     # ArgoCD GitOps operator
│       ├── openshift-pipelines/  # Tekton CI/CD Pipelines
│       ├── acm-cluster-import/   # ACM managed cluster import (mgmt clusters)
│       ├── acm-dr-applications/  # ACM DR application failover (mgmt clusters)
│       ├── compliance-operator/      # OpenSCAP compliance scanning (CIS/NIST/PCI-DSS)
│       ├── file-integrity-operator/  # AIDE file integrity monitoring
│       ├── cert-manager/             # TLS certificate lifecycle management
│       ├── gatekeeper/               # OPA Gatekeeper policy enforcement
│       ├── network-policies/         # Default-deny network policies with allowlists
│       ├── nmstate-operator/         # NMState node network configuration
│       ├── external-dns/             # Automated DNS record management
│       ├── ingress-controller/       # Custom ingress controller tuning
│       ├── multus-networks/          # Multus secondary CNI networks
│       ├── network-observability/    # eBPF Network Observability with FlowCollector
│       ├── alertmanager-config/      # Alertmanager routing (Slack/PagerDuty/Email)
│       ├── custom-grafana-dashboards/ # Grafana dashboards (capacity/GPU/namespace)
│       ├── opentelemetry-collector/  # OpenTelemetry distributed tracing with Tempo
│       ├── loki-logging/             # LokiStack log aggregation
│       ├── thanos-ruler/             # Thanos long-term metrics storage
│       ├── node-tuning-profiles/     # Performance tuning (hugepages/RT kernel/sysctl)
│       ├── image-registry/           # Internal image registry with pruning
│       ├── custom-catalogsource/     # Private operator catalog sources
│       ├── machine-config-pools/     # Custom MachineConfigPools for worker groups
│       ├── node-maintenance/         # Node Maintenance Operator for controlled drain
│       ├── cost-management/          # Red Hat Cost Management metrics
│       ├── devspaces/                # Eclipse Che / OpenShift Dev Spaces
│       ├── web-terminal/             # Browser-based web terminal
│       ├── image-streams/            # Custom ImageStreams and S2I refresh
│       ├── kuberay-operator/         # KubeRay for Ray cluster orchestration
│       ├── training-operator/        # Kubeflow Training Operator (PyTorch/TF)
│       ├── model-registry/           # ML model versioning registry
│       ├── nvidia-nim/               # NVIDIA NIM inference microservices
│       ├── mig-manager/              # NVIDIA MIG GPU partitioning
│       ├── global-load-balancer/     # Cross-cluster global load balancing
│       ├── velero-schedule/          # Velero backup schedules
│       └── dr-runbook-automation/    # DR failover/failback automation
│
├── openshiftbaremetal-dr/        # DR Secondary — workload cluster (UPI)
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
└── azure-pipelines-upi.yml      # ADO pipeline for multi-cluster UPI deployment
```

## Day 1 vs Day 2 Separation

| Phase | Var File | Pipeline | Scope |
|---|---|---|---|
| Day 1 — Install | `terraform.tfvars` | `azure-pipelines-upi.yml` | Cluster install, core operators, networking |
| Day 2 — Post-Install | `day2-terraform.tfvars` | `azure-pipelines-day2-upi.yml` | Logging, OADP backup, LDAP/OAuth, GitOps (ArgoCD), Pipelines (Tekton) |

Day 2 operations are applied separately after cluster installation completes:

```bash
terraform apply -var-file=terraform.tfvars -var-file=day2-terraform.tfvars
```

See the [UPI Day 2 Pipeline documentation](../pipeline/terraform-upi-ado-pipeline-day2.md) for details.

## Boot Methods

UPI supports three boot methods configured via the `boot_method` variable:

### PXE Boot (`boot_method = "pxe"`)

![PXE Boot Sequence](../diagrams/clusters/07-pxe-boot-sequence.svg){: .drawio-diagram }

???+ note "Draw.io Source: PXE Boot Sequence"
    [:material-download: Download .drawio file](../diagrams/clusters/07-pxe-boot-sequence.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### ISO Boot (`boot_method = "iso"`)

The RHCOS live ISO is embedded with the ignition config URL. Operator mounts the ISO via iLO/iDRAC console or USB.

### Manual Boot (`boot_method = "manual"`)

The pipeline includes a **ManualValidation** gate — the operator boots nodes outside of Terraform, then approves the pipeline to continue.

## Prerequisites

Before running the UPI deployment:

### Infrastructure Requirements

1. **Bastion node** configured with:
    - `openshift-install` binary (not `openshift-baremetal-install`)
    - `oc` CLI
    - HTTP server for ignition configs (port 8080)
    - PXE/TFTP server (if using PXE boot)

2. **External load balancer** (HAProxy) configured for:
    - API server: `api.<cluster>.<domain>` → port 6443 → all control plane nodes + bootstrap
    - Machine config: `api-int.<cluster>.<domain>` → port 22623 → all control plane nodes + bootstrap
    - Ingress HTTP: `*.apps.<cluster>.<domain>` → port 80 → all worker nodes
    - Ingress HTTPS: `*.apps.<cluster>.<domain>` → port 443 → all worker nodes

3. **DNS records** for:
    - `api.<cluster>.<domain>` → load balancer VIP
    - `api-int.<cluster>.<domain>` → load balancer VIP
    - `*.apps.<cluster>.<domain>` → ingress VIP
    - Reverse DNS for all nodes

4. **RHCOS images** served via HTTP on the bastion

### Firewall Port Requirements

The following ports must be opened in the firewall between the relevant network zones:

#### Cluster Communication Ports

| Port | Protocol | Source | Destination | Purpose |
|------|----------|--------|-------------|---------|
| 6443 | TCP | Clients / Load Balancer | Control Plane Nodes | Kubernetes API Server |
| 22623 | TCP | Cluster Nodes | Control Plane Nodes | Machine Config Server |
| 443 | TCP | Clients / Load Balancer | Worker Nodes | HTTPS Ingress (Router) |
| 80 | TCP | Clients / Load Balancer | Worker Nodes | HTTP Ingress (Router) |
| 2379-2380 | TCP | Control Plane | Control Plane | etcd peer and client |
| 10250 | TCP | Control Plane | All Nodes | Kubelet API |
| 10257 | TCP | Control Plane | Control Plane | kube-controller-manager |
| 10259 | TCP | Control Plane | Control Plane | kube-scheduler |
| 9000-9999 | TCP/UDP | All Nodes | All Nodes | Host-level services (node exporter, etc.) |
| 30000-32767 | TCP/UDP | All Nodes | All Nodes | NodePort Services (Kubernetes) |
| 4789 | UDP | All Nodes | All Nodes | VXLAN (OVN-Kubernetes overlay) |
| 6081 | UDP | All Nodes | All Nodes | Geneve (OVN-Kubernetes overlay) |

#### Infrastructure Services Ports

| Port | Protocol | Source | Destination | Purpose |
|------|----------|--------|-------------|---------|
| 53 | TCP/UDP | All Nodes | DNS Server | DNS resolution |
| 123 | UDP | All Nodes | NTP Server | Time synchronization |
| 22 | TCP | Bastion | All Nodes | SSH access |
| 8080 | TCP | Cluster Nodes | Bastion | Ignition config HTTP server |
| 67-69 | UDP | Bastion (DHCP/TFTP) | Provisioning Network | DHCP/TFTP (PXE boot) |

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

!!! warning "Disconnected / Air-Gapped Environments"
    In air-gapped deployments, the only system with internet access should be the **Local Quay** (internet-facing mirror). All other cluster nodes must pull images from local Quay or Quay Enterprise. Ensure the firewall blocks direct internet access from cluster nodes.

### Secrets & Credentials — Files on the Bastion Host

Download and place the following files on the bastion node before running Terraform:

| File | Bastion Path | Download Source | Terraform Variable |
|------|-------------|----------------|--------------------|
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

Create a Variable Group named **`ocp-baremetal-upi-secrets`** in Azure DevOps (**Project Settings → Pipelines → Library → + Variable Group**):

| Secret Name | Source | Used By | Description |
|-------------|--------|---------|-------------|
| `quay-admin-password` | Your Quay mirror admin password | All clusters | Quay mirror registry authentication |
| `ngc-api-key` | [NVIDIA NGC Portal](https://ngc.nvidia.com/setup/api-key) → Generate API Key | DC, DR | Pull vGPU driver images from `nvcr.io` |
| `odf-dr-s3-access-key` | S3-compatible storage (MinIO, AWS, etc.) for ODF DR metadata store | DR | ODF DR async replication |
| `odf-dr-s3-secret-key` | Same S3 storage provider | DR | ODF DR async replication |

!!! tip "UPI vs IPI Secrets"
    UPI does **not** require `submariner-broker-token` in the ADO Variable Group — Submariner agent configuration uses `terraform.tfvars` values from the DC Primary broker output.
    Management cluster secrets (`acs-central-admin-password`, `acm-s3-*` keys) are also passed via `terraform.tfvars` for UPI.

!!! warning "Security Best Practices"
    - Mark all secrets as **🔒 secret** (padlock icon) in ADO to mask them in pipeline logs
    - **Never** commit secrets to Git — use ADO Variable Groups or HashiCorp Vault
    - Rotate `ngc-api-key` and S3 keys periodically

### Secrets Flow — How Secrets Reach Terraform (UPI)

![UPI Secrets Flow](../diagrams/clusters/08-upi-secrets-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: UPI Secrets Flow"
    [:material-download: Download .drawio file](../diagrams/clusters/08-upi-secrets-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Quick Start

```bash
# 1. Edit terraform.tfvars with your environment values
vi upi-method/terraform.tfvars

# 2. Initialize Terraform
cd upi-method && terraform init

# 3. Plan the full deployment
terraform plan -var-file=terraform.tfvars

# 4. Apply prerequisites (DNS + LB + Quay)
terraform apply -var-file=terraform.tfvars \
  -target=module.dns \
  -target=module.haproxy \
  -target=module.quay_mirror

# 5. Generate ignition configs
terraform apply -var-file=terraform.tfvars \
  -target=module.install_config \
  -target=module.ignition \
  -target=module.ignition_server

# 6. Boot nodes and complete install
terraform apply -var-file=terraform.tfvars

# 7. Verify cluster
export KUBECONFIG=/home/kni/ocp-install/auth/kubeconfig
oc get nodes
oc get clusteroperators
```

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
| `ldap_attr_preferred_username` | string | `"sAMAccountName"` | LDAP attribute for username |
| `enable_ldap_group_sync` | bool | `true` | Enable LDAP group sync CronJob |
| `ldap_group_base_dn` | string | `""` | Group search base DN |
| `ldap_group_filter` | string | `"(objectClass=group)"` | Group search filter |
| `ldap_group_sync_schedule` | string | `"*/30 * * * *"` | Cron schedule for group sync |
| `ldap_group_role_bindings` | list(object) | `[]` | Group-to-ClusterRole mappings |
| `disable_kubeadmin` | bool | `false` | Remove kubeadmin user (irreversible) |

!!! info "Mirrored Operators (Updated)"
    The UPI clusters now also mirror **Submariner** (`stable-0.20`), **OADP** (`stable-1.6`), and **ODR** (`stable-4.20`) operators for workload clusters.
