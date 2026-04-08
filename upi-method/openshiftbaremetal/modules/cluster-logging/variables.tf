# Author: Sathishkumar Munirathinam

variable "kubeconfig" {
  description = "Path to kubeconfig on bastion"
  type        = string
}

variable "bastion_host" {
  description = "Bastion hostname/IP"
  type        = string
}

variable "bastion_user" {
  description = "Bastion SSH user"
  type        = string
}

variable "bastion_ssh_key" {
  description = "Path to bastion SSH private key"
  type        = string
}

# --- Logging Configuration ---
variable "logging_channel" {
  description = "OLM subscription channel for Cluster Logging operator"
  type        = string
  default     = "stable-5.9"
}

variable "log_store_type" {
  description = "Log store backend: elasticsearch or lokistack"
  type        = string
  default     = "elasticsearch"
}

variable "log_retention_application" {
  description = "Application log retention period"
  type        = string
  default     = "7d"
}

variable "log_retention_infra" {
  description = "Infrastructure log retention period"
  type        = string
  default     = "7d"
}

variable "log_retention_audit" {
  description = "Audit log retention period"
  type        = string
  default     = "7d"
}

variable "elasticsearch_node_count" {
  description = "Number of Elasticsearch nodes"
  type        = number
  default     = 3
}

variable "log_storage_class" {
  description = "StorageClass for logging PVCs (use ODF: ocs-storagecluster-ceph-rbd)"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}

variable "log_storage_size" {
  description = "PVC size per Elasticsearch node"
  type        = string
  default     = "200Gi"
}

variable "elasticsearch_memory" {
  description = "Memory request per Elasticsearch node"
  type        = string
  default     = "8Gi"
}

# --- S3 Log Forwarding (ODF RGW / MinIO / AWS S3) ---
variable "enable_log_forwarding_s3" {
  description = "Enable forwarding logs to S3-compatible endpoint"
  type        = bool
  default     = false
}

variable "log_s3_endpoint" {
  description = "S3 endpoint URL for log forwarding (e.g., ODF RGW endpoint)"
  type        = string
  default     = ""
}

variable "log_s3_bucket" {
  description = "S3 bucket name for log storage"
  type        = string
  default     = "openshift-logs"
}

variable "log_s3_region" {
  description = "S3 region (use 'us-east-1' for ODF RGW)"
  type        = string
  default     = "us-east-1"
}

variable "log_s3_access_key" {
  description = "S3 access key for log forwarding"
  type        = string
  sensitive   = true
  default     = ""
}

variable "log_s3_secret_key" {
  description = "S3 secret key for log forwarding"
  type        = string
  sensitive   = true
  default     = ""
}
