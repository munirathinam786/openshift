# =============================================================================
# Module: OpenShift Data Foundation (ODF)
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "odf_channel" { type = string }
variable "storage_capacity" { type = string }
variable "odf_worker_nodes" {
  type = list(object({
    name = string
  }))
}

resource "null_resource" "odf_operator" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create namespace
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: openshift-storage",
      "  labels:",
      "    openshift.io/cluster-monitoring: 'true'",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: openshift-storage-operatorgroup",
      "  namespace: openshift-storage",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-storage",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: odf-operator",
      "  namespace: openshift-storage",
      "spec:",
      "  channel: ${var.odf_channel}",
      "  installPlanApproval: Automatic",
      "  name: odf-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Enable console plugin
      "oc patch console.operator cluster -n openshift-storage --type json -p '[{\"op\": \"add\", \"path\": \"/spec/plugins/-\", \"value\": \"odf-console\"}]' 2>/dev/null || true",

      # Wait for operator
      "echo 'Waiting for ODF operator to install...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-storage 2>/dev/null | grep odf-operator | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Label ODF nodes
    ]
  }
}

resource "null_resource" "odf_label_nodes" {
  for_each = { for idx, node in var.odf_worker_nodes : idx => node }

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "oc label node ${each.value.name} cluster.ocs.openshift.io/openshift-storage='' --overwrite",
    ]
  }

  depends_on = [null_resource.odf_operator]
}

resource "null_resource" "odf_storage_cluster" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create StorageCluster
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: ocs.openshift.io/v1",
      "kind: StorageCluster",
      "metadata:",
      "  name: ocs-storagecluster",
      "  namespace: openshift-storage",
      "spec:",
      "  manageNodes: false",
      "  monDataDirHostPath: /var/lib/rook",
      "  storageDeviceSets:",
      "    - name: ocs-deviceset",
      "      count: ${length(var.odf_worker_nodes)}",
      "      dataPVCTemplate:",
      "        spec:",
      "          accessModes:",
      "            - ReadWriteOnce",
      "          resources:",
      "            requests:",
      "              storage: ${var.storage_capacity}",
      "          storageClassName: localblock",
      "          volumeMode: Block",
      "      placement: {}",
      "      portable: true",
      "      replica: 3",
      "  multiCloudGateway:",
      "    reconcileStrategy: standalone",
      "EOF",

      # Wait for StorageCluster to be ready
      "echo 'Waiting for StorageCluster to be ready...'",
      "for i in $(seq 1 90); do",
      "  PHASE=$(oc get storagecluster ocs-storagecluster -n openshift-storage -o jsonpath='{.status.phase}' 2>/dev/null)",
      "  [ \"$PHASE\" = \"Ready\" ] && echo 'StorageCluster is ready' && break",
      "  echo \"StorageCluster phase: $PHASE (attempt $i/90)\"",
      "  sleep 20",
      "done",
    ]
  }

  depends_on = [null_resource.odf_label_nodes]
}
