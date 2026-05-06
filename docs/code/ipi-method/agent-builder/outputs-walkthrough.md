# outputs.tf — Line-by-Line Walkthrough

!!! info "File Location"
    `ipi-method/agent-builder/outputs.tf`

This file defines what information Terraform **displays after deployment**. When `terraform apply` finishes, these values are printed to the terminal.

---

## What Are Outputs?

Outputs serve three purposes:

1. **Display useful information** after `terraform apply` (URLs, endpoints)
2. **Export values** for other Terraform configurations to consume
3. **Document** the deployment's external interface

---

## Complete Source Code

```hcl linenums="1"
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

---

## Line-by-Line Explanation

### Output Syntax

Every output follows this pattern:

```hcl
output "output_name" {
  description = "Human-readable explanation"
  value       = <expression>
}
```

| Field | Purpose |
|---|---|
| `"output_name"` | Name shown in `terraform output` command |
| `description` | Human-readable help text |
| `value` | The actual value to display — can be a string, number, list, or map |

---

### External URLs (Lines 4–42)

All external-facing URLs follow the same pattern:

```hcl
value = "https://<prefix>.${local.domain}"
```

Where `local.domain` = `agent-builder.apps.ocp-ai.example.com`

| Output | Prefix | Full URL |
|---|---|---|
| `agent_builder_ui_url` | `ui` | `https://ui.agent-builder.apps.ocp-ai.example.com` |
| `agent_builder_api_url` | `api` | `https://api.agent-builder.apps.ocp-ai.example.com` |
| `litellm_proxy_url` | `litellm` | `https://litellm.agent-builder.apps.ocp-ai.example.com` |
| `temporal_ui_url` | `temporal` | `https://temporal.agent-builder.apps.ocp-ai.example.com` |
| `tool_catalog_url` | `tools` | `https://tools.agent-builder.apps.ocp-ai.example.com` |
| `agent_registry_url` | `registry` | `https://registry.agent-builder.apps.ocp-ai.example.com` |
| `a2a_gateway_url` | `a2a` | `https://a2a.agent-builder.apps.ocp-ai.example.com` |
| `deploy_service_url` | `deploy` | `https://deploy.agent-builder.apps.ocp-ai.example.com` |

!!! tip "Why `https://`?"
    All routes in this project use TLS edge termination (`tls.termination: edge` in the Route spec). OpenShift's router handles HTTPS and forwards traffic as HTTP to the pod.

---

### Conditional Output: Ollama (Lines 46–49)

```hcl
output "ollama_internal_url" {
  description = "Ollama internal service URL (cluster-only)"
  value       = var.enable_ollama ? "http://agent-builder-ollama.${local.ab_namespace}.svc.cluster.local:11434" : "disabled"
}
```

This uses a **ternary expression**:

```
condition ? value_if_true : value_if_false
```

- If `enable_ollama = true` → Shows the internal Kubernetes URL
- If `enable_ollama = false` → Shows `"disabled"`

!!! info "Why `http://` (not `https://`)?"
    This is a **cluster-internal** URL. Traffic between pods within the same cluster stays inside the Kubernetes network and does not need TLS. The URL format uses the Kubernetes DNS convention: `<service>.<namespace>.svc.cluster.local:<port>`.

---

### Namespace Output (Lines 51–54)

```hcl
output "namespace" {
  description = "Kubernetes namespace for the Agent Builder platform"
  value       = local.ab_namespace
}
```

Outputs the namespace name (`"agent-builder"`) for reference or use by other automation.

---

## What `terraform apply` Shows

After a successful deployment, Terraform prints:

```
Apply complete! Resources: 28 added, 0 changed, 0 destroyed.

Outputs:

a2a_gateway_url        = "https://a2a.agent-builder.apps.ocp-ai.example.com"
agent_builder_api_url  = "https://api.agent-builder.apps.ocp-ai.example.com"
agent_builder_ui_url   = "https://ui.agent-builder.apps.ocp-ai.example.com"
deploy_service_url     = "https://deploy.agent-builder.apps.ocp-ai.example.com"
litellm_proxy_url      = "https://litellm.agent-builder.apps.ocp-ai.example.com"
namespace              = "agent-builder"
ollama_internal_url    = "http://agent-builder-ollama.agent-builder.svc.cluster.local:11434"
temporal_ui_url        = "https://temporal.agent-builder.apps.ocp-ai.example.com"
tool_catalog_url       = "https://tools.agent-builder.apps.ocp-ai.example.com"
agent_registry_url     = "https://registry.agent-builder.apps.ocp-ai.example.com"
```

You can also retrieve outputs later:

```bash
# Show all outputs
terraform output

# Show a specific output
terraform output agent_builder_ui_url

# Show output as raw value (no quotes)
terraform output -raw agent_builder_api_url
```

---

## How to Write `outputs.tf` From Scratch

1. **Identify every URL or value** a user needs after deployment
2. **Create one `output` block per value**
3. **Use `description`** to explain what each output is
4. **Use ternary expressions** for conditional outputs
5. **Follow naming conventions:** `service_name_type` (e.g., `agent_builder_ui_url`, `ollama_internal_url`)

```hcl
# Template:
output "meaningful_name" {
  description = "What this URL/value is for"
  value       = "https://prefix.${local.domain}"
}
```
