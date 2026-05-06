# Author: Sathishkumar Munirathinam
# Module: PostgreSQL — StatefulSet for Temporal + LiteLLM backend

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "postgres_password" { type = string; sensitive = true }
variable "postgres_storage_size" { type = string; default = "50Gi" }
variable "postgres_storage_class" { type = string }

resource "null_resource" "postgresql_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-postgresql-credentials -n ${var.namespace} \\",
      "  --from-literal=POSTGRES_USER=agentbuilder \\",
      "  --from-literal=POSTGRES_PASSWORD='${var.postgres_password}' \\",
      "  --from-literal=POSTGRES_DB=agentbuilder \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "postgresql_init_script" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'CMEOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: agent-builder-postgresql-init",
      "  namespace: ${var.namespace}",
      "data:",
      "  init.sql: |",
      "    CREATE DATABASE temporal_db;",
      "    CREATE DATABASE temporal_visibility_db;",
      "    CREATE DATABASE litellm_db;",
      "    CREATE DATABASE agent_registry_db;",
      "    GRANT ALL PRIVILEGES ON DATABASE temporal_db TO agentbuilder;",
      "    GRANT ALL PRIVILEGES ON DATABASE temporal_visibility_db TO agentbuilder;",
      "    GRANT ALL PRIVILEGES ON DATABASE litellm_db TO agentbuilder;",
      "    GRANT ALL PRIVILEGES ON DATABASE agent_registry_db TO agentbuilder;",
      "CMEOF",
    ]
  }

  depends_on = [null_resource.postgresql_secret]
}

resource "null_resource" "postgresql" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: PersistentVolumeClaim",
      "metadata:",
      "  name: agent-builder-postgresql-data",
      "  namespace: ${var.namespace}",
      "spec:",
      "  accessModes:",
      "    - ReadWriteOnce",
      "  storageClassName: ${var.postgres_storage_class}",
      "  resources:",
      "    requests:",
      "      storage: ${var.postgres_storage_size}",
      "---",
      "apiVersion: apps/v1",
      "kind: StatefulSet",
      "metadata:",
      "  name: agent-builder-postgresql",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: postgresql",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  serviceName: agent-builder-postgresql",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: postgresql",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: postgresql",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      securityContext:",
      "        fsGroup: 26",
      "      containers:",
      "        - name: postgresql",
      "          image: registry.redhat.io/rhel9/postgresql-16:latest",
      "          ports:",
      "            - containerPort: 5432",
      "              name: postgresql",
      "          envFrom:",
      "            - secretRef:",
      "                name: agent-builder-postgresql-credentials",
      "          env:",
      "            - name: POSTGRESQL_ADMIN_PASSWORD",
      "              valueFrom:",
      "                secretKeyRef:",
      "                  name: agent-builder-postgresql-credentials",
      "                  key: POSTGRES_PASSWORD",
      "          resources:",
      "            requests:",
      "              cpu: 500m",
      "              memory: 1Gi",
      "            limits:",
      "              cpu: '2'",
      "              memory: 4Gi",
      "          volumeMounts:",
      "            - name: data",
      "              mountPath: /var/lib/pgsql/data",
      "            - name: init-scripts",
      "              mountPath: /opt/app-root/src/postgresql-init",
      "          livenessProbe:",
      "            exec:",
      "              command:",
      "                - /bin/sh",
      "                - -c",
      "                - pg_isready -U agentbuilder",
      "            initialDelaySeconds: 30",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            exec:",
      "              command:",
      "                - /bin/sh",
      "                - -c",
      "                - pg_isready -U agentbuilder",
      "            initialDelaySeconds: 5",
      "            periodSeconds: 10",
      "      volumes:",
      "        - name: data",
      "          persistentVolumeClaim:",
      "            claimName: agent-builder-postgresql-data",
      "        - name: init-scripts",
      "          configMap:",
      "            name: agent-builder-postgresql-init",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-postgresql",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: postgresql",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 5432",
      "      targetPort: 5432",
      "      name: postgresql",
      "  selector:",
      "    app.kubernetes.io/name: postgresql",
      "  type: ClusterIP",
      "EOF",

      "echo 'Waiting for PostgreSQL to be ready...'",
      "for i in $(seq 1 60); do",
      "  oc get pod -n ${var.namespace} -l app.kubernetes.io/name=postgresql 2>/dev/null | grep -q Running && break",
      "  sleep 10",
      "done",
      "echo 'PostgreSQL deployment complete'",
    ]
  }

  depends_on = [null_resource.postgresql_init_script]
}

output "service_name" {
  value = "agent-builder-postgresql"
}

output "port" {
  value = 5432
}
