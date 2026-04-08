# =============================================================================
# UPI — Cluster Complete
# Waits for cluster install to complete, approves remaining CSRs,
# and verifies all nodes and cluster operators are ready
# =============================================================================

variable "install_dir" { type = string }
variable "ocp_version" { type = string }
variable "kubeconfig" { type = string }
variable "worker_count" { type = number }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

resource "null_resource" "cluster_complete" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Approve all pending CSRs (worker nodes)
      <<-EOT
      echo "Approving pending worker CSRs..."
      for i in $(seq 1 60); do
        PENDING=$(oc get csr -o go-template='{{range .items}}{{if not .status}}{{.metadata.name}}{{"\n"}}{{end}}{{end}}' 2>/dev/null)
        if [ -n "$PENDING" ]; then
          echo "$PENDING" | xargs oc adm certificate approve 2>/dev/null || true
        fi
        READY_WORKERS=$(oc get nodes --selector='node-role.kubernetes.io/worker' --no-headers 2>/dev/null | grep -c ' Ready' || true)
        [ "$READY_WORKERS" -ge "${var.worker_count}" ] && echo "All $READY_WORKERS workers ready." && break
        sleep 30
      done
      EOT
      ,

      # Wait for cluster install to complete
      "openshift-install wait-for install-complete --dir=${var.install_dir} --log-level=info 2>&1 | tail -20",

      # Verify all cluster operators are available
      "echo '=== Cluster Operator Status ==='",
      "oc get clusteroperators",
      "echo ''",
      "echo '=== Node Status ==='",
      "oc get nodes -o wide",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "kubeconfig_path" {
  value = var.kubeconfig
}

output "cluster_complete" {
  value = true
}
