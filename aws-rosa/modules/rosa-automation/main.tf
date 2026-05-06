variable "assets_dir" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "domain_prefix" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "machine_cidr" {
  type = string
}

variable "pod_cidr" {
  type = string
}

variable "service_cidr" {
  type = string
}

variable "host_prefix" {
  type = number
}

variable "openshift_version" {
  type = string
}

variable "compute_machine_type" {
  type = string
}

variable "compute_replicas" {
  type = number
}

variable "multi_az" {
  type = bool
}

variable "private_cluster" {
  type = bool
}

variable "enable_autoscaling" {
  type = bool
}

variable "autoscaling_min_replicas" {
  type = number
}

variable "autoscaling_max_replicas" {
  type = number
}

variable "additional_compute_security_group_ids" {
  type = list(string)
}

variable "endpoint_inventory" {
  type = any
}

variable "route53_zone_id" {
  type = string
}

variable "route53_zone_name" {
  type = string
}

variable "rosa_cli_binary" {
  type = string
}

variable "aws_cli_binary" {
  type = string
}

variable "oc_binary" {
  type = string
}

variable "jq_binary" {
  type = string
}

variable "ocm_token_env_var" {
  type = string
}

variable "aws_profile" {
  type = string
}

variable "auto_execute" {
  type = bool
}

locals {
  aws_profile_export = trimspace(var.aws_profile) != "" ? "export AWS_PROFILE=${var.aws_profile}" : ""
  private_flag       = var.private_cluster ? "--private" : ""
  multi_az_flag      = var.multi_az ? "--multi-az" : ""
  autoscaling_flags  = var.enable_autoscaling ? "--enable-autoscaling --min-replicas ${var.autoscaling_min_replicas} --max-replicas ${var.autoscaling_max_replicas}" : "--replicas ${var.compute_replicas}"
  sg_flags           = length(var.additional_compute_security_group_ids) > 0 ? "--additional-compute-security-group-ids ${join(",", var.additional_compute_security_group_ids)}" : ""
  route53_enabled    = trimspace(var.route53_zone_id) != ""

  preflight_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    ${local.aws_profile_export}
    export AWS_REGION="${var.aws_region}"
    export OCM_TOKEN_ENV_NAME="${var.ocm_token_env_var}"

    for bin in "${var.aws_cli_binary}" "${var.rosa_cli_binary}" "${var.oc_binary}" "${var.jq_binary}"; do
      command -v "$${bin}" >/dev/null 2>&1 || {
        echo "Required binary not found: $${bin}" >&2
        exit 1
      }
    done

    if [[ -z "$${!OCM_TOKEN_ENV_NAME:-}" ]]; then
      echo "Environment variable $${OCM_TOKEN_ENV_NAME} must contain a valid OCM token." >&2
      exit 1
    fi

    ${var.rosa_cli_binary} login --token "$${!OCM_TOKEN_ENV_NAME}"
    ${var.rosa_cli_binary} verify permissions
    ${var.rosa_cli_binary} verify quota

    echo "ROSA preflight completed for ${var.cluster_name} in ${var.aws_region}."
  EOT

  create_cluster_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    ${local.aws_profile_export}
    export AWS_REGION="${var.aws_region}"
    export OCM_TOKEN_ENV_NAME="${var.ocm_token_env_var}"

    if [[ -z "$${!OCM_TOKEN_ENV_NAME:-}" ]]; then
      echo "Environment variable $${OCM_TOKEN_ENV_NAME} must contain a valid OCM token." >&2
      exit 1
    fi

    ${var.rosa_cli_binary} login --token "$${!OCM_TOKEN_ENV_NAME}"

    ${var.rosa_cli_binary} create cluster \
      --cluster-name "${var.cluster_name}" \
      --sts \
      --mode auto \
      --yes \
      --region "${var.aws_region}" \
      --version "${var.openshift_version}" \
      --subnet-ids "${join(",", var.private_subnet_ids)}" \
      --machine-cidr "${var.machine_cidr}" \
      --service-cidr "${var.service_cidr}" \
      --pod-cidr "${var.pod_cidr}" \
      --host-prefix ${var.host_prefix} \
      --compute-machine-type "${var.compute_machine_type}" \
      --domain-prefix "${var.domain_prefix}" \
      ${local.private_flag} \
      ${local.multi_az_flag} \
      ${local.autoscaling_flags} \
      ${local.sg_flags}

    echo "Cluster creation requested. Use the commands below to track progress:"
    echo "  ${var.rosa_cli_binary} logs install -c ${var.cluster_name} --watch"
    echo "  ${var.rosa_cli_binary} describe cluster -c ${var.cluster_name}"
  EOT

  route53_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    ${local.aws_profile_export}

    if [[ -z "${var.route53_zone_id}" ]]; then
      echo "route53_zone_id is empty; no Route 53 changes are configured for this cluster."
      exit 0
    fi

    API_LB_DNS="$${API_LB_DNS:-replace-me-api-lb.example.amazonaws.com}"
    APPS_LB_DNS="$${APPS_LB_DNS:-replace-me-apps-lb.example.amazonaws.com}"

    cat > /tmp/${var.cluster_name}-route53-alias.json <<JSON
    {
      "Comment": "ROSA aliases for ${var.cluster_name}",
      "Changes": [
        {
          "Action": "UPSERT",
          "ResourceRecordSet": {
            "Name": "api.${var.domain_prefix}.${var.route53_zone_name}",
            "Type": "CNAME",
            "TTL": 60,
            "ResourceRecords": [{ "Value": "$${API_LB_DNS}" }]
          }
        },
        {
          "Action": "UPSERT",
          "ResourceRecordSet": {
            "Name": "*.apps.${var.domain_prefix}.${var.route53_zone_name}",
            "Type": "CNAME",
            "TTL": 60,
            "ResourceRecords": [{ "Value": "$${APPS_LB_DNS}" }]
          }
        }
      ]
    }
JSON

    ${var.aws_cli_binary} route53 change-resource-record-sets \
      --hosted-zone-id "${var.route53_zone_id}" \
      --change-batch file:///tmp/${var.cluster_name}-route53-alias.json
  EOT

  delete_cluster_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    ${local.aws_profile_export}
    export OCM_TOKEN_ENV_NAME="${var.ocm_token_env_var}"

    if [[ -z "$${!OCM_TOKEN_ENV_NAME:-}" ]]; then
      echo "Environment variable $${OCM_TOKEN_ENV_NAME} must contain a valid OCM token." >&2
      exit 1
    fi

    ${var.rosa_cli_binary} login --token "$${!OCM_TOKEN_ENV_NAME}"
    ${var.rosa_cli_binary} delete cluster -c "${var.cluster_name}" --yes
  EOT

  environment_summary = <<-EOT
    # ROSA environment summary — ${var.cluster_name}

    - AWS account: `${var.aws_account_id}`
    - AWS region: `${var.aws_region}`
    - Private subnets: `${join(", ", var.private_subnet_ids)}`
    - Public subnets: `${join(", ", var.public_subnet_ids)}`
    - Machine CIDR: `${var.machine_cidr}`
    - Pod CIDR: `${var.pod_cidr}`
    - Service CIDR: `${var.service_cidr}`
    - Private cluster: `${var.private_cluster}`
    - Multi-AZ: `${var.multi_az}`
    - Compute type: `${var.compute_machine_type}`
    - Route 53 zone ID: `${var.route53_zone_id}`

    ## Required interface endpoints

    `${jsonencode(var.endpoint_inventory)}`
  EOT
}

resource "local_file" "preflight" {
  filename = "${var.assets_dir}/rosa-preflight-checks.sh"
  content  = local.preflight_script
}

resource "local_file" "create_cluster" {
  filename = "${var.assets_dir}/create-rosa-cluster.sh"
  content  = local.create_cluster_script
}

resource "local_file" "route53" {
  filename = "${var.assets_dir}/configure-route53-aliases.sh"
  content  = local.route53_script
}

resource "local_file" "delete_cluster" {
  filename = "${var.assets_dir}/delete-rosa-cluster.sh"
  content  = local.delete_cluster_script
}

resource "local_file" "environment_summary" {
  filename = "${var.assets_dir}/rosa-environment.md"
  content  = local.environment_summary
}

resource "null_resource" "execute_create" {
  triggers = {
    preflight = sha256(local.preflight_script)
    create    = sha256(local.create_cluster_script)
  }

  provisioner "local-exec" {
    command = var.auto_execute ? "chmod +x '${local_file.preflight.filename}' '${local_file.create_cluster.filename}' && '${local_file.preflight.filename}' && '${local_file.create_cluster.filename}'" : "echo 'ROSA scripts rendered to ${var.assets_dir}; execution skipped by configuration.'"
  }
}

output "preflight_script_file" {
  value = local_file.preflight.filename
}

output "create_cluster_script_file" {
  value = local_file.create_cluster.filename
}

output "route53_script_file" {
  value = local_file.route53.filename
}
