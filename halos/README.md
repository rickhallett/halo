# halos/

Life-management CLI tools — 17 composable modules for work tracking, personal metrics, memory, communication, and infrastructure.

## Install

```bash
# From the repo root
uv sync

# All 17 CLIs are now available
nightctl --help
calctl --help
dashctl --help
```

## Modules

### Work & Planning

| CLI | What It Does |
|-----|-------------|
| `nightctl` | Work tracking with Eisenhower matrix (q1-q4), 13-state machine, overnight execution |
| `cronctl` | Cron job definitions as YAML, crontab generation, manual triggering |
| `calctl` | Unified schedule — Google Calendar + nightctl deadlines + cronctl jobs |

```bash
nightctl add --title "Fix race condition" --quadrant q1
nightctl list --quadrant q1 --state active
nightctl graph                              # Eisenhower matrix view
calctl today                                # everything happening today
calctl conflicts                            # overlapping commitments
calctl free --duration 60                   # find open 60-min slots
cronctl list                                # all scheduled jobs
```

### Personal Metrics

| CLI | What It Does |
|-----|-------------|
| `trackctl` | Habit tracker with pluggable domains, streak engine, daily sums |
| `dashctl` | TUI dashboard — RPG character sheet for metrics + Eisenhower view |
| `ledgerctl` | Plain-text accounting, bank CSV import (ANZ, Wise), categorisation rules |

```bash
trackctl add zazen --duration 25            # log 25 minutes of meditation
trackctl add movement --duration 45         # log exercise
trackctl add study --duration 60            # log study time
trackctl streak zazen                       # current: 12, longest: 47, target: 100
dashctl                                     # full TUI dashboard
dashctl --html --output dashboard.html      # self-contained HTML export
ledgerctl import --bank anz --csv statement.csv
ledgerctl balance                           # P&L by account
```

### Memory & Knowledge

| CLI | What It Does |
|-----|-------------|
| `memctl` | Structured memory — atomic notes, entity linking, decay pruning, graph analysis |

```bash
memctl new --title "..." --type decision --tags "arch,security" --body "..."
memctl search --tags arch --type decision
memctl graph                                # interactive knowledge graph (HTML)
memctl stats                                # corpus health metrics
```

### Communication

| CLI | What It Does |
|-----|-------------|
| `mailctl` | Gmail via himalaya — inbox, search, triage rules, filter management, send |

```bash
mailctl inbox --unread                      # what needs attention
mailctl triage --execute                    # apply deterministic triage rules
mailctl summary                             # "12 unread (3 from ben) | 247 total"
```

### Observability

| CLI | What It Does |
|-----|-------------|
| `logctl` | Structured log search, fleet aggregation, token usage tracking |
| `agentctl` | Session tracking, spin detection, error streaks |
| `statusctl` | Fleet health — service, container, agent, and host metrics |

```bash
logctl errors                               # errors in last 24h
logctl usage --since 7d --by model          # token cost breakdown
statusctl                                   # full health report
statusctl check                             # exit 0 if HEALTHY, exit 1 if not
```

### Operations

| CLI | What It Does |
|-----|-------------|
| `halctl` | Fleet provisioning, session lifecycle, eval harness, supervisor |
| `backupctl` | Structured backup policy, SQLite-safe snapshots, restic/tar backend |

```bash
halctl create --name ben --personality discovering-ben
halctl session list                          # all active sessions
halctl session clear telegram_main           # clear poisoned session
halctl health all --heal                     # fleet health check + auto-fix
backupctl run                                # backup all targets
backupctl verify                             # check integrity
```

### Synthesis

| CLI | What It Does |
|-----|-------------|
| `hal-briefing` | Daily digests — morning, nightly, overnight summary, diary, check-in |
| `reportctl` | Periodic data collection — briefing, weekly, health, digest |

```bash
hal-briefing morning                        # 0600 daily briefing
hal-briefing nightly                        # 2100 recap
hal-briefing diary                          # autonomous reflection entry
reportctl digest --since 24h               # activity digest
```

### Other

| CLI | What It Does |
|-----|-------------|
| `blogctl` | Blog post management |
| `carnivorectl` | Carnivore diet tracking |

## Adding a New Module

1. Create `halos/<name>ctl/` with `__init__.py` and `cli.py`
2. Implement `cli.py` with a `main()` entry point
3. Add to `pyproject.toml` under `[project.scripts]`:
   ```toml
   namectl = "halos.namectl.cli:main"
   ```
4. Run `uv sync` to register the new CLI
5. Add tests in `tests/<name>ctl/`

### Adding a Tracking Domain

Trackctl supports pluggable domains. To add one:

1. Create `halos/trackctl/domains/<name>.py`
2. Call `register(name, description, target=N)` at module level
3. The domain auto-discovers at import time — no other wiring needed

```python
# halos/trackctl/domains/reading.py
from halos.trackctl.registry import register
register("reading", "Daily reading time", target=30)
```

## Configuration

YAML config files live at the repo root:

| File | Module | Purpose |
|------|--------|---------|
| `nightctl.yaml` | nightctl | Work item defaults, quadrant labels |
| `cronctl.yaml` | cronctl | Cron schedule definitions |
| `memctl.yaml` | memctl | Memory config, decay rules |
| `logctl.yaml` | logctl | Log paths, fleet instances |
| `briefings.yaml` | hal-briefing | Briefing schedule and content config |
| `reportctl.yaml` | reportctl | Report collectors and formatters |
| `todoctl.yaml` | todoctl | Legacy todo config |
| `agentctl.yaml` | agentctl | Agent session config |

## Data Storage

```
store/              SQLite databases (one per domain)
memory/             Markdown notes, reflections, session dumps
queue/items/        YAML work items
cron/jobs/          YAML cron job definitions
logs/               Structured JSONL event stream
```

## Testing

```bash
# All tests
uv run pytest tests/ -v --tb=short

# Coverage
uv run pytest tests/ -v --tb=short --cov=halos --cov-report=term-missing

# Single module
uv run pytest tests/nightctl/ -v
uv run pytest tests/memctl/ -v
```

## Programmatic Access

Every module exposes Python APIs alongside the CLI:

```python
from halos.trackctl.store import add_entry
from halos.trackctl.engine import compute_summary, text_summary
from halos.nightctl.item import Item
from halos.mailctl.engine import list_messages, search
from halos.memctl.store import create_note, search_notes
from halos.dashctl.panels import full_dashboard
```
