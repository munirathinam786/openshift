cluster_name                = "aro-prod"
location                    = "eastus"
resource_group_name         = "aro-prod-rg"
managed_resource_group_name = "aro-prod-managed-rg"
cluster_domain              = "aro.example.com"
openshift_version           = "4.17.27"

vnet_cidr                 = "10.90.0.0/22"
control_plane_subnet_cidr = "10.90.0.0/23"
worker_subnet_cidr        = "10.90.2.0/23"

pod_cidr     = "10.128.0.0/14"
service_cidr = "172.30.0.0/16"

master_vm_size      = "Standard_D8s_v5"
worker_vm_size      = "Standard_D4s_v5"
worker_disk_size_gb = 128
worker_node_count   = 3

api_visibility     = "Public"
ingress_visibility = "Public"
outbound_type      = "LoadBalancer"

create_service_principal = true

# Prefer providing the pull secret through a secure variable or protected file path.
# pull_secret_file = "/secure/path/pull-secret.txt"

# Optional Azure DNS helper configuration.
# dns_zone_name           = "example.com"
# dns_resource_group_name = "shared-dns-rg"

additional_tags = {
  environment = "production"
  workload    = "aro"
}
