provider "aws" {
  region                      = var.aws_region
  skip_credentials_validation = var.skip_aws_provider_validation
  skip_metadata_api_check     = var.skip_aws_provider_validation
  skip_requesting_account_id  = var.skip_aws_provider_validation
}

locals {
  assets_dir         = "${path.module}/generated/${var.cluster_name}"
  effective_domain   = trimspace(var.domain_prefix) != "" ? var.domain_prefix : var.cluster_name
  common_tags        = merge(var.additional_tags, { Name = var.cluster_name, cluster = var.cluster_name })
  private_subnet_csv = join(",", module.networking.private_subnet_ids)
  public_subnet_csv  = join(",", module.networking.public_subnet_ids)
}

resource "null_resource" "assets_dir" {
  triggers = {
    assets_dir = local.assets_dir
  }

  provisioner "local-exec" {
    command = "mkdir -p '${local.assets_dir}'"
  }
}

module "networking" {
  source = "./modules/networking"

  cluster_name         = var.cluster_name
  aws_region           = var.aws_region
  availability_zones   = var.availability_zones
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  enable_nat_gateways  = var.enable_nat_gateways
  allowed_cidrs        = var.allowed_cidrs
  additional_tags      = local.common_tags
}

module "vpc_endpoints" {
  source = "./modules/vpc-endpoints"

  cluster_name                = var.cluster_name
  aws_region                  = var.aws_region
  vpc_id                      = module.networking.vpc_id
  private_subnet_ids          = module.networking.private_subnet_ids
  private_route_table_ids     = module.networking.private_route_table_ids
  endpoint_security_group_id  = module.networking.endpoint_security_group_id
  interface_endpoint_services = var.interface_vpc_endpoints
  gateway_endpoint_services   = var.gateway_vpc_endpoints
  additional_tags             = local.common_tags
}

module "rosa_automation" {
  source = "./modules/rosa-automation"

  assets_dir                            = local.assets_dir
  cluster_name                          = var.cluster_name
  domain_prefix                         = local.effective_domain
  aws_region                            = var.aws_region
  aws_account_id                        = var.aws_account_id
  private_subnet_ids                    = module.networking.private_subnet_ids
  public_subnet_ids                     = module.networking.public_subnet_ids
  machine_cidr                          = var.machine_cidr
  pod_cidr                              = var.pod_cidr
  service_cidr                          = var.service_cidr
  host_prefix                           = var.host_prefix
  openshift_version                     = var.openshift_version
  compute_machine_type                  = var.compute_machine_type
  compute_replicas                      = var.compute_replicas
  multi_az                              = var.multi_az
  private_cluster                       = var.private_cluster
  enable_autoscaling                    = var.enable_autoscaling
  autoscaling_min_replicas              = var.autoscaling_min_replicas
  autoscaling_max_replicas              = var.autoscaling_max_replicas
  additional_compute_security_group_ids = [module.networking.cluster_security_group_id]
  endpoint_inventory                    = module.vpc_endpoints.endpoint_inventory
  route53_zone_id                       = var.route53_zone_id
  route53_zone_name                     = var.route53_zone_name
  rosa_cli_binary                       = var.rosa_cli_binary
  aws_cli_binary                        = var.aws_cli_binary
  oc_binary                             = var.oc_binary
  jq_binary                             = var.jq_binary
  ocm_token_env_var                     = var.ocm_token_env_var
  aws_profile                           = var.aws_profile
  auto_execute                          = var.auto_execute_rosa

  depends_on = [null_resource.assets_dir]
}

module "alb_operator" {
  source = "./modules/alb-operator"

  assets_dir             = local.assets_dir
  cluster_name           = var.cluster_name
  aws_account_id         = var.aws_account_id
  aws_region             = var.aws_region
  vpc_id                 = module.networking.vpc_id
  private_subnet_ids     = module.networking.private_subnet_ids
  public_subnet_ids      = module.networking.public_subnet_ids
  rosa_cli_binary        = var.rosa_cli_binary
  aws_cli_binary         = var.aws_cli_binary
  oc_binary              = var.oc_binary
  jq_binary              = var.jq_binary
  helm_binary            = var.helm_binary
  aws_profile            = var.aws_profile
  alb_operator_namespace = var.alb_operator_namespace
  alb_ingress_scheme     = var.alb_ingress_scheme
  auto_execute           = var.auto_execute_alb_setup
  additional_tags        = local.common_tags

  depends_on = [null_resource.assets_dir]
}
