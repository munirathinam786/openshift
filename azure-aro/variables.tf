variable "cluster_name" {
  description = "Short ARO cluster name."
  type        = string
  default     = "aro-prod"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,30}$", var.cluster_name))
    error_message = "cluster_name must be 3-30 characters and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "location" {
  description = "Azure region for the ARO deployment."
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Azure resource group that hosts the ARO cluster resource and network foundation."
  type        = string
  default     = "aro-prod-rg"
}

variable "managed_resource_group_name" {
  description = "Optional managed resource group name created by ARO for cluster-managed Azure resources."
  type        = string
  default     = ""
}

variable "vnet_name" {
  description = "Optional virtual network name. Defaults to <cluster_name>-vnet when empty."
  type        = string
  default     = ""
}

variable "control_plane_subnet_name" {
  description = "Subnet name used by the ARO control plane."
  type        = string
  default     = "control-plane-subnet"
}

variable "worker_subnet_name" {
  description = "Subnet name used by ARO worker nodes."
  type        = string
  default     = "worker-subnet"
}

variable "vnet_cidr" {
  description = "CIDR block for the ARO virtual network."
  type        = string
  default     = "10.90.0.0/22"
}

variable "control_plane_subnet_cidr" {
  description = "CIDR block for the control-plane subnet. Must be /27 or larger."
  type        = string
  default     = "10.90.0.0/23"

  validation {
    condition     = can(cidrhost(var.control_plane_subnet_cidr, 0)) && tonumber(split("/", var.control_plane_subnet_cidr)[1]) <= 27
    error_message = "control_plane_subnet_cidr must be a valid CIDR with a prefix length of /27 or larger."
  }
}

variable "worker_subnet_cidr" {
  description = "CIDR block for the worker subnet. Must be /27 or larger."
  type        = string
  default     = "10.90.2.0/23"

  validation {
    condition     = can(cidrhost(var.worker_subnet_cidr, 0)) && tonumber(split("/", var.worker_subnet_cidr)[1]) <= 27
    error_message = "worker_subnet_cidr must be a valid CIDR with a prefix length of /27 or larger."
  }
}

variable "cluster_domain" {
  description = "Custom domain for the ARO cluster, for example aro.example.com."
  type        = string
  default     = "aro.example.com"

  validation {
    condition     = can(regex("^[a-z0-9.-]+$", var.cluster_domain))
    error_message = "cluster_domain must contain only lowercase letters, numbers, dots, and hyphens."
  }
}

variable "openshift_version" {
  description = "Desired OpenShift version for ARO. Use az aro get-versions --location <region> to confirm availability."
  type        = string
  default     = "4.17.27"
}

variable "pod_cidr" {
  description = "Pod network CIDR used by OpenShift SDN / OVN."
  type        = string
  default     = "10.128.0.0/14"

  validation {
    condition     = can(cidrhost(var.pod_cidr, 0))
    error_message = "pod_cidr must be a valid CIDR block."
  }
}

variable "service_cidr" {
  description = "Service network CIDR used by OpenShift."
  type        = string
  default     = "172.30.0.0/16"

  validation {
    condition     = can(cidrhost(var.service_cidr, 0))
    error_message = "service_cidr must be a valid CIDR block."
  }
}

variable "master_vm_size" {
  description = "VM size used by ARO control-plane nodes."
  type        = string
  default     = "Standard_D8s_v5"
}

variable "worker_vm_size" {
  description = "VM size used by ARO worker nodes."
  type        = string
  default     = "Standard_D4s_v5"
}

variable "worker_disk_size_gb" {
  description = "OS disk size in GB for worker nodes."
  type        = number
  default     = 128
}

variable "worker_node_count" {
  description = "Initial worker node count created with the ARO cluster."
  type        = number
  default     = 3

  validation {
    condition     = var.worker_node_count >= 3 && var.worker_node_count <= 50
    error_message = "worker_node_count must be between 3 and 50 for initial ARO creation."
  }
}

variable "api_visibility" {
  description = "API server visibility. Supported values are Public or Private."
  type        = string
  default     = "Public"

  validation {
    condition     = contains(["Public", "Private"], var.api_visibility)
    error_message = "api_visibility must be either Public or Private."
  }
}

variable "ingress_visibility" {
  description = "Ingress visibility. Supported values are Public or Private."
  type        = string
  default     = "Public"

  validation {
    condition     = contains(["Public", "Private"], var.ingress_visibility)
    error_message = "ingress_visibility must be either Public or Private."
  }
}

variable "outbound_type" {
  description = "ARO outbound routing method. Supported values are LoadBalancer or UserDefinedRouting."
  type        = string
  default     = "LoadBalancer"

  validation {
    condition     = contains(["LoadBalancer", "UserDefinedRouting"], var.outbound_type)
    error_message = "outbound_type must be either LoadBalancer or UserDefinedRouting."
  }
}

variable "preconfigured_network_security_group_enabled" {
  description = "Whether preconfigured NSGs are used on the ARO subnets."
  type        = bool
  default     = false
}

variable "fips_enabled" {
  description = "Whether FIPS validated cryptographic modules are enabled for the cluster."
  type        = bool
  default     = false
}

variable "master_encryption_at_host_enabled" {
  description = "Whether host-based encryption is enabled for control-plane VMs."
  type        = bool
  default     = false
}

variable "worker_encryption_at_host_enabled" {
  description = "Whether host-based encryption is enabled for worker VMs."
  type        = bool
  default     = false
}

variable "pull_secret" {
  description = "Optional Red Hat pull secret content. Prefer secure variables rather than inline values."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "pull_secret_file" {
  description = "Optional path to a local Red Hat pull secret file used when pull_secret is not set."
  type        = string
  default     = ""
}

variable "create_service_principal" {
  description = "If true, Terraform creates a dedicated Microsoft Entra application and service principal for ARO."
  type        = bool
  default     = true
}

variable "existing_service_principal_client_id" {
  description = "Existing service principal client ID used when create_service_principal is false."
  type        = string
  default     = ""

  validation {
    condition     = var.create_service_principal || trimspace(var.existing_service_principal_client_id) != ""
    error_message = "existing_service_principal_client_id must be set when create_service_principal is false."
  }
}

variable "existing_service_principal_client_secret" {
  description = "Existing service principal client secret used when create_service_principal is false."
  type        = string
  default     = ""
  sensitive   = true

  validation {
    condition     = var.create_service_principal || trimspace(var.existing_service_principal_client_secret) != ""
    error_message = "existing_service_principal_client_secret must be set when create_service_principal is false."
  }
}

variable "dns_zone_name" {
  description = "Optional Azure DNS zone name for helper script generation."
  type        = string
  default     = ""
}

variable "dns_resource_group_name" {
  description = "Optional Azure resource group that contains the Azure DNS zone."
  type        = string
  default     = ""
}

variable "azure_cli_binary" {
  description = "Path or command name for the Azure CLI."
  type        = string
  default     = "az"
}

variable "oc_binary" {
  description = "Path or command name for the OpenShift oc CLI."
  type        = string
  default     = "oc"
}

variable "kubeconfig_path" {
  description = "Optional path for the generated admin kubeconfig file. Defaults to the generated assets folder."
  type        = string
  default     = ""
}

variable "auto_fetch_admin_kubeconfig" {
  description = "If true, run the generated preflight and admin kubeconfig helper scripts after cluster creation."
  type        = bool
  default     = false
}

variable "additional_tags" {
  description = "Additional tags applied to Azure resources created by this blueprint."
  type        = map(string)
  default     = {}
}
