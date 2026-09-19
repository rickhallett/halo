---
title: "Claude Reference Map"
category: reference
status: active
created: 2026-04-15
---

# Claude Reference Map

On-demand reference for file lookups, module APIs, agents, and documentation standards.
Read this when you need to find something — not on every boot.

## File Lookup by Task

| Task | Start at |
|---|---|
| Devlog / decisions | `docs/d1/development-logbook.md` (canonical — no other decision logs) |
| Work tracking | `halos/nightctl/` (state machine: open->active->done) |
| Memory system | `halos/memctl/`, `memory/INDEX.md` |
| Cron/briefings | `halos/cronctl/`, `halos/briefings/` |
| Metrics | `halos/trackctl/` (add domain: `halos/trackctl/domains/`) |
| Email ops | `halos/mailctl/` (engine->himalaya, triage rules, filter audit) |
| Agent spawning | `agent/listen/`, `agent/direct/` |
| Fleet manifests | `infra/k8s/fleet/` (manual kubectl apply via SSH to ryzen32) |
| Fleet image | `Dockerfile`, `docker/`, `vendor/hermes-agent` |

## Key Docs by Topic

| Topic | File | What's in it |
|---|---|---|
| Architecture | `docs/d2/REQUIREMENTS.md` | Architecture decisions, design rationale |
| Architecture | `docs/d2/architecture-deep-trace.md` | Full system trace |
| Architecture | `docs/d2/halos-architecture-review.md` | Architecture review findings |
| Modules | `docs/d1/halos-modules.md` | Module registry (canonical) |
| Memory ops | `docs/d1/memctl-operations.md` | memctl usage guide |
| Memory design | `docs/d2/memctl-spec.md` | memctl specification |
| Memory design | `docs/d2/memctl-architecture-overview.md` | memctl architecture |
| nightctl | `docs/d2/nightctl-spec.md` | nightctl specification |
| Security | `docs/d1/SECURITY.md` | Security model |
| Debug | `docs/d1/DEBUG_CHECKLIST.md` | Debug procedures |
| Containers | `docs/d1/docker-sandboxes.md` | Docker sandbox setup |
| Containers | `docs/d1/APPLE-CONTAINER-NETWORKING.md` | Apple Container networking |
| AI patterns | `docs/ai-engineering-patterns.md` | Full AI engineering governance catalogue |
| Review | `docs/d2/review-taxonomy.md` | Review finding categories |
| Review | `docs/d2/review-guide-2026-03-21.md` | Review process guide |
| Devlog | `docs/d1/development-logbook.md` | Decisions, lessons (canonical -- no other logs) |
| Deploy | `docs/d2/k8s-fleet-lessons-learned.md` | Fleet deploy lessons (Ryzen bare metal) |
| Topology | `docs/d1/system-topology.md` | System topology detail |
| Ecosystem | `docs/d2/halos-ecosystem-digest.md` | Ecosystem overview |
| Capability | `docs/d2/halos-capability-map.md` | Capability mapping |

## Module Quick Reference

All modules support `--help`. Detailed API docs: read source or run the command.

- **trackctl**: Pluggable domains in `store/track_<domain>.db`. Add domain: create `halos/trackctl/domains/<name>.py` with `register(name, description, target=N)`. Programmatic: `halos.trackctl.engine.text_summary(domain, target)`.
- **nightctl**: Eisenhower quadrants (q1-q4). `nightctl add --title "..." --quadrant q2`, `nightctl graph`. States: open->active->testing->done (also: blocked, deferred, cancelled). `--priority` auto-maps to `q<N>`.
- **dashctl**: TUI dashboard. `dashctl` (single), `dashctl --live`, `dashctl --json`, `dashctl --text`.
- **journalctl**: Qualitative journal. `journalctl add "text"`, `journalctl recent`, `journalctl window` (7d cached summary), `journalctl window --months 1` (30d). Tags: `--tags movement,body`. Source: `--source voice`. Store: `store/journal.db`, cache: `store/journal-cache/`.
- **watchctl**: YouTube monitor. Config: `watchctl.yaml` + `rubrics/watchctl-triage.yaml`. LLM: Groq (llama-3.3-70b) via GROQ_API_KEY. Transcripts: `youtube-transcript-api` with cookie auth.
- **mailctl**: Gmail via himalaya (`~/.config/himalaya/config.toml`). Triage rules in `halos/mailctl/triage.py` (VIP/noise, first match wins). Labels: jobs, infra, newsletters, commerce, noise; fallthrough stays in inbox.

## Programmatic API (import paths)

```python
# trackctl
trackctl.store.add_entry(domain, duration_mins, notes, timestamp) -> dict
trackctl.store.list_entries(domain, days=None) -> list[dict]
trackctl.store.daily_totals(domain, days=None) -> dict[str, int]
trackctl.engine.compute_summary(domain, target=None) -> dict
trackctl.engine.compute_streak(domain) -> dict
trackctl.engine.text_summary(domain, target=None) -> str

# nightctl
nightctl.item.load_all_items(items_dir) -> list[Item]
nightctl.item.find_item(items_dir, item_id) -> Item | None
nightctl.item.valid_transitions(status, kind) -> list[str]

# mailctl
mailctl.engine.list_messages(folder, page, page_size) -> list[dict]
mailctl.engine.read_message(message_id, folder="INBOX") -> dict
mailctl.engine.search(query, folder="INBOX") -> list[dict]
mailctl.engine.send(to, subject, body, cc=None) -> None
mailctl.briefing.text_summary() -> str

# dashctl
dashctl.panels.full_dashboard() -> list  # Rich renderables

# journalctl
journalctl.store.add_entry(raw_text, tags, source, mood, energy, timestamp) -> dict
journalctl.store.list_entries(days=7, tags=None) -> list[dict]
journalctl.store.count_entries() -> int
journalctl.window.window(days=7, no_cache=False) -> str
journalctl.window.window_month(no_cache=False) -> str

# memctl
memctl.index.read(path) -> Index
memctl.index.rebuild_from_notes(notes_dir, max_summary) -> (list[Entry], int)
memctl.note.parse(data) -> Note
memctl.note.marshal(note) -> str

# changoctl
changoctl.store.get_inventory(db_path=None) -> list[dict]
changoctl.store.restock(item, quantity=1, db_path=None) -> dict
changoctl.store.consume(item, mood=None, session_context=None, db_path=None) -> dict
changoctl.store.add_quote(text, category, source_session=None, source_module=None, db_path=None) -> dict
changoctl.store.random_quote(category=None, db_path=None) -> Optional[dict]
changoctl.store.list_consumption_history(item=None, days=None, db_path=None) -> list[dict]
changoctl.engine.sustain(mood, session_context=None, db_path=None) -> dict
changoctl.engine.text_summary(db_path=None) -> str

# briefings
briefings.gather.gather_morning(cfg) -> BriefingData
briefings.gather.gather_nightly(cfg) -> BriefingData
briefings.synthesise.synthesise(data, cfg) -> str
briefings.deliver.deliver_message(cfg, text) -> Path
```

All under `halos.` prefix (e.g. `from halos.trackctl.engine import text_summary`).

## Session Management

Agent sessions (Claude SDK conversation state) are managed through `halctl session`. **Never clear sessions via raw sqlite3 commands** -- always use halctl so mutations are logged via hlog and discoverable in logctl.

```bash
halctl session list                              # list sessions
halctl session clear telegram_main               # clear a specific group's session
halctl session clear-all                         # nuclear: clear all sessions
```

When to clear a session:
- Agent is unresponsive or spinning (poisoned context)
- Rate limit on resume (bloated session)
- After major CLAUDE.md or prompt changes that need a clean start

## Agents & Commands

| Name                 | Type    | File                                     | Purpose                                                                       |
| -------------------- | ------- | ---------------------------------------- | ----------------------------------------------------------------------------- |
| adversarial-reviewer | agent   | `.claude/agents/adversarial-reviewer.md` | Finds bugs after code changes (PostToolUse hook nudges)                       |
| strategic-analyst    | agent   | `.claude/agents/strategic-analyst.md`    | Research, scenario modelling, decision support                                |
| agent-organizer      | agent   | `.claude/agents/agent-organizer.md`      | Analyses requests, recommends agent teams (scans .claude/agents/ dynamically) |
| test-automator       | agent   | `.claude/agents/test-automator.md`       | Designs and implements test suites (pytest, vitest, Makefile gate)            |
| debugger             | agent   | `.claude/agents/debugger.md`             | Systematic root cause analysis (traces, doesn't guess)                        |
| tdd-driver           | agent   | `.claude/agents/tdd-driver.md`           | Red-green TDD: test first, minimum implementation, manual exercise            |
| documentation-expert | agent   | `.claude/agents/documentation-expert.md` | Maintains docs after changes (knows d1/d2/d3 hierarchy)                       |
| /spec                | command | `.claude/commands/spec.md`               | Interview-driven specification before coding                                  |
| /decompose           | command | `.claude/commands/decompose.md`          | Break tasks into atomic testable steps                                        |
| /dump                | command | `.claude/commands/dump.md`               | Checkpoint session context before compaction                                  |
| /review              | command | `.claude/commands/review.md`             | Orchestrated 3-round adversarial review (handoff -> blind -> targeted)        |
| /review-handoff      | command | `.claude/commands/review-handoff.md`     | Implementation model produces review map (not self-certification)             |
| /review-blind        | command | `.claude/commands/review-blind.md`       | Pass 1: blind adversarial review, ignores author framing                      |
| /review-targeted     | command | `.claude/commands/review-targeted.md`    | Pass 2: verify handoff claims against code                                    |

## Roundtable Advisors

Historical-figure advisors with persistent personas under `data/advisors/`. Summon by name or load the skill `roundtable-advisors` for full protocol.

| Seat | Name | Domain | Schedule |
|------|------|--------|----------|
| I | Musashi | Body (movement + zazen) | 07:00 daily |
| II | Draper | Pitch (positioning, narrative, creative authority) | 07:10 daily |
| III | Karpathy | Craft (AI engineering, fundamentals, learning) | 07:05 daily |
| IV | Gibson | Futures (market terrain, technology trajectory) | 07:25 daily |
| V | Machiavelli | Power, perception, leverage | 07:20 daily |
| VI | Medici | Money (debt, burn, runway, time economics) | 07:15 daily |
| VII | Bankei | Rest (rhythm, the cost of never stopping) | 07:35 daily |
| VIII | Hightower | Heavy Iron (K8s ops, cluster debugging, CKA) | 07:30 daily |
| IX | Turing | The Imitation Game (agentic engineering, systems design, interview drilling) | 10:00 daily |
| -- | Guido | Python craft, code aesthetics, language design | not deployed |
| -- | Plutarch | Dramaturg, narrator, parallel lives | not deployed |

## Data & Memory

| File                                | Purpose                                                     |
| ----------------------------------- | ----------------------------------------------------------- |
| `memory/INDEX.md`                   | Memory index (auto-maintained by memctl)                    |
| `memctl.yaml`                       | Memory governance config                                    |
| `store/messages.db`                 | SQLite: messages, sessions, onboarding, assessments, groups |
| `store/mail.db`                     | SQLite: managed Gmail filters, mailctl audit log            |

## Documentation Standards

All markdown files in `docs/` MUST have YAML frontmatter with four required fields:

```yaml
---
title: "Short descriptive title"
category: spec | analysis | runbook | review | briefing | reference | guide | journal | archive
status: draft | active | superseded | archived
created: YYYY-MM-DD
---
```

**Directory semantics** -- placement follows information lifecycle:

| Directory | Purpose | Rule of thumb |
|-----------|---------|---------------|
| `docs/d1/` | Working reference -- operational runbooks, guides, briefings, journals | You'd `cat` this mid-task |
| `docs/d2/` | Design record -- specs, analyses, reviews, research | You'd read this before starting a task |
| `docs/d3/` | Archive -- superseded, completed, historical | Archaeology only |

**Category vocabulary** -- nine words, controlled, no synonyms:

| Category | Where it lives | What it is |
|----------|----------------|------------|
| `runbook` | d1 | How to do X, step-by-step, command-oriented |
| `guide` | d1 | Setup, config, onboarding, narrative |
| `reference` | d1 | Module registry, security model, API surface |
| `journal` | d1 | Logbook, lessons learned, session patterns |
| `briefing` | d1/briefings | Machine-generated daily output |
| `spec` | d2 | Prescriptive -- what to build |
| `analysis` | d2 | Descriptive -- research, investigation, decision support |
| `review` | d2/reviews | Audit findings, code review output |
| `archive` | d3 | Superseded, completed, historical |

**Indexes** -- each directory has an auto-generated `INDEX.md` (never hand-edit). Rebuild with `docctl index rebuild`.

**When creating docs:** Add frontmatter, pick the right category, put it in the right directory. When in doubt: d2 for new analysis/specs, d1 for how-to content.

## Skills

| Skill               | When to Use                                                       |
| ------------------- | ----------------------------------------------------------------- |
| `/spec`             | Interview-driven specification before coding                      |
| `/decompose`        | Break tasks into atomic testable steps                            |
| `/review`           | Orchestrated 3-round adversarial review                           |
| `/qodo-pr-resolver` | Fetch and fix Qodo PR review issues interactively or in batch     |
| `/get-qodo-rules`   | Load org- and repo-level coding rules from Qodo before code tasks |
