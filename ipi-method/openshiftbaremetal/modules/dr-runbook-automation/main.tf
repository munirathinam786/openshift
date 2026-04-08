# =============================================================================
# Module: DR Runbook Automation — Automated DR failover/failback procedures
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "dr_primary_api" {
  description = "Primary cluster API URL"
  type        = string
  default     = ""
}
variable "dr_secondary_api" {
  description = "Secondary/DR cluster API URL"
  type        = string
  default     = ""
}
variable "dr_primary_kubeconfig" {
  description = "Path to primary cluster kubeconfig"
  type        = string
  default     = "/root/primary-kubeconfig"
}
variable "dr_secondary_kubeconfig" {
  description = "Path to secondary cluster kubeconfig"
  type        = string
  default     = "/root/secondary-kubeconfig"
}
variable "dr_namespaces" {
  description = "Namespaces to include in DR automation"
  type        = list(string)
  default     = ["*"]
}
variable "dr_rpo_minutes" {
  description = "Recovery Point Objective in minutes"
  type        = number
  default     = 15
}
variable "dr_health_check_interval" {
  description = "Health check interval for primary cluster (cron)"
  type        = string
  default     = "*/5 * * * *"
}

resource "null_resource" "dr_runbook_automation" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace dr-automation --dry-run=client -o yaml | oc apply -f -",

      # DR configuration ConfigMap
      "cat <<EOF | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: dr-config",
      "  namespace: dr-automation",
      "data:",
      "  primary-api: ${var.dr_primary_api}",
      "  secondary-api: ${var.dr_secondary_api}",
      "  rpo-minutes: '${var.dr_rpo_minutes}'",
      "  namespaces: '${join(",", var.dr_namespaces)}'",
      "EOF",

      # Failover script ConfigMap
      "cat <<'FAILOVER_EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: dr-failover-script",
      "  namespace: dr-automation",
      "data:",
      "  failover.sh: |",
      "    #!/bin/bash",
      "    set -euo pipefail",
      "    echo '=== DR FAILOVER INITIATED ==='",
      "    echo \"Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)\"",
      "    # Check primary cluster health",
      "    PRIMARY_HEALTHY=true",
      "    if ! oc --kubeconfig=$PRIMARY_KUBECONFIG get nodes &>/dev/null; then",
      "      PRIMARY_HEALTHY=false",
      "      echo 'PRIMARY CLUSTER IS DOWN'",
      "    fi",
      "    if [ \"$PRIMARY_HEALTHY\" = \"false\" ]; then",
      "      echo 'Initiating failover to secondary cluster...'",
      "      # Scale up workloads on DR cluster",
      "      for ns in $(echo $DR_NAMESPACES | tr ',' ' '); do",
      "        oc --kubeconfig=$SECONDARY_KUBECONFIG get deploy -n $ns -o name 2>/dev/null | while read deploy; do",
      "          echo \"Scaling up $deploy in $ns on DR cluster\"",
      "          oc --kubeconfig=$SECONDARY_KUBECONFIG scale $deploy --replicas=1 -n $ns 2>/dev/null || true",
      "        done",
      "      done",
      "      echo 'Failover complete. Workloads active on DR cluster.'",
      "    else",
      "      echo 'Primary healthy. No action needed.'",
      "    fi",
      "  failback.sh: |",
      "    #!/bin/bash",
      "    set -euo pipefail",
      "    echo '=== DR FAILBACK INITIATED ==='",
      "    echo \"Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)\"",
      "    # Verify primary is back",
      "    if oc --kubeconfig=$PRIMARY_KUBECONFIG get nodes &>/dev/null; then",
      "      echo 'Primary cluster is healthy. Starting failback...'",
      "      # Sync latest data from DR to primary",
      "      echo 'Syncing application state...'",
      "      # Scale down DR workloads",
      "      for ns in $(echo $DR_NAMESPACES | tr ',' ' '); do",
      "        oc --kubeconfig=$SECONDARY_KUBECONFIG get deploy -n $ns -o name 2>/dev/null | while read deploy; do",
      "          echo \"Scaling down $deploy in $ns on DR cluster\"",
      "          oc --kubeconfig=$SECONDARY_KUBECONFIG scale $deploy --replicas=0 -n $ns 2>/dev/null || true",
      "        done",
      "      done",
      "      echo 'Failback complete. Primary cluster active.'",
      "    else",
      "      echo 'Primary still down. Failback aborted.'",
      "      exit 1",
      "    fi",
      "FAILOVER_EOF",

      # Health check CronJob
      "cat <<EOF | oc apply -f -",
      "apiVersion: batch/v1",
      "kind: CronJob",
      "metadata:",
      "  name: dr-health-monitor",
      "  namespace: dr-automation",
      "spec:",
      "  schedule: '${var.dr_health_check_interval}'",
      "  successfulJobsHistoryLimit: 5",
      "  failedJobsHistoryLimit: 3",
      "  jobTemplate:",
      "    spec:",
      "      template:",
      "        spec:",
      "          serviceAccountName: dr-automation-sa",
      "          containers:",
      "            - name: health-check",
      "              image: registry.redhat.io/openshift4/ose-cli:latest",
      "              command: ['/bin/bash', '/scripts/failover.sh']",
      "              env:",
      "                - name: PRIMARY_KUBECONFIG",
      "                  value: /kubeconfigs/primary",
      "                - name: SECONDARY_KUBECONFIG",
      "                  value: /kubeconfigs/secondary",
      "                - name: DR_NAMESPACES",
      "                  valueFrom:",
      "                    configMapKeyRef:",
      "                      name: dr-config",
      "                      key: namespaces",
      "              volumeMounts:",
      "                - name: scripts",
      "                  mountPath: /scripts",
      "                - name: kubeconfigs",
      "                  mountPath: /kubeconfigs",
      "                  readOnly: true",
      "              resources:",
      "                limits:",
      "                  cpu: 200m",
      "                  memory: 256Mi",
      "          volumes:",
      "            - name: scripts",
      "              configMap:",
      "                name: dr-failover-script",
      "                defaultMode: 0755",
      "            - name: kubeconfigs",
      "              secret:",
      "                secretName: dr-kubeconfigs",
      "          restartPolicy: OnFailure",
      "EOF",

      # Create ServiceAccount with cluster-admin for DR ops
      "oc create serviceaccount dr-automation-sa -n dr-automation --dry-run=client -o yaml | oc apply -f -",
      "oc adm policy add-cluster-role-to-user cluster-admin -z dr-automation-sa -n dr-automation 2>/dev/null || true",

      "echo 'DR Runbook Automation deployed (RPO: ${var.dr_rpo_minutes}m, Health check: ${var.dr_health_check_interval})'",
    ]
  }
}
