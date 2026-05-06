# UPI Management DC — versions.tf

Provider version constraints for the UPI Management DC cluster.
Identical to all other UPI clusters.

## Required Versions

| Provider | Source | Version |
|----------|--------|---------|
| Terraform | — | `>= 1.9.0` |
| `null` | `hashicorp/null` | `~> 3.2` |
| `local` | `hashicorp/local` | `~> 2.8` |
| `tls` | `hashicorp/tls` | `~> 4.2` |

## Source Code

```hcl
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.8"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.2"
    }
  }
}
```
