# Platform & Automation Playbook

![Platform and automation service map](assets/diagrams/platform-automation.svg)

This playbook covers the OpenShift platform services used to understand lifecycle automation, delivery posture, machine management, virtualization, and day-2 operating readiness.

## Cluster infrastructure and platform pattern

Use: `list_cluster_infrastructure`

What to look for:

- platform type resolving differently than expected for ROSA, ARO, baremetal, or IBM Z clusters
- infrastructure signals that explain why lifecycle or delivery workflows behave differently across clusters
- cluster identity or topology drift before broader automation analysis

Suggested prompts:

- `Inspect cluster infrastructure posture and summarize platform-pattern drift.`

## Machine config pools

Use: `list_machine_config_pools`

What to look for:

- pools stuck updating, degraded, or paused unexpectedly
- machine config rollout drift affecting upgrade readiness
- worker configuration differences that explain inconsistent workload behavior

Suggested prompts:

- `Inspect machine config pools and summarize lifecycle or rollout drift.`

## Machine sets

Use: `list_machine_sets`

What to look for:

- replica targets that no longer match capacity intent
- machine-set posture inconsistent with the infrastructure pattern
- unhealthy or stale machine-set definitions in clusters that should scale predictably

Suggested prompts:

- `Inspect machine sets and summarize scaling or topology drift.`

## GitOps controllers and applications

Use:

- `list_gitops_argocds`
- `list_gitops_applications`

What to look for:

- Argo CD instances missing from clusters where GitOps is expected
- applications drifting, out of sync, or failing health checks repeatedly
- fleet delivery posture that diverges across clusters or platform patterns

Suggested prompts:

- `Review OpenShift GitOps posture and summarize the most important delivery drift.`

## Tekton and build automation

Use:

- `list_tekton_configs`
- `list_tekton_pipeline_runs`
- `list_builds`
- `list_image_streams`

What to look for:

- Tekton configuration drift or missing controller posture
- pipeline runs failing in the same namespaces or phases
- build and image-stream patterns that block release velocity

Suggested prompts:

- `Inspect Tekton, builds, and image streams and summarize delivery-automation drift.`

## Operator lifecycle posture

Use:

- `list_operator_subscriptions`
- `list_cluster_service_versions`

What to look for:

- subscriptions that are not progressing or are pinned unexpectedly
- CSVs stuck in pending, replacing, or failed states
- operator drift that can break day-2 automation or upgrades

Suggested prompts:

- `Review OLM subscriptions and CSVs for platform-automation drift.`

## Cluster logging and day-2 automation

Use:

- `list_cluster_logging`
- `list_oadp_resources`

What to look for:

- logging components or forwarding posture not ready
- backup schedules or backup storage missing where platform standards expect them
- day-2 services drifting enough to weaken operational recovery

Suggested prompts:

- `Inspect cluster logging and OADP posture and summarize day-2 automation gaps.`

## Virtualization and disaster recovery

Use:

- `list_virtualization_resources`
- `list_disaster_recovery_resources`

What to look for:

- virtualization resources not aligned with workload-mobility expectations
- DR resources missing from clusters expected to support failover or migration
- migration posture that looks blocked by platform-service drift

Suggested prompts:

- `Inspect virtualization and disaster-recovery resources and summarize platform readiness concerns.`

Operator actions:

1. confirm the cluster infrastructure matches the platform pattern you think you are operating
2. review MachineConfigPool and MachineSet posture before platform changes
3. inspect GitOps, Tekton, builds, and image streams for delivery drift
4. review OLM, logging, and OADP posture as part of day-2 automation readiness
5. compare virtualization and DR posture before migration, failover, or upgrade work
