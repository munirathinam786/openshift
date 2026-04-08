# =============================================================================
# Module: etcd Backup CronJob
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "backup_schedule" { type = string }

resource "null_resource" "etcd_backup" {
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
      "  name: ocp-backup-etcd",
      "  labels:",
      "    openshift.io/cluster-monitoring: 'true'",
      "EOF",

      # Create ServiceAccount
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ServiceAccount",
      "metadata:",
      "  name: etcd-backup-sa",
      "  namespace: ocp-backup-etcd",
      "EOF",

      # Bind cluster-etcd-backup ClusterRole
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: rbac.authorization.k8s.io/v1",
      "kind: ClusterRoleBinding",
      "metadata:",
      "  name: etcd-backup-crb",
      "roleRef:",
      "  apiGroup: rbac.authorization.k8s.io",
      "  kind: ClusterRole",
      "  name: cluster-admin",
      "subjects:",
      "  - kind: ServiceAccount",
      "    name: etcd-backup-sa",
      "    namespace: ocp-backup-etcd",
      "EOF",

      # Grant privileged SCC
      "oc adm policy add-scc-to-user privileged -z etcd-backup-sa -n ocp-backup-etcd",

      # Create CronJob
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: batch/v1",
      "kind: CronJob",
      "metadata:",
      "  name: etcd-backup",
      "  namespace: ocp-backup-etcd",
      "spec:",
      "  schedule: '${var.backup_schedule}'",
      "  concurrencyPolicy: Forbid",
      "  successfulJobsHistoryLimit: 5",
      "  failedJobsHistoryLimit: 5",
      "  jobTemplate:",
      "    spec:",
      "      backoffLimit: 0",
      "      template:",
      "        spec:",
      "          serviceAccountName: etcd-backup-sa",
      "          hostNetwork: true",
      "          hostPID: true",
      "          nodeSelector:",
      "            node-role.kubernetes.io/master: ''",
      "          tolerations:",
      "            - operator: Exists",
      "          containers:",
      "            - name: etcd-backup",
      "              image: registry.redhat.io/openshift4/ose-tools-rhel8:latest",
      "              command:",
      "                - /bin/sh",
      "                - -c",
      "                - |",
      "                  chroot /host /usr/local/bin/cluster-backup.sh /home/core/backup",
      "                  find /host/home/core/backup -type f -ctime +2 -delete",
      "              securityContext:",
      "                privileged: true",
      "                runAsUser: 0",
      "              volumeMounts:",
      "                - name: host",
      "                  mountPath: /host",
      "          restartPolicy: Never",
      "          volumes:",
      "            - name: host",
      "              hostPath:",
      "                path: /",
      "                type: Directory",
      "EOF",

      "echo 'etcd backup CronJob created (schedule: ${var.backup_schedule})'",
    ]
  }
}
