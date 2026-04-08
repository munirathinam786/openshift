# =============================================================================
# OpenShift LDAP Identity Provider — OAuth + Group Sync + RBAC
# Configures LDAP authentication, automatic group synchronisation, and
# cluster role bindings for LDAP groups.
# =============================================================================

# --- Create LDAP bind-password Secret ---
resource "null_resource" "ldap_bind_secret" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create secret with LDAP bind password
      "oc create secret generic ldap-bind-password",
      "  --from-literal=bindPassword='${var.ldap_bind_password}'",
      "  -n openshift-config --dry-run=client -o yaml | oc apply -f -",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Upload LDAP CA certificate ---
resource "null_resource" "ldap_ca_configmap" {
  count = var.ldap_ca_cert_file != "" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create configmap ldap-ca-cert",
      "  --from-file=ca.crt=${var.ldap_ca_cert_file}",
      "  -n openshift-config --dry-run=client -o yaml | oc apply -f -",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.ldap_bind_secret]
}

# --- Configure OAuth CR with LDAP Identity Provider ---
resource "null_resource" "oauth_ldap" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: config.openshift.io/v1",
      "kind: OAuth",
      "metadata:",
      "  name: cluster",
      "spec:",
      "  identityProviders:",
      "  - name: ${var.ldap_provider_name}",
      "    mappingMethod: claim",
      "    type: LDAP",
      "    ldap:",
      "      attributes:",
      "        id:",
      "        - ${var.ldap_attr_id}",
      "        email:",
      "        - ${var.ldap_attr_email}",
      "        name:",
      "        - ${var.ldap_attr_name}",
      "        preferredUsername:",
      "        - ${var.ldap_attr_preferred_username}",
      "      bindDN: \"${var.ldap_bind_dn}\"",
      "      bindPassword:",
      "        name: ldap-bind-password",
      "      ${var.ldap_ca_cert_file != "" ? "ca:\\n        name: ldap-ca-cert" : "insecure: ${var.ldap_insecure}"}",
      "      url: \"${var.ldap_url}\"",
      "EOF",

      # Wait for oauth-openshift pods to roll out
      "echo 'Waiting for OAuth pods to restart...'",
      "sleep 30",
      "oc wait pod -l app=oauth-openshift -n openshift-authentication --for=condition=Ready --timeout=300s || true",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.ldap_bind_secret, null_resource.ldap_ca_configmap]
}

# --- LDAP Group Sync CronJob ---
resource "null_resource" "ldap_group_sync" {
  count = var.enable_ldap_group_sync ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create group-sync namespace
      "oc create namespace ldap-group-sync --dry-run=client -o yaml | oc apply -f -",

      # Create group sync ConfigMap with sync configuration
      "cat <<'SYNCEOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: ldap-group-sync-config",
      "  namespace: ldap-group-sync",
      "data:",
      "  sync.yaml: |",
      "    kind: LDAPSyncConfig",
      "    apiVersion: v1",
      "    url: \"${var.ldap_url}\"",
      "    bindDN: \"${var.ldap_bind_dn}\"",
      "    bindPassword:",
      "      file: /etc/secrets/bindPassword",
      "    insecure: ${var.ldap_ca_cert_file == "" ? var.ldap_insecure : "false"}",
      "    ${var.ldap_ca_cert_file != "" ? "ca: /etc/ca/ca.crt" : ""}",
      "    groupUIDNameMapping:",
      "    rfc2307:",
      "      groupsQuery:",
      "        baseDN: \"${var.ldap_group_base_dn}\"",
      "        scope: sub",
      "        derefAliases: never",
      "        filter: ${var.ldap_group_filter}",
      "        pageSize: 0",
      "      groupUIDAttribute: dn",
      "      groupNameAttributes:",
      "      - cn",
      "      groupMembershipAttributes:",
      "      - ${var.ldap_group_membership_attr}",
      "      usersQuery:",
      "        baseDN: \"${var.ldap_user_base_dn}\"",
      "        scope: sub",
      "        derefAliases: never",
      "        pageSize: 0",
      "      userUIDAttribute: dn",
      "      userNameAttributes:",
      "      - ${var.ldap_attr_preferred_username}",
      "SYNCEOF",

      # Create ServiceAccount for group sync
      "oc create serviceaccount ldap-group-syncer -n ldap-group-sync --dry-run=client -o yaml | oc apply -f -",

      # Grant cluster-admin to the SA for group management
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: rbac.authorization.k8s.io/v1",
      "kind: ClusterRoleBinding",
      "metadata:",
      "  name: ldap-group-syncer",
      "roleRef:",
      "  apiGroup: rbac.authorization.k8s.io",
      "  kind: ClusterRole",
      "  name: cluster-admin",
      "subjects:",
      "- kind: ServiceAccount",
      "  name: ldap-group-syncer",
      "  namespace: ldap-group-sync",
      "EOF",

      # Create the CronJob
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: batch/v1",
      "kind: CronJob",
      "metadata:",
      "  name: ldap-group-sync",
      "  namespace: ldap-group-sync",
      "spec:",
      "  schedule: \"${var.ldap_group_sync_schedule}\"",
      "  concurrencyPolicy: Forbid",
      "  successfulJobsHistoryLimit: 3",
      "  failedJobsHistoryLimit: 3",
      "  jobTemplate:",
      "    spec:",
      "      template:",
      "        spec:",
      "          serviceAccountName: ldap-group-syncer",
      "          restartPolicy: Never",
      "          containers:",
      "          - name: ldap-group-sync",
      "            image: registry.redhat.io/openshift4/ose-cli:v4.15",
      "            command:",
      "            - /bin/bash",
      "            - -c",
      "            - |",
      "              oc adm groups sync --sync-config=/etc/config/sync.yaml --confirm",
      "            volumeMounts:",
      "            - name: sync-config",
      "              mountPath: /etc/config",
      "              readOnly: true",
      "            - name: ldap-bind-password",
      "              mountPath: /etc/secrets",
      "              readOnly: true",
      "${var.ldap_ca_cert_file != "" ? "            - name: ldap-ca\\n              mountPath: /etc/ca\\n              readOnly: true" : ""}",
      "          volumes:",
      "          - name: sync-config",
      "            configMap:",
      "              name: ldap-group-sync-config",
      "          - name: ldap-bind-password",
      "            secret:",
      "              secretName: ldap-bind-password-sync",
      "${var.ldap_ca_cert_file != "" ? "          - name: ldap-ca\\n            configMap:\\n              name: ldap-ca-cert-sync" : ""}",
      "EOF",

      # Copy the bind password secret into ldap-group-sync namespace
      "oc get secret ldap-bind-password -n openshift-config -o json",
      "  | jq 'del(.metadata.namespace,.metadata.resourceVersion,.metadata.uid,.metadata.creationTimestamp)'",
      "  | jq '.metadata.name = \"ldap-bind-password-sync\" | .metadata.namespace = \"ldap-group-sync\"'",
      "  | oc apply -n ldap-group-sync -f -",

      # Copy CA cert ConfigMap if present
      "${var.ldap_ca_cert_file != "" ? "oc get configmap ldap-ca-cert -n openshift-config -o json | jq 'del(.metadata.namespace,.metadata.resourceVersion,.metadata.uid,.metadata.creationTimestamp)' | jq '.metadata.name = \"ldap-ca-cert-sync\" | .metadata.namespace = \"ldap-group-sync\"' | oc apply -n ldap-group-sync -f -" : "echo 'No CA cert to copy'"}",

      # Trigger initial sync
      "oc create job --from=cronjob/ldap-group-sync ldap-group-sync-initial -n ldap-group-sync --dry-run=client -o yaml | oc apply -f -",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.oauth_ldap]
}

# --- RBAC — ClusterRoleBindings for LDAP Groups ---
resource "null_resource" "ldap_rbac" {
  count = length(var.ldap_group_role_bindings) > 0 ? 1 : 0

  provisioner "remote-exec" {
    inline = concat(
      ["export KUBECONFIG=${var.kubeconfig}"],
      [for binding in var.ldap_group_role_bindings :
        "oc adm policy add-cluster-role-to-group ${binding.cluster_role} '${binding.group_name}' --dry-run=client -o yaml | oc apply -f -"
      ]
    )

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.ldap_group_sync]
}

# --- Disable default kubeadmin (optional) ---
resource "null_resource" "remove_kubeadmin" {
  count = var.disable_kubeadmin ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "oc delete secret kubeadmin -n kube-system --ignore-not-found=true",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.ldap_rbac]
}
