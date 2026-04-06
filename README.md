# Halo

Halo is a personal AI operating system built as a monorepo.

At runtime, it is not one thing but a stack of cooperating systems:
- a message gateway for HAL-prime
- a shared Python tooling layer (`halos/`)
- a macOS computer-use / job-execution layer (`agent/`)

At portfolio level, it is also a proving ground for end-to-end agentic engineering:
- specification precision
- evaluation and quality judgment
- decomposition and orchestration
- failure diagnosis
- trust and guardrail design
- context architecture
- token / cost economics

The repo matters less as “an AI app” and more as an environment for making AI work legibly, reliably, and operationally.

---

## Working definition

Halo is a monorepo for building and operating personal agent infrastructure.

It combines three layers:

```text
halo/
├── gateway/   Node.js message gateway for HAL-prime
├── halos/     Python CLI tooling for work, memory, metrics, mail, cron, reporting
└── agent/     macOS host-side computer-use and job execution
```

The important claim is not that these layers exist.
The important claim is that they compose.

A useful Halo workflow is one where:
- a task is clearly specified
- the right context is loaded
- tools are invoked in a constrained way
- outputs are evaluated
- failures are diagnosable
- the resulting system remains operable by a human, not only by the model that built it

---

## Why this exists

There are many AI demos and many AI wrappers.
There are far fewer systems that visibly answer the operational questions:

- how is agent intent specified?
- how is output evaluated?
- what happens when agents fail?
- what is the trust boundary?
- what context is loaded and why?
- what does this cost and is it worth it?

Halo exists to answer those questions in a concrete personal setting.

It is designed for the kind of work where agents are useful only if they are governable:
- daily briefings
- work tracking
- memory and notes
- email triage
- dashboards and metrics
- message-based assistant workflows
- host-side computer use on macOS

---

## Core thesis

The winning AI systems are not the ones that merely generate plausible language.
They are the ones that can be:
- clearly specified
- evaluated consistently
- decomposed into controllable parts
- debugged when they fail
- governed at the trust boundary
- fed the right context
- justified economically

Halo is built around that thesis.

This means:
- composable CLI tools over opaque app logic
- explicit files and databases over hidden state
- operational legibility over “magic”
- constrained autonomy over theatrical autonomy

---

## Product / system pillars

### 1. Shared operational tooling

The `halos/` package is the center of gravity.
It provides Python CLIs for structured work across domains:
- work tracking
- scheduling
- memory
- reporting
- metrics
- email
- cron
- health and session management

These tools are useful on their own.
They are more useful because they compose through files, SQLite, and shell-friendly outputs.

### 2. Gateway-mediated agent workflows

The `gateway/` layer is HAL-prime’s runtime.
It routes messages from channels like Telegram and Gmail to Claude-powered agents running in isolated environments.

This layer is about:
- message routing
- session handling
- credential proxying
- isolation
- scheduled task execution
- bridging conversation interfaces to tool-using agents

### 3. Host-side macOS execution

The `agent/` layer handles what should not happen inside a container:
- reading the screen
- clicking and typing in GUI apps
- orchestrating tmux sessions
- running host-side jobs through a listen/send model

This is the “hands and eyes” layer.

### 4. Context architecture and memory

Halo is opinionated that context should be structured, not merely accumulated.

That means:
- markdown where prose matters
- YAML where human-readable config matters
- SQLite where queryability matters
- logs where append-only audit trails matter

The repo is therefore also a context architecture project.

### 5. Briefings, reports, and operational visibility

Halo is not only about acting.
It is also about making state legible.

Examples:
- morning briefings
- nightly recaps
- work summaries
- metrics dashboards
- mail summaries
- session / health reporting

A system that cannot explain its own condition is not operationally mature.

---

## Repository structure

```text
halo/
├── agent/              macOS computer-use, tmux orchestration, listen/send job server
├── gateway/            HAL-prime message gateway and runtime
├── halos/              shared Python CLI tooling
├── docs/               specs, analyses, runbooks, reviews, archives
├── memory/             structured notes and reflections
├── cron/               cron job definitions
├── store/              SQLite databases
├── logs/               operational logs
├── queue/              queued work items
└── templates/          templates and scaffolding for related workflows
```

---

## halos modules

Current tooling includes:

| Module | Command | Purpose |
|---|---|---|
| memctl | `memctl` | Structured memory governance |
| nightctl | `nightctl` | Work tracker with Eisenhower matrix and state machine |
| cronctl | `cronctl` | Cron job definitions and crontab generation |
| logctl | `logctl` | Structured log reading and search |
| reportctl | `reportctl` | Periodic digests from the ecosystem |
| agentctl | `agentctl` | LLM session tracking and spin detection |
| briefings | `hal-briefing` | Morning / nightly digests |
| trackctl | `trackctl` | Personal metrics tracker |
| dashctl | `dashctl` | Dashboard / TUI over metrics and work |
| halctl | `halctl` | Session lifecycle and health checks |
| mailctl | `mailctl` | Gmail operations via himalaya |

Several other modules also exist or are being explored in-repo.
The point is less the count than the pattern: narrow tools with explicit surfaces, designed to compose.

---

## Example compositions

### Morning briefing

```text
cronctl
  → hal-briefing morning
    → memctl stats
    → nightctl items
    → trackctl summary
    → mailctl summary
    → log/status data
    → synthesis
    → Telegram delivery
```

### Message-driven assistant workflow

```text
Telegram message
  → gateway routes
  → agent receives context + tools
  → runs halos commands
  → returns result via messaging channel
```

### Host-side agent run on macOS

```text
listen server receives job
  → spawns local Claude Code run in tmux
  → agent uses GUI / terminal host tools
  → trace and result remain inspectable
```

The value is not just that these workflows run.
The value is that they remain understandable.

---

## Storage model

Halo uses a mixed storage model on purpose.

```text
store/         SQLite databases (queryable state)
memory/        Markdown notes and reflections
cron/jobs/     YAML cron definitions
queue/         YAML work items / queues
logs/          JSONL / structured event logs
docs/          specs, analyses, runbooks, reviews
```

Storage principle:
- SQLite for queryable domain state
- YAML for human-readable config and work items
- Markdown for prose, specs, and context
- JSONL / structured logs for append-only operational events

---

## Design principles

- legibility over magic
- auditability over novelty
- evaluation over vibes
- constrained autonomy over theatrical autonomy
- composable tools over monoliths
- explicit context over accidental context
- narrow tools over sprawling abstractions
- real traces over retrospective storytelling

---

## What this repo is good for

Halo is especially useful if you care about:
- personal AI operations
- agentic workflows with real tools
- CLI-first life / work systems
- host-side computer use on macOS
- briefings, dashboards, and operational visibility
- building portfolio evidence for AI engineering competence

It is less well described as:
- a polished SaaS product
- a single-purpose AI app
- a generic starter template

---

## Quick start

### Requirements

- macOS or Linux for most of the repo
- macOS specifically for `agent/` computer-use tooling
- Python 3.11+
- `uv`
- Node.js 20+
- Docker for gateway/container workflows
- Claude Code for agent-oriented flows

### Install

```bash
git clone https://github.com/rickhallett/halo.git
cd halo

# Python tooling
uv sync

# Gateway
cd gateway
npm install
npm run build
cd ..
```

### Basic use

```bash
# dashboard
uv run dashctl

# add work item
uv run nightctl add --title "Ship it" --quadrant q1

# inspect metrics
uv run trackctl summary

# regenerate/install cron
uv run cronctl install --execute
```

### Gateway use

```bash
cd gateway
npm run dev
```

### Agent listen/send use

```bash
cd agent
just listen

# from another shell
just send "Open Safari and take a screenshot"
```

---

## Documentation

The repo’s deeper documentation lives in `docs/`.

Directory semantics:
- `docs/d1/` — working reference, runbooks, guides, journals
- `docs/d2/` — specs, analyses, design records, reviews
- `docs/d3/` — archive

If you want the system’s design intent, start in `docs/d2/`.
If you want to operate something, start in `docs/d1/`.

---

## Current status

Halo is a living system, not a frozen product.
Some parts are actively used day to day; some exist as infrastructure or portfolio scaffolding; some are experiments that may later be promoted, merged, or retired.

That is intentional.
The repo is both:
- an operational environment
- a research / portfolio environment for disciplined agentic engineering

---

## License

MIT
