# ADO Pipeline — UPI Day 2 Operations

This pipeline runs **Day 2 post-install operations** for UPI (User Provisioned Infrastructure) clusters, separately from the Day 1 cluster installation pipeline. Day 2 covers Cluster Logging, OADP Backup & Restore, LDAP/OAuth integration, OpenShift GitOps (Argo CD), and OpenShift Pipelines (Tekton).

!!! info "Day 1 vs Day 2"
    - **Day 1** (`azure-pipelines-upi.yml`) — UPI cluster install, core operators, networking, storage
    - **Day 2** (`azure-pipelines-day2-upi.yml`) — Logging, backup/restore, identity provider, GitOps (ArgoCD), Pipelines (Tekton)

## Pipeline Flow

![Day-2 Pipeline Flow (UPI)](../diagrams/pipeline/13-day2-upi-pipeline.svg){: .drawio-diagram }

???+ note "Draw.io Source: Day-2 Pipeline Flow (UPI)"
    [:material-download: Download .drawio file](../diagrams/pipeline/13-day2-upi-pipeline.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Pipeline Parameters

| Parameter | Type | Default | Values | Description |
|-----------|------|---------|--------|-------------|
| `deploymentScope` | string | `dc-only` | `dc-only`, `dr-only`, `dc-and-dr`, `mgmt-dc-only`, `mgmt-dr-only`, `mgmt-clusters`, `all-dc`, `all-dr`, `all` | Target cluster(s) for Day 2 |
| `enableClusterLogging` | boolean | `true` | `true` / `false` | Enable Cluster Logging (Elasticsearch + S3 forwarding) |
| `enableOADP` | boolean | `true` | `true` / `false` | Enable OADP Backup & Restore (Velero + S3) |
| `enableLDAP` | boolean | `true` | `true` / `false` | Enable LDAP / OAuth Integration |
| `enableGitOps` | boolean | `true` | `true` / `false` | Enable OpenShift GitOps (Argo CD) |
| `enablePipelines` | boolean | `true` | `true` / `false` | Enable OpenShift Pipelines (Tekton) |
| `terraformAction` | string | `plan` | `plan`, `apply`, `destroy` | Terraform action to execute |
| `variableGroup` | string | `ocp-upi-day2-secrets` | — | ADO Variable Group name for Day 2 secrets |

## ADO Variable Group — Day 2 Secrets

Create a Variable Group named **`ocp-upi-day2-secrets`** in Azure DevOps (**Project Settings → Pipelines → Library → + Variable Group**):

| Secret Name | Source | Used By | Description |
|-------------|--------|---------|-------------|
| `ldap-bind-password` | Corporate LDAP service account password | All clusters | LDAP bind credential for OAuth integration |
| `log-s3-access-key` | S3-compatible storage (ODF RGW, MinIO, AWS) | All clusters | Log forwarding S3 access key |
| `log-s3-secret-key` | Same S3 storage provider | All clusters | Log forwarding S3 secret key |
| `oadp-s3-access-key` | S3-compatible storage for Velero backups | All clusters | OADP backup storage access key |
| `oadp-s3-secret-key` | Same S3 storage provider | All clusters | OADP backup storage secret key |
| `argocd-repo-token` | Git repository PAT for ArgoCD | All clusters | ArgoCD Git repository authentication |
| `pac-webhook-secret` | Pipelines-as-Code webhook token | All clusters | Pipelines-as-Code webhook authentication |
| `pac-webhook-shared-secret` | Pipelines-as-Code shared webhook secret | All clusters | Pipelines-as-Code shared secret |

!!! warning "Security"
    - Mark all secrets as **🔒 secret** (padlock icon) in ADO to mask them in pipeline logs
    - **Never** commit secrets to Git
    - Rotate S3 keys and LDAP bind password periodically

## Pipeline Stages

| Stage | Display Name | Cluster Folder | Condition |
|-------|-------------|----------------|-----------|
| `Day2_UPI_DC_Primary` | Day 2 — UPI DC Primary | `openshiftbaremetal/` | `dc-only`, `dc-and-dr`, `all-dc`, `all` |
| `Day2_UPI_DR_Secondary` | Day 2 — UPI DR Secondary | `openshiftbaremetal-dr/` | `dr-only`, `dc-and-dr`, `all-dr`, `all` |
| `Day2_UPI_Mgmt_DC` | Day 2 — UPI Management DC | `mgmt-dc/` | `mgmt-dc-only`, `mgmt-clusters`, `all-dc`, `all` |
| `Day2_UPI_Mgmt_DR` | Day 2 — UPI Management DR | `mgmt-dr/` | `mgmt-dr-only`, `mgmt-clusters`, `all-dr`, `all` |

### Stage Dependencies

- **UPI DR Secondary** waits for UPI DC Primary when scope is `dc-and-dr` or `all`
- **UPI Mgmt DR** waits for UPI Mgmt DC when scope is `mgmt-clusters` or `all`

## Usage

Each stage runs Terraform with **both** var files to layer Day 2 on top of Day 1:

```bash
terraform apply \
  -var-file=terraform.tfvars \
  -var-file=day2-terraform.tfvars \
  -var enable_cluster_logging=true \
  -var enable_oadp=true \
  -var enable_ldap=true \
  -var enable_openshift_gitops=true \
  -var enable_openshift_pipelines=true \
  -input=false \
  -auto-approve
```

Secrets are injected as environment variables from the ADO Variable Group:

```yaml
env:
  TF_VAR_ldap_bind_password: $(ldap-bind-password)
  TF_VAR_log_s3_access_key:  $(log-s3-access-key)
  TF_VAR_log_s3_secret_key:  $(log-s3-secret-key)
  TF_VAR_oadp_s3_access_key: $(oadp-s3-access-key)
  TF_VAR_oadp_s3_secret_key: $(oadp-s3-secret-key)
  TF_VAR_argocd_repo_token: $(argocd-repo-token)
  TF_VAR_pac_webhook_secret: $(pac-webhook-secret)
  TF_VAR_pac_webhook_shared_secret: $(pac-webhook-shared-secret)
```

## Day 2 Features

### Cluster Logging
- Deploys OpenShift Logging Operator (Elasticsearch-backed)
- Configures log retention for application, infrastructure, and audit logs
- Enables S3 log forwarding to ODF RGW endpoint

### OADP — Backup & Restore
- Deploys OADP Operator (Velero-based)
- Configures S3 Backup Storage Location (ODF RGW)
- Creates daily backup schedule with configurable TTL

### LDAP / OAuth
- Adds LDAP identity provider to OpenShift OAuth
- Deploys LDAP Group Sync CronJob
- Creates RBAC ClusterRoleBindings from LDAP groups
- Optional kubeadmin removal

### OpenShift GitOps (Argo CD)
- Installs OpenShift GitOps operator
- Configures ArgoCD instance with RBAC, HA, and managed namespaces
- Connects Git repositories for GitOps workflows
- Grants cluster-admin to ArgoCD application controller

### OpenShift Pipelines (Tekton)
- Installs OpenShift Pipelines operator
- Configures TektonConfig CR with profile, cluster tasks, and templates
- Enables Pipelines-as-Code for GitHub/GitLab webhook integration
- Configurable pipeline timeouts and resource limits

## Source Code

See the full pipeline YAML: [azure-pipelines-day2-upi.yml](../code/upi-method/azure-pipelines-day2-upi.md)
