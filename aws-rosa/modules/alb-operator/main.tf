variable "assets_dir" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "rosa_cli_binary" {
  type = string
}

variable "aws_cli_binary" {
  type = string
}

variable "oc_binary" {
  type = string
}

variable "jq_binary" {
  type = string
}

variable "helm_binary" {
  type = string
}

variable "aws_profile" {
  type = string
}

variable "alb_operator_namespace" {
  type = string
}

variable "alb_ingress_scheme" {
  type = string
}

variable "auto_execute" {
  type = bool
}

variable "additional_tags" {
  type = map(string)
}

locals {
  aws_profile_export = trimspace(var.aws_profile) != "" ? "export AWS_PROFILE=${var.aws_profile}" : ""

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:RevokeSecurityGroupIngress",
          "ec2:CreateSecurityGroup",
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "ec2:DeleteSecurityGroup",
          "ec2:ModifyInstanceAttribute",
          "ec2:ModifyNetworkInterfaceAttribute",
          "ec2:CreateNetworkInterfacePermission",
          "elasticloadbalancing:*",
          "iam:CreateServiceLinkedRole",
          "cognito-idp:DescribeUserPoolClient",
          "acm:ListCertificates",
          "acm:DescribeCertificate",
          "acm:GetCertificate",
          "iam:ListServerCertificates",
          "iam:GetServerCertificate",
          "waf-regional:GetWebACL",
          "waf-regional:GetWebACLForResource",
          "waf-regional:AssociateWebACL",
          "waf-regional:DisassociateWebACL",
          "wafv2:GetWebACL",
          "wafv2:GetWebACLForResource",
          "wafv2:AssociateWebACL",
          "wafv2:DisassociateWebACL",
          "shield:GetSubscriptionState",
          "shield:DescribeProtection",
          "shield:CreateProtection",
          "shield:DeleteProtection",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          "tag:GetResources",
          "tag:TagResources"
        ]
        Resource = "*"
      }
    ]
  })

  install_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    ${local.aws_profile_export}
    export AWS_REGION="${var.aws_region}"

    for bin in "${var.aws_cli_binary}" "${var.rosa_cli_binary}" "${var.oc_binary}" "${var.jq_binary}" "${var.helm_binary}"; do
      command -v "$${bin}" >/dev/null 2>&1 || {
        echo "Required binary not found: $${bin}" >&2
        exit 1
      }
    done

    CLUSTER_JSON="$$(${var.rosa_cli_binary} describe cluster -c "${var.cluster_name}" -o json)"
    OIDC_ENDPOINT="$$(${var.jq_binary} -r '.aws.sts.oidc_endpoint_url // empty' <<<"$${CLUSTER_JSON}")"

    if [[ -z "$${OIDC_ENDPOINT}" ]]; then
      echo "Could not determine the ROSA OIDC endpoint. Ensure the cluster exists and STS is enabled." >&2
      exit 1
    fi

    OIDC_PROVIDER_HOST="$${OIDC_ENDPOINT#https://}"
    ROLE_NAME="${var.cluster_name}-alb-operator"
    ROLE_ARN="arn:aws:iam::${var.aws_account_id}:role/$${ROLE_NAME}"

    cat > /tmp/$${ROLE_NAME}-trust.json <<JSON
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::${var.aws_account_id}:oidc-provider/$${OIDC_PROVIDER_HOST}"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "$${OIDC_PROVIDER_HOST}:sub": "system:serviceaccount:${var.alb_operator_namespace}:aws-load-balancer-controller",
              "$${OIDC_PROVIDER_HOST}:aud": "sts.amazonaws.com"
            }
          }
        }
      ]
    }
JSON

    ${var.aws_cli_binary} iam create-role \
      --role-name "$${ROLE_NAME}" \
      --assume-role-policy-document file:///tmp/$${ROLE_NAME}-trust.json >/dev/null 2>&1 || true

    ${var.aws_cli_binary} iam attach-role-policy \
      --role-name "$${ROLE_NAME}" \
      --policy-arn "${aws_iam_policy.alb_operator.arn}" >/dev/null 2>&1 || true

    ${var.oc_binary} create namespace ${var.alb_operator_namespace} --dry-run=client -o yaml | ${var.oc_binary} apply -f -

    cat <<YAML | ${var.oc_binary} apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: aws-load-balancer-controller
  namespace: ${var.alb_operator_namespace}
  annotations:
    eks.amazonaws.com/role-arn: "$${ROLE_ARN}"
YAML

    ${var.helm_binary} repo add eks https://aws.github.io/eks-charts >/dev/null 2>&1 || true
    ${var.helm_binary} repo update >/dev/null 2>&1

    ${var.helm_binary} upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
      --namespace ${var.alb_operator_namespace} \
      --set clusterName=${var.cluster_name} \
      --set region=${var.aws_region} \
      --set vpcId=${var.vpc_id} \
      --set serviceAccount.create=false \
      --set serviceAccount.name=aws-load-balancer-controller

    echo "ALB controller installed. Apply the sample ingress manifest at ${var.assets_dir}/sample-alb-ingress.yaml after replacing the service name and certificate ARN."
  EOT

  example_ingress = <<-EOT
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: example-alb
      namespace: default
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: ${var.alb_ingress_scheme}
        alb.ingress.kubernetes.io/target-type: ip
        alb.ingress.kubernetes.io/subnets: ${join(",", var.public_subnet_ids)}
        alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
        alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:${var.aws_region}:${var.aws_account_id}:certificate/replace-me
    spec:
      rules:
        - host: app.replace-me.example.com
          http:
            paths:
              - path: /
                pathType: Prefix
                backend:
                  service:
                    name: replace-me-service
                    port:
                      number: 8080
  EOT
}

resource "aws_iam_policy" "alb_operator" {
  name        = "${var.cluster_name}-aws-load-balancer-controller"
  description = "Permissions used by the AWS load balancer controller in ROSA"
  policy      = local.policy_document

  tags = merge(var.additional_tags, {
    Name   = "${var.cluster_name}-alb-policy"
    module = "alb-operator"
  })
}

resource "local_file" "policy_json" {
  filename = "${var.assets_dir}/alb-iam-policy.json"
  content  = local.policy_document
}

resource "local_file" "install_script" {
  filename = "${var.assets_dir}/install-alb-operator.sh"
  content  = local.install_script
}

resource "local_file" "example_ingress" {
  filename = "${var.assets_dir}/sample-alb-ingress.yaml"
  content  = local.example_ingress
}

resource "null_resource" "execute_install" {
  triggers = {
    install = sha256(local.install_script)
    policy  = sha256(local.policy_document)
  }

  provisioner "local-exec" {
    command = var.auto_execute ? "chmod +x '${local_file.install_script.filename}' && '${local_file.install_script.filename}'" : "echo 'ALB assets rendered to ${var.assets_dir}; execution skipped by configuration.'"
  }
}

output "policy_arn" {
  value = aws_iam_policy.alb_operator.arn
}

output "install_script_file" {
  value = local_file.install_script.filename
}

output "example_ingress_file" {
  value = local_file.example_ingress.filename
}
