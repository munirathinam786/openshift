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
