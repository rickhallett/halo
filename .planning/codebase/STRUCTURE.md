# Codebase Structure

**Analysis Date:** 2026-04-07

## Directory Layout

```
halo/
├── .claude/                # Claude Code agent/command/skill definitions
│   ├── agents/             # Agent persona prompts (adversarial-reviewer, tdd-driver, etc.)
│   ├── commands/           # Slash commands (/spec, /review, /decompose, etc.)
│   ├── evals/              # Evaluation definitions
│   └── skills/             # Reusable skill packs (qodo-pr-resolver, etc.)
├── .hermes/                # Hermes agent plans
│   └── plans/
├── .pi/                    # Pi agent config (skills for halos modules, extensions)
│   ├── extensions/
│   └── skills/             # Per-module skill definitions (halos-memctl, roundtable-advisors, etc.)
├── .planning/              # GSD planning workspace
│   └── codebase/           # Architecture/convention docs (this file lives here)
├── agent/                  # Local agent spawner (listen server + direct client)
│   ├── direct/             # CLI client for listen server (click-based)
│   ├── drive/              # Tmux terminal control (legacy, removed in heritage sweep)
│   ├── listen/             # FastAPI HTTP server on :7600 for job management
│   │   ├── jobs/           # Active job YAML files
│   │   │   └── archived/   # Completed/cleared jobs
│   │   ├── main.py         # FastAPI app (create, get, list, stop, clear jobs)
│   │   └── worker.py       # Subprocess that runs Claude Code per job
│   ├── assets/             # Diagrams and visual assets
│   └── specs/              # Agent job specifications
├── backlog/                # Backlog items (YAML files)
│   └── items/              # Individual backlog item files
├── config-examples/        # Example configuration files
├── cron/                   # Cron job definitions
│   └── jobs/               # YAML job specs (morning-briefing, nightctl-summary, etc.)
├── data/                   # Runtime data and advisor personas
│   ├── advisors/           # Per-advisor persona data
│   │   ├── musashi/        # persona.md, profile.md, prototype-week.md
│   │   ├── draper/
│   │   ├── karpathy/
│   │   ├── gibson/
│   │   ├── machiavelli/
│   │   ├── medici/
│   │   ├── bankei/
│   │   ├── hightower/
│   │   └── ...             # (seneca, socrates, sun-tzu, plutarch — inactive)
│   ├── agent-sessions/     # Agent session state
│   ├── clients/            # Client-specific data (e.g., aura/)
│   ├── env/                # Environment data
│   ├── finance/            # Financial tools (ark-accounting — uv workspace member)
│   ├── ipc/                # Inter-process communication (Telegram message drops)
│   │   └── telegram_main/  # input/, messages/, tasks/
│   ├── observations/       # Observation data (client observations)
│   └── sessions/           # Hermes session state (Claude SDK conversations)
├── docker/                 # Container build support
│   ├── defaults/           # Default config.yaml and system-prompt.md for fresh containers
│   └── entrypoint.sh       # Container entrypoint (bootstrap, hooks, heartbeat, consumer)
├── docs/                   # Documentation (d1/d2/d3 hierarchy)
│   ├── d1/                 # Working reference — runbooks, guides, journals
│   ├── d2/                 # Design record — specs, analyses, reviews
│   │   └── reviews/        # Code review and audit outputs
│   └── d3/                 # Archive — superseded, historical
├── groups/                 # Group-specific config for Hermes
│   ├── global/             # Global CLAUDE.md (applies to all groups)
│   └── telegram_main/      # Telegram-specific CLAUDE.md, fleet audit scripts
├── halos/                  # Python CLI tooling package (the core)
│   ├── common/             # Shared utilities (log.py, paths.py)
│   ├── agentctl/           # LLM session tracking and spin detection
│   ├── backupctl/          # Backup management
│   ├── briefings/          # Daily digest pipeline (gather → synthesise → deliver)
│   ├── calctl/             # Calendar operations
│   ├── cronctl/            # Cron job definitions and crontab generation
│   ├── dashctl/            # TUI dashboard (Rich-based RPG character sheet)
│   ├── docctl/             # Documentation management and frontmatter validation
│   ├── eventsource/        # NATS event sourcing (core, consumer, projection, handlers)
│   │   └── handlers/       # Domain-specific projection handlers (track, night, journal, observation)
│   ├── halctl/             # Session lifecycle, health checks, eval harness, provisioning
│   ├── halyt/              # (Minimal helper)
│   ├── journalctl/         # Qualitative journal with LLM-synthesised sliding window
│   ├── ledgerctl/          # Finance ledger
│   ├── logctl/             # Structured log reader, search, fleet log aggregation
│   ├── mailctl/            # Gmail operations via himalaya (triage, filters, briefing)
│   ├── memctl/             # Structured memory governance (notes, index, enrich, prune, graph)
│   ├── microhal/           # Onboarding module
│   ├── nightctl/           # Unified work tracker with Eisenhower matrix + state machine
│   ├── reportctl/          # Periodic digest collectors
│   ├── secretctl/          # 1Password secret access (client + daemon)
│   ├── statusctl/          # System status checks
│   ├── telemetry/          # Telemetry collection
│   ├── todoctl/            # Legacy todo (migrated to nightctl)
│   ├── trackctl/           # Personal metrics tracker
│   │   └── domains/        # Pluggable domain definitions (movement, zazen, study)
│   ├── watchctl/           # YouTube channel monitor (RSS → transcript → LLM eval → Obsidian)
│   ├── hal.py              # Unified `hal` dispatcher command
│   └── README.md           # Halos package overview
├── infra/                  # Infrastructure manifests
│   └── k8s/
│       └── fleet/          # K8s fleet manifests (Argo CD managed)
│           ├── cronjobs/   # Per-advisor CronJob manifests + kustomization.yaml
│           ├── *-deployment.yaml   # Per-advisor Deployment (8 advisors)
│           ├── *-config.yaml       # Per-advisor ConfigMap
│           ├── *-prompt.yaml       # Per-advisor system prompt ConfigMap
│           ├── *-secrets.yaml      # Per-advisor Secret (gitignored, examples tracked)
│           ├── nats.yaml           # NATS StatefulSet
│           ├── nats-config.yaml    # NATS ConfigMap
│           ├── nats-init-stream.yaml  # NATS stream init Job
│           ├── nfs-server.yaml     # NFS server for shared memory PVC
│           ├── memory-pvc.yaml     # Shared memory PersistentVolumeClaim
│           ├── namespace.yaml      # halo-fleet namespace
│           ├── argocd-app.yaml     # Argo CD Application definition
│           └── kaniko-build.yaml   # In-cluster image build Job
├── jobctl/                 # Job automation tools (JD evaluator, form fillers)
├── logs/                   # Local log directory
├── memory/                 # Structured memory (memctl-managed)
│   ├── notes/              # Active memory notes (YAML frontmatter + markdown)
│   ├── archive/            # Archived/pruned notes
│   ├── backlinks/          # Auto-generated backlink files
│   ├── reflections/        # HAL's autonomous journal (not governed by memctl)
│   ├── session-dumps/      # Context dumps from /dump command
│   └── INDEX.md            # Auto-generated memory index (never hand-edit)
├── queue/                  # Job queue directory
├── rubrics/                # LLM evaluation rubrics (watchctl-triage.yaml)
├── scripts/                # One-off and utility scripts
├── silicon-dao/            # Static site (HTML/CSS)
├── store/                  # SQLite databases and persistent state
│   ├── track_*.db          # Per-domain tracking databases
│   ├── journal.db          # Journal entries
│   ├── journal-cache/      # LLM synthesis cache for journal windows
│   ├── jobs.db             # Nightctl job database
│   ├── messages.db         # Hermes messages, sessions, groups
│   ├── mail.db             # Mailctl filter audit
│   ├── watch.db            # Watchctl YouTube monitor
│   └── blogctl.db          # Blog management
├── templates/              # Templates (docs frontmatter, microhal)
├── tests/                  # Test suite (mirrors halos module structure)
├── vendor/                 # Git submodules
│   └── hermes-agent        # Upstream Hermes Telegram bot (submodule)
├── Dockerfile              # Fleet container image (Debian + Hermes + halos)
├── Dockerfile.halos        # Halos-only image (init container for overlay)
├── Makefile                # Gate: test + lint + typecheck
├── pyproject.toml          # Python project config (halos package)
├── CLAUDE.md               # Project instructions for Claude Code
├── AGENTS.md               # Agent registry documentation
└── *.yaml                  # Module config files (memctl, nightctl, cronctl, etc.)
```

## Directory Purposes

**`halos/`:**
- Purpose: Core Python tooling package — all CLI modules and shared libraries
- Contains: 20+ subpackages, each a self-contained CLI tool with importable API
- Key files: `hal.py` (dispatcher), `common/log.py` (structured logging), `common/paths.py` (path resolution)

**`infra/k8s/fleet/`:**
- Purpose: Complete K8s manifest set for the advisor fleet, synced by Argo CD
- Contains: Per-advisor Deployments/ConfigMaps/Secrets, NATS infrastructure, NFS shared storage, CronJobs
- Key files: `argocd-app.yaml` (Argo CD entry), `namespace.yaml`, `nats.yaml`, `README.md`

**`agent/listen/`:**
- Purpose: Local agent job server — accepts prompts via HTTP, spawns Claude Code workers
- Contains: FastAPI app, worker subprocess, session telemetry, job YAML files
- Key files: `main.py` (server), `worker.py` (job runner), `justfile` (task runner)

**`docker/`:**
- Purpose: Container build support — entrypoint script and default configs
- Contains: `entrypoint.sh` (main bootstrap logic), `defaults/` (fallback config files)
- Key files: `entrypoint.sh` (~280 lines of bootstrap, hook registration, heartbeat wrapper)

**`memory/`:**
- Purpose: Structured memory corpus governed by memctl
- Contains: Active notes, archived notes, backlinks, reflections, session dumps
- Key files: `INDEX.md` (auto-generated, never hand-edit), `notes/` (active corpus)

**`store/`:**
- Purpose: SQLite databases for all halos modules
- Contains: Domain-specific DBs (tracking, journal, jobs, messages, mail, blog, watch)
- Key files: `jobs.db` (nightctl), `messages.db` (Hermes sessions), `track_*.db` (per-domain metrics)

**`data/advisors/`:**
- Purpose: Persona definitions for roundtable advisor agents
- Contains: Per-advisor directories with persona.md, profile.md, and optional prototype-week.md
- Key files: `{name}/persona.md` (character definition injected as system prompt)

**`cron/jobs/`:**
- Purpose: Cron job definitions for scheduled tasks
- Contains: YAML files defining schedule, command, and delivery for each cron job
- Key files: `morning-briefing.yaml`, `nightly-recap.yaml`, `nightctl-summary.yaml`

**`tests/`:**
- Purpose: Test suite matching halos module structure
- Contains: Per-module test directories, fixtures, fleet tests, integration tests
- Key files: `test_e2e_gauntlet.py` (60k lines, comprehensive E2E), `test_docctl.py`, `test_journalctl.py`

## Key File Locations

**Entry Points:**
- `halos/hal.py`: Unified `hal` CLI dispatcher — start here for any halos module
- `docker/entrypoint.sh`: Container bootstrap — start here for fleet/container behaviour
- `agent/listen/main.py`: Agent job server — start here for local agent spawning
- `halos/briefings/cli.py`: Briefing pipeline entry
- `halos/eventsource/run_consumer.py`: Event consumer entry (started by entrypoint.sh)

**Configuration:**
- `pyproject.toml`: Python package definition, console_scripts, test markers, uv workspace
- `Makefile`: Gate (test + lint + typecheck)
- `CLAUDE.md`: Project instructions for all Claude Code sessions
- `memctl.yaml`, `nightctl.yaml`, `cronctl.yaml`, `briefings.yaml`, `watchctl.yaml`: Module configs at repo root
- `.gitmodules`: Tracks `vendor/hermes-agent` submodule

**Core Logic:**
- `halos/eventsource/core.py`: Event envelope and NATS publisher primitives
- `halos/eventsource/consumer.py`: NATS consumer lifecycle (AdvisorEventLoop)
- `halos/eventsource/projection.py`: SQLite projection engine
- `halos/memctl/cli.py`: Memory governance commands (19k lines)
- `halos/nightctl/cli.py`: Work tracker commands (33k lines)
- `halos/nightctl/item.py`: Work item model and state machine (18k lines)
- `halos/briefings/gather.py`: Briefing data collection from all modules
- `halos/briefings/synthesise.py`: LLM synthesis with 3-tier auth fallback

**Infrastructure:**
- `Dockerfile`: Main fleet image (Debian + Hermes + halos + Node.js)
- `Dockerfile.halos`: Halos-only image (used as init container for PYTHONPATH overlay)
- `infra/k8s/fleet/musashi-deployment.yaml`: Reference advisor deployment (pattern for all 8)
- `infra/k8s/fleet/nats.yaml`: NATS StatefulSet
- `infra/k8s/fleet/argocd-app.yaml`: Argo CD Application

**Testing:**
- `tests/`: Per-module test directories mirroring `halos/` structure
- `tests/fleet/`: Fleet-specific tests (tier markers: tier1-tier5)
- `tests/fixtures/`: Shared test fixtures
- `tests/test_e2e_gauntlet.py`: Comprehensive E2E test suite

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `session_telemetry.py`, `eval_harness.py`)
- K8s manifests: `{advisor}-{resource}.yaml` (e.g., `musashi-deployment.yaml`, `draper-config.yaml`)
- Config files: `{module}.yaml` at repo root (e.g., `memctl.yaml`, `nightctl.yaml`)
- Cron jobs: `{descriptive-name}.yaml` in `cron/jobs/` (e.g., `morning-briefing.yaml`)
- Memory notes: `{YYYYMMDD}-{HHMMSS}-{slug}.md` in `memory/notes/`
- Backlog items: `{YYYYMMDD}-{HHMMSS}-{slug}.yaml` in `backlog/items/`
- SQLite databases: `{module}.db` or `track_{domain}.db` in `store/`

**Directories:**
- Halos modules: `halos/{modulename}/` — lowercase, no hyphens (e.g., `nightctl`, `mailctl`, `eventsource`)
- Test directories: `tests/{modulename}/` — mirrors halos structure
- Advisor data: `data/advisors/{name}/` — lowercase advisor name
- K8s fleet: `infra/k8s/fleet/` — flat directory with name-prefixed files

**Python:**
- Modules use `__init__.py` (often empty or with brief `__all__` export)
- CLI entry: always `cli.py` with `main()` function
- Config loading: always `config.py` with `load_config()` or `Config` class
- Store/persistence: `store.py` for SQLite operations, `engine.py` for business logic

## Where to Add New Code

**New Halos Module:**
- Implementation: `halos/{modulename}/` with at minimum `__init__.py`, `cli.py`, `config.py`
- Console script: Add entry in `pyproject.toml` `[project.scripts]`
- Dispatcher alias: Add entry in `halos/hal.py` `MODULES` dict
- Config file: `{modulename}.yaml` at repo root
- Tests: `tests/{modulename}/`
- Database: `store/{modulename}.db` (if needed)
- Docs: Update `CLAUDE.md` module table and `docs/d1/halos-modules.md`

**New Advisor:**
- Persona data: `data/advisors/{name}/persona.md`, `profile.md`
- K8s manifests: `infra/k8s/fleet/{name}-deployment.yaml`, `{name}-config.yaml`, `{name}-prompt.yaml`, `{name}-secrets.yaml`
- CronJob (if scheduled): `infra/k8s/fleet/cronjobs/advisor-{name}-cronjob.yaml`
- Update kustomization: `infra/k8s/fleet/cronjobs/kustomization.yaml`

**New Event Handler:**
- Handler: `halos/eventsource/handlers/{domain}.py` implementing `ProjectionHandler`
- Register: Add to handler list in `halos/eventsource/handlers/__init__.py`
- Tests: `tests/eventsource/`

**New Trackctl Domain:**
- Domain: `halos/trackctl/domains/{name}.py` with `register(name, description, target=N)`
- Database: Auto-created as `store/track_{name}.db`

**New Cron Job:**
- Job definition: `cron/jobs/{name}.yaml`
- Install: `cronctl install --execute` to regenerate crontab

**New Documentation:**
- Design/spec: `docs/d2/{slug}.md` with required YAML frontmatter (title, category, status, created)
- Operational guide: `docs/d1/{slug}.md` with required YAML frontmatter
- Rebuild index: `docctl index rebuild`

## Special Directories

**`vendor/hermes-agent`:**
- Purpose: Upstream Hermes Telegram bot framework (git submodule)
- Generated: No (external source)
- Committed: Submodule reference only (`.gitmodules`)
- Rule: Never patch source. All customisation via config, entrypoint hooks, PYTHONPATH overlay.

**`store/`:**
- Purpose: All SQLite databases for halos modules
- Generated: Yes (created at runtime by modules)
- Committed: No (gitignored, except structure)
- Rule: Use WAL mode. Backup via backupctl.

**`memory/INDEX.md`:**
- Purpose: Auto-generated memory index
- Generated: Yes (by `memctl rebuild`)
- Committed: Yes
- Rule: Never hand-edit. Rebuild with `memctl rebuild`.

**`data/sessions/`:**
- Purpose: Hermes Claude SDK session state
- Generated: Yes (runtime)
- Committed: No
- Rule: Clear via `halctl session clear`, never raw sqlite3.

**`.planning/`:**
- Purpose: GSD planning workspace for architecture docs and phase plans
- Generated: Yes (by GSD tooling)
- Committed: Selective
- Rule: Consumed by `/gsd-plan-phase` and `/gsd-execute-phase`.

---

*Structure analysis: 2026-04-07*
