# UPI Method — outputs.tf

Outputs for the UPI baremetal deployment (`upi-method/`).

## UPI-Specific Outputs

In addition to the standard cluster outputs, UPI exposes:

| Output | Description |
|--------|-------------|
| `install_dir` | Path to the install directory on bastion |
| `install_method` | Always `UPI (User Provisioned Infrastructure)` |
| `boot_method` | The configured boot method (`pxe`, `iso`, or `manual`) |

## Source Code

```hcl
# =============================================================================
# Outputs
# =============================================================================

output "cluster_name" {
  value = var.cluster_name
}

output "cluster_domain" {
  value = "${var.cluster_name}.${var.base_domain}"
}

output "api_url" {
  value = "https://api.${var.cluster_name}.${var.base_domain}:6443"
}

output "console_url" {
  value = "https://console-openshift-console.apps.${var.cluster_name}.${var.base_domain}"
}

output "openshift_ai_dashboard_url" {
  value = var.enable_openshift_ai ? "https://rhods-dashboard-redhat-ods-applications.apps.${var.cluster_name}.${var.base_domain}" : ""
}

output "kubeconfig_path" {
  value = "${var.install_dir}/auth/kubeconfig"
}

output "install_dir" {
  value = var.install_dir
}

output "install_method" {
  value = "UPI (User Provisioned Infrastructure)"
}

output "boot_method" {
  value = var.boot_method
}
```
