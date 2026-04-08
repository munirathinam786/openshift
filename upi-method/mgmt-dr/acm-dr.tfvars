# =============================================================================
# ACM DR Applications — Variable Values (Management DR — Standby Hub)
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
