# UPI Method — azure-pipelines-upi.yml

Azure DevOps pipeline for phased UPI deployment of OpenShift on bare metal.

## Key Differences from IPI Pipeline

| Aspect | IPI Pipeline | UPI Pipeline |
|--------|-------------|-------------|
| **Stages** | 5 (per-cluster) | 6 (per-phase) |
| **Scope** | Multi-cluster deployment | Single UPI cluster phases |
| **Boot control** | Automated via BMC | PXE / ISO / Manual gate |
| **Parameters** | `deploymentScope` | `deploymentPhase` + `bootMethod` |
| **Manual gates** | None | ManualValidation for `manual` boot |

## Source Code

```yaml
# =============================================================================
# Azure DevOps Pipeline — OpenShift UPI Baremetal Deployment
# UPI-specific: multi-phase install with manual node boot steps
# =============================================================================

trigger:
  branches:
    include:
      - main
  paths:
    include:
      - upi-method/**

parameters:
  # ---- Boot Method ----
  - name: bootMethod
    displayName: "Node Boot Method"
    type: string
    default: "pxe"
    values:
      - pxe
      - iso
      - manual

  # ---- Deployment Phase ----
  - name: deploymentPhase
    displayName: "Deployment Phase"
    type: string
    default: "full"
    values:
      - prerequisites
      - ignition
      - bootstrap
      - compute
      - day2-operators
      - full

  # ---- Terraform Action ----
  - name: terraformAction
    displayName: "Terraform Action"
    type: string
    default: "plan"
    values:
      - plan
      - apply
      - destroy

  # ---- ODF Replication ----
  - name: enableOdfReplication
    displayName: "Enable ODF DR Replication (DC ↔ DR)"
    type: boolean
    default: false

  - name: odfDrMode
    displayName: "ODF DR Mode"
    type: string
    default: "regional-dr"
    values:
      - regional-dr
      - metro-dr

  # ---- Submariner ----
  - name: enableSubmariner
    displayName: "Enable Submariner"
    type: boolean
    default: false

  # ---- Variable Group ----
  - name: variableGroup
    displayName: "ADO Variable Group (for secrets)"
    type: string
    default: "ocp-baremetal-upi-secrets"

variables:
  - group: ${{ parameters.variableGroup }}
  - name: TF_IN_AUTOMATION
    value: "true"
  - name: TF_INPUT
    value: "false"
  - name: WORKING_DIR
    value: "upi-method"

stages:
  # Stage 1: Prerequisites
  - stage: Prerequisites
    displayName: "Prerequisites — DNS + HAProxy LB + Quay Mirror"
    condition: |
      and(succeeded(),
        or(eq('${{ parameters.deploymentPhase }}', 'prerequisites'),
           eq('${{ parameters.deploymentPhase }}', 'full')))
    jobs:
      - job: TerraformPrerequisites
        pool: { name: "self-hosted-linux" }
        steps:
          - checkout: self
          - task: TerraformInstaller@1
            inputs: { terraformVersion: "latest" }
          - script: cd $(WORKING_DIR) && terraform init -input=false
          - script: |
              cd $(WORKING_DIR)
              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                -var boot_method=${{ parameters.bootMethod }} \
                -target=module.dns -target=module.haproxy -target=module.quay_mirror \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" != "plan" ]; then echo "-auto-approve"; fi)

  # Stage 2: Ignition
  - stage: Ignition
    displayName: "Generate install-config + Ignition Configs"
    # ... (targets: install_config, ignition, ignition_server)

  # Stage 3: Bootstrap
  - stage: Bootstrap
    displayName: "Boot Bootstrap + Control Plane Nodes"
    # ... (targets: bootstrap, control_plane, bootstrap_complete)
    # Includes ManualValidation gate when bootMethod=manual

  # Stage 4: Compute
  - stage: Compute
    displayName: "Boot Compute Nodes + Approve CSRs"
    # ... (targets: compute_nodes, cluster_complete)

  # Stage 5: Day-2 Operators
  - stage: Day2_Operators
    displayName: "Day-2 Operators — GPU, ODF, AI, Monitoring"
    # ... (full apply with all day-2 modules)

  # Stage 6: Summary
  - stage: Summary
    displayName: "Deployment Summary"
    # ... prints UPI deployment summary
```
