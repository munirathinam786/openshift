# Agent Builder Factory — variables.tf (IPI DR Secondary)

All input variables for the Agent Builder Factory platform. Organized by functional area: bastion connection, platform configuration, database credentials, LLM settings (cloud + local), authentication, and GitHub integration.

## Source Code

```hcl
# Author: Sathishkumar Munirathinam
# Agent Builder Factory — Variables

# ==============================================================================
# Bastion / Cluster Connection
# ==============================================================================

variable "bastion_host" {
  description = "IP address or hostname of the bastion node with oc/kubectl access"
  type        = string
}

variable "bastion_user" {
  description = "SSH user for bastion connection"
  type        = string
  default     = "kni"
}

variable "bastion_ssh_private_key_file" {
  description = "Path to SSH private key for bastion connection"
  type        = string
  default     = "~/.ssh/id_ed25519"
}

variable "cluster_name" {
  description = "OpenShift cluster name"
  type        = string
}

variable "base_domain" {
  description = "Base DNS domain for the cluster"
  type        = string
}

# ==============================================================================
# Agent Builder Platform
# ==============================================================================

variable "agent_builder_namespace" {
  description = "Kubernetes namespace for the Agent Builder platform"
  type        = string
  default     = "agent-builder"
}

variable "agent_builder_subdomain" {
  description = "Subdomain prefix for Agent Builder routes (e.g., 'agent-builder' creates agent-builder.apps.cluster.domain)"
  type        = string
  default     = "agent-builder"
}

variable "container_registry" {
  description = "Container registry URL for Agent Builder images (e.g., quay-host:8443/agent-builder)"
  type        = string
}

variable "image_tag" {
  description = "Container image tag for all Agent Builder services"
  type        = string
  default     = "latest"
}

variable "storage_class" {
  description = "Kubernetes StorageClass for persistent volumes (e.g., ocs-storagecluster-ceph-rbd)"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}

# ==============================================================================
# PostgreSQL
# ==============================================================================

variable "postgres_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "postgres_storage_size" {
  description = "PostgreSQL PVC storage size"
  type        = string
  default     = "50Gi"
}

# ==============================================================================
# MongoDB
# ==============================================================================

variable "mongodb_root_password" {
  description = "MongoDB root password"
  type        = string
  sensitive   = true
}

variable "mongodb_storage_size" {
  description = "MongoDB PVC storage size"
  type        = string
  default     = "50Gi"
}

# ==============================================================================
# Redis
# ==============================================================================

variable "redis_password" {
  description = "Redis authentication password"
  type        = string
  sensitive   = true
}

variable "redis_storage_size" {
  description = "Redis PVC storage size"
  type        = string
  default     = "10Gi"
}

# ==============================================================================
# LiteLLM — Multi-Model LLM Gateway
# ==============================================================================

variable "litellm_master_key" {
  description = "LiteLLM master API key for gateway access"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude models (optional if using local LLM only)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint URL (optional)"
  type        = string
  default     = ""
}

variable "azure_openai_key" {
  description = "Azure OpenAI API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

# ==============================================================================
# Ollama — Local LLM (In-Cluster)
# ==============================================================================

variable "enable_ollama" {
  description = "Deploy Ollama for local LLM inference (Llama3) on the OpenShift cluster"
  type        = bool
  default     = true
}

variable "ollama_model" {
  description = "Ollama model to pull and serve (e.g., llama3, llama3:70b, mistral, codellama)"
  type        = string
  default     = "llama3"
}

variable "ollama_storage_size" {
  description = "PVC storage size for Ollama model data"
  type        = string
  default     = "100Gi"
}

variable "ollama_gpu_enabled" {
  description = "Enable GPU allocation for Ollama (requires NVIDIA GPU Operator)"
  type        = bool
  default     = false
}

variable "ollama_gpu_limit" {
  description = "Number of NVIDIA GPUs to allocate to Ollama"
  type        = number
  default     = 1
}

variable "ollama_memory_limit" {
  description = "Memory limit for Ollama container"
  type        = string
  default     = "16Gi"
}

variable "ollama_cpu_limit" {
  description = "CPU limit for Ollama container"
  type        = string
  default     = "8"
}

# ==============================================================================
# Local LLM — Laptop / External Ollama
# ==============================================================================

variable "enable_local_llm_laptop" {
  description = "Enable connecting to a local LLM running on a laptop (Ollama endpoint reachable from cluster)"
  type        = bool
  default     = false
}

variable "local_llm_laptop_url" {
  description = "URL of the Ollama instance running on a laptop (e.g., http://192.168.1.100:11434)"
  type        = string
  default     = ""
}

# ==============================================================================
# Temporal
# ==============================================================================

variable "temporal_workers_replicas" {
  description = "Number of Temporal Worker replicas"
  type        = number
  default     = 2
}

# ==============================================================================
# Authentication (OIDC)
# ==============================================================================

variable "oidc_authority" {
  description = "OIDC authority URL (e.g., Okta issuer URL)"
  type        = string
  default     = ""
}

variable "oidc_client_id" {
  description = "OIDC client ID for authentication"
  type        = string
  default     = ""
}

# ==============================================================================
# GitHub Integration
# ==============================================================================

variable "github_token" {
  description = "GitHub personal access token for agent repository operations"
  type        = string
  sensitive   = true
  default     = ""
}
```
