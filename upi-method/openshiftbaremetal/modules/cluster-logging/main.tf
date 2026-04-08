# Author: Sathishkumar Munirathinam

# =============================================================================
# OpenShift Cluster Logging — ClusterLogging + ClusterLogForwarder
# Deploys Logging stack with optional S3 log forwarding (ODF-backed)
# =============================================================================

# --- Install Cluster Logging Operator ---
resource "null_resource" "logging_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create openshift-logging namespace
      "oc create namespace openshift-logging --dry-run=client -o yaml | oc apply -f -",
      "oc label namespace openshift-logging openshift.io/cluster-monitoring=true --overwrite",

      # Install Cluster Logging Operator
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: cluster-logging",
      "  namespace: openshift-logging",
      "spec:",
      "  channel: ${var.logging_channel}",
      "  name: cluster-logging",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "  installPlanApproval: Automatic",
      "EOF",

      # Install Elasticsearch Operator (if using elasticsearch store)
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: elasticsearch-operator",
      "  namespace: openshift-operators-redhat",
      "spec:",
      "  channel: ${var.logging_channel}",
      "  name: elasticsearch-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "  installPlanApproval: Automatic",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: cluster-logging",
      "  namespace: openshift-logging",
      "spec:",
      "  targetNamespaces:",
      "  - openshift-logging",
      "EOF",

      # Wait for operator to be ready
      "sleep 60",
      "oc wait --for=condition=Available deployment/cluster-logging-operator -n openshift-logging --timeout=300s || true",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Create ClusterLogging Instance ---
resource "null_resource" "cluster_logging_instance" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: logging.openshift.io/v1",
      "kind: ClusterLogging",
      "metadata:",
      "  name: instance",
      "  namespace: openshift-logging",
      "spec:",
      "  managementState: Managed",
      "  logStore:",
      "    type: ${var.log_store_type}",
      "    retentionPolicy:",
      "      application:",
      "        maxAge: ${var.log_retention_application}",
      "      infra:",
      "        maxAge: ${var.log_retention_infra}",
      "      audit:",
      "        maxAge: ${var.log_retention_audit}",
      "    elasticsearch:",
      "      nodeCount: ${var.elasticsearch_node_count}",
      "      storage:",
      "        storageClassName: ${var.log_storage_class}",
      "        size: ${var.log_storage_size}",
      "      resources:",
      "        requests:",
      "          memory: ${var.elasticsearch_memory}",
      "      redundancyPolicy: SingleRedundancy",
      "  visualization:",
      "    type: kibana",
      "    kibana:",
      "      replicas: 1",
      "  collection:",
      "    type: vector",
      "EOF",

      "echo 'ClusterLogging instance created'",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.logging_operator]
}

# --- S3 Secret for Log Forwarding ---
resource "null_resource" "logging_s3_secret" {
  count = var.enable_log_forwarding_s3 ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic logging-s3-secret -n openshift-logging \\",
      "  --from-literal=aws_access_key_id=${var.log_s3_access_key} \\",
      "  --from-literal=aws_secret_access_key=${var.log_s3_secret_key} \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.logging_operator]
}

# --- ClusterLogForwarder with S3 Output ---
resource "null_resource" "cluster_log_forwarder" {
  count = var.enable_log_forwarding_s3 ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: logging.openshift.io/v1",
      "kind: ClusterLogForwarder",
      "metadata:",
      "  name: instance",
      "  namespace: openshift-logging",
      "spec:",
      "  outputs:",
      "  - name: s3-output",
      "    type: s3",
      "    s3:",
      "      endpoint: ${var.log_s3_endpoint}",
      "      bucket: ${var.log_s3_bucket}",
      "      region: ${var.log_s3_region}",
      "    secret:",
      "      name: logging-s3-secret",
      "  pipelines:",
      "  - name: all-logs-to-s3",
      "    inputRefs:",
      "    - application",
      "    - infrastructure",
      "    - audit",
      "    outputRefs:",
      "    - s3-output",
      "    - default",
      "EOF",

      "echo 'ClusterLogForwarder with S3 output created'",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.cluster_logging_instance, null_resource.logging_s3_secret]
}
