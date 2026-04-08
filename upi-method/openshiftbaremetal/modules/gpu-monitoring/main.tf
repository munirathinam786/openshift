# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: NVIDIA DCGM Exporter Dashboard (GPU Monitoring)
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

resource "null_resource" "gpu_monitoring" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Download DCGM exporter dashboard JSON
      "curl -sL https://raw.githubusercontent.com/NVIDIA/dcgm-exporter/main/grafana/dcgm-exporter-dashboard.json -o /tmp/dcgm-exporter-dashboard.json",

      # Create ConfigMap from dashboard JSON
      "oc create configmap nvidia-dcgm-exporter-dashboard -n openshift-config-managed --from-file=dcgm-exporter-dashboard.json=/tmp/dcgm-exporter-dashboard.json --dry-run=client -o yaml | oc apply -f -",

      # Label for OCP console Admin perspective
      "oc label configmap nvidia-dcgm-exporter-dashboard -n openshift-config-managed 'console.openshift.io/dashboard=true' --overwrite",

      # Label for OCP console Developer perspective
      "oc label configmap nvidia-dcgm-exporter-dashboard -n openshift-config-managed 'console.openshift.io/odc-dashboard=true' --overwrite",

      "rm -f /tmp/dcgm-exporter-dashboard.json",
      "echo 'NVIDIA DCGM Exporter Dashboard installed — view in Observe > Dashboards'",
    ]
  }
}
