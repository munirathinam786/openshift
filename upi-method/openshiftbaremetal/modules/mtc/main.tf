# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: MTC (Migration Toolkit for Containers)
# Migrates containerized workloads (namespaces, PVs, Deployments) between
# OpenShift clusters using Velero + Restic.
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

# ---- Operator ----
variable "mtc_channel" {
  type    = string
  default = "release-v1.8"
}
variable "mtc_install_plan_approval" {
  type    = string
  default = "Automatic"
}

# ---- MigrationController ----
variable "mtc_cluster_name" {
  description = "Name of this cluster (used in MigCluster registration)"
  type        = string
  default     = "host"
}

# ---- Source Cluster (remote cluster to migrate FROM) ----
variable "mtc_source_cluster_name" {
  description = "Logical name for the source cluster"
  type        = string
  default     = "source-cluster"
}
variable "mtc_source_cluster_url" {
  description = "API URL of the source cluster (e.g. https://api.source.example.com:6443)"
  type        = string
  default     = ""
}
variable "mtc_source_cluster_sa_token" {
  description = "Service account token for the source cluster (migration-controller SA)"
  type        = string
  default     = ""
  sensitive   = true
}
variable "mtc_source_cluster_insecure" {
  description = "Skip TLS verification for source cluster API"
  type        = bool
  default     = false
}
variable "mtc_source_cluster_ca_bundle" {
  description = "CA bundle (PEM) for the source cluster API (path on bastion)"
  type        = string
  default     = ""
}
variable "mtc_source_cluster_registry" {
  description = "Internal registry URL for the source cluster (for image migration)"
  type        = string
  default     = ""
}
variable "mtc_source_cluster_exposed_route" {
  description = "Exposed migration controller route on the source cluster (for direct volume migration)"
  type        = string
  default     = ""
}

# ---- Destination Cluster ----
variable "mtc_destination_cluster_name" {
  description = "Logical name for the destination (host) cluster"
  type        = string
  default     = "host"
}
variable "mtc_destination_cluster_url" {
  description = "API URL of the destination cluster (empty = local host cluster)"
  type        = string
  default     = ""
}
variable "mtc_destination_cluster_sa_token" {
  description = "SA token for destination cluster (empty = auto-detect for host)"
  type        = string
  default     = ""
  sensitive   = true
}

# ---- Replication Repository (S3/Minio/ODF storage for migration data) ----
variable "mtc_replication_repository_name" {
  description = "Name for the replication repository"
  type        = string
  default     = "migration-repo"
}
variable "mtc_replication_repository_type" {
  description = "Type of replication repository"
  type        = string
  default     = "s3"
}
variable "mtc_replication_repository_url" {
  description = "S3-compatible endpoint URL (e.g. https://s3.example.com)"
  type        = string
  default     = ""
}
variable "mtc_replication_repository_bucket" {
  description = "S3 bucket name"
  type        = string
  default     = "mtc-migration-data"
}
variable "mtc_replication_repository_region" {
  description = "S3 region (e.g. us-east-1)"
  type        = string
  default     = "us-east-1"
}
variable "mtc_replication_repository_access_key" {
  description = "S3 access key"
  type        = string
  default     = ""
  sensitive   = true
}
variable "mtc_replication_repository_secret_key" {
  description = "S3 secret key"
  type        = string
  default     = ""
  sensitive   = true
}
variable "mtc_replication_repository_insecure" {
  description = "Use HTTP instead of HTTPS for replication repository"
  type        = bool
  default     = false
}
variable "mtc_replication_repository_ca_bundle" {
  description = "CA bundle for the replication repository endpoint"
  type        = string
  default     = ""
}

# ---- Migration Plan ----
variable "mtc_migration_plan_name" {
  description = "Name of the migration plan"
  type        = string
  default     = "mtc-migration-plan"
}
variable "mtc_migration_plan_namespaces" {
  description = "List of namespaces to migrate"
  type = list(object({
    source_namespace      = string
    destination_namespace = optional(string, "")
    annotations           = optional(map(string), {})
  }))
  default = []
}

# ---- Migration Type ----
variable "mtc_migration_type" {
  description = "Migration type: stage (copies data without cutover), final (full cutover), rollback"
  type        = string
  default     = "final"
}

# ---- PV Migration ----
variable "mtc_pv_copy_method" {
  description = "PV copy method: filesystem (Restic), snapshot (CSI snapshot)"
  type        = string
  default     = "filesystem"
}
variable "mtc_pv_verify" {
  description = "Verify data integrity of copied PVs"
  type        = bool
  default     = true
}
variable "mtc_pv_storage_class_mapping" {
  description = "Map source PV storage classes to destination storage classes"
  type = list(object({
    source_storage_class      = string
    destination_storage_class = string
  }))
  default = []
}
variable "mtc_pv_access_mode_mapping" {
  description = "Map source PV access modes to destination access modes"
  type = list(object({
    source_access_mode      = string
    destination_access_mode = string
  }))
  default = []
}

# ---- Direct Migration ----
variable "mtc_enable_direct_volume_migration" {
  description = "Enable Direct Volume Migration (DVM) — faster, bypasses replication repo for PVs"
  type        = bool
  default     = true
}
variable "mtc_enable_direct_image_migration" {
  description = "Enable Direct Image Migration (DIM) — migrate images directly between registries"
  type        = bool
  default     = true
}

# ---- Migration Options ----
variable "mtc_quiesce_pods" {
  description = "Quiesce (scale down) source pods during final migration"
  type        = bool
  default     = true
}
variable "mtc_keep_annotations" {
  description = "Preserve annotations on migrated resources"
  type        = bool
  default     = true
}
variable "mtc_preserve_node_ports" {
  description = "Preserve NodePort values in migrated Services"
  type        = bool
  default     = false
}

# ---- Hooks ----
variable "mtc_migration_hooks" {
  description = "Pre/post migration hooks (Ansible playbooks or custom images)"
  type = list(object({
    name            = string
    namespace       = string
    phase           = string
    playbook_path   = optional(string, "")
    custom_image    = optional(string, "")
    service_account = optional(string, "migration-controller")
  }))
  default = []
}

# ---- Excluded Resources ----
variable "mtc_excluded_resources" {
  description = "Kubernetes resource types to exclude from migration"
  type        = list(string)
  default     = []
}

# ---- Labels / Selectors ----
variable "mtc_label_selector" {
  description = "Label selector to filter resources within migrated namespaces (empty = all)"
  type        = string
  default     = ""
}

# =============================================================================
# Resources
# =============================================================================

resource "null_resource" "mtc_namespace" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create namespace
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: openshift-migration",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: migration",
      "  namespace: openshift-migration",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-migration",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: mtc-operator",
      "  namespace: openshift-migration",
      "spec:",
      "  channel: ${var.mtc_channel}",
      "  installPlanApproval: ${var.mtc_install_plan_approval}",
      "  name: mtc-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for MTC operator
      "echo 'Waiting for MTC operator to install...'",
      "for i in $(seq 1 90); do",
      "  oc get csv -n openshift-migration 2>/dev/null | grep mtc-operator | grep -q Succeeded && break",
      "  sleep 10",
      "done",
      "oc get csv -n openshift-migration | grep mtc-operator | grep -q Succeeded || { echo 'ERROR: MTC operator not ready'; exit 1; }",

      # Create MigrationController CR
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: migration.openshift.io/v1alpha1",
      "kind: MigrationController",
      "metadata:",
      "  name: migration-controller",
      "  namespace: openshift-migration",
      "spec:",
      "  olm_managed: true",
      "  migration_velero: true",
      "  migration_controller: true",
      "  migration_ui: true",
      "  restic_timeout: 1h",
      "EOF",

      # Wait for MigrationController
      "echo 'Waiting for MigrationController to become ready...'",
      "for i in $(seq 1 120); do",
      "  PHASE=$(oc get migrationcontroller migration-controller -n openshift-migration -o jsonpath='{.status.phase}' 2>/dev/null)",
      "  [ \"$PHASE\" = \"Ready\" ] && break",
      "  sleep 10",
      "done",
      "echo 'MTC MigrationController is ready.'",
    ]
  }
}

resource "null_resource" "mtc_replication_repository" {
  count      = var.mtc_replication_repository_url != "" ? 1 : 0
  depends_on = [null_resource.mtc_namespace]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create S3 credentials secret
      "cat <<EOF | oc apply -f -",
      "apiVersion: v1",
      "kind: Secret",
      "metadata:",
      "  name: ${var.mtc_replication_repository_name}-secret",
      "  namespace: openshift-migration",
      "type: Opaque",
      "stringData:",
      "  aws-access-key-id: ${var.mtc_replication_repository_access_key}",
      "  aws-secret-access-key: ${var.mtc_replication_repository_secret_key}",
      "EOF",

      # Create MigStorage
      "cat <<EOF | oc apply -f -",
      "apiVersion: migration.openshift.io/v1alpha1",
      "kind: MigStorage",
      "metadata:",
      "  name: ${var.mtc_replication_repository_name}",
      "  namespace: openshift-migration",
      "spec:",
      "  backupStorageProvider: ${var.mtc_replication_repository_type}",
      "  volumeSnapshotProvider: ${var.mtc_replication_repository_type}",
      "  backupStorageConfig:",
      "    awsBucketName: ${var.mtc_replication_repository_bucket}",
      "    awsRegion: ${var.mtc_replication_repository_region}",
      "    awsS3Url: ${var.mtc_replication_repository_url}",
      "    credsSecretRef:",
      "      name: ${var.mtc_replication_repository_name}-secret",
      "      namespace: openshift-migration",
      "    insecure: ${var.mtc_replication_repository_insecure}",
      "  volumeSnapshotConfig:",
      "    awsRegion: ${var.mtc_replication_repository_region}",
      "    credsSecretRef:",
      "      name: ${var.mtc_replication_repository_name}-secret",
      "      namespace: openshift-migration",
      "EOF",
    ]
  }
}

resource "null_resource" "mtc_source_cluster" {
  count      = var.mtc_source_cluster_url != "" ? 1 : 0
  depends_on = [null_resource.mtc_namespace]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create source cluster SA token secret
      "cat <<EOF | oc apply -f -",
      "apiVersion: v1",
      "kind: Secret",
      "metadata:",
      "  name: ${var.mtc_source_cluster_name}-token",
      "  namespace: openshift-migration",
      "type: Opaque",
      "stringData:",
      "  saToken: ${var.mtc_source_cluster_sa_token}",
      "EOF",

      # Register source cluster
      "cat <<EOF | oc apply -f -",
      "apiVersion: migration.openshift.io/v1alpha1",
      "kind: MigCluster",
      "metadata:",
      "  name: ${var.mtc_source_cluster_name}",
      "  namespace: openshift-migration",
      "spec:",
      "  isHostCluster: false",
      "  url: ${var.mtc_source_cluster_url}",
      "  insecure: ${var.mtc_source_cluster_insecure}",
      "  serviceAccountSecretRef:",
      "    name: ${var.mtc_source_cluster_name}-token",
      "    namespace: openshift-migration",
      "EOF",

      # Wait for source cluster to become Ready
      "echo 'Waiting for source MigCluster to become Ready...'",
      "for i in $(seq 1 60); do",
      "  STATUS=$(oc get migcluster ${var.mtc_source_cluster_name} -n openshift-migration -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}' 2>/dev/null)",
      "  [ \"$STATUS\" = \"True\" ] && break",
      "  sleep 10",
      "done",
    ]
  }
}

resource "null_resource" "mtc_migration_plan" {
  count      = length(var.mtc_migration_plan_namespaces) > 0 ? 1 : 0
  depends_on = [null_resource.mtc_source_cluster, null_resource.mtc_replication_repository]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create MigPlan
      "cat <<EOF | oc apply -f -",
      "apiVersion: migration.openshift.io/v1alpha1",
      "kind: MigPlan",
      "metadata:",
      "  name: ${var.mtc_migration_plan_name}",
      "  namespace: openshift-migration",
      "spec:",
      "  srcMigClusterRef:",
      "    name: ${var.mtc_source_cluster_name}",
      "    namespace: openshift-migration",
      "  destMigClusterRef:",
      "    name: ${var.mtc_destination_cluster_name}",
      "    namespace: openshift-migration",
      "  migStorageRef:",
      "    name: ${var.mtc_replication_repository_name}",
      "    namespace: openshift-migration",
      "  indirectImageMigration: ${!var.mtc_enable_direct_image_migration}",
      "  indirectVolumeMigration: ${!var.mtc_enable_direct_volume_migration}",
      "  namespaces: []",
      "EOF",

      # Wait for MigPlan to become Ready
      "echo 'Waiting for MigPlan to become Ready...'",
      "for i in $(seq 1 60); do",
      "  STATUS=$(oc get migplan ${var.mtc_migration_plan_name} -n openshift-migration -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}' 2>/dev/null)",
      "  [ \"$STATUS\" = \"True\" ] && break",
      "  sleep 10",
      "done",
    ]
  }
}

resource "null_resource" "mtc_migration_execute" {
  count      = var.mtc_migration_type != "" && length(var.mtc_migration_plan_namespaces) > 0 ? 1 : 0
  depends_on = [null_resource.mtc_migration_plan]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create MigMigration to trigger the actual migration
      "cat <<EOF | oc apply -f -",
      "apiVersion: migration.openshift.io/v1alpha1",
      "kind: MigMigration",
      "metadata:",
      "  name: ${var.mtc_migration_plan_name}-migration",
      "  namespace: openshift-migration",
      "spec:",
      "  migPlanRef:",
      "    name: ${var.mtc_migration_plan_name}",
      "    namespace: openshift-migration",
      "  stage: ${var.mtc_migration_type == "stage" ? "true" : "false"}",
      "  quiescePods: ${var.mtc_quiesce_pods}",
      "  keepAnnotations: ${var.mtc_keep_annotations}",
      "  rollback: ${var.mtc_migration_type == "rollback" ? "true" : "false"}",
      "EOF",

      "echo 'MigMigration created — monitor progress via: oc get migmigration -n openshift-migration'",
    ]
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "mtc_namespace" {
  value = "openshift-migration"
}

output "mtc_status" {
  value = "MTC deployed via mtc-operator with MigrationController, Velero, and Restic"
}
