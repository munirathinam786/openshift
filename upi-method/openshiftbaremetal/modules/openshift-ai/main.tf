# =============================================================================
# Module: Red Hat OpenShift AI (RHOAI) + DataScienceCluster
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "oai_components" {
  type = object({
    dashboard            = optional(string, "Managed")
    workbenches          = optional(string, "Managed")
    datasciencepipelines = optional(string, "Managed")
    modelmeshserving     = optional(string, "Managed")
    kserve               = optional(string, "Managed")
    codeflare            = optional(string, "Managed")
    ray                  = optional(string, "Managed")
    trustyai             = optional(string, "Managed")
  })
}
variable "enable_nim" { type = bool }
variable "ngc_api_key" {
  type      = string
  sensitive = true
}

resource "null_resource" "openshift_ai_operator" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # --- OpenShift Pipelines (Tekton) — prerequisite for DS Pipelines ---
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: openshift-pipelines-operator",
      "  namespace: openshift-operators",
      "spec:",
      "  channel: latest",
      "  installPlanApproval: Automatic",
      "  name: openshift-pipelines-operator-rh",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for Pipelines operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-operators 2>/dev/null | grep pipelines | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # --- OpenShift AI Operator ---
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: redhat-ods-operator",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: rhods-operator",
      "  namespace: redhat-ods-operator",
      "spec: {}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: rhods-operator",
      "  namespace: redhat-ods-operator",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: rhods-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for RHOAI operator
      "echo 'Waiting for OpenShift AI operator...'",
      "for i in $(seq 1 90); do",
      "  oc get csv -n redhat-ods-operator 2>/dev/null | grep rhods | grep -q Succeeded && break",
      "  sleep 10",
      "done",
    ]
  }
}

# --- Create DataScienceCluster ---
resource "null_resource" "datasciencecluster" {
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
      "apiVersion: datasciencecluster.opendatahub.io/v1",
      "kind: DataScienceCluster",
      "metadata:",
      "  name: default-dsc",
      "spec:",
      "  components:",
      "    dashboard:",
      "      managementState: ${var.oai_components.dashboard}",
      "    workbenches:",
      "      managementState: ${var.oai_components.workbenches}",
      "    datasciencepipelines:",
      "      managementState: ${var.oai_components.datasciencepipelines}",
      "    modelmeshserving:",
      "      managementState: ${var.oai_components.modelmeshserving}",
      "    kserve:",
      "      managementState: ${var.oai_components.kserve}",
      "    codeflare:",
      "      managementState: ${var.oai_components.codeflare}",
      "    ray:",
      "      managementState: ${var.oai_components.ray}",
      "    trustyai:",
      "      managementState: ${var.oai_components.trustyai}",
      "EOF",

      # Wait for DSC to be ready
      "echo 'Waiting for DataScienceCluster to be ready...'",
      "for i in $(seq 1 90); do",
      "  READY=$(oc get datasciencecluster default-dsc -o jsonpath='{.status.conditions[?(@.type==\"Available\")].status}' 2>/dev/null)",
      "  [ \"$READY\" = \"True\" ] && echo 'DataScienceCluster is ready' && break",
      "  sleep 10",
      "done",

      # Verify namespaces
      "echo '--- OpenShift AI Namespaces ---'",
      "oc get ns | grep -E 'redhat-ods|rhods'",
    ]
  }

  depends_on = [null_resource.openshift_ai_operator]
}

# --- Enable NVIDIA NIM ---
resource "null_resource" "enable_nim" {
  count = var.enable_nim ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Patch OdhDashboardConfig to enable NIM
      "oc patch odhdashboardconfig odh-dashboard-config -n redhat-ods-applications --type merge -p '{\"spec\":{\"disableNIMModelServing\":false}}'",

      # Create NGC secret in redhat-ods-applications for NIM
      "oc create secret generic nvidia-nim-secrets -n redhat-ods-applications --from-literal=NGC_API_KEY='${var.ngc_api_key}' --dry-run=client -o yaml | oc apply -f -",

      "echo 'NVIDIA NIM integration enabled'",
    ]
  }

  depends_on = [null_resource.datasciencecluster]
}
