# =============================================================================
# OpenShift Pipelines (Tekton) Module — Outputs
# =============================================================================

output "pipelines_namespace" {
  description = "Namespace where Tekton Pipelines is deployed"
  value       = "openshift-pipelines"
}

output "tekton_profile" {
  description = "TektonConfig profile applied"
  value       = var.tekton_profile
}

output "pipelines_as_code_enabled" {
  description = "Whether Pipelines-as-Code is enabled"
  value       = var.enable_pipelines_as_code
}
