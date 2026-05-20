# FinOps & Optimization Playbook

This playbook covers capacity posture, namespace pressure, storage efficiency, and platform optimization signals that operators can review directly from the OpenShift estate.

## Cluster infrastructure summary

Use: `list_cluster_infrastructure`

What to look for:

- platform-pattern mismatches across clusters
- worker footprint or topology that no longer matches intended sizing
- infrastructure signals that suggest a cluster is overbuilt, underbuilt, or drifting from design

Suggested prompts:

- `Summarize cluster infrastructure posture and call out obvious scaling or platform-pattern concerns.`

## Node and workload pressure

Use:

- `list_nodes`
- `list_workload_health`

What to look for:

- nodes that are ready but clearly under strain
- repeated workload rollouts failing because of capacity or scheduling pressure
- unhealthy workloads clustering in the same pool, zone, or platform slice

Suggested prompts:

- `Review node and workload posture and summarize where cluster capacity looks tight or inefficient.`

## Namespace quota governance

Use: `list_resource_quotas`

What to look for:

- shared namespaces without quota guardrails
- quota shapes that do not match the workload class they are supposed to protect
- clusters where project-level governance is too loose to support safe multi-tenancy

Suggested prompts:

- `Inspect resource quota posture and summarize the biggest namespace-governance gaps.`

## Persistent storage posture

Use:

- `list_persistent_storage`
- `list_storage_classes`

What to look for:

- PVCs and PVs that look stranded, oversized, or misaligned with the intended storage tier
- storage classes that do not match the platform standard
- projects carrying storage posture that will complicate failover, migration, or optimization work

Suggested prompts:

- `Review persistent storage and storage classes and summarize optimization or governance risks.`

## Machine API and upgrade readiness

Use:

- `list_machine_config_pools`
- `list_machine_sets`

What to look for:

- machine-set or machine-config posture suggesting uneven capacity management
- pools stuck updating or degraded before a change window
- scaling patterns that make cluster capacity expensive to operate or hard to reason about

Suggested prompts:

- `Inspect Machine API posture and summarize capacity-management or upgrade-readiness risks.`

## Delivery-stack efficiency

Use:

- `list_gitops_applications`
- `list_tekton_pipeline_runs`
- `list_builds`
- `list_image_streams`

What to look for:

- delivery workflows repeatedly re-running or failing in ways that waste cluster capacity
- build and pipeline backlogs creating unnecessary platform churn
- image-stream or rollout patterns that suggest poor workload hygiene

Suggested prompts:

- `Inspect GitOps, Tekton, builds, and image streams and summarize the most likely platform-efficiency issues.`

## Recommended FinOps drilldown workflow

1. start with `list_cluster_infrastructure` to confirm the baseline platform shape
2. use `list_nodes` and `list_workload_health` to identify real pressure or over-provisioning signals
3. use `list_resource_quotas` to inspect namespace-level governance and contention controls
4. use `list_persistent_storage` and `list_storage_classes` to understand storage efficiency
5. use `list_machine_config_pools` and `list_machine_sets` to inspect scaling and upgrade readiness
6. use GitOps, Tekton, build, and image-stream posture to turn platform friction into optimization actions

## Recommendation patterns the agent should surface

- reduce noisy re-delivery loops and failed pipelines that waste cluster capacity
- tighten quota posture in shared namespaces before pressure becomes an outage
- normalize storage classes and remove stranded storage where possible
- align machine pools and worker topology with actual platform demand
- use platform-pattern context when comparing ROSA, ARO, baremetal, and IBM Z optimization actions
