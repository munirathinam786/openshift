# Terraform Automation — Management Cluster DC

The Management DC cluster is the **central operations hub** running ACM, ACS Central, and Quay Enterprise to manage all workload clusters.

!!! info "Multi-Cluster Architecture"
    See also:
    [Multi-Cluster Overview](../architecture/terraform-multi-cluster-overview.md) |
    [DC Primary](terraform-ocp-baremetal.md) |
    [DR Secondary](terraform-dr-secondary.md) |
    [Management DR](terraform-mgmt-dr.md)

## Architecture

![Mgmt DC Architecture](../diagrams/clusters/11-mgmt-dc-architecture.svg){: .drawio-diagram }

???+ note "Draw.io Source: Mgmt DC Architecture"
    [:material-download: Download .drawio file](../diagrams/clusters/11-mgmt-dc-architecture.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Inter-Cluster Connectivity — Mgmt DC

The Management DC cluster is the **control plane hub** with outbound connections to every other cluster:

![Mgmt DC Connectivity](../diagrams/clusters/12-mgmt-dc-connectivity.svg){: .drawio-diagram }

???+ note "Draw.io Source: Mgmt DC Connectivity"
    [:material-download: Download .drawio file](../diagrams/clusters/12-mgmt-dc-connectivity.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| # | Connection | Direction | Protocol | Purpose |
|---|------------|-----------|----------|----------|
| 1-2 | ACM Hub → DC/DR API | Outbound | TCP 6443 | Deploy Klusterlet, deliver policies, governance |
| 3-4 | DC/DR Klusterlet → ACM Hub | Inbound | TCP 443 | Cluster status, health, resource inventory |
| 5-6 | DC/DR Metrics → Observability | Inbound | TCP 10902 | Prometheus remote-write to Thanos Receive |
| 7-9 | Sensors → ACS Central | Inbound | TCP 443 (gRPC) | CVE reports, compliance results, runtime alerts |
| 10 | Quay DC ↔ Quay DR | Bidirectional | TCP 443 (S3) | Image geo-replication via shared S3 storage |
| 11 | ACM Hub → ACM Standby | Failover | TCP 443 | Manual failover triggers DR promotion |

### Quay Enterprise — Geo-Replication Flow

![ACM Observability Flow](../diagrams/clusters/13-acm-observability-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: ACM Observability Flow"
    [:material-download: Download .drawio file](../diagrams/clusters/13-acm-observability-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### ACM Observability Data Flow

![ACS Central Security Stack](../diagrams/clusters/14-acs-central-security-stack.svg){: .drawio-diagram }

???+ note "Draw.io Source: ACS Central Security Stack"
    [:material-download: Download .drawio file](../diagrams/clusters/14-acs-central-security-stack.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Components

### ACM — Advanced Cluster Management

![ACM Hub Components](../diagrams/clusters/15-acm-hub-components.svg){: .drawio-diagram }

???+ note "Draw.io Source: ACM Hub Components"
    [:material-download: Download .drawio file](../diagrams/clusters/15-acm-hub-components.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Feature | Description |
|---------|-------------|
| **Cluster Lifecycle** | Import, upgrade, and decommission managed clusters |
| **Governance** | Deploy policies (security, compliance, configuration) across clusters |
| **Application Lifecycle** | GitOps-based application deployment via Channels + Subscriptions |
| **Observability** | Cross-cluster metrics via Thanos (requires S3-compatible storage) |
| **Search** | Federated search across all managed cluster resources |

### ACS — Advanced Cluster Security (Central)

![Quay Geo-Replication Failover](../diagrams/clusters/20-quay-geo-replication-failover.svg){: .drawio-diagram }

???+ note "Draw.io Source: Quay Geo-Replication Failover"
    [:material-download: Download .drawio file](../diagrams/clusters/20-quay-geo-replication-failover.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Feature | Description |
|---------|-------------|
| **Vulnerability Management** | Scan images for CVEs (Clair-based) |
| **Compliance** | CIS Benchmarks, NIST 800-53, PCI-DSS |
| **Runtime** | eBPF-based anomaly detection |
| **Network Policies** | Auto-generated network segmentation |
| **Risk Profiling** | Deployment risk scoring |

### Quay Enterprise

| Feature | Description |
|---------|-------------|
| **Image Registry** | Enterprise container image hosting |
| **Clair Scanner** | Integrated image vulnerability scanning |
| **Mirror Sync** | Automatic upstream mirroring |
| **Geo-Replication** | Replicate to Mgmt DR Quay instance |
| **Robot Accounts** | CI/CD integration tokens |

## Variable Reference

### ACM

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_acm` | bool | `true` | Deploy ACM Hub |
| `acm_channel` | string | `release-2.11` | Operator channel |
| `acm_instance_name` | string | `multiclusterhub` | MCH CR name |
| `acm_enable_observability` | bool | `false` | Enable Thanos-based observability |
| `acm_s3_bucket` | string | — | S3 bucket (observability) |
| `acm_s3_endpoint` | string | — | S3 endpoint (ODF RGW or MinIO) |

### ACS

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_acs` | bool | `true` | Deploy ACS Central + SecuredCluster |
| `acs_channel` | string | `stable` | Operator channel |
| `acs_central_admin_password` | string | — | Initial admin password |
| `acs_central_storage_size` | string | `100Gi` | Central DB PVC size |

### Quay Enterprise

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_quay_enterprise` | bool | `true` | Deploy Quay on-cluster |
| `quay_enterprise_channel` | string | `stable-3.12` | Operator channel |
| `quay_enterprise_instance_name` | string | `central-quay` | QuayRegistry CR name |
| `quay_enterprise_storage_size` | string | `100Gi` | Storage PVC size |
| `quay_enterprise_superuser` | string | `quayadmin` | Superuser account |

### Quay Mirror Replication (Local Quay → Quay Enterprise)

The **quay-mirror-replicate** module replicates operator and OCP release images from the internet-facing local Quay to the on-cluster Quay Enterprise instance.

![Quay Geo-Replication Flow](../diagrams/clusters/21-quay-geo-replication-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: Quay Geo-Replication Flow"
    [:material-download: Download .drawio file](../diagrams/clusters/21-quay-geo-replication-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_quay_mirror_replicate` | bool | `false` | Enable replication from local Quay to Quay Enterprise |
| `quay_enterprise_route` | string | `""` | Quay Enterprise route URL (auto-discovered if empty) |
| `quay_enterprise_password` | string | `""` | Quay Enterprise admin password |
| `quay_enterprise_mirror_org` | string | `ocp4-mirror` | Organization in Quay Enterprise for mirrored content |

!!! info "Operator Mirroring Flow"
    1. **Local Quay** (internet-facing) downloads operators from Red Hat CDN using `oc mirror`
    2. **quay-mirror-replicate** module replicates all images from local Quay to Quay Enterprise on the management cluster
    3. An **ImageDigestMirrorSet** is applied to redirect cluster image pulls to the local Quay Enterprise
    4. A **CatalogSource** pointing to the replicated operator index is created in the cluster

### LDAP / OAuth Integration

The **LDAP/OAuth module** configures OpenShift to authenticate users against a corporate LDAP directory. It deploys:

1. **OAuth CR** — Adds an LDAP identity provider to the cluster OAuth configuration
2. **LDAP Group Sync CronJob** — Periodically syncs LDAP groups into OpenShift Group objects
3. **RBAC ClusterRoleBindings** — Maps LDAP groups to OpenShift ClusterRoles
4. **Optional kubeadmin removal** — Removes the default `kubeadmin` user after LDAP is configured

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_ldap` | bool | `false` | Enable LDAP identity provider |
| `ldap_url` | string | `""` | LDAP URL (`ldaps://host:636/...`) |
| `ldap_bind_dn` | string | `""` | Service account DN |
| `ldap_bind_password` | string | `""` | Bind password (sensitive) |
| `enable_ldap_group_sync` | bool | `true` | Enable group sync CronJob |
| `ldap_group_role_bindings` | list(object) | `[]` | Group-to-ClusterRole mappings |
| `disable_kubeadmin` | bool | `false` | Remove kubeadmin (irreversible) |

!!! info "Mirrored Operators (Updated)"
    The Management DC cluster now also mirrors **OADP** (`stable-1.4`), **Submariner** (`stable-0.18`), and **ODR Hub** operators.

## ACM Cluster Import

The Management DC cluster can **import workload clusters** (DC Primary, DR Secondary) into the ACM Hub as ManagedClusters. This enables centralized governance, policy delivery, and observability across all clusters.

![Acm Import Topology](../diagrams/clusters/23-acm-import-topology.svg){: .drawio-diagram }

???+ note "Draw.io Source: Acm Import Topology"
    [:material-download: Download .drawio file](../diagrams/clusters/23-acm-import-topology.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Resource | Description |
|----------|-------------|
| **ManagedCluster** | Registers each workload cluster with ACM and deploys the Klusterlet agent |
| **KlusterletAddonConfig** | Enables add-ons: Application Manager, Policy Controller, Search, Cert Policy, IAM Policy |
| **ManagedClusterSet** | Groups clusters for placement and policy scoping |

!!! tip "Dedicated Pipeline"
    ACM Cluster Import has a separate pipeline: [ACM Cluster Import Pipeline](../pipeline/terraform-acm-import-pipeline.md)
    ```bash
    terraform apply -var-file=terraform.tfvars -var-file=acm-import.tfvars
    ```

## ACM DR Applications

The Management DC cluster manages **application-level disaster recovery** using OpenShift DR (ODR). DRPolicy and DRPlacementControl resources are created on the ACM Hub to protect applications across DC and DR clusters.

![Acm Dr Application Failover](../diagrams/clusters/24-acm-dr-application-failover.svg){: .drawio-diagram }

???+ note "Draw.io Source: Acm Dr Application Failover"
    [:material-download: Download .drawio file](../diagrams/clusters/24-acm-dr-application-failover.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Action | Description |
|--------|-------------|
| **Configure** | Create DRPolicy + DRPlacementControl (initial setup) |
| **Failover** | Move applications to DR cluster when DC is unavailable |
| **Failback** | Restore applications to DC after recovery |
| **Relocate** | Planned migration between healthy clusters |

!!! tip "Dedicated Pipeline"
    ACM DR has a separate pipeline: [ACM DR Failover/Failback Pipeline](../pipeline/terraform-acm-dr-pipeline.md)
    ```bash
    terraform apply -var-file=terraform.tfvars -var-file=acm-dr.tfvars
    ```

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

## Quick Start

```bash
cd ipi-method/mgmt-dc/
vi terraform.tfvars
terraform init
terraform plan
terraform apply
```

After deployment, access:

| Service | URL |
|---------|-----|
| OCP Console | `https://console-openshift-console.apps.mgmt-dc.example.com` |
| ACM Hub | `https://multicloud-console.apps.mgmt-dc.example.com` |
| ACS Central | `https://central-stackrox.apps.mgmt-dc.example.com` |
| Quay Registry | `https://central-quay-quay-enterprise.apps.mgmt-dc.example.com` |
