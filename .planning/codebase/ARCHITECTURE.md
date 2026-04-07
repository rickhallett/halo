# Architecture

**Analysis Date:** 2026-04-07

## Pattern Overview

**Overall:** Multi-surface personal AI assistant with event-sourced communication between a K8s fleet of advisor agents, a Python CLI tooling layer, and cron-driven briefings. The system is a monorepo containing infrastructure manifests, agent harnesses, and a shared Python package (`halos/`).

**Key Characteristics:**
- **Monorepo with heterogeneous surfaces:** Three runtime contexts (K8s fleet, local agent spawner, cron jobs) share one repository and one Python tooling layer
- **Event sourcing via NATS JetStream:** Advisors publish events to a `HALO` stream; each advisor maintains a local SQLite projection rebuilt from the stream
- **Upstream wrapping, not forking:** The Hermes Telegram bot (`vendor/hermes-agent`) is consumed as a git submodule. All customisation is via config injection, entrypoint hooks, and PYTHONPATH overlays — never source patches
- **CLI-first tooling:** Every halos module is a standalone CLI (console_scripts) and also importable as a Python library. The `hal` command (`halos/hal.py`) is a unified dispatcher

## Layers

**Agent Surface Layer (Hermes / Fleet):**
- Purpose: Provides conversational AI interfaces via Telegram
- Location: `vendor/hermes-agent` (git submodule), `docker/entrypoint.sh`, `Dockerfile`
- Contains: Upstream Hermes bot runtime, entrypoint hooks for prompt injection, NATS hook registration, heartbeat wrapper, WAL enforcement
- Depends on: halos tooling (overlaid via init container), NATS JetStream, Anthropic API
- Used by: End users via Telegram

**Agent Spawner Layer (listen/direct):**
- Purpose: Local HTTP server that accepts prompts and spawns Claude Code instances in background processes
- Location: `agent/listen/main.py` (FastAPI server on :7600), `agent/direct/main.py` (CLI client)
- Contains: Job lifecycle management (create, list, stop, archive), worker process spawning, session telemetry
- Depends on: Claude Code CLI, tmux (for interactive mode)
- Used by: Developer (locally) via `just` commands or HTTP

**Halos Tooling Layer (Python CLI):**
- Purpose: Shared operational CLI tools used by all surfaces — memory, work tracking, briefings, metrics, mail, secrets
- Location: `halos/` package (20+ modules)
- Contains: Each module follows cli.py + engine/store pattern with YAML/SQLite persistence
- Depends on: `halos/common/` (logging, path resolution), SQLite databases in `store/`, YAML configs at repo root
- Used by: All surfaces (Hermes via PYTHONPATH overlay, cron via `uv run`, developer directly)

**Event Sourcing Layer:**
- Purpose: Asynchronous event bus connecting advisors and projecting shared state
- Location: `halos/eventsource/` (core, consumer, projection, handlers)
- Contains: Event envelope (`core.py`), NATS consumer lifecycle (`consumer.py`), SQLite projection engine (`projection.py`), domain handlers (`handlers/`)
- Depends on: NATS JetStream (cluster-internal), SQLite
- Used by: Fleet advisors (each runs a consumer sidecar process via `entrypoint.sh`)

**Infrastructure Layer:**
- Purpose: K8s manifests for the advisor fleet, managed by Argo CD
- Location: `infra/k8s/fleet/` (deployments, configs, secrets, NATS, PVCs), `infra/k8s/fleet/cronjobs/` (scheduled advisor jobs)
- Contains: Per-advisor Deployment + ConfigMap + Secret + prompt YAML, NATS StatefulSet, NFS server for shared memory, Argo CD app definition
- Depends on: Vultr Container Registry (`lhr.vultrcr.com/jeany/halo`), Argo CD
- Used by: K8s cluster (Argo CD sync)

**Data & Memory Layer:**
- Purpose: Persistent structured memory, work items, personal metrics, journals
- Location: `memory/` (memctl-managed notes + INDEX.md), `store/` (SQLite databases), `backlog/items/` (YAML work items)
- Contains: Markdown notes with YAML frontmatter (memory), domain-specific SQLite DBs (tracking, jobs, journal, mail, blog), YAML backlog items
- Depends on: memctl for governance, nightctl for work tracking
- Used by: All halos modules, briefings gather layer

**Configuration Layer:**
- Purpose: YAML config files that control module behaviour
- Location: Repo root — `memctl.yaml`, `nightctl.yaml`, `cronctl.yaml`, `briefings.yaml`, `watchctl.yaml`, `agentctl.yaml`, `logctl.yaml`, `reportctl.yaml`
- Contains: Module-specific settings (paths, schedules, thresholds)
- Depends on: Nothing
- Used by: Each respective halos module's `config.py`

## Data Flow

**Advisor Touchbase (Scheduled):**

1. K8s CronJob creates a pod from the advisor's Deployment template (`infra/k8s/fleet/cronjobs/`)
2. `docker/entrypoint.sh` bootstraps config, injects system prompt from ConfigMap, registers NATS hooks, starts event consumer sidecar
3. Hermes processes the touchbase prompt using the advisor's persona (from `system-prompt.md` ConfigMap)
4. NATS hook (`handler.py` generated in entrypoint) publishes `advisor.inbound.received` / `advisor.outbound.sent` events to JetStream
5. Other advisors' consumer sidecars receive events and update their local SQLite projections via `ProjectionEngine`

**Briefing Pipeline (Cron):**

1. `cronctl` triggers `hal-briefing` at scheduled times (defined in `cron/jobs/`)
2. `halos/briefings/gather.py` collects data from reportctl collectors, trackctl, nightctl, logctl, dashctl, git-pulse
3. `halos/briefings/synthesise.py` passes gathered context through Claude (via CLI, OAuth, or API key — 3-tier auth fallback)
4. `halos/briefings/deliver.py` writes the synthesised briefing to Telegram via file drop to Hermes IPC

**Agent Job (Local):**

1. HTTP POST to `agent/listen/main.py` :7600 `/job` with prompt and mode
2. FastAPI handler writes job YAML to `agent/listen/jobs/{id}.yaml`, spawns `worker.py` subprocess
3. Worker invokes `claude` CLI (Claude Code) with the prompt, captures output
4. Job YAML updated with status, summary, and telemetry on completion

**Memory Governance:**

1. `memctl new` creates a note in `memory/notes/` with YAML frontmatter (tags, links, score)
2. `memctl rebuild` regenerates `memory/INDEX.md` from all notes (scored, sorted, with entity extraction)
3. `memctl prune` removes low-score notes past retention threshold
4. `memctl enrich` runs LLM-powered enrichment (backlinks, entity graph)

**State Management:**
- Each halos module owns its own SQLite database in `store/` (e.g., `store/track_zazen.db`, `store/journal.db`, `store/jobs.db`)
- Memory notes are filesystem-based (markdown in `memory/notes/`)
- Fleet state is projected from the NATS event stream into per-advisor SQLite DBs
- Agent jobs are YAML files in `agent/listen/jobs/`

## Key Abstractions

**Event Envelope (`halos/eventsource/core.py: Event`):**
- Purpose: Immutable event record with ULID-based ID, type, version, source, timestamp, correlation_id, and payload
- Pattern: Event sourcing with idempotent projection replay
- Subject convention: `halo.{event.type}` (e.g., `halo.track.zazen.logged`, `halo.advisor.inbound.received`)

**ProjectionHandler (`halos/eventsource/core.py: ProjectionHandler`):**
- Purpose: Abstract base for event handlers that update a local SQLite read model
- Examples: `halos/eventsource/handlers/track.py`, `halos/eventsource/handlers/night.py`, `halos/eventsource/handlers/journal.py`, `halos/eventsource/handlers/observation.py`
- Pattern: Each handler declares `handles() -> list[str]` and `apply(event, db)`. Schema init via `init_schema(db)`.

**ProjectionEngine (`halos/eventsource/projection.py`):**
- Purpose: Disposable SQLite read model. Delete it, replay from stream, get same state. Stream is truth.
- Pattern: Checkpoint-based consumption with idempotency via `_processed_events` table

**Advisor Persona (`data/advisors/{name}/`):**
- Purpose: Historical-figure AI advisor with persistent persona, profile, and prototype schedule
- Examples: `data/advisors/musashi/persona.md`, `data/advisors/draper/profile.md`
- Pattern: Persona markdown injected as system prompt via K8s ConfigMap → entrypoint `HERMES_EPHEMERAL_SYSTEM_PROMPT`

**Halos Module (cli.py + engine/store):**
- Purpose: Self-contained CLI tool with importable Python API
- Examples: `halos/trackctl/` (cli.py, engine.py, store.py, registry.py, domains/), `halos/nightctl/` (cli.py, item.py, executor.py, config.py)
- Pattern: argparse or click CLI → engine/store logic → SQLite or filesystem persistence → structured JSON logging via `hlog()`

**Unified Dispatcher (`halos/hal.py`):**
- Purpose: Single `hal` command that dispatches to any halos module or agent tool
- Pattern: Module registry dict mapping aliases to console_script commands, with `os.execvp` dispatch

## Entry Points

**`hal` CLI (`halos/hal.py: main`):**
- Location: `halos/hal.py`
- Triggers: User runs `hal <module> [args]`
- Responsibilities: Dispatch to any halos module or agent tool via alias lookup and `os.execvp`

**Container Entrypoint (`docker/entrypoint.sh`):**
- Location: `docker/entrypoint.sh`
- Triggers: Container start (K8s pod creation or `docker run`)
- Responsibilities: Directory bootstrap, config injection, system prompt loading, NATS hook installation, touchbase cron setup, WAL enforcement, skill sync, heartbeat wrapper, event consumer sidecar launch, Hermes process start

**Agent Listen Server (`agent/listen/main.py`):**
- Location: `agent/listen/main.py`
- Triggers: `just listen` from `agent/` directory
- Responsibilities: FastAPI HTTP server on :7600 for job CRUD — create, get, list, stop, clear

**Briefing CLI (`halos/briefings/cli.py`):**
- Location: `halos/briefings/cli.py`
- Triggers: Cron via `hal-briefing morning` or `hal-briefing nightly`
- Responsibilities: Orchestrate gather → synthesise → deliver pipeline

**Event Consumer (`halos/eventsource/run_consumer.py`):**
- Location: `halos/eventsource/run_consumer.py`
- Triggers: `entrypoint.sh` launches as background process when `NATS_PASS` is set
- Responsibilities: Connect to NATS JetStream, replay from checkpoint, maintain local SQLite projection

## Error Handling

**Strategy:** Fail-safe with structured logging. Hooks and sidecars must never block the main process.

**Patterns:**
- NATS hooks wrap all operations in `try/except Exception: return` — gateway processing is never blocked by event publishing failures
- Event consumer acks poison messages after reporting errors via `system.error` events — prevents infinite redelivery
- Briefing synthesis has 3-tier auth fallback (CLI → OAuth refresh → API key → raw data) — degrades gracefully
- Container entrypoint uses `|| echo "WARNING: ..."` for non-critical failures (WAL enforcement, skill sync) — pod starts regardless
- Heartbeat wrapper detects Hermes death but not asyncio deadlocks (documented limitation, TD-3 tracks HTTP health sidecar)

## Cross-Cutting Concerns

**Logging:**
- Structured JSON logging via `halos/common/log.py: hlog(source, level, event, data)`
- All halos modules emit structured events (e.g., `hlog("cronctl", "info", "job_created", {...})`)
- Fleet log aggregation via `halos/logctl/fleet.py`
- Env var `HALOS_LOG_FILE` controls output destination (file or stderr)

**Path Resolution:**
- `halos/common/paths.py` provides `store_dir()` and `repo_root()` 
- Priority chain: env var (`HALO_STORE_DIR`) → `HERMES_HOME/store` → `cwd/store`
- Ensures halos modules work in both local dev (cwd = repo root) and container (cwd = `HERMES_HOME`) contexts

**Configuration:**
- Each module has a `config.py` that loads from a YAML file at repo root (e.g., `memctl.yaml`, `nightctl.yaml`)
- Config file paths are overridable via env vars (e.g., `MEMCTL_CONFIG`)

**Authentication:**
- Fleet advisors: Anthropic API key via K8s Secret, Telegram bot token via K8s Secret
- Briefings: 3-tier fallback (Claude CLI OAuth → token refresh → `ANTHROPIC_API_KEY`)
- Secrets: 1Password SDK via `halos/secretctl/` (daemon mode for caching)
- NATS: username/password auth via K8s Secrets

---

*Architecture analysis: 2026-04-07*
