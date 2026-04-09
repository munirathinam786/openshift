# Author: Sathishkumar Munirathinam
# Module: Redis — StatefulSet for caching layer

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "redis_password" { type = string; sensitive = true }
variable "redis_storage_size" { type = string; default = "10Gi" }
variable "redis_storage_class" { type = string }

resource "null_resource" "redis_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-redis-credentials -n ${var.namespace} \\",
      "  --from-literal=REDIS_PASSWORD='${var.redis_password}' \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "redis" {
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
      "  name: agent-builder-redis-data",
      "  namespace: ${var.namespace}",
      "spec:",
      "  accessModes:",
      "    - ReadWriteOnce",
      "  storageClassName: ${var.redis_storage_class}",
      "  resources:",
      "    requests:",
      "      storage: ${var.redis_storage_size}",
      "---",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: agent-builder-redis-config",
      "  namespace: ${var.namespace}",
      "data:",
      "  redis.conf: |",
      "    maxmemory 2gb",
      "    maxmemory-policy allkeys-lru",
      "    appendonly yes",
      "    appendfsync everysec",
      "    requirepass REDIS_PASSWORD_PLACEHOLDER",
      "---",
      "apiVersion: apps/v1",
      "kind: StatefulSet",
      "metadata:",
      "  name: agent-builder-redis",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: redis",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  serviceName: agent-builder-redis",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: redis",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: redis",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: redis",
      "          image: registry.redhat.io/rhel9/redis-7:latest",
      "          ports:",
      "            - containerPort: 6379",
      "              name: redis",
      "          env:",
      "            - name: REDIS_PASSWORD",
      "              valueFrom:",
      "                secretKeyRef:",
      "                  name: agent-builder-redis-credentials",
      "                  key: REDIS_PASSWORD",
      "          command:",
      "            - redis-server",
      "            - --requirepass",
      "            - $(REDIS_PASSWORD)",
      "            - --maxmemory",
      "            - 2gb",
      "            - --maxmemory-policy",
      "            - allkeys-lru",
      "            - --appendonly",
      "            - 'yes'",
      "          resources:",
      "            requests:",
      "              cpu: 250m",
      "              memory: 512Mi",
      "            limits:",
      "              cpu: '1'",
      "              memory: 3Gi",
      "          volumeMounts:",
      "            - name: data",
      "              mountPath: /var/lib/redis/data",
      "          livenessProbe:",
      "            exec:",
      "              command:",
      "                - redis-cli",
      "                - -a",
      "                - $(REDIS_PASSWORD)",
      "                - ping",
      "            initialDelaySeconds: 15",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            exec:",
      "              command:",
      "                - redis-cli",
      "                - -a",
      "                - $(REDIS_PASSWORD)",
      "                - ping",
      "            initialDelaySeconds: 5",
      "            periodSeconds: 10",
      "      volumes:",
      "        - name: data",
      "          persistentVolumeClaim:",
      "            claimName: agent-builder-redis-data",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-redis",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: redis",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 6379",
      "      targetPort: 6379",
      "      name: redis",
      "  selector:",
      "    app.kubernetes.io/name: redis",
      "  type: ClusterIP",
      "EOF",

      "echo 'Waiting for Redis to be ready...'",
      "for i in $(seq 1 30); do",
      "  oc get pod -n ${var.namespace} -l app.kubernetes.io/name=redis 2>/dev/null | grep -q Running && break",
      "  sleep 10",
      "done",
      "echo 'Redis deployment complete'",
    ]
  }

  depends_on = [null_resource.redis_secret]
}

output "service_name" {
  value = "agent-builder-redis"
}

output "port" {
  value = 6379
}
