# AWS ROSA Architecture

This architecture adapts the repository's Terraform style to **Red Hat OpenShift Service on AWS (ROSA)**. Instead of provisioning the full control plane directly, the Terraform code prepares the **customer-managed AWS footprint** and renders the automation assets required to create and extend the cluster with `rosa`, `aws`, `oc`, and `helm`.

## High-level topology

![AWS ROSA Architecture Overview](../diagrams/aws-rosa/01-aws-rosa-architecture.svg){: .drawio-diagram }

???+ note "Draw.io Source: AWS ROSA Architecture Overview"
    [:material-download: Download .drawio file](../diagrams/aws-rosa/01-aws-rosa-architecture.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Deployment flow

![AWS ROSA Deployment Flow](../diagrams/aws-rosa/02-aws-rosa-deployment-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: AWS ROSA Deployment Flow"
    [:material-download: Download .drawio file](../diagrams/aws-rosa/02-aws-rosa-deployment-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Component mapping

| Layer | AWS ROSA component | Role in the design |
| --- | --- | --- |
| Management plane | ROSA service / OCM | Provisions and manages the OpenShift control plane |
| Customer network | VPC, subnets, IGW, NAT, route tables | Hosts worker nodes and connectivity controls |
| Private service access | Interface and gateway endpoints | Keeps worker traffic inside AWS where possible |
| IAM / identity | STS, OIDC, IAM roles | Powers ROSA STS mode and post-install service accounts |
| Application ingress | AWS Load Balancer Controller | Creates ALBs for application routes and custom ingress patterns |
| DNS | Route 53 | Optional aliases for API and wildcard app endpoints |

## Architecture differences from bare metal and IBM Z

### Managed control plane

ROSA moves control-plane lifecycle into Red Hat's service boundary. Terraform still matters, but it focuses on:

- customer VPC design
- subnet layout
- endpoint reachability
- security groups
- generated automation assets

### Private worker connectivity

Private ROSA worker nodes need predictable access to AWS APIs used by the cluster and the ingress stack. That is why this blueprint explicitly creates endpoints for:

- EC2 and Auto Scaling
- ELB APIs
- STS
- ECR API and image pulls
- CloudWatch Logs and Monitoring
- Route 53 and tagging APIs
- S3 as a gateway endpoint

### ALB-backed ingress

Classic ROSA cluster creation gives you the default OpenShift ingress path. This blueprint goes one step further and includes the **AWS load balancer controller** prerequisites so you can expose workload routes with ALBs, WAF, ACM certificates, and internet-facing or internal schemes.

## Networking considerations

The sample Terraform defaults to:

- three public subnets for NAT and internet-facing ALB placement
- three private subnets for worker nodes
- one NAT gateway per AZ
- an additional compute security group you can pass into the ROSA create command

That model mirrors the patterns many enterprises use for production ROSA clusters and can be simplified for lower environments.

## Practical deployment notes

1. Confirm that the AWS account has ROSA quota and STS permissions before execution.
2. Align the VPC CIDR and subnet plan with existing Transit Gateway, Direct Connect, or overlapping CIDR constraints.
3. Review the generated `create-rosa-cluster.sh` before execution so the final cluster flags match your support model.
4. Only run the ALB installation script after the cluster is ready and you can log in with `oc`.
