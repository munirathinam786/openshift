# LLM provider guide

This page documents how the AWS SRE agent now supports both the original local Ollama workflow and hosted providers.

## Supported providers

| Provider ID | Type | Typical use |
| --- | --- | --- |
| `ollama` | local | Run the agent entirely against a local model on the laptop or workstation |
| `openai` | external | Use OpenAI-hosted chat models through the Chat Completions API |
| `azure-openai` | external | Use Azure OpenAI deployments with explicit endpoint and API-version control |
| `anthropic` | external | Use Claude models through the Messages API |
| `gemini` | external | Use Google Gemini through the Generative Language API |
| `openrouter` | external | Use OpenRouter through its OpenAI-compatible API |

## Core environment variables

These variables control the provider used when the process starts.

| Variable | Purpose |
| --- | --- |
| `LLM_PROVIDER` | Active provider ID. Defaults to `ollama` |
| `LLM_MODEL_NAME` | Hosted-provider model or deployment name |
| `LLM_BASE_URL` | Hosted-provider base URL or endpoint |
| `LLM_API_KEY` | Provider API key |
| `LLM_API_VERSION` | Provider API version for providers that require one |
| `LLM_ORGANIZATION` | Optional org or tenant hint |
| `OLLAMA_BASE_URL` | Local Ollama endpoint used when `LLM_PROVIDER=ollama` |
| `LOCAL_MODEL_NAME` | Local Ollama model tag used when `LLM_PROVIDER=ollama` |
| `FALLBACK_MODELS` | Comma-separated fallback model list |

## Browser runtime overrides

All main operator pages now include a provider dropdown and switch the settings panel between:

- **local Ollama controls**
  - base URL
  - local model selector / refresh
- **hosted-provider controls**
  - provider model or deployment name
  - base URL or endpoint
  - API key
  - organization / tenant hint
  - API version when relevant

These overrides apply only to the current request and do not rewrite `.env`.

## Provider examples

### Ollama

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_MODEL_NAME=gpt-oss:20b
```

Typical Podman-hosted local runtime on macOS:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.containers.internal:11434
LOCAL_MODEL_NAME=gpt-oss:20b
```

### OpenAI

```env
LLM_PROVIDER=openai
LLM_MODEL_NAME=gpt-4.1-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=replace-me
LLM_ORGANIZATION=
```

### Azure OpenAI

```env
LLM_PROVIDER=azure-openai
LLM_MODEL_NAME=gpt-4.1-mini
LLM_BASE_URL=https://your-resource-name.openai.azure.com
LLM_API_KEY=replace-me
LLM_API_VERSION=2024-06-01
```

For Azure OpenAI, `LLM_MODEL_NAME` is treated as the deployment name in the request path.

### Anthropic

```env
LLM_PROVIDER=anthropic
LLM_MODEL_NAME=claude-3-5-sonnet-latest
LLM_BASE_URL=https://api.anthropic.com
LLM_API_KEY=replace-me
LLM_API_VERSION=2023-06-01
```

### Gemini

```env
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-pro
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta
LLM_API_KEY=replace-me
```

### OpenRouter

```env
LLM_PROVIDER=openrouter
LLM_MODEL_NAME=openai/gpt-4.1-mini
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=replace-me
```

## Request-scoped `/chat` example

```json
{
  "prompt": "Review Security Hub findings and summarize the highest-risk controls.",
  "runtime": {
    "llm_provider": "anthropic",
    "llm_model_name": "claude-3-5-sonnet-latest",
    "llm_base_url": "https://api.anthropic.com",
    "llm_api_key": "replace-me",
    "llm_api_version": "2023-06-01",
    "aws_region": "us-east-1",
    "agent_max_steps": 12
  }
}
```

## Token usage normalization

The backend records token usage across providers, but each provider reports those numbers differently.

| Provider | Native usage fields |
| --- | --- |
| Ollama | `prompt_eval_count`, `eval_count` |
| OpenAI / OpenRouter | `prompt_tokens`, `completion_tokens`, `total_tokens` |
| Azure OpenAI | `prompt_tokens`, `completion_tokens`, `total_tokens` |
| Anthropic | `input_tokens`, `output_tokens` |
| Gemini | `promptTokenCount`, `candidatesTokenCount`, `totalTokenCount` |

The backend normalizes those into:

- `prompt_tokens`
- `completion_tokens`
- `total_tokens`

## Provider selection behavior

- `Settings.load()` reads the process-wide defaults from `.env`
- `Settings.with_overrides(...)` applies request-scoped overrides without mutating the base process config
- `GET /llm/providers` returns the provider catalog used by the UI
- `GET /readyz` reports the active provider in the readiness payload

## Fallback models

`FALLBACK_MODELS` lets the runtime try additional model names after a failed request.

Example:

```env
FALLBACK_MODELS=qwen3:8b,llama3.1:8b
```

This is most useful for Ollama, but it can also be used with provider-compatible model names when the target provider accepts them.

## Operational notes

- Use the local `LLM Utilization` page for Ollama-specific visibility such as loaded models, VRAM footprint, and host-process notes.
- Use `GET /llm/providers` and the page-level settings panels to understand hosted-provider configuration.
- Keep real API keys out of committed files; the repository `.env` should contain placeholders rather than live credentials.
