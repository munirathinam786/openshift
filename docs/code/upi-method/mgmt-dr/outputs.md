# UPI Management DR — outputs.tf

Output values for the UPI Management DR cluster.
Exposes ACM Standby console, ACS SecuredCluster status, and Quay Enterprise URLs.

## Outputs

| Output | Description |
|--------|-------------|
| `cluster_name` | Cluster name (`mgmt-dr-upi`) |
| `cluster_domain` | Full domain |
| `api_url` | API server URL (`:6443`) |
| `console_url` | Web console URL |
| `install_method` | `UPI` |
| `boot_method` | `pxe`, `iso`, or `manual` |
| `acm_console_url` | ACM Multicloud Console URL (standby) |
| `acs_central_endpoint` | Remote ACS Central URL (on Mgmt DC) |
| `quay_enterprise_url` | Quay Enterprise registry URL |
| `kubeconfig_path` | Path to kubeconfig on bastion |

## Source Code

!!! tip "Full Source"
    View the complete 43-line source file at [upi-method/mgmt-dr/outputs.tf](../../../../upi-method/mgmt-dr/outputs.tf)
