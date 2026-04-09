# Author: Sathishkumar Munirathinam
# Agent Builder Factory — terraform.tfvars
# Customize values below for your environment

# ==============================================================================
# Bastion / Cluster Connection
# ==============================================================================

bastion_host                 = "10.142.41.10"
bastion_user                 = "kni"
bastion_ssh_private_key_file = "~/.ssh/id_ed25519"
cluster_name                 = "ocp-ai"
base_domain                  = "example.com"

# ==============================================================================
# Agent Builder Platform
# ==============================================================================

agent_builder_namespace  = "agent-builder"
agent_builder_subdomain  = "agent-builder"
container_registry       = "quay-host:8443/agent-builder"
image_tag                = "latest"
storage_class            = "ocs-storagecluster-ceph-rbd"

# ==============================================================================
# PostgreSQL
# ==============================================================================

postgres_password     = "REPLACE_POSTGRES_PASSWORD"
postgres_storage_size = "50Gi"

# ==============================================================================
# MongoDB
# ==============================================================================

mongodb_root_password = "REPLACE_MONGODB_PASSWORD"
mongodb_storage_size  = "50Gi"

# ==============================================================================
# Redis
# ==============================================================================

redis_password     = "REPLACE_REDIS_PASSWORD"
redis_storage_size = "10Gi"

# ==============================================================================
# LiteLLM — Multi-Model LLM Gateway
# ==============================================================================

litellm_master_key    = "REPLACE_LITELLM_MASTER_KEY"

# Cloud LLM Provider keys (optional — leave empty if using Ollama/local only)
anthropic_api_key     = ""
azure_openai_endpoint = ""
azure_openai_key      = ""
openai_api_key        = ""

# ==============================================================================
# Ollama — Local LLM (In-Cluster on OpenShift)
# ==============================================================================

enable_ollama        = true
ollama_model         = "llama3"
ollama_storage_size  = "100Gi"
ollama_gpu_enabled   = false
ollama_gpu_limit     = 1
ollama_memory_limit  = "16Gi"
ollama_cpu_limit     = "8"

# ==============================================================================
# Local LLM — Laptop (External Ollama)
# Connects LiteLLM to an Ollama running on your laptop / workstation.
# The laptop must be network-reachable from the OpenShift cluster.
# ==============================================================================

enable_local_llm_laptop = false
local_llm_laptop_url    = ""        # e.g., "http://192.168.1.100:11434"

# ==============================================================================
# Temporal
# ==============================================================================

temporal_workers_replicas = 2

# ==============================================================================
# Authentication (OIDC) — Optional
# ==============================================================================

oidc_authority = ""
oidc_client_id = ""

# ==============================================================================
# GitHub Integration — Optional
# ==============================================================================

github_token = ""
