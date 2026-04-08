# =============================================================================
# Module: External DNS — Automatic DNS Record Management
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "external_dns_provider" {
  description = "DNS provider (infoblox, rfc2136, aws, azure)"
  type        = string
  default     = "rfc2136"
}
variable "external_dns_domain_filter" {
  description = "Domain to manage DNS records for"
  type        = string
  default     = ""
}
variable "external_dns_sources" {
  description = "Kubernetes resources to watch for DNS records"
  type        = list(string)
  default     = ["route", "service"]
}
variable "rfc2136_host" {
  description = "DNS server host for RFC2136 dynamic updates"
  type        = string
  default     = ""
}
variable "rfc2136_port" {
  description = "DNS server port"
  type        = number
  default     = 53
}
variable "rfc2136_zone" {
  description = "DNS zone for RFC2136"
  type        = string
  default     = ""
}
variable "rfc2136_tsig_keyname" {
  description = "TSIG key name"
  type        = string
  default     = ""
}
variable "rfc2136_tsig_secret" {
  description = "TSIG shared secret (base64)"
  type        = string
  default     = ""
  sensitive   = true
}

resource "null_resource" "external_dns_operator" {
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
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: external-dns-operator",
      "  namespace: external-dns-operator",
      "spec:",
      "  channel: stable-v1",
      "  installPlanApproval: Automatic",
      "  name: external-dns-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for External DNS Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n external-dns-operator 2>/dev/null | grep external-dns | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      "echo 'External DNS Operator installed'",
    ]
  }
}

# --- Create ExternalDNS instance ---
resource "null_resource" "external_dns_instance" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<EOF | oc apply -f -",
      "apiVersion: externaldns.olm.openshift.io/v1beta1",
      "kind: ExternalDNS",
      "metadata:",
      "  name: cluster-external-dns",
      "  namespace: external-dns-operator",
      "spec:",
      "  provider:",
      "    type: ${var.external_dns_provider}",
      var.external_dns_provider == "rfc2136" ? "    rfc2136:" : "",
      var.external_dns_provider == "rfc2136" ? "      host: ${var.rfc2136_host}" : "",
      var.external_dns_provider == "rfc2136" ? "      port: ${var.rfc2136_port}" : "",
      var.external_dns_provider == "rfc2136" ? "      zone: ${var.rfc2136_zone}" : "",
      var.external_dns_provider == "rfc2136" ? "      tsigKeyName: ${var.rfc2136_tsig_keyname}" : "",
      var.external_dns_provider == "rfc2136" ? "      tsigSecretSecretRef:" : "",
      var.external_dns_provider == "rfc2136" ? "        name: external-dns-tsig-secret" : "",
      "  zones:",
      "    - ${var.external_dns_domain_filter}",
      "  source:",
      "    type: OpenShiftRoute",
      "    openshiftRouteOptions:",
      "      routerName: default",
      "EOF",

      "echo 'ExternalDNS instance created'",
    ]
  }

  depends_on = [null_resource.external_dns_operator]
}
