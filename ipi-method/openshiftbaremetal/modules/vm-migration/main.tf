# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: VM Migration (MTV — Migration Toolkit for Virtualization)
# Migrates VMs from VMware vSphere, RHV, oVirt, or OpenStack to OpenShift Virtualization
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

# ---- Operator ----
variable "mtv_channel" {
  type    = string
  default = "release-v2.7"
}
variable "mtv_install_plan_approval" {
  type    = string
  default = "Automatic"
}

# ---- Source Provider ----
variable "source_provider_type" {
  description = "Source virtualization provider (vsphere, ovirt, openstack)"
  type        = string
  default     = "vsphere"
}
variable "source_provider_name" {
  description = "Name for the source provider resource"
  type        = string
  default     = "vmware-source"
}
variable "source_provider_url" {
  description = "API URL of the source provider (e.g. vCenter URL https://vcenter.example.com/sdk)"
  type        = string
}
variable "source_provider_username" {
  description = "Username for the source provider"
  type        = string
}
variable "source_provider_password" {
  description = "Password for the source provider"
  type        = string
  sensitive   = true
}
variable "source_provider_thumbprint" {
  description = "SSL thumbprint of the source provider (vSphere). Leave empty for RHV/OpenStack."
  type        = string
  default     = ""
}
variable "source_provider_ca_cert" {
  description = "CA certificate for the source provider (PEM format, path on bastion)"
  type        = string
  default     = ""
}
variable "source_provider_insecure_skip_verify" {
  description = "Skip TLS verification for source provider (not recommended for production)"
  type        = bool
  default     = false
}

# ---- Destination Provider (host OpenShift cluster) ----
variable "destination_provider_name" {
  description = "Name for the destination (OpenShift) provider resource"
  type        = string
  default     = "host"
}

# ---- Network Map ----
variable "network_map_name" {
  description = "Name for the network mapping"
  type        = string
  default     = "vm-network-map"
}
variable "network_mappings" {
  description = "Map source networks to destination networks"
  type = list(object({
    source_network      = string
    destination_network = string
    destination_type    = optional(string, "pod")
  }))
  default = [
    {
      source_network      = "VM Network"
      destination_network = "pod"
      destination_type    = "pod"
    }
  ]
}

# ---- Storage Map ----
variable "storage_map_name" {
  description = "Name for the storage mapping"
  type        = string
  default     = "vm-storage-map"
}
variable "storage_mappings" {
  description = "Map source datastores to destination storage classes"
  type = list(object({
    source_datastore         = string
    destination_storage_class = string
    volume_mode              = optional(string, "Filesystem")
  }))
  default = [
    {
      source_datastore         = "datastore1"
      destination_storage_class = "ocs-storagecluster-ceph-rbd-virtualization"
      volume_mode              = "Filesystem"
    }
  ]
}

# ---- Migration Plan ----
variable "migration_plan_name" {
  description = "Name for the migration plan"
  type        = string
  default     = "vm-migration-plan"
}
variable "migration_plan_namespace" {
  description = "Namespace for the migration plan and migrated VMs"
  type        = string
  default     = "openshift-mtv"
}
variable "migration_vms" {
  description = "List of VMs to migrate"
  type = list(object({
    name       = string
    id         = optional(string, "")
    namespace  = optional(string, "")
    hooks      = optional(list(object({
      hook_name = string
      step      = string
    })), [])
  }))
  default = []
}

# ---- Migration Options ----
variable "migration_type" {
  description = "cold (shutdown VM first) or warm (live, vSphere only with CBT)"
  type        = string
  default     = "cold"
}
variable "migration_start_immediately" {
  description = "Start migration immediately after plan creation"
  type        = bool
  default     = false
}
variable "migration_cutover_datetime" {
  description = "Scheduled cutover time for warm migration (ISO 8601, e.g. 2026-04-10T02:00:00Z)"
  type        = string
  default     = ""
}
variable "migration_preserve_static_ips" {
  description = "Preserve static IPs from source VMs"
  type        = bool
  default     = true
}
variable "migration_preserve_mac_addresses" {
  description = "Preserve MAC addresses from source VMs"
  type        = bool
  default     = false
}

# ---- Pre/Post Migration Hooks ----
variable "migration_hooks" {
  description = "Ansible playbook hooks to run pre/post migration"
  type = list(object({
    name      = string
    namespace = string
    playbook  = string
    image     = optional(string, "quay.io/konveyor/hook-runner:latest")
  }))
  default = []
}

# ---- Transfer Network ----
variable "migration_transfer_network" {
  description = "Dedicated network for disk transfer (NAD name or empty for default)"
  type        = string
  default     = ""
}

# ---- Concurrent VMs ----
variable "migration_max_concurrent_vms" {
  description = "Maximum number of VMs to migrate simultaneously"
  type        = number
  default     = 10
}
variable "migration_max_concurrent_disks_per_vm" {
  description = "Maximum concurrent disk transfers per VM"
  type        = number
  default     = 2
}

# =============================================================================
# Resources
# =============================================================================

resource "null_resource" "mtv_namespace" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create namespace
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: openshift-mtv",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: migration",
      "  namespace: openshift-mtv",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-mtv",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: mtv-operator",
      "  namespace: openshift-mtv",
      "spec:",
      "  channel: ${var.mtv_channel}",
      "  installPlanApproval: ${var.mtv_install_plan_approval}",
      "  name: mtv-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for MTV operator
      "echo 'Waiting for MTV operator to install...'",
      "for i in $(seq 1 90); do",
      "  oc get csv -n openshift-mtv 2>/dev/null | grep mtv-operator | grep -q Succeeded && break",
      "  sleep 10",
      "done",
      "oc get csv -n openshift-mtv | grep mtv-operator | grep -q Succeeded || { echo 'ERROR: MTV operator not ready'; exit 1; }",

      # Create ForkliftController CR
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: forklift.konveyor.io/v1beta1",
      "kind: ForkliftController",
      "metadata:",
      "  name: forklift-controller",
      "  namespace: openshift-mtv",
      "spec:",
      "  olm_managed: true",
      "EOF",

      # Wait for ForkliftController
      "echo 'Waiting for ForkliftController to become ready...'",
      "for i in $(seq 1 60); do",
      "  PHASE=$(oc get forkliftcontroller forklift-controller -n openshift-mtv -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}' 2>/dev/null)",
      "  [ \"$PHASE\" = \"True\" ] && break",
      "  sleep 10",
      "done",
    ]
  }
}

resource "null_resource" "mtv_source_provider_secret" {
  depends_on = [null_resource.mtv_namespace]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create provider credentials secret
      "cat <<EOF | oc apply -f -",
      "apiVersion: v1",
      "kind: Secret",
      "metadata:",
      "  name: ${var.source_provider_name}-secret",
      "  namespace: openshift-mtv",
      "  labels:",
      "    createdForProviderType: ${var.source_provider_type}",
      "    createdForResourceType: providers",
      "type: Opaque",
      "stringData:",
      "  user: ${var.source_provider_username}",
      "  password: ${var.source_provider_password}",
      "  thumbprint: ${var.source_provider_thumbprint}",
      "  insecureSkipVerify: \"${var.source_provider_insecure_skip_verify}\"",
      "EOF",
    ]
  }
}

resource "null_resource" "mtv_source_provider" {
  depends_on = [null_resource.mtv_source_provider_secret]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create source provider
      "cat <<EOF | oc apply -f -",
      "apiVersion: forklift.konveyor.io/v1beta1",
      "kind: Provider",
      "metadata:",
      "  name: ${var.source_provider_name}",
      "  namespace: openshift-mtv",
      "spec:",
      "  type: ${var.source_provider_type}",
      "  url: ${var.source_provider_url}",
      "  secret:",
      "    name: ${var.source_provider_name}-secret",
      "    namespace: openshift-mtv",
      "EOF",

      # Wait for provider to become Ready
      "echo 'Waiting for source provider to become Ready...'",
      "for i in $(seq 1 60); do",
      "  STATUS=$(oc get provider ${var.source_provider_name} -n openshift-mtv -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}' 2>/dev/null)",
      "  [ \"$STATUS\" = \"True\" ] && break",
      "  sleep 10",
      "done",
    ]
  }
}

resource "null_resource" "mtv_destination_provider" {
  depends_on = [null_resource.mtv_namespace]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create host (OpenShift) provider
      "cat <<EOF | oc apply -f -",
      "apiVersion: forklift.konveyor.io/v1beta1",
      "kind: Provider",
      "metadata:",
      "  name: ${var.destination_provider_name}",
      "  namespace: openshift-mtv",
      "spec:",
      "  type: openshift",
      "  url: https://kubernetes.default.svc:443",
      "  secret: {}",
      "EOF",
    ]
  }
}

resource "null_resource" "mtv_network_map" {
  depends_on = [null_resource.mtv_source_provider, null_resource.mtv_destination_provider]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create NetworkMap
      "cat <<EOF | oc apply -f -",
      "apiVersion: forklift.konveyor.io/v1beta1",
      "kind: NetworkMap",
      "metadata:",
      "  name: ${var.network_map_name}",
      "  namespace: openshift-mtv",
      "spec:",
      "  map: []",
      "  provider:",
      "    source:",
      "      name: ${var.source_provider_name}",
      "      namespace: openshift-mtv",
      "    destination:",
      "      name: ${var.destination_provider_name}",
      "      namespace: openshift-mtv",
      "EOF",
    ]
  }
}

resource "null_resource" "mtv_storage_map" {
  depends_on = [null_resource.mtv_source_provider, null_resource.mtv_destination_provider]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create StorageMap
      "cat <<EOF | oc apply -f -",
      "apiVersion: forklift.konveyor.io/v1beta1",
      "kind: StorageMap",
      "metadata:",
      "  name: ${var.storage_map_name}",
      "  namespace: openshift-mtv",
      "spec:",
      "  map: []",
      "  provider:",
      "    source:",
      "      name: ${var.source_provider_name}",
      "      namespace: openshift-mtv",
      "    destination:",
      "      name: ${var.destination_provider_name}",
      "      namespace: openshift-mtv",
      "EOF",
    ]
  }
}

resource "null_resource" "mtv_migration_plan" {
  count      = length(var.migration_vms) > 0 ? 1 : 0
  depends_on = [null_resource.mtv_network_map, null_resource.mtv_storage_map]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create Migration Plan
      "cat <<EOF | oc apply -f -",
      "apiVersion: forklift.konveyor.io/v1beta1",
      "kind: Plan",
      "metadata:",
      "  name: ${var.migration_plan_name}",
      "  namespace: openshift-mtv",
      "spec:",
      "  warm: ${var.migration_type == "warm" ? "true" : "false"}",
      "  preserveStaticIPs: ${var.migration_preserve_static_ips}",
      "  provider:",
      "    source:",
      "      name: ${var.source_provider_name}",
      "      namespace: openshift-mtv",
      "    destination:",
      "      name: ${var.destination_provider_name}",
      "      namespace: openshift-mtv",
      "  map:",
      "    network:",
      "      name: ${var.network_map_name}",
      "      namespace: openshift-mtv",
      "    storage:",
      "      name: ${var.storage_map_name}",
      "      namespace: openshift-mtv",
      "  targetNamespace: ${var.migration_plan_namespace}",
      "  vms: []",
      "EOF",
    ]
  }
}

resource "null_resource" "mtv_migration_execute" {
  count      = var.migration_start_immediately && length(var.migration_vms) > 0 ? 1 : 0
  depends_on = [null_resource.mtv_migration_plan]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create Migration CR to start the migration
      "cat <<EOF | oc apply -f -",
      "apiVersion: forklift.konveyor.io/v1beta1",
      "kind: Migration",
      "metadata:",
      "  name: ${var.migration_plan_name}-execution",
      "  namespace: openshift-mtv",
      "spec:",
      "  plan:",
      "    name: ${var.migration_plan_name}",
      "    namespace: openshift-mtv",
      "EOF",

      "echo 'Migration initiated. Monitor with: oc get migration -n openshift-mtv'",
    ]
  }
}

output "mtv_namespace" {
  value = "openshift-mtv"
}

output "mtv_status" {
  value = "MTV operator deployed. Source provider: ${var.source_provider_name} (${var.source_provider_type})"
}
