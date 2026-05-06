# Author: Sathishkumar Munirathinam

# =============================================================================
# MTC (Migration Toolkit for Containers) — UPI DR Secondary
# Apply separately: terraform apply -var-file=terraform.tfvars -var-file=mtc.tfvars
# =============================================================================

enable_mtc = true

# =============================================================================
# MTC Operator
# =============================================================================
mtc_channel               = "release-v1.10"
mtc_install_plan_approval = "Automatic"

# =============================================================================
# Source Cluster
# =============================================================================
mtc_source_cluster_name          = "source-ocp-cluster-dr"
mtc_source_cluster_url           = "https://api.source-cluster-dr.example.com:6443"
mtc_source_cluster_sa_token      = "REPLACE_SOURCE_SA_TOKEN"
mtc_source_cluster_insecure      = false
mtc_source_cluster_ca_bundle     = ""
mtc_source_cluster_registry      = "image-registry.openshift-image-registry.svc:5000"
mtc_source_cluster_exposed_route = ""

# =============================================================================
# Destination Cluster
# =============================================================================
mtc_destination_cluster_name     = "host"
mtc_destination_cluster_url      = ""
mtc_destination_cluster_sa_token = ""

# =============================================================================
# Replication Repository
# =============================================================================
mtc_replication_repository_name       = "migration-s3-repo"
mtc_replication_repository_type       = "s3"
mtc_replication_repository_url        = "https://minio-dr.example.com:9000"
mtc_replication_repository_bucket     = "mtc-migration-data-dr"
mtc_replication_repository_region     = "us-east-1"
mtc_replication_repository_access_key = "REPLACE_S3_ACCESS_KEY"
mtc_replication_repository_secret_key = "REPLACE_S3_SECRET_KEY"
mtc_replication_repository_insecure   = false
mtc_replication_repository_ca_bundle  = ""

# =============================================================================
# Migration Plan
# =============================================================================
mtc_migration_plan_name = "workload-migration-upi-dr"

mtc_migration_plan_namespaces = []

# =============================================================================
# Migration Options
# =============================================================================
mtc_migration_type                  = "final"
mtc_pv_copy_method                  = "filesystem"
mtc_pv_verify                       = true
mtc_pv_storage_class_mapping        = []
mtc_pv_access_mode_mapping          = []
mtc_enable_direct_volume_migration  = true
mtc_enable_direct_image_migration   = true
mtc_quiesce_pods                    = true
mtc_keep_annotations                = true
mtc_preserve_node_ports             = false
mtc_excluded_resources              = []
mtc_label_selector                  = ""
mtc_migration_hooks                 = []
