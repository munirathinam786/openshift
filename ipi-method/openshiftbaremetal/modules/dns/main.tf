# =============================================================================
# Module: DNS Records — validates/generates DNS entries for OCP cluster
# =============================================================================

variable "cluster_name" { type = string }
variable "base_domain" { type = string }
variable "api_vip" { type = string }
variable "ingress_vip" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "dns_servers" { type = list(string) }
variable "master_nodes" {
  type = list(object({
    name = string
    ip   = string
  }))
}
variable "worker_nodes" {
  type = list(object({
    name = string
    ip   = string
  }))
}

locals {
  cluster_domain = "${var.cluster_name}.${var.base_domain}"
}

# Generate /etc/hosts-style reference for validation
resource "local_file" "dns_records" {
  filename = "${path.module}/generated/dns-records.txt"
  content  = <<-EOT
# =============================================================================
# Required DNS Records for ${local.cluster_domain}
# Configure these in your DNS server before running the OCP installer.
# =============================================================================

# --- API and Ingress VIPs ---
${var.api_vip}    api.${local.cluster_domain}
${var.ingress_vip}    *.apps.${local.cluster_domain}

# --- Master Nodes ---
%{for node in var.master_nodes~}
${node.ip}    ${node.name}.${local.cluster_domain}
%{endfor~}

# --- Worker Nodes ---
%{for node in var.worker_nodes~}
${node.ip}    ${node.name}.${local.cluster_domain}
%{endfor~}

# --- etcd SRV Records (_etcd-server-ssl._tcp.${local.cluster_domain}) ---
%{for i, node in var.master_nodes~}
# _etcd-server-ssl._tcp.${local.cluster_domain}  SRV 0 10 2380 etcd-${i}.${local.cluster_domain}
${node.ip}    etcd-${i}.${local.cluster_domain}
%{endfor~}
EOT
}

# Validate DNS resolution from bastion
resource "null_resource" "dns_validation" {
  triggers = {
    records_hash = sha256(local_file.dns_records.content)
  }

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "echo '--- Validating DNS resolution ---'",
      "dig +short api.${local.cluster_domain} @${var.dns_servers[0]} | grep -q '${var.api_vip}' && echo 'OK: api.${local.cluster_domain} -> ${var.api_vip}' || echo 'WARN: api.${local.cluster_domain} not resolving to ${var.api_vip}'",
      "dig +short *.apps.${local.cluster_domain} @${var.dns_servers[0]} | grep -q '${var.ingress_vip}' && echo 'OK: *.apps.${local.cluster_domain} -> ${var.ingress_vip}' || echo 'WARN: *.apps.${local.cluster_domain} not resolving to ${var.ingress_vip}'",
      "echo '--- DNS validation complete ---'",
    ]
  }
}
