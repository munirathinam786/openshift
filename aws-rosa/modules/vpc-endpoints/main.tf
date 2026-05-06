variable "cluster_name" {
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

variable "private_route_table_ids" {
  type = list(string)
}

variable "endpoint_security_group_id" {
  type = string
}

variable "interface_endpoint_services" {
  type = list(string)
}

variable "gateway_endpoint_services" {
  type = list(string)
}

variable "additional_tags" {
  type = map(string)
}

locals {
  common_tags = merge(var.additional_tags, { module = "vpc-endpoints" })
}

resource "aws_vpc_endpoint" "interface" {
  for_each = toset(var.interface_endpoint_services)

  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [var.endpoint_security_group_id]

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-${replace(each.value, ".", "-")}-endpoint"
  })
}

resource "aws_vpc_endpoint" "gateway" {
  for_each = toset(var.gateway_endpoint_services)

  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.private_route_table_ids

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-${replace(each.value, ".", "-")}-endpoint"
  })
}

output "endpoint_inventory" {
  value = {
    interface = {
      for name, endpoint in aws_vpc_endpoint.interface : name => {
        id        = endpoint.id
        dns_names = [for entry in endpoint.dns_entry : entry.dns_name]
      }
    }
    gateway = {
      for name, endpoint in aws_vpc_endpoint.gateway : name => {
        id = endpoint.id
      }
    }
  }
}
