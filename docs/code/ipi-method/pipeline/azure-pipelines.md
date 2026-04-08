# IPI — Azure DevOps Pipeline — azure-pipelines.yml

Multi-stage pipeline for deploying all 4 OpenShift clusters via Terraform using the **IPI (Installer Provisioned Infrastructure)** method.
Supports selective deployment scopes, Submariner cross-site networking, and ODF DR replication.

!!! info "Pipeline Location"
    Source file: `ipi-method/azure-pipelines.yml`

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `deploymentScope` | string | `dc-only` | Which clusters to deploy |
| `enableOdfReplication` | boolean | `false` | Enable ODF DR replication (DC ↔ DR) |
| `odfDrMode` | string | `regional-dr` | Async (`regional-dr`) or sync (`metro-dr`) |
| `enableSubmariner` | boolean | `false` | Enable Submariner cross-cluster networking |
| `terraformAction` | string | `plan` | `plan`, `apply`, or `destroy` |
| `variableGroup` | string | `ocp-baremetal-secrets` | ADO Variable Group for secrets |

## Deployment Scope Options

| Scope | Clusters Deployed |
|-------|------------------|
| `dc-only` | DC Primary only |
| `dr-only` | DR Secondary only |
| `dc-and-dr` | DC + DR (sequential) |
| `mgmt-dc-only` | Mgmt DC only |
| `mgmt-dr-only` | Mgmt DR only |
| `mgmt-clusters` | Mgmt DC + Mgmt DR |
| `all-dc` | DC Primary + Mgmt DC |
| `all-dr` | DR Secondary + Mgmt DR |
| `all` | All 4 clusters |

## Stage Execution Order

![Ipi Pipeline Stage Order](../../../diagrams/code/09-ipi-pipeline-stage-order.svg){: .drawio-diagram }

???+ note "Draw.io Source: Ipi Pipeline Stage Order"
    [:material-download: Download .drawio file](../../../diagrams/code/09-ipi-pipeline-stage-order.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Source Code

```yaml
# =============================================================================
# Azure DevOps Pipeline — OpenShift Multi-Cluster Deployment
# Supports selective deployment: DC, DR, Management, or All
# =============================================================================

trigger:
  branches:
    include:
      - main
  paths:
    include:
      - openshiftbaremetal/**
      - openshiftbaremetal-dr/**
      - mgmt-dc/**
      - mgmt-dr/**

parameters:
  # ---- Deployment Scope Selection ----
  - name: deploymentScope
    displayName: "Deployment Scope"
    type: string
    default: "dc-only"
    values:
      - dc-only                 # DC Primary workload cluster only
      - dr-only                 # DR Secondary workload cluster only
      - dc-and-dr               # Both DC + DR workload clusters
      - mgmt-dc-only            # Management DC cluster only
      - mgmt-dr-only            # Management DR cluster only
      - mgmt-clusters           # Both management clusters (DC + DR)
      - all-dc                  # DC Primary + Management DC
      - all-dr                  # DR Secondary + Management DR
      - all                     # Deploy everything

  # ---- ODF Replication (DC ↔ DR) ----
  - name: enableOdfReplication
    displayName: "Enable ODF DR Replication (DC ↔ DR)"
    type: boolean
    default: false

  - name: odfDrMode
    displayName: "ODF DR Mode"
    type: string
    default: "regional-dr"
    values:
      - regional-dr             # Async replication (RPO: minutes)
      - metro-dr                # Sync replication (RPO: zero)

  # ---- Submariner Cross-Site Networking ----
  - name: enableSubmariner
    displayName: "Enable Submariner (DC ↔ DR cross-cluster networking)"
    type: boolean
    default: false

  # ---- Terraform Action ----
  - name: terraformAction
    displayName: "Terraform Action"
    type: string
    default: "plan"
    values:
      - plan                    # Preview changes only
      - apply                   # Apply changes
      - destroy                 # Tear down infrastructure

  # ---- Variable Group ----
  - name: variableGroup
    displayName: "ADO Variable Group (for secrets)"
    type: string
    default: "ocp-baremetal-secrets"

variables:
  - group: ${{ parameters.variableGroup }}
  - name: TF_IN_AUTOMATION
    value: "true"
  - name: TF_INPUT
    value: "false"
  - name: ARM_SKIP_PROVIDER_REGISTRATION
    value: "true"

# ---- Determine which clusters to deploy ----
# Boolean expressions for each cluster based on deploymentScope parameter
stages:
  # =====================================================================
  # Stage 1: DC Primary Workload Cluster
  # =====================================================================
  - stage: DC_Primary
    displayName: "DC Primary — Workload Cluster"
    condition: |
      and(
        succeeded(),
        or(
          eq('${{ parameters.deploymentScope }}', 'dc-only'),
          eq('${{ parameters.deploymentScope }}', 'dc-and-dr'),
          eq('${{ parameters.deploymentScope }}', 'all-dc'),
          eq('${{ parameters.deploymentScope }}', 'all')
        )
      )
    jobs:
      - job: TerraformDCPrimary
        displayName: "Terraform — DC Primary"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - task: TerraformInstaller@1
            displayName: "Install Terraform"
            inputs:
              terraformVersion: "latest"

          - script: |
              cd openshiftbaremetal
              terraform init -input=false
            displayName: "Terraform Init — DC Primary"

          - script: |
              cd openshiftbaremetal
              # Override Submariner if selected
              EXTRA_ARGS=""
              if [ "${{ parameters.enableSubmariner }}" = "true" ]; then
                EXTRA_ARGS="$EXTRA_ARGS -var enable_submariner=true"
              fi
              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                $EXTRA_ARGS \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" = "apply" ] || [ "${{ parameters.terraformAction }}" = "destroy" ]; then echo "-auto-approve"; fi)
            displayName: "Terraform ${{ parameters.terraformAction }} — DC Primary"
            env:
              TF_VAR_quay_admin_password: $(quay-admin-password)
              TF_VAR_ngc_api_key: $(ngc-api-key)

  # =====================================================================
  # Stage 2: DR Secondary Workload Cluster
  # =====================================================================
  - stage: DR_Secondary
    displayName: "DR Secondary — Workload Cluster"
    condition: |
      and(
        succeeded(),
        or(
          eq('${{ parameters.deploymentScope }}', 'dr-only'),
          eq('${{ parameters.deploymentScope }}', 'dc-and-dr'),
          eq('${{ parameters.deploymentScope }}', 'all-dr'),
          eq('${{ parameters.deploymentScope }}', 'all')
        )
      )
    dependsOn:
      - ${{ if or(eq(parameters.deploymentScope, 'dc-and-dr'), eq(parameters.deploymentScope, 'all')) }}:
          - DC_Primary
    jobs:
      - job: TerraformDRSecondary
        displayName: "Terraform — DR Secondary"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - task: TerraformInstaller@1
            displayName: "Install Terraform"
            inputs:
              terraformVersion: "latest"

          - script: |
              cd openshiftbaremetal-dr
              terraform init -input=false
            displayName: "Terraform Init — DR Secondary"

          - script: |
              cd openshiftbaremetal-dr
              EXTRA_ARGS=""
              # Enable Submariner agent
              if [ "${{ parameters.enableSubmariner }}" = "true" ]; then
                EXTRA_ARGS="$EXTRA_ARGS -var enable_submariner=true"
              fi
              # Enable ODF DR replication
              if [ "${{ parameters.enableOdfReplication }}" = "true" ]; then
                EXTRA_ARGS="$EXTRA_ARGS -var enable_odf_dr=true -var odf_dr_mode=${{ parameters.odfDrMode }}"
              fi
              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                $EXTRA_ARGS \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" = "apply" ] || [ "${{ parameters.terraformAction }}" = "destroy" ]; then echo "-auto-approve"; fi)
            displayName: "Terraform ${{ parameters.terraformAction }} — DR Secondary"
            env:
              TF_VAR_quay_admin_password: $(quay-admin-password)
              TF_VAR_ngc_api_key: $(ngc-api-key)
              TF_VAR_submariner_broker_token: $(submariner-broker-token)
              TF_VAR_odf_dr_s3_access_key: $(odf-dr-s3-access-key)
              TF_VAR_odf_dr_s3_secret_key: $(odf-dr-s3-secret-key)

  # =====================================================================
  # Stage 3: Management Cluster — DC
  # =====================================================================
  - stage: Mgmt_DC
    displayName: "Management Cluster — DC (ACM Hub + ACS + Quay)"
    condition: |
      and(
        succeeded(),
        or(
          eq('${{ parameters.deploymentScope }}', 'mgmt-dc-only'),
          eq('${{ parameters.deploymentScope }}', 'mgmt-clusters'),
          eq('${{ parameters.deploymentScope }}', 'all-dc'),
          eq('${{ parameters.deploymentScope }}', 'all')
        )
      )
    dependsOn:
      - ${{ if or(eq(parameters.deploymentScope, 'all-dc'), eq(parameters.deploymentScope, 'all')) }}:
          - DC_Primary
    jobs:
      - job: TerraformMgmtDC
        displayName: "Terraform — Mgmt DC"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - task: TerraformInstaller@1
            displayName: "Install Terraform"
            inputs:
              terraformVersion: "latest"

          - script: |
              cd mgmt-dc
              terraform init -input=false
            displayName: "Terraform Init — Mgmt DC"

          - script: |
              cd mgmt-dc
              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" = "apply" ] || [ "${{ parameters.terraformAction }}" = "destroy" ]; then echo "-auto-approve"; fi)
            displayName: "Terraform ${{ parameters.terraformAction }} — Mgmt DC"
            env:
              TF_VAR_quay_admin_password: $(quay-admin-password)
              TF_VAR_acs_central_admin_password: $(acs-central-admin-password)
              TF_VAR_acm_s3_access_key: $(acm-s3-access-key)
              TF_VAR_acm_s3_secret_key: $(acm-s3-secret-key)

  # =====================================================================
  # Stage 4: Management Cluster — DR
  # =====================================================================
  - stage: Mgmt_DR
    displayName: "Management Cluster — DR (ACM Standby + ACS + Quay)"
    condition: |
      and(
        succeeded(),
        or(
          eq('${{ parameters.deploymentScope }}', 'mgmt-dr-only'),
          eq('${{ parameters.deploymentScope }}', 'mgmt-clusters'),
          eq('${{ parameters.deploymentScope }}', 'all-dr'),
          eq('${{ parameters.deploymentScope }}', 'all')
        )
      )
    dependsOn:
      - ${{ if or(eq(parameters.deploymentScope, 'mgmt-clusters'), eq(parameters.deploymentScope, 'all')) }}:
          - Mgmt_DC
      - ${{ if eq(parameters.deploymentScope, 'all-dr') }}:
          - DR_Secondary
    jobs:
      - job: TerraformMgmtDR
        displayName: "Terraform — Mgmt DR"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - task: TerraformInstaller@1
            displayName: "Install Terraform"
            inputs:
              terraformVersion: "latest"

          - script: |
              cd mgmt-dr
              terraform init -input=false
            displayName: "Terraform Init — Mgmt DR"

          - script: |
              cd mgmt-dr
              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" = "apply" ] || [ "${{ parameters.terraformAction }}" = "destroy" ]; then echo "-auto-approve"; fi)
            displayName: "Terraform ${{ parameters.terraformAction }} — Mgmt DR"
            env:
              TF_VAR_quay_admin_password: $(quay-admin-password)
              TF_VAR_acm_s3_access_key: $(acm-s3-access-key)
              TF_VAR_acm_s3_secret_key: $(acm-s3-secret-key)

  # =====================================================================
  # Stage 5: Post-Deployment Summary
  # =====================================================================
  - stage: Summary
    displayName: "Deployment Summary"
    dependsOn:
      - DC_Primary
      - DR_Secondary
      - Mgmt_DC
      - Mgmt_DR
```
