# Platform & Automation Playbook

![Platform and automation service map](assets/diagrams/platform-automation.svg)

This playbook covers services used to understand operational automation, image delivery, event-driven workflows, and day-2 infrastructure posture.

## Auto Scaling groups

Use: `list_autoscaling_groups`

What to look for:

- desired capacity drifting too close to min or max bounds
- suspiciously uneven AZ spread
- launch-template posture missing where modern configuration is expected

Suggested prompts:

- `Inspect Auto Scaling groups and summarize capacity or configuration drift.`

## EBS volumes

Use: `list_ebs_volumes`

What to look for:

- unattached but still provisioned volumes
- unencrypted volumes in sensitive environments
- volume classes or IOPS profiles that look inconsistent with workload intent

Suggested prompts:

- `Inspect EBS volumes and summarize storage posture or cost-risk drift.`

## SSM managed instances

Use: `list_ssm_managed_instances`

What to look for:

- instances missing from Systems Manager
- `PingStatus` not healthy
- inconsistent agent versions

Suggested prompts:

- `Inspect SSM managed instances and summarize agent health drift.`

## Parameter Store

Use: `list_ssm_parameters`

What to look for:

- unexpected parameter sprawl
- wrong parameter types/tiers
- stale metadata suggesting unmanaged config

Suggested prompts:

- `Review Parameter Store metadata and identify suspicious configuration sprawl.`

## Secrets Manager

Use: `list_secrets_manager_secrets`

What to look for:

- rotation disabled for high-value secrets
- stale rotation dates
- inconsistent owning services

Suggested prompts:

- `Inspect Secrets Manager metadata and summarize rotation posture.`

## EventBridge

Use:

- `list_eventbridge_buses`
- `list_eventbridge_rules`

What to look for:

- unexpected custom buses
- disabled rules
- stale or risky schedule expressions

Suggested prompts:

- `Review EventBridge buses and rules for automation drift.`

## ECR

Use: `list_ecr_repositories`

What to look for:

- mutable tags where immutability is expected
- scan-on-push disabled
- inconsistent encryption settings

Suggested prompts:

- `Inspect ECR repositories and summarize image governance gaps.`

## CloudFormation stacks

Use: `list_cloudformation_stacks`

What to look for:

- stacks stuck in failure states
- old stacks with suspicious drift status
- missing termination protection where it should exist

Suggested prompts:

- `Inspect CloudFormation stacks and summarize provisioning or drift concerns.`

## KMS keys

Use: `list_kms_keys`

What to look for:

- customer-managed keys without rotation enabled
- alias sprawl or unclear key ownership
- keys in unexpected states

Suggested prompts:

- `Inspect KMS key inventory and summarize encryption-key posture concerns.`

## ALB / NLB and target groups

Use:

- `list_load_balancers`
- `list_target_groups`

What to look for:

- load balancers with suspicious state
- target groups with mismatched health check configuration
- internet-facing surfaces without clear purpose

Suggested prompts:

- `Review ALB, NLB, and target groups for traffic delivery risk.`

Operator actions:

1. map external surfaces
2. inspect listener and target-group design
3. compare health-check paths/protocols with application expectations
4. compare desired capacity and storage posture with workload expectations
5. inspect infrastructure stack health and key-management hygiene
