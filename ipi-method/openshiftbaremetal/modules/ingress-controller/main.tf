# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Ingress Controller — Custom Certs, Sharding, Tuning
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "ingress_default_cert_name" {
  description = "Name of the TLS secret for default ingress cert"
  type        = string
  default     = ""
}
variable "ingress_hsts_max_age" {
  description = "HSTS max-age in seconds (0 to disable)"
  type        = number
  default     = 0
}
variable "ingress_replicas" {
  description = "Number of ingress controller replicas"
  type        = number
  default     = 2
}
variable "ingress_thread_count" {
  description = "HAProxy thread count per ingress pod"
  type        = number
  default     = 4
}
variable "ingress_timeout_client" {
  description = "Client timeout (e.g., 30s)"
  type        = string
  default     = "30s"
}
variable "ingress_timeout_server" {
  description = "Server/backend timeout (e.g., 30s)"
  type        = string
  default     = "30s"
}
variable "ingress_max_connections" {
  description = "Maximum number of connections per ingress pod"
  type        = number
  default     = 50000
}

resource "null_resource" "ingress_controller_config" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Patch default IngressController
      "cat <<EOF | oc apply -f -",
      "apiVersion: operator.openshift.io/v1",
      "kind: IngressController",
      "metadata:",
      "  name: default",
      "  namespace: openshift-ingress-operator",
      "spec:",
      "  replicas: ${var.ingress_replicas}",
      "  tuningOptions:",
      "    threadCount: ${var.ingress_thread_count}",
      "    clientTimeout: ${var.ingress_timeout_client}",
      "    serverTimeout: ${var.ingress_timeout_server}",
      "    maxConnections: ${var.ingress_max_connections}",
      var.ingress_hsts_max_age > 0 ? "  httpHeaders:" : "",
      var.ingress_hsts_max_age > 0 ? "    actions:" : "",
      var.ingress_hsts_max_age > 0 ? "      response:" : "",
      var.ingress_hsts_max_age > 0 ? "        - name: Strict-Transport-Security" : "",
      var.ingress_hsts_max_age > 0 ? "          action:" : "",
      var.ingress_hsts_max_age > 0 ? "            type: Set" : "",
      var.ingress_hsts_max_age > 0 ? "            set:" : "",
      var.ingress_hsts_max_age > 0 ? "              value: 'max-age=${var.ingress_hsts_max_age}; includeSubDomains; preload'" : "",
      var.ingress_default_cert_name != "" ? "  defaultCertificate:" : "",
      var.ingress_default_cert_name != "" ? "    name: ${var.ingress_default_cert_name}" : "",
      "EOF",

      "echo 'IngressController default patched'",
    ]
  }
}
