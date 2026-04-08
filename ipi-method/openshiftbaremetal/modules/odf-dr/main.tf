# =============================================================================
# ODF Disaster Recovery — Regional-DR / Metro-DR Replication
# Configures ODF mirroring between DC and DR clusters via Submariner
# =============================================================================

variable "kubeconfig" {
  type = string
}

variable "bastion_host" {
  type = string
}

variable "bastion_user" {
  type = string
}

variable "bastion_ssh_key" {
  type = string
}

variable "dr_mode" {
  description = "DR mode: regional-dr (async) or metro-dr (sync)"
  type        = string
  default     = "regional-dr"
  validation {
    condition     = contains(["regional-dr", "metro-dr"], var.dr_mode)
    error_message = "dr_mode must be 'regional-dr' or 'metro-dr'."
  }
}

variable "replication_schedule" {
  description = "Cron schedule for async mirroring (regional-dr only, e.g. '*/5 * * * *')"
  type        = string
  default     = "*/5 * * * *"
}

variable "peer_cluster_name" {
  description = "Name of the peer cluster for mirroring"
  type        = string
}

variable "s3_profile_name" {
  description = "S3 profile name for Rook-Ceph RBD mirroring"
  type        = string
  default     = "s3-profile"
}

variable "s3_endpoint" {
  description = "S3 endpoint for mirroring metadata (ODF RGW)"
  type        = string
  default     = ""
}

variable "s3_bucket" {
  description = "S3 bucket for DR metadata"
  type        = string
  default     = "odf-dr-metadata"
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

# --- Install ODF DR Operator (odr-hub-operator for hub; odr-cluster-operator for spoke) ---
resource "null_resource" "odf_dr_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operators.coreos.com/v1alpha1
      kind: Subscription
      metadata:
        name: odr-cluster-operator
        namespace: openshift-operators
      spec:
        channel: stable-4.16
        installPlanApproval: Automatic
        name: odr-cluster-operator
        source: redhat-operators
        sourceNamespace: openshift-marketplace
      EOF
      EOT
      ,
      "echo 'Waiting for ODF DR Operator CSV...'",
      "for i in $(seq 1 60); do oc get csv -n openshift-operators 2>/dev/null | grep odr-cluster-operator | grep -q Succeeded && break || sleep 10; done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Enable Ceph RBD Mirroring on the StorageCluster ---
resource "null_resource" "enable_rbd_mirroring" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "oc patch storagecluster ocs-storagecluster -n openshift-storage --type=merge -p '{\"spec\":{\"mirroring\":{\"enabled\":true}}}'",
      "echo 'Waiting for RBD mirroring daemon to start...'",
      "for i in $(seq 1 60); do oc get cephblockpool -n openshift-storage ocs-storagecluster-cephblockpool -o jsonpath='{.status.mirroringStatus.summary.daemon_health}' 2>/dev/null | grep -q OK && break || sleep 10; done",
      "oc get cephblockpool -n openshift-storage ocs-storagecluster-cephblockpool -o jsonpath='{.status.mirroringStatus}' 2>/dev/null || true",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.odf_dr_operator]
}

# --- Create S3 secret for DR metadata store ---
resource "null_resource" "odf_dr_s3_secret" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      oc create secret generic ${var.s3_profile_name}-secret \
        -n openshift-dr-system \
        --from-literal=AWS_ACCESS_KEY_ID="${var.s3_access_key}" \
        --from-literal=AWS_SECRET_ACCESS_KEY="${var.s3_secret_key}" \
        --dry-run=client -o yaml | oc apply -f -
      EOT
      ,
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.odf_dr_operator]
}

# --- Create MirrorPeer (connects two ODF clusters) ---
resource "null_resource" "mirror_peer" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: multicluster.odf.openshift.io/v1alpha1
      kind: MirrorPeer
      metadata:
        name: mirrorpeer-${var.peer_cluster_name}
      spec:
        items:
          - clusterName: "${var.peer_cluster_name}"
            storageClusterRef:
              name: ocs-storagecluster
              namespace: openshift-storage
        manageS3: true
        schedulingIntervals:
          - "${var.replication_schedule}"
        type: ${var.dr_mode == "regional-dr" ? "async" : "sync"}
      EOF
      EOT
      ,
      "echo 'MirrorPeer created.'",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.enable_rbd_mirroring, null_resource.odf_dr_s3_secret]
}

output "dr_mode" {
  value = var.dr_mode
}

output "mirror_peer_name" {
  value = "mirrorpeer-${var.peer_cluster_name}"
}
