# IPI Management DR — acm-dr.tfvars

Configuration for ACM DR applications — DRPolicy and DRPlacementControl for failover/failback
on the IPI Management DR cluster.
Identical to the Mgmt DC configuration — used when Mgmt DR is promoted to active ACM Hub.

!!! info "Usage"
    ```bash
    terraform apply -var-file=terraform.tfvars -var-file=acm-dr.tfvars
    ```

## Variable Reference

| Variable | Type | Value | Description |
|----------|------|-------|-------------|
| `enable_acm_dr_apps` | bool | `true` | Enable the ACM DR applications module |
| `dr_policy_name` | string | `dc-dr-policy` | Name of the DRPolicy CR |
| `dr_scheduling_interval` | string | `5m` | Replication scheduling interval |
| `dr_mode` | string | `regional-dr` | DR mode |
| `dr_clusters` | list(string) | `["dc-primary", "dr-secondary"]` | Cluster pair |
| `dr_action` | string | `none` | DR action |
| `dr_applications` | list(object) | See source | Protected applications |

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
dr_applications = [
  {
    name              = "sample-app"
    namespace         = "sample-app-ns"
    placement_name    = "sample-app-placement"
    preferred_cluster = "dc-primary"
    failover_cluster  = "dr-secondary"
    pvc_selector = {
      app = "sample-app"
    }
    kubeobject_protection = false
    s3_profile_name       = "s3-profile"
  },
]
```
