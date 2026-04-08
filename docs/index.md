# Terraform IaC for OpenShift Multi Cluster AirGapped

Welcome to the **Terraform IaC documentation** for deploying a multi-cluster Red Hat OpenShift environment on bare metal in air-gapped mode with NVIDIA GPU support, disaster recovery, and centralized management.

## What This Covers

This documentation site provides the complete Terraform codebase and architecture guidance for deploying **four OpenShift clusters** across DC and DR sites:

| Cluster | IPI Folder | UPI Folder | Role | Key Components |
|---------|-----------|-----------|------|----------------|
| **DC Primary** | `ipi-method/openshiftbaremetal/` | `upi-method/openshiftbaremetal/` | Production workload | OCP + OpenShift AI + GPU + ODF + Submariner Broker |
| **DR Secondary** | `ipi-method/openshiftbaremetal-dr/` | `upi-method/openshiftbaremetal-dr/` | Standby workload | OCP + OpenShift AI + GPU + ODF + Submariner Agent + ODF DR |
| **Management DC** | `ipi-method/mgmt-dc/` | `upi-method/mgmt-dc/` | Cluster management hub | OCP + ACM Hub + ACS Central + Quay Enterprise |
| **Management DR** | `ipi-method/mgmt-dr/` | `upi-method/mgmt-dr/` | Management standby | OCP + ACM Standby + ACS SecuredCluster + Quay Enterprise |

## Documentation Sections

- **[Architecture](architecture/terraform-multi-cluster-overview.md)** — Multi-cluster architecture, network topology, deployment flows, failover workflows
- **[Cluster Environments](clusters/terraform-ocp-baremetal.md)** — Per-cluster Terraform documentation with module details and variable references
- **[CI/CD Pipeline](pipeline/terraform-ado-pipeline.md)** — Azure DevOps pipeline for selective multi-cluster deployment
- **[Terraform Code — IPI](code/ipi-method/openshiftbaremetal/main.md)** — Complete annotated IPI Terraform code for all cluster environments
- **[Terraform Code — UPI](code/upi-method/main.md)** — Complete annotated UPI Terraform code for all cluster environments

## Quick Start

### Option 1: Deploy via Azure DevOps Pipeline

1. Configure `terraform.tfvars` for each cluster environment
2. Push to the `main` branch
3. Run the ADO pipeline with your desired deployment scope

### Option 2: Manual Terraform Deployment

```bash
# === IPI Method ===
# DC Primary (workload cluster)
cd ipi-method/openshiftbaremetal/
vi terraform.tfvars          # Update environment values
terraform init
terraform plan
terraform apply

# DR Secondary (workload cluster)
cd ../openshiftbaremetal-dr/
vi terraform.tfvars
terraform init && terraform apply

# Management DC (ACM + ACS + Quay)
cd ../mgmt-dc/
vi terraform.tfvars
terraform init && terraform apply

# Management DR (ACM standby + ACS secured + Quay)
cd ../mgmt-dr/
vi terraform.tfvars
terraform init && terraform apply

# === UPI Method ===
cd ../../upi-method/openshiftbaremetal/
vi terraform.tfvars
terraform init && terraform apply
```

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Terraform** | >= 1.5.0 |
| **Bastion Node** | RHEL 8.x/9.x with `kni` user, libvirt, `oc` CLI, `openshift-baremetal-install` (IPI) or `openshift-install` (UPI) |
| **Pull Secret** | From [console.redhat.com](https://console.redhat.com/openshift/downloads#tool-pull-secret) |
| **DNS** | A records for `api.<cluster>.<domain>`, `*.apps.<cluster>.<domain>` |
| **BMC Access** | iDRAC/iLO Redfish API accessible from provisioner **(IPI only)** |
| **SSH Key Pair** | Ed25519 or RSA for `core` user |
| **NVIDIA NGC** | NGC API key for GPU driver images |
| **HAProxy** | External load balancer for API + Ingress **(UPI only — IPI uses built-in keepalived)** |

### Secrets & Credentials

All sensitive values must be obtained, placed on the bastion host, and injected into Terraform via ADO Variable Groups or `terraform.tfvars`.

#### Files on the Bastion Host

| File | Bastion Path | Download Source | Used By |
|------|-------------|----------------|---------|
| **Pull Secret** | `/home/kni/pull-secret.json` | [console.redhat.com/openshift/downloads](https://console.redhat.com/openshift/downloads#tool-pull-secret) | All clusters — `pull_secret_file` |
| **SSH Private Key** | `/home/kni/.ssh/id_ed25519` | Generate: `ssh-keygen -t ed25519` | All clusters — `ssh_private_key_file` |
| **SSH Public Key** | `/home/kni/.ssh/id_ed25519.pub` | Generated with private key | All clusters — `ssh_public_key_file` |
| **Quay CA Certificate** | `/home/kni/quay-ca.crt` | From your Quay mirror server | Disconnected installs — `quay_ca_cert_file` |
| **NLS License Token** | `/home/kni/nls-client-token.tok` | [NVIDIA Licensing Portal](https://ui.licensing.nvidia.com/) | GPU clusters — `nls_token_file` |
| **Entitlement PEM** | `/home/kni/entitlement.pem` | Red Hat Subscription Manager | GPU clusters — `entitlement_pem_file` |

#### ADO Variable Group Secrets

Create Variable Groups in Azure DevOps (**Project Settings → Pipelines → Library**):

=== "IPI — `ocp-baremetal-secrets`"

    | Secret Name | Source | Used By |
    |-------------|--------|---------|
    | `quay-admin-password` | Your Quay mirror admin password | All clusters |
    | `ngc-api-key` | [NVIDIA NGC Portal](https://ngc.nvidia.com/setup/api-key) → Generate API Key | DC, DR (GPU) |
    | `submariner-broker-token` | From DC Primary after Submariner broker install: `oc get secret -n submariner-k8s-broker` | DR |
    | `odf-dr-s3-access-key` | S3-compatible storage (e.g., MinIO, AWS) for ODF DR metadata | DR |
    | `odf-dr-s3-secret-key` | S3-compatible storage for ODF DR metadata | DR |
    | `acs-central-admin-password` | Choose a strong password for ACS StackRox Central | Mgmt DC |
    | `acm-s3-access-key` | S3-compatible storage for ACM Observability | Mgmt DC, Mgmt DR |
    | `acm-s3-secret-key` | S3-compatible storage for ACM Observability | Mgmt DC, Mgmt DR |

=== "UPI — `ocp-baremetal-upi-secrets`"

    | Secret Name | Source | Used By |
    |-------------|--------|---------|
    | `quay-admin-password` | Your Quay mirror admin password | All clusters |
    | `ngc-api-key` | [NVIDIA NGC Portal](https://ngc.nvidia.com/setup/api-key) → Generate API Key | DC, DR (GPU) |
    | `odf-dr-s3-access-key` | S3-compatible storage for ODF DR metadata | DR |
    | `odf-dr-s3-secret-key` | S3-compatible storage for ODF DR metadata | DR |

!!! warning "Security Best Practices"
    - **Never** commit secrets to Git — use ADO Variable Groups (marked as secret) or HashiCorp Vault
    - Mark all secret variables in ADO as **🔒 secret** (padlock icon) to mask them in pipeline logs
    - The `pull-secret.json` file on the bastion should be owned by `kni` with `chmod 600`
    - Rotate `ngc-api-key` and S3 keys periodically

## Day 1 vs Day 2 Operations

Deployment is split into two phases with separate var files and pipelines:

| Phase | Var File | IPI Pipeline | UPI Pipeline | Scope |
|---|---|---|---|---|
| **Day 1 — Install** | `terraform.tfvars` | `azure-pipelines.yml` | `azure-pipelines-upi.yml` | Cluster install, core operators, networking, storage |
| **Day 2 — Post-Install** | `day2-terraform.tfvars` | `azure-pipelines-day2.yml` | `azure-pipelines-day2-upi.yml` | Cluster Logging, OADP backup, LDAP/OAuth, GitOps (ArgoCD), Pipelines (Tekton) |

Day 2 operations are applied **after** cluster installation completes:

```bash
terraform apply -var-file=terraform.tfvars -var-file=day2-terraform.tfvars
```

### Day 2 Components

| Component | Description |
|-----------|-------------|
| **Cluster Logging** | OpenShift Logging (Elasticsearch) + S3 log forwarding to ODF RGW |
| **OADP** | Backup & Restore via Velero with S3 Backup Storage Location |
| **LDAP/OAuth** | Corporate LDAP identity provider + Group Sync CronJob + RBAC bindings |
| **OpenShift GitOps** | Argo CD operator + ArgoCD instance with RBAC, HA, managed namespaces, and Git repo connections |
| **OpenShift Pipelines** | Tekton operator + TektonConfig CR with profile, cluster tasks, Pipelines-as-Code, and resource limits |

### Day 2 Documentation

- **[IPI Day 2 Pipeline](pipeline/terraform-ado-pipeline-day2.md)** — ADO pipeline for IPI Day 2 operations
- **[UPI Day 2 Pipeline](pipeline/terraform-upi-ado-pipeline-day2.md)** — ADO pipeline for UPI Day 2 operations
- **[IPI Day 2 Pipeline YAML](code/ipi-method/pipeline/azure-pipelines-day2.md)** — Annotated pipeline source
- **[UPI Day 2 Pipeline YAML](code/upi-method/azure-pipelines-day2-upi.md)** — Annotated pipeline source

## Network Architecture

Each cluster uses **non-overlapping CIDRs** for Submariner cross-cluster routing:

| Cluster | Machine CIDR | Pod CIDR | Service CIDR |
|---------|-------------|----------|-------------|
| DC Primary | 10.142.41.0/24 | 10.128.0.0/14 | 172.30.0.0/16 |
| DR Secondary | 10.143.41.0/24 | 10.132.0.0/14 | 172.31.0.0/16 |
| Mgmt DC | 10.142.42.0/24 | 10.136.0.0/14 | 172.28.0.0/16 |
| Mgmt DR | 10.143.42.0/24 | 10.140.0.0/14 | 172.29.0.0/16 |

## Running This Documentation Locally

```bash
# Using Podman Compose
podman-compose up -d --build

# Or build and run manually with Podman
podman build -t terraform-iac-docs -f Containerfile .
podman run -d -p 8000:8000 -v ./:/docs --name terraform-iac-docs terraform-iac-docs

# Access at http://localhost:8000
```
