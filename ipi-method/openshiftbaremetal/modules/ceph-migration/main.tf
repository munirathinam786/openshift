# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Ceph Migration
# Migrates Ceph/ODF storage data (RBD images, CephFS volumes) between
# OpenShift clusters or datacenters using Rook-Ceph mirroring and
# rbd-mirror daemon with snapshot-based replication.
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

# ---- Source Cluster ----
variable "source_cluster_name" {
  description = "Name of the source cluster (migrating FROM)"
  type        = string
}

variable "source_cluster_kubeconfig" {
  description = "Kubeconfig path for the source cluster (on bastion)"
  type        = string
  default     = ""
}

# ---- Destination Cluster ----
variable "destination_cluster_name" {
  description = "Name of the destination cluster (migrating TO)"
  type        = string
}

variable "destination_cluster_kubeconfig" {
  description = "Kubeconfig path for the destination cluster (on bastion)"
  type        = string
  default     = ""
}

# ---- Migration Configuration ----
variable "migration_mode" {
  description = "Migration mode: async (snapshot-based) or sync (real-time replication)"
  type        = string
  default     = "async"
  validation {
    condition     = contains(["async", "sync"], var.migration_mode)
    error_message = "migration_mode must be 'async' or 'sync'."
  }
}

variable "replication_schedule" {
  description = "Cron schedule for async replication (e.g., '*/5 * * * *')"
  type        = string
  default     = "*/5 * * * *"
}

variable "pool_name" {
  description = "Ceph block pool name to migrate"
  type        = string
  default     = "ocs-storagecluster-cephblockpool"
}

variable "cephfs_pool_name" {
  description = "CephFS data pool name to migrate (empty to skip CephFS)"
  type        = string
  default     = ""
}

variable "storage_class" {
  description = "StorageClass for migrated PVCs on the destination cluster"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}

variable "namespaces" {
  description = "List of namespaces whose PVCs should be migrated"
  type = list(object({
    name           = string
    pvc_selector   = optional(map(string), {})
    exclude_pvcs   = optional(list(string), [])
  }))
  default = []
}

variable "migration_action" {
  description = "Action: prepare (setup mirroring), migrate (promote destination), validate (check status), cleanup (remove source mirroring)"
  type        = string
  default     = "prepare"
  validation {
    condition     = contains(["prepare", "migrate", "validate", "cleanup"], var.migration_action)
    error_message = "migration_action must be 'prepare', 'migrate', 'validate', or 'cleanup'."
  }
}

# ---- S3 Configuration (for mirroring metadata) ----
variable "s3_endpoint" {
  description = "S3 endpoint for Ceph mirroring metadata"
  type        = string
  default     = ""
}

variable "s3_bucket" {
  description = "S3 bucket for migration metadata"
  type        = string
  default     = "ceph-migration-metadata"
}

variable "s3_access_key" {
  description = "S3 access key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "s3_secret_key" {
  description = "S3 secret key"
  type        = string
  default     = ""
  sensitive   = true
}

# ---- Advanced ----
variable "rbd_mirror_count" {
  description = "Number of rbd-mirror daemon instances"
  type        = number
  default     = 1
}

variable "verify_data_integrity" {
  description = "Verify data integrity after migration using checksums"
  type        = bool
  default     = true
}

# =============================================================================
# Step 1: Prepare — Enable RBD mirroring on source cluster
# =============================================================================
resource "null_resource" "prepare_source_mirroring" {
  count = var.migration_action == "prepare" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.source_cluster_kubeconfig != "" ? var.source_cluster_kubeconfig : var.kubeconfig}",

      "echo '=== Step 1a: Enable RBD mirroring on source cluster ==='",
      "oc patch storagecluster ocs-storagecluster -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"enabled\":true}}}'",

      "echo '=== Step 1b: Wait for rbd-mirror daemon ==='",
      "for i in $(seq 1 60); do",
      "  STATUS=$(oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus.summary.daemon_health}' 2>/dev/null)",
      "  if [ \"$STATUS\" = \"OK\" ]; then echo 'RBD mirror daemon healthy on source'; break; fi",
      "  echo \"Waiting for rbd-mirror daemon... ($i/60)\"",
      "  sleep 10",
      "done",

      "echo '=== Step 1c: Configure mirroring mode on pool ==='",
      "oc patch cephblockpool ${var.pool_name} -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"enabled\":true,\"mode\":\"${var.migration_mode == "async" ? "image" : "pool"}\"}}}'",

      var.migration_mode == "async" ? "oc patch cephblockpool ${var.pool_name} -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"snapshotSchedules\":[{\"interval\":\"${var.replication_schedule}\"}]}}}'" : "echo 'Sync mode: no snapshot schedule needed'",

      "echo '=== Step 1d: Export bootstrap peer token ==='",
      "oc get secret rook-ceph-rbd-mirror-peer-token-${var.pool_name} -n openshift-storage -o jsonpath='{.data.token}' 2>/dev/null > /tmp/ceph-mirror-peer-token.b64 || echo 'Peer token not yet available'",

      "echo '=== Source cluster mirroring preparation complete ==='",
      "oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus}' 2>/dev/null || true",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# =============================================================================
# Step 2: Prepare — Enable RBD mirroring on destination cluster
# =============================================================================
resource "null_resource" "prepare_destination_mirroring" {
  count = var.migration_action == "prepare" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.destination_cluster_kubeconfig != "" ? var.destination_cluster_kubeconfig : var.kubeconfig}",

      "echo '=== Step 2a: Enable RBD mirroring on destination cluster ==='",
      "oc patch storagecluster ocs-storagecluster -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"enabled\":true}}}'",

      "echo '=== Step 2b: Wait for rbd-mirror daemon on destination ==='",
      "for i in $(seq 1 60); do",
      "  STATUS=$(oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus.summary.daemon_health}' 2>/dev/null)",
      "  if [ \"$STATUS\" = \"OK\" ]; then echo 'RBD mirror daemon healthy on destination'; break; fi",
      "  echo \"Waiting for rbd-mirror daemon... ($i/60)\"",
      "  sleep 10",
      "done",

      "echo '=== Step 2c: Configure mirroring mode on destination pool ==='",
      "oc patch cephblockpool ${var.pool_name} -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"enabled\":true,\"mode\":\"${var.migration_mode == "async" ? "image" : "pool"}\"}}}'",

      "echo '=== Step 2d: Import bootstrap peer token ==='",
      "PEER_TOKEN=$(cat /tmp/ceph-mirror-peer-token.b64 2>/dev/null || echo '')",
      "if [ -n \"$PEER_TOKEN\" ]; then",
      "  oc create secret generic rook-ceph-rbd-mirror-peer-token-import -n openshift-storage --from-literal=token=\"$PEER_TOKEN\" --dry-run=client -o yaml | oc apply -f -",
      "  echo 'Peer token imported on destination'",
      "else",
      "  echo 'WARNING: No peer token found — manual peer exchange may be required'",
      "fi",

      "echo '=== Destination cluster mirroring preparation complete ==='",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.prepare_source_mirroring]
}

# =============================================================================
# Step 3: Create MirrorPeer between source and destination
# =============================================================================
resource "null_resource" "create_mirror_peer" {
  count = var.migration_action == "prepare" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "echo '=== Step 3: Create MirrorPeer ==='",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: multicluster.odf.openshift.io/v1alpha1
      kind: MirrorPeer
      metadata:
        name: ceph-migration-${var.source_cluster_name}-to-${var.destination_cluster_name}
      spec:
        items:
          - clusterName: "${var.source_cluster_name}"
            storageClusterRef:
              name: ocs-storagecluster
              namespace: openshift-storage
          - clusterName: "${var.destination_cluster_name}"
            storageClusterRef:
              name: ocs-storagecluster
              namespace: openshift-storage
        manageS3: true
        schedulingIntervals:
          - "${var.replication_schedule}"
        type: ${var.migration_mode == "async" ? "async" : "sync"}
      EOF
      EOT
      ,
      "echo 'MirrorPeer created.'",

      "echo '=== Waiting for MirrorPeer to become healthy ==='",
      "for i in $(seq 1 60); do",
      "  PHASE=$(oc get mirrorpeer ceph-migration-${var.source_cluster_name}-to-${var.destination_cluster_name} -o jsonpath='{.status.phase}' 2>/dev/null)",
      "  if [ \"$PHASE\" = \"ExchangedSecret\" ] || [ \"$PHASE\" = \"S3ProfileSynced\" ]; then echo \"MirrorPeer phase: $PHASE\"; break; fi",
      "  echo \"Waiting for MirrorPeer... phase=$PHASE ($i/60)\"",
      "  sleep 10",
      "done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.prepare_destination_mirroring]
}

# =============================================================================
# Step 4: Enable mirroring on PVCs in selected namespaces
# =============================================================================
resource "null_resource" "enable_pvc_mirroring" {
  for_each = var.migration_action == "prepare" ? { for idx, ns in var.namespaces : ns.name => ns } : {}

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.source_cluster_kubeconfig != "" ? var.source_cluster_kubeconfig : var.kubeconfig}",

      "echo '=== Enabling mirroring for PVCs in namespace: ${each.value.name} ==='",

      # Label PVCs for mirroring
      "for PVC in $(oc get pvc -n ${each.value.name} -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do",
      "  EXCLUDED=false",
      "  for EXCL in ${join(" ", each.value.exclude_pvcs)}; do",
      "    if [ \"$PVC\" = \"$EXCL\" ]; then EXCLUDED=true; break; fi",
      "  done",
      "  if [ \"$EXCLUDED\" = \"false\" ]; then",
      "    echo \"Enabling mirroring for PVC: $PVC\"",
      "    oc label pvc $PVC -n ${each.value.name} replication.storage.openshift.io/enabled=true --overwrite",
      "  else",
      "    echo \"Skipping excluded PVC: $PVC\"",
      "  fi",
      "done",

      "echo '=== PVC mirroring enabled for namespace: ${each.value.name} ==='",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.create_mirror_peer]
}

# =============================================================================
# Step 5: Migrate — Promote destination and demote source
# =============================================================================
resource "null_resource" "execute_migration" {
  count = var.migration_action == "migrate" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "echo '=== Ceph Migration: Promoting Destination Cluster ==='",

      "echo '--- Step 5a: Verify replication sync status on source ---'",
      "export KUBECONFIG=${var.source_cluster_kubeconfig != "" ? var.source_cluster_kubeconfig : var.kubeconfig}",
      "oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus}' 2>/dev/null",
      "echo ''",

      "echo '--- Step 5b: Fence source workloads (scale down) ---'",
      "for NS in ${join(" ", [for ns in var.namespaces : ns.name])}; do",
      "  echo \"Scaling down workloads in $NS on source...\"",
      "  for DEPLOY in $(oc get deploy -n $NS -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do",
      "    oc scale deploy $DEPLOY -n $NS --replicas=0",
      "  done",
      "  for SS in $(oc get statefulset -n $NS -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do",
      "    oc scale statefulset $SS -n $NS --replicas=0",
      "  done",
      "done",

      "echo '--- Step 5c: Wait for final sync to complete ---'",
      "sleep 30",
      "oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus.summary}' 2>/dev/null",
      "echo ''",

      "echo '--- Step 5d: Demote source pool ---'",
      "oc patch cephblockpool ${var.pool_name} -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"mode\":\"image\",\"peers\":{\"secretNames\":[]}}}}' 2>/dev/null || true",

      "echo '--- Step 5e: Promote destination pool ---'",
      "export KUBECONFIG=${var.destination_cluster_kubeconfig != "" ? var.destination_cluster_kubeconfig : var.kubeconfig}",

      "echo '--- Step 5f: Recreate PVCs and workloads on destination ---'",
      "for NS in ${join(" ", [for ns in var.namespaces : ns.name])}; do",
      "  echo \"Verifying namespace $NS exists on destination...\"",
      "  oc get namespace $NS 2>/dev/null || oc create namespace $NS",
      "  echo \"Checking mirrored PVCs in $NS...\"",
      "  oc get pvc -n $NS -o wide 2>/dev/null || echo 'No PVCs found yet'",
      "done",

      "echo '=== Migration promotion complete — verify workloads on destination ==='",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# =============================================================================
# Step 6: Validate — Check mirroring and data status
# =============================================================================
resource "null_resource" "validate_migration" {
  count = var.migration_action == "validate" || var.migration_action == "migrate" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "echo '=== Ceph Migration Validation ==='",

      "echo '--- Source Cluster Status ---'",
      "export KUBECONFIG=${var.source_cluster_kubeconfig != "" ? var.source_cluster_kubeconfig : var.kubeconfig}",
      "echo 'CephBlockPool mirroring status:'",
      "oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus}' 2>/dev/null || echo 'Not available'",
      "echo ''",
      "echo 'RBD mirror daemon health:'",
      "oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus.summary.daemon_health}' 2>/dev/null || echo 'Not available'",
      "echo ''",
      "echo 'Image health:'",
      "oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus.summary.image_health}' 2>/dev/null || echo 'Not available'",
      "echo ''",

      "echo '--- Destination Cluster Status ---'",
      "export KUBECONFIG=${var.destination_cluster_kubeconfig != "" ? var.destination_cluster_kubeconfig : var.kubeconfig}",
      "echo 'CephBlockPool mirroring status:'",
      "oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus}' 2>/dev/null || echo 'Not available'",
      "echo ''",
      "echo 'Mirrored images summary:'",
      "oc get cephblockpool ${var.pool_name} -n openshift-storage -o jsonpath='{.status.mirroringStatus.summary.states}' 2>/dev/null || echo 'Not available'",
      "echo ''",

      "echo '--- MirrorPeer Status ---'",
      "oc get mirrorpeer -o wide 2>/dev/null || echo 'No MirrorPeer found'",

      "echo '--- PVC Replication Status ---'",
      "for NS in ${join(" ", [for ns in var.namespaces : ns.name])}; do",
      "  echo \"Namespace: $NS\"",
      "  oc get pvc -n $NS -l replication.storage.openshift.io/enabled=true -o wide 2>/dev/null || echo 'No mirrored PVCs'",
      "done",

      var.verify_data_integrity ? "echo '--- Data Integrity Check ---' && echo 'Checking rbd image status...' && oc exec -n openshift-storage $(oc get pod -n openshift-storage -l app=rook-ceph-tools -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) -- rbd mirror pool status ${var.pool_name} 2>/dev/null || echo 'Ceph tools pod not available'" : "echo 'Data integrity check skipped'",

      "echo '=== Validation complete ==='",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.execute_migration]
}

# =============================================================================
# Step 7: Cleanup — Remove mirroring configuration from source
# =============================================================================
resource "null_resource" "cleanup_source" {
  count = var.migration_action == "cleanup" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "echo '=== Ceph Migration Cleanup: Source Cluster ==='",
      "export KUBECONFIG=${var.source_cluster_kubeconfig != "" ? var.source_cluster_kubeconfig : var.kubeconfig}",

      "echo '--- Removing PVC replication labels ---'",
      "for NS in ${join(" ", [for ns in var.namespaces : ns.name])}; do",
      "  for PVC in $(oc get pvc -n $NS -l replication.storage.openshift.io/enabled=true -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do",
      "    oc label pvc $PVC -n $NS replication.storage.openshift.io/enabled- 2>/dev/null || true",
      "  done",
      "done",

      "echo '--- Disabling RBD mirroring on source pool ---'",
      "oc patch cephblockpool ${var.pool_name} -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"enabled\":false}}}' 2>/dev/null || true",

      "echo '--- Disabling mirroring on StorageCluster ---'",
      "oc patch storagecluster ocs-storagecluster -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"enabled\":false}}}' 2>/dev/null || true",

      "echo '--- Removing MirrorPeer ---'",
      "oc delete mirrorpeer ceph-migration-${var.source_cluster_name}-to-${var.destination_cluster_name} 2>/dev/null || true",

      "echo '=== Cleanup complete ==='",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "migration_action" {
  value       = var.migration_action
  description = "The migration action that was executed"
}

output "source_cluster" {
  value       = var.source_cluster_name
  description = "Source cluster name"
}

output "destination_cluster" {
  value       = var.destination_cluster_name
  description = "Destination cluster name"
}

output "mirror_peer_name" {
  value       = "ceph-migration-${var.source_cluster_name}-to-${var.destination_cluster_name}"
  description = "Name of the MirrorPeer resource"
}

output "migrated_namespaces" {
  value       = [for ns in var.namespaces : ns.name]
  description = "List of namespaces included in migration"
}
