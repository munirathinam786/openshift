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

# --- OADP Configuration ---
variable "oadp_channel" {
  description = "OLM subscription channel for OADP operator"
  type        = string
  default     = "stable-1.6"
}

variable "oadp_dpa_name" {
  description = "DataProtectionApplication CR name"
  type        = string
  default     = "velero-dpa"
}

# --- S3 Backup Storage Location ---
variable "oadp_s3_endpoint" {
  description = "S3 endpoint URL (ODF RGW, MinIO, AWS S3)"
  type        = string
}

variable "oadp_s3_bucket" {
  description = "S3 bucket name for backups"
  type        = string
  default     = "openshift-backups"
}

variable "oadp_s3_prefix" {
  description = "S3 key prefix (folder) for backup data"
  type        = string
  default     = "velero"
}

variable "oadp_s3_region" {
  description = "S3 region (use 'us-east-1' for ODF RGW)"
  type        = string
  default     = "us-east-1"
}

variable "oadp_s3_access_key" {
  description = "S3 access key"
  type        = string
  sensitive   = true
}

variable "oadp_s3_secret_key" {
  description = "S3 secret key"
  type        = string
  sensitive   = true
}

variable "oadp_s3_insecure_skip_tls" {
  description = "Skip TLS verification for S3 endpoint"
  type        = string
  default     = "false"
}

# --- Backup Schedule ---
variable "enable_backup_schedule" {
  description = "Create a default backup schedule"
  type        = bool
  default     = true
}

variable "backup_schedule_name" {
  description = "Name for the default backup schedule"
  type        = string
  default     = "daily-backup"
}

variable "backup_schedule_cron" {
  description = "Cron expression for backup schedule"
  type        = string
  default     = "0 2 * * *"
}

variable "backup_included_namespaces" {
  description = "Namespaces to include in scheduled backups"
  type        = list(string)
  default     = ["*"]
}

variable "backup_ttl" {
  description = "Backup retention TTL"
  type        = string
  default     = "720h0m0s"
}

variable "backup_volumes_fs" {
  description = "Use filesystem backup for volumes"
  type        = bool
  default     = false
}

variable "backup_csi_snapshot_timeout" {
  description = "Timeout for CSI volume snapshots"
  type        = string
  default     = "10m0s"
}
