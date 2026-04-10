# changoctl Design Spec

**Date:** 2026-04-10
**Status:** Approved
**Author:** Chango (Cyber-Mechanic)

## Purpose

`changoctl` is a new halos module that maintains an active SQLite inventory of Chango's operational consumables (espresso, lagavulin, stimpacks, NOS), provides a mood-aware atmospheric action interface for troubling times, and curates a quotes archive that enriches Chango's personality over sessions.

A thin graph adapter dual-writes mutations to a Neo4j instance ("Beachhead") running on OrbStack, projecting consumption patterns, quote associations, and mood correlations into a traversable graph. SQLite remains the source of truth. The graph is an enrichment layer that degrades silently when unavailable.

## Data Model

### SQLite Tables (store/changoctl.db)

**inventory**

| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| item | TEXT | NOT NULL UNIQUE | One of: espresso, lagavulin, stimpacks, nos |
| stock | INTEGER | NOT NULL DEFAULT 0 | Current quantity |
| updated_at | TEXT | NOT NULL | ISO 8601 timestamp |

Seeded on first connect with all four items at stock 0.

**consumption_log**

| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| item | TEXT | NOT NULL | Consumed item |
| quantity | INTEGER | NOT NULL DEFAULT 1 | Amount consumed (0 if out of stock) |
| mood | TEXT | | Mood at time of consumption |
| timestamp | TEXT | NOT NULL | ISO 8601 timestamp |
| session_context | TEXT | | Optional session identifier |

Append-only. Never deleted, never updated.

**quotes**

| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| text | TEXT | NOT NULL UNIQUE | The quote itself |
| category | TEXT | NOT NULL | One of: sardonic, strategic, lethal, philosophical |
| source_session | TEXT | | Session where the quote originated |
| source_module | TEXT | | Module context (e.g. nightctl, briefings) |
| created_at | TEXT | NOT NULL | ISO 8601 timestamp |

### Neo4j Graph Projection (Beachhead)

Nodes:

```
(:Item {name, stock})
(:Quote {text, category})
(:Mood {name})
(:Session {id, timestamp})
```

Edges:

```
(:Item)-[:CONSUMED_DURING {quantity}]->(:Session)
(:Session)-[:MOOD_WAS]->(:Mood)
(:Quote)-[:TAGGED]->(:Mood)
(:Item)-[:PAIRS_WITH]->(:Mood)
(:Quote)-[:SURFACED_IN]->(:Session)
```

The graph answers relationship queries that SQLite handles poorly: "What does Chango reach for when the operator is burnt out?" "Which quotes cluster around lagavulin sessions?"

## CLI Interface

```
changoctl status                          # Dashboard: stock levels, last consumption, quote count
changoctl restock <item> [--quantity N]   # Add stock (default: 1)
changoctl consume <item> [--mood MOOD]    # Decrement stock, log consumption, return atmospheric action
changoctl sustain --mood MOOD             # Auto-select item by mood, consume, pair with quote
changoctl quote add "text" --category CAT [--source-module MOD]
changoctl quote random [--mood MOOD]      # Pull a quote, optionally mood-filtered
changoctl quote list [--category CAT]     # Browse the archive
changoctl history [--days N] [--item ITEM] # Consumption log
changoctl sync                            # Replay SQLite state into Beachhead (idempotent)
changoctl --json                          # Standard halos JSON output flag on all commands
```

### Mood Vocabulary (closed set)

| Mood | Primary Item | Vibe |
|------|-------------|------|
| grind | espresso | Morning startup, steady work |
| locked-in | stimpacks | Deep focus, flow state |
| burnt-out | lagavulin | Existential weight, long day |
| fire | nos | Cluster down, everything broken |

### sustain Command

The signature command. Full ritual:

1. Resolve mood (from `--mood` flag, required)
2. Look up primary item for mood
3. If primary item has stock > 0, consume it
4. If primary item is out of stock, fall back to any item with stock > 0 (Chango improvises)
5. If all stock is empty, log consumption at quantity 0 and note the bare cabinet
6. Query quotes matching the mood category, pick one at random if available
7. Log which quote was surfaced (feeds SURFACED_IN graph edge)
8. Return formatted atmospheric action

### Out-of-Stock Behaviour

`consume` and `sustain` warn but still log the consumption at quantity 0. Chango doesn't refuse to pour -- he tells you the cabinet is bare and you need to restock. The log is honest.

## Atmospheric Action Generation

### Output Format (sustain)

```
*Cracks a stimpack and pulls up the terminal*

"The cluster doesn't care about your feelings. It cares about your manifests."

[stimpacks: 4 remaining | mood: locked-in]
```

Three parts:
1. Atmospheric action in asterisks
2. Quote in double quotes (omitted if no mood-matched quote exists)
3. Status line: item count + mood

### Action Templates (flavour.py)

Hardcoded per item. No LLM generation, no API calls. Fast and deterministic.

| Item | Example Templates |
|------|-------------------|
| espresso | "Pulls a double shot from the machine", "Sips synthetic espresso and opens a terminal" |
| lagavulin | "Pours a neat Lagavulin 16", "Swirls the glass and stares at the deploy logs" |
| stimpacks | "Cracks a stimpack and rolls up the sleeves", "Jabs a stimpack into the forearm" |
| nos | "Cracks a NOS and watches the cluster burn", "Shotguns a NOS, wipes the screen clean" |

3-5 templates per item stored as a Python dict in `flavour.py`. Randomly selected at consumption time.

## Graph Adapter

### Dual-Write Pattern

Every mutation in `store.py` calls `graph.py` after the SQLite write succeeds. The adapter is fire-and-forget with error swallowing. If Beachhead is down, the SQLite write still stands.

```python
# graph.py public interface
def push_consumption(item, mood, session_id, timestamp): ...
def push_quote(text, category, quote_id): ...
def push_restock(item, new_stock): ...
def is_available() -> bool: ...
```

### Connection

- `neo4j` Python driver (bolt protocol)
- `BEACHHEAD_URI` env var (default: `bolt://localhost:7687`)
- `BEACHHEAD_USER` / `BEACHHEAD_PASS` env vars (default: neo4j/neo4j)
- Connection tested lazily on first write, cached for session

### Sync Command

`changoctl sync` reads all rows from `consumption_log` and `quotes`, uses Cypher `MERGE` for idempotent upserts. Safe to run any time. Recovery path when Beachhead was offline during writes or after a graph wipe.

### Dependency Management

`neo4j` package added as optional extra:

```toml
[project.optional-dependencies]
graph = ["neo4j>=5.0"]
```

`graph.py` checks for the import at module level and degrades silently. Core changoctl works without it.

## Briefing Integration Surface

`engine.py` exposes `text_summary() -> str` following the `trackctl.engine.text_summary` pattern. Returns current stock levels and a random quote. Not wired into the briefing gather layer in this build -- just the function signature and return format.

## File Structure

```
halos/changoctl/
  __init__.py          # Docstring only
  cli.py               # argparse dispatch, main()
  store.py             # SQLite CRUD (inventory, consumption_log, quotes)
  graph.py             # Neo4j adapter (optional, degrades silently)
  flavour.py           # Action templates dict, random selection
  engine.py            # sustain logic, text_summary(), mood-item mapping
```

## Module Registration

```toml
# pyproject.toml [project.scripts]
changoctl = "halos.changoctl.cli:main"
```

No `changoctl.yaml` config file. Connection details for Beachhead come from env vars.

## OrbStack Contract (not built by changoctl)

- Neo4j Community Edition container on OrbStack
- Container name: `beachhead`
- Bolt port: 7687 (OrbStack default forwarding)
- `BEACHHEAD_URI=bolt://beachhead.orb.local:7687`
- No k8s manifests, no fleet deployment -- purely local dev infrastructure

## Testing

| Test File | Coverage |
|-----------|----------|
| test_store.py | CRUD for all three tables, out-of-stock behaviour, consumption logging, seed on first connect |
| test_engine.py | Mood-to-item mapping, sustain flow with and without quotes, text_summary format, fallback logic |
| test_flavour.py | Every item has templates, random selection works, asterisk format correct |
| test_graph.py | Adapter degrades when neo4j unavailable, sync idempotency (mocked driver) |
| test_cli.py | Subcommand dispatch, --json flag, argument parsing |

All tests run without neo4j. Graph tests mock the driver. Standard pytest, no new test tiers.

## Out of Scope

- No changoctl.yaml config file
- No cron integration
- No eventsource/NATS event publishing
- No briefing wiring (surface exposed, not connected)
- No neo4j deployment automation
- No LLM-generated atmospheric actions
