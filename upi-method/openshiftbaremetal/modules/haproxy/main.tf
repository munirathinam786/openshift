# =============================================================================
# Module: HAProxy Load Balancer
# =============================================================================

variable "cluster_name" { type = string }
variable "base_domain" { type = string }
variable "api_vip" { type = string }
variable "ingress_vip" { type = string }
variable "bootstrap_ip" {
  description = "Bootstrap node IP for UPI HAProxy config"
  type        = string
  default     = ""
}
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
variable "haproxy_hosts" {
  type = list(object({
    host    = string
    user    = string
    ssh_key = string
  }))
}

locals {
  cluster_domain = "${var.cluster_name}.${var.base_domain}"
}

resource "local_file" "haproxy_config" {
  filename = "${path.module}/generated/haproxy.cfg"
  content = templatefile("${path.module}/templates/haproxy.cfg.tftpl", {
    cluster_domain = local.cluster_domain
    api_vip        = var.api_vip
    ingress_vip    = var.ingress_vip
    master_nodes   = var.master_nodes
    worker_nodes   = var.worker_nodes
  })
}

resource "null_resource" "deploy_haproxy" {
  for_each = { for idx, h in var.haproxy_hosts : idx => h }

  triggers = {
    config_hash = sha256(local_file.haproxy_config.content)
  }

  connection {
    type        = "ssh"
    host        = each.value.host
    user        = each.value.user
    private_key = file(each.value.ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "yum install -y haproxy || dnf install -y haproxy",
    ]
  }

  provisioner "file" {
    source      = local_file.haproxy_config.filename
    destination = "/etc/haproxy/haproxy.cfg"
  }

  provisioner "remote-exec" {
    inline = [
      "setsebool -P haproxy_connect_any=1",
      "systemctl enable --now haproxy",
      "systemctl restart haproxy",
    ]
  }
}
