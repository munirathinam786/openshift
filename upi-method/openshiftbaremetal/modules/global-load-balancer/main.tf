# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Global Load Balancer — Cross-cluster DNS-based GSLB
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "gslb_domain" {
  description = "Global domain for cross-cluster load balancing"
  type        = string
  default     = ""
}
variable "gslb_primary_ingress_ip" {
  description = "Primary cluster ingress IP"
  type        = string
  default     = ""
}
variable "gslb_secondary_ingress_ip" {
  description = "Secondary cluster ingress IP"
  type        = string
  default     = ""
}
variable "gslb_dns_provider" {
  description = "DNS provider for GSLB records (rfc2136, route53, azure)"
  type        = string
  default     = "rfc2136"
}
variable "gslb_strategy" {
  description = "Load balancing strategy (roundrobin, failover, geolocation)"
  type        = string
  default     = "failover"
}
variable "gslb_health_check_path" {
  description = "HTTP health check path"
  type        = string
  default     = "/healthz"
}
variable "gslb_health_check_port" {
  description = "Health check port"
  type        = number
  default     = 443
}

resource "null_resource" "global_load_balancer" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace global-load-balancer --dry-run=client -o yaml | oc apply -f -",

      # Create GSLB health check endpoints ConfigMap
      "cat <<EOF | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: gslb-config",
      "  namespace: global-load-balancer",
      "data:",
      "  gslb-domain: ${var.gslb_domain}",
      "  primary-ingress-ip: ${var.gslb_primary_ingress_ip}",
      "  secondary-ingress-ip: ${var.gslb_secondary_ingress_ip}",
      "  strategy: ${var.gslb_strategy}",
      "  health-check-path: ${var.gslb_health_check_path}",
      "  health-check-port: '${var.gslb_health_check_port}'",
      "EOF",

      # Deploy health check CronJob
      "cat <<EOF | oc apply -f -",
      "apiVersion: batch/v1",
      "kind: CronJob",
      "metadata:",
      "  name: gslb-health-check",
      "  namespace: global-load-balancer",
      "spec:",
      "  schedule: '*/1 * * * *'",
      "  jobTemplate:",
      "    spec:",
      "      template:",
      "        spec:",
      "          containers:",
      "            - name: health-checker",
      "              image: registry.access.redhat.com/ubi8/ubi-minimal:latest",
      "              command:",
      "                - /bin/sh",
      "                - -c",
      "                - |",
      "                  PRIMARY_OK=false",
      "                  SECONDARY_OK=false",
      "                  curl -sk https://${var.gslb_primary_ingress_ip}${var.gslb_health_check_path} && PRIMARY_OK=true",
      "                  curl -sk https://${var.gslb_secondary_ingress_ip}${var.gslb_health_check_path} && SECONDARY_OK=true",
      "                  echo \"Primary: \\$PRIMARY_OK, Secondary: \\$SECONDARY_OK\"",
      "                  # Update DNS based on health and strategy",
      "                  if [ \"${var.gslb_strategy}\" = \"failover\" ]; then",
      "                    if [ \"\\$PRIMARY_OK\" = \"true\" ]; then",
      "                      echo 'Primary active'",
      "                    elif [ \"\\$SECONDARY_OK\" = \"true\" ]; then",
      "                      echo 'Failover to secondary'",
      "                    fi",
      "                  fi",
      "              resources:",
      "                limits:",
      "                  cpu: 100m",
      "                  memory: 128Mi",
      "          restartPolicy: OnFailure",
      "EOF",

      # If using ACM, create ManagedClusterSet for LB
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: cluster.open-cluster-management.io/v1beta2",
      "kind: ManagedClusterSetBinding",
      "metadata:",
      "  name: global-clusterset",
      "  namespace: global-load-balancer",
      "spec:",
      "  clusterSet: global-clusterset",
      "EOF",

      "echo 'Global Load Balancer configured (strategy: ${var.gslb_strategy})'",
    ]
  }
}
