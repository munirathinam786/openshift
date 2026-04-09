# Agent Builder Factory — versions.tf (UPI DR Secondary)

Terraform and provider version constraints for the Agent Builder Factory platform.

## Source Code

```hcl
# Author: Sathishkumar Munirathinam

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
