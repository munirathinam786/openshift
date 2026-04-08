# =============================================================================
# ACM DR Applications — DRPolicy + Application Failover/Failback
# Configures Disaster Recovery policies and protected applications on the
# ACM hub for automated failover and failback between DC and DR clusters.
# =============================================================================

variable "kubeconfig" {
  description = "Path to hub kubeconfig on bastion"
  type        = string
}

variable "bastion_host" {
  type = string
}

variable "bastion_user" {
  type = string
}

variable "bastion_ssh_key" {
  type = string
}

# ---- DR Policy ----

variable "dr_policy_name" {
  description = "Name of the DRPolicy CR"
  type        = string
  default     = "dr-policy"
}

variable "dr_clusters" {
  description = "List of cluster names in the DR pair (typically [dc-primary, dr-secondary])"
  type        = list(string)
}

variable "scheduling_interval" {
  description = "Replication scheduling interval (e.g. 5m for async, 0m for sync)"
  type        = string
  default     = "5m"
}

variable "dr_mode" {
  description = "DR mode: regional-dr (async) or metro-dr (sync)"
  type        = string
  default     = "regional-dr"
  validation {
    condition     = contains(["regional-dr", "metro-dr"], var.dr_mode)
    error_message = "dr_mode must be 'regional-dr' or 'metro-dr'."
  }
}

# ---- Protected Applications ----

variable "dr_applications" {
  description = "List of applications to protect with DR failover/failback"
  type = list(object({
    name                 = string
    namespace            = string
    placement_name       = string
    preferred_cluster    = string
    failover_cluster     = string
    pvc_selector         = optional(map(string), {})
    kubeobject_protection = optional(bool, false)
    s3_profile_name      = optional(string, "s3-profile")
  }))
  default = []
}

variable "dr_action" {
  description = "DR action to perform: none, failover, failback, or relocate"
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "failover", "failback", "relocate"], var.dr_action)
    error_message = "dr_action must be one of: none, failover, failback, relocate."
  }
}

# ---- Placement & Subscription ----

variable "create_placement_rules" {
  description = "Create PlacementRule and Subscription resources for each application"
  type        = bool
  default     = true
}

variable "channel_namespace" {
  description = "Namespace for the ACM application Channel (git repo)"
  type        = string
  default     = "acm-app-channel"
}

variable "channel_git_url" {
  description = "Git URL for the ACM application Channel"
  type        = string
  default     = ""
}

variable "channel_git_branch" {
  description = "Git branch for the ACM application Channel"
  type        = string
  default     = "main"
}

variable "channel_git_token" {
  description = "Git access token for private Channel repository"
  type        = string
  default     = ""
  sensitive   = true
}

# --- Install ODF DR Hub Operator on ACM Hub ---
resource "null_resource" "odr_hub_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operators.coreos.com/v1alpha1
      kind: Subscription
      metadata:
        name: odr-hub-operator
        namespace: openshift-operators
      spec:
        channel: stable-4.16
        installPlanApproval: Automatic
        name: odr-hub-operator
        source: redhat-operators
        sourceNamespace: openshift-marketplace
      EOF
      EOT
      ,

      "echo 'Waiting for ODR Hub Operator CSV...'",
      "for i in $(seq 1 60); do oc get csv -n openshift-operators 2>/dev/null | grep odr-hub-operator | grep -q Succeeded && break || sleep 10; done",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Create DRPolicy (defines the DR pair and replication schedule) ---
resource "null_resource" "dr_policy" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: ramendr.openshift.io/v1alpha1
      kind: DRPolicy
      metadata:
        name: ${var.dr_policy_name}
      spec:
        drClusters:
%{for cluster in var.dr_clusters~}
          - ${cluster}
%{endfor~}
        schedulingInterval: ${var.scheduling_interval}
      EOF
      EOT
      ,

      "echo 'Waiting for DRPolicy to be validated...'",
      "for i in $(seq 1 60); do",
      "  oc get drpolicy ${var.dr_policy_name} -o jsonpath='{.status.conditions[?(@.type==\"Validated\")].status}' 2>/dev/null | grep -q True && break",
      "  sleep 10",
      "done",
      "oc get drpolicy ${var.dr_policy_name} -o yaml | grep -A5 'conditions' || true",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.odr_hub_operator]
}

# --- Create Application Channel (Git-based if URL provided) ---
resource "null_resource" "app_channel" {
  count = var.channel_git_url != "" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace ${var.channel_namespace} --dry-run=client -o yaml | oc apply -f -",

      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: apps.open-cluster-management.io/v1
      kind: Channel
      metadata:
        name: app-channel
        namespace: ${var.channel_namespace}
      spec:
        type: Git
        pathname: ${var.channel_git_url}
      EOF
      EOT
      ,
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.dr_policy]
}

# --- Create Git Channel Secret (if token provided) ---
resource "null_resource" "channel_git_secret" {
  count = var.channel_git_url != "" && var.channel_git_token != "" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace ${var.channel_namespace} --dry-run=client -o yaml | oc apply -f -",

      <<-EOT
      oc create secret generic channel-git-secret \
        -n ${var.channel_namespace} \
        --from-literal=accessToken=${var.channel_git_token} \
        --dry-run=client -o yaml | oc apply -f -
      EOT
      ,

      <<-EOT
      oc label secret channel-git-secret \
        -n ${var.channel_namespace} \
        apps.open-cluster-management.io/secret-type=acm-access-token-secret \
        --overwrite || true
      EOT
      ,
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.app_channel]
}

# --- Create DRPlacementControl for each protected application ---
resource "null_resource" "dr_placement_control" {
  count = var.create_placement_rules ? length(var.dr_applications) : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create application namespace on the hub
      "oc create namespace ${var.dr_applications[count.index].namespace} --dry-run=client -o yaml | oc apply -f -",

      # Create Placement
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: cluster.open-cluster-management.io/v1beta1
      kind: Placement
      metadata:
        name: ${var.dr_applications[count.index].placement_name}
        namespace: ${var.dr_applications[count.index].namespace}
      spec:
        predicates:
          - requiredClusterSelector:
              labelSelector:
                matchExpressions:
                  - key: name
                    operator: In
                    values:
                      - ${var.dr_applications[count.index].preferred_cluster}
                      - ${var.dr_applications[count.index].failover_cluster}
      EOF
      EOT
      ,

      # Create DRPlacementControl
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: ramendr.openshift.io/v1alpha1
      kind: DRPlacementControl
      metadata:
        name: ${var.dr_applications[count.index].name}-drpc
        namespace: ${var.dr_applications[count.index].namespace}
        labels:
          app: ${var.dr_applications[count.index].name}
      spec:
        preferredCluster: ${var.dr_applications[count.index].preferred_cluster}
        failoverCluster: ${var.dr_applications[count.index].failover_cluster}
        drPolicyRef:
          name: ${var.dr_policy_name}
        placementRef:
          kind: Placement
          name: ${var.dr_applications[count.index].placement_name}
        pvcSelector:
          matchLabels:
%{for k, v in var.dr_applications[count.index].pvc_selector~}
            ${k}: "${v}"
%{endfor~}
      EOF
      EOT
      ,
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.dr_policy]
}

# --- Execute Failover/Failback/Relocate action ---
resource "null_resource" "dr_failover_action" {
  count = var.dr_action != "none" ? length(var.dr_applications) : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Patch the DRPlacementControl to trigger the action
      <<-EOT
      %{if var.dr_action == "failover" ~}
      oc patch drplacementcontrol ${var.dr_applications[count.index].name}-drpc \
        -n ${var.dr_applications[count.index].namespace} \
        --type=merge \
        -p '{"spec":{"action":"Failover","failoverCluster":"${var.dr_applications[count.index].failover_cluster}"}}'
      %{endif~}

      %{if var.dr_action == "failback" || var.dr_action == "relocate" ~}
      oc patch drplacementcontrol ${var.dr_applications[count.index].name}-drpc \
        -n ${var.dr_applications[count.index].namespace} \
        --type=merge \
        -p '{"spec":{"action":"Relocate","preferredCluster":"${var.dr_applications[count.index].preferred_cluster}"}}'
      %{endif~}
      EOT
      ,

      # Wait for DR action to complete
      "echo 'Waiting for DR action (${var.dr_action}) to complete for ${var.dr_applications[count.index].name}...'",
      "for i in $(seq 1 120); do",
      "  PHASE=$(oc get drplacementcontrol ${var.dr_applications[count.index].name}-drpc -n ${var.dr_applications[count.index].namespace} -o jsonpath='{.status.phase}' 2>/dev/null)",
      "  [ \"$PHASE\" = \"Deployed\" ] && echo 'DR action completed successfully.' && break",
      "  sleep 15",
      "done",
      "oc get drplacementcontrol ${var.dr_applications[count.index].name}-drpc -n ${var.dr_applications[count.index].namespace} -o jsonpath='{.status}' || true",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.dr_placement_control]
}

output "dr_policy_name" {
  value = var.dr_policy_name
}

output "protected_applications" {
  value = [for app in var.dr_applications : app.name]
}

output "dr_action" {
  value = var.dr_action
}
