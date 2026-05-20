# Storage & Governance Playbook

![Storage and governance service map](assets/diagrams/storage-governance.svg)

This playbook covers storage, backup, and multi-account governance visibility.

## EFS

Use: `list_efs_file_systems`

What to look for:

- unencrypted file systems
- unexpected throughput modes
- file systems with unclear ownership or naming

Suggested prompts:

- `Inspect EFS posture and summarize encryption and throughput concerns.`

## Storage Backup

Use:

- `list_backup_vaults`
- `list_backup_recovery_points`

What to look for:

- missing vaults/plans in expected environments
- no recovery points where data protection should exist
- vault lock posture missing when expected

Suggested prompts:

- `Review Storage Backup vaults and plans for governance gaps.`
- `Inspect backup recovery-point posture and identify weak coverage areas.`

## Organizations

Use:

- `list_organization_accounts`
- `list_organization_structure`

What to look for:

- unknown accounts
- suspended accounts still present
- roots/policy types not matching governance expectations

Suggested prompts:

- `Inspect Platform Governance accounts and summarize governance drift.`
- `Summarize Organizations roots, top-level OUs, and SCP inventory for governance drift.`

## Combined storage/governance workflow

Suggested prompt:

- `Inspect EFS, Storage Backup, and Organizations data for storage and governance posture issues.`

Operator actions:

1. inventory storage surfaces
2. inspect backup coverage and recovery-point posture
3. correlate ownership with multi-account structure
4. capture follow-up remediation items for missing protections

For deeper cross-service security/governance review, continue into the [`Advanced Security & Governance`](playbook-advanced-security-governance.md) playbook.
