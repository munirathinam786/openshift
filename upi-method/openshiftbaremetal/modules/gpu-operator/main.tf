# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: NVIDIA GPU Operator + ClusterPolicy
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "ngc_api_key" {
  type      = string
  sensitive = true
}
variable "nls_token_file" { type = string }
variable "vgpu_driver_version" { type = string }
variable "vgpu_driver_image" { type = string }
variable "rdma_enabled" { type = bool }
variable "entitlement_pem_file" { type = string }

# --- Apply cluster-wide entitlement first ---
resource "null_resource" "cluster_entitlement" {
  count = var.entitlement_pem_file != "" ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "file" {
    source      = var.entitlement_pem_file
    destination = "/tmp/entitlement.pem"
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "ENTITLEMENT_B64=$(base64 -w 0 /tmp/entitlement.pem)",

      # Apply MachineConfig for cluster-wide entitlement
      "cat <<EOF | oc apply -f -",
      "apiVersion: machineconfiguration.openshift.io/v1",
      "kind: MachineConfig",
      "metadata:",
      "  labels:",
      "    machineconfiguration.openshift.io/role: worker",
      "  name: 50-worker-entitlement-pem",
      "spec:",
      "  config:",
      "    ignition:",
      "      version: 3.2.0",
      "    storage:",
      "      files:",
      "        - path: /etc/pki/entitlement/entitlement.pem",
      "          mode: 0644",
      "          overwrite: true",
      "          contents:",
      "            source: data:text/plain;base64,$ENTITLEMENT_B64",
      "        - path: /etc/pki/entitlement/entitlement-key.pem",
      "          mode: 0644",
      "          overwrite: true",
      "          contents:",
      "            source: data:text/plain;base64,$ENTITLEMENT_B64",
      "EOF",

      # Wait for MCP worker to finish rolling update
      "echo 'Waiting for MachineConfigPool worker update...'",
      "oc wait mcp/worker --for=condition=Updated --timeout=1800s",

      "rm -f /tmp/entitlement.pem",
    ]
  }
}

# --- Install GPU Operator ---
resource "null_resource" "gpu_operator" {
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
      "  name: nvidia-gpu-operator",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: nvidia-gpu-operator",
      "  namespace: nvidia-gpu-operator",
      "spec:",
      "  targetNamespaces:",
      "    - nvidia-gpu-operator",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: gpu-operator-certified",
      "  namespace: nvidia-gpu-operator",
      "spec:",
      "  channel: v24.6",
      "  installPlanApproval: Automatic",
      "  name: gpu-operator-certified",
      "  source: certified-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator CSV
      "echo 'Waiting for GPU Operator to install...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n nvidia-gpu-operator 2>/dev/null | grep -q Succeeded && break",
      "  sleep 10",
      "done",
    ]
  }

  depends_on = [null_resource.cluster_entitlement]
}

# --- Create NGC image pull secret ---
resource "null_resource" "ngc_secret" {
  count = var.ngc_api_key != "" ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "oc create secret docker-registry ngc-secret -n nvidia-gpu-operator --docker-server=nvcr.io --docker-username='\\$oauthtoken' --docker-password='${var.ngc_api_key}' --dry-run=client -o yaml | oc apply -f -",
    ]
  }

  depends_on = [null_resource.gpu_operator]
}

# --- Create NLS licensing ConfigMap ---
resource "null_resource" "nls_config" {
  count = var.nls_token_file != "" ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "file" {
    source      = var.nls_token_file
    destination = "/tmp/client_configuration_token.tok"
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "oc create configmap licensing-config -n nvidia-gpu-operator --from-file=client_configuration_token.tok=/tmp/client_configuration_token.tok --dry-run=client -o yaml | oc apply -f -",
      "rm -f /tmp/client_configuration_token.tok",
    ]
  }

  depends_on = [null_resource.gpu_operator]
}

# --- Create ClusterPolicy ---
resource "null_resource" "cluster_policy" {
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
      "apiVersion: nvidia.com/v1",
      "kind: ClusterPolicy",
      "metadata:",
      "  name: gpu-cluster-policy",
      "spec:",
      "  operator:",
      "    defaultRuntime: crio",
      "  driver:",
      "    enabled: true",
      "    repository: nvcr.io/nvidia/vgpu",
      "    version: '${var.vgpu_driver_version}'",
      "    image: ${var.vgpu_driver_image}",
      "    imagePullSecrets:",
      "      - ngc-secret",
      "    licensingConfig:",
      "      configMapName: licensing-config",
      "      nlsEnabled: true",
      "  dcgmExporter:",
      "    enabled: true",
      "  devicePlugin:",
      "    enabled: true",
      "  toolkit:",
      "    enabled: true",
      "  rdma:",
      "    enabled: ${var.rdma_enabled}",
      "  nodeStatusExporter:",
      "    enabled: true",
      "  gfd:",
      "    enabled: true",
      "EOF",

      # Wait for ClusterPolicy to be ready
      "echo 'Waiting for ClusterPolicy to be ready...'",
      "for i in $(seq 1 90); do",
      "  STATUS=$(oc get clusterpolicy gpu-cluster-policy -o jsonpath='{.status.state}' 2>/dev/null)",
      "  [ \"$STATUS\" = \"ready\" ] && echo 'ClusterPolicy is ready' && break",
      "  echo \"ClusterPolicy status: $STATUS (attempt $i/90)\"",
      "  sleep 20",
      "done",

      # Verify GPUs
      "echo '--- GPU Detection ---'",
      "oc get nodes -o=custom-columns='Node:metadata.name,GPUs:status.capacity.nvidia\\.com/gpu'",
    ]
  }

  depends_on = [
    null_resource.gpu_operator,
    null_resource.ngc_secret,
    null_resource.nls_config,
  ]
}
