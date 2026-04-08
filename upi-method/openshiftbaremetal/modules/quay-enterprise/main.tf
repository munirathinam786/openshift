# Author: Sathishkumar Munirathinam

# =============================================================================
# Red Hat Quay Enterprise Registry
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

variable "quay_channel" {
  description = "Quay operator channel"
  type        = string
  default     = "stable-3.12"
}

variable "quay_instance_name" {
  description = "QuayRegistry CR instance name"
  type        = string
  default     = "central-quay"
}

variable "quay_storage_size" {
  description = "PVC size for Quay storage backend"
  type        = string
  default     = "100Gi"
}

variable "quay_components" {
  description = "Quay component management overrides"
  type = object({
    clair          = optional(string, "managed")
    clairpostgres  = optional(string, "managed")
    objectstorage  = optional(string, "managed")
    postgres       = optional(string, "managed")
    redis          = optional(string, "managed")
    horizontalpodautoscaler = optional(string, "managed")
    mirror         = optional(string, "managed")
    monitoring     = optional(string, "managed")
    route          = optional(string, "managed")
    tls            = optional(string, "managed")
  })
  default = {}
}

variable "quay_superuser" {
  description = "Quay superuser username"
  type        = string
  default     = "quayadmin"
}

# --- Install Quay Operator ---
resource "null_resource" "quay_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: v1
      kind: Namespace
      metadata:
        name: quay-enterprise
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
        name: quay-operator-group
        namespace: quay-enterprise
      spec:
        targetNamespaces:
          - quay-enterprise
      EOF
      EOT
      ,
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operators.coreos.com/v1alpha1
      kind: Subscription
      metadata:
        name: quay-operator
        namespace: quay-enterprise
      spec:
        channel: ${var.quay_channel}
        installPlanApproval: Automatic
        name: quay-operator
        source: redhat-operators
        sourceNamespace: openshift-marketplace
      EOF
      EOT
      ,
      "echo 'Waiting for Quay Operator CSV...'",
      "for i in $(seq 1 60); do oc get csv -n quay-enterprise 2>/dev/null | grep -q Succeeded && break || sleep 10; done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Deploy QuayRegistry CR ---
resource "null_resource" "quay_registry" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: quay.redhat.com/v1
      kind: QuayRegistry
      metadata:
        name: ${var.quay_instance_name}
        namespace: quay-enterprise
      spec:
        components:
          - kind: clair
            managed: ${var.quay_components.clair == "managed" ? true : false}
          - kind: clairpostgres
            managed: ${var.quay_components.clairpostgres == "managed" ? true : false}
          - kind: objectstorage
            managed: ${var.quay_components.objectstorage == "managed" ? true : false}
          - kind: postgres
            managed: ${var.quay_components.postgres == "managed" ? true : false}
          - kind: redis
            managed: ${var.quay_components.redis == "managed" ? true : false}
          - kind: horizontalpodautoscaler
            managed: ${var.quay_components.horizontalpodautoscaler == "managed" ? true : false}
          - kind: mirror
            managed: ${var.quay_components.mirror == "managed" ? true : false}
          - kind: monitoring
            managed: ${var.quay_components.monitoring == "managed" ? true : false}
          - kind: route
            managed: ${var.quay_components.route == "managed" ? true : false}
          - kind: tls
            managed: ${var.quay_components.tls == "managed" ? true : false}
      EOF
      EOT
      ,
      "echo 'Waiting for QuayRegistry to be available...'",
      "for i in $(seq 1 120); do oc get quayregistry ${var.quay_instance_name} -n quay-enterprise -o jsonpath='{.status.conditions[?(@.type==\"Available\")].status}' 2>/dev/null | grep -q True && break || sleep 15; done",
      "oc get quayregistry ${var.quay_instance_name} -n quay-enterprise -o jsonpath='{.status.registryEndpoint}' 2>/dev/null || true",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.quay_operator]
}

output "quay_namespace" {
  value = "quay-enterprise"
}

output "quay_instance_name" {
  value = var.quay_instance_name
}
