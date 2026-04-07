# Technology Stack

**Analysis Date:** 2026-04-07

## Languages

**Primary:**
- Python 3.11+ - All halos tooling (`halos/`), fleet containers, cron jobs, briefings, CLI tools
- Bash - Container entrypoint (`docker/entrypoint.sh`), cron scripts, justfiles

**Secondary:**
- JavaScript/Node.js - Hermes agent gateway (`vendor/hermes-agent/gateway/`), npm-based tooling in container
- YAML - K8s manifests (`infra/k8s/fleet/`), module configs (`*.yaml` at project root)

## Runtime

**Environment:**
- Python >=3.11 (specified in `pyproject.toml`; system Python on macOS is 3.9.6 — use uv-managed venv)
- Node.js v24.14.1 (Hermes gateway runtime in container)
- Debian 13.4 (container base image in `Dockerfile`)

**Package Manager:**
- uv 0.10.12 - Python dependency management (exclusive; pip is banned by standing orders)
- npm 11.11.0 - Node.js deps for Hermes gateway (container only)
- Lockfile: `uv.lock` present at root; `agent/listen/uv.lock` for agent spawner

**Build System:**
- hatchling - Python build backend (`pyproject.toml` `[build-system]`)
- setuptools - Hermes agent build backend (`vendor/hermes-agent/pyproject.toml`)

## Frameworks

**Core:**
- Hermes Agent 0.7.0 (`vendor/hermes-agent/`) - Upstream AI agent framework (Nous Research fork), git submodule. Provides Telegram bot, gateway, skills, cron infrastructure
- halos 0.1.0 (`halos/`) - Custom Python package of 20+ CLI tools (memctl, nightctl, trackctl, etc.)

**Testing:**
- pytest >=9.0.2 - Test runner (`pyproject.toml` dev dependency)
- pytest-cov >=5.0 - Coverage (optional dev dep)
- Test tiers: smoke, fleet, tier1-tier5, chaos, telegram markers (`pyproject.toml [tool.pytest.ini_options]`)

**Build/Dev:**
- Docker - Container builds (`Dockerfile`)
- just - Task runner (`agent/justfile`)
- Argo CD - GitOps deployment (`infra/k8s/fleet/argocd-app.yaml`)
- Kaniko - In-cluster container builds (`infra/k8s/fleet/kaniko-build.yaml`)

## Key Dependencies

**Critical (halos):**
- `anthropic>=0.84.0` - LLM API client for briefings, evaluations, journal windows
- `httpx>=0.27.0` - HTTP client for Telegram Bot API, Anthropic API, Groq API
- `onepassword-sdk>=0.4.0` - 1Password secret management (`halos/secretctl/`)
- `rich>=14.3.3` - Terminal UI rendering (dashctl, CLI output)
- `pyyaml>=6.0` - Config file parsing (all `*.yaml` configs)
- `jinja2>=3.0` - Template rendering
- `feedparser>=6.0` - RSS feed parsing (watchctl YouTube monitor)
- `youtube-transcript-api>=1.2.4` - YouTube transcript extraction (watchctl)
- `playwright>=1.58.0` - Browser automation (optional, disabled by default in container)
- `requests>=2.32.5` - HTTP client (legacy usage in watchctl transcript, halctl supervisor)

**Critical (Hermes — installed in container):**
- `anthropic>=0.39.0,<1` - LLM provider
- `openai>=2.21.0,<3` - LLM provider (OpenAI-compatible)
- `python-telegram-bot>=22.6,<23` - Telegram messaging (via `[messaging]` extra)
- `pydantic>=2.12.5,<3` - Data validation
- `tenacity>=9.1.4,<10` - Retry logic
- `exa-py>=2.9.0,<3` - Web search tool
- `firecrawl-py>=4.16.0,<5` - Web scraping tool
- `fal-client>=0.13.1,<1` - Image generation
- `edge-tts>=7.2.7,<8` - Text-to-speech
- `croniter>=6.0.0,<7` - Cron schedule parsing (via `[cron]` extra)

**Optional (halos extras):**
- `nats-py>=2.9.0` - NATS JetStream client (`[eventsource]` extra)
- `python-ulid>=3.0.0` - ULID generation for events (`[eventsource]` extra)
- `networkx>=3.0` / `pyvis>=0.3.2` - Graph visualization (`[graph]` extra)

**Infrastructure:**
- `ripgrep` - Installed in container for skill search
- `ffmpeg` - Installed in container for media processing

## Configuration

**Module Configs (project root YAML):**
- `memctl.yaml` - Memory governance rules
- `nightctl.yaml` - Work item management config
- `briefings.yaml` - Daily briefing config (model, chat_id, db_path, IPC settings)
- `watchctl.yaml` - YouTube channel monitor (channels list, LLM config, Obsidian vault path)
- `cronctl.yaml` - Cron job definitions
- `logctl.yaml` - Log reader config
- `agentctl.yaml` - Agent session tracking
- `reportctl.yaml` - Periodic digest config
- `todoctl.yaml` - Legacy todo config

**Environment:**
- `.env` - Primary secrets file (exists, never read by tooling analysis)
- `.env.example` - Template: `TELEGRAM_BOT_TOKEN=`
- `.env.halo-dev` - Dev environment config (exists)

**Container Config:**
- `docker/entrypoint.sh` - Generates `.env` from environment vars, bootstraps directories, WAL mode, skill sync, heartbeat wrapper, NATS consumer
- `docker/defaults/` - Default config.yaml and SOUL.md for fresh containers

**K8s Config:**
- ConfigMaps: per-advisor `config.yaml` and `system-prompt.md` (`infra/k8s/fleet/*-config.yaml`, `*-prompt.yaml`)
- Secrets: per-advisor `.env` files (`infra/k8s/fleet/*-secrets.yaml`), NATS auth (`nats-secrets.yaml`)

## Data Storage

**SQLite Databases (all in `store/`):**
- `store/messages.db` - Messages, sessions, onboarding, assessments, groups
- `store/mail.db` - Gmail filters, mailctl audit log
- `store/journal.db` - Qualitative journal entries
- `store/watch.db` - YouTube monitor state
- `store/blogctl.db` - Blog content management
- `store/jobs.db` - Background jobs
- `store/nanoclaw.db` - Legacy (nanoclaw era)
- `store/track_*.db` - Per-domain metrics (movement, zazen, study-source, study-neetcode, study-crafters, project)
- `store/journal-cache/` - LLM-synthesised window cache (content-hash keyed)

**WAL Mode:** Enforced at container startup via `docker/entrypoint.sh` for crash resilience.

## Platform Requirements

**Development:**
- macOS (Darwin, Apple Silicon)
- Python 3.11+ via uv-managed venv
- uv for all Python dependency management
- just for agent task running
- himalaya CLI for email operations (external binary, configured at `~/.config/himalaya/config.toml`)
- 1Password SDK for secret management (requires biometric auth via desktop app)

**Production (K8s Fleet):**
- Vultr Kubernetes Engine (VKE)
- Vultr Container Registry (`lhr.vultrcr.com/jeany/`)
- Two container images: `halo:fleet-latest` (full Hermes + halos), `halo-halos:latest` (halos overlay only)
- Vultr Block Storage HDD (PVCs for NATS data: 40Gi)
- NFS server pod for shared advisor state (`infra/k8s/fleet/nfs-server.yaml`)
- Argo CD for GitOps sync from `infra/k8s/fleet/`
- Namespace: `halo-fleet`

## uv Workspace

The project defines a uv workspace (`pyproject.toml [tool.uv.workspace]`) with one member:
- `data/finance/ark-accounting` - Finance/accounting subproject

---

*Stack analysis: 2026-04-07*
