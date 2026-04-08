# UPI DR Secondary — versions.tf

Provider version constraints for the UPI DR Secondary cluster.
Identical to all other UPI clusters.

## Required Versions

| Provider | Source | Version |
|----------|--------|---------|
| Terraform | — | `>= 1.5.0` |
| `null` | `hashicorp/null` | `~> 3.2` |
| `local` | `hashicorp/local` | `~> 2.4` |
| `tls` | `hashicorp/tls` | `~> 4.0` |

## Source Code

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}
```
