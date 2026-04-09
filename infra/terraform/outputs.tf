output "cluster_id" {
  description = "VKE cluster ID"
  value       = vultr_kubernetes.halo.id
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint"
  value       = vultr_kubernetes.halo.endpoint
}

output "cluster_status" {
  description = "Cluster status"
  value       = vultr_kubernetes.halo.status
}

output "kubeconfig_command" {
  description = "Command to fetch kubeconfig"
  value       = "vultr-cli kubernetes config ${vultr_kubernetes.halo.id} | base64 -d > ~/.kube/vultr-halo.yaml"
}
