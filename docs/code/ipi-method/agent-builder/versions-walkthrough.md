# versions.tf — Line-by-Line Walkthrough

!!! info "File Location"
    `ipi-method/agent-builder/versions.tf`

This file is the **first file Terraform reads** when you run `terraform init`. It declares:

1. The minimum Terraform CLI version required
2. Which provider plugins to download

---

## Complete Source Code

```hcl linenums="1"
# Author: Sathishkumar Munirathinam

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

---

## Line-by-Line Explanation

### Line 1: Author Comment

```hcl
# Author: Sathishkumar Munirathinam
```

- Lines starting with `#` are **comments** — Terraform ignores them
- Best practice: always document the author and purpose at the top of every file

---

### Lines 3–4: Terraform Block + Version Constraint

```hcl
terraform {
  required_version = ">= 1.9.0"
```

| Part | Meaning |
|---|---|
| `terraform { }` | Special configuration block — tells Terraform about itself (not about infrastructure) |
| `required_version` | The minimum Terraform CLI version that can run this code |
| `">= 1.9.0"` | Any version **1.5.0 or newer** is allowed |

!!! question "Where does the `terraform` block come from?"
    This is a **built-in Terraform keyword** — it is part of the HCL (HashiCorp Configuration Language) syntax. You don't import it; it is always available. See: [Terraform Settings](https://developer.hashicorp.com/terraform/language/settings)

**Version constraint operators:**

| Operator | Example | Meaning |
|---|---|---|
| `>=` | `">= 1.9.0"` | Version 1.5.0 or higher |
| `~>` | `"~> 1.5"` | Any 1.x version (1.5, 1.6, 1.7... but NOT 2.0) |
| `=` | `"= 1.5.0"` | Exactly this version only |
| `>=, <` | `">= 1.9.0, < 2.0.0"` | Range: at least 1.5 but below 2.0 |

---

### Lines 6–19: Required Providers

```hcl
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
```

The `required_providers` block declares which **provider plugins** Terraform needs to download.

#### Provider 1: `null`

```hcl
null = {
  source  = "hashicorp/null"
  version = "~> 3.2"
}
```

| Field | Value | Meaning |
|---|---|---|
| `null` | (local name) | How you refer to this provider in your code |
| `source` | `"hashicorp/null"` | Download from the [Terraform Registry](https://registry.terraform.io/providers/hashicorp/null/latest): `registry.terraform.io/hashicorp/null` |
| `version` | `"~> 3.2"` | Any 3.x version ≥ 3.2 (e.g., 3.2.0, 3.2.1, 3.3.0) but **NOT** 4.0 |

!!! tip "Why the `null` provider?"
    The `null` provider gives us `null_resource` — a resource that does nothing by itself but can run **provisioners** (shell commands). This project uses it to:
    
    1. SSH into the bastion host
    2. Run `oc apply -f -` to deploy Kubernetes manifests
    
    This is essential for **air-gapped deployments** where there is no cloud API provider.

**Where to find it:** [registry.terraform.io/providers/hashicorp/null](https://registry.terraform.io/providers/hashicorp/null/latest)

#### Provider 2: `local`

```hcl
local = {
  source  = "hashicorp/local"
  version = "~> 2.8"
}
```

| Field | Value | Meaning |
|---|---|---|
| `source` | `"hashicorp/local"` | Download from Terraform Registry |
| `version` | `"~> 2.8"` | Any 2.x version ≥ 2.4 |

!!! tip "Why the `local` provider?"
    The `local` provider lets Terraform read and write files on the machine where Terraform runs. Used for:
    
    - Reading SSH keys from disk (`file()` function)
    - Writing generated configuration files

**Where to find it:** [registry.terraform.io/providers/hashicorp/local](https://registry.terraform.io/providers/hashicorp/local/latest)

#### Provider 3: `tls`

```hcl
tls = {
  source  = "hashicorp/tls"
  version = "~> 4.2"
}
```

| Field | Value | Meaning |
|---|---|---|
| `source` | `"hashicorp/tls"` | Download from Terraform Registry |
| `version` | `"~> 4.2"` | Any 4.x version ≥ 4.0 |

!!! tip "Why the `tls` provider?"
    The `tls` provider generates TLS certificates and private keys. Useful for creating self-signed certs for internal services.

**Where to find it:** [registry.terraform.io/providers/hashicorp/tls](https://registry.terraform.io/providers/hashicorp/tls/latest)

---

### Line 20: Closing Brace

```hcl
}
```

Closes the `terraform { }` block.

---

## What Happens When You Run `terraform init`

When you run `terraform init` in the `agent-builder/` directory, Terraform:

1. **Reads** `versions.tf`
2. **Downloads** the three providers from the Terraform Registry (or from a local mirror in air-gapped mode)
3. **Stores** them in `.terraform/providers/` directory
4. **Creates** `.terraform.lock.hcl` — a lock file that pins exact versions

```bash
$ terraform init

Initializing provider plugins...
- Finding hashicorp/null versions matching "~> 3.2"...
- Finding hashicorp/local versions matching "~> 2.8"...
- Finding hashicorp/tls versions matching "~> 4.2"...
- Installing hashicorp/null v3.2.3...
- Installing hashicorp/local v2.5.2...
- Installing hashicorp/tls v4.0.6...

Terraform has been successfully initialized!
```

---

## How to Write This File From Scratch

1. **Start with the `terraform` block:**
    ```hcl
    terraform {
      required_version = ">= 1.9.0"
    }
    ```

2. **Identify which providers you need** by looking at the resources you plan to use:
    - Using `null_resource`? → You need the `null` provider
    - Using `local_file`? → You need the `local` provider
    - Using `tls_private_key`? → You need the `tls` provider
    - Using `aws_instance`? → You need the `aws` provider

3. **Look up the provider on the Terraform Registry** to find the `source` path and latest version

4. **Add each provider to `required_providers`:**
    ```hcl
    required_providers {
      provider_name = {
        source  = "namespace/provider_name"
        version = "~> MAJOR.MINOR"
      }
    }
    ```

!!! warning "Air-Gapped Environments"
    In air-gapped mode, providers cannot be downloaded from the internet. You must:
    
    1. Pre-download providers on an internet-connected machine: `terraform providers mirror /path/to/mirror`
    2. Copy the mirror directory to the bastion host
    3. Configure a filesystem mirror in `~/.terraformrc`:
    ```hcl
    provider_installation {
      filesystem_mirror {
        path = "/opt/terraform/providers"
      }
    }
    ```
