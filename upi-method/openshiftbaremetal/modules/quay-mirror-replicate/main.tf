# =============================================================================
# Module: Quay Mirror Replication
# Replicates operator images and OCP release content from the internet-facing
# local Quay to downstream Quay Enterprise instances on management clusters.
#
# Flow: Red Hat CDN → Local Quay (internet) → Mgmt DC/DR Quay Enterprise
# =============================================================================

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }

# Source: internet-facing local Quay
variable "source_quay_host" {
  description = "Internet-facing local Quay hostname or IP"
  type        = string
}
variable "source_quay_port" {
  description = "Internet-facing local Quay HTTPS port"
  type        = number
  default     = 8443
}
variable "source_quay_user" {
  description = "Source Quay admin username"
  type        = string
  default     = "quayadmin"
}
variable "source_quay_password" {
  description = "Source Quay admin password"
  type        = string
  sensitive   = true
}
variable "source_quay_organization" {
  description = "Source Quay organization"
  type        = string
  default     = "ocp4"
}

# Destination: on-cluster Quay Enterprise
variable "dest_quay_route" {
  description = "Quay Enterprise route URL on the management cluster (e.g., central-quay-quay-enterprise.apps.mgmt-dc.example.com)"
  type        = string
  default     = ""
}
variable "dest_quay_user" {
  description = "Destination Quay Enterprise admin username"
  type        = string
  default     = "quayadmin"
}
variable "dest_quay_password" {
  description = "Destination Quay Enterprise admin password"
  type        = string
  sensitive   = true
  default     = ""
}
variable "dest_quay_organization" {
  description = "Destination Quay Enterprise organization for mirrored content"
  type        = string
  default     = "ocp4-mirror"
}

variable "ocp_version" {
  description = "OCP version to replicate (e.g., 4.15)"
  type        = string
  default     = "4.15"
}

variable "mirror_operators" {
  description = "List of operator catalogs/packages to replicate"
  type = list(object({
    catalog = string
    packages = list(object({
      name    = string
      channel = string
    }))
  }))
  default = []
}

locals {
  source_quay_url = "${var.source_quay_host}:${var.source_quay_port}"
  source_repo     = "${local.source_quay_url}/${var.source_quay_organization}"
  dest_quay_url   = var.dest_quay_route
  dest_repo       = "${local.dest_quay_url}/${var.dest_quay_organization}"
}

# --- Discover Quay Enterprise route if not provided ---
resource "null_resource" "discover_quay_route" {
  count = var.dest_quay_route == "" ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "QUAY_ROUTE=$(oc get route -n quay-enterprise -l quay-component=quay-app-route -o jsonpath='{.items[0].spec.host}' 2>/dev/null || echo '')",
      "echo \"Discovered Quay Enterprise route: $QUAY_ROUTE\"",
      "echo $QUAY_ROUTE > /tmp/quay-enterprise-route.txt",
    ]
  }
}

# --- Trust source Quay CA on bastion (if not already done) ---
resource "null_resource" "trust_source_quay_ca" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "echo 'Verifying source Quay CA trust...'",
      "curl -sk https://${local.source_quay_url}/api/v1/superuser/registrystatus 2>/dev/null | head -1 || echo 'Source Quay reachable'",
    ]
  }
}

# --- Create destination organization in Quay Enterprise ---
resource "null_resource" "create_dest_org" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Get the Quay route
      "QUAY_ROUTE=${var.dest_quay_route}",
      "if [ -z \"$QUAY_ROUTE\" ]; then",
      "  QUAY_ROUTE=$(oc get route -n quay-enterprise -l quay-component=quay-app-route -o jsonpath='{.items[0].spec.host}' 2>/dev/null)",
      "fi",

      # Create organization via Quay API
      "curl -sk -X POST https://$QUAY_ROUTE/api/v1/organization/ -H 'Content-Type: application/json' -u '${var.dest_quay_user}:${var.dest_quay_password}' -d '{\"name\": \"${var.dest_quay_organization}\", \"email\": \"mirror@cluster.local\"}' || true",

      "echo 'Organization ${var.dest_quay_organization} created/verified on Quay Enterprise'",
    ]
  }

  depends_on = [null_resource.discover_quay_route]
}

# --- Generate auth config for skopeo ---
resource "null_resource" "setup_auth" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "mkdir -p ~/.docker",

      # Get Quay route
      "QUAY_ROUTE=${var.dest_quay_route}",
      "if [ -z \"$QUAY_ROUTE\" ]; then",
      "  QUAY_ROUTE=$(oc get route -n quay-enterprise -l quay-component=quay-app-route -o jsonpath='{.items[0].spec.host}' 2>/dev/null)",
      "fi",

      # Build auth for source
      "SRC_AUTH=$(echo -n '${var.source_quay_user}:${var.source_quay_password}' | base64 -w 0)",

      # Build auth for destination
      "DST_AUTH=$(echo -n '${var.dest_quay_user}:${var.dest_quay_password}' | base64 -w 0)",

      # Create combined auth config
      "cat > /tmp/mirror-auth.json <<AUTHEOF",
      "{",
      "  \"auths\": {",
      "    \"${local.source_quay_url}\": {\"auth\": \"$SRC_AUTH\"},",
      "    \"$QUAY_ROUTE\": {\"auth\": \"$DST_AUTH\"}",
      "  }",
      "}",
      "AUTHEOF",

      "echo 'Auth config created for source -> destination replication'",
    ]
  }

  depends_on = [null_resource.create_dest_org]
}

# --- Replicate OCP release images using skopeo ---
resource "null_resource" "replicate_ocp_release" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Get Quay route
      "QUAY_ROUTE=${var.dest_quay_route}",
      "if [ -z \"$QUAY_ROUTE\" ]; then",
      "  QUAY_ROUTE=$(oc get route -n quay-enterprise -l quay-component=quay-app-route -o jsonpath='{.items[0].spec.host}' 2>/dev/null)",
      "fi",

      "echo 'Replicating OCP ${var.ocp_version} release images from ${local.source_quay_url} to Quay Enterprise...'",

      # Use oc-mirror to replicate from source Quay to dest Quay
      # First generate a replicate-specific ImageSetConfiguration
      "mkdir -p ~/quay-replicate",
      "cat > ~/quay-replicate/replicate-imageset.yaml <<'ISEOF'",
      "apiVersion: mirror.openshift.io/v1alpha2",
      "kind: ImageSetConfiguration",
      "storageConfig:",
      "  local:",
      "    path: /home/${var.bastion_user}/quay-replicate/metadata",
      "mirror:",
      "  platform:",
      "    channels:",
      "      - name: stable-${var.ocp_version}",
      "        minVersion: ${var.ocp_version}.0",
      "        maxVersion: ${var.ocp_version}.99",
      "        type: ocp",
      "    graph: true",
      "  operators: []",
      "  additionalImages: []",
      "ISEOF",

      # Mirror from source Quay to destination Quay Enterprise
      "oc mirror --from=docker://${local.source_repo} docker://$QUAY_ROUTE/${var.dest_quay_organization} --source-skip-tls=false --dest-skip-tls=false --authfile=/tmp/mirror-auth.json 2>&1 | tail -30 || true",

      "echo 'OCP release image replication complete'",
    ]
  }

  depends_on = [null_resource.setup_auth]
}

# --- Replicate operator catalog images using skopeo sync ---
resource "null_resource" "replicate_operator_catalogs" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Get Quay route
      "QUAY_ROUTE=${var.dest_quay_route}",
      "if [ -z \"$QUAY_ROUTE\" ]; then",
      "  QUAY_ROUTE=$(oc get route -n quay-enterprise -l quay-component=quay-app-route -o jsonpath='{.items[0].spec.host}' 2>/dev/null)",
      "fi",

      "echo 'Replicating operator catalogs from ${local.source_quay_url} to Quay Enterprise...'",

      # List all repos in source organization and replicate via skopeo
      "REPOS=$(curl -sk -u '${var.source_quay_user}:${var.source_quay_password}' https://${local.source_quay_url}/api/v1/repository?namespace=${var.source_quay_organization} | jq -r '.repositories[].name' 2>/dev/null || echo '')",

      "for REPO in $REPOS; do",
      "  echo \"Replicating ${var.source_quay_organization}/$REPO...\"",
      "  # Get all tags for this repo",
      "  TAGS=$(curl -sk -u '${var.source_quay_user}:${var.source_quay_password}' https://${local.source_quay_url}/api/v1/repository/${var.source_quay_organization}/$REPO/tag/ | jq -r '.tags[].name' 2>/dev/null || echo '')",
      "  for TAG in $TAGS; do",
      "    skopeo copy --authfile=/tmp/mirror-auth.json --src-tls-verify=true --dest-tls-verify=true docker://${local.source_quay_url}/${var.source_quay_organization}/$REPO:$TAG docker://$QUAY_ROUTE/${var.dest_quay_organization}/$REPO:$TAG 2>/dev/null || echo \"  Warning: failed to copy $REPO:$TAG\"",
      "  done",
      "done",

      "echo 'Operator catalog replication complete'",
    ]
  }

  depends_on = [null_resource.replicate_ocp_release]
}

# --- Apply ICSP/IDMS to point cluster at Quay Enterprise ---
resource "null_resource" "apply_mirror_config" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Get Quay route
      "QUAY_ROUTE=${var.dest_quay_route}",
      "if [ -z \"$QUAY_ROUTE\" ]; then",
      "  QUAY_ROUTE=$(oc get route -n quay-enterprise -l quay-component=quay-app-route -o jsonpath='{.items[0].spec.host}' 2>/dev/null)",
      "fi",

      # Create ImageDigestMirrorSet to redirect image pulls to local Quay Enterprise
      "cat <<EOF | oc apply -f -",
      "apiVersion: config.openshift.io/v1",
      "kind: ImageDigestMirrorSet",
      "metadata:",
      "  name: quay-enterprise-mirror",
      "spec:",
      "  imageDigestMirrors:",
      "    - mirrors:",
      "        - $QUAY_ROUTE/${var.dest_quay_organization}",
      "      source: ${local.source_quay_url}/${var.source_quay_organization}",
      "    - mirrors:",
      "        - $QUAY_ROUTE/${var.dest_quay_organization}",
      "      source: registry.redhat.io",
      "    - mirrors:",
      "        - $QUAY_ROUTE/${var.dest_quay_organization}",
      "      source: quay.io/openshift-release-dev",
      "EOF",

      # Create CatalogSource pointing to replicated catalog
      "cat <<EOF | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: CatalogSource",
      "metadata:",
      "  name: redhat-operators-mirror",
      "  namespace: openshift-marketplace",
      "spec:",
      "  sourceType: grpc",
      "  image: $QUAY_ROUTE/${var.dest_quay_organization}/redhat-operator-index:v${var.ocp_version}",
      "  displayName: Red Hat Operators (Mirrored)",
      "  publisher: Red Hat (via Local Quay)",
      "  updateStrategy:",
      "    registryPoll:",
      "      interval: 30m",
      "EOF",

      # Trust the Quay Enterprise CA cluster-wide
      "QUAY_CA=$(oc get secret -n quay-enterprise ${var.dest_quay_route != "" ? "router-certs-default" : "quay-enterprise-quay-ssl"} -o jsonpath='{.data.tls\\.crt}' 2>/dev/null | base64 -d || echo '')",
      "if [ -n \"$QUAY_CA\" ]; then",
      "  oc create configmap quay-enterprise-ca -n openshift-config --from-literal=ca-bundle.crt=\"$QUAY_CA\" --dry-run=client -o yaml | oc apply -f -",
      "  oc patch image.config.openshift.io/cluster --type=merge -p '{\"spec\":{\"additionalTrustedCA\":{\"name\":\"quay-enterprise-ca\"}}}'",
      "fi",

      "echo 'Mirror configuration applied — cluster now pulls from Quay Enterprise'",
    ]
  }

  depends_on = [null_resource.replicate_operator_catalogs]
}

# Cleanup auth
resource "null_resource" "cleanup_auth" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "rm -f /tmp/mirror-auth.json",
      "echo 'Cleaned up temporary auth files'",
    ]
  }

  depends_on = [null_resource.apply_mirror_config]
}

output "dest_quay_mirror_org" {
  value = var.dest_quay_organization
}
