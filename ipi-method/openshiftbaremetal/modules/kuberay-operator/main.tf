# =============================================================================
# Module: KubeRay Operator — Ray cluster orchestration for distributed ML
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kuberay_namespace" {
  description = "Namespace for KubeRay Operator"
  type        = string
  default     = "kuberay-system"
}
variable "kuberay_version" {
  description = "KubeRay operator version"
  type        = string
  default     = "v1.1.0"
}
variable "ray_cluster_name" {
  description = "Default Ray cluster name"
  type        = string
  default     = "raycluster"
}
variable "ray_head_cpu" {
  description = "CPU for Ray head node"
  type        = string
  default     = "4"
}
variable "ray_head_memory" {
  description = "Memory for Ray head node"
  type        = string
  default     = "8Gi"
}
variable "ray_worker_replicas" {
  description = "Number of Ray worker replicas"
  type        = number
  default     = 2
}
variable "ray_worker_cpu" {
  description = "CPU per Ray worker"
  type        = string
  default     = "4"
}
variable "ray_worker_memory" {
  description = "Memory per Ray worker"
  type        = string
  default     = "16Gi"
}
variable "ray_worker_gpu" {
  description = "GPUs per Ray worker"
  type        = number
  default     = 1
}

resource "null_resource" "kuberay_operator" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace ${var.kuberay_namespace} --dry-run=client -o yaml | oc apply -f -",

      # Install KubeRay via OLM
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: kuberay",
      "  namespace: ${var.kuberay_namespace}",
      "spec:",
      "  targetNamespaces:",
      "    - ${var.kuberay_namespace}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: kuberay-operator",
      "  namespace: ${var.kuberay_namespace}",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: kuberay-operator",
      "  source: community-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for KubeRay Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n ${var.kuberay_namespace} 2>/dev/null | grep kuberay | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create default RayCluster
      "cat <<EOF | oc apply -f -",
      "apiVersion: ray.io/v1",
      "kind: RayCluster",
      "metadata:",
      "  name: ${var.ray_cluster_name}",
      "  namespace: ${var.kuberay_namespace}",
      "spec:",
      "  headGroupSpec:",
      "    rayStartParams:",
      "      dashboard-host: '0.0.0.0'",
      "    template:",
      "      spec:",
      "        containers:",
      "          - name: ray-head",
      "            image: rayproject/ray:2.9.0",
      "            resources:",
      "              limits:",
      "                cpu: '${var.ray_head_cpu}'",
      "                memory: '${var.ray_head_memory}'",
      "              requests:",
      "                cpu: '2'",
      "                memory: '4Gi'",
      "            ports:",
      "              - containerPort: 6379",
      "                name: gcs-server",
      "              - containerPort: 8265",
      "                name: dashboard",
      "              - containerPort: 10001",
      "                name: client",
      "  workerGroupSpecs:",
      "    - replicas: ${var.ray_worker_replicas}",
      "      minReplicas: 1",
      "      maxReplicas: 10",
      "      groupName: gpu-workers",
      "      rayStartParams: {}",
      "      template:",
      "        spec:",
      "          containers:",
      "            - name: ray-worker",
      "              image: rayproject/ray:2.9.0",
      "              resources:",
      "                limits:",
      "                  cpu: '${var.ray_worker_cpu}'",
      "                  memory: '${var.ray_worker_memory}'",
      "                  nvidia.com/gpu: '${var.ray_worker_gpu}'",
      "                requests:",
      "                  cpu: '2'",
      "                  memory: '8Gi'",
      "EOF",

      # Create Route for Ray Dashboard
      "oc expose service ${var.ray_cluster_name}-head-svc -n ${var.kuberay_namespace} --port=dashboard --name=ray-dashboard 2>/dev/null || true",

      "echo 'KubeRay Operator and RayCluster deployed'",
    ]
  }
}
