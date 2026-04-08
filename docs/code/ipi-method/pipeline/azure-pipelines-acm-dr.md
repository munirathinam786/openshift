# IPI — Azure DevOps Pipeline — azure-pipelines-acm-dr.yml

Pipeline for configuring DRPolicy, DRPlacementControl, and executing failover/failback actions via ACM and OpenShift DR.

!!! info "Pipeline Location"
    Source file: `ipi-method/azure-pipelines-acm-dr.yml`

!!! tip "High-Level Documentation"
    See [ACM DR Failover/Failback Pipeline](../../../pipeline/terraform-acm-dr-pipeline.md) for workflow details, prerequisites, and usage guide.

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `drAction` | string | `none` | DR action (`none`, `failover`, `failback`, `relocate`) |
| `acmHub` | string | `mgmt-dc` | ACM Hub cluster (DR control plane) |
| `configureDRPolicy` | boolean | `true` | Configure DRPolicy + DRPlacementControl |
| `executeDRAction` | boolean | `false` | Execute the failover/failback action |
| `applicationScope` | string | `all` | Applications to protect/failover |
| `terraformAction` | string | `plan` | `plan`, `apply`, or `destroy` |
| `variableGroup` | string | `ocp-baremetal-acm-dr-secrets` | ADO Variable Group |

## Source Code

```yaml
# =============================================================================
# Azure DevOps Pipeline — ACM DR Failover / Failback
# Configures DRPolicy, DRPlacementControl for protected applications and
# triggers Failover or Failback (Relocate) actions on the ACM Hub.
# =============================================================================

trigger: none   # DR operations are always manual — never auto-triggered

parameters:
  # ---- DR Action ----
  - name: drAction
    displayName: "DR Action"
    type: string
    default: "none"
    values:
      - none
      - failover
      - failback
      - relocate

  # ---- ACM Hub Target ----
  - name: acmHub
    displayName: "ACM Hub Cluster (DR control plane)"
    type: string
    default: "mgmt-dc"
    values:
      - mgmt-dc
      - mgmt-dr

  # ---- Configuration vs Execution ----
  - name: configureDRPolicy
    displayName: "Configure DRPolicy + DRPlacementControl (initial setup)"
    type: boolean
    default: true

  - name: executeDRAction
    displayName: "Execute Failover/Failback Action"
    type: boolean
    default: false

  # ---- Application Selection ----
  - name: applicationScope
    displayName: "Applications to protect/failover"
    type: string
    default: "all"
    values:
      - all
      - selected

  # ---- Terraform Action ----
  - name: terraformAction
    displayName: "Terraform Action"
    type: string
    default: "plan"
    values:
      - plan
      - apply
      - destroy

  # ---- Variable Group ----
  - name: variableGroup
    displayName: "ADO Variable Group (for secrets)"
    type: string
    default: "ocp-baremetal-acm-dr-secrets"

variables:
  - group: ${{ parameters.variableGroup }}
  - name: TF_IN_AUTOMATION
    value: "true"
  - name: TF_INPUT
    value: "false"

stages:
  # =====================================================================
  # Stage 1: Configure DR — DRPolicy + DRPlacementControl + ODR Hub Operator
  # =====================================================================
  - stage: Configure_DR
    displayName: "Configure DR — DRPolicy & Applications"
    condition: |
      and(
        succeeded(),
        eq('${{ parameters.configureDRPolicy }}', 'True')
      )
    jobs:
      - job: ConfigureDR
        displayName: "Terraform DR Configuration — ${{ parameters.acmHub }}"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - task: TerraformInstaller@1
            displayName: "Install Terraform"
            inputs:
              terraformVersion: "latest"

          - script: |
              cd ${{ parameters.acmHub }}
              terraform init -input=false
            displayName: "Terraform Init — ${{ parameters.acmHub }}"

          - script: |
              cd ${{ parameters.acmHub }}
              EXTRA_ARGS=""
              EXTRA_ARGS="$EXTRA_ARGS -var enable_acm_dr_apps=true"
              EXTRA_ARGS="$EXTRA_ARGS -var dr_action=none"

              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                -var-file=acm-dr.tfvars \
                $EXTRA_ARGS \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" = "apply" ] || [ "${{ parameters.terraformAction }}" = "destroy" ]; then echo "-auto-approve"; fi)
            displayName: "Terraform ${{ parameters.terraformAction }} — DR Configuration"
            env:
              TF_VAR_channel_git_token: $(channel-git-token)

  # =====================================================================
  # Stage 2: Execute DR Action — Failover or Failback (Relocate)
  # =====================================================================
  - stage: Execute_DR_Action
    displayName: "Execute DR — ${{ parameters.drAction }}"
    condition: |
      and(
        succeeded(),
        eq('${{ parameters.executeDRAction }}', 'True'),
        ne('${{ parameters.drAction }}', 'none')
      )
    dependsOn:
      - ${{ if eq(parameters.configureDRPolicy, true) }}:
          - Configure_DR
    jobs:
      - job: ExecuteDRAction
        displayName: "Terraform DR ${{ parameters.drAction }} — ${{ parameters.acmHub }}"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - task: TerraformInstaller@1
            displayName: "Install Terraform"
            inputs:
              terraformVersion: "latest"

          - script: |
              cd ${{ parameters.acmHub }}
              terraform init -input=false
            displayName: "Terraform Init — ${{ parameters.acmHub }}"

          - script: |
              cd ${{ parameters.acmHub }}
              EXTRA_ARGS=""
              EXTRA_ARGS="$EXTRA_ARGS -var enable_acm_dr_apps=true"
              EXTRA_ARGS="$EXTRA_ARGS -var dr_action=${{ parameters.drAction }}"

              terraform apply \
                -var-file=terraform.tfvars \
                -var-file=acm-dr.tfvars \
                $EXTRA_ARGS \
                -input=false \
                -auto-approve
            displayName: "Terraform Apply — DR ${{ parameters.drAction }}"
            env:
              TF_VAR_channel_git_token: $(channel-git-token)

  # =====================================================================
  # Stage 3: Validate DR — Check application placement and DR status
  # =====================================================================
  - stage: Validate_DR
    displayName: "Validate — DR Status"
    dependsOn:
      - ${{ if eq(parameters.executeDRAction, true) }}:
          - Execute_DR_Action
      - ${{ if and(eq(parameters.configureDRPolicy, true), eq(parameters.executeDRAction, false)) }}:
          - Configure_DR
    condition: and(succeeded(), eq('${{ parameters.terraformAction }}', 'apply'))
    jobs:
      - job: ValidateDR
        displayName: "Validate DR Status"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - script: |
              echo "=== DR Validation on ACM Hub ==="
              export KUBECONFIG=/opt/ocp/${{ parameters.acmHub }}/auth/kubeconfig

              echo ""
              echo "--- DRPolicy ---"
              oc get drpolicy -o wide

              echo ""
              echo "--- DRClusters ---"
              oc get drclusters -o wide

              echo ""
              echo "--- DRPlacementControl (all namespaces) ---"
              oc get drplacementcontrol --all-namespaces -o wide

              echo ""
              echo "--- Application Placement ---"
              oc get placement --all-namespaces -o wide
            displayName: "Validate DR Status"
```
