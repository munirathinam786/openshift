# =============================================================================
# Module: Training Operator — Kubeflow Training Operator for distributed ML
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "training_operator_namespace" {
  description = "Namespace for Training Operator"
  type        = string
  default     = "kubeflow"
}

resource "null_resource" "training_operator" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace ${var.training_operator_namespace} --dry-run=client -o yaml | oc apply -f -",

      # Install kubeflow training-operator via manifests
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ServiceAccount",
      "metadata:",
      "  name: training-operator",
      "  namespace: ${var.training_operator_namespace}",
      "EOF",

      # ClusterRole
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: rbac.authorization.k8s.io/v1",
      "kind: ClusterRole",
      "metadata:",
      "  name: training-operator",
      "rules:",
      "  - apiGroups: ['']",
      "    resources: [pods, services, endpoints, events, configmaps, serviceaccounts]",
      "    verbs: ['*']",
      "  - apiGroups: [apps]",
      "    resources: [deployments, replicasets, statefulsets]",
      "    verbs: ['*']",
      "  - apiGroups: [batch]",
      "    resources: [jobs]",
      "    verbs: ['*']",
      "  - apiGroups: [kubeflow.org]",
      "    resources: ['*']",
      "    verbs: ['*']",
      "  - apiGroups: [scheduling.volcano.sh]",
      "    resources: ['*']",
      "    verbs: ['*']",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: rbac.authorization.k8s.io/v1",
      "kind: ClusterRoleBinding",
      "metadata:",
      "  name: training-operator",
      "roleRef:",
      "  apiGroup: rbac.authorization.k8s.io",
      "  kind: ClusterRole",
      "  name: training-operator",
      "subjects:",
      "  - kind: ServiceAccount",
      "    name: training-operator",
      "    namespace: ${var.training_operator_namespace}",
      "EOF",

      # Register CRDs for PyTorchJob, TFJob, etc.
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: apiextensions.k8s.io/v1",
      "kind: CustomResourceDefinition",
      "metadata:",
      "  name: pytorchjobs.kubeflow.org",
      "spec:",
      "  group: kubeflow.org",
      "  names:",
      "    kind: PyTorchJob",
      "    plural: pytorchjobs",
      "    singular: pytorchjob",
      "  scope: Namespaced",
      "  versions:",
      "    - name: v1",
      "      served: true",
      "      storage: true",
      "      schema:",
      "        openAPIV3Schema:",
      "          type: object",
      "          x-kubernetes-preserve-unknown-fields: true",
      "      subresources:",
      "        status: {}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: apiextensions.k8s.io/v1",
      "kind: CustomResourceDefinition",
      "metadata:",
      "  name: tfjobs.kubeflow.org",
      "spec:",
      "  group: kubeflow.org",
      "  names:",
      "    kind: TFJob",
      "    plural: tfjobs",
      "    singular: tfjob",
      "  scope: Namespaced",
      "  versions:",
      "    - name: v1",
      "      served: true",
      "      storage: true",
      "      schema:",
      "        openAPIV3Schema:",
      "          type: object",
      "          x-kubernetes-preserve-unknown-fields: true",
      "      subresources:",
      "        status: {}",
      "EOF",

      # Deploy training-operator
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: apps/v1",
      "kind: Deployment",
      "metadata:",
      "  name: training-operator",
      "  namespace: ${var.training_operator_namespace}",
      "  labels:",
      "    control-plane: kubeflow-training-operator",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      control-plane: kubeflow-training-operator",
      "  template:",
      "    metadata:",
      "      labels:",
      "        control-plane: kubeflow-training-operator",
      "    spec:",
      "      serviceAccountName: training-operator",
      "      containers:",
      "        - name: training-operator",
      "          image: kubeflow/training-operator:v1-855e096",
      "          ports:",
      "            - containerPort: 8443",
      "          resources:",
      "            limits:",
      "              cpu: 500m",
      "              memory: 512Mi",
      "            requests:",
      "              cpu: 100m",
      "              memory: 128Mi",
      "          securityContext:",
      "            allowPrivilegeEscalation: false",
      "            readOnlyRootFilesystem: true",
      "            runAsNonRoot: true",
      "EOF",

      "echo 'Kubeflow Training Operator deployed (PyTorchJob, TFJob CRDs registered)'",
    ]
  }
}
