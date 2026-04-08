# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Alertmanager Config — Alert Routing (PagerDuty, Slack, Email)
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "alertmanager_slack_webhook_url" {
  description = "Slack incoming webhook URL for alerts"
  type        = string
  default     = ""
  sensitive   = true
}
variable "alertmanager_slack_channel" {
  description = "Slack channel for alerts"
  type        = string
  default     = "#ocp-alerts"
}
variable "alertmanager_pagerduty_key" {
  description = "PagerDuty integration key"
  type        = string
  default     = ""
  sensitive   = true
}
variable "alertmanager_email_to" {
  description = "Email address for critical alerts"
  type        = string
  default     = ""
}
variable "alertmanager_email_from" {
  description = "Sender email for alerts"
  type        = string
  default     = "alertmanager@openshift.local"
}
variable "alertmanager_smtp_host" {
  description = "SMTP relay host:port"
  type        = string
  default     = ""
}
variable "alertmanager_group_wait" {
  description = "Time to buffer alerts before sending"
  type        = string
  default     = "30s"
}
variable "alertmanager_group_interval" {
  description = "Time between alert group notifications"
  type        = string
  default     = "5m"
}
variable "alertmanager_repeat_interval" {
  description = "Time before re-alerting"
  type        = string
  default     = "4h"
}

resource "null_resource" "alertmanager_config" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Build alertmanager config
      "cat <<'ALERTCFG' > /tmp/alertmanager.yaml",
      "global:",
      "  resolve_timeout: 5m",
      var.alertmanager_smtp_host != "" ? "  smtp_smarthost: '${var.alertmanager_smtp_host}'" : "",
      var.alertmanager_smtp_host != "" ? "  smtp_from: '${var.alertmanager_email_from}'" : "",
      var.alertmanager_smtp_host != "" ? "  smtp_require_tls: false" : "",
      "route:",
      "  group_by: ['namespace', 'alertname']",
      "  group_wait: ${var.alertmanager_group_wait}",
      "  group_interval: ${var.alertmanager_group_interval}",
      "  repeat_interval: ${var.alertmanager_repeat_interval}",
      "  receiver: default-receiver",
      "  routes:",
      "    - matchers:",
      "        - severity = critical",
      "      receiver: critical-receiver",
      "    - matchers:",
      "        - severity = warning",
      "      receiver: warning-receiver",
      "receivers:",
      "  - name: default-receiver",
      var.alertmanager_slack_webhook_url != "" ? "    slack_configs:" : "",
      var.alertmanager_slack_webhook_url != "" ? "      - api_url: '${var.alertmanager_slack_webhook_url}'" : "",
      var.alertmanager_slack_webhook_url != "" ? "        channel: '${var.alertmanager_slack_channel}'" : "",
      var.alertmanager_slack_webhook_url != "" ? "        send_resolved: true" : "",
      "  - name: critical-receiver",
      var.alertmanager_pagerduty_key != "" ? "    pagerduty_configs:" : "",
      var.alertmanager_pagerduty_key != "" ? "      - service_key: '${var.alertmanager_pagerduty_key}'" : "",
      var.alertmanager_email_to != "" ? "    email_configs:" : "",
      var.alertmanager_email_to != "" ? "      - to: '${var.alertmanager_email_to}'" : "",
      var.alertmanager_email_to != "" ? "        send_resolved: true" : "",
      "  - name: warning-receiver",
      var.alertmanager_slack_webhook_url != "" ? "    slack_configs:" : "",
      var.alertmanager_slack_webhook_url != "" ? "      - api_url: '${var.alertmanager_slack_webhook_url}'" : "",
      var.alertmanager_slack_webhook_url != "" ? "        channel: '${var.alertmanager_slack_channel}'" : "",
      var.alertmanager_slack_webhook_url != "" ? "        send_resolved: true" : "",
      "ALERTCFG",

      # Apply as secret in openshift-monitoring
      "oc create secret generic alertmanager-main -n openshift-monitoring --from-file=alertmanager.yaml=/tmp/alertmanager.yaml --dry-run=client -o yaml | oc apply -f -",
      "rm -f /tmp/alertmanager.yaml",

      "echo 'Alertmanager configuration applied'",
    ]
  }
}
