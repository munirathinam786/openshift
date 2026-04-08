# =============================================================================
# Module: NVIDIA NIM — NVIDIA Inference Microservices
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "nim_namespace" {
  description = "Namespace for NIM deployment"
  type        = string
  default     = "nvidia-nim"
}
variable "nim_model" {
  description = "NIM model to deploy (e.g., meta/llama3-8b-instruct)"
  type        = string
  default     = "meta/llama3-8b-instruct"
}
variable "nim_gpu_count" {
  description = "Number of GPUs for NIM container"
  type        = number
  default     = 1
}
variable "nim_replicas" {
  description = "Number of NIM replicas"
  type        = number
  default     = 1
}
variable "ngc_api_key" {
  description = "NVIDIA NGC API key for pulling NIM images"
  type        = string
  sensitive   = true
  default     = ""
}
variable "nim_storage_class" {
  description = "StorageClass for model cache"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}
variable "nim_cache_size" {
  description = "PVC size for model cache"
  type        = string
  default     = "100Gi"
}

resource "null_resource" "nvidia_nim" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace ${var.nim_namespace} --dry-run=client -o yaml | oc apply -f -",

      # Create NGC pull secret
      "oc create secret docker-registry ngc-secret -n ${var.nim_namespace} --docker-server=nvcr.io --docker-username='\\$oauthtoken' --docker-password='${var.ngc_api_key}' --dry-run=client -o yaml | oc apply -f -",

      # Create NGC API key secret
      "oc create secret generic ngc-api-secret -n ${var.nim_namespace} --from-literal=NGC_API_KEY='${var.ngc_api_key}' --dry-run=client -o yaml | oc apply -f -",

      # Create model cache PVC
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: PersistentVolumeClaim",
      "metadata:",
      "  name: nim-model-cache",
      "  namespace: ${var.nim_namespace}",
      "spec:",
      "  accessModes:",
      "    - ReadWriteOnce",
      "  storageClassName: ${var.nim_storage_class}",
      "  resources:",
      "    requests:",
      "      storage: ${var.nim_cache_size}",
      "EOF",

      # Deploy NIM
      "NIM_IMAGE_NAME=$(echo '${var.nim_model}' | tr '/' '-')",

      "cat <<EOF | oc apply -f -",
      "apiVersion: apps/v1",
      "kind: Deployment",
      "metadata:",
      "  name: nim-$NIM_IMAGE_NAME",
      "  namespace: ${var.nim_namespace}",
      "spec:",
      "  replicas: ${var.nim_replicas}",
      "  selector:",
      "    matchLabels:",
      "      app: nim-$NIM_IMAGE_NAME",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app: nim-$NIM_IMAGE_NAME",
      "    spec:",
      "      imagePullSecrets:",
      "        - name: ngc-secret",
      "      containers:",
      "        - name: nim",
      "          image: nvcr.io/nim/${var.nim_model}:latest",
      "          ports:",
      "            - containerPort: 8000",
      "              name: http",
      "          env:",
      "            - name: NGC_API_KEY",
      "              valueFrom:",
      "                secretKeyRef:",
      "                  name: ngc-api-secret",
      "                  key: NGC_API_KEY",
      "            - name: NIM_CACHE_PATH",
      "              value: /opt/nim/cache",
      "          volumeMounts:",
      "            - name: model-cache",
      "              mountPath: /opt/nim/cache",
      "          resources:",
      "            limits:",
      "              nvidia.com/gpu: '${var.nim_gpu_count}'",
      "              memory: 32Gi",
      "            requests:",
      "              cpu: '4'",
      "              memory: 16Gi",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /v1/health/ready",
      "              port: 8000",
      "            initialDelaySeconds: 120",
      "            periodSeconds: 10",
      "          livenessProbe:",
      "            httpGet:",
      "              path: /v1/health/live",
      "              port: 8000",
      "            initialDelaySeconds: 120",
      "            periodSeconds: 15",
      "      volumes:",
      "        - name: model-cache",
      "          persistentVolumeClaim:",
      "            claimName: nim-model-cache",
      "      tolerations:",
      "        - key: nvidia.com/gpu",
      "          operator: Exists",
      "          effect: NoSchedule",
      "      nodeSelector:",
      "        nvidia.com/gpu.present: 'true'",
      "EOF",

      # Create Service and Route
      "cat <<EOF | oc apply -f -",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: nim-$NIM_IMAGE_NAME",
      "  namespace: ${var.nim_namespace}",
      "spec:",
      "  selector:",
      "    app: nim-$NIM_IMAGE_NAME",
      "  ports:",
      "    - name: http",
      "      port: 8000",
      "      targetPort: 8000",
      "EOF",

      "oc create route edge nim-$NIM_IMAGE_NAME -n ${var.nim_namespace} --service=nim-$NIM_IMAGE_NAME --port=http 2>/dev/null || true",

      "echo 'NVIDIA NIM deployed for model ${var.nim_model}'",
    ]
  }
}
