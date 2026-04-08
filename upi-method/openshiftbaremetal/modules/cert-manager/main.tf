# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: cert-manager — Automated TLS Certificate Lifecycle
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "certmanager_channel" {
  description = "OLM channel for cert-manager operator"
  type        = string
  default     = "stable-v1"
}
variable "cluster_issuer_name" {
  description = "Name of the default ClusterIssuer"
  type        = string
  default     = "internal-ca"
}
variable "cluster_issuer_type" {
  description = "Type of ClusterIssuer (self-signed, ca, acme)"
  type        = string
  default     = "self-signed"
}
variable "acme_server" {
  description = "ACME server URL (for acme issuer type)"
  type        = string
  default     = ""
}
variable "acme_email" {
  description = "Email for ACME registration"
  type        = string
  default     = ""
}

resource "null_resource" "cert_manager_operator" {
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
      "  name: cert-manager-operator",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: cert-manager-operator",
      "  namespace: cert-manager-operator",
      "spec:",
      "  targetNamespaces:",
      "    - cert-manager-operator",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: openshift-cert-manager-operator",
      "  namespace: cert-manager-operator",
      "spec:",
      "  channel: ${var.certmanager_channel}",
      "  installPlanApproval: Automatic",
      "  name: openshift-cert-manager-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for cert-manager Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n cert-manager-operator 2>/dev/null | grep cert-manager | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Wait for cert-manager pods
      "sleep 30",
      "oc wait --for=condition=Available deployment/cert-manager -n cert-manager --timeout=300s || true",

      "echo 'cert-manager Operator installed'",
    ]
  }
}

# --- Create ClusterIssuer ---
resource "null_resource" "cluster_issuer" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      <<-EOT
      %{if var.cluster_issuer_type == "self-signed"~}
      cat <<'EOF' | oc apply -f -
      apiVersion: cert-manager.io/v1
      kind: ClusterIssuer
      metadata:
        name: ${var.cluster_issuer_name}
      spec:
        selfSigned: {}
      EOF
      %{endif~}

      %{if var.cluster_issuer_type == "ca"~}
      cat <<'EOF' | oc apply -f -
      apiVersion: cert-manager.io/v1
      kind: ClusterIssuer
      metadata:
        name: ${var.cluster_issuer_name}-root
      spec:
        selfSigned: {}
      ---
      apiVersion: cert-manager.io/v1
      kind: Certificate
      metadata:
        name: ${var.cluster_issuer_name}-ca-cert
        namespace: cert-manager
      spec:
        isCA: true
        duration: 87600h
        commonName: ${var.cluster_issuer_name}-ca
        secretName: ${var.cluster_issuer_name}-ca-secret
        issuerRef:
          name: ${var.cluster_issuer_name}-root
          kind: ClusterIssuer
      ---
      apiVersion: cert-manager.io/v1
      kind: ClusterIssuer
      metadata:
        name: ${var.cluster_issuer_name}
      spec:
        ca:
          secretName: ${var.cluster_issuer_name}-ca-secret
      EOF
      %{endif~}

      %{if var.cluster_issuer_type == "acme"~}
      cat <<'EOF' | oc apply -f -
      apiVersion: cert-manager.io/v1
      kind: ClusterIssuer
      metadata:
        name: ${var.cluster_issuer_name}
      spec:
        acme:
          server: ${var.acme_server}
          email: ${var.acme_email}
          privateKeySecretRef:
            name: ${var.cluster_issuer_name}-acme-key
          solvers:
            - http01:
                ingress:
                  class: openshift-default
      EOF
      %{endif~}
      EOT
      ,

      "echo 'ClusterIssuer ${var.cluster_issuer_name} (${var.cluster_issuer_type}) created'",
    ]
  }

  depends_on = [null_resource.cert_manager_operator]
}
