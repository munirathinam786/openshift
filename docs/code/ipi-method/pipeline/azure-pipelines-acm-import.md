# IPI — Azure DevOps Pipeline — azure-pipelines-acm-import.yml

Pipeline for importing workload clusters into ACM Hub as ManagedClusters.
Supports selective import scope, ManagedClusterSet creation, and post-import validation.

!!! info "Pipeline Location"
    Source file: `ipi-method/azure-pipelines-acm-import.yml`

!!! tip "High-Level Documentation"
    See [ACM Cluster Import Pipeline](../../../pipeline/terraform-acm-import-pipeline.md) for workflow details, prerequisites, and usage guide.

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `importScope` | string | `all-workload` | Clusters to import (`dc-primary-only`, `dr-secondary-only`, `all-workload`) |
| `acmHub` | string | `mgmt-dc` | ACM Hub cluster target |
| `enableClusterImport` | boolean | `true` | Enable ManagedCluster + KlusterletAddonConfig |
| `enableClusterSet` | boolean | `true` | Create ManagedClusterSet |
| `terraformAction` | string | `plan` | `plan`, `apply`, or `destroy` |
| `variableGroup` | string | `ocp-baremetal-acm-secrets` | ADO Variable Group |

## Source Code

```yaml
# =============================================================================
# Azure DevOps Pipeline — ACM Cluster Import
# Imports workload clusters into ACM Hub as managed clusters and creates
# ManagedClusterSet for logical grouping.
# Runs on the Management DC (ACM Hub).
# =============================================================================

trigger: none   # ACM import is always manual — never auto-triggered

parameters:
  # ---- Cluster Import Scope ----
  - name: importScope
    displayName: "Clusters to Import"
    type: string
    default: "all-workload"
    values:
      - dc-primary-only
      - dr-secondary-only
      - all-workload

  # ---- ACM Hub Target ----
  - name: acmHub
    displayName: "ACM Hub Cluster (where to import)"
    type: string
    default: "mgmt-dc"
    values:
      - mgmt-dc
      - mgmt-dr

  # ---- Feature Toggles ----
  - name: enableClusterImport
    displayName: "Enable Cluster Import (ManagedCluster + KlusterletAddonConfig)"
    type: boolean
    default: true

  - name: enableClusterSet
    displayName: "Create ManagedClusterSet for grouping"
    type: boolean
    default: true

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
    default: "ocp-baremetal-acm-secrets"

variables:
  - group: ${{ parameters.variableGroup }}
  - name: TF_IN_AUTOMATION
    value: "true"
  - name: TF_INPUT
    value: "false"

stages:
  # =====================================================================
  # Stage 1: ACM Cluster Import — Import workload clusters into ACM Hub
  # =====================================================================
  - stage: ACM_Cluster_Import
    displayName: "ACM Cluster Import — ${{ parameters.acmHub }}"
    condition: succeeded()
    jobs:
      - job: ACMClusterImport
        displayName: "Terraform ACM Import — ${{ parameters.acmHub }}"
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
              # Feature toggles from pipeline parameters
              EXTRA_ARGS="$EXTRA_ARGS -var enable_acm_cluster_import=${{ parameters.enableClusterImport }}"
              EXTRA_ARGS="$EXTRA_ARGS -var enable_acm_cluster_set=${{ parameters.enableClusterSet }}"

              # Scope: which clusters to import
              EXTRA_ARGS="$EXTRA_ARGS -var acm_import_scope=${{ parameters.importScope }}"

              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                -var-file=acm-import.tfvars \
                $EXTRA_ARGS \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" = "apply" ] || [ "${{ parameters.terraformAction }}" = "destroy" ]; then echo "-auto-approve"; fi)
            displayName: "Terraform ${{ parameters.terraformAction }} — ACM Cluster Import"
            env:
              TF_VAR_dc_primary_kubeconfig: $(dc-primary-kubeconfig-path)
              TF_VAR_dr_secondary_kubeconfig: $(dr-secondary-kubeconfig-path)

  # =====================================================================
  # Stage 2: Validate Import — Check all ManagedClusters are Available
  # =====================================================================
  - stage: Validate_Import
    displayName: "Validate — Cluster Import Status"
    dependsOn: ACM_Cluster_Import
    condition: and(succeeded(), eq('${{ parameters.terraformAction }}', 'apply'))
    jobs:
      - job: ValidateImport
        displayName: "Validate ManagedCluster Status"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - script: |
              echo "=== Checking ManagedCluster status on ACM Hub ==="
              export KUBECONFIG=/opt/ocp/${{ parameters.acmHub }}/auth/kubeconfig

              echo ""
              echo "--- ManagedClusters ---"
              oc get managedclusters -o wide

              echo ""
              echo "--- ManagedClusterSets ---"
              oc get managedclusterset -o wide

              echo ""
              echo "--- KlusterletAddonConfig ---"
              oc get klusterletaddonconfig --all-namespaces

              echo ""
              echo "--- Checking availability ---"
              FAILED=0
              for CLUSTER in $(oc get managedclusters -o jsonpath='{.items[*].metadata.name}'); do
                STATUS=$(oc get managedcluster $CLUSTER -o jsonpath='{.status.conditions[?(@.type=="ManagedClusterConditionAvailable")].status}')
                if [ "$STATUS" != "True" ]; then
                  echo "WARNING: Cluster $CLUSTER is NOT Available (status=$STATUS)"
                  FAILED=1
                else
                  echo "OK: Cluster $CLUSTER is Available"
                fi
              done

              if [ $FAILED -eq 1 ]; then
                echo ""
                echo "WARNING: One or more clusters are not in Available state."
                echo "Check the ACM console for more details."
              fi
            displayName: "Validate ManagedCluster Availability"
```
