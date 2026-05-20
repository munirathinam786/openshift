# Service Coverage

This agent spans a broad set of **OpenShift SRE investigation domains** while staying in a **read-only-by-default** posture.

See [`Platform Impact Notes`](cost-impact.md) for a tool-by-tool view of which paths are lightweight versus more intensive control-plane reads.

## Impact legend

- `lightweight control-plane read`
- `moderate inventory read`
- `heavier troubleshooting read`

## Cluster and platform core

- `get_cluster_identity` — `lightweight control-plane read`
- `list_projects` — `lightweight control-plane read`
- `list_cluster_version` — `lightweight control-plane read`
- `list_cluster_operators` — `moderate inventory read`
- `list_nodes` — `moderate inventory read`
- `list_node_pressure` — `moderate inventory read`

Typical use cases:

- cluster identity and context verification
- control-plane health review
- degraded operator detection
- node readiness and pressure triage
- platform drift review

## Workloads and traffic

- `list_pods` — `moderate inventory read`
- `list_workload_health` — `moderate inventory read`
- `list_services` — `lightweight control-plane read`
- `list_routes` — `moderate inventory read`
- `list_ingresses` — `lightweight control-plane read`
- `list_events` — `heavier troubleshooting read`

Typical use cases:

- rollout failure triage
- pending pod and restart analysis
- route and ingress exposure review
- service-to-route validation
- warning-event correlation during incidents

## Storage and capacity guardrails

- `list_persistent_storage` — `moderate inventory read`
- `list_storage_classes` — `lightweight control-plane read`
- `list_resource_quotas` — `moderate inventory read`

Typical use cases:

- PVC bind triage
- storage class validation
- quota pressure review
- capacity governance checks

## Platform operations and lifecycle

- `list_machine_config_pools` — `moderate inventory read`
- `list_machine_sets` — `moderate inventory read`
- `list_operator_subscriptions` — `moderate inventory read`
- `list_cluster_service_versions` — `moderate inventory read`
- `list_builds` — `moderate inventory read`
- `list_image_streams` — `moderate inventory read`

Typical use cases:

- operator lifecycle troubleshooting
- machine config drift detection
- cluster upgrade readiness review
- upgrade preflight scoring before a controlled change window
- operator upgrade blast-radius mapping across auth, ingress, storage, and workload surfaces
- build and image pipeline visibility

## Security posture

- `list_security_context_constraints` — `moderate inventory read`
- `list_network_policies` — `moderate inventory read`
- `list_routes` — `moderate inventory read`
- `list_cluster_operators` — `moderate inventory read`

Typical use cases:

- privileged SCC review
- namespace isolation review
- insecure route detection
- security-related operator health review
- alert-to-runbook correlation when security, auth, or platform alerts need an owning playbook

## Reliability, SLO, and runbook posture

- `list_monitoring_alert_posture` — `moderate inventory read`
- `list_cluster_logging` — `moderate inventory read`
- `list_workload_health` — `moderate inventory read`
- `list_horizontal_pod_autoscalers` — `moderate inventory read`
- `list_pod_disruption_budgets` — `moderate inventory read`
- `list_events` — `heavier troubleshooting read`

Typical use cases:

- SLO / error-budget posture reviews before approving more change
- early detection of alert coverage gaps and noisy-burn patterns
- workload and exposure-path checks that explain likely customer impact
- alert-to-runbook correlation and owner handoff during live triage or pre-change review

## Fallback and safety

- `run_read_only_oc_cli` — `heavier troubleshooting read`

The fallback command path is still guarded:

- only safe read-style `oc` verbs such as `get`, `describe`, `logs`, `whoami`, `version`, and selected `adm` reads are allowed
- shell operators are blocked
- multiline commands are blocked
- mutating verbs are rejected

## GUI shortcut mapping

The browser console includes shortcut flows for common platform review paths such as:

- cluster health
- workload health
- route exposure
- storage posture
- security posture
- operator lifecycle checks
- upgrade preflight scoring
- SLO / error-budget posture
- operator upgrade blast-radius mapping
- alert-to-runbook correlation

## Operator note

If your local container environment cannot validate the cluster certificate chain, you can temporarily disable verification with `OPENSHIFT_VERIFY_SSL=false`, but the preferred long-term fix is to use a valid kubeconfig and trusted CA chain.
