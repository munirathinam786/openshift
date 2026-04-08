# =============================================================================
# Module: Model Registry — ML Model versioning and serving registry
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "model_registry_namespace" {
  description = "Namespace for Model Registry"
  type        = string
  default     = "model-registry"
}
variable "model_registry_storage_class" {
  description = "StorageClass for Model Registry database"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}
variable "model_registry_storage_size" {
  description = "PVC size for Model Registry database"
  type        = string
  default     = "20Gi"
}

resource "null_resource" "model_registry" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace ${var.model_registry_namespace} --dry-run=client -o yaml | oc apply -f -",

      # Deploy PostgreSQL for metadata storage
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: PersistentVolumeClaim",
      "metadata:",
      "  name: model-registry-db",
      "  namespace: ${var.model_registry_namespace}",
      "spec:",
      "  accessModes:",
      "    - ReadWriteOnce",
      "  storageClassName: ${var.model_registry_storage_class}",
      "  resources:",
      "    requests:",
      "      storage: ${var.model_registry_storage_size}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: apps/v1",
      "kind: Deployment",
      "metadata:",
      "  name: model-registry-db",
      "  namespace: ${var.model_registry_namespace}",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app: model-registry-db",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app: model-registry-db",
      "    spec:",
      "      containers:",
      "        - name: postgres",
      "          image: registry.redhat.io/rhel8/postgresql-15:latest",
      "          ports:",
      "            - containerPort: 5432",
      "          env:",
      "            - name: POSTGRESQL_USER",
      "              value: mlmd",
      "            - name: POSTGRESQL_PASSWORD",
      "              valueFrom:",
      "                secretKeyRef:",
      "                  name: model-registry-db-credentials",
      "                  key: password",
      "            - name: POSTGRESQL_DATABASE",
      "              value: model_registry",
      "          volumeMounts:",
      "            - name: db-data",
      "              mountPath: /var/lib/pgsql/data",
      "          resources:",
      "            limits:",
      "              cpu: '1'",
      "              memory: 1Gi",
      "            requests:",
      "              cpu: 250m",
      "              memory: 256Mi",
      "      volumes:",
      "        - name: db-data",
      "          persistentVolumeClaim:",
      "            claimName: model-registry-db",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: model-registry-db",
      "  namespace: ${var.model_registry_namespace}",
      "spec:",
      "  selector:",
      "    app: model-registry-db",
      "  ports:",
      "    - port: 5432",
      "      targetPort: 5432",
      "EOF",

      # Deploy Model Registry server
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: apps/v1",
      "kind: Deployment",
      "metadata:",
      "  name: model-registry",
      "  namespace: ${var.model_registry_namespace}",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app: model-registry",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app: model-registry",
      "    spec:",
      "      containers:",
      "        - name: model-registry",
      "          image: quay.io/opendatahub/model-registry:latest",
      "          ports:",
      "            - containerPort: 8080",
      "              name: http-api",
      "            - containerPort: 9090",
      "              name: grpc-api",
      "          env:",
      "            - name: MR_DB_HOST",
      "              value: model-registry-db",
      "            - name: MR_DB_PORT",
      "              value: '5432'",
      "            - name: MR_DB_USER",
      "              value: mlmd",
      "            - name: MR_DB_PASSWORD",
      "              valueFrom:",
      "                secretKeyRef:",
      "                  name: model-registry-db-credentials",
      "                  key: password",
      "            - name: MR_DB_NAME",
      "              value: model_registry",
      "          resources:",
      "            limits:",
      "              cpu: '1'",
      "              memory: 1Gi",
      "            requests:",
      "              cpu: 250m",
      "              memory: 256Mi",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: model-registry",
      "  namespace: ${var.model_registry_namespace}",
      "spec:",
      "  selector:",
      "    app: model-registry",
      "  ports:",
      "    - name: http-api",
      "      port: 8080",
      "      targetPort: 8080",
      "    - name: grpc-api",
      "      port: 9090",
      "      targetPort: 9090",
      "EOF",

      "oc expose service model-registry -n ${var.model_registry_namespace} --port=http-api --name=model-registry 2>/dev/null || true",

      "echo 'Model Registry deployed'",
    ]
  }
}
