# UPI Management DC — outputs.tf

Output values for the UPI Management DC cluster.
Exposes ACM Hub console, ACS Central, and Quay Enterprise URLs.

## Outputs

| Output | Description |
|--------|-------------|
| `cluster_name` | Cluster name (`mgmt-dc-upi`) |
| `cluster_domain` | Full domain |
| `api_url` | API server URL (`:6443`) |
| `console_url` | Web console URL |
| `install_method` | `UPI` |
| `boot_method` | `pxe`, `iso`, or `manual` |
| `acm_console_url` | ACM Multicloud Console URL |
| `acs_central_url` | ACS Central (StackRox) URL |
| `quay_enterprise_url` | Quay Enterprise registry URL |
| `kubeconfig_path` | Path to kubeconfig on bastion |

## Source Code

!!! tip "Full Source"
    View the complete 47-line source file at [upi-method/mgmt-dc/outputs.tf](../../../../upi-method/mgmt-dc/outputs.tf)
