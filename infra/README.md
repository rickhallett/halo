---
title: "Infrastructure Directory Map"
category: reference
status: active
created: 2026-04-06
---

# Infrastructure

All infrastructure code for the Halo ecosystem. Target: VKE (Vultr Kubernetes Engine), single-node cluster.

## Directory Layout

```
infra/
├── k8s/
│   ├── fleet/              ← Argo CD tracked (source of truth for halo-fleet namespace)
│   │   ├── namespace.yaml          Namespace definition (PodSecurity: baseline)
│   │   ├── argocd-app.yaml         Argo CD Application CR (self-excluded from sync)
│   │   ├── README.md               Fleet deployment runbook (gotchas, procedures)
│   │   │
│   │   ├── *-deployment.yaml       Advisor pod deployments (7 advisors)
│   │   ├── *-config.yaml           Advisor ConfigMaps (config.yaml)
│   │   ├── *-prompt.yaml           Advisor ConfigMaps (system-prompt.md)
│   │   ├── *-secrets.yaml          Advisor Secrets (gitignored — tokens, API keys)
│   │   ├── *-secrets.yaml.example  Secret templates (committed)
│   │   │
│   │   ├── memctl-authority.yaml        Memory governance pod (single writer)
│   │   ├── memctl-authority-config.yaml ConfigMap for authority (memory_dir: /memory)
│   │   ├── memctl-reader-config.yaml    ConfigMap for advisors (read-only memctl)
│   │   ├── memory-pvc.yaml             PVC for NFS-backed memory corpus (in halo-infra)
│   │   ├── nfs-server.yaml             NFS server + Service (in halo-infra)
│   │   │
│   │   ├── nats.yaml               NATS server deployment + service
│   │   ├── nats-config.yaml        NATS server configuration
│   │   ├── nats-secrets.yaml       NATS auth credentials (gitignored)
│   │   ├── nats-secrets.yaml.example
│   │   ├── nats-init-stream.yaml   Job: creates HALO JetStream stream on startup
│   │   │
│   │   ├── musashi-secrets.yaml.example  Template for advisor secrets
│   │   └── kaniko-build.yaml       Kaniko in-cluster build (unused — blocked by PodSecurity)
│   │
│   ├── archived-fleet/     ← Replaced advisor manifests (Socrates → Karpathy, etc.)
│   ├── base/               ← Kustomize base (legacy, pre-fleet)
│   ├── aura/               ← Aura relay patch
│   └── monitoring/         ← Helm values for Prometheus, Loki, Promtail (not yet deployed)
│
├── terraform/              ← VKE cluster provisioning (Vultr provider)
│   ├── main.tf             Cluster, node pool, firewall
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
│
└── gemini-bridge/          ← Experimental Gemini CLI ↔ Telegram bridge (local only)
    ├── bridge.py           Polling bridge (150 LOC)
    ├── GEMINI.md           Chango persona
    ├── pyproject.toml
    └── .gemini/settings.json  API key auth (no keyring)
```

## Namespaces

| Namespace | PodSecurity | What's in it |
|-----------|------------|-------------|
| `halo-fleet` | baseline | 7 advisor pods, memctl-authority, NATS, init jobs |
| `halo-infra` | privileged | NFS server (requires privileged container) |
| `argocd` | (default) | Argo CD (7 pods — server, repo-server, controller, redis, dex, notifications, applicationset) |

## Argo CD

Argo CD tracks `infra/k8s/fleet/` on `feat/containerisation` branch. Self-heal enabled, auto-prune enabled.

- **UI:** `kubectl port-forward svc/argocd-server -n argocd 8080:443` → `https://localhost:8080`
- **Credentials:** admin / (stored in `argocd-initial-admin-secret`)
- **Excluded from sync:** `*-secrets.yaml`, `*-secrets.yaml.example`, `kaniko-build.yaml`, `argocd-app.yaml`, `README.md`

## Shared Storage

### Memory Corpus (NFS)

Single-writer architecture. `memctl-authority` pod writes to NFS. All advisors mount read-only.

```
NFS Server (halo-infra)
  └── PVC: halo-memory (40Gi, vultr-block-storage-hdd-retain)
       └── /exports/ (chown 1000:1000)
            ├── INDEX.md (88KB)
            ├── notes/ (157 .md files)
            └── reflections/ (13 .md files)

Mounted in all advisor pods at /memory (read-only, NFS ClusterIP: 10.100.54.223)
Mounted in memctl-authority at /memory (read-write)
```

**Gotcha:** Kubelet mounts NFS from the host network. ClusterIP must be hardcoded in volume specs — `.svc.cluster.local` DNS doesn't resolve from the host. See `docs/d2/k8s-fleet-lessons-learned.md` for details.

### NATS JetStream (Halostream)

Event bus connecting all advisors. Stream: `HALO`, subjects: `halo.>`.

Each advisor pod runs an event consumer sidecar (`halos.eventsource.run_consumer`) that projects events into a local `projection.db` (SQLite).

## Per-Advisor Manifest Pattern

Each advisor has 3-4 manifests:

| File | Content | Secret? |
|------|---------|---------|
| `<name>-deployment.yaml` | Pod spec, env, volumes, probes | No |
| `<name>-config.yaml` | ConfigMap: `config.yaml` (model, modules, domains) | No |
| `<name>-prompt.yaml` | ConfigMap: `system-prompt.md` (persona) | No |
| `<name>-secrets.yaml` | Secret: `.env` (bot token, API key, allowed users) | **Yes — gitignored** |

### Adding a New Advisor

See `infra/k8s/fleet/README.md` for the full procedure. Summary:

1. Create bot via @BotFather
2. Copy manifests from an existing advisor
3. Update: `ADVISOR_NAME`, bot token, persona, ConfigMap names, trackctl domains
4. `kubectl apply` the secret (not in git), then push the rest for Argo to sync

## Terraform

VKE cluster provisioning. Single node pool (`vc2-2c-4gb`), London region.

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

KUBECONFIG at `~/.kube/vultr-halo.yaml`.

## Lessons Learned

See `docs/d2/k8s-fleet-lessons-learned.md` — 16 hard-won items covering NFS, PodSecurity, Argo CD, and Vultr-specific gotchas.
