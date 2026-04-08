# Author: Sathishkumar Munirathinam

# =============================================================================
# OpenShift GitOps (Argo CD) Module — Outputs
# =============================================================================

output "argocd_namespace" {
  description = "Namespace where ArgoCD is deployed"
  value       = "openshift-gitops"
}

output "argocd_route" {
  description = "ArgoCD server route URL"
  value       = "https://openshift-gitops-server-openshift-gitops.apps.${split(".", var.kubeconfig)[0]}"
}

output "argocd_cluster_admin" {
  description = "Whether ArgoCD has cluster-admin privileges"
  value       = var.argocd_cluster_admin
}
