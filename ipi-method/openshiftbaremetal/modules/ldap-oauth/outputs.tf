# Author: Sathishkumar Munirathinam

output "ldap_provider_name" {
  description = "Name of the configured LDAP identity provider"
  value       = var.ldap_provider_name
}

output "ldap_group_sync_enabled" {
  description = "Whether LDAP group sync CronJob was created"
  value       = var.enable_ldap_group_sync
}

output "kubeadmin_removed" {
  description = "Whether kubeadmin secret was deleted"
  value       = var.disable_kubeadmin
}
