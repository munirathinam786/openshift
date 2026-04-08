# =============================================================================
# OpenShift Pipelines (Tekton) Module — Variables
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

# ---- Pipelines Operator ----

variable "pipelines_channel" {
  description = "OpenShift Pipelines operator subscription channel"
  type        = string
  default     = "latest"
}

# ---- TektonConfig ----

variable "tekton_profile" {
  description = "TektonConfig profile (all, basic, lite)"
  type        = string
  default     = "all"
}

variable "tekton_api_fields" {
  description = "Tekton API fields stability level (stable, beta, alpha)"
  type        = string
  default     = "stable"
}

variable "enable_cluster_tasks" {
  description = "Install default ClusterTasks"
  type        = bool
  default     = true
}

variable "enable_pipeline_templates" {
  description = "Install pipeline templates"
  type        = bool
  default     = true
}

variable "enable_community_cluster_tasks" {
  description = "Install community ClusterTasks"
  type        = bool
  default     = false
}

variable "enable_pipelines_as_code" {
  description = "Enable Pipelines-as-Code (GitHub/GitLab webhook integration)"
  type        = bool
  default     = true
}

variable "pipeline_default_timeout" {
  description = "Default pipeline run timeout in minutes"
  type        = string
  default     = "60"
}

variable "pipeline_default_sa" {
  description = "Default service account for pipeline and trigger runs"
  type        = string
  default     = "pipeline"
}

# ---- Pipeline Namespaces ----

variable "pipeline_namespaces" {
  description = "List of namespaces to create and label for Tekton pipeline workloads"
  type        = list(string)
  default     = []
}

# ---- Resource Limits ----

variable "enable_pipeline_resource_limits" {
  description = "Apply LimitRange to the openshift-pipelines namespace"
  type        = bool
  default     = false
}

variable "pipeline_container_cpu_request" {
  description = "Default CPU request for pipeline containers"
  type        = string
  default     = "100m"
}

variable "pipeline_container_memory_request" {
  description = "Default memory request for pipeline containers"
  type        = string
  default     = "256Mi"
}

variable "pipeline_container_cpu_limit" {
  description = "Default CPU limit for pipeline containers"
  type        = string
  default     = "500m"
}

variable "pipeline_container_memory_limit" {
  description = "Default memory limit for pipeline containers"
  type        = string
  default     = "1Gi"
}

# ---- Pipelines-as-Code (webhook) ----

variable "pac_webhook_secret" {
  description = "Git provider personal access token for Pipelines-as-Code (leave empty to skip)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "pac_webhook_shared_secret" {
  description = "Shared webhook secret for Pipelines-as-Code"
  type        = string
  default     = ""
  sensitive   = true
}
