# =============================================================================
# MTC (Migration Toolkit for Containers) — IPI DC Primary
# Apply separately: terraform apply -var-file=terraform.tfvars -var-file=mtc.tfvars
# =============================================================================

# =============================================================================
# Feature Toggle
# =============================================================================
enable_mtc = true

# =============================================================================
# MTC Operator
# =============================================================================
mtc_channel               = "release-v1.8"
mtc_install_plan_approval = "Automatic"

# =============================================================================
# Source Cluster — Remote OpenShift Cluster to Migrate FROM
# =============================================================================
# Name for the source cluster in MTC
mtc_source_cluster_name = "source-ocp-cluster"

# API URL of the source cluster
mtc_source_cluster_url = "https://api.source-cluster.example.com:6443"

# Service account token from the source cluster
# Generate: oc sa get-token migration-controller -n openshift-migration
mtc_source_cluster_sa_token = "REPLACE_SOURCE_SA_TOKEN"           # Override via ADO Variable Group

# Skip TLS verification for source cluster API (NOT recommended for production)
mtc_source_cluster_insecure = false

# CA bundle for the source cluster API (PEM file path on bastion)
mtc_source_cluster_ca_bundle = ""

# Internal image registry URL on source cluster (for image migration)
mtc_source_cluster_registry = "image-registry.openshift-image-registry.svc:5000"

# Exposed migration controller route on source cluster (for direct volume migration)
# Get: oc get route -n openshift-migration
mtc_source_cluster_exposed_route = ""

# =============================================================================
# Destination Cluster
# =============================================================================
# "host" means the local cluster where MTC is installed
mtc_destination_cluster_name = "host"

# API URL (empty = auto-detect for host cluster)
mtc_destination_cluster_url = ""

# SA token (empty = auto-detect for host cluster)
mtc_destination_cluster_sa_token = ""

# =============================================================================
# Replication Repository — S3/Minio Storage for Migration Data
# =============================================================================
mtc_replication_repository_name = "migration-s3-repo"
mtc_replication_repository_type = "s3"

# S3-compatible endpoint URL
# For AWS S3:     https://s3.amazonaws.com
# For MinIO:      https://minio.example.com:9000
# For ODF MCG:    https://s3-openshift-storage.apps.cluster.example.com
mtc_replication_repository_url = "https://minio.example.com:9000"

# S3 bucket name (must exist before migration)
mtc_replication_repository_bucket = "mtc-migration-data"

# S3 region
mtc_replication_repository_region = "us-east-1"

# S3 credentials — override via ADO Variable Group
mtc_replication_repository_access_key = "REPLACE_S3_ACCESS_KEY"
mtc_replication_repository_secret_key = "REPLACE_S3_SECRET_KEY"

# Use HTTP instead of HTTPS for S3 endpoint
mtc_replication_repository_insecure = false

# CA bundle for the S3 endpoint (PEM file path on bastion)
mtc_replication_repository_ca_bundle = ""

# =============================================================================
# Migration Plan
# =============================================================================
mtc_migration_plan_name = "workload-migration-dc"

# =============================================================================
# Namespaces to Migrate
# =============================================================================
# List of namespaces with optional destination namespace mapping
mtc_migration_plan_namespaces = [
  # {
  #   source_namespace      = "production-app"
  #   destination_namespace = "production-app"       # empty = same name
  #   annotations           = {}
  # },
  # {
  #   source_namespace      = "staging-app"
  #   destination_namespace = "staging-app"
  #   annotations           = { "migration-wave" = "2" }
  # },
  # {
  #   source_namespace      = "monitoring"
  #   destination_namespace = "monitoring"
  #   annotations           = {}
  # },
]

# =============================================================================
# Migration Type
# =============================================================================
# "stage"    — Copy data without quiescing pods or cutting over (incremental, repeatable)
# "final"    — Full migration with quiesce + cutover
# "rollback" — Rollback a completed migration
mtc_migration_type = "final"

# =============================================================================
# PV (Persistent Volume) Migration
# =============================================================================
# Copy method: "filesystem" (Restic) or "snapshot" (CSI VolumeSnapshot)
mtc_pv_copy_method = "filesystem"

# Verify data integrity after PV copy
mtc_pv_verify = true

# Map source PV storage classes to destination storage classes
mtc_pv_storage_class_mapping = [
  # {
  #   source_storage_class      = "glusterfs-storage"
  #   destination_storage_class = "ocs-storagecluster-ceph-rbd"
  # },
  # {
  #   source_storage_class      = "thin"                        # vSphere CSI
  #   destination_storage_class = "ocs-storagecluster-ceph-rbd"
  # },
]

# Map source PV access modes to destination access modes
mtc_pv_access_mode_mapping = [
  # {
  #   source_access_mode      = "ReadWriteOnce"
  #   destination_access_mode = "ReadWriteOnce"
  # },
]

# =============================================================================
# Direct Migration (faster — bypasses replication repository)
# =============================================================================
# Direct Volume Migration (DVM) — transfers PV data directly between clusters
mtc_enable_direct_volume_migration = true

# Direct Image Migration (DIM) — transfers images directly between registries
mtc_enable_direct_image_migration = true

# =============================================================================
# Migration Options
# =============================================================================
# Quiesce (scale down to 0) source pods during final migration
mtc_quiesce_pods = true

# Preserve annotations on migrated Kubernetes resources
mtc_keep_annotations = true

# Preserve NodePort values in migrated Services
mtc_preserve_node_ports = false

# =============================================================================
# Resource Exclusions
# =============================================================================
# Kubernetes resource types to exclude from migration
mtc_excluded_resources = [
  # "imagestreams",
  # "templateinstances",
  # "clusterserviceversions",
]

# =============================================================================
# Label Selector
# =============================================================================
# Migrate only resources matching this label (empty = all resources in namespace)
mtc_label_selector = ""

# =============================================================================
# Pre/Post Migration Hooks
# =============================================================================
mtc_migration_hooks = [
  # {
  #   name            = "pre-migration-db-backup"
  #   namespace       = "openshift-migration"
  #   phase           = "PreBackup"               # PreBackup, PostBackup, PreRestore, PostRestore
  #   playbook_path   = "/home/kni/playbooks/db-backup.yml"
  #   custom_image    = ""
  #   service_account = "migration-controller"
  # },
  # {
  #   name            = "post-migration-validation"
  #   namespace       = "openshift-migration"
  #   phase           = "PostRestore"
  #   playbook_path   = "/home/kni/playbooks/validate-app.yml"
  #   custom_image    = ""
  #   service_account = "migration-controller"
  # },
]
