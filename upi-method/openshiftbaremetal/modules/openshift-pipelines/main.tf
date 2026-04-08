# =============================================================================
# OpenShift Pipelines (Tekton) — Operator + TektonConfig + ClusterTasks
# Installs the OpenShift Pipelines operator and configures the TektonConfig CR
# with optional cluster tasks, pipeline-as-code, and resource limits.
# =============================================================================

# --- Install OpenShift Pipelines Operator ---
resource "null_resource" "pipelines_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: openshift-pipelines-operator-rh",
      "  namespace: openshift-operators",
      "spec:",
      "  channel: ${var.pipelines_channel}",
      "  installPlanApproval: Automatic",
      "  name: openshift-pipelines-operator-rh",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator to become available
      "echo 'Waiting for OpenShift Pipelines operator...'",
      "for i in $(seq 1 90); do",
      "  oc get csv -n openshift-operators 2>/dev/null | grep pipelines | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Wait for TektonConfig CR
      "echo 'Waiting for TektonConfig...'",
      "for i in $(seq 1 60); do",
      "  oc get tektonconfig config 2>/dev/null && break",
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

# --- Configure TektonConfig CR ---
resource "null_resource" "tekton_config" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operator.tekton.dev/v1alpha1",
      "kind: TektonConfig",
      "metadata:",
      "  name: config",
      "spec:",
      "  profile: ${var.tekton_profile}",
      "  targetNamespace: openshift-pipelines",
      "  addon:",
      "    enablePipelinesAsCode: ${var.enable_pipelines_as_code}",
      "    params:",
      "    - name: clusterTasks",
      "      value: '${var.enable_cluster_tasks}'",
      "    - name: pipelineTemplates",
      "      value: '${var.enable_pipeline_templates}'",
      "    - name: communityClusterTasks",
      "      value: '${var.enable_community_cluster_tasks}'",
      "  pipeline:",
      "    params:",
      "    - name: default-timeout-minutes",
      "      value: '${var.pipeline_default_timeout}'",
      "    - name: enable-api-fields",
      "      value: ${var.tekton_api_fields}",
      "    default-service-account: ${var.pipeline_default_sa}",
      "  trigger:",
      "    default-service-account: ${var.pipeline_default_sa}",
      "    enable-api-fields: ${var.tekton_api_fields}",
      "EOF",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.pipelines_operator]
}

# --- Create pipeline namespaces with resource quotas ---
resource "null_resource" "pipeline_namespaces" {
  count = length(var.pipeline_namespaces) > 0 ? 1 : 0

  provisioner "remote-exec" {
    inline = concat(
      ["export KUBECONFIG=${var.kubeconfig}"],
      [for ns in var.pipeline_namespaces : join("\n", [
        "oc create namespace ${ns} --dry-run=client -o yaml | oc apply -f -",
        "oc label namespace ${ns} app.kubernetes.io/managed-by=tekton --overwrite",
      ])]
    )

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.tekton_config]
}

# --- Configure pipeline resource limits per namespace ---
resource "null_resource" "pipeline_resource_limits" {
  count = var.enable_pipeline_resource_limits ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: LimitRange",
      "metadata:",
      "  name: pipeline-limits",
      "  namespace: openshift-pipelines",
      "spec:",
      "  limits:",
      "  - type: Container",
      "    default:",
      "      cpu: ${var.pipeline_container_cpu_limit}",
      "      memory: ${var.pipeline_container_memory_limit}",
      "    defaultRequest:",
      "      cpu: ${var.pipeline_container_cpu_request}",
      "      memory: ${var.pipeline_container_memory_request}",
      "EOF",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.tekton_config]
}

# --- Configure Pipelines-as-Code (GitHub/GitLab webhook integration) ---
resource "null_resource" "pipelines_as_code_config" {
  count = var.enable_pipelines_as_code && var.pac_webhook_secret != "" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Secret",
      "metadata:",
      "  name: pipelines-as-code-secret",
      "  namespace: openshift-pipelines",
      "type: Opaque",
      "stringData:",
      "  provider.token: ${var.pac_webhook_secret}",
      "  webhook.secret: ${var.pac_webhook_shared_secret}",
      "EOF",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.tekton_config]
}
