# =============================================================================
# ACM Cluster Import — Import Managed Clusters into ACM Hub
# Creates ManagedCluster + KlusterletAddonConfig + auto-import Secret
# for each cluster to be managed by ACM.
# =============================================================================

variable "kubeconfig" {
  description = "Path to hub kubeconfig on bastion"
  type        = string
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

variable "managed_clusters" {
  description = "List of clusters to import into ACM hub"
  type = list(object({
    name               = string
    api_url            = string
    kubeconfig_path    = string
    cluster_labels     = map(string)
    klusterlet_addons  = optional(object({
      application_manager = optional(bool, true)
      policy_controller   = optional(bool, true)
      search_collector    = optional(bool, true)
      cert_policy         = optional(bool, true)
      iam_policy          = optional(bool, true)
    }), {})
  }))
  default = []
}

variable "auto_import_retry" {
  description = "Number of retries for auto-import"
  type        = number
  default     = 2
}

# --- Create ManagedCluster + KlusterletAddonConfig + Auto-Import Secret ---
resource "null_resource" "import_managed_cluster" {
  count = length(var.managed_clusters)

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # --- Create ManagedCluster namespace ---
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: v1
      kind: Namespace
      metadata:
        name: ${var.managed_clusters[count.index].name}
      EOF
      EOT
      ,

      # --- Create ManagedCluster CR ---
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: cluster.open-cluster-management.io/v1
      kind: ManagedCluster
      metadata:
        name: ${var.managed_clusters[count.index].name}
        labels:
          cloud: BareMetal
          vendor: OpenShift
          name: ${var.managed_clusters[count.index].name}
%{for k, v in var.managed_clusters[count.index].cluster_labels~}
          ${k}: "${v}"
%{endfor~}
      spec:
        hubAcceptsClient: true
        leaseDurationSeconds: 60
      EOF
      EOT
      ,

      # --- Create KlusterletAddonConfig ---
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: agent.open-cluster-management.io/v1
      kind: KlusterletAddonConfig
      metadata:
        name: ${var.managed_clusters[count.index].name}
        namespace: ${var.managed_clusters[count.index].name}
      spec:
        clusterName: ${var.managed_clusters[count.index].name}
        clusterNamespace: ${var.managed_clusters[count.index].name}
        applicationManager:
          enabled: ${try(var.managed_clusters[count.index].klusterlet_addons.application_manager, true)}
        policyController:
          enabled: ${try(var.managed_clusters[count.index].klusterlet_addons.policy_controller, true)}
        searchCollector:
          enabled: ${try(var.managed_clusters[count.index].klusterlet_addons.search_collector, true)}
        certPolicyController:
          enabled: ${try(var.managed_clusters[count.index].klusterlet_addons.cert_policy, true)}
        iamPolicyController:
          enabled: ${try(var.managed_clusters[count.index].klusterlet_addons.iam_policy, true)}
      EOF
      EOT
      ,

      # --- Create auto-import Secret (using the managed cluster's kubeconfig) ---
      <<-EOT
      oc create secret generic auto-import-secret \
        -n ${var.managed_clusters[count.index].name} \
        --from-file=kubeconfig=${var.managed_clusters[count.index].kubeconfig_path} \
        --from-literal=autoImportRetry=${var.auto_import_retry} \
        --dry-run=client -o yaml | oc apply -f -
      EOT
      ,

      # --- Wait for cluster to reach Available status ---
      "echo 'Waiting for ManagedCluster ${var.managed_clusters[count.index].name} to be imported...'",
      "for i in $(seq 1 90); do",
      "  STATUS=$(oc get managedcluster ${var.managed_clusters[count.index].name} -o jsonpath='{.status.conditions[?(@.type==\"ManagedClusterConditionAvailable\")].status}' 2>/dev/null)",
      "  [ \"$STATUS\" = \"True\" ] && echo 'Cluster imported successfully.' && break",
      "  sleep 20",
      "done",
      "oc get managedcluster ${var.managed_clusters[count.index].name} || true",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Create ManagedClusterSet for grouping ---
resource "null_resource" "managed_cluster_set" {
  count = var.cluster_set_name != "" ? 1 : 0

  provisioner "remote-exec" {
    inline = concat([
      "export KUBECONFIG=${var.kubeconfig}",

      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: cluster.open-cluster-management.io/v1beta2
      kind: ManagedClusterSet
      metadata:
        name: ${var.cluster_set_name}
      spec:
        clusterSelector:
          selectorType: ExclusiveClusterSetLabel
      EOF
      EOT
      ,

      # Bind the ClusterSet to the openshift-gitops namespace for ArgoCD integration
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: cluster.open-cluster-management.io/v1beta2
      kind: ManagedClusterSetBinding
      metadata:
        name: ${var.cluster_set_name}
        namespace: openshift-gitops
      spec:
        clusterSet: ${var.cluster_set_name}
      EOF
      EOT
      ,

    ], [for mc in var.managed_clusters : "oc label managedcluster ${mc.name} cluster.open-cluster-management.io/clusterset=${var.cluster_set_name} --overwrite || true"])

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.import_managed_cluster]
}

variable "cluster_set_name" {
  description = "Name of the ManagedClusterSet for grouping imported clusters (empty to skip)"
  type        = string
  default     = ""
}

output "imported_clusters" {
  description = "List of imported managed cluster names"
  value       = [for mc in var.managed_clusters : mc.name]
}

output "cluster_set_name" {
  description = "ManagedClusterSet name"
  value       = var.cluster_set_name
}
