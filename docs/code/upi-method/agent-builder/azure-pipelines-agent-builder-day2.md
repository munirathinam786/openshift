# Agent Builder Factory — Azure DevOps Pipeline (Day 2 — UPI)

Azure DevOps Pipeline for Day 2 operations of the Agent Builder Factory platform on OpenShift Baremetal (UPI). Supports scaling, LLM model changes, laptop Ollama connectivity, container image updates, secret rotation, and rolling restarts.

## Source Code

```yaml
# Author: Sathishkumar Munirathinam
# Azure DevOps Pipeline — Agent Builder Factory (Day 2 Operations — UPI)
# Handles scaling, model changes, configuration updates, and maintenance (UPI)

trigger: none

parameters:
  - name: operation
    displayName: "Day 2 Operation"
    type: string
    default: "update-config"
    values:
      - update-config
      - scale-services
      - change-llm-model
      - add-laptop-llm
      - remove-laptop-llm
      - rotate-secrets
      - update-images
      - restart-services

  - name: terraformAction
    displayName: "Terraform Action"
    type: string
    default: "plan"
    values:
      - plan
      - apply

  - name: variableGroup
    displayName: "ADO Variable Group"
    type: string
    default: "agent-builder-secrets"

  # ---- Scaling ----
  - name: apiReplicas
    displayName: "Agent Builder API Replicas"
    type: number
    default: 2

  - name: uiReplicas
    displayName: "Agent Builder UI Replicas"
    type: number
    default: 2

  - name: temporalWorkersReplicas
    displayName: "Temporal Workers Replicas"
    type: number
    default: 2

  # ---- LLM Configuration ----
  - name: enableOllama
    displayName: "Enable In-Cluster Ollama"
    type: boolean
    default: true

  - name: ollamaModel
    displayName: "Ollama Model"
    type: string
    default: "llama3"
    values:
      - llama3
      - "llama3:70b"
      - mistral
      - codellama
      - "llama3:8b"
      - deepseek-coder
      - phi3

  - name: enableLocalLLMLaptop
    displayName: "Enable Laptop Ollama"
    type: boolean
    default: false

  - name: localLLMLaptopUrl
    displayName: "Laptop Ollama URL"
    type: string
    default: ""

  # ---- Image Update ----
  - name: imageTag
    displayName: "Container Image Tag"
    type: string
    default: "latest"

variables:
  - group: ${{ parameters.variableGroup }}
  - name: TF_IN_AUTOMATION
    value: "true"
  - name: TF_INPUT
    value: "false"
  - name: WORKING_DIR
    value: "upi-method/agent-builder"

stages:
  # ============================================================================
  # Stage: Scale Services
  # ============================================================================
  - stage: Scale_Services
    displayName: "Scale — Adjust Replicas"
    condition: eq('${{ parameters.operation }}', 'scale-services')
    jobs:
      - job: ScaleServices
        displayName: "Scale Agent Builder Services"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - script: |
              BASTION=$(grep 'bastion_host' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)
              CLUSTER=$(grep 'cluster_name' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)
              NS=$(grep 'agent_builder_namespace' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)

              ssh -o StrictHostKeyChecking=no kni@${BASTION} "
                export KUBECONFIG=/home/kni/ocp/${CLUSTER}/auth/kubeconfig

                echo 'Scaling Agent Builder API to ${{ parameters.apiReplicas }} replicas...'
                oc scale deployment agent-builder-api -n ${NS} --replicas=${{ parameters.apiReplicas }}

                echo 'Scaling Agent Builder UI to ${{ parameters.uiReplicas }} replicas...'
                oc scale deployment agent-builder-ui -n ${NS} --replicas=${{ parameters.uiReplicas }}

                echo 'Scaling Temporal Workers to ${{ parameters.temporalWorkersReplicas }} replicas...'
                oc scale deployment agent-builder-temporal-workers -n ${NS} --replicas=${{ parameters.temporalWorkersReplicas }}

                echo 'Current deployment status:'
                oc get deployments -n ${NS}
              "
            displayName: "Scale Services"

  # ============================================================================
  # Stage: Change LLM Model
  # ============================================================================
  - stage: Change_LLM_Model
    displayName: "Update — LLM Model Configuration"
    condition: |
      or(
        eq('${{ parameters.operation }}', 'change-llm-model'),
        eq('${{ parameters.operation }}', 'add-laptop-llm'),
        eq('${{ parameters.operation }}', 'remove-laptop-llm')
      )
    jobs:
      - job: UpdateLLMConfig
        displayName: "Update LiteLLM + Ollama Configuration"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - task: TerraformInstaller@1
            displayName: "Install Terraform"
            inputs:
              terraformVersion: "latest"

          - script: |
              cd $(WORKING_DIR)
              terraform init -input=false
            displayName: "Terraform Init"

          - script: |
              cd $(WORKING_DIR)
              EXTRA_ARGS=""
              EXTRA_ARGS="$EXTRA_ARGS -var enable_ollama=${{ parameters.enableOllama }}"
              EXTRA_ARGS="$EXTRA_ARGS -var ollama_model=${{ parameters.ollamaModel }}"
              EXTRA_ARGS="$EXTRA_ARGS -var enable_local_llm_laptop=${{ parameters.enableLocalLLMLaptop }}"

              if [ "${{ parameters.enableLocalLLMLaptop }}" = "True" ] && [ -n "${{ parameters.localLLMLaptopUrl }}" ]; then
                EXTRA_ARGS="$EXTRA_ARGS -var local_llm_laptop_url=${{ parameters.localLLMLaptopUrl }}"
              fi

              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                $EXTRA_ARGS \
                -target=module.ollama \
                -target=module.litellm \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" = "apply" ]; then echo "-auto-approve"; fi)
            displayName: "Terraform ${{ parameters.terraformAction }} — LLM Configuration"
            env:
              TF_VAR_postgres_password: $(postgres-password)
              TF_VAR_mongodb_root_password: $(mongodb-root-password)
              TF_VAR_redis_password: $(redis-password)
              TF_VAR_litellm_master_key: $(litellm-master-key)
              TF_VAR_anthropic_api_key: $(anthropic-api-key)
              TF_VAR_azure_openai_key: $(azure-openai-key)
              TF_VAR_openai_api_key: $(openai-api-key)

          - script: |
              BASTION=$(grep 'bastion_host' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)
              CLUSTER=$(grep 'cluster_name' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)
              NS=$(grep 'agent_builder_namespace' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)

              ssh -o StrictHostKeyChecking=no kni@${BASTION} "
                export KUBECONFIG=/home/kni/ocp/${CLUSTER}/auth/kubeconfig

                echo 'Restarting LiteLLM to pick up new config...'
                oc rollout restart deployment/agent-builder-litellm -n ${NS}
                oc rollout status deployment/agent-builder-litellm -n ${NS} --timeout=300s

                if oc get deployment agent-builder-ollama -n ${NS} 2>/dev/null; then
                  echo 'Ollama model pull status:'
                  oc logs deployment/agent-builder-ollama -n ${NS} --tail=20
                fi
              "
            displayName: "Restart LiteLLM & Verify"
            condition: eq('${{ parameters.terraformAction }}', 'apply')

  # ============================================================================
  # Stage: Update Images
  # ============================================================================
  - stage: Update_Images
    displayName: "Update — Container Images"
    condition: eq('${{ parameters.operation }}', 'update-images')
    jobs:
      - job: UpdateImages
        displayName: "Rolling Update to New Image Tag"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - task: TerraformInstaller@1
            displayName: "Install Terraform"
            inputs:
              terraformVersion: "latest"

          - script: |
              cd $(WORKING_DIR)
              terraform init -input=false
            displayName: "Terraform Init"

          - script: |
              cd $(WORKING_DIR)
              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                -var image_tag=${{ parameters.imageTag }} \
                -var enable_ollama=${{ parameters.enableOllama }} \
                -var ollama_model=${{ parameters.ollamaModel }} \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" = "apply" ]; then echo "-auto-approve"; fi)
            displayName: "Terraform ${{ parameters.terraformAction }} — Update Images"
            env:
              TF_VAR_postgres_password: $(postgres-password)
              TF_VAR_mongodb_root_password: $(mongodb-root-password)
              TF_VAR_redis_password: $(redis-password)
              TF_VAR_litellm_master_key: $(litellm-master-key)
              TF_VAR_anthropic_api_key: $(anthropic-api-key)
              TF_VAR_azure_openai_key: $(azure-openai-key)
              TF_VAR_openai_api_key: $(openai-api-key)
              TF_VAR_github_token: $(github-token)

  # ============================================================================
  # Stage: Restart Services
  # ============================================================================
  - stage: Restart_Services
    displayName: "Restart — All Services"
    condition: eq('${{ parameters.operation }}', 'restart-services')
    jobs:
      - job: RestartServices
        displayName: "Rolling Restart All Deployments"
        pool:
          name: "self-hosted-linux"
        steps:
          - checkout: self

          - script: |
              BASTION=$(grep 'bastion_host' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)
              CLUSTER=$(grep 'cluster_name' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)
              NS=$(grep 'agent_builder_namespace' $(WORKING_DIR)/terraform.tfvars | cut -d'"' -f2)

              ssh -o StrictHostKeyChecking=no kni@${BASTION} "
                export KUBECONFIG=/home/kni/ocp/${CLUSTER}/auth/kubeconfig

                echo '=== Rolling Restart All Agent Builder Services ==='
                for deploy in \$(oc get deployments -n ${NS} -o name); do
                  echo \"Restarting \${deploy}...\"
                  oc rollout restart \${deploy} -n ${NS}
                done

                echo ''
                echo 'Waiting for rollouts to complete...'
                for deploy in \$(oc get deployments -n ${NS} -o name); do
                  oc rollout status \${deploy} -n ${NS} --timeout=300s || echo \"Warning: \${deploy} rollout timed out\"
                done

                echo ''
                echo '=== Final Status ==='
                oc get pods -n ${NS}
              "
            displayName: "Restart All Services"

  # ============================================================================
  # Stage: Summary
  # ============================================================================
  - stage: Summary
    displayName: "Summary"
    dependsOn:
      - Scale_Services
      - Change_LLM_Model
      - Update_Images
      - Restart_Services
    condition: always()
    jobs:
      - job: SummaryJob
        displayName: "Day 2 Operation Summary"
        pool:
          name: "self-hosted-linux"
        steps:
          - script: |
              echo "============================================="
              echo "  Agent Builder — Day 2 Operation Summary"
              echo "============================================="
              echo ""
              echo "Operation:        ${{ parameters.operation }}"
              echo "Action:           ${{ parameters.terraformAction }}"
              echo "Ollama Enabled:   ${{ parameters.enableOllama }}"
              echo "Ollama Model:     ${{ parameters.ollamaModel }}"
              echo "Laptop LLM:      ${{ parameters.enableLocalLLMLaptop }}"
              echo "Image Tag:        ${{ parameters.imageTag }}"
              echo ""
              echo "============================================="
            displayName: "Operation Summary"
```
