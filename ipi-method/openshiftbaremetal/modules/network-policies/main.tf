# =============================================================================
# Module: Network Policies — Default-deny + allow-list per namespace
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "network_policy_namespaces" {
  description = "Namespaces to apply default-deny + allow policies"
  type        = list(string)
  default     = []
}
variable "allow_dns" {
  description = "Allow egress to cluster DNS"
  type        = bool
  default     = true
}
variable "allow_monitoring" {
  description = "Allow ingress from openshift-monitoring (Prometheus scraping)"
  type        = bool
  default     = true
}
variable "allow_ingress_controller" {
  description = "Allow ingress from openshift-ingress (router pods)"
  type        = bool
  default     = true
}

resource "null_resource" "network_policies" {
  count = length(var.network_policy_namespaces)

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Ensure namespace exists
      "oc create namespace ${var.network_policy_namespaces[count.index]} --dry-run=client -o yaml | oc apply -f -",

      # Default deny all ingress
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: networking.k8s.io/v1",
      "kind: NetworkPolicy",
      "metadata:",
      "  name: default-deny-ingress",
      "  namespace: ${var.network_policy_namespaces[count.index]}",
      "spec:",
      "  podSelector: {}",
      "  policyTypes:",
      "    - Ingress",
      "EOF",

      # Default deny all egress
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: networking.k8s.io/v1",
      "kind: NetworkPolicy",
      "metadata:",
      "  name: default-deny-egress",
      "  namespace: ${var.network_policy_namespaces[count.index]}",
      "spec:",
      "  podSelector: {}",
      "  policyTypes:",
      "    - Egress",
      "EOF",

      # Allow intra-namespace traffic
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: networking.k8s.io/v1",
      "kind: NetworkPolicy",
      "metadata:",
      "  name: allow-same-namespace",
      "  namespace: ${var.network_policy_namespaces[count.index]}",
      "spec:",
      "  podSelector: {}",
      "  ingress:",
      "    - from:",
      "        - podSelector: {}",
      "  egress:",
      "    - to:",
      "        - podSelector: {}",
      "  policyTypes:",
      "    - Ingress",
      "    - Egress",
      "EOF",

      # Allow DNS egress
      <<-EOT
      %{if var.allow_dns~}
      cat <<'EOF' | oc apply -f -
      apiVersion: networking.k8s.io/v1
      kind: NetworkPolicy
      metadata:
        name: allow-dns-egress
        namespace: ${var.network_policy_namespaces[count.index]}
      spec:
        podSelector: {}
        egress:
          - to:
              - namespaceSelector:
                  matchLabels:
                    kubernetes.io/metadata.name: openshift-dns
            ports:
              - protocol: UDP
                port: 5353
              - protocol: TCP
                port: 5353
        policyTypes:
          - Egress
      EOF
      %{endif~}
      EOT
      ,

      # Allow monitoring ingress
      <<-EOT
      %{if var.allow_monitoring~}
      cat <<'EOF' | oc apply -f -
      apiVersion: networking.k8s.io/v1
      kind: NetworkPolicy
      metadata:
        name: allow-monitoring-ingress
        namespace: ${var.network_policy_namespaces[count.index]}
      spec:
        podSelector: {}
        ingress:
          - from:
              - namespaceSelector:
                  matchLabels:
                    kubernetes.io/metadata.name: openshift-monitoring
        policyTypes:
          - Ingress
      EOF
      %{endif~}
      EOT
      ,

      # Allow ingress controller
      <<-EOT
      %{if var.allow_ingress_controller~}
      cat <<'EOF' | oc apply -f -
      apiVersion: networking.k8s.io/v1
      kind: NetworkPolicy
      metadata:
        name: allow-ingress-controller
        namespace: ${var.network_policy_namespaces[count.index]}
      spec:
        podSelector: {}
        ingress:
          - from:
              - namespaceSelector:
                  matchLabels:
                    network.openshift.io/policy-group: ingress
        policyTypes:
          - Ingress
      EOF
      %{endif~}
      EOT
      ,

      "echo 'Network policies applied to namespace ${var.network_policy_namespaces[count.index]}'",
    ]
  }
}
