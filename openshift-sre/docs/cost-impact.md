# Cost Impact & Potentially Billable Tools

This page gives a **practical billing-risk label for every agent tool**. It is meant for operator awareness, not as a substitute for the official AWS pricing pages.

## Labels used on this page

- **likely free control-plane read** — usually a metadata or inventory API call; typically low risk for direct per-call billing
- **may incur request charges** — can trigger metered request pricing depending on the target AWS service or object/API class
- **may incur query/analysis charges** — can trigger metered analytics, scanning, query, or billing-analysis charges

## Read this before using the table

- These labels describe the **tool call itself**, not the baseline cost of keeping a service enabled in your AWS account.
- A tool can be a `likely free control-plane read` and still surface data from a service that is already billing you separately, such as `GuardDuty`, `Macie`, `Inspector`, `AWS Config`, or `Security Hub`.
- AWS pricing can change. Treat this page as **operator guidance**, not a contractual billing statement.

## Tool-by-tool cost impact

| Tool | Cost impact | Why |
| --- | --- | --- |
| `list_ec2_instances` | likely free control-plane read | EC2 inventory / describe call |
| `list_autoscaling_groups` | likely free control-plane read | Auto Scaling inventory call |
| `list_ebs_volumes` | likely free control-plane read | EBS metadata inventory |
| `list_vpc_inventory` | likely free control-plane read | VPC, subnet, route, and gateway describe calls |
| `list_subnets` | likely free control-plane read | subnet metadata inventory |
| `list_transit_gateways` | likely free control-plane read | TGW metadata inventory |
| `list_load_balancers` | likely free control-plane read | ELBv2 inventory and listener metadata |
| `list_target_groups` | likely free control-plane read | ELBv2 target-group metadata |
| `get_cloudwatch_metric` | likely free control-plane read | metric retrieval is usually a low-risk monitoring read |
| `query_logs_insights` | may incur query/analysis charges | CloudWatch Logs Insights is billed by data scanned |
| `list_alarms` | likely free control-plane read | alarm state and metadata read |
| `list_cost_and_usage_summary` | may incur query/analysis charges | Cost Explorer / billing analysis API |
| `list_cost_by_service` | may incur query/analysis charges | Cost Explorer grouped spend analysis |
| `list_cost_by_tag` | may incur query/analysis charges | Cost Explorer grouped billing analysis |
| `get_cost_forecast` | may incur query/analysis charges | Cost Explorer forecast / billing analysis |
| `list_savings_plans_coverage` | may incur query/analysis charges | billing optimization analysis API |
| `list_rightsizing_recommendations` | may incur query/analysis charges | Cost Explorer optimization analysis |
| `list_rds_instances` | likely free control-plane read | RDS metadata inventory |
| `list_cloudformation_stacks` | likely free control-plane read | CloudFormation stack status read |
| `list_redshift_clusters` | likely free control-plane read | Redshift cluster metadata |
| `list_redshift_serverless` | likely free control-plane read | Redshift Serverless metadata inventory |
| `list_eks_clusters` | likely free control-plane read | EKS control-plane inventory |
| `list_ecs_clusters` | likely free control-plane read | ECS control-plane inventory |
| `list_lambda_functions` | likely free control-plane read | Lambda metadata inventory |
| `list_ssm_managed_instances` | likely free control-plane read | Systems Manager inventory read |
| `list_ssm_parameters` | likely free control-plane read | Parameter Store metadata only |
| `list_secrets_manager_secrets` | likely free control-plane read | secret metadata only, not secret value retrieval |
| `list_cloudtrail_trails` | likely free control-plane read | CloudTrail trail metadata |
| `list_cloudtrail_event_selectors` | likely free control-plane read | CloudTrail selector metadata |
| `list_config_rules` | likely free control-plane read | AWS Config metadata read; Config itself may already be billing |
| `list_config_compliance_summary` | likely free control-plane read | compliance metadata read; Config service billing may still exist |
| `list_guardduty_detectors` | likely free control-plane read | GuardDuty posture metadata read |
| `list_guardduty_findings` | likely free control-plane read | finding retrieval; GuardDuty service charges may already apply |
| `list_detective_graphs` | likely free control-plane read | Detective graph metadata read |
| `list_inspector_findings` | likely free control-plane read | Inspector finding retrieval |
| `list_macie_posture` | likely free control-plane read | Macie posture/job metadata read |
| `list_access_analyzers` | likely free control-plane read | IAM Access Analyzer metadata |
| `list_kms_keys` | likely free control-plane read | KMS key metadata and rotation status |
| `list_securityhub_standards` | likely free control-plane read | Security Hub standards metadata |
| `list_securityhub_findings` | likely free control-plane read | Security Hub findings retrieval |
| `list_dynamodb_tables` | likely free control-plane read | DynamoDB metadata inventory |
| `list_efs_file_systems` | likely free control-plane read | EFS metadata read |
| `list_s3_buckets` | may incur request charges | S3 list/location lookups can fall under request pricing |
| `list_glue_catalog` | likely free control-plane read | Glue catalog metadata read |
| `list_athena_workgroups` | likely free control-plane read | Athena workgroup/catalog metadata only, not query execution |
| `list_sqs_queues` | likely free control-plane read | queue metadata and attribute read |
| `list_sns_topics` | likely free control-plane read | topic inventory metadata |
| `list_kinesis_streams` | likely free control-plane read | stream metadata inventory |
| `list_opensearch_domains` | likely free control-plane read | domain metadata read |
| `list_elasticache_clusters` | likely free control-plane read | cache metadata inventory |
| `list_api_gateways` | likely free control-plane read | API Gateway metadata inventory |
| `list_cloudfront_distributions` | likely free control-plane read | CloudFront metadata read |
| `list_route53_zones` | likely free control-plane read | hosted-zone metadata read |
| `list_step_functions` | likely free control-plane read | state-machine metadata inventory |
| `list_emr_clusters` | likely free control-plane read | EMR cluster metadata inventory |
| `list_backup_vaults` | likely free control-plane read | Backup metadata inventory |
| `list_backup_recovery_points` | likely free control-plane read | Backup metadata read |
| `list_backup_plan_vault_mappings` | likely free control-plane read | Backup plan metadata read |
| `list_network_firewalls` | likely free control-plane read | AWS Network Firewall firewall and policy metadata inventory |
| `list_firewall_manager_policies` | likely free control-plane read | Firewall Manager policy metadata and remediation posture read |
| `list_controltower_controls` | likely free control-plane read | Control Tower landing-zone and enabled-control metadata inventory |
| `list_organization_accounts` | likely free control-plane read | Organizations metadata inventory |
| `list_organization_account_mappings` | likely free control-plane read | Organizations parent/OU metadata read |
| `list_organization_structure` | likely free control-plane read | Organizations OU/SCP metadata inventory |
| `list_eventbridge_buses` | likely free control-plane read | EventBridge metadata inventory |
| `list_eventbridge_rules` | likely free control-plane read | EventBridge rule metadata |
| `list_ecr_repositories` | likely free control-plane read | ECR repository metadata |
| `list_waf_web_acls` | likely free control-plane read | WAF ACL metadata inventory |
| `run_read_only_aws_cli` | may incur query/analysis charges | fallback path depends on the specific AWS CLI command and target service |

## Practical guidance

If you want the lowest billing risk when using this agent:

- prefer inventory prompts first
- treat `query_logs_insights` and all FinOps tools as **potentially billable analysis paths**
- use extra care with `S3`-related inspection in large environments
- remember that querying enabled security/governance services does not turn them on, but those services may already have their own standing AWS charges
