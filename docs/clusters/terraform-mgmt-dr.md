# Terraform Automation — Management Cluster DR

The Management DR cluster is the **standby operations hub** that can be promoted to active during a DC site failure.

!!! info "Multi-Cluster Architecture"
    See also:
    [Multi-Cluster Overview](../architecture/terraform-multi-cluster-overview.md) |
    [DC Primary](terraform-ocp-baremetal.md) |
    [DR Secondary](terraform-dr-secondary.md) |
    [Management DC](terraform-mgmt-dc.md)

## Architecture

![Mgmt DR Architecture](../diagrams/clusters/16-mgmt-dr-architecture.svg){: .drawio-diagram }

???+ note "Draw.io Source: Mgmt DR Architecture"
    [:material-download: Download .drawio file](../diagrams/clusters/16-mgmt-dr-architecture.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Inter-Cluster Connectivity — Mgmt DR

The Management DR cluster connects inbound to Mgmt DC services and stands ready for failover promotion:

![Mgmt DR Connectivity](../diagrams/clusters/17-mgmt-dr-connectivity.svg){: .drawio-diagram }

???+ note "Draw.io Source: Mgmt DR Connectivity"
    [:material-download: Download .drawio file](../diagrams/clusters/17-mgmt-dr-connectivity.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| # | Connection | Direction | Protocol | Purpose |
|---|------------|-----------|----------|----------|
| 1 | ACS Sensor → ACS Central (DC) | Outbound | TCP 443 (gRPC) | Vulnerability reports, compliance results, runtime alerts |
| 2 | Quay DC ↔ Quay DR | Bidirectional | TCP 443 (S3 API) | Image geo-replication via shared S3 backend |
| 3 | ACM Hub → ACM Standby | Inbound (failover) | TCP 443 | Promotion trigger during DC site failure |
| 4-5 | ACM Standby → Workloads | Post-failover | TCP 6443 | Re-import managed clusters after promotion |

## Role Comparison — DC vs DR Management

| Component | Mgmt DC | Mgmt DR |
|-----------|---------|---------|
| **ACM** | Active Hub — manages all clusters | Standby — promotable on failover |
| **ACS** | Central — full UI, policies, scanner | SecuredCluster only — sensor + collector |
| **Quay** | Primary registry | Geo-replicated mirror |
| **ODF** | Full storage cluster | Full storage cluster |

## ACS SecuredCluster

The DR management cluster runs only the **SecuredCluster** components (no Central):

![ACS SecuredCluster Components](../diagrams/clusters/18-acs-secured-cluster-components.svg){: .drawio-diagram }

???+ note "Draw.io Source: ACS SecuredCluster Components"
    [:material-download: Download .drawio file](../diagrams/clusters/18-acs-secured-cluster-components.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

```hcl
# terraform.tfvars (Mgmt DR)
enable_acs           = true
acs_channel          = "stable"
acs_central_endpoint = "central-stackrox.apps.mgmt-dc.example.com:443"
```

## DR Failover — ACM Promotion

![ACM DR Applications](../diagrams/clusters/22-acm-dr-applications.svg){: .drawio-diagram }

???+ note "Draw.io Source: ACM DR Applications"
    [:material-download: Download .drawio file](../diagrams/clusters/22-acm-dr-applications.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### Quay Geo-Replication — Failover Behavior

![Quay Failover Behavior](../diagrams/clusters/25-quay-failover-behavior.svg){: .drawio-diagram }

???+ note "Draw.io Source: Quay Failover Behavior"
    [:material-download: Download .drawio file](../diagrams/clusters/25-quay-failover-behavior.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Variable Reference — DR-Specific

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_acm` | bool | `true` | Deploy ACM (standby mode) |
| `enable_acs` | bool | `true` | Deploy ACS SecuredCluster (no Central) |
| `acs_central_endpoint` | string | — | ACS Central endpoint from Mgmt DC |
| `enable_quay_enterprise` | bool | `true` | Deploy Quay (geo-replicated) |

All other variables are identical to [Management DC](terraform-mgmt-dc.md).

### Quay Mirror Replication (Local Quay → Quay Enterprise)

The **quay-mirror-replicate** module replicates operator and OCP release images from the internet-facing local Quay to the on-cluster Quay Enterprise instance on the DR management cluster.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_quay_mirror_replicate` | bool | `false` | Enable replication from local Quay to Quay Enterprise |
| `quay_enterprise_route` | string | `""` | Quay Enterprise route URL (auto-discovered if empty) |
| `quay_enterprise_password` | string | `""` | Quay Enterprise admin password |
| `quay_enterprise_mirror_org` | string | `ocp4-mirror` | Organization in Quay Enterprise for mirrored content |

!!! info "Operator Mirroring Flow"
    The DR cluster receives the same mirrored operator content as the DC cluster. The local Quay (internet-facing) downloads from Red Hat CDN, then the replicate module pushes to both DC and DR Quay Enterprise instances independently.

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
    The Management DR cluster now also mirrors **OADP** (`stable-1.4`), **Submariner** (`stable-0.18`), and **ODR Hub** operators.

## ACM Cluster Import (Post-Failover)

After failover promotion, the Management DR cluster can **import workload clusters** into its ACM Hub. The same `acm-import.tfvars` configuration and pipeline are used as on Mgmt DC.

![Acm Post Failover Reimport](../diagrams/clusters/26-acm-post-failover-reimport.svg){: .drawio-diagram }

???+ note "Draw.io Source: Acm Post Failover Reimport"
    [:material-download: Download .drawio file](../diagrams/clusters/26-acm-post-failover-reimport.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

!!! tip "Dedicated Pipeline"
    ACM Cluster Import: [ACM Cluster Import Pipeline](../pipeline/terraform-acm-import-pipeline.md)
    Set `acmHub = mgmt-dr` to target the promoted DR hub.

## ACM DR Applications (Post-Failover)

After promotion, the Management DR cluster takes over DR application management. DRPolicy and DRPlacementControl resources are re-created to manage failback to the recovered DC site.

!!! tip "Dedicated Pipeline"
    ACM DR: [ACM DR Failover/Failback Pipeline](../pipeline/terraform-acm-dr-pipeline.md)
    Set `acmHub = mgmt-dr` when running from the promoted DR hub.

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
cd ipi-method/mgmt-dr/
vi terraform.tfvars
terraform init
terraform plan
terraform apply
```

After deployment, access:

| Service | URL |
|---------|-----|
| OCP Console | `https://console-openshift-console.apps.mgmt-dr.dr.example.com` |
| ACM Standby | `https://multicloud-console.apps.mgmt-dr.dr.example.com` |
| Quay Registry | `https://central-quay-quay-enterprise.apps.mgmt-dr.dr.example.com` |
