# UPI DR Secondary — outputs.tf

Output values for the UPI DR Secondary workload cluster.
Includes standard cluster endpoints plus **Submariner agent status** and **ODF DR replication status**.

## Outputs

| Output | Description |
|--------|-------------|
| `cluster_name` | Cluster name (`ocp-ai-upi-dr`) |
| `cluster_domain` | Full domain (`ocp-ai-upi-dr.dr.example.com`) |
| `api_url` | API server URL (`:6443`) |
| `console_url` | Web console URL |
| `openshift_ai_dashboard_url` | OpenShift AI dashboard (if enabled) |
| `kubeconfig_path` | Path to kubeconfig on bastion |
| `install_method` | `UPI (User Provisioned Infrastructure)` |
| `boot_method` | `pxe`, `iso`, or `manual` |
| `submariner_status` | Agent role, broker URL, cable driver, gateway count, globalnet |
| `odf_dr_status` | Mode, peer cluster, replication schedule, S3 bucket |

## Source Code

!!! tip "Full Source"
    View the complete 75-line source file at [upi-method/openshiftbaremetal-dr/outputs.tf](../../../../upi-method/openshiftbaremetal-dr/outputs.tf)
