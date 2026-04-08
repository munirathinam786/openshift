# =============================================================================
# OADP — OpenShift API for Data Protection (Backup & Restore)
# Deploys OADP operator + DataProtectionApplication with S3 BSL
# =============================================================================

# --- Install OADP Operator ---
resource "null_resource" "oadp_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create namespace
      "oc create namespace openshift-adp --dry-run=client -o yaml | oc apply -f -",

      # Install OADP Operator
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: redhat-oadp-operator",
      "  namespace: openshift-adp",
      "spec:",
      "  channel: ${var.oadp_channel}",
      "  name: redhat-oadp-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "  installPlanApproval: Automatic",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: openshift-adp",
      "  namespace: openshift-adp",
      "spec:",
      "  targetNamespaces:",
      "  - openshift-adp",
      "EOF",

      # Wait for operator
      "sleep 60",
      "oc wait --for=condition=Available deployment/oadp-operator-controller-manager -n openshift-adp --timeout=300s || true",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- S3 Credentials Secret ---
resource "null_resource" "oadp_s3_secret" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create cloud-credentials secret for Velero
      "cat <<EOF > /tmp/oadp-credentials",
      "[default]",
      "aws_access_key_id=${var.oadp_s3_access_key}",
      "aws_secret_access_key=${var.oadp_s3_secret_key}",
      "EOF",

      "oc create secret generic cloud-credentials -n openshift-adp \\",
      "  --from-file=cloud=/tmp/oadp-credentials \\",
      "  --dry-run=client -o yaml | oc apply -f -",

      "rm -f /tmp/oadp-credentials",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.oadp_operator]
}

# --- DataProtectionApplication ---
resource "null_resource" "dpa" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: oadp.openshift.io/v1alpha1",
      "kind: DataProtectionApplication",
      "metadata:",
      "  name: ${var.oadp_dpa_name}",
      "  namespace: openshift-adp",
      "spec:",
      "  configuration:",
      "    velero:",
      "      defaultPlugins:",
      "      - openshift",
      "      - aws",
      "      - csi",
      "      - kubevirt",
      "    nodeAgent:",
      "      enable: true",
      "      uploaderType: kopia",
      "  backupLocations:",
      "  - velero:",
      "      provider: aws",
      "      default: true",
      "      objectStorage:",
      "        bucket: ${var.oadp_s3_bucket}",
      "        prefix: ${var.oadp_s3_prefix}",
      "      config:",
      "        s3Url: ${var.oadp_s3_endpoint}",
      "        s3ForcePathStyle: \"true\"",
      "        region: ${var.oadp_s3_region}",
      "        insecureSkipTLSVerify: \"${var.oadp_s3_insecure_skip_tls}\"",
      "        profile: default",
      "      credential:",
      "        name: cloud-credentials",
      "        key: cloud",
      "  snapshotLocations:",
      "  - velero:",
      "      provider: aws",
      "      config:",
      "        region: ${var.oadp_s3_region}",
      "        profile: default",
      "EOF",

      # Wait for DPA to be reconciled
      "sleep 30",
      "oc wait --for=condition=Reconciled dpa/${var.oadp_dpa_name} -n openshift-adp --timeout=300s || true",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.oadp_s3_secret]
}

# --- Default Backup Schedule ---
resource "null_resource" "backup_schedule" {
  count = var.enable_backup_schedule ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: velero.io/v1",
      "kind: Schedule",
      "metadata:",
      "  name: ${var.backup_schedule_name}",
      "  namespace: openshift-adp",
      "spec:",
      "  schedule: '${var.backup_schedule_cron}'",
      "  template:",
      "    includedNamespaces: ${jsonencode(var.backup_included_namespaces)}",
      "    ttl: ${var.backup_ttl}",
      "    storageLocation: ${var.oadp_dpa_name}-1",
      "    defaultVolumesToFsBackup: ${var.backup_volumes_fs}",
      "    csiSnapshotTimeout: ${var.backup_csi_snapshot_timeout}",
      "EOF",

      "echo 'Backup schedule created: ${var.backup_schedule_name}'",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.dpa]
}
