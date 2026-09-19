---
title: "Claude Tech Stack Reference"
category: reference
status: active
created: 2026-04-15
---

# Claude Tech Stack Reference

Technology stack, coding conventions, and architecture details.
Read this when working on code — not loaded at boot.

## Technology Stack

### Languages
- Python 3.11+ - All halos tooling (`halos/`), fleet containers, cron jobs, briefings, CLI tools
- Bash - Container entrypoint (`docker/entrypoint.sh`), cron scripts, justfiles
- JavaScript/Node.js - Hermes agent gateway (`vendor/hermes-agent/gateway/`), npm-based tooling in container
- YAML - K8s manifests (`infra/k8s/fleet/`), module configs (`*.yaml` at project root)

### Runtime
- Python >=3.11 (specified in `pyproject.toml`; system Python on macOS is 3.9.6 -- use uv-managed venv)
- Node.js v24.14.1 (Hermes gateway runtime in container)
- Debian 13.4 (container base image in `Dockerfile`)
- uv 0.10.12 - Python dependency management (exclusive; pip is banned by standing orders)
- npm 11.11.0 - Node.js deps for Hermes gateway (container only)
- Lockfile: `uv.lock` present at root; `agent/listen/uv.lock` for agent spawner
- hatchling - Python build backend (`pyproject.toml` `[build-system]`)
- setuptools - Hermes agent build backend (`vendor/hermes-agent/pyproject.toml`)

### Frameworks
- Hermes Agent 0.7.0 (`vendor/hermes-agent/`) - Upstream AI agent framework (Nous Research fork), git submodule. Provides Telegram bot, gateway, skills, cron infrastructure
- halos 0.1.0 (`halos/`) - Custom Python package of 20+ CLI tools (memctl, nightctl, trackctl, etc.)
- pytest >=9.0.2 - Test runner (`pyproject.toml` dev dependency)
- pytest-cov >=5.0 - Coverage (optional dev dep)
- Test tiers: smoke, fleet, tier1-tier5, chaos, telegram markers (`pyproject.toml [tool.pytest.ini_options]`)
- Docker - Container builds (`Dockerfile`)
- just - Task runner (`justfile` at root for deploy, `agent/justfile` for agent spawner)
- Mutagen 0.18.1 - One-way file sync (Mac -> Ryzen) for deploy pipeline
- Deploy pipeline: Mutagen sync -> `just deploy` (build on Ryzen local disk -> push localhost:5000 -> kubectl rollout restart)

### Key Dependencies
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
- `nats-py>=2.9.0` - NATS JetStream client (`[eventsource]` extra)
- `python-ulid>=3.0.0` - ULID generation for events (`[eventsource]` extra)
- `networkx>=3.0` / `pyvis>=0.3.2` - Graph visualization (`[graph]` extra)
- `ripgrep` - Installed in container for skill search
- `ffmpeg` - Installed in container for media processing

### Configuration
- `memctl.yaml` - Memory governance rules
- `nightctl.yaml` - Work item management config
- `briefings.yaml` - Daily briefing config (model, chat_id, db_path, IPC settings)
- `watchctl.yaml` - YouTube channel monitor (channels list, LLM config, Obsidian vault path)
- `cronctl.yaml` - Cron job definitions
- `logctl.yaml` - Log reader config
- `agentctl.yaml` - Agent session tracking
- `reportctl.yaml` - Periodic digest config
- `todoctl.yaml` - Legacy todo config
- `.env` - Primary secrets file (exists, never read by tooling analysis)
- `.env.example` - Template: `TELEGRAM_BOT_TOKEN=`
- `.env.halo-dev` - Dev environment config (exists)
- `docker/entrypoint.sh` - Generates `.env` from environment vars, bootstraps directories, WAL mode, skill sync, heartbeat wrapper, NATS consumer
- `docker/defaults/` - Default config.yaml and SOUL.md for fresh containers
- ConfigMaps: per-advisor `config.yaml` and `system-prompt.md` (`infra/k8s/fleet/*-config.yaml`, `*-prompt.yaml`)
- Secrets: per-advisor `.env` files (`infra/k8s/fleet/*-secrets.yaml`), NATS auth (`nats-secrets.yaml`)

### Data Storage
- `store/messages.db` - Messages, sessions, onboarding, assessments, groups
- `store/mail.db` - Gmail filters, mailctl audit log
- `store/journal.db` - Qualitative journal entries
- `store/watch.db` - YouTube monitor state
- `store/blogctl.db` - Blog content management
- `store/jobs.db` - Background jobs
- `store/nanoclaw.db` - Legacy (nanoclaw era)
- `store/track_*.db` - Per-domain metrics (movement, zazen, study-source, study-neetcode, study-crafters, project)
- `store/journal-cache/` - LLM-synthesised window cache (content-hash keyed)

### Platform Requirements
- macOS (Darwin, Apple Silicon)
- Python 3.11+ via uv-managed venv
- uv for all Python dependency management
- just for agent task running
- himalaya CLI for email operations (external binary, configured at `~/.config/himalaya/config.toml`)
- 1Password SDK for secret management (requires biometric auth via desktop app)
- k3s on Ryzen homelab (ryzen32 via Tailscale) -- all kubectl needs `sudo`
- Local container registry: `localhost:5000` (dev builds)
- Single container image: `localhost:5000/halo:dev`
- Namespace: `halo-fleet`

### uv Workspace
- `data/finance/ark-accounting` - Finance/accounting subproject

## Conventions

### Naming Patterns
- Use `snake_case.py` for all Python source files
- Module directories are `lowercase` single words or compound words: `memctl`, `nightctl`, `trackctl`, `backupctl`
- Each module has a standard file set: `cli.py`, `config.py`, `engine.py` (or domain-specific names like `store.py`, `item.py`, `note.py`)
- Test files follow `test_<module_or_feature>.py` pattern
- Use `snake_case` for all functions and methods
- Private/internal functions prefixed with underscore: `_connect()`, `_find_repo_root()`, `_make_config()`
- CLI entry points are always `main()` in `cli.py`
- Factory/builder functions use descriptive verbs: `add_entry()`, `load_config()`, `create()`, `parse()`
- Use `snake_case` for all variables
- Constants use `UPPER_SNAKE_CASE`: `VALID_KINDS`, `TERMINAL_STATUSES`, `FLEET_NS`
- Type aliases and sentinel values use `UPPER_SNAKE_CASE`
- Use `PascalCase` for all classes: `Item`, `Note`, `BackupConfig`, `CheckResult`
- Exception classes end with `Error`: `ValidationError`, `TransitionError`, `SaveError`, `ContainerError`, `PlanValidationError`
- Dataclass names describe the data they hold: `RetentionPolicy`, `BackupTarget`, `Event`

### Code Style
- No automated formatter configured (no black, ruff format, or autopep8)
- Follow consistent 4-space indentation
- Line length appears to be ~100-120 characters (no enforced limit)
- Use double quotes for strings consistently
- No linter configured. `Makefile` has placeholder: `lint: @echo "lint: no linter configured"`
- No type checker configured. `Makefile` has placeholder: `typecheck: @echo "typecheck: no type checker configured"`
- No pre-commit hooks (`.pre-commit-config.yaml` does not exist)

### Import Organization
- None. All imports use the `halos.` package prefix or relative dots.

### Error Handling
- Define module-specific exceptions inheriting from `Exception` directly
- Include structured data on exception objects for programmatic access

### Function Design
- Return `dict` for data objects from storage layers (SQLite rows)
- Return dataclass instances for domain models
- Return `list[str]` for validation errors
- CLI `main()` functions return `int` exit codes (0 for success, 1 for error)

## Architecture

### Pattern Overview
- **Monorepo with heterogeneous surfaces:** Three runtime contexts (K8s fleet, local agent spawner, cron jobs) share one repository and one Python tooling layer
- **Event sourcing via NATS JetStream:** Advisors publish events to a `HALO` stream; each advisor maintains a local SQLite projection rebuilt from the stream
- **Upstream wrapping, not forking:** The Hermes Telegram bot (`vendor/hermes-agent`) is consumed as a git submodule. All customisation is via config injection, entrypoint hooks, and PYTHONPATH overlays -- never source patches
- **CLI-first tooling:** Every halos module is a standalone CLI (console_scripts) and also importable as a Python library. The `hal` command (`halos/hal.py`) is a unified dispatcher

### Layers
- **Telegram Interface** -- `vendor/hermes-agent`, `docker/entrypoint.sh`, `Dockerfile`. Upstream Hermes bot runtime with config injection, NATS hooks, heartbeat wrapper, WAL enforcement. Depends on halos tooling, NATS, Anthropic API.
- **Agent Spawner** -- `agent/listen/main.py` (FastAPI on :7600), `agent/direct/main.py` (CLI). Job lifecycle management, worker process spawning, session telemetry. Depends on Claude Code CLI.
- **Halos Tooling** -- `halos/` package (20+ modules). Each module follows cli.py + engine/store pattern with YAML/SQLite persistence. Depends on `halos/common/`, SQLite in `store/`, YAML configs.
- **Event Bus** -- `halos/eventsource/` (core, consumer, projection, handlers). NATS JetStream consumer with checkpoint-based replay into SQLite projections.
- **Infrastructure** -- `infra/k8s/fleet/`. Per-advisor Deployment + ConfigMap + Secret + prompt YAML, NATS StatefulSet, local-path PVCs. Manual kubectl apply.
- **Persistence** -- `memory/` (memctl notes), `store/` (SQLite DBs), `backlog/items/` (YAML work items).
- **Configuration** -- Repo root YAML files (`memctl.yaml`, `nightctl.yaml`, etc.). Overridable via env vars.

### Data Flow
- Each halos module owns its own SQLite database in `store/`
- Memory notes are filesystem-based (markdown in `memory/notes/`)
- Fleet state is projected from NATS event stream into per-advisor SQLite DBs
- Agent jobs are YAML files in `agent/listen/jobs/`

### Key Abstractions
- **Event** -- Immutable record with ULID ID, type, version, source, timestamp, correlation_id, payload. Subject: `halo.{event.type}`.
- **Handler** -- Abstract base for event handlers. Declares `handles() -> list[str]` and `apply(event, db)`. Schema init via `init_schema(db)`.
- **Projection** -- Disposable SQLite read model. Delete it, replay from stream, get same state. Stream is truth.
- **Advisor** -- Historical-figure AI persona injected as system prompt via K8s ConfigMap -> entrypoint `HERMES_EPHEMERAL_SYSTEM_PROMPT`.
- **halos Module** -- Self-contained CLI + Python API. argparse/click -> engine/store -> SQLite/filesystem -> `hlog()`.
- **hal Dispatcher** -- `halos/hal.py`. Module registry dict -> `os.execvp` dispatch.

### Entry Points
- `halos/hal.py` -- `hal <module> [args]` dispatcher
- `docker/entrypoint.sh` -- Container start (directory bootstrap, config injection, prompt loading, NATS hooks, heartbeat, consumer sidecar, Hermes start)
- `agent/listen/main.py` -- FastAPI on :7600 (job CRUD)
- `halos/briefings/cli.py` -- Cron: `hal-briefing morning|nightly` (gather -> synthesise -> deliver)
- `halos/eventsource/run_consumer.py` -- Background NATS consumer (launched by entrypoint when `NATS_PASS` is set)

### Error Handling Patterns
- NATS hooks: `try/except Exception: return` -- never block gateway
- Event consumer: ack poison messages after `system.error` events -- prevent infinite redelivery
- Briefing synthesis: 3-tier auth fallback (CLI -> OAuth refresh -> API key -> raw data)
- Entrypoint: `|| echo "WARNING: ..."` for non-critical failures -- pod starts regardless
- Heartbeat: detects Hermes death but not asyncio deadlocks (TD-3 tracks health sidecar)

### Cross-Cutting Concerns
- **Logging**: `halos/common/log.py: hlog(source, level, event, data)` -- structured JSON. `HALOS_LOG_FILE` controls destination.
- **Path resolution**: `halos/common/paths.py` -- `store_dir()`, `repo_root()`. Priority: env var -> `HERMES_HOME/store` -> `cwd/store`.
- **Config loading**: Each module has `config.py` loading from repo-root YAML. Paths overridable via env vars.
- **Secrets**: Fleet: K8s Secrets. Briefings: 3-tier fallback. Local: 1Password SDK via `halos/secretctl/`. NATS: K8s username/password.
