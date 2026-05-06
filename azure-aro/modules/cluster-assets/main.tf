variable "assets_dir" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "managed_resource_group_name" {
  type = string
}

variable "cluster_domain" {
  type = string
}

variable "console_url" {
  type = string
}

variable "api_server_url" {
  type = string
}

variable "api_server_ip" {
  type = string
}

variable "ingress_ip" {
  type = string
}

variable "dns_zone_name" {
  type = string
}

variable "dns_resource_group_name" {
  type = string
}

variable "azure_cli_binary" {
  type = string
}

variable "oc_binary" {
  type = string
}

variable "kubeconfig_path" {
  type = string
}

variable "auto_fetch_admin_kubeconfig" {
  type = bool
}

locals {
  effective_kubeconfig_path = trimspace(var.kubeconfig_path) != "" ? var.kubeconfig_path : "${var.assets_dir}/kubeconfig"
  dns_enabled               = trimspace(var.dns_zone_name) != "" && trimspace(var.dns_resource_group_name) != ""

  preflight_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    for bin in "${var.azure_cli_binary}" "${var.oc_binary}"; do
      command -v "$${bin}" >/dev/null 2>&1 || {
        echo "Required binary not found: $${bin}" >&2
        exit 1
      }
    done

    ${var.azure_cli_binary} account show >/dev/null

    echo "Checking Azure resource provider registration state..."
    ${var.azure_cli_binary} provider show --namespace Microsoft.RedHatOpenShift --query registrationState -o tsv
    ${var.azure_cli_binary} provider show --namespace Microsoft.Compute --query registrationState -o tsv
    ${var.azure_cli_binary} provider show --namespace Microsoft.Storage --query registrationState -o tsv
    ${var.azure_cli_binary} provider show --namespace Microsoft.Authorization --query registrationState -o tsv

    echo "Available ARO versions in ${var.location}:"
    ${var.azure_cli_binary} aro get-versions --location "${var.location}" -o table || true
  EOT

  kubeconfig_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    mkdir -p "$(dirname "${local.effective_kubeconfig_path}")"

    ${var.azure_cli_binary} aro get-admin-kubeconfig \
      --resource-group "${var.resource_group_name}" \
      --name "${var.cluster_name}" \
      --file "${local.effective_kubeconfig_path}"

    echo "Kubeconfig written to ${local.effective_kubeconfig_path}"
    echo "Console URL: ${var.console_url}"
    echo "API server : ${var.api_server_url}"
  EOT

  dns_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    if [[ -z "${var.dns_zone_name}" || -z "${var.dns_resource_group_name}" ]]; then
      echo "dns_zone_name or dns_resource_group_name is empty; Azure DNS changes are not configured for this cluster."
      exit 0
    fi

    ${var.azure_cli_binary} network dns record-set a create \
      --resource-group "${var.dns_resource_group_name}" \
      --zone-name "${var.dns_zone_name}" \
      --name "api.${var.cluster_domain}" >/dev/null 2>&1 || true

    ${var.azure_cli_binary} network dns record-set a add-record \
      --resource-group "${var.dns_resource_group_name}" \
      --zone-name "${var.dns_zone_name}" \
      --record-set-name "api.${var.cluster_domain}" \
      --ipv4-address "${var.api_server_ip}"

    ${var.azure_cli_binary} network dns record-set a create \
      --resource-group "${var.dns_resource_group_name}" \
      --zone-name "${var.dns_zone_name}" \
      --name "*.apps.${var.cluster_domain}" >/dev/null 2>&1 || true

    ${var.azure_cli_binary} network dns record-set a add-record \
      --resource-group "${var.dns_resource_group_name}" \
      --zone-name "${var.dns_zone_name}" \
      --record-set-name "*.apps.${var.cluster_domain}" \
      --ipv4-address "${var.ingress_ip}"
  EOT

  delete_cluster_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    ${var.azure_cli_binary} aro delete \
      --resource-group "${var.resource_group_name}" \
      --name "${var.cluster_name}" \
      --yes
  EOT

  environment_summary = <<-EOT
    # ARO environment summary — ${var.cluster_name}

    - Azure location: `${var.location}`
    - Resource group: `${var.resource_group_name}`
    - Managed resource group: `${var.managed_resource_group_name}`
    - Cluster domain: `${var.cluster_domain}`
    - Console URL: `${var.console_url}`
    - API server URL: `${var.api_server_url}`
    - API server IP: `${var.api_server_ip}`
    - Ingress IP: `${var.ingress_ip}`
    - Azure DNS zone: `${var.dns_zone_name}`
    - Azure DNS resource group: `${var.dns_resource_group_name}`
    - Admin kubeconfig path: `${local.effective_kubeconfig_path}`
  EOT
}

resource "local_file" "preflight" {
  filename = "${var.assets_dir}/aro-preflight-checks.sh"
  content  = local.preflight_script
}

resource "local_file" "kubeconfig" {
  filename = "${var.assets_dir}/get-admin-kubeconfig.sh"
  content  = local.kubeconfig_script
}

resource "local_file" "dns" {
  filename = "${var.assets_dir}/configure-azure-dns-records.sh"
  content  = local.dns_script
}

resource "local_file" "delete_cluster" {
  filename = "${var.assets_dir}/delete-aro-cluster.sh"
  content  = local.delete_cluster_script
}

resource "local_file" "environment_summary" {
  filename = "${var.assets_dir}/aro-environment.md"
  content  = local.environment_summary
}

resource "null_resource" "fetch_admin_kubeconfig" {
  triggers = {
    preflight  = sha256(local.preflight_script)
    kubeconfig = sha256(local.kubeconfig_script)
  }

  provisioner "local-exec" {
    command = var.auto_fetch_admin_kubeconfig ? "chmod +x '${local_file.preflight.filename}' '${local_file.kubeconfig.filename}' && '${local_file.preflight.filename}' && '${local_file.kubeconfig.filename}'" : "echo 'ARO helper assets rendered to ${var.assets_dir}; execution skipped by configuration.'"
  }
}

output "preflight_script_file" {
  value = local_file.preflight.filename
}

output "kubeconfig_script_file" {
  value = local_file.kubeconfig.filename
}

output "dns_script_file" {
  value = local_file.dns.filename
}
