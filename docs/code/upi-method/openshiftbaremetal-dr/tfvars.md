# UPI DR Secondary — terraform.tfvars

Environment-specific values for the UPI DR Secondary workload cluster.
Edit this file to match your DR site infrastructure before running `terraform apply`.

!!! warning "Sensitive Values"
    Replace all `REPLACE_*` placeholders with actual values.
    Store secrets like `quay_admin_password`, `ngc_api_key`, `submariner_broker_token`, and ODF DR S3 keys in Azure DevOps Variable Groups — not in this file.

## Key DR-Specific Values

| Setting | Value | Note |
|---------|-------|------|
| `cluster_name` | `ocp-ai-upi-dr` | DR site cluster |
| `base_domain` | `dr.example.com` | DR DNS domain |
| `machine_network_cidr` | `10.143.41.0/24` | DR site machine network |
| `cluster_network_cidr` | `10.132.0.0/14` | Non-overlapping with DC (`10.128.0.0/14`) |
| `service_network_cidr` | `172.31.0.0/16` | Non-overlapping with DC (`172.30.0.0/16`) |
| Submariner role | Agent | Connects to DC Primary broker |
| ODF DR peer | `ocp-ai-upi` | Points to DC Primary cluster |
| LDAP | `enable_ldap = true` | Corporate LDAP identity provider |

## Source Code

!!! tip "Full Source"
    View the complete 246-line source file at [upi-method/openshiftbaremetal-dr/terraform.tfvars](../../../../upi-method/openshiftbaremetal-dr/terraform.tfvars)
