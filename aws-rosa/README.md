# AWS ROSA Terraform Blueprint

This folder contains a Terraform-driven blueprint for deploying **Red Hat OpenShift Service on AWS (ROSA)** with the AWS foundation, required VPC endpoints, and post-cluster **ALB operator** enablement assets.

## What is included

- `versions.tf` — Terraform and provider constraints for AWS, local files, and helper execution
- `variables.tf` — ROSA, AWS networking, endpoint, DNS, and automation inputs
- `terraform.tfvars` — starter values for a multi-AZ ROSA deployment
- `main.tf` — root orchestration across networking, endpoints, ROSA automation, and ALB assets
- `outputs.tf` — VPC IDs, subnet IDs, endpoint inventories, script paths, and ALB policy references
- `azure-pipelines-rosa.yml` — Azure DevOps workflow for validation and optional execution
- `modules/networking` — VPC, public/private subnets, route tables, NAT, and security groups
- `modules/vpc-endpoints` — required AWS interface and gateway endpoints for private worker connectivity
- `modules/rosa-automation` — generated ROSA CLI scripts, environment inventory, and Route 53 helper scripts
- `modules/alb-operator` — IAM policy plus install scripts for the AWS Load Balancer Controller / ALB flow

## Deployment model

The implementation assumes:

1. ROSA runs in **STS mode** and is created by the `rosa` CLI in `--mode auto` for account roles, OIDC, and operator roles.
2. Terraform owns the **customer VPC**, subnets, security groups, and VPC endpoints required by private worker nodes.
3. A command runner host or pipeline agent has `aws`, `rosa`, `oc`, `jq`, and `helm` available when executing the generated scripts.
4. ALB enablement is completed after cluster creation using the generated IAM policy and install assets under `aws-rosa/generated/<cluster>/`.

## Notes

- The generated scripts are intentionally explicit and reviewable rather than hiding ROSA lifecycle work inside opaque provisioners.
- Interface endpoints default to the AWS services most commonly required by private ROSA clusters: STS, EC2, ELB, ECR API/DKR, CloudWatch Logs, Monitoring, Auto Scaling, Route 53, Service Quotas, and Tagging.
- Route 53 integration is optional. If you provide a hosted zone ID, Terraform will render a helper script to create API and wildcard app aliases once the cluster endpoints are known.
