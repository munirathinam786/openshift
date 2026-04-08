# =============================================================================
# Module: Loki Logging — LokiStack-based log aggregation
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "loki_storage_class" {
  description = "StorageClass for Loki PVCs"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}
variable "loki_storage_size" {
  description = "Storage size for each Loki component"
  type        = string
  default     = "50Gi"
}
variable "loki_size" {
  description = "LokiStack size (1x.demo, 1x.extra-small, 1x.small, 1x.medium)"
  type        = string
  default     = "1x.extra-small"
}
variable "loki_s3_endpoint" {
  description = "S3 endpoint for object storage backend"
  type        = string
  default     = ""
}
variable "loki_s3_bucket" {
  description = "S3 bucket name"
  type        = string
  default     = "loki-logs"
}
variable "loki_s3_access_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "loki_s3_secret_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "loki_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

resource "null_resource" "loki_operator" {
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
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: openshift-logging",
      "  labels:",
      "    openshift.io/cluster-monitoring: 'true'",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: loki-operator",
      "  namespace: openshift-operators-redhat",
      "spec:",
      "  channel: stable-6.1",
      "  installPlanApproval: Automatic",
      "  name: loki-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for Loki Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-operators-redhat 2>/dev/null | grep loki | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create S3 secret
      "cat <<EOF | oc apply -f -",
      "apiVersion: v1",
      "kind: Secret",
      "metadata:",
      "  name: loki-s3-secret",
      "  namespace: openshift-logging",
      "type: Opaque",
      "stringData:",
      "  endpoint: ${var.loki_s3_endpoint}",
      "  bucketnames: ${var.loki_s3_bucket}",
      "  access_key_id: ${var.loki_s3_access_key}",
      "  access_key_secret: ${var.loki_s3_secret_key}",
      "EOF",

      # Create LokiStack
      "cat <<EOF | oc apply -f -",
      "apiVersion: loki.grafana.com/v1",
      "kind: LokiStack",
      "metadata:",
      "  name: logging-loki",
      "  namespace: openshift-logging",
      "spec:",
      "  size: ${var.loki_size}",
      "  storage:",
      "    schemas:",
      "      - version: v13",
      "        effectiveDate: '2024-10-01'",
      "    secret:",
      "      name: loki-s3-secret",
      "      type: s3",
      "  storageClassName: ${var.loki_storage_class}",
      "  limits:",
      "    global:",
      "      retention:",
      "        days: ${var.loki_retention_days}",
      "  tenants:",
      "    mode: openshift-logging",
      "EOF",

      "echo 'LokiStack deployed'",
    ]
  }
}
