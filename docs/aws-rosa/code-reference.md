# AWS ROSA Terraform Code Reference

<!-- markdownlint-disable MD024 -->

This page explains the Terraform implementation under the repository's `aws-rosa/` folder and includes the full source for every top-level Terraform file, the sample `terraform.tfvars`, the delivery pipeline, and each module entry point.

## Module relationship

![AWS ROSA Terraform Modules](../diagrams/aws-rosa/03-aws-rosa-terraform-modules.svg){: .drawio-diagram }

???+ note "Draw.io Source: AWS ROSA Terraform Modules"
    [:material-download: Download .drawio file](../diagrams/aws-rosa/03-aws-rosa-terraform-modules.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Root module structure

```text
aws-rosa/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── terraform.tfvars
├── azure-pipelines-rosa.yml
└── modules/
    ├── networking/
    ├── vpc-endpoints/
    ├── rosa-automation/
    └── alb-operator/
```

## `main.tf` orchestration

The root module composes the ROSA workflow in four parts:

- `networking` — creates the VPC, subnets, route tables, NAT, and security groups
- `vpc-endpoints` — creates AWS interface and gateway endpoints for private worker access
- `rosa-automation` — renders preflight, cluster create, Route 53, and delete scripts
- `alb-operator` — creates the IAM policy and install assets for ALB-backed ingress

This is not a placeholder layout with empty modules. The root module wires concrete Terraform resources together and emits executable operational assets for the pieces that must be driven by the ROSA CLI.

### Full source

```hcl
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
```

## `variables.tf`

The ROSA variables model AWS-specific concerns, including VPC layout, ROSA STS cluster settings, Route 53 integration, CLI paths, ALB defaults, and tagging.

### Full source

```hcl
variable "cluster_name" {
  description = "Short ROSA cluster name."
  type        = string
  default     = "rosa-prod"
}

variable "domain_prefix" {
  description = "Optional domain prefix for the ROSA cluster; defaults to cluster_name when empty."
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "AWS region for the ROSA deployment."
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID that owns the ROSA VPC and IAM objects."
  type        = string
}

variable "availability_zones" {
  description = "Availability zones used by the ROSA worker subnets."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "ROSA should use at least two availability zones."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the customer VPC."
  type        = string
  default     = "10.80.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs aligned to availability_zones."
  type        = list(string)
  default     = ["10.80.0.0/20", "10.80.16.0/20", "10.80.32.0/20"]

  validation {
    condition     = length(var.public_subnet_cidrs) == length(var.availability_zones)
    error_message = "public_subnet_cidrs must match the number of availability_zones."
  }
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs aligned to availability_zones."
  type        = list(string)
  default     = ["10.80.128.0/20", "10.80.144.0/20", "10.80.160.0/20"]

  validation {
    condition     = length(var.private_subnet_cidrs) == length(var.availability_zones)
    error_message = "private_subnet_cidrs must match the number of availability_zones."
  }
}

variable "enable_nat_gateways" {
  description = "If true, create one NAT gateway per public subnet."
  type        = bool
  default     = true
}

variable "allowed_cidrs" {
  description = "CIDRs allowed to reach the additional ROSA compute security group."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "interface_vpc_endpoints" {
  description = "AWS interface endpoints required by the ROSA worker VPC."
  type        = list(string)
  default = [
    "ec2",
    "elasticloadbalancing",
    "sts",
    "ecr.api",
    "ecr.dkr",
    "logs",
    "monitoring",
    "autoscaling",
    "route53",
    "servicequotas",
    "tagging",
  ]
}

variable "gateway_vpc_endpoints" {
  description = "AWS gateway endpoints required by the ROSA worker VPC."
  type        = list(string)
  default     = ["s3"]
}

variable "private_cluster" {
  description = "If true, the generated ROSA command uses a private cluster topology."
  type        = bool
  default     = false
}

variable "multi_az" {
  description = "If true, generate a multi-AZ ROSA cluster create command."
  type        = bool
  default     = true
}

variable "openshift_version" {
  description = "Desired OpenShift version for ROSA."
  type        = string
  default     = "4.17.15"
}

variable "compute_machine_type" {
  description = "AWS instance type for ROSA worker nodes."
  type        = string
  default     = "m5.xlarge"
}

variable "compute_replicas" {
  description = "Static worker replica count when autoscaling is disabled."
  type        = number
  default     = 3
}

variable "enable_autoscaling" {
  description = "If true, configure the generated ROSA command for autoscaling."
  type        = bool
  default     = false
}

variable "autoscaling_min_replicas" {
  description = "Minimum worker replicas when autoscaling is enabled."
  type        = number
  default     = 3
}

variable "autoscaling_max_replicas" {
  description = "Maximum worker replicas when autoscaling is enabled."
  type        = number
  default     = 6
}

variable "machine_cidr" {
  description = "Machine CIDR passed to ROSA. Defaults should match the VPC range."
  type        = string
  default     = "10.80.0.0/16"
}

variable "pod_cidr" {
  description = "Pod network CIDR passed to ROSA."
  type        = string
  default     = "10.128.0.0/14"
}

variable "service_cidr" {
  description = "Service network CIDR passed to ROSA."
  type        = string
  default     = "172.30.0.0/16"
}

variable "host_prefix" {
  description = "Pod host prefix for ROSA networking."
  type        = number
  default     = 23
}

variable "route53_zone_id" {
  description = "Optional Route 53 hosted zone ID used by the generated alias helper script."
  type        = string
  default     = ""
}

variable "route53_zone_name" {
  description = "Optional Route 53 hosted zone name for documentation and helper output."
  type        = string
  default     = ""
}

variable "rosa_cli_binary" {
  description = "Path or command name for the rosa CLI."
  type        = string
  default     = "rosa"
}

variable "aws_cli_binary" {
  description = "Path or command name for the AWS CLI."
  type        = string
  default     = "aws"
}

variable "oc_binary" {
  description = "Path or command name for the oc CLI."
  type        = string
  default     = "oc"
}

variable "jq_binary" {
  description = "Path or command name for jq."
  type        = string
  default     = "jq"
}

variable "helm_binary" {
  description = "Path or command name for helm."
  type        = string
  default     = "helm"
}

variable "ocm_token_env_var" {
  description = "Environment variable name containing the OCM token used by the rosa CLI."
  type        = string
  default     = "OCM_TOKEN"
}

variable "aws_profile" {
  description = "Optional AWS profile name exported in the generated scripts."
  type        = string
  default     = ""
}

variable "auto_execute_rosa" {
  description = "If true, Terraform runs the generated ROSA create script locally after rendering."
  type        = bool
  default     = false
}

variable "auto_execute_alb_setup" {
  description = "If true, Terraform runs the generated ALB install script locally after rendering."
  type        = bool
  default     = false
}

variable "skip_aws_provider_validation" {
  description = "Allows terraform validate to run without live AWS credential checks."
  type        = bool
  default     = true
}

variable "alb_operator_namespace" {
  description = "Namespace used for the AWS load balancer controller installation assets."
  type        = string
  default     = "aws-load-balancer-operator"
}

variable "alb_ingress_scheme" {
  description = "Default ALB ingress scheme written into the sample ingress manifest."
  type        = string
  default     = "internet-facing"
}

variable "additional_tags" {
  description = "Common tags applied to AWS resources."
  type        = map(string)
  default = {
    platform = "rosa"
  }
}
```

## `outputs.tf`

The outputs surface the infrastructure IDs and generated helper assets operators need after `terraform apply`.

### Full source

```hcl
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
```

## `versions.tf`

Provider and Terraform version constraints for the ROSA blueprint.

### Full source

```hcl
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}
```

## `terraform.tfvars`

Sample input values for the AWS ROSA deployment. Replace the example account, DNS, and credential-related values to match your environment.

### Full source

```hcl
cluster_name   = "rosa-prod"
domain_prefix  = "rosa-prod"
aws_region     = "us-east-1"
aws_account_id = "123456789012"

availability_zones = [
  "us-east-1a",
  "us-east-1b",
  "us-east-1c",
]

vpc_cidr = "10.80.0.0/16"

public_subnet_cidrs = [
  "10.80.0.0/20",
  "10.80.16.0/20",
  "10.80.32.0/20",
]

private_subnet_cidrs = [
  "10.80.128.0/20",
  "10.80.144.0/20",
  "10.80.160.0/20",
]

enable_nat_gateways = true
allowed_cidrs       = ["10.0.0.0/8", "203.0.113.0/24"]

private_cluster          = false
multi_az                 = true
openshift_version        = "4.17.15"
compute_machine_type     = "m5.xlarge"
compute_replicas         = 3
enable_autoscaling       = false
autoscaling_min_replicas = 3
autoscaling_max_replicas = 6

machine_cidr = "10.80.0.0/16"
pod_cidr     = "10.128.0.0/14"
service_cidr = "172.30.0.0/16"
host_prefix  = 23

route53_zone_id   = "Z0123456789EXAMPLE"
route53_zone_name = "example.awsrosa.lab"

aws_profile            = "rosa-admin"
auto_execute_rosa      = false
auto_execute_alb_setup = false

additional_tags = {
  environment = "production"
  owner       = "platform-team"
  cost-center = "openshift"
}
```

## `azure-pipelines-rosa.yml`

Azure DevOps pipeline for validating the ROSA Terraform, rendering helper assets, and optionally executing the generated ROSA and ALB scripts.

### Full source

```yaml
# =============================================================================
# Azure DevOps Pipeline — OpenShift on AWS (ROSA)
# Builds the AWS network foundation, VPC endpoints, and renders ROSA / ALB assets
# =============================================================================

trigger:
  branches:
    include:
      - develop
  paths:
    include:
      - aws-rosa/**
      - docs/aws-rosa/**
      - docs/diagrams/aws-rosa/**

parameters:
  - name: terraformAction
    displayName: Terraform Action
    type: string
    default: plan
    values:
      - plan
      - apply
      - destroy

  - name: runRosaCli
    displayName: Execute generated ROSA scripts
    type: boolean
    default: false

  - name: runAlbSetup
    displayName: Execute generated ALB setup script
    type: boolean
    default: false

variables:
  - name: TF_IN_AUTOMATION
    value: "true"
  - name: TF_INPUT
    value: "false"
  - name: WORKING_DIR
    value: "aws-rosa"

stages:
  - stage: Validate
    displayName: Validate ROSA Terraform
    jobs:
      - job: FmtValidate
        pool:
          name: self-hosted-linux
        steps:
          - checkout: self
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: latest
          - script: |
              cd $(WORKING_DIR)
              terraform init -input=false
              terraform fmt -check -recursive
              terraform validate
            displayName: terraform init / fmt / validate

  - stage: Provision
    displayName: Render ROSA and ALB assets
    dependsOn: Validate
    jobs:
      - job: TerraformApply
        pool:
          name: self-hosted-linux
        steps:
          - checkout: self
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: latest
          - script: |
              cd $(WORKING_DIR)
              terraform init -input=false
              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                -var auto_execute_rosa=${{ lower(parameters.runRosaCli) }} \
                -var auto_execute_alb_setup=${{ lower(parameters.runAlbSetup) }} \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" != "plan" ]; then echo "-auto-approve"; fi)
            displayName: terraform plan/apply/destroy
            env:
              AWS_ACCESS_KEY_ID: $(aws-access-key-id)
              AWS_SECRET_ACCESS_KEY: $(aws-secret-access-key)
              AWS_SESSION_TOKEN: $(aws-session-token)
              AWS_DEFAULT_REGION: $(aws-region)
              OCM_TOKEN: $(ocm-token)

  - stage: Summary
    displayName: ROSA summary
    dependsOn: Provision
    condition: always()
    jobs:
      - job: OutputSummary
        pool:
          name: self-hosted-linux
        steps:
          - checkout: none
          - script: |
              echo "ROSA Terraform workflow completed."
              echo "Review aws-rosa/generated for the preflight, cluster creation, Route 53, and ALB scripts."
              echo "If runRosaCli=false or runAlbSetup=false, execute the generated scripts manually once credentials and CLI tools are available."
            displayName: Print summary
```

## `modules/networking`

This module creates the AWS primitives ROSA depends on in the customer account: VPC, public/private subnets, internet gateway, route tables, optional NAT gateways, and the security groups used by worker nodes and interface endpoints.

### Full source

```hcl
variable "cluster_name" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "availability_zones" {
  type = list(string)
}

variable "vpc_cidr" {
  type = string
}

variable "public_subnet_cidrs" {
  type = list(string)
}

variable "private_subnet_cidrs" {
  type = list(string)
}

variable "enable_nat_gateways" {
  type = bool
}

variable "allowed_cidrs" {
  type = list(string)
}

variable "additional_tags" {
  type = map(string)
}

locals {
  common_tags = merge(var.additional_tags, { module = "networking" })
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-igw"
  })
}

resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name                     = "${var.cluster_name}-public-${count.index + 1}"
    "kubernetes.io/role/elb" = "1"
  })
}

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.private_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name                              = "${var.cluster_name}-private-${count.index + 1}"
    "kubernetes.io/role/internal-elb" = "1"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateways ? length(aws_subnet.public) : 0
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-nat-eip-${count.index + 1}"
  })
}

resource "aws_nat_gateway" "this" {
  count = var.enable_nat_gateways ? length(aws_subnet.public) : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-nat-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "private" {
  count = length(aws_subnet.private)

  vpc_id = aws_vpc.this.id

  dynamic "route" {
    for_each = var.enable_nat_gateways ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.this[count.index].id
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-private-rt-${count.index + 1}"
  })
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

resource "aws_security_group" "cluster" {
  name        = "${var.cluster_name}-compute"
  description = "Additional compute security group for ROSA worker nodes"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "OpenShift ingress and API"
    from_port   = 443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  ingress {
    description = "Machine config server"
    from_port   = 22623
    to_port     = 22623
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-compute-sg"
  })
}

resource "aws_security_group" "endpoints" {
  name        = "${var.cluster_name}-endpoints"
  description = "Security group for AWS interface endpoints used by ROSA workers"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTPS from the VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-endpoint-sg"
  })
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "private_route_table_ids" {
  value = aws_route_table.private[*].id
}

output "cluster_security_group_id" {
  value = aws_security_group.cluster.id
}

output "endpoint_security_group_id" {
  value = aws_security_group.endpoints.id
}

output "nat_gateway_ids" {
  value = aws_nat_gateway.this[*].id
}
```

## `modules/vpc-endpoints`

This module turns the ROSA network into a private-service-aware VPC by creating interface endpoints such as STS, EC2, ECR, ELB, and CloudWatch plus gateway endpoints such as S3.

### Full source

```hcl
variable "cluster_name" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "private_route_table_ids" {
  type = list(string)
}

variable "endpoint_security_group_id" {
  type = string
}

variable "interface_endpoint_services" {
  type = list(string)
}

variable "gateway_endpoint_services" {
  type = list(string)
}

variable "additional_tags" {
  type = map(string)
}

locals {
  common_tags = merge(var.additional_tags, { module = "vpc-endpoints" })
}

resource "aws_vpc_endpoint" "interface" {
  for_each = toset(var.interface_endpoint_services)

  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [var.endpoint_security_group_id]

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-${replace(each.value, ".", "-")}-endpoint"
  })
}

resource "aws_vpc_endpoint" "gateway" {
  for_each = toset(var.gateway_endpoint_services)

  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.private_route_table_ids

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-${replace(each.value, ".", "-")}-endpoint"
  })
}

output "endpoint_inventory" {
  value = {
    interface = {
      for name, endpoint in aws_vpc_endpoint.interface : name => {
        id        = endpoint.id
        dns_names = [for entry in endpoint.dns_entry : entry.dns_name]
      }
    }
    gateway = {
      for name, endpoint in aws_vpc_endpoint.gateway : name => {
        id = endpoint.id
      }
    }
  }
}
```

## `modules/rosa-automation`

This module renders the operational hand-off files under `aws-rosa/generated/<cluster>/`, including preflight, create, Route 53, delete, and summary assets. When `auto_execute_rosa=true`, Terraform can also execute the generated preflight and cluster creation scripts during apply.

### Full source

```hcl
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
```

## `modules/alb-operator`

This module adds the application ingress extension path by creating the AWS IAM policy, writing the policy JSON to disk, rendering `install-alb-operator.sh`, and rendering a sample `sample-alb-ingress.yaml` manifest.

### Full source

```hcl
variable "assets_dir" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "public_subnet_ids" {
  type = list(string)
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

variable "helm_binary" {
  type = string
}

variable "aws_profile" {
  type = string
}

variable "alb_operator_namespace" {
  type = string
}

variable "alb_ingress_scheme" {
  type = string
}

variable "auto_execute" {
  type = bool
}

variable "additional_tags" {
  type = map(string)
}

locals {
  aws_profile_export = trimspace(var.aws_profile) != "" ? "export AWS_PROFILE=${var.aws_profile}" : ""

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:RevokeSecurityGroupIngress",
          "ec2:CreateSecurityGroup",
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "ec2:DeleteSecurityGroup",
          "ec2:ModifyInstanceAttribute",
          "ec2:ModifyNetworkInterfaceAttribute",
          "ec2:CreateNetworkInterfacePermission",
          "elasticloadbalancing:*",
          "iam:CreateServiceLinkedRole",
          "cognito-idp:DescribeUserPoolClient",
          "acm:ListCertificates",
          "acm:DescribeCertificate",
          "acm:GetCertificate",
          "iam:ListServerCertificates",
          "iam:GetServerCertificate",
          "waf-regional:GetWebACL",
          "waf-regional:GetWebACLForResource",
          "waf-regional:AssociateWebACL",
          "waf-regional:DisassociateWebACL",
          "wafv2:GetWebACL",
          "wafv2:GetWebACLForResource",
          "wafv2:AssociateWebACL",
          "wafv2:DisassociateWebACL",
          "shield:GetSubscriptionState",
          "shield:DescribeProtection",
          "shield:CreateProtection",
          "shield:DeleteProtection",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          "tag:GetResources",
          "tag:TagResources"
        ]
        Resource = "*"
      }
    ]
  })

  install_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    ${local.aws_profile_export}
    export AWS_REGION="${var.aws_region}"

    for bin in "${var.aws_cli_binary}" "${var.rosa_cli_binary}" "${var.oc_binary}" "${var.jq_binary}" "${var.helm_binary}"; do
      command -v "$${bin}" >/dev/null 2>&1 || {
        echo "Required binary not found: $${bin}" >&2
        exit 1
      }
    done

    CLUSTER_JSON="$$(${var.rosa_cli_binary} describe cluster -c "${var.cluster_name}" -o json)"
    OIDC_ENDPOINT="$$(${var.jq_binary} -r '.aws.sts.oidc_endpoint_url // empty' <<<"$${CLUSTER_JSON}")"

    if [[ -z "$${OIDC_ENDPOINT}" ]]; then
      echo "Could not determine the ROSA OIDC endpoint. Ensure the cluster exists and STS is enabled." >&2
      exit 1
    fi

    OIDC_PROVIDER_HOST="$${OIDC_ENDPOINT#https://}"
    ROLE_NAME="${var.cluster_name}-alb-operator"
    ROLE_ARN="arn:aws:iam::${var.aws_account_id}:role/$${ROLE_NAME}"

    cat > /tmp/$${ROLE_NAME}-trust.json <<JSON
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::${var.aws_account_id}:oidc-provider/$${OIDC_PROVIDER_HOST}"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "$${OIDC_PROVIDER_HOST}:sub": "system:serviceaccount:${var.alb_operator_namespace}:aws-load-balancer-controller",
              "$${OIDC_PROVIDER_HOST}:aud": "sts.amazonaws.com"
            }
          }
        }
      ]
    }
JSON

    ${var.aws_cli_binary} iam create-role \
      --role-name "$${ROLE_NAME}" \
      --assume-role-policy-document file:///tmp/$${ROLE_NAME}-trust.json >/dev/null 2>&1 || true

    ${var.aws_cli_binary} iam attach-role-policy \
      --role-name "$${ROLE_NAME}" \
      --policy-arn "${aws_iam_policy.alb_operator.arn}" >/dev/null 2>&1 || true

    ${var.oc_binary} create namespace ${var.alb_operator_namespace} --dry-run=client -o yaml | ${var.oc_binary} apply -f -

    cat <<YAML | ${var.oc_binary} apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: aws-load-balancer-controller
  namespace: ${var.alb_operator_namespace}
  annotations:
    eks.amazonaws.com/role-arn: "$${ROLE_ARN}"
YAML

    ${var.helm_binary} repo add eks https://aws.github.io/eks-charts >/dev/null 2>&1 || true
    ${var.helm_binary} repo update >/dev/null 2>&1

    ${var.helm_binary} upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
      --namespace ${var.alb_operator_namespace} \
      --set clusterName=${var.cluster_name} \
      --set region=${var.aws_region} \
      --set vpcId=${var.vpc_id} \
      --set serviceAccount.create=false \
      --set serviceAccount.name=aws-load-balancer-controller

    echo "ALB controller installed. Apply the sample ingress manifest at ${var.assets_dir}/sample-alb-ingress.yaml after replacing the service name and certificate ARN."
  EOT

  example_ingress = <<-EOT
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: example-alb
      namespace: default
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: ${var.alb_ingress_scheme}
        alb.ingress.kubernetes.io/target-type: ip
        alb.ingress.kubernetes.io/subnets: ${join(",", var.public_subnet_ids)}
        alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
        alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:${var.aws_region}:${var.aws_account_id}:certificate/replace-me
    spec:
      rules:
        - host: app.replace-me.example.com
          http:
            paths:
              - path: /
                pathType: Prefix
                backend:
                  service:
                    name: replace-me-service
                    port:
                      number: 8080
  EOT
}

resource "aws_iam_policy" "alb_operator" {
  name        = "${var.cluster_name}-aws-load-balancer-controller"
  description = "Permissions used by the AWS load balancer controller in ROSA"
  policy      = local.policy_document

  tags = merge(var.additional_tags, {
    Name   = "${var.cluster_name}-alb-policy"
    module = "alb-operator"
  })
}

resource "local_file" "policy_json" {
  filename = "${var.assets_dir}/alb-iam-policy.json"
  content  = local.policy_document
}

resource "local_file" "install_script" {
  filename = "${var.assets_dir}/install-alb-operator.sh"
  content  = local.install_script
}

resource "local_file" "example_ingress" {
  filename = "${var.assets_dir}/sample-alb-ingress.yaml"
  content  = local.example_ingress
}

resource "null_resource" "execute_install" {
  triggers = {
    install = sha256(local.install_script)
    policy  = sha256(local.policy_document)
  }

  provisioner "local-exec" {
    command = var.auto_execute ? "chmod +x '${local_file.install_script.filename}' && '${local_file.install_script.filename}'" : "echo 'ALB assets rendered to ${var.assets_dir}; execution skipped by configuration.'"
  }
}

output "policy_arn" {
  value = aws_iam_policy.alb_operator.arn
}

output "install_script_file" {
  value = local_file.install_script.filename
}

output "example_ingress_file" {
  value = local_file.example_ingress.filename
}
```
