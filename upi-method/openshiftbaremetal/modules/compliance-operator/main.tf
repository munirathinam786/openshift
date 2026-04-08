# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Compliance Operator — OpenSCAP Scanning
# Deploys CIS, NIST, PCI-DSS compliance profiles with auto-remediation
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "compliance_profiles" {
  description = "List of compliance profiles to deploy (e.g., cis, moderate, pci-dss)"
  type        = list(string)
  default     = ["cis"]
}
variable "auto_remediate" {
  description = "Enable automatic remediation of failed compliance checks"
  type        = bool
  default     = false
}
variable "scan_schedule" {
  description = "CronJob schedule for periodic compliance scans"
  type        = string
  default     = "0 1 * * *"
}

resource "null_resource" "compliance_operator" {
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
      "  name: openshift-compliance",
      "  labels:",
      "    openshift.io/cluster-monitoring: 'true'",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: compliance-operator",
      "  namespace: openshift-compliance",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-compliance",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: compliance-operator",
      "  namespace: openshift-compliance",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: compliance-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator
      "echo 'Waiting for Compliance Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-compliance 2>/dev/null | grep compliance | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Wait for ProfileBundles to be ready
      "sleep 30",
      "oc wait --for=condition=Ready profilebundle/ocp4 -n openshift-compliance --timeout=300s || true",
      "oc wait --for=condition=Ready profilebundle/rhcos4 -n openshift-compliance --timeout=300s || true",

      "echo 'Compliance Operator installed'",
    ]
  }
}

# --- Create ScanSettingBinding for each profile ---
resource "null_resource" "compliance_scan_bindings" {
  count = length(var.compliance_profiles)

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create ScanSetting with schedule
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: compliance.openshift.io/v1alpha1",
      "kind: ScanSetting",
      "metadata:",
      "  name: periodic-scan-${var.compliance_profiles[count.index]}",
      "  namespace: openshift-compliance",
      "schedule: '${var.scan_schedule}'",
      "rawResultStorage:",
      "  size: 2Gi",
      "  rotation: 5",
      "roles:",
      "  - worker",
      "  - master",
      "autoApplyRemediations: ${var.auto_remediate}",
      "EOF",

      # Create ScanSettingBinding
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: compliance.openshift.io/v1alpha1",
      "kind: ScanSettingBinding",
      "metadata:",
      "  name: ${var.compliance_profiles[count.index]}-binding",
      "  namespace: openshift-compliance",
      "profiles:",
      "  - name: ocp4-${var.compliance_profiles[count.index]}",
      "    kind: Profile",
      "    apiGroup: compliance.openshift.io/v1alpha1",
      "  - name: rhcos4-${var.compliance_profiles[count.index]}",
      "    kind: Profile",
      "    apiGroup: compliance.openshift.io/v1alpha1",
      "settingsRef:",
      "  name: periodic-scan-${var.compliance_profiles[count.index]}",
      "  kind: ScanSetting",
      "  apiGroup: compliance.openshift.io/v1alpha1",
      "EOF",

      "echo 'Compliance profile ${var.compliance_profiles[count.index]} bound'",
    ]
  }

  depends_on = [null_resource.compliance_operator]
}
