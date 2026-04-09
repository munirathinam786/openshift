# Agent Builder Factory — outputs.tf (UPI DC Primary)

Terraform outputs for the Agent Builder Factory platform on the **UPI DC Primary** environment. Provides URLs for all deployed services.

## Source Code

```hcl
# Author: Sathishkumar Munirathinam
# Agent Builder Factory — Outputs

output "agent_builder_ui_url" {
  description = "Agent Builder UI URL"
  value       = "https://ui.${local.domain}"
}

output "agent_builder_api_url" {
  description = "Agent Builder API URL"
  value       = "https://api.${local.domain}"
}

output "litellm_proxy_url" {
  description = "LiteLLM Proxy URL"
  value       = "https://litellm.${local.domain}"
}

output "temporal_ui_url" {
  description = "Temporal Web UI URL"
  value       = "https://temporal.${local.domain}"
}

output "tool_catalog_url" {
  description = "Tool Catalog (MCP) URL"
  value       = "https://tools.${local.domain}"
}

output "agent_registry_url" {
  description = "Agent Registry URL"
  value       = "https://registry.${local.domain}"
}

output "a2a_gateway_url" {
  description = "A2A Gateway URL"
  value       = "https://a2a.${local.domain}"
}

output "deploy_service_url" {
  description = "Agent Deployment Service URL"
  value       = "https://deploy.${local.domain}"
}

output "ollama_internal_url" {
  description = "Ollama internal service URL (cluster-only)"
  value       = var.enable_ollama ? "http://agent-builder-ollama.${local.ab_namespace}.svc.cluster.local:11434" : "disabled"
}

output "namespace" {
  description = "Kubernetes namespace for the Agent Builder platform"
  value       = local.ab_namespace
}
```
