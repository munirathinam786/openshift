# Author: Sathishkumar Munirathinam

# =============================================================================
# Red Hat Advanced Cluster Security (ACS / StackRox)
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

variable "acs_channel" {
  description = "ACS operator channel"
  type        = string
  default     = "stable"
}

variable "acs_central_admin_password" {
  description = "Initial admin password for ACS Central (leave empty for auto-generated)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "acs_central_storage_size" {
  description = "PVC size for ACS Central DB"
  type        = string
  default     = "100Gi"
}

variable "deploy_secured_cluster" {
  description = "Deploy SecuredCluster CR on this cluster (sensor + collector)"
  type        = bool
  default     = true
}

variable "central_endpoint" {
  description = "Central endpoint for SecuredCluster (host:port). Required when deploy_secured_cluster=true on a non-Central cluster."
  type        = string
  default     = ""
}

variable "cluster_name" {
  description = "Cluster name for SecuredCluster registration"
  type        = string
  default     = ""
}

variable "deploy_central" {
  description = "Deploy ACS Central on this cluster (management cluster)"
  type        = bool
  default     = true
}

# --- Install ACS Operator ---
resource "null_resource" "acs_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: v1
      kind: Namespace
      metadata:
        name: rhacs-operator
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
        name: rhacs-operator-group
        namespace: rhacs-operator
      spec: {}
      EOF
      EOT
      ,
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operators.coreos.com/v1alpha1
      kind: Subscription
      metadata:
        name: rhacs-operator
        namespace: rhacs-operator
      spec:
        channel: ${var.acs_channel}
        installPlanApproval: Automatic
        name: rhacs-operator
        source: redhat-operators
        sourceNamespace: openshift-marketplace
      EOF
      EOT
      ,
      "echo 'Waiting for ACS Operator CSV...'",
      "for i in $(seq 1 60); do oc get csv -n rhacs-operator 2>/dev/null | grep -q Succeeded && break || sleep 10; done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Create stackrox namespace ---
resource "null_resource" "acs_namespace" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: v1
      kind: Namespace
      metadata:
        name: stackrox
      EOF
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

  depends_on = [null_resource.acs_operator]
}

# --- Deploy ACS Central (management cluster only) ---
resource "null_resource" "acs_central" {
  count = var.deploy_central ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: platform.stackrox.io/v1alpha1
      kind: Central
      metadata:
        name: stackrox-central-services
        namespace: stackrox
      spec:
        central:
          exposure:
            loadBalancer:
              enabled: false
            route:
              enabled: true
          persistence:
            persistentVolumeClaim:
              claimName: stackrox-db
              size: ${var.acs_central_storage_size}
          db:
            isEnabled: Default
            persistence:
              persistentVolumeClaim:
                claimName: central-db
                size: ${var.acs_central_storage_size}
        egress:
          connectivityPolicy: Online
        scanner:
          analyzer:
            scaling:
              autoScaling: Enabled
              maxReplicas: 5
              minReplicas: 2
              replicas: 3
          scannerComponent: Enabled
      EOF
      EOT
      ,
      "echo 'Waiting for ACS Central to be ready...'",
      "for i in $(seq 1 120); do oc get central stackrox-central-services -n stackrox -o jsonpath='{.status.conditions[?(@.type==\"Deployed\")].status}' 2>/dev/null | grep -q True && break || sleep 15; done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.acs_namespace]
}

# --- Deploy SecuredCluster (all clusters including management) ---
resource "null_resource" "acs_secured_cluster" {
  count = var.deploy_secured_cluster ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: platform.stackrox.io/v1alpha1
      kind: SecuredCluster
      metadata:
        name: stackrox-secured-cluster-services
        namespace: stackrox
      spec:
        auditLogs:
          collection: Auto
        admissionControl:
          listenOnUpdates: true
          bypass: BreakGlassAnnotation
          contactImageScanners: DoNotScanInline
          listenOnCreates: true
          listenOnEvents: true
          timeoutSeconds: 20
        centralEndpoint: "${var.central_endpoint != "" ? var.central_endpoint : "central-stackrox.apps.${var.cluster_name}"}"
        clusterName: "${var.cluster_name}"
        perNode:
          collector:
            collection: EBPF
            imageFlavor: Regular
          taintToleration: TolerateTaints
      EOF
      EOT
      ,
      "echo 'Waiting for SecuredCluster to be ready...'",
      "for i in $(seq 1 90); do oc get securedcluster -n stackrox stackrox-secured-cluster-services -o jsonpath='{.status.conditions[?(@.type==\"Deployed\")].status}' 2>/dev/null | grep -q True && break || sleep 10; done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.acs_central, null_resource.acs_namespace]
}

output "acs_namespace" {
  value = "stackrox"
}

output "acs_central_route" {
  value = var.deploy_central ? "https://central-stackrox.apps.<cluster-domain>" : ""
}
