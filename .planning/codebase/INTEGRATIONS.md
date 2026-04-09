# External Integrations

**Analysis Date:** 2026-04-07

## APIs & External Services

**LLM Providers:**
- Anthropic Claude - Primary LLM for briefings, evaluations, journal windows, advisor conversations
  - SDK/Client: `anthropic>=0.84.0` (halos), `anthropic>=0.39.0` (Hermes), also raw `httpx` calls to `https://api.anthropic.com/v1/messages`
  - Auth: `ANTHROPIC_API_KEY` env var (read from `.env` or environment)
  - Model config: `briefings.yaml` specifies `claude-sonnet-4-20250514`; watchctl uses configurable model
  - Used in: `halos/briefings/synthesise.py`, `halos/watchctl/evaluate.py`, `halos/journalctl/window.py` (via `claude` CLI subprocess)

- Groq - Fast/cheap LLM for watchctl evaluation (fallback)
  - SDK/Client: Raw `httpx` calls to Groq API
  - Auth: `GROQ_API_KEY` env var
  - Model: `llama-3.3-70b` (per CLAUDE.md)
  - Used in: `halos/watchctl/evaluate.py` (fallback when no Anthropic key)

- OpenAI-compatible - Via Hermes upstream
  - SDK/Client: `openai>=2.21.0` (in Hermes)
  - Auth: configured per-provider in Hermes

- Claude CLI - Zero-config fallback for LLM calls when no API key is set
  - Used in: `halos/watchctl/evaluate.py`, `halos/journalctl/window.py` (subprocess call to `claude` binary)

**Messaging:**
- Telegram Bot API - Primary user interface for all advisor interactions and briefing delivery
  - SDK/Client: `python-telegram-bot>=22.6` (Hermes), direct `httpx` to `https://api.telegram.org/bot{token}/sendMessage` (halos briefings/watchctl)
  - Auth: `TELEGRAM_BOT_TOKEN` env var (per-advisor in fleet), `HERMES_BOT_TOKEN` (briefings)
  - Config: `TELEGRAM_ALLOWED_USERS` (access control), `TELEGRAM_CHAT_ID` (delivery target)
  - Used in: `halos/briefings/deliver.py`, `halos/watchctl/digest.py`, Hermes gateway

**Web Search & Scraping (Hermes tools):**
- Exa Search - Web search
  - SDK/Client: `exa-py>=2.9.0`
  - Used in: Hermes agent tools

- Firecrawl - Web scraping
  - SDK/Client: `firecrawl-py>=4.16.0`
  - Used in: Hermes agent tools

- Parallel Web - Parallel web fetching
  - SDK/Client: `parallel-web>=0.4.2`
  - Used in: Hermes agent tools

**Media:**
- fal.ai - Image generation
  - SDK/Client: `fal-client>=0.13.1`
  - Used in: Hermes agent tools

- Edge TTS - Text-to-speech (free, no API key)
  - SDK/Client: `edge-tts>=7.2.7`
  - Used in: Hermes agent tools

**YouTube:**
- YouTube Transcript API - Transcript extraction for watchctl
  - SDK/Client: `youtube-transcript-api>=1.2.4`
  - Auth: Cookie-based authentication
  - Used in: `halos/watchctl/transcript.py`

- YouTube RSS Feeds - Channel monitoring
  - SDK/Client: `feedparser>=6.0`, `httpx`
  - Used in: `halos/watchctl/feed.py`

## Data Storage

**Databases:**
- SQLite (local) - All persistent state
  - Connection: File-based, WAL mode enforced at container startup
  - Client: Python `sqlite3` stdlib
  - Locations: `store/*.db` (see STACK.md for full list)
  - In K8s: mounted via NFS shared volume and per-advisor PVC subpaths

**File Storage:**
- Local filesystem + NFS (K8s)
  - Advisor state: NFS mount at `10.100.54.223:/` shared across pods
  - Memory system: NFS-backed PVC (`infra/k8s/fleet/memory-pvc.yaml`)
  - Obsidian vault: `~/Documents/vault/main` (watchctl output target, local only)

**Caching:**
- Content-hash file cache for journal LLM windows (`store/journal-cache/`)
- No external cache service (Redis, Memcached, etc.)

## Event Streaming

**NATS JetStream:**
- Purpose: Inter-advisor event bus ("Halostream") for the K8s fleet
- Server: `nats:2.10-alpine` deployed in-cluster (`infra/k8s/fleet/nats.yaml`)
- URL: `nats://nats.halo-fleet.svc.cluster.local:4222`
- Auth: Username/password (`nats-auth` K8s Secret, users: `hq`, `advisor`)
- Stream: `HALO` (initialized via `infra/k8s/fleet/nats-init-stream.yaml`)
- Subjects: `halo.>` wildcard subscription; specific: `halo.advisor.inbound.received`, `halo.advisor.outbound.sent`
- SDK/Client: `nats-py>=2.9.0` (halos `[eventsource]` extra)
- Publisher: Gateway NATS hook (generated in `docker/entrypoint.sh`)
- Consumer: `halos/eventsource/run_consumer.py` — maintains SQLite projections
- Projection handlers: `halos/eventsource/handlers/` (track, journal, night, observation)
- Aura relay: `halos/eventsource/aura_relay.py` — tails Hermes JSONL, publishes to NATS
- Storage: 40Gi Vultr Block Storage HDD PVC

## Authentication & Identity

**Secrets Management:**
- 1Password SDK - Runtime secret resolution
  - SDK/Client: `onepassword-sdk>=0.4.0`
  - Implementation: `halos/secretctl/` (CLI + daemon with Unix socket)
  - Auth: Desktop biometric (`DesktopAuth` from onepassword SDK)
  - Features: Daemon mode with TTL auto-shutdown, `op://` URI resolution
  - Used in: `halos/secretctl/client.py`, `halos/secretctl/daemon.py`

**Telegram Access Control:**
- `TELEGRAM_ALLOWED_USERS` env var - Whitelist of allowed Telegram user IDs
- Configured per-advisor in K8s Secrets

**K8s Secrets:**
- Per-advisor: `*-secrets.yaml` containing `.env` with `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`
- NATS auth: `nats-auth` Secret with `HQ_PASS`, `ADVISOR_PASS`
- Container registry: `vultr-cr` imagePullSecret

## Email

**Gmail (via himalaya):**
- Engine: himalaya CLI binary (external, not a Python package)
- Config: `~/.config/himalaya/config.toml`
- Accounts: gmail, icloud (`halos/mailctl/engine.py` `ACCOUNTS` tuple)
- Implementation: subprocess wrapper in `halos/mailctl/engine.py`
- Features: list, read, search, send, triage rules, filter audit
- Triage: Rule-based in `halos/mailctl/triage.py` (VIP/noise, labels: jobs, infra, newsletters, commerce, noise)
- Store: `store/mail.db`

## Monitoring & Observability

**Health Checks:**
- Heartbeat file: `$HERMES_HOME/heartbeat` touched every 30s by background loop in `docker/entrypoint.sh`
- K8s startup probe: checks heartbeat file exists (30 retries, 10s apart)
- K8s liveness probe: checks heartbeat file < 120s stale (60s period)
- NATS: HTTP health at port 8222 `/healthz`

**Logging:**
- `halos/common/log.py` (`hlog`) - Structured logging across all halos modules
- `halos/logctl/` - Log reader and search CLI
- `halos/agentctl/` - LLM session tracking and spin detection

**Error Tracking:**
- None (no Sentry, Datadog, etc.)

**Telemetry:**
- `halos/telemetry/` - Internal telemetry emission
- `agent/listen/session_telemetry.py` - Agent session telemetry

## CI/CD & Deployment

**Container Registry:**
- Vultr Container Registry: `lhr.vultrcr.com/jeany/`
- Images: `halo:fleet-latest`, `halo-halos:latest`

**GitOps:**
- Argo CD - Syncs from `infra/k8s/fleet/` to `halo-fleet` namespace
- App definition: `infra/k8s/fleet/argocd-app.yaml`

**In-Cluster Builds:**
- Kaniko: `infra/k8s/fleet/kaniko-build.yaml`

**CI Pipeline:**
- Not detected (no `.github/workflows/`, no `.gitlab-ci.yml`, no Jenkinsfile)

**Backup:**
- S3-compatible: Optional restore from `BACKUP_S3_BUCKET` on empty PVC (`docker/entrypoint.sh`)
- `halos/backupctl/` - Structured backup policy management CLI

## Environment Configuration

**Required env vars (fleet advisors):**
- `TELEGRAM_BOT_TOKEN` - Per-advisor Telegram bot token
- `ANTHROPIC_API_KEY` - LLM API access
- `TELEGRAM_ALLOWED_USERS` - Access control whitelist
- `ADVISOR_NAME` - Advisor identifier (e.g., "musashi")
- `NATS_PASS` - NATS authentication password

**Optional env vars:**
- `COST_CEILING_USD` - Spending limit for LLM calls
- `DEFAULT_MODEL` - LLM model override
- `DEFAULT_PROVIDER` - LLM provider override
- `GROQ_API_KEY` - Groq LLM fallback (watchctl)
- `HERMES_BOT_TOKEN` - Separate bot token for briefings delivery
- `ADVISOR_TOUCHBASE_SCHEDULE` - Cron schedule for advisor touchbase
- `ADVISOR_TOUCHBASE_CHAT_ID` - Target chat for touchbase delivery
- `ENABLE_NATS_GATEWAY_HOOK` - Enable/disable NATS event publishing (default: 1)
- `NATS_URL` - NATS server URL (default: `nats://nats.halo-fleet.svc.cluster.local:4222`)
- `NATS_USER` - NATS auth user (default: "advisor")
- `HALO_STORE_DIR` - Override store directory path
- `HERMES_HOME` - Data directory (default: `/opt/data`)
- `BACKUP_S3_BUCKET` - S3 bucket for PVC restore on empty state
- `INSTALL_BROWSER` - Docker build arg to install Playwright/Chromium (default: false)

**Secrets location:**
- Local: `.env` file at project root (gitignored)
- K8s: Kubernetes Secrets mounted as files (per-advisor `*-secrets.yaml`)
- Runtime: 1Password SDK via `secretctl` daemon

## Webhooks & Callbacks

**Incoming:**
- Agent listener: HTTP server on `:7600` (`agent/listen/main.py`) - Accepts job requests, spawns Claude Code instances in tmux sessions

**Outgoing:**
- Telegram Bot API: Message delivery (briefings, watchctl digests, advisor touchbase)
- NATS JetStream: Event publishing from gateway hooks (advisor inbound/outbound messages)

## Cron & Scheduled Tasks

**Local (via cronctl):**
- `cronctl install --execute` - Generates and installs system crontab
- Config: `cronctl.yaml`

**K8s Fleet:**
- Per-advisor CronJobs: `infra/k8s/fleet/cronjobs/advisor-*-cronjob.yaml`
- 8 advisors with scheduled touchbase (Musashi 07:00, Karpathy 09:00, Medici 19:45, Machiavelli 20:15, Draper 20:00, Gibson 20:30, Bankei unscheduled, Hightower on-demand)
- Managed via Kustomize: `infra/k8s/fleet/cronjobs/kustomization.yaml`

**In-container:**
- Hermes cron system: Jobs created/managed via `cron.jobs` module in entrypoint
- Touchbase cron bootstrap: Auto-created from `ADVISOR_TOUCHBASE_SCHEDULE` env var

---

*Integration audit: 2026-04-07*
