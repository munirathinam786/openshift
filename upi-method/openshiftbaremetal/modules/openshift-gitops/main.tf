# Author: Sathishkumar Munirathinam

# =============================================================================
# OpenShift GitOps (Argo CD) — Operator + ArgoCD Instance + RBAC
# Installs the OpenShift GitOps operator and configures an ArgoCD instance
# with optional RBAC policies, managed namespaces, and SSO integration.
# =============================================================================

# --- Install OpenShift GitOps Operator ---
resource "null_resource" "gitops_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Install OpenShift GitOps operator (cluster-scoped — no OperatorGroup needed)
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: openshift-gitops-operator",
      "  namespace: openshift-operators",
      "spec:",
      "  channel: ${var.gitops_channel}",
      "  installPlanApproval: Automatic",
      "  name: openshift-gitops-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator to become available
      "echo 'Waiting for OpenShift GitOps operator...'",
      "for i in $(seq 1 90); do",
      "  oc get csv -n openshift-gitops 2>/dev/null | grep openshift-gitops-operator | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Wait for default ArgoCD instance
      "echo 'Waiting for default ArgoCD instance...'",
      "for i in $(seq 1 60); do",
      "  oc get argocd openshift-gitops -n openshift-gitops 2>/dev/null && break",
      "  sleep 10",
      "done",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Configure ArgoCD Instance ---
resource "null_resource" "argocd_instance" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: argoproj.io/v1beta1",
      "kind: ArgoCD",
      "metadata:",
      "  name: openshift-gitops",
      "  namespace: openshift-gitops",
      "spec:",
      "  server:",
      "    autoscale:",
      "      enabled: ${var.argocd_server_autoscale}",
      "    route:",
      "      enabled: true",
      "      tls:",
      "        termination: reencrypt",
      "    resources:",
      "      requests:",
      "        cpu: ${var.argocd_server_cpu_request}",
      "        memory: ${var.argocd_server_memory_request}",
      "      limits:",
      "        cpu: ${var.argocd_server_cpu_limit}",
      "        memory: ${var.argocd_server_memory_limit}",
      "  controller:",
      "    resources:",
      "      requests:",
      "        cpu: ${var.argocd_controller_cpu_request}",
      "        memory: ${var.argocd_controller_memory_request}",
      "      limits:",
      "        cpu: ${var.argocd_controller_cpu_limit}",
      "        memory: ${var.argocd_controller_memory_limit}",
      "  repo:",
      "    resources:",
      "      requests:",
      "        cpu: 250m",
      "        memory: 256Mi",
      "      limits:",
      "        cpu: '1'",
      "        memory: 1Gi",
      "  ha:",
      "    enabled: ${var.argocd_ha_enabled}",
      "  rbac:",
      "    defaultPolicy: '${var.argocd_rbac_default_policy}'",
      "    policy: |",
      "      ${indent(6, var.argocd_rbac_policy)}",
      "    scopes: '[groups]'",
      "  resourceExclusions: |",
      "    - apiGroups:",
      "      - tekton.dev",
      "      clusters:",
      "      - '*'",
      "      kinds:",
      "      - TaskRun",
      "      - PipelineRun",
      "EOF",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.gitops_operator]
}

# --- Grant ArgoCD cluster-admin for managed namespaces ---
resource "null_resource" "argocd_cluster_role" {
  count = var.argocd_cluster_admin ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Grant cluster-admin to the ArgoCD application-controller SA
      "oc adm policy add-cluster-role-to-user cluster-admin",
      "  system:serviceaccount:openshift-gitops:openshift-gitops-argocd-application-controller",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.argocd_instance]
}

# --- Create managed namespaces and label them for ArgoCD ---
resource "null_resource" "argocd_managed_namespaces" {
  count = length(var.argocd_managed_namespaces) > 0 ? 1 : 0

  provisioner "remote-exec" {
    inline = concat(
      ["export KUBECONFIG=${var.kubeconfig}"],
      [for ns in var.argocd_managed_namespaces :
        "oc create namespace ${ns} --dry-run=client -o yaml | oc apply -f - && oc label namespace ${ns} argocd.argoproj.io/managed-by=openshift-gitops --overwrite"
      ]
    )

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.argocd_instance]
}

# --- Configure Git repository connections ---
resource "null_resource" "argocd_repo_credentials" {
  count = var.argocd_repo_url != "" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Secret",
      "metadata:",
      "  name: repo-${replace(var.argocd_repo_url, "/[^a-zA-Z0-9]/", "-")}",
      "  namespace: openshift-gitops",
      "  labels:",
      "    argocd.argoproj.io/secret-type: repository",
      "type: Opaque",
      "stringData:",
      "  type: git",
      "  url: ${var.argocd_repo_url}",
      "  password: ${var.argocd_repo_token}",
      "  username: git",
      "  insecure: '${var.argocd_repo_insecure}'",
      "EOF",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.argocd_instance]
}
