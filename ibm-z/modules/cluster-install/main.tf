variable "assets_dir" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "bastion_host" {
  type = string
}

variable "bastion_user" {
  type = string
}

variable "bastion_ssh_private_key_file" {
  type = string
}

variable "openshift_install_binary" {
  type = string
}

variable "remote_assets_dir" {
  type = string
}

variable "auto_approve_install" {
  type = bool
}

locals {
  remote_install_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    REMOTE_DIR="${var.remote_assets_dir}"
    INSTALLER="${var.openshift_install_binary}"

    mkdir -p "$REMOTE_DIR"
    cd "$REMOTE_DIR"
    "$INSTALLER" agent create image --dir .

    echo "Agent ISO and PXE artifacts generated in $REMOTE_DIR"

    if [[ "${var.auto_approve_install}" == "true" ]]; then
      "$INSTALLER" wait-for bootstrap-complete --dir . --log-level=info
      "$INSTALLER" wait-for install-complete --dir . --log-level=info
    else
      echo "Install monitoring disabled. Run openshift-install wait-for install-complete manually when ready."
    fi
  EOT

  launch_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    remote_target="${var.bastion_user}@${var.bastion_host}"

    ssh -i "${var.bastion_ssh_private_key_file}" -o StrictHostKeyChecking=no "$remote_target" "mkdir -p '${var.remote_assets_dir}'"
    scp -i "${var.bastion_ssh_private_key_file}" -o StrictHostKeyChecking=no "${var.assets_dir}/install-config.yaml" "${var.assets_dir}/agent-config.yaml" "$remote_target:${var.remote_assets_dir}/"
    ssh -i "${var.bastion_ssh_private_key_file}" -o StrictHostKeyChecking=no "$remote_target" "cat > '${var.remote_assets_dir}/run-ibmz-install.sh' <<'SCRIPT'
${local.remote_install_script}
SCRIPT
chmod +x '${var.remote_assets_dir}/run-ibmz-install.sh'
'${var.remote_assets_dir}/run-ibmz-install.sh'"
  EOT
}

resource "local_file" "launch_script" {
  filename = "${var.assets_dir}/launch-ibmz-install.sh"
  content  = local.launch_script
}

resource "null_resource" "launch_install" {
  triggers = {
    install_config = fileexists("${var.assets_dir}/install-config.yaml") ? filesha256("${var.assets_dir}/install-config.yaml") : "missing"
    agent_config   = fileexists("${var.assets_dir}/agent-config.yaml") ? filesha256("${var.assets_dir}/agent-config.yaml") : "missing"
  }

  provisioner "local-exec" {
    command = "chmod +x '${local_file.launch_script.filename}' && '${local_file.launch_script.filename}'"
  }
}

output "remote_assets_dir" {
  value = var.remote_assets_dir
}

output "launch_script_file" {
  value = local_file.launch_script.filename
}
