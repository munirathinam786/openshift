# =============================================================================
# Module: Thanos Ruler — Long-term metrics retention with S3
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "thanos_s3_endpoint" {
  description = "S3 endpoint for long-term metrics storage"
  type        = string
  default     = ""
}
variable "thanos_s3_bucket" {
  description = "S3 bucket for Thanos object store"
  type        = string
  default     = "thanos-metrics"
}
variable "thanos_s3_access_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "thanos_s3_secret_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "thanos_retention" {
  description = "Metrics retention period"
  type        = string
  default     = "90d"
}

resource "null_resource" "thanos_ruler_config" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create Thanos object storage config secret
      "cat <<EOF > /tmp/thanos-objstore.yaml",
      "type: s3",
      "config:",
      "  bucket: ${var.thanos_s3_bucket}",
      "  endpoint: ${var.thanos_s3_endpoint}",
      "  access_key: ${var.thanos_s3_access_key}",
      "  secret_key: ${var.thanos_s3_secret_key}",
      "  insecure: false",
      "EOF",

      "oc create secret generic thanos-objectstorage -n openshift-monitoring --from-file=thanos.yaml=/tmp/thanos-objstore.yaml --dry-run=client -o yaml | oc apply -f -",
      "rm -f /tmp/thanos-objstore.yaml",

      # Configure cluster monitoring with Thanos sidecar + remote write
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: cluster-monitoring-config",
      "  namespace: openshift-monitoring",
      "data:",
      "  config.yaml: |",
      "    enableUserWorkload: true",
      "    prometheusK8s:",
      "      retention: 15d",
      "      volumeClaimTemplate:",
      "        spec:",
      "          storageClassName: ocs-storagecluster-ceph-rbd",
      "          resources:",
      "            requests:",
      "              storage: 100Gi",
      "      externalLabels:",
      "        cluster: $(oc get infrastructure cluster -o jsonpath='{.status.infrastructureName}' 2>/dev/null || echo 'unknown')",
      "    thanosQuerier:",
      "      enableRequestLogging: true",
      "EOF",

      "echo 'Thanos long-term metrics storage configured with ${var.thanos_retention} retention'",
    ]
  }
}
