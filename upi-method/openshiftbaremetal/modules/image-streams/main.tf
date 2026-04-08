# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Image Streams — Pre-built language/framework image streams
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "image_stream_namespace" {
  description = "Namespace for custom image streams"
  type        = string
  default     = "openshift"
}
variable "custom_image_streams" {
  description = "Custom image streams to deploy"
  type = list(object({
    name       = string
    from_image = string
    tag        = string
    scheduled  = bool
  }))
  default = [
    {
      name       = "python-39-custom"
      from_image = "registry.access.redhat.com/ubi8/python-39"
      tag        = "latest"
      scheduled  = true
    },
    {
      name       = "nodejs-18-custom"
      from_image = "registry.access.redhat.com/ubi8/nodejs-18"
      tag        = "latest"
      scheduled  = true
    },
    {
      name       = "openjdk-17-custom"
      from_image = "registry.access.redhat.com/ubi8/openjdk-17"
      tag        = "latest"
      scheduled  = true
    }
  ]
}

resource "null_resource" "image_stream" {
  count = length(var.custom_image_streams)

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<EOF | oc apply -f -",
      "apiVersion: image.openshift.io/v1",
      "kind: ImageStream",
      "metadata:",
      "  name: ${var.custom_image_streams[count.index].name}",
      "  namespace: ${var.image_stream_namespace}",
      "spec:",
      "  lookupPolicy:",
      "    local: true",
      "  tags:",
      "    - name: ${var.custom_image_streams[count.index].tag}",
      "      from:",
      "        kind: DockerImage",
      "        name: ${var.custom_image_streams[count.index].from_image}",
      "      importPolicy:",
      "        scheduled: ${var.custom_image_streams[count.index].scheduled}",
      "      referencePolicy:",
      "        type: Local",
      "EOF",

      "echo 'ImageStream ${var.custom_image_streams[count.index].name} created'",
    ]
  }
}

# Import default S2I image streams
resource "null_resource" "default_image_streams" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Re-import default image streams
      "oc import-image -n openshift --all --confirm python 2>/dev/null || true",
      "oc import-image -n openshift --all --confirm nodejs 2>/dev/null || true",
      "oc import-image -n openshift --all --confirm java 2>/dev/null || true",
      "oc import-image -n openshift --all --confirm httpd 2>/dev/null || true",
      "oc import-image -n openshift --all --confirm nginx 2>/dev/null || true",
      "oc import-image -n openshift --all --confirm php 2>/dev/null || true",
      "oc import-image -n openshift --all --confirm ruby 2>/dev/null || true",
      "oc import-image -n openshift --all --confirm dotnet 2>/dev/null || true",

      "echo 'Default S2I image streams refreshed'",
    ]
  }
}
