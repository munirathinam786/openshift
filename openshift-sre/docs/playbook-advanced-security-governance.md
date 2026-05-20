# Advanced Security & Governance Playbook

![Advanced security and governance service map](assets/diagrams/advanced-security-governance.svg)

This playbook covers the deeper posture services that help answer:

- **Is multi-cluster governance healthy across ACM, ACS, and platform patterns?**
- **Do backup, disaster-recovery, and virtualization layers match expectations?**
- **Are lifecycle, operator, and identity controls drifting across the fleet?**
- **Can we explain security and governance posture cluster-by-cluster?**

## ACM hub posture

Use: `list_acm_multicluster_hubs`

What to look for:

- hub resources missing from the management cluster
- components not available or obviously degraded
- more than one hub pattern where the fleet design expects a single control point

Suggested prompts:

- `Summarize ACM hub posture and whether fleet governance looks healthy.`

## Managed-cluster coverage

Use: `list_acm_managed_clusters`

What to look for:

- clusters missing from ACM enrollment
- unavailable or detached clusters in important environments
- platform-pattern skew across ROSA, ARO, baremetal, and IBM Z footprints

Suggested prompts:

- `Review ACM managed-cluster coverage and summarize the highest-risk fleet gaps.`

## ACM governance policies

Use: `list_acm_policies`

What to look for:

- policies stuck in non-compliant or unknown states
- governance coverage missing in shared or regulated clusters
- policy posture drifting differently across platform patterns

Suggested prompts:

- `Summarize ACM governance policy compliance and highlight the most important drift.`

## ACS service and secured-cluster posture

Use:

- `list_acs_central_services`
- `list_acs_secured_clusters`

What to look for:

- ACS central components not ready
- secured-cluster rollout incomplete across the known fleet
- a mismatch between ACM-managed clusters and ACS-secured clusters

Suggested prompts:

- `Review ACS platform coverage and summarize where cluster protection still looks incomplete.`

## Disaster recovery and backup readiness

Use:

- `list_oadp_resources`
- `list_disaster_recovery_resources`

What to look for:

- backup schedules or backup-storage locations missing where recovery is expected
- DR resources present but not obviously bound to the right applications or clusters
- stale recovery posture in failover or migration-sensitive environments

Suggested prompts:

- `Inspect OADP and disaster-recovery resources and summarize recovery readiness gaps.`

## Virtualization and workload mobility

Use: `list_virtualization_resources`

What to look for:

- VM, VMI, or migration posture not matching workload expectations
- virtualization resources concentrated in clusters without the expected supporting platform services
- mobility or migration workflows that appear blocked by infrastructure drift

Suggested prompts:

- `Review OpenShift Virtualization posture and summarize the biggest workload-mobility risks.`

## Identity and cluster-access governance

Use: `list_oauth_configuration`

What to look for:

- inconsistent provider posture across clusters
- cluster access paths that drift from the intended enterprise auth pattern
- emergency or legacy identity providers still active in sensitive estates

Suggested prompts:

- `Compare OAuth and identity-provider posture across clusters and summarize governance drift.`

## Platform lifecycle and operator governance

Use:

- `list_cluster_infrastructure`
- `list_machine_config_pools`
- `list_machine_sets`
- `list_operator_subscriptions`
- `list_cluster_service_versions`

What to look for:

- upgrade readiness issues hidden behind degraded operators or machine config drift
- machine-set posture inconsistent with the infrastructure pattern
- OLM subscriptions or CSVs stuck before or after platform updates

Suggested prompts:

- `Summarize platform lifecycle readiness across machine config, Machine API, and OLM posture.`

## Combined workflow

Suggested prompt:

- `Summarize ACM hubs, managed clusters, ACM policies, ACS coverage, OADP resources, disaster-recovery resources, virtualization posture, and OAuth drift into one governance review.`
- `Compare platform lifecycle readiness, virtualization posture, and recovery readiness across ROSA, ARO, baremetal, and IBM Z clusters.`

Operator actions:

1. confirm ACM and ACS coverage matches the clusters you actually operate
2. compare governance drift across platform patterns instead of treating the fleet as homogeneous
3. verify backup and DR resources exist where recovery promises have been made
4. inspect virtualization posture anywhere VM migration or CNV adoption matters
5. compare OAuth, Machine API, and OLM posture before planning upgrades or failovers
