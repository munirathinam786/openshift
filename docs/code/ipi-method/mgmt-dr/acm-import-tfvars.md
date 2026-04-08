# IPI Management DR — acm-import.tfvars

Configuration for importing workload clusters into the ACM Hub on the IPI Management DR cluster.
Identical to the Mgmt DC configuration — used when Mgmt DR is promoted to active ACM Hub.

!!! info "Usage"
    ```bash
    terraform apply -var-file=terraform.tfvars -var-file=acm-import.tfvars
    ```

## Variable Reference

| Variable | Type | Value | Description |
|----------|------|-------|-------------|
| `enable_acm_cluster_import` | bool | `true` | Enable the ACM cluster import module |
| `enable_acm_cluster_set` | bool | `true` | Create a ManagedClusterSet for grouping |
| `acm_cluster_set_name` | string | `ocp-workload-clusters` | Name of the ManagedClusterSet |
| `acm_auto_import_retry` | number | `2` | Number of auto-import retries |
| `acm_managed_clusters` | list(object) | See source | Clusters to import |
| `acm_import_scope` | string | `all-workload` | Pipeline scope override |

## Source Code

```hcl
# =============================================================================
# ACM Cluster Import — Variable Values (Management DC)
# Import workload clusters into ACM Hub for centralized management
# =============================================================================

# ---- Enable ACM Cluster Import ----
enable_acm_cluster_import = true
enable_acm_cluster_set    = true

# ---- ManagedClusterSet ----
acm_cluster_set_name = "ocp-workload-clusters"

# ---- Auto-Import Settings ----
acm_auto_import_retry = 2

# ---- Managed Clusters to Import ----
acm_managed_clusters = [
  {
    name            = "dc-primary"
    api_url         = "https://api.dc-primary.example.com:6443"
    kubeconfig_path = "/opt/ocp/dc-primary/auth/kubeconfig"
    cluster_labels = {
      environment  = "production"
      site         = "dc"
      role         = "workload"
      dr-role      = "primary"
      cluster-type = "baremetal"
    }
    klusterlet_addons = {
      application_manager = true
      policy_controller   = true
      search_collector    = true
      cert_policy         = true
      iam_policy          = true
    }
  },
  {
    name            = "dr-secondary"
    api_url         = "https://api.dr-secondary.example.com:6443"
    kubeconfig_path = "/opt/ocp/dr-secondary/auth/kubeconfig"
    cluster_labels = {
      environment  = "production"
      site         = "dr"
      role         = "workload"
      dr-role      = "secondary"
      cluster-type = "baremetal"
    }
    klusterlet_addons = {
      application_manager = true
      policy_controller   = true
      search_collector    = true
      cert_policy         = true
      iam_policy          = true
    }
  }
]

# ---- Pipeline Scope (overridden by pipeline parameter) ----
acm_import_scope = "all-workload"
```
