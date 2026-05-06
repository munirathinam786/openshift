output "generated_assets_dir" {
  description = "Directory containing the rendered ROSA helper scripts and inventories."
  value       = local.assets_dir
}

output "vpc_id" {
  description = "Customer VPC used by ROSA workers and endpoints."
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnets used for NAT and optional internet-facing ALBs."
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnets passed to the ROSA cluster create command."
  value       = module.networking.private_subnet_ids
}

output "additional_compute_security_group_id" {
  description = "Additional compute security group rendered for the ROSA cluster command."
  value       = module.networking.cluster_security_group_id
}

output "endpoint_inventory" {
  description = "Resolved VPC endpoint IDs and DNS references."
  value       = module.vpc_endpoints.endpoint_inventory
}

output "rosa_preflight_script" {
  description = "Script that validates AWS and ROSA CLI prerequisites."
  value       = module.rosa_automation.preflight_script_file
}

output "rosa_create_script" {
  description = "Script that creates the ROSA cluster in auto mode."
  value       = module.rosa_automation.create_cluster_script_file
}

output "route53_helper_script" {
  description = "Optional helper script for Route 53 aliases once the cluster endpoints are known."
  value       = module.rosa_automation.route53_script_file
}

output "alb_policy_arn" {
  description = "IAM policy ARN used by the AWS load balancer controller assets."
  value       = module.alb_operator.policy_arn
}

output "alb_install_script" {
  description = "Script that creates the ALB controller role and installs the chart."
  value       = module.alb_operator.install_script_file
}

output "sample_alb_ingress_manifest" {
  description = "Sample ingress manifest that demonstrates ALB annotations for ROSA workloads."
  value       = module.alb_operator.example_ingress_file
}
