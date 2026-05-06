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
