# UPI Management DR — terraform.tfvars

Environment-specific values for the UPI Management DR cluster.
Configures ACM Standby, ACS SecuredCluster (pointing to Mgmt DC Central), and Quay Enterprise.

!!! warning "Sensitive Values"
    Replace all `REPLACE_*` placeholders. Store `acm_s3_*` keys and `quay_admin_password` in ADO Variable Groups.

## Key Settings

| Setting | Value | Note |
|---------|-------|------|
| `cluster_name` | `mgmt-dr-upi` | Management DR cluster |
| `base_domain` | `dr.example.com` | DR site domain |
| `machine_network_cidr` | `10.143.42.0/24` | Mgmt DR network |
| `cluster_network_cidr` | `10.140.0.0/14` | Non-overlapping |
| `service_network_cidr` | `172.29.0.0/16` | Non-overlapping |
| ACM | Standby, `release-2.11` | Passive hub |
| ACS | SecuredCluster only | `acs_central_endpoint = central-stackrox.apps.mgmt-dc-upi.example.com:443` |
| Quay Enterprise | `stable-3.12`, all components managed | Geo-replicated |
| LDAP | `enable_ldap = true` | Corporate LDAP identity provider |
| Mirror Operators | Added `redhat-oadp-operator` (stable-1.4), `submariner` (stable-0.18), `odr-hub-operator` (stable-4.16) | Updated |

!!! info "ACM Additional Var Files"
    ACM Cluster Import and DR Applications use separate tfvars files:
    
    - `acm-import.tfvars` — [ACM Import Config](acm-import-tfvars.md)
    - `acm-dr.tfvars` — [ACM DR Config](acm-dr-tfvars.md)

## Source Code

!!! tip "Full Source"
    View the complete 200-line source file at [upi-method/mgmt-dr/terraform.tfvars](../../../../upi-method/mgmt-dr/terraform.tfvars)
