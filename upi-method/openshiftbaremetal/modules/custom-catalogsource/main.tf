# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Custom CatalogSource — Private/mirror operator catalogs
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "custom_catalog_sources" {
  description = "List of custom CatalogSource definitions"
  type = list(object({
    name    = string
    image   = string
    publisher = string
    interval  = string
  }))
  default = [
    {
      name      = "custom-operators"
      image     = "registry.example.com/custom-catalog:latest"
      publisher = "Custom"
      interval  = "30m"
    }
  ]
}
variable "disable_default_sources" {
  description = "Disable default OperatorHub catalog sources"
  type        = bool
  default     = false
}

resource "null_resource" "custom_catalogsource" {
  count = length(var.custom_catalog_sources)

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
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: CatalogSource",
      "metadata:",
      "  name: ${var.custom_catalog_sources[count.index].name}",
      "  namespace: openshift-marketplace",
      "spec:",
      "  sourceType: grpc",
      "  image: ${var.custom_catalog_sources[count.index].image}",
      "  displayName: ${var.custom_catalog_sources[count.index].name}",
      "  publisher: ${var.custom_catalog_sources[count.index].publisher}",
      "  updateStrategy:",
      "    registryPoll:",
      "      interval: ${var.custom_catalog_sources[count.index].interval}",
      "EOF",

      "echo 'CatalogSource ${var.custom_catalog_sources[count.index].name} created'",
    ]
  }
}

# --- Disable Default Catalog Sources ---
resource "null_resource" "disable_default_catalogs" {
  count = var.disable_default_sources ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc patch operatorhub cluster --type merge -p '{\"spec\":{\"disableAllDefaultSources\": true}}'",

      "echo 'Default OperatorHub catalog sources disabled'",
    ]
  }
}
