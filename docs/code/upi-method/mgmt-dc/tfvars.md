# UPI Management DC — terraform.tfvars

Environment-specific values for the UPI Management DC cluster.
Configures ACM Hub, ACS Central, and Quay Enterprise with ODF storage.

!!! warning "Sensitive Values"
    Replace all `REPLACE_*` placeholders. Store `acs_central_admin_password`, `acm_s3_*` keys, and `quay_admin_password` in ADO Variable Groups.

## Key Settings

| Setting | Value | Note |
|---------|-------|------|
| `cluster_name` | `mgmt-dc-upi` | Management DC cluster |
| `base_domain` | `example.com` | DC site domain |
| `machine_network_cidr` | `10.142.42.0/24` | Mgmt DC network |
| `cluster_network_cidr` | `10.136.0.0/14` | Non-overlapping |
| `service_network_cidr` | `172.28.0.0/16` | Non-overlapping |
| ACM | Hub, `release-2.11`, observability enabled | Manages all clusters |
| ACS | Central + SecuredCluster, `stable` channel | Security scanning |
| Quay Enterprise | `stable-3.12`, all components managed | Container registry |
| LDAP | `enable_ldap = true` | Corporate LDAP identity provider |
| Mirror Operators | Added `redhat-oadp-operator` (stable-1.4), `submariner` (stable-0.18), `odr-hub-operator` (stable-4.16) | Updated |

!!! info "ACM Additional Var Files"
    ACM Cluster Import and DR Applications use separate tfvars files:
    
    - `acm-import.tfvars` — [ACM Import Config](acm-import-tfvars.md)
    - `acm-dr.tfvars` — [ACM DR Config](acm-dr-tfvars.md)

## Source Code

!!! tip "Full Source"
    View the complete 201-line source file at [upi-method/mgmt-dc/terraform.tfvars](../../../../upi-method/mgmt-dc/terraform.tfvars)
