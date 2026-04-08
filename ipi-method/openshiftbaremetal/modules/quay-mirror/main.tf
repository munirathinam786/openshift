# =============================================================================
# Module: Local Quay Mirror Registry
# Sets up oc-mirror against a dedicated local Quay server for disconnected
# OpenShift installs. Mirrors OCP release images + required operators.
# =============================================================================

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "quay_host" { type = string }
variable "quay_port" { type = number }
variable "quay_admin_user" { type = string }
variable "quay_admin_password" {
  type      = string
  sensitive = true
}
variable "quay_ca_cert_file" { type = string }
variable "quay_organization" { type = string }
variable "ocp_version" { type = string }
variable "ocp_channel" { type = string }
variable "pull_secret_file" { type = string }
variable "mirror_operators" {
  description = "List of operators to mirror into local Quay"
  type = list(object({
    catalog = string
    packages = list(object({
      name    = string
      channel = string
    }))
  }))
}

locals {
  quay_url       = "${var.quay_host}:${var.quay_port}"
  quay_repo_base = "${local.quay_url}/${var.quay_organization}"
}

# --- Trust the Quay CA on the bastion ---
resource "null_resource" "trust_quay_ca" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "file" {
    source      = var.quay_ca_cert_file
    destination = "/tmp/quay-ca.pem"
  }

  provisioner "remote-exec" {
    inline = [
      "sudo cp /tmp/quay-ca.pem /etc/pki/ca-trust/source/anchors/quay-ca.pem",
      "sudo update-ca-trust extract",
      "rm -f /tmp/quay-ca.pem",
    ]
  }
}

# --- Merge Quay credentials into pull-secret ---
resource "null_resource" "merge_pull_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      # Generate base64 auth for local Quay
      "QUAY_AUTH=$(echo -n '${var.quay_admin_user}:${var.quay_admin_password}' | base64 -w 0)",

      # Merge local Quay creds into pull-secret
      "cat ${var.pull_secret_file} | jq '.auths[\"${local.quay_url}\"] = {\"auth\": \"'\"$QUAY_AUTH\"'\", \"email\": \"\"}' > /tmp/merged-pull-secret.json",
      "cp /tmp/merged-pull-secret.json ${var.pull_secret_file}",
      "rm -f /tmp/merged-pull-secret.json",
      "echo 'Merged Quay credentials into pull-secret'",
    ]
  }

  depends_on = [null_resource.trust_quay_ca]
}

# --- Generate ImageSetConfiguration for oc-mirror ---
resource "local_file" "imageset_config" {
  filename = "${path.module}/generated/imageset-config.yaml"
  content = yamlencode({
    apiVersion = "mirror.openshift.io/v1alpha2"
    kind       = "ImageSetConfiguration"
    storageConfig = {
      local = {
        path = "/home/${var.bastion_user}/quay-mirror/metadata"
      }
    }
    mirror = {
      platform = {
        channels = [
          {
            name       = var.ocp_channel
            minVersion = "${var.ocp_version}.0"
            maxVersion = "${var.ocp_version}.99"
            type       = "ocp"
          }
        ]
        graph = true
      }
      operators = [
        for catalog in var.mirror_operators : {
          catalog = catalog.catalog
          packages = [
            for pkg in catalog.packages : {
              name = pkg.name
              channels = [
                { name = pkg.channel }
              ]
            }
          ]
        }
      ]
      additionalImages = []
    }
  })
}

resource "null_resource" "upload_imageset_config" {
  triggers = {
    config_hash = sha256(local_file.imageset_config.content)
  }

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "mkdir -p ~/quay-mirror",
    ]
  }

  provisioner "file" {
    source      = local_file.imageset_config.filename
    destination = "/home/${var.bastion_user}/quay-mirror/imageset-config.yaml"
  }

  depends_on = [null_resource.merge_pull_secret, local_file.imageset_config]
}

# --- Run oc-mirror to mirror content to local Quay ---
resource "null_resource" "run_oc_mirror" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "echo 'Starting oc-mirror to ${local.quay_url} — this may take a long time...'",
      "oc mirror --config ~/quay-mirror/imageset-config.yaml docker://${local.quay_repo_base} --dest-skip-tls=false 2>&1 | tail -20",
      "echo 'oc-mirror completed'",

      # The results directory contains ICSP/IDMS and CatalogSource YAMLs
      "echo '--- Generated manifests ---'",
      "ls -la ~/quay-mirror/oc-mirror-workspace/results-*/",
    ]
  }

  depends_on = [null_resource.upload_imageset_config]
}

# --- Serve RHCOS boot image from Quay/bastion HTTP ---
resource "null_resource" "stage_rhcos_image" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      # Ensure httpd is serving the RHCOS image
      "sudo dnf install -y httpd || sudo yum install -y httpd",
      "sudo systemctl enable --now httpd",
      "sudo firewall-cmd --permanent --add-service=http 2>/dev/null || true",
      "sudo firewall-cmd --reload 2>/dev/null || true",

      # Download RHCOS qemu image if not already staged
      "RHCOS_DIR=/var/www/html",
      "if [ ! -f $RHCOS_DIR/rhcos-qemu.x86_64.qcow2.gz ]; then",
      "  echo 'Downloading RHCOS image...'",
      "  sudo curl -sL https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/${var.ocp_version}/latest/rhcos-qemu.x86_64.qcow2.gz -o $RHCOS_DIR/rhcos-qemu.x86_64.qcow2.gz",
      "  sudo restorecon -Rv $RHCOS_DIR/ 2>/dev/null || true",
      "fi",

      "RHCOS_SHA=$(sha256sum $RHCOS_DIR/rhcos-qemu.x86_64.qcow2.gz | awk '{print $1}')",
      "echo \"RHCOS image staged at http://${var.bastion_host}:8080/rhcos-qemu.x86_64.qcow2.gz?sha256=$RHCOS_SHA\"",
    ]
  }

  depends_on = [null_resource.trust_quay_ca]
}

output "mirror_registry_url" {
  value = local.quay_url
}

output "mirror_repo_base" {
  value = local.quay_repo_base
}
