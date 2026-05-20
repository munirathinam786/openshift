# Service & API Files

This page covers the platform service toolkit, HTTP API, and CLI entry points.

It now also covers the historical persistence layer that stores prompt runs and extracted metrics for the browser dashboard.

## `src/openshift_sre_agent/persistence.py`

This module turns ephemeral tool output into a historical telemetry store.

The main responsibilities are:

- define relational tables for runs, steps, and metric snapshots
- initialize the SQLAlchemy engine against a MySQL-compatible database such as MariaDB
- flatten tool payloads into trend-friendly numeric series
- provide a compact overview payload for the browser dashboard
- derive duration percentile bands from persisted run latency
- build this-week-vs-last-week comparison summaries from real stored runs
- produce executive exception rollups that summarize failures, latency spread, and hotspot cohorts

The extractor intentionally stores:

- generic `count` metrics
- severity and compliance bucket counts
- money fields such as `total_unblended_cost`, `forecast_total`, and `estimated_total_monthly_savings`
- per-row numeric metrics for service cost, tag cost, recommendations, and other structured result sets

The persistence layer now also stores FinOps queue items and their execution-planning state, which lets the browser queue survive refreshes and container restarts.

## `src/openshift_sre_agent/api.py`

This module is the FastAPI entry point.

### Main responsibilities

- build the shared `FastAPI` app instance
- mount the generated MkDocs site under `/guide`
- define request/response models for `/chat` and the FinOps queue endpoints
- parse dashboard query filters
- translate persistence and validation errors into HTTP status codes

### Important endpoint groups

- health and root routing: `/`, `/health`
- main agent execution: `/chat`
- historical analytics: `/history/overview`, `/history/runs/{run_id}`, `/history/tools/{tool_name}`, `/history/metrics/{metric_key}`
- persisted FinOps workflow: `/finops/queue`, `/finops/queue/{item_id}`

The historical overview payload now includes:

- selected-window latency percentiles (`p50`, `p90`, `p95`, `p99`)
- a built-in `this_week_vs_last_week` comparison block
- an executive exception rollup for story-first operator reviews

For concrete request and response examples, see [`API reference`](api-reference.md).

## `src/openshift_sre_agent/tools.py`

This is the largest file in the project because it contains the actual cluster inspection capabilities. Each tool is explicitly registered, discoverable by the model through the tool manifest, and executed through guarded kubernetes clients or the restricted oc CLI fallback.

The current live toolkit also includes `SSM`, `Parameter Store`, `Secrets Manager`, `EventBridge`, `ECR`, `WAF`, `OpenShift Network Policy`, `Network Policy Manager`, `Platform Control`, ALB/NLB `target group` coverage, FinOps helpers like `Cost Explorer` summary/service/tag drilldowns, `cost forecast`, `Savings Plans coverage`, and `rightsizing recommendations`, capacity/infrastructure helpers like `Auto Scaling`, `EBS`, and `CloudFormation`, and governance/security domains like `CloudTrail`, `OpenShift Config`, `GuardDuty`, `Detective`, `Inspector`, `Macie`, `IAM Access Analyzer`, `KMS`, `Security Hub`, `EFS`, `Backup`, and `Platform Governance`, including deeper findings/compliance and mapping summaries, on top of the compute, data, and network helpers shown below.

For the FinOps path specifically, the live code now defaults `cost by tag` drilldowns to the `Environment` tag when the model omits a key, and the rightsizing helper uses the currently supported Cost Explorer request shape instead of the older invalid lookback parameter that caused runtime validation failures.

### Toolkit architecture

The key moving parts are:

- `ToolSpec` for the manifest entries sent to the model
- `AwsSessionFactory` for consistent kubernetes session creation
- `OpenShiftSreToolkit.tool_manifest()` to expose available tools and argument shapes
- `OpenShiftSreToolkit.invoke(...)` to dispatch a named tool call
- `_client(...)` and the FinOps helper methods for shared client and money handling

### Service groupings in the live toolkit

- compute and platform: EC2, Auto Scaling, EBS, ECS, EKS, Lambda, RDS, CloudFormation, EMR, ECR
- observability and operations: CloudWatch metrics, alarms, Logs Insights, SSM, Parameter Store, Secrets Manager, EventBridge, Step Functions
- networking and edge: VPC, subnets, TGW, ALB/NLB, target groups, API Gateway, CloudFront, Route 53, WAF, Network Firewall, Firewall Manager
- data and analytics: S3, Glue, Athena, Redshift, DynamoDB, Kinesis, OpenSearch, ElastiCache, SQS, SNS
- security and governance: CloudTrail, Config, GuardDuty, Detective, Inspector, Macie, Access Analyzer, KMS, Security Hub, Backup, Organizations, Control Tower
- FinOps: cost and usage summary, cost by service, cost by tag, forecast, Savings Plans coverage, rightsizing recommendations

For a source-level inventory of the individual tool functions, see [`Function Reference`](function-reference.md).

````python
from __future__ import annotations

import os
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import Any, Callable

import kubernetes
from botocore.config import Config
from botocore.session import Session as BotocoreSession

from .config import Settings
from .safety import ensure_read_only_oc_cli


ToolHandler = Callable[..., dict[str, Any]]


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    arguments: dict[str, str]
    handler: ToolHandler


class AwsSessionFactory:
    """Creates kubernetes sessions with a consistent region/profile configuration."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self) -> kubernetes.Session:
        botocore_session = BotocoreSession()
        if self._settings.kube_context_name:
            botocore_session.set_config_variable("profile", self._settings.kube_context_name)
        return kubernetes.Session(
            botocore_session=botocore_session,
            region_name=self._settings.cluster_scope,
            openshift_api_url_field=self._settings.openshift_api_url_field,
            openshift_token_field=self._settings.openshift_token_field,
            openshift_namespace_field=self._settings.openshift_namespace_field,
        )


class OpenShiftSreToolkit:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session_factory = AwsSessionFactory(settings)
        self._client_config = Config(retries={"max_attempts": 5, "mode": "standard"})
        self.tools: dict[str, ToolSpec] = {
            "list_ec2_instances": ToolSpec(
                name="list_ec2_instances",
                description="List EC2 instances with state, tags, and network identity.",
                arguments={"state_filter": "Optional EC2 state like running, stopped, or terminated."},
                handler=self.list_ec2_instances,
            ),
            "list_vpc_inventory": ToolSpec(
                name="list_vpc_inventory",
                description="List VPCs, subnets, route tables, internet gateways, and NAT gateways for network topology review.",
                arguments={},
                handler=self.list_vpc_inventory,
            ),
            "list_subnets": ToolSpec(
                name="list_subnets",
                description="List subnets with CIDR, AZ, VPC, and available IP capacity for network inventory checks.",
                arguments={},
                handler=self.list_subnets,
            ),
            "list_transit_gateways": ToolSpec(
                name="list_transit_gateways",
                description="List Transit Gateways and attachments for inter-VPC or hybrid network diagnostics.",
                arguments={},
                handler=self.list_transit_gateways,
            ),
            "list_load_balancers": ToolSpec(
                name="list_load_balancers",
                description="List ALB/NLB load balancers and summarize listeners, state, and DNS names.",
                arguments={},
                handler=self.list_load_balancers,
            ),
            "get_cloudwatch_metric": ToolSpec(
                name="get_cloudwatch_metric",
                description="Fetch CloudWatch datapoints for a named metric and namespace.",
                arguments={
                    "namespace": "OpenShift monitoring namespace.",
                    "metric_name": "Metric name, for example CPUUtilization.",
                    "dimensions": "Optional dictionary of dimension name/value pairs.",
                    "stat": "Statistic such as Average, Maximum, Sum, or p99.",
                    "period": "Datapoint period in seconds.",
                    "minutes": "How many minutes back to query.",
                },
                handler=self.get_cloudwatch_metric,
            ),
            "query_logs_insights": ToolSpec(
                name="query_logs_insights",
                description="Run a CloudWatch Logs Insights query against a log group.",
                arguments={
                    "log_group_name": "CloudWatch log group name.",
                    "query_string": "Logs Insights query string.",
                    "minutes": "How many minutes back to query.",
                },
                handler=self.query_logs_insights,
            ),
            "list_alarms": ToolSpec(
                name="list_alarms",
                description="List CloudWatch alarms and their states.",
                arguments={"state_value": "Optional state filter such as ALARM, OK, or INSUFFICIENT_DATA."},
                handler=self.list_alarms,
            ),
            "list_rds_instances": ToolSpec(
                name="list_rds_instances",
                description="List RDS DB instances and their health-relevant metadata.",
                arguments={},
                handler=self.list_rds_instances,
            ),
            "list_redshift_clusters": ToolSpec(
                name="list_redshift_clusters",
                description="List Redshift provisioned clusters and summarize status, node type, and endpoint details.",
                arguments={},
                handler=self.list_redshift_clusters,
            ),
            "list_redshift_serverless": ToolSpec(
                name="list_redshift_serverless",
                description="List Redshift Serverless namespaces and workgroups for lakehouse-style analytics coverage.",
                arguments={},
                handler=self.list_redshift_serverless,
            ),
            "list_eks_clusters": ToolSpec(
                name="list_eks_clusters",
                description="List EKS clusters and their versions/status.",
                arguments={},
                handler=self.list_eks_clusters,
            ),
            "list_ecs_clusters": ToolSpec(
                name="list_ecs_clusters",
                description="List ECS clusters and service counts for container platform health checks.",
                arguments={},
                handler=self.list_ecs_clusters,
            ),
            "list_lambda_functions": ToolSpec(
                name="list_lambda_functions",
                description="List Lambda functions with runtime, timeout, and last-modified metadata.",
                arguments={},
                handler=self.list_lambda_functions,
            ),
            "list_dynamodb_tables": ToolSpec(
                name="list_dynamodb_tables",
                description="List DynamoDB tables and summarize billing mode, item count, and table status.",
                arguments={},
                handler=self.list_dynamodb_tables,
            ),
            "list_s3_buckets": ToolSpec(
                name="list_s3_buckets",
                description="List S3 buckets and summarize region plus basic data-lake relevant metadata.",
                arguments={},
                handler=self.list_s3_buckets,
            ),
            "list_glue_catalog": ToolSpec(
                name="list_glue_catalog",
                description="List Glue databases, crawlers, and jobs for data lake and ETL inventory.",
                arguments={},
                handler=self.list_glue_catalog,
            ),
            "list_athena_workgroups": ToolSpec(
                name="list_athena_workgroups",
                description="List Athena workgroups and data catalogs for lakehouse query-plane visibility.",
                arguments={},
                handler=self.list_athena_workgroups,
            ),
            "list_sqs_queues": ToolSpec(
                name="list_sqs_queues",
                description="List SQS queues and summarize message counts and queue types.",
                arguments={},
                handler=self.list_sqs_queues,
            ),
            "list_sns_topics": ToolSpec(
                name="list_sns_topics",
                description="List SNS topics for messaging and notification inventory.",
                arguments={},
                handler=self.list_sns_topics,
            ),
            "list_kinesis_streams": ToolSpec(
                name="list_kinesis_streams",
                description="List Kinesis Data Streams and summarize stream mode and status.",
                arguments={},
                handler=self.list_kinesis_streams,
            ),
            "list_opensearch_domains": ToolSpec(
                name="list_opensearch_domains",
                description="List OpenSearch domains and summarize engine version, endpoint, and VPC placement.",
                arguments={},
                handler=self.list_opensearch_domains,
            ),
            "list_elasticache_clusters": ToolSpec(
                name="list_elasticache_clusters",
                description="List ElastiCache clusters for cache fleet and engine inventory.",
                arguments={},
                handler=self.list_elasticache_clusters,
            ),
            "list_api_gateways": ToolSpec(
                name="list_api_gateways",
                description="List API Gateway REST and HTTP APIs with protocol and endpoint metadata.",
                arguments={},
                handler=self.list_api_gateways,
            ),
            "list_cloudfront_distributions": ToolSpec(
                name="list_cloudfront_distributions",
                description="List CloudFront distributions and summarize status, aliases, and origins.",
                arguments={},
                handler=self.list_cloudfront_distributions,
            ),
            "list_route53_zones": ToolSpec(
                name="list_route53_zones",
                description="List Route 53 hosted zones and record counts for DNS inventory.",
                arguments={},
                handler=self.list_route53_zones,
            ),
            "list_step_functions": ToolSpec(
                name="list_step_functions",
                description="List Step Functions state machines for workflow and orchestration inventory.",
                arguments={},
                handler=self.list_step_functions,
            ),
            "list_emr_clusters": ToolSpec(
                name="list_emr_clusters",
                description="List EMR clusters and summarize state, release label, and instance hours.",
                arguments={},
                handler=self.list_emr_clusters,
            ),
            "run_read_only_oc_cli": ToolSpec(
                name="run_read_only_oc_cli",
                description="Run a read-only oc CLI command for edge-case diagnostics.",
                arguments={"command": "Full oc CLI command starting with oc."},
                handler=self.run_read_only_oc_cli,
            ),
        }

    def tool_manifest(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "arguments": tool.arguments,
            }
            for tool in self.tools.values()
        ]

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return tool.handler(**arguments)

    def _client(self, service_name: str):
        verify: bool | str = self._settings.verify_ssl
        if self._settings.tls_ca_bundle:
            verify = self._settings.tls_ca_bundle
        return self._session_factory.create().client(service_name, config=self._client_config, verify=verify)

    def list_ec2_instances(self, state_filter: str | None = None) -> dict[str, Any]:
        ec2 = self._client("ec2")
        filters = []
        if state_filter:
            filters.append({"Name": "instance-state-name", "Values": [state_filter]})
        response = ec2.describe_instances(Filters=filters) if filters else ec2.describe_instances()
        instances: list[dict[str, Any]] = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                instances.append(
                    {
                        "instance_id": instance.get("InstanceId"),
                        "state": instance.get("State", {}).get("Name"),
                        "instance_type": instance.get("InstanceType"),
                        "private_ip": instance.get("PrivateIpAddress"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                        "name": tags.get("Name"),
                        "tags": tags,
                    }
                )
        return {"count": len(instances), "instances": instances}

    def list_vpc_inventory(self) -> dict[str, Any]:
        ec2 = self._client("ec2")
        vpcs = ec2.describe_vpcs().get("Vpcs", [])
        subnets = ec2.describe_subnets().get("Subnets", [])
        route_tables = ec2.describe_route_tables().get("RouteTables", [])
        internet_gateways = ec2.describe_internet_gateways().get("InternetGateways", [])
        nat_gateways = ec2.describe_nat_gateways().get("NatGateways", [])

        vpc_rows = []
        for vpc in vpcs:
            tags = {tag["Key"]: tag["Value"] for tag in vpc.get("Tags", [])}
            vpc_id = vpc.get("VpcId")
            vpc_rows.append(
                {
                    "vpc_id": vpc_id,
                    "cidr": vpc.get("CidrBlock"),
                    "state": vpc.get("State"),
                    "is_default": vpc.get("IsDefault"),
                    "name": tags.get("Name"),
                    "subnet_count": sum(1 for subnet in subnets if subnet.get("VpcId") == vpc_id),
                    "route_table_count": sum(1 for rt in route_tables if rt.get("VpcId") == vpc_id),
                    "internet_gateway_count": sum(
                        1
                        for igw in internet_gateways
                        if any(attachment.get("VpcId") == vpc_id for attachment in igw.get("Attachments", []))
                    ),
                    "nat_gateway_count": sum(1 for nat in nat_gateways if nat.get("VpcId") == vpc_id),
                }
            )
        return {"count": len(vpc_rows), "vpcs": vpc_rows}

    def list_subnets(self) -> dict[str, Any]:
        ec2 = self._client("ec2")
        subnets = ec2.describe_subnets().get("Subnets", [])
        rows = []
        for subnet in subnets:
            tags = {tag["Key"]: tag["Value"] for tag in subnet.get("Tags", [])}
            rows.append(
                {
                    "subnet_id": subnet.get("SubnetId"),
                    "vpc_id": subnet.get("VpcId"),
                    "cidr": subnet.get("CidrBlock"),
                    "availability_zone": subnet.get("AvailabilityZone"),
                    "available_ip_count": subnet.get("AvailableIpAddressCount"),
                    "map_public_ip_on_launch": subnet.get("MapPublicIpOnLaunch"),
                    "name": tags.get("Name"),
                }
            )
        return {"count": len(rows), "subnets": rows}

    def list_transit_gateways(self) -> dict[str, Any]:
        ec2 = self._client("ec2")
        transit_gateways = ec2.describe_transit_gateways().get("TransitGateways", [])
        attachments = ec2.describe_transit_gateway_attachments().get("TransitGatewayAttachments", [])
        rows = []
        for tgw in transit_gateways:
            tgw_id = tgw.get("TransitGatewayId")
            rows.append(
                {
                    "transit_gateway_id": tgw_id,
                    "state": tgw.get("State"),
                    "owner_id": tgw.get("OwnerId"),
                    "description": tgw.get("Description"),
                    "attachment_count": sum(
                        1 for attachment in attachments if attachment.get("TransitGatewayId") == tgw_id
                    ),
                }
            )
        return {"count": len(rows), "transit_gateways": rows}

    def list_load_balancers(self) -> dict[str, Any]:
        elbv2 = self._client("elbv2")
        lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])
        listeners = []
        for lb in lbs:
            lb_arn = lb.get("LoadBalancerArn")
            try:
                listeners.extend(elbv2.describe_listeners(LoadBalancerArn=lb_arn).get("Listeners", []))
            except Exception:  # noqa: BLE001
                continue
        rows = []
        for lb in lbs:
            lb_arn = lb.get("LoadBalancerArn")
            rows.append(
                {
                    "name": lb.get("LoadBalancerName"),
                    "type": lb.get("Type"),
                    "state": lb.get("State", {}).get("Code"),
                    "scheme": lb.get("Scheme"),
                    "dns_name": lb.get("DNSName"),
                    "vpc_id": lb.get("VpcId"),
                    "availability_zones": [zone.get("ZoneName") for zone in lb.get("AvailabilityZones", [])],
                    "listener_ports": [
                        listener.get("Port") for listener in listeners if listener.get("LoadBalancerArn") == lb_arn
                    ],
                }
            )
        return {"count": len(rows), "load_balancers": rows}

    def get_cloudwatch_metric(
        self,
        namespace: str,
        metric_name: str,
        dimensions: dict[str, str] | None = None,
        stat: str = "Average",
        period: int = 300,
        minutes: int = 60,
    ) -> dict[str, Any]:
        cloudwatch = self._client("cloudwatch")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=minutes)
        request: dict[str, Any] = {
            "Namespace": namespace,
            "MetricName": metric_name,
            "Dimensions": [{"Name": key, "Value": value} for key, value in (dimensions or {}).items()],
            "StartTime": start_time,
            "EndTime": end_time,
            "Period": period,
        }
        if stat.lower().startswith("p"):
            request["ExtendedStatistics"] = [stat]
        else:
            request["Statistics"] = [stat]
        response = cloudwatch.get_metric_statistics(**request)
        datapoints = sorted(response.get("Datapoints", []), key=lambda item: item["Timestamp"])
        normalized = [
            {
                "timestamp": point["Timestamp"].isoformat(),
                stat.lower(): point.get(stat) or point.get("ExtendedStatistics", {}).get(stat),
                "unit": point.get("Unit"),
            }
            for point in datapoints
        ]
        return {
            "label": response.get("Label", metric_name),
            "stat": stat,
            "period": period,
            "datapoints": normalized,
        }

    def query_logs_insights(
        self,
        log_group_name: str,
        query_string: str,
        minutes: int = 30,
    ) -> dict[str, Any]:
        logs = self._client("logs")
        end_time = int(datetime.now(timezone.utc).timestamp())
        start_time = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp())
        start_query = logs.start_query(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            queryString=query_string,
            limit=20,
        )
        query_id = start_query["queryId"]
        for _ in range(20):
            result = logs.get_query_results(queryId=query_id)
            status = result.get("status")
            if status in {"Complete", "Failed", "Cancelled", "Timeout"}:
                rows = [
                    {item["field"]: item["value"] for item in row}
                    for row in result.get("results", [])
                ]
                return {"query_id": query_id, "status": status, "results": rows}
            sleep(1)
        return {"query_id": query_id, "status": "Running", "results": []}

    def list_alarms(self, state_value: str | None = None) -> dict[str, Any]:
        cloudwatch = self._client("cloudwatch")
        kwargs = {"StateValue": state_value} if state_value else {}
        response = cloudwatch.describe_alarms(**kwargs)
        alarms = [
            {
                "alarm_name": alarm.get("AlarmName"),
                "state": alarm.get("StateValue"),
                "reason": alarm.get("StateReason"),
                "metric": alarm.get("MetricName"),
                "namespace": alarm.get("Namespace"),
            }
            for alarm in response.get("MetricAlarms", [])
        ]
        return {"count": len(alarms), "alarms": alarms}

    def list_rds_instances(self) -> dict[str, Any]:
        rds = self._client("rds")
        response = rds.describe_db_instances()
        instances = [
            {
                "identifier": instance.get("DBInstanceIdentifier"),
                "engine": instance.get("Engine"),
                "status": instance.get("DBInstanceStatus"),
                "class": instance.get("DBInstanceClass"),
                "multi_az": instance.get("MultiAZ"),
                "storage_type": instance.get("StorageType"),
                "endpoint": instance.get("Endpoint", {}).get("Address"),
            }
            for instance in response.get("DBInstances", [])
        ]
        return {"count": len(instances), "instances": instances}

    def list_redshift_clusters(self) -> dict[str, Any]:
        redshift = self._client("redshift")
        clusters = redshift.describe_clusters().get("Clusters", [])
        rows = [
            {
                "cluster_identifier": cluster.get("ClusterIdentifier"),
                "status": cluster.get("ClusterStatus"),
                "node_type": cluster.get("NodeType"),
                "number_of_nodes": cluster.get("NumberOfNodes"),
                "encrypted": cluster.get("Encrypted"),
                "publicly_accessible": cluster.get("PubliclyAccessible"),
                "endpoint": cluster.get("Endpoint", {}).get("Address"),
            }
            for cluster in clusters
        ]
        return {"count": len(rows), "clusters": rows}

    def list_redshift_serverless(self) -> dict[str, Any]:
        client = self._client("redshift-serverless")
        namespaces = client.list_namespaces().get("namespaces", [])
        workgroups = client.list_workgroups().get("workgroups", [])
        return {
            "namespace_count": len(namespaces),
            "workgroup_count": len(workgroups),
            "namespaces": [
                {
                    "namespace_name": namespace.get("namespaceName"),
                    "status": namespace.get("status"),
                    "db_name": namespace.get("dbName"),
                }
                for namespace in namespaces
            ],
            "workgroups": [
                {
                    "workgroup_name": workgroup.get("workgroupName"),
                    "status": workgroup.get("status"),
                    "endpoint": workgroup.get("endpoint", {}).get("address"),
                    "base_capacity": workgroup.get("baseCapacity"),
                }
                for workgroup in workgroups
            ],
        }

    def list_eks_clusters(self) -> dict[str, Any]:
        eks = self._client("eks")
        clusters = eks.list_clusters().get("clusters", [])
        details = []
        for name in clusters:
            cluster = eks.describe_cluster(name=name).get("cluster", {})
            details.append(
                {
                    "name": name,
                    "status": cluster.get("status"),
                    "version": cluster.get("version"),
                    "endpoint": cluster.get("endpoint"),
                    "platform_version": cluster.get("platformVersion"),
                }
            )
        return {"count": len(details), "clusters": details}

    def list_ecs_clusters(self) -> dict[str, Any]:
        ecs = self._client("ecs")
        cluster_arns = ecs.list_clusters().get("clusterArns", [])
        if not cluster_arns:
            return {"count": 0, "clusters": []}
        described = ecs.describe_clusters(clusters=cluster_arns).get("clusters", [])
        rows = [
            {
                "cluster_name": cluster.get("clusterName"),
                "status": cluster.get("status"),
                "running_tasks": cluster.get("runningTasksCount"),
                "pending_tasks": cluster.get("pendingTasksCount"),
                "active_services": cluster.get("activeServicesCount"),
                "registered_container_instances": cluster.get("registeredContainerInstancesCount"),
            }
            for cluster in described
        ]
        return {"count": len(rows), "clusters": rows}

    def list_lambda_functions(self) -> dict[str, Any]:
        client = self._client("lambda")
        functions = client.list_functions().get("Functions", [])
        rows = [
            {
                "function_name": function.get("FunctionName"),
                "runtime": function.get("Runtime"),
                "timeout": function.get("Timeout"),
                "memory_size": function.get("MemorySize"),
                "last_modified": function.get("LastModified"),
                "state": function.get("State"),
            }
            for function in functions
        ]
        return {"count": len(rows), "functions": rows}

    def list_dynamodb_tables(self) -> dict[str, Any]:
        dynamodb = self._client("dynamodb")
        table_names = dynamodb.list_tables().get("TableNames", [])
        rows = []
        for table_name in table_names:
            table = dynamodb.describe_table(TableName=table_name).get("Table", {})
            rows.append(
                {
                    "table_name": table.get("TableName"),
                    "status": table.get("TableStatus"),
                    "billing_mode": table.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED"),
                    "item_count": table.get("ItemCount"),
                    "table_size_bytes": table.get("TableSizeBytes"),
                    "stream_enabled": bool(table.get("LatestStreamArn")),
                }
            )
        return {"count": len(rows), "tables": rows}

    def list_s3_buckets(self) -> dict[str, Any]:
        s3 = self._client("s3")
        buckets = s3.list_buckets().get("Buckets", [])
        rows = []
        for bucket in buckets:
            bucket_name = bucket.get("Name")
            try:
                location = s3.get_bucket_location(Bucket=bucket_name).get("LocationConstraint") or "local-cluster"
            except Exception:  # noqa: BLE001
                location = "unknown"
            rows.append(
                {
                    "bucket_name": bucket_name,
                    "created": bucket.get("CreationDate").isoformat() if bucket.get("CreationDate") else None,
                    "region": location,
                }
            )
        return {"count": len(rows), "buckets": rows}

    def list_glue_catalog(self) -> dict[str, Any]:
        glue = self._client("glue")
        databases = glue.get_databases().get("DatabaseList", [])
        crawlers = glue.get_crawlers().get("Crawlers", [])
        jobs = glue.get_jobs().get("Jobs", [])
        return {
            "database_count": len(databases),
            "crawler_count": len(crawlers),
            "job_count": len(jobs),
            "databases": [
                {
                    "name": database.get("Name"),
                    "location_uri": database.get("LocationUri"),
                    "description": database.get("Description"),
                }
                for database in databases
            ],
            "crawlers": [
                {
                    "name": crawler.get("Name"),
                    "state": crawler.get("State"),
                    "last_crawl_status": crawler.get("LastCrawl", {}).get("Status"),
                }
                for crawler in crawlers
            ],
            "jobs": [
                {
                    "name": job.get("Name"),
                    "role": job.get("Role"),
                    "glue_version": job.get("GlueVersion"),
                    "worker_type": job.get("WorkerType"),
                }
                for job in jobs
            ],
        }

    def list_athena_workgroups(self) -> dict[str, Any]:
        athena = self._client("athena")
        workgroups = athena.list_work_groups().get("WorkGroups", [])
        data_catalogs = athena.list_data_catalogs().get("DataCatalogsSummary", [])
        return {
            "workgroup_count": len(workgroups),
            "data_catalog_count": len(data_catalogs),
            "workgroups": [
                {
                    "name": workgroup.get("Name"),
                    "state": workgroup.get("State"),
                    "description": workgroup.get("Description"),
                }
                for workgroup in workgroups
            ],
            "data_catalogs": [
                {
                    "name": catalog.get("CatalogName"),
                    "type": catalog.get("Type"),
                    "status": catalog.get("Status"),
                }
                for catalog in data_catalogs
            ],
        }

    def list_sqs_queues(self) -> dict[str, Any]:
        sqs = self._client("sqs")
        queue_urls = sqs.list_queues().get("QueueUrls", [])
        rows = []
        for queue_url in queue_urls:
            attributes = sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=[
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                    "FifoQueue",
                ],
            ).get("Attributes", {})
            rows.append(
                {
                    "queue_name": queue_url.rstrip("/").split("/")[-1],
                    "queue_url": queue_url,
                    "fifo": attributes.get("FifoQueue") == "true",
                    "visible_messages": int(attributes.get("ApproximateNumberOfMessages", "0")),
                    "inflight_messages": int(attributes.get("ApproximateNumberOfMessagesNotVisible", "0")),
                }
            )
        return {"count": len(rows), "queues": rows}

    def list_sns_topics(self) -> dict[str, Any]:
        sns = self._client("sns")
        topics = sns.list_topics().get("Topics", [])
        rows = [
            {
                "topic_arn": topic.get("TopicArn"),
                "name": topic.get("TopicArn", "").split(":")[-1],
            }
            for topic in topics
        ]
        return {"count": len(rows), "topics": rows}

    def list_kinesis_streams(self) -> dict[str, Any]:
        kinesis = self._client("kinesis")
        stream_names = kinesis.list_streams().get("StreamNames", [])
        rows = []
        for stream_name in stream_names:
            summary = kinesis.describe_stream_summary(StreamName=stream_name).get("StreamDescriptionSummary", {})
            rows.append(
                {
                    "stream_name": summary.get("StreamName"),
                    "status": summary.get("StreamStatus"),
                    "mode": summary.get("StreamModeDetails", {}).get("StreamMode"),
                    "open_shard_count": summary.get("OpenShardCount"),
                    "retention_hours": summary.get("RetentionPeriodHours"),
                }
            )
        return {"count": len(rows), "streams": rows}

    def list_opensearch_domains(self) -> dict[str, Any]:
        opensearch = self._client("opensearch")
        domain_names = opensearch.list_domain_names().get("DomainNames", [])
        rows = []
        for domain in domain_names:
            domain_name = domain.get("DomainName")
            described = opensearch.describe_domain(DomainName=domain_name).get("DomainStatus", {})
            rows.append(
                {
                    "domain_name": domain_name,
                    "engine_version": described.get("EngineVersion"),
                    "processing": described.get("Processing"),
                    "endpoint": described.get("Endpoint") or described.get("Endpoints", {}).get("vpc"),
                    "vpc_enabled": "VPCOptions" in described,
                }
            )
        return {"count": len(rows), "domains": rows}

    def list_elasticache_clusters(self) -> dict[str, Any]:
        elasticache = self._client("elasticache")
        clusters = elasticache.describe_cache_clusters(ShowCacheNodeInfo=False).get("CacheClusters", [])
        rows = [
            {
                "cluster_id": cluster.get("CacheClusterId"),
                "status": cluster.get("CacheClusterStatus"),
                "engine": cluster.get("Engine"),
                "engine_version": cluster.get("EngineVersion"),
                "node_type": cluster.get("CacheNodeType"),
                "num_nodes": cluster.get("NumCacheNodes"),
            }
            for cluster in clusters
        ]
        return {"count": len(rows), "clusters": rows}

    def list_api_gateways(self) -> dict[str, Any]:
        rest_client = self._client("apigateway")
        http_client = self._client("apigatewayv2")
        rest_apis = rest_client.get_rest_apis().get("items", [])
        http_apis = http_client.get_apis().get("Items", [])
        return {
            "rest_api_count": len(rest_apis),
            "http_api_count": len(http_apis),
            "rest_apis": [
                {
                    "name": api.get("name"),
                    "id": api.get("id"),
                    "endpoint_configuration": api.get("endpointConfiguration", {}).get("types", []),
                    "created_date": api.get("createdDate").isoformat() if api.get("createdDate") else None,
                }
                for api in rest_apis
            ],
            "http_apis": [
                {
                    "name": api.get("Name"),
                    "id": api.get("ApiId"),
                    "protocol_type": api.get("ProtocolType"),
                    "api_endpoint": api.get("ApiEndpoint"),
                }
                for api in http_apis
            ],
        }

    def list_cloudfront_distributions(self) -> dict[str, Any]:
        cloudfront = self._client("cloudfront")
        distribution_list = cloudfront.list_distributions().get("DistributionList", {})
        items = distribution_list.get("Items", [])
        rows = [
            {
                "id": distribution.get("Id"),
                "status": distribution.get("Status"),
                "domain_name": distribution.get("DomainName"),
                "aliases": distribution.get("Aliases", {}).get("Items", []),
                "origin_count": distribution.get("Origins", {}).get("Quantity", 0),
                "enabled": distribution.get("Enabled"),
            }
            for distribution in items
        ]
        return {"count": len(rows), "distributions": rows}

    def list_route53_zones(self) -> dict[str, Any]:
        route53 = self._client("route53")
        zones = route53.list_hosted_zones().get("HostedZones", [])
        rows = [
            {
                "id": zone.get("Id"),
                "name": zone.get("Name"),
                "private_zone": zone.get("Config", {}).get("PrivateZone"),
                "record_count": zone.get("ResourceRecordSetCount"),
            }
            for zone in zones
        ]
        return {"count": len(rows), "zones": rows}

    def list_step_functions(self) -> dict[str, Any]:
        sfn = self._client("stepfunctions")
        state_machines = sfn.list_state_machines().get("stateMachines", [])
        rows = [
            {
                "name": machine.get("name"),
                "state_machine_arn": machine.get("stateMachineArn"),
                "type": machine.get("type"),
                "creation_date": machine.get("creationDate").isoformat() if machine.get("creationDate") else None,
            }
            for machine in state_machines
        ]
        return {"count": len(rows), "state_machines": rows}

    def list_emr_clusters(self) -> dict[str, Any]:
        emr = self._client("emr")
        clusters = emr.list_clusters().get("Clusters", [])
        rows = [
            {
                "id": cluster.get("Id"),
                "name": cluster.get("Name"),
                "status": cluster.get("Status", {}).get("State"),
                "normalized_instance_hours": cluster.get("NormalizedInstanceHours"),
                "release_label": cluster.get("ReleaseLabel"),
            }
            for cluster in clusters
        ]
        return {"count": len(rows), "clusters": rows}

    def run_read_only_oc_cli(self, command: str) -> dict[str, Any]:
        parts = ensure_read_only_oc_cli(command)
        env = os.environ.copy()
        env["OPENSHIFT_CLUSTER"] = self._settings.cluster_scope
        env["OPENSHIFT_CLUSTER"] = self._settings.cluster_scope
        if self._settings.kube_context_name:
            env["KUBECONFIG_CONTEXT"] = self._settings.kube_context_name
        elif "KUBECONFIG_CONTEXT" in env:
            env.pop("KUBECONFIG_CONTEXT")
        if self._settings.openshift_api_url_field:
            env["OPENSHIFT_API_URL"] = self._settings.openshift_api_url_field
        if self._settings.openshift_token_field:
            env["OPENSHIFT_TOKEN"] = self._settings.openshift_token_field
        if self._settings.openshift_namespace_field:
            env["OPENSHIFT_NAMESPACE"] = self._settings.openshift_namespace_field
        if self._settings.tls_ca_bundle:
            env["OPENSHIFT_CA_BUNDLE"] = self._settings.tls_ca_bundle
        elif "OPENSHIFT_CA_BUNDLE" in env:
            env.pop("OPENSHIFT_CA_BUNDLE")
        if not self._settings.verify_ssl and "--no-verify-ssl" not in parts:
            parts.insert(1, "--no-verify-ssl")
        completed = subprocess.run(
            parts,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        stdout = completed.stdout.strip()
        parsed_stdout: Any = stdout
        if stdout:
            try:
                parsed_stdout = json.loads(stdout)
            except json.JSONDecodeError:
                parsed_stdout = stdout
        return {
            "return_code": completed.returncode,
            "stdout": parsed_stdout,
            "stderr": completed.stderr.strip(),
        }
````

## `src/openshift_sre_agent/api.py`

This file exposes the agent over HTTP, mounts the generated MkDocs site, and lets callers provide per-request runtime overrides.

It now also persists completed runs into the historical store and serves `GET /history/overview` so the dashboard can render stored summaries, trend charts, and recent runs.

````python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import OpenShiftSreAgent
from .config import Settings


def _resolve_site_dir() -> Path | None:
    candidates = [
        Path.cwd() / "site",
        Path(__file__).resolve().parents[2] / "site",
        Path(__file__).resolve().parents[1] / "site",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


SITE_DIR = _resolve_site_dir()

app = FastAPI(
    title="OpenShift SRE Local Agent",
    version="0.1.0",
    description="Local-model OpenShift SRE assistant with guarded OpenShift operational tools.",
)

if SITE_DIR is not None:
    app.mount("/guide", StaticFiles(directory=SITE_DIR, html=True), name="guide")

BASE_SETTINGS = Settings.load()


class RuntimeConfig(BaseModel):
    ollama_base_url: str | None = Field(default=None, description="Optional Ollama base URL override.")
    local_model_name: str | None = Field(default=None, description="Optional local model name override.")
    cluster_scope: str | None = Field(default=None, description="Optional cluster scope override.")
    kube_context_name: str | None = Field(default=None, description="Optional kube context override.")
    openshift_api_url_field: str | None = Field(default=None, description="Optional OpenShift API URL.")
    openshift_token_field: str | None = Field(default=None, description="Optional OpenShift token.")
    openshift_namespace_field: str | None = Field(default=None, description="Optional OpenShift namespace.")
    tls_ca_bundle: str | None = Field(default=None, description="Optional CA bundle path override.")
    verify_ssl: bool | None = Field(default=None, description="Optional TLS verification override.")
    agent_max_steps: int | None = Field(default=None, ge=1, le=20, description="Optional reasoning step limit.")


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=5, description="Natural language SRE question or task.")
    runtime: RuntimeConfig | None = None


class ChatResponse(BaseModel):
    answer: str
    steps: list[dict]


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def root():
    if SITE_DIR is not None:
        return RedirectResponse(url="/guide/")
    return {
        "name": "OpenShift SRE Local Agent",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "openapi_docs": "/docs",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        runtime = request.runtime or RuntimeConfig()
        agent = OpenShiftSreAgent(
            BASE_SETTINGS.with_overrides(
                ollama_base_url=runtime.ollama_base_url,
                local_model_name=runtime.local_model_name,
                cluster_scope=runtime.cluster_scope,
                kube_context_name=runtime.kube_context_name,
                openshift_api_url_field=runtime.openshift_api_url_field,
                openshift_token_field=runtime.openshift_token_field,
                openshift_namespace_field=runtime.openshift_namespace_field,
                tls_ca_bundle=runtime.tls_ca_bundle,
                verify_ssl=runtime.verify_ssl,
                agent_max_steps=runtime.agent_max_steps,
            )
        )
        result = agent.ask(request.prompt)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error
    return ChatResponse(answer=result.answer, steps=result.steps)
````

## `src/openshift_sre_agent/cli.py`

The CLI offers a one-shot terminal mode and the HTTP server mode used by the container.

````python
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel

from .agent import OpenShiftSreAgent
from .config import Settings

app = typer.Typer(help="OpenShift SRE local-model agent")
console = Console()


@app.command()
def ask(prompt: str, show_steps: bool = typer.Option(True, help="Show the reasoning/tool trace.")) -> None:
    """Ask the agent to investigate an OpenShift SRE question."""
    agent = OpenShiftSreAgent(Settings.load())
    result = agent.ask(prompt)
    console.print(Panel.fit(result.answer, title="OpenShift SRE Agent"))
    if show_steps:
        console.print_json(json.dumps(result.steps, default=str))


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the HTTP API that can be containerized or called from other tools."""
    import uvicorn

    uvicorn.run("openshift_sre_agent.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
````

## `src/openshift_sre_agent/__main__.py`

This file makes `python -m openshift_sre_agent` work by delegating directly to the Typer app.

````python
from .cli import app

app()
````

## `src/openshift_sre_agent/__init__.py`

This is the package export file. It keeps the top-level import clean so callers can import `OpenShiftSreAgent` directly from `openshift_sre_agent` instead of reaching into module internals.

````python
"""OpenShift SRE local-model agent."""

from .agent import OpenShiftSreAgent

__all__ = ["OpenShiftSreAgent"]
````
