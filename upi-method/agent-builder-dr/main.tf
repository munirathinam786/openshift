# Author: Sathishkumar Munirathinam
# Agent Builder Factory — DR Secondary Deployment on OpenShift Baremetal (UPI)
# Deploys the complete Kyndryl Agent Builder platform including:
#   - PostgreSQL (Temporal + LiteLLM backend)
#   - MongoDB (Agent metadata)
#   - Redis (Caching layer)
#   - Temporal Server + Web UI (Workflow orchestration)
#   - Temporal Workers (Activity execution)
#   - LiteLLM Proxy (Multi-model LLM gateway)
#   - Ollama (Local LLM — Llama3)
#   - Agent Builder API (FastAPI backend)
#   - Agent Builder UI (React frontend)
#   - Tool Catalog (MCP Tools Discovery)
#   - Agent Deployment Service
#   - Agent Registry
#   - A2A Gateway (Agent-to-Agent communication)

# ==============================================================================
# Locals
# ==============================================================================

locals {
  kubeconfig   = "/home/${var.bastion_user}/ocp/${var.cluster_name}/auth/kubeconfig"
  ab_namespace = var.agent_builder_namespace
  registry     = var.container_registry
  domain       = "${var.agent_builder_subdomain}.apps.${var.cluster_name}.${var.base_domain}"
}

# ==============================================================================
# Module: Namespace
# ==============================================================================

module "namespace" {
  source = "./modules/namespace"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace
}

# ==============================================================================
# Module: PostgreSQL
# ==============================================================================

module "postgresql" {
  source = "./modules/postgresql"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  postgres_password       = var.postgres_password
  postgres_storage_size   = var.postgres_storage_size
  postgres_storage_class  = var.storage_class

  depends_on = [module.namespace]
}

# ==============================================================================
# Module: MongoDB
# ==============================================================================

module "mongodb" {
  source = "./modules/mongodb"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  mongodb_root_password  = var.mongodb_root_password
  mongodb_storage_size   = var.mongodb_storage_size
  mongodb_storage_class  = var.storage_class

  depends_on = [module.namespace]
}

# ==============================================================================
# Module: Redis
# ==============================================================================

module "redis" {
  source = "./modules/redis"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  redis_password      = var.redis_password
  redis_storage_size  = var.redis_storage_size
  redis_storage_class = var.storage_class

  depends_on = [module.namespace]
}

# ==============================================================================
# Module: Temporal Server
# ==============================================================================

module "temporal" {
  source = "./modules/temporal"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  postgres_host     = "agent-builder-postgresql.${local.ab_namespace}.svc.cluster.local"
  postgres_password = var.postgres_password
  temporal_ui_host  = "temporal.${local.domain}"

  depends_on = [module.postgresql]
}

# ==============================================================================
# Module: Ollama (Local LLM — Llama3)
# ==============================================================================

module "ollama" {
  source = "./modules/ollama"
  count  = var.enable_ollama ? 1 : 0

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  ollama_model          = var.ollama_model
  ollama_storage_size   = var.ollama_storage_size
  ollama_storage_class  = var.storage_class
  ollama_gpu_enabled    = var.ollama_gpu_enabled
  ollama_gpu_limit      = var.ollama_gpu_limit
  ollama_memory_limit   = var.ollama_memory_limit
  ollama_cpu_limit      = var.ollama_cpu_limit

  depends_on = [module.namespace]
}

# ==============================================================================
# Module: LiteLLM Proxy
# ==============================================================================

module "litellm" {
  source = "./modules/litellm"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  litellm_master_key       = var.litellm_master_key
  postgres_host            = "agent-builder-postgresql.${local.ab_namespace}.svc.cluster.local"
  postgres_password        = var.postgres_password
  redis_host               = "agent-builder-redis.${local.ab_namespace}.svc.cluster.local"
  redis_password            = var.redis_password
  anthropic_api_key        = var.anthropic_api_key
  azure_openai_endpoint    = var.azure_openai_endpoint
  azure_openai_key         = var.azure_openai_key
  openai_api_key           = var.openai_api_key
  litellm_host             = "litellm.${local.domain}"

  enable_ollama            = var.enable_ollama
  ollama_host              = var.enable_ollama ? "agent-builder-ollama.${local.ab_namespace}.svc.cluster.local" : ""
  ollama_model             = var.ollama_model

  enable_local_llm_laptop  = var.enable_local_llm_laptop
  local_llm_laptop_url     = var.local_llm_laptop_url

  depends_on = [module.postgresql, module.redis]
}

# ==============================================================================
# Module: Temporal Workers
# ==============================================================================

module "temporal_workers" {
  source = "./modules/temporal-workers"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  container_image  = "${local.registry}/agent-builder-temporal-workers:${var.image_tag}"
  temporal_host    = "agent-builder-temporal.${local.ab_namespace}.svc.cluster.local:7233"
  mongodb_uri      = "mongodb://root:${var.mongodb_root_password}@agent-builder-mongodb.${local.ab_namespace}.svc.cluster.local:27017"
  replicas         = var.temporal_workers_replicas

  depends_on = [module.temporal, module.mongodb]
}

# ==============================================================================
# Module: Agent Builder API
# ==============================================================================

module "agent_builder_api" {
  source = "./modules/agent-builder-api"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  container_image       = "${local.registry}/agent-builder-api:${var.image_tag}"
  litellm_proxy_base    = "http://agent-builder-litellm.${local.ab_namespace}.svc.cluster.local:4000"
  litellm_master_key    = var.litellm_master_key
  mongodb_uri           = "mongodb://root:${var.mongodb_root_password}@agent-builder-mongodb.${local.ab_namespace}.svc.cluster.local:27017"
  temporal_host         = "agent-builder-temporal.${local.ab_namespace}.svc.cluster.local:7233"
  github_token          = var.github_token
  api_host              = "api.${local.domain}"
  oidc_authority        = var.oidc_authority
  oidc_client_id        = var.oidc_client_id

  depends_on = [module.temporal, module.litellm, module.mongodb]
}

# ==============================================================================
# Module: Agent Builder UI
# ==============================================================================

module "agent_builder_ui" {
  source = "./modules/agent-builder-ui"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  container_image  = "${local.registry}/agent-builder-ui:${var.image_tag}"
  api_base_url     = "https://api.${local.domain}"
  ui_host          = "ui.${local.domain}"
  oidc_authority   = var.oidc_authority
  oidc_client_id   = var.oidc_client_id
  oidc_redirect_uri = "https://ui.${local.domain}"

  depends_on = [module.agent_builder_api]
}

# ==============================================================================
# Module: Tool Catalog (MCP Tools Discovery)
# ==============================================================================

module "tool_catalog" {
  source = "./modules/tool-catalog"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  container_image     = "${local.registry}/agent-builder-tool-catalog:${var.image_tag}"
  tool_catalog_host   = "tools.${local.domain}"

  depends_on = [module.namespace]
}

# ==============================================================================
# Module: Agent Deployment Service
# ==============================================================================

module "agent_deployment_service" {
  source = "./modules/agent-deployment-service"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  container_image  = "${local.registry}/agent-deployment-service:${var.image_tag}"
  temporal_host    = "agent-builder-temporal.${local.ab_namespace}.svc.cluster.local:7233"
  mongodb_uri      = "mongodb://root:${var.mongodb_root_password}@agent-builder-mongodb.${local.ab_namespace}.svc.cluster.local:27017"
  deploy_svc_host  = "deploy.${local.domain}"

  depends_on = [module.temporal, module.mongodb]
}

# ==============================================================================
# Module: Agent Registry
# ==============================================================================

module "agent_registry" {
  source = "./modules/agent-registry"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  container_image  = "${local.registry}/agent-builder-registry:${var.image_tag}"
  mongodb_uri      = "mongodb://root:${var.mongodb_root_password}@agent-builder-mongodb.${local.ab_namespace}.svc.cluster.local:27017"
  postgres_host    = "agent-builder-postgresql.${local.ab_namespace}.svc.cluster.local"
  postgres_password = var.postgres_password
  registry_host    = "registry.${local.domain}"

  depends_on = [module.postgresql, module.mongodb]
}

# ==============================================================================
# Module: A2A Gateway
# ==============================================================================

module "a2a_gateway" {
  source = "./modules/a2a-gateway"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  container_image  = "${local.registry}/agent-builder-a2a-gateway:${var.image_tag}"
  a2a_host         = "a2a.${local.domain}"

  depends_on = [module.agent_registry]
}
