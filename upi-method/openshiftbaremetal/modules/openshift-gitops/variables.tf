# =============================================================================
# OpenShift GitOps (Argo CD) Module — Variables
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

# ---- GitOps Operator ----

variable "gitops_channel" {
  description = "OpenShift GitOps operator subscription channel"
  type        = string
  default     = "latest"
}

# ---- ArgoCD Instance ----

variable "argocd_ha_enabled" {
  description = "Enable HA for ArgoCD components"
  type        = bool
  default     = false
}

variable "argocd_server_autoscale" {
  description = "Enable autoscaling for ArgoCD server"
  type        = bool
  default     = false
}

variable "argocd_server_cpu_request" {
  description = "CPU request for ArgoCD server"
  type        = string
  default     = "250m"
}

variable "argocd_server_memory_request" {
  description = "Memory request for ArgoCD server"
  type        = string
  default     = "256Mi"
}

variable "argocd_server_cpu_limit" {
  description = "CPU limit for ArgoCD server"
  type        = string
  default     = "500m"
}

variable "argocd_server_memory_limit" {
  description = "Memory limit for ArgoCD server"
  type        = string
  default     = "512Mi"
}

variable "argocd_controller_cpu_request" {
  description = "CPU request for ArgoCD application controller"
  type        = string
  default     = "500m"
}

variable "argocd_controller_memory_request" {
  description = "Memory request for ArgoCD application controller"
  type        = string
  default     = "512Mi"
}

variable "argocd_controller_cpu_limit" {
  description = "CPU limit for ArgoCD application controller"
  type        = string
  default     = "2"
}

variable "argocd_controller_memory_limit" {
  description = "Memory limit for ArgoCD application controller"
  type        = string
  default     = "2Gi"
}

# ---- RBAC ----

variable "argocd_cluster_admin" {
  description = "Grant cluster-admin to ArgoCD application-controller SA"
  type        = bool
  default     = true
}

variable "argocd_rbac_default_policy" {
  description = "Default RBAC policy for ArgoCD (role:readonly or empty)"
  type        = string
  default     = "role:readonly"
}

variable "argocd_rbac_policy" {
  description = "ArgoCD RBAC policy CSV (multi-line string)"
  type        = string
  default     = <<-EOT
    g, system:cluster-admins, role:admin
    g, ocp-cluster-admins, role:admin
  EOT
}

# ---- Managed Namespaces ----

variable "argocd_managed_namespaces" {
  description = "List of namespaces managed by ArgoCD (will be created and labelled)"
  type        = list(string)
  default     = []
}

# ---- Repository ----

variable "argocd_repo_url" {
  description = "Git repository URL for ArgoCD (leave empty to skip)"
  type        = string
  default     = ""
}

variable "argocd_repo_token" {
  description = "Git PAT / token for ArgoCD repo authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "argocd_repo_insecure" {
  description = "Skip TLS verification for the Git repository"
  type        = bool
  default     = false
}
