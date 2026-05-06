# DR Secondary — versions.tf

Terraform and provider version constraints for the DR Secondary cluster.
Identical to DC Primary.

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
