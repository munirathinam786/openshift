# ADO Pipeline — Agent Builder Factory (Day 2 Operations)

This page documents the **Day 2 operations pipeline** for managing the Agent Builder Factory after initial deployment.

!!! info "Pipeline File"
    **IPI Source:** `ipi-method/azure-pipelines-agent-builder-day2.yml`
    **UPI Source:** `upi-method/azure-pipelines-agent-builder-day2.yml`
    See also: [Day 1 Deployment Pipeline](terraform-agent-builder-pipeline.md) | [Agent Builder Deployment](../clusters/terraform-agent-builder.md)

## Day 2 Operations

| Operation | Description | Method |
|-----------|-------------|--------|
| `update-config` | Update Terraform configuration and re-apply | Terraform apply |
| `scale-services` | Scale service replicas up/down | `oc scale` |
| `change-llm-model` | Switch Ollama model (e.g., llama3 → mistral) | Terraform target apply |
| `add-laptop-llm` | Add laptop Ollama connectivity | Terraform target apply |
| `remove-laptop-llm` | Remove laptop Ollama connectivity | Terraform target apply |
| `rotate-secrets` | Rotate all service passwords/keys | Terraform apply |
| `update-images` | Update container image tags | Terraform apply |
| `restart-services` | Rolling restart all deployments | `oc rollout restart` |

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `day2Operation` | string | `update-config` | Operation to perform (see table above) |
| `targetCluster` | string | `dc-primary` | Target cluster |
| `apiReplicas` | number | `2` | API replica count (for scale operation) |
| `uiReplicas` | number | `2` | UI replica count (for scale operation) |
| `workerReplicas` | number | `2` | Worker replica count (for scale operation) |
| `ollamaModel` | string | `llama3` | New Ollama model (for model change) |
| `localLLMLaptopUrl` | string | `http://192.168.1.100:11434` | Laptop Ollama URL (for laptop LLM ops) |
| `newImageTag` | string | `latest` | New image tag (for image updates) |

## Stage Details

### Scale Services

Scales individual services using `oc scale`:

```bash
oc scale deployment/agent-builder-api --replicas=3 -n agent-builder
oc scale deployment/agent-builder-ui --replicas=3 -n agent-builder
oc scale deployment/temporal-workers --replicas=4 -n agent-builder
```

**Condition:** `day2Operation` is `scale-services`.

### Change LLM Model

Switches the Ollama model by targeting specific Terraform modules:

```bash
terraform apply \
  -target=module.ollama \
  -target=module.litellm \
  -var="ollama_model=mistral"
```

**Condition:** `day2Operation` is `change-llm-model`.

### Add/Remove Laptop LLM

Modifies LiteLLM configuration to add or remove laptop Ollama connectivity:

```bash
terraform apply \
  -target=module.litellm \
  -var="enable_local_llm_laptop=true" \
  -var="local_llm_laptop_url=http://192.168.1.100:11434"
```

### Update Images

Applies new container image tags across all services:

```bash
terraform apply -var="image_tag=v2.1.0"
```

### Restart Services

Performs rolling restarts of all Agent Builder deployments:

```bash
oc rollout restart deployment/agent-builder-api -n agent-builder
oc rollout restart deployment/agent-builder-ui -n agent-builder
oc rollout restart deployment/temporal-workers -n agent-builder
oc rollout restart deployment/litellm -n agent-builder
oc rollout restart deployment/ollama -n agent-builder
oc rollout restart deployment/tool-catalog -n agent-builder
oc rollout restart deployment/agent-deployment-service -n agent-builder
oc rollout restart deployment/agent-registry -n agent-builder
oc rollout restart deployment/a2a-gateway -n agent-builder
```

## Related Pages

- [Agent Builder Deployment](../clusters/terraform-agent-builder.md)
- [Day 1 Deployment Pipeline](terraform-agent-builder-pipeline.md)
- [ADO Pipeline (IPI — Day 2)](terraform-ado-pipeline-day2.md)
