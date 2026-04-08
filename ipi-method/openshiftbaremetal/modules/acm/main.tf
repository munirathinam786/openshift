# Author: Sathishkumar Munirathinam

# =============================================================================
# Red Hat Advanced Cluster Management (ACM) — Management Cluster
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

variable "acm_channel" {
  description = "ACM operator channel"
  type        = string
  default     = "release-2.11"
}

variable "acm_instance_name" {
  description = "MultiClusterHub instance name"
  type        = string
  default     = "multiclusterhub"
}

variable "enable_observability" {
  description = "Enable ACM Observability (requires ODF/S3)"
  type        = bool
  default     = false
}

variable "s3_bucket" {
  description = "S3 bucket name for observability (if enabled)"
  type        = string
  default     = ""
}

variable "s3_endpoint" {
  description = "S3 endpoint URL (e.g. ODF RGW or MinIO)"
  type        = string
  default     = ""
}

variable "s3_access_key" {
  description = "S3 access key for observability"
  type        = string
  default     = ""
  sensitive   = true
}

variable "s3_secret_key" {
  description = "S3 secret key for observability"
  type        = string
  default     = ""
  sensitive   = true
}

# --- Install ACM Operator ---
resource "null_resource" "acm_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: v1
      kind: Namespace
      metadata:
        name: open-cluster-management
        labels:
          openshift.io/cluster-monitoring: "true"
      EOF
      EOT
      ,
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operators.coreos.com/v1
      kind: OperatorGroup
      metadata:
        name: acm-operator-group
        namespace: open-cluster-management
      spec:
        targetNamespaces:
          - open-cluster-management
      EOF
      EOT
      ,
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operators.coreos.com/v1alpha1
      kind: Subscription
      metadata:
        name: advanced-cluster-management
        namespace: open-cluster-management
      spec:
        channel: ${var.acm_channel}
        installPlanApproval: Automatic
        name: advanced-cluster-management
        source: redhat-operators
        sourceNamespace: openshift-marketplace
      EOF
      EOT
      ,
      "echo 'Waiting for ACM Operator CSV...'",
      "for i in $(seq 1 90); do oc get csv -n open-cluster-management 2>/dev/null | grep -q Succeeded && break || sleep 10; done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Deploy MultiClusterHub CR ---
resource "null_resource" "multiclusterhub" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operator.open-cluster-management.io/v1
      kind: MultiClusterHub
      metadata:
        name: ${var.acm_instance_name}
        namespace: open-cluster-management
      spec:
        availabilityConfig: High
      EOF
      EOT
      ,
      "echo 'Waiting for MultiClusterHub to be Running...'",
      "for i in $(seq 1 120); do oc get multiclusterhub -n open-cluster-management ${var.acm_instance_name} -o jsonpath='{.status.phase}' 2>/dev/null | grep -q Running && break || sleep 15; done",
      "oc get multiclusterhub -n open-cluster-management ${var.acm_instance_name} -o jsonpath='{.status.phase}' || true",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.acm_operator]
}

# --- ACM Observability (optional) ---
resource "null_resource" "acm_observability" {
  count = var.enable_observability ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: v1
      kind: Namespace
      metadata:
        name: open-cluster-management-observability
      EOF
      EOT
      ,
      <<-EOT
      oc create secret generic thanos-object-storage \
        -n open-cluster-management-observability \
        --from-literal=thanos.yaml="$(cat <<YAML
      type: s3
      config:
        bucket: ${var.s3_bucket}
        endpoint: ${var.s3_endpoint}
        insecure: true
        access_key: ${var.s3_access_key}
        secret_key: ${var.s3_secret_key}
      YAML
      )" --dry-run=client -o yaml | oc apply -f -
      EOT
      ,
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: observability.open-cluster-management.io/v1beta2
      kind: MultiClusterObservability
      metadata:
        name: observability
      spec:
        observabilityAddonSpec: {}
        storageConfig:
          metricObjectStorage:
            name: thanos-object-storage
            key: thanos.yaml
          statefulSetSize: 10Gi
      EOF
      EOT
      ,
      "echo 'ACM Observability deployed.'",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.multiclusterhub]
}

output "acm_namespace" {
  value = "open-cluster-management"
}

output "acm_console_url" {
  value = "https://multicloud-console.apps.<cluster-domain>"
}
