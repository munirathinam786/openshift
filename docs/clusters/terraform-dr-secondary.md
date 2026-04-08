# Terraform Automation — DR Secondary Workload Cluster

The DR Secondary cluster mirrors the DC Primary workload cluster with **Submariner agent** connectivity and **ODF DR replication** support.

!!! info "Multi-Cluster Architecture"
    This is one of **four cluster environments**. See also:
    [Multi-Cluster Overview](../architecture/terraform-multi-cluster-overview.md) |
    [DC Primary](terraform-ocp-baremetal.md) |
    [Management DC](terraform-mgmt-dc.md) |
    [Management DR](terraform-mgmt-dr.md)

## Architecture

![DR Secondary Architecture](../diagrams/clusters/09-dr-secondary-architecture.svg){: .drawio-diagram }

???+ note "Draw.io Source: DR Secondary Architecture"
    [:material-download: Download .drawio file](../diagrams/clusters/09-dr-secondary-architecture.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## What's Different from DC Primary

| Aspect | DC Primary | DR Secondary |
|--------|-----------|--------------|
| Folder | `ipi-method/openshiftbaremetal/` | `ipi-method/openshiftbaremetal-dr/` |
| Modules | Local (`./modules/`) | Referenced (`../openshiftbaremetal/modules/`) |
| Submariner role | Broker | Agent (connects to DC broker) |
| ODF DR | Source | Target (receives replicated data) |
| Pod CIDR | `10.128.0.0/14` | `10.132.0.0/14` (non-overlapping) |
| Service CIDR | `172.30.0.0/16` | `172.31.0.0/16` (non-overlapping) |
| Machine CIDR | `10.142.41.0/24` | `10.143.41.0/24` (DR site) |

## Submariner Agent Configuration

The DR cluster connects to the DC Primary broker:

![DR Secondary Connectivity](../diagrams/clusters/10-dr-secondary-connectivity.svg){: .drawio-diagram }

???+ note "Draw.io Source: DR Secondary Connectivity"
    [:material-download: Download .drawio file](../diagrams/clusters/10-dr-secondary-connectivity.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

```hcl
# terraform.tfvars (DR Secondary)
enable_submariner              = true
submariner_broker_api_url      = "https://api.ocp-ai.example.com:6443"
submariner_broker_token        = "REPLACE_BROKER_TOKEN"
submariner_cable_driver        = "libreswan"
submariner_globalnet_enabled   = false
```

## ODF DR Replication

Once both Submariner and ODF are enabled, ODF DR can replicate PVCs:

```hcl
# terraform.tfvars (DR Secondary)
enable_odf_dr               = true
odf_dr_mode                 = "regional-dr"     # async
odf_dr_replication_schedule = "*/5 * * * *"      # every 5 minutes
odf_dr_peer_cluster_name    = "ocp-ai"           # DC Primary cluster name
odf_dr_s3_endpoint          = "https://rgw.ocp-ai.example.com"
odf_dr_s3_bucket            = "odf-dr-metadata"
odf_dr_s3_access_key        = "REPLACE_S3_ACCESS_KEY"
odf_dr_s3_secret_key        = "REPLACE_S3_SECRET_KEY"
```

## Variable Reference — DR-Specific

All DC Primary variables are also available. The following are **unique to DR**:

### Submariner Agent

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_submariner` | bool | `false` | Enable Submariner agent |
| `submariner_broker_api_url` | string | — | DC Primary API URL |
| `submariner_broker_token` | string | — | Broker SA token |
| `submariner_broker_ca` | string | — | Broker cluster CA |
| `submariner_cable_driver` | string | `libreswan` | Tunnel driver |
| `submariner_globalnet_enabled` | bool | `false` | Globalnet for overlapping CIDRs |

### ODF DR

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_odf_dr` | bool | `false` | Enable ODF DR replication |
| `odf_dr_mode` | string | `regional-dr` | `regional-dr` or `metro-dr` |
| `odf_dr_replication_schedule` | string | `*/5 * * * *` | Async mirror schedule |
| `odf_dr_peer_cluster_name` | string | — | DC Primary cluster name |
| `odf_dr_s3_endpoint` | string | — | S3 endpoint for metadata |
| `odf_dr_s3_bucket` | string | `odf-dr-metadata` | S3 bucket |

## Cross-Cluster Connectivity — DR Secondary

The DR Secondary has connections to DC Primary (Submariner + ODF) and both management clusters:

![DR Failover ACM Promotion](../diagrams/clusters/19-dr-failover-acm-promotion.svg){: .drawio-diagram }

???+ note "Draw.io Source: DR Failover ACM Promotion"
    [:material-download: Download .drawio file](../diagrams/clusters/19-dr-failover-acm-promotion.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| # | Connection | Direction | Protocol | Purpose |
|---|------------|-----------|----------|----------|
| 1 | DR Agent → DC Broker | Outbound | TCP 6443 | Register with Submariner broker |
| 2 | DR Gateway ↔ DC Gateway | Bidirectional | UDP 4500 + ESP | Encrypted pod-to-pod tunnel |
| 3 | DC Ceph → DR Ceph | Inbound | TCP 6789, 3300 | Receive replicated RBD images |
| 4 | ACM Hub → DR API | Inbound | TCP 6443 | Klusterlet agent, governance policies |
| 5 | ACS Central → DR | Inbound | TCP 443 | SecuredCluster sensor deployment |
| 6 | ACM Standby → DR | Failover | TCP 6443 | Re-import on DC site failure |

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
    The DR Secondary cluster now also mirrors **Submariner** (`stable-0.18`), **OADP** (`stable-1.4`), and **ODR** (`stable-4.16`) operators.

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
cd openshiftbaremetal-dr/
vi terraform.tfvars        # Update DR site values
terraform init
terraform plan
terraform apply
```
