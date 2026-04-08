# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Image Registry — Internal Registry Configuration
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "registry_storage_class" {
  description = "StorageClass for registry PVC"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}
variable "registry_storage_size" {
  description = "PVC size for internal registry"
  type        = string
  default     = "100Gi"
}
variable "registry_replicas" {
  description = "Number of registry replicas"
  type        = number
  default     = 2
}
variable "registry_pruning_enabled" {
  description = "Enable automatic image pruning"
  type        = bool
  default     = true
}
variable "registry_pruning_schedule" {
  description = "Cron schedule for image pruning"
  type        = string
  default     = "0 4 * * 0"
}
variable "registry_pruning_keep_tag_revisions" {
  description = "Number of tag revisions to keep"
  type        = number
  default     = 3
}

resource "null_resource" "image_registry_config" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create PVC for registry
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: PersistentVolumeClaim",
      "metadata:",
      "  name: image-registry-storage",
      "  namespace: openshift-image-registry",
      "spec:",
      "  accessModes:",
      "    - ReadWriteMany",
      "  storageClassName: ${var.registry_storage_class}",
      "  resources:",
      "    requests:",
      "      storage: ${var.registry_storage_size}",
      "EOF",

      # Patch the registry operator config
      "oc patch configs.imageregistry.operator.openshift.io cluster --type merge -p '{",
      "  \"spec\": {",
      "    \"managementState\": \"Managed\",",
      "    \"replicas\": ${var.registry_replicas},",
      "    \"storage\": {",
      "      \"pvc\": {",
      "        \"claim\": \"image-registry-storage\"",
      "      }",
      "    }",
      "  }",
      "}'",

      "echo 'Image registry configured with ${var.registry_storage_size} PVC'",
    ]
  }
}

# --- Image Pruning CronJob ---
resource "null_resource" "image_pruning" {
  count = var.registry_pruning_enabled ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: imageregistry.operator.openshift.io/v1",
      "kind: ImagePruner",
      "metadata:",
      "  name: cluster",
      "spec:",
      "  schedule: '${var.registry_pruning_schedule}'",
      "  suspend: false",
      "  keepTagRevisions: ${var.registry_pruning_keep_tag_revisions}",
      "  keepYoungerThanDuration: 72h",
      "  successfulJobsHistoryLimit: 3",
      "  failedJobsHistoryLimit: 3",
      "EOF",

      "echo 'Image pruning configured (schedule: ${var.registry_pruning_schedule})'",
    ]
  }

  depends_on = [null_resource.image_registry_config]
}
