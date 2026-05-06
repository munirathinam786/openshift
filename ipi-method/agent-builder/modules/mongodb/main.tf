# Author: Sathishkumar Munirathinam
# Module: MongoDB — StatefulSet for agent metadata storage

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "mongodb_root_password" { type = string; sensitive = true }
variable "mongodb_storage_size" { type = string; default = "50Gi" }
variable "mongodb_storage_class" { type = string }

resource "null_resource" "mongodb_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-mongodb-credentials -n ${var.namespace} \\",
      "  --from-literal=MONGO_INITDB_ROOT_USERNAME=root \\",
      "  --from-literal=MONGO_INITDB_ROOT_PASSWORD='${var.mongodb_root_password}' \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "mongodb" {
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
      "  name: agent-builder-mongodb-data",
      "  namespace: ${var.namespace}",
      "spec:",
      "  accessModes:",
      "    - ReadWriteOnce",
      "  storageClassName: ${var.mongodb_storage_class}",
      "  resources:",
      "    requests:",
      "      storage: ${var.mongodb_storage_size}",
      "---",
      "apiVersion: apps/v1",
      "kind: StatefulSet",
      "metadata:",
      "  name: agent-builder-mongodb",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: mongodb",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  serviceName: agent-builder-mongodb",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: mongodb",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: mongodb",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      securityContext:",
      "        fsGroup: 184",
      "      containers:",
      "        - name: mongodb",
      "          image: registry.redhat.io/rhel9/mongodb-7:latest",
      "          ports:",
      "            - containerPort: 27017",
      "              name: mongodb",
      "          envFrom:",
      "            - secretRef:",
      "                name: agent-builder-mongodb-credentials",
      "          resources:",
      "            requests:",
      "              cpu: 500m",
      "              memory: 1Gi",
      "            limits:",
      "              cpu: '2'",
      "              memory: 4Gi",
      "          volumeMounts:",
      "            - name: data",
      "              mountPath: /var/lib/mongodb/data",
      "          livenessProbe:",
      "            exec:",
      "              command:",
      "                - /bin/sh",
      "                - -c",
      "                - mongosh --eval 'db.runCommand({ping:1}).ok' --quiet",
      "            initialDelaySeconds: 30",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            exec:",
      "              command:",
      "                - /bin/sh",
      "                - -c",
      "                - mongosh --eval 'db.runCommand({ping:1}).ok' --quiet",
      "            initialDelaySeconds: 5",
      "            periodSeconds: 10",
      "      volumes:",
      "        - name: data",
      "          persistentVolumeClaim:",
      "            claimName: agent-builder-mongodb-data",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-mongodb",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: mongodb",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 27017",
      "      targetPort: 27017",
      "      name: mongodb",
      "  selector:",
      "    app.kubernetes.io/name: mongodb",
      "  type: ClusterIP",
      "EOF",

      "echo 'Waiting for MongoDB to be ready...'",
      "for i in $(seq 1 60); do",
      "  oc get pod -n ${var.namespace} -l app.kubernetes.io/name=mongodb 2>/dev/null | grep -q Running && break",
      "  sleep 10",
      "done",
      "echo 'MongoDB deployment complete'",
    ]
  }

  depends_on = [null_resource.mongodb_secret]
}

output "service_name" {
  value = "agent-builder-mongodb"
}

output "port" {
  value = 27017
}
