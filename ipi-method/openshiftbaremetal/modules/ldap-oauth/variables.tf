# Author: Sathishkumar Munirathinam

# =============================================================================
# LDAP/OAuth Module — Variables
# =============================================================================

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

# ---- LDAP Connection ----

variable "ldap_provider_name" {
  description = "Display name for the LDAP identity provider"
  type        = string
  default     = "LDAP"
}

variable "ldap_url" {
  description = "LDAP URL (ldap:// or ldaps://host:port/baseDN?attribute?scope?filter)"
  type        = string
}

variable "ldap_bind_dn" {
  description = "LDAP bind DN (service account for LDAP queries)"
  type        = string
}

variable "ldap_bind_password" {
  description = "LDAP bind password"
  type        = string
  sensitive   = true
}

variable "ldap_ca_cert_file" {
  description = "Path to LDAP CA certificate on bastion (leave empty for insecure/public CA)"
  type        = string
  default     = ""
}

variable "ldap_insecure" {
  description = "Allow insecure LDAP connections (only when ldap_ca_cert_file is empty)"
  type        = string
  default     = "false"
}

# ---- LDAP Attribute Mapping ----

variable "ldap_attr_id" {
  description = "LDAP attribute to use as the identity (unique ID)"
  type        = string
  default     = "dn"
}

variable "ldap_attr_email" {
  description = "LDAP attribute for user email"
  type        = string
  default     = "mail"
}

variable "ldap_attr_name" {
  description = "LDAP attribute for user display name"
  type        = string
  default     = "cn"
}

variable "ldap_attr_preferred_username" {
  description = "LDAP attribute for preferred username (login name)"
  type        = string
  default     = "sAMAccountName"
}

# ---- LDAP Group Sync ----

variable "enable_ldap_group_sync" {
  description = "Enable automatic LDAP group synchronisation via CronJob"
  type        = bool
  default     = true
}

variable "ldap_user_base_dn" {
  description = "Base DN for user searches"
  type        = string
  default     = ""
}

variable "ldap_group_base_dn" {
  description = "Base DN for group searches"
  type        = string
  default     = ""
}

variable "ldap_group_filter" {
  description = "LDAP filter for group queries"
  type        = string
  default     = "(objectClass=group)"
}

variable "ldap_group_membership_attr" {
  description = "LDAP attribute listing group members"
  type        = string
  default     = "member"
}

variable "ldap_group_sync_schedule" {
  description = "Cron schedule for LDAP group sync CronJob"
  type        = string
  default     = "*/30 * * * *"
}

# ---- RBAC Bindings ----

variable "ldap_group_role_bindings" {
  description = "List of LDAP group -> ClusterRole bindings"
  type = list(object({
    group_name   = string
    cluster_role = string
  }))
  default = []
}

# ---- kubeadmin removal ----

variable "disable_kubeadmin" {
  description = "Delete the kubeadmin secret after LDAP is configured (irreversible)"
  type        = bool
  default     = false
}
