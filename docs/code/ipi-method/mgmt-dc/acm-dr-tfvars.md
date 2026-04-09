# IPI Management DC — acm-dr.tfvars

Configuration for ACM DR applications — DRPolicy and DRPlacementControl for failover/failback
between DC Primary and DR Secondary clusters on the IPI Management DC.
Used with the [ACM DR Failover/Failback Pipeline](../../../pipeline/terraform-acm-dr-pipeline.md).

!!! info "Usage"
    This file is passed as an additional var-file alongside `terraform.tfvars`:
    ```bash
    terraform apply -var-file=terraform.tfvars -var-file=acm-dr.tfvars
    ```

!!! warning "DR Action"
    Set `dr_action = "none"` for initial configuration. Change to `failover`, `failback`, or `relocate` only when executing a DR operation.

## Variable Reference

| Variable | Type | Value | Description |
|----------|------|-------|-------------|
| `enable_acm_dr_apps` | bool | `true` | Enable the ACM DR applications module |
| `dr_policy_name` | string | `dc-dr-policy` | Name of the DRPolicy CR |
| `dr_scheduling_interval` | string | `5m` | Replication scheduling interval |
| `dr_mode` | string | `regional-dr` | DR mode (`regional-dr` or `metro-dr`) |
| `dr_clusters` | list(string) | `["dc-primary", "dr-secondary"]` | Cluster pair for DR |
| `dr_create_placement_rules` | bool | `true` | Create Placement rules for apps |
| `dr_channel_namespace` | string | `acm-app-channel` | Namespace for the app channel |
| `dr_channel_git_url` | string | `https://git.example.com/...` | Git repo for app deployments |
| `dr_channel_git_branch` | string | `main` | Git branch |
| `dr_action` | string | `none` | DR action (`none`, `failover`, `failback`, `relocate`) |
| `dr_applications` | list(object) | See below | Protected applications |

## Protected Applications

| Application | Namespace | Preferred Cluster | Failover Cluster | PVC Selector |
|-------------|-----------|-------------------|------------------|--------------|
| `agent-builder` | `agent-builder` | `dc-primary` | `dr-secondary` | `app=agent-builder` |

## Source Code

```hcl
# =============================================================================
# ACM DR Applications — Variable Values (Management DC)
# DRPolicy + DRPlacementControl for application failover/failback
# between DC Primary and DR Secondary clusters.
# =============================================================================

# ---- Enable ACM DR Applications ----
enable_acm_dr_apps = true

# ---- DRPolicy Configuration ----
dr_policy_name       = "dc-dr-policy"
dr_scheduling_interval = "5m"
dr_mode              = "regional-dr"

# ---- DR Cluster Pair ----
dr_clusters = [
  "dc-primary",
  "dr-secondary"
]

# ---- Application Channel (Git) ----
dr_create_placement_rules = true
dr_channel_namespace      = "acm-app-channel"
dr_channel_git_url        = "https://git.example.com/org/ocp-app-deployments.git"
dr_channel_git_branch     = "main"

# ---- DR Action (none = configure only, failover/failback/relocate = execute) ----
dr_action = "none"

# ---- Protected Applications ----
# Each application requires:
#   - name:              Application name (used in DRPC naming)
#   - namespace:         Kubernetes namespace on managed clusters
#   - placement_name:    Placement CR name for cluster scheduling
#   - preferred_cluster: Cluster where app normally runs
#   - failover_cluster:  Cluster to failover to
#   - pvc_selector:      Labels to match PVCs for replication
dr_applications = [
  {
    name              = "agent-builder"
    namespace         = "agent-builder"
    placement_name    = "agent-builder-placement"
    preferred_cluster = "dc-primary"
    failover_cluster  = "dr-secondary"
    pvc_selector = {
      app = "agent-builder"
    }
    kubeobject_protection = true
    s3_profile_name       = "s3-profile"
  },
  # Uncomment and configure additional applications:
  # {
  #   name              = "critical-db"
  #   namespace         = "critical-db-ns"
  #   placement_name    = "critical-db-placement"
  #   preferred_cluster = "dc-primary"
  #   failover_cluster  = "dr-secondary"
  #   pvc_selector = {
  #     app  = "critical-db"
  #     tier = "database"
  #   }
  #   kubeobject_protection = true
  #   s3_profile_name       = "s3-profile"
  # },
]
```
