# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Velero Schedule — Automated backup schedules for namespaces
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "velero_schedules" {
  description = "Backup schedules for namespaces"
  type = list(object({
    name                     = string
    schedule                 = string
    included_namespaces      = list(string)
    excluded_resources       = list(string)
    ttl                      = string
    snapshot_volumes         = bool
    default_volumes_to_restic = bool
  }))
  default = [
    {
      name                     = "daily-app-backup"
      schedule                 = "0 2 * * *"
      included_namespaces      = ["*"]
      excluded_resources       = ["events", "events.events.k8s.io"]
      ttl                      = "720h"
      snapshot_volumes         = true
      default_volumes_to_restic = false
    },
    {
      name                     = "hourly-critical-backup"
      schedule                 = "0 * * * *"
      included_namespaces      = ["critical-app"]
      excluded_resources       = ["events"]
      ttl                      = "168h"
      snapshot_volumes         = true
      default_volumes_to_restic = false
    }
  ]
}

resource "null_resource" "velero_schedule" {
  count = length(var.velero_schedules)

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
      "apiVersion: velero.io/v1",
      "kind: Schedule",
      "metadata:",
      "  name: ${var.velero_schedules[count.index].name}",
      "  namespace: openshift-adp",
      "spec:",
      "  schedule: '${var.velero_schedules[count.index].schedule}'",
      "  template:",
      "    includedNamespaces:",
      join("\n", [for ns in var.velero_schedules[count.index].included_namespaces : "      - ${ns}"]),
      "    excludedResources:",
      join("\n", [for res in var.velero_schedules[count.index].excluded_resources : "      - ${res}"]),
      "    ttl: ${var.velero_schedules[count.index].ttl}",
      "    snapshotVolumes: ${var.velero_schedules[count.index].snapshot_volumes}",
      "    defaultVolumesToRestic: ${var.velero_schedules[count.index].default_volumes_to_restic}",
      "    storageLocation: default",
      "    hooks: {}",
      "  useOwnerReferencesInBackup: false",
      "EOF",

      "echo 'Velero Schedule ${var.velero_schedules[count.index].name} created'",
    ]
  }
}
