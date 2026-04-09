# ──────────────────────────────────────────────────────────────
# Halo Infrastructure — Vultr Kubernetes Engine
#
# Dedicated VKE cluster for Halo multi-tenant deployment.
# Each client gets a namespace; shared node pool.
#
# Phase 1: Single node, single client (Aura).
# Phase 2: Auto-scaler when client count > 3.
# ──────────────────────────────────────────────────────────────

resource "vultr_kubernetes" "halo" {
  region          = var.region
  label           = "halo"
  version         = var.k8s_version
  enable_firewall = true

  node_pools {
    label         = "halo-workers"
    plan          = var.node_plan
    node_quantity = var.node_count
    auto_scaler   = false  # Phase 1: fixed size
  }
}
