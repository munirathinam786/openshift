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
