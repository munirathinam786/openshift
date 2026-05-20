# Audit & Security Playbook

![Audit and security service map](assets/diagrams/audit-security.svg)

This playbook covers the services that help an operator answer:

- **Are core OpenShift guardrails configured the way we expect?**
- **Is namespace isolation and route exposure aligned with policy?**
- **Are identity-provider, fleet-security, and logging controls healthy?**
- **Do we have enough evidence for a security or compliance review?**

For deeper vulnerability, data-security, and org-governance review, continue into the [`Advanced Security & Governance`](playbook-advanced-security-governance.md) playbook.

## Security Console workflow

If you prefer a guided UI instead of typing every prompt manually, use the dedicated [`Security Console`](security-console.html).

That page now gives you:

- audit-profile launchers for SOX and related frameworks
- a multi-select for platform security and governance controls
- the same **Connection & credentials** panel used in the FinOps console
- export actions for CSV, PowerPoint, PDF, and Word-compatible security handoff packs

The important implementation detail is that the page sends request-scoped runtime overrides directly to `/chat`, so an operator can change model or cluster credential context for a single review without changing the global container environment.

Example runtime shape used by the UI:

```json
{
  "runtime": {
    "cluster_scope": "local-cluster",
    "local_model_name": "gpt-oss:20b",
    "ollama_base_url": "http://host.containers.internal:11434",
    "kube_context_name": "default",
    "verify_ssl": true
  }
}
```

Use this when you want the browser workflow to mirror the same runtime flexibility already available in the FinOps workspace.

## Security context constraints

Use: `list_security_context_constraints`

What to look for:

- privileged or host-access SCCs still bound more broadly than expected
- legacy SCC usage that should have been replaced by tighter workload settings
- service accounts relying on broad SCCs without a current business reason

Suggested prompts:

- `Inspect SCC posture and summarize the riskiest privilege assignments.`
- `Review security context constraints and highlight namespaces or service accounts that look over-permissive.`

Operator actions:

1. identify the SCCs with the broadest privilege surface
2. map high-risk SCC usage back to namespaces and service accounts
3. flag workloads that need a migration path toward tighter pod security settings

## Network policies

Use: `list_network_policies`

What to look for:

- namespaces with no policy coverage where isolation is expected
- default-deny posture missing in shared or regulated projects
- policy count present but obviously not aligned with application tiers

Suggested prompts:

- `Review OpenShift network policy coverage and summarize namespace isolation gaps.`
- `Tell me which projects appear under-protected from east-west traffic.`

Operator actions:

1. compare protected and unprotected namespaces
2. look for shared namespaces without clear ingress and egress controls
3. capture which application tiers still depend on broad intra-cluster reachability

## OAuth and identity-provider posture

Use: `list_oauth_configuration`

What to look for:

- unexpected identity providers still enabled
- LDAP, HTPasswd, or GitHub mappings drifting from the intended auth design
- branding, login, or claim-mapping details inconsistent across clusters

Suggested prompts:

- `Inspect OAuth configuration and summarize identity-provider drift.`
- `Review LDAP and OAuth posture across this cluster and call out risky auth patterns.`

Operator actions:

1. confirm the expected identity providers are present and healthy
2. compare cluster auth posture with the intended platform-standard design
3. flag legacy or emergency providers that should be retired

## ACS coverage

Use:

- `list_acs_central_services`
- `list_acs_secured_clusters`

What to look for:

- central services missing or degraded
- secured clusters absent from environments that should be enrolled
- fleet coverage that does not match the known managed-cluster estate

Suggested prompts:

- `Inspect ACS central and secured-cluster coverage and summarize the biggest protection gaps.`

Operator actions:

1. confirm ACS central components exist and appear healthy
2. compare secured-cluster enrollment with the fleet you expect ACM to manage
3. identify clusters or environments where enforcement or visibility is still missing

## Cluster logging evidence

Use: `list_cluster_logging`

What to look for:

- log store or collector components not ready
- forwarding posture missing where audit evidence is expected off-cluster
- retention or pipeline gaps that could block incident reconstruction

Suggested prompts:

- `Inspect Cluster Logging posture and summarize evidence-collection gaps.`

Operator actions:

1. confirm logging operators and collectors are present
2. review forwarding targets and obvious readiness issues
3. note whether the cluster appears able to support an audit or incident review without extra manual collection

## Route exposure and namespace guardrails

Use:

- `list_routes`
- `list_resource_quotas`

What to look for:

- public routes without clear ownership or TLS posture
- namespaces with weak quota controls in shared environments
- route inventory that does not align with the intended ingress pattern

Suggested prompts:

- `Review route exposure and quota posture for security and governance drift.`

Operator actions:

1. identify the most exposed routes and confirm they belong where expected
2. compare quota posture across shared namespaces
3. capture any guardrail gaps that could increase blast radius during an incident
