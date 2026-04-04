---
title: "journalctl — qualitative journal module + roundtable consolidation"
category: spec
status: draft
created: 2026-04-04
---

# journalctl Spec

## Problem

The roundtable advisors operate on sparse quantitative data (trackctl metrics, nightctl backlog). There is no qualitative signal — no record of how things felt, why plans diverged from reality, what patterns are emerging in behaviour. The advisors can't see the space between the numbers.

Additionally, the roundtable schedule is scattered throughout the day (individual advisor crons), which fragments attention rather than bookending the day cleanly.

## Solution

Three pieces:

1. **journalctl** — new halos module for unstructured temporal entries with LLM-synthesised sliding window summaries
2. **Roundtable consolidation** — collapse advisor crons into two sessions (morning + evening)
3. **Advisor integration** — journal window as standard context for all advisors

## 1. journalctl Module

### Storage

SQLite at `store/journal.db`. Same pattern as trackctl.

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',       -- comma-separated
    source TEXT NOT NULL DEFAULT 'text', -- text | voice | agent
    mood TEXT NOT NULL DEFAULT '',       -- optional freeform
    energy TEXT NOT NULL DEFAULT ''      -- optional freeform
);
CREATE INDEX idx_journal_timestamp ON entries(timestamp);
```

No summary column in the DB. Summaries are cached artifacts, not source data.

### CLI Surface

```bash
# Write
journalctl add "felt heavy today, skipped pistol squats, knee grumbling"
journalctl add --tags movement,body --source voice "transcribed voice text"
journalctl add --mood low --energy 3 "didn't sleep well, dragging"

# Read
journalctl recent                    # last 7 days, raw entries
journalctl recent --days 3           # last 3 days
journalctl recent --tags movement    # filtered

# Summaries (LLM-synthesised, content-hash cached)
journalctl window                    # 7-day sliding window summary
journalctl window --days 14          # custom range
journalctl window --months 1         # last 30 days
journalctl window --no-cache         # force regeneration

# Machine-readable
journalctl recent --json
journalctl window --json
```

### Sliding Window Summaries

`journalctl window` produces an LLM-synthesised narrative summary of recent journal entries. Designed for injection into advisor context.

**Synthesis prompt goals:**
- Compress N entries into a coherent narrative paragraph (~300-500 tokens output)
- Highlight: what happened, what's in progress, what might be coming
- Surface: plan↔actuality drift, recurring themes, mood/energy trends
- Note: discrepancies between stated intentions and actual behaviour
- Flag: patterns that might indicate habitual compulsion, aversion, or attachment

**Standard windows:**
- 7-day window (± a few days around today) — the default, captures weekly rhythm
- 30-day window — broader arc, slower-moving patterns

### Content-Hash Caching

The cache invalidates when journal content changes. No TTL, no cron regeneration.

```
store/journal-cache/
  window-7d.md          # cached 7-day summary (plain markdown)
  window-7d.hash        # SHA-256 of the entries that produced it
  window-30d.md         # cached 30-day summary
  window-30d.hash
```

**Invalidation logic:**

```python
def _content_hash(entries: list[dict]) -> str:
    """SHA-256 of all entry IDs + timestamps + text in the window."""
    ...

def window(days: int = 7, no_cache: bool = False) -> str:
    entries = _entries_in_range(days)
    current_hash = _content_hash(entries)
    cached_hash = _read_hash_file(days)
    
    if not no_cache and current_hash == cached_hash:
        return _read_cached_summary(days)
    
    summary = _synthesise_window(entries)
    _write_cache(days, summary, current_hash)
    return summary
```

**Cost model:**
- Morning roundtable (07:00) is typically the first reader → pays one LLM call per stale window
- Evening roundtable (20:00) → cache hit if no new entries since morning, one call if there are
- Individual advisor summons during the day → cache hit
- Worst case: 2 LLM calls/day for 7d window, 1/day for 30d window
- ~500 input tokens (entries) + ~300 output tokens per synthesis ≈ negligible cost

### Module Structure

```
halos/journalctl/
  __init__.py
  cli.py          # argparse CLI
  store.py        # SQLite CRUD
  window.py       # sliding window synthesis + caching
  config.py       # paths, defaults
```

Entry point: `journalctl` (console_script in pyproject.toml).

### Design Decisions

- **Not memctl.** memctl is structured knowledge with governed lifecycle (scores, pruning, backlinks, one claim per note). Journal entries are temporal experience — messy, subjective, sequential, multi-claim. Different storage, different lifecycle.
- **Never pruned.** Journal entries are permanent record. The cache layer handles compression for context injection.
- **No mandatory fields beyond raw_text.** Mood, energy, tags are optional. Low friction is the priority — if adding metadata makes someone skip the entry, the metadata isn't worth it.
- **Source field for provenance.** Distinguishes typed vs voice vs agent-generated entries for downstream analysis.

## 2. Roundtable Consolidation

### Current State

Advisors have individual cron jobs scattered throughout the day. This fragments attention and produces multiple small Telegram messages at unpredictable times.

### Target State

Two consolidated sessions per day:

| Session | Time  | Format |
|---------|-------|--------|
| Morning | 07:00 | All advisors, Plutarch routes, single Telegram message |
| Evening | 20:00 | All advisors, Plutarch routes, single Telegram message |

### How It Works

Each session is a **single LLM synthesis call**:

1. Gather data:
   - `journalctl window` (7d, cached)
   - `journalctl window --months 1` (30d, cached)
   - `dashctl --text` (trackctl metrics)
   - `nightctl list --status open` (backlog)
2. Load all advisor personas (static text, ~2k tokens total)
3. Plutarch acts as dramaturg: decides who speaks based on what the data shows
4. Advisors who have nothing to say stay silent
5. Output: single formatted message, ≤2000 chars, delivered to Telegram

**Token budget per session:**
- Journal windows: ~800 tokens (cached summaries)
- Metrics/backlog: ~400 tokens
- Advisor personas: ~2000 tokens
- Output: ~800 tokens
- Total: ~4k in, ~800 out — one call, twice daily

### Cron Changes

Remove individual advisor cron jobs. Add two:

```yaml
# cron/jobs/roundtable-morning.yaml
- name: roundtable-morning
  schedule: "0 7 * * *"
  command: hal-briefing roundtable --session morning

# cron/jobs/roundtable-evening.yaml  
- name: roundtable-evening
  schedule: "0 20 * * *"
  command: hal-briefing roundtable --session evening
```

Individual advisors can still be summoned on-demand via "summon X" in Telegram. The consolidated roundtable doesn't replace ad-hoc summons — it replaces the scattered cron schedule.

## 3. Advisor Integration

### Persona Updates

Each `data/advisors/<name>/persona.md` gets a new integration:

```markdown
## Integrations
...existing trackctl/nightctl commands...
- `uv run journalctl window` — 7-day qualitative context (read before speaking)
- `uv run journalctl window --months 1` — monthly arc
```

### Profile Updates

Advisor profiles can reference journal patterns discovered during sessions:

```markdown
## Patterns (from journal)
- Tends to skip movement on days after poor sleep
- Energy dips correlate with inbox overload
- Plans ambitious mornings but actual output clusters in afternoons
```

These are written by advisors during sessions, not auto-generated.

## 4. Gateway Voice Pipeline (Future)

Not built in this phase. Documented here for completeness.

When implemented, the gateway needs to:
1. Detect Telegram voice messages (`.ogg` audio file)
2. Download via Telegram Bot API (`getFile` → HTTPS download)
3. Transcribe via mlx-whisper (local, ~6s for 60s audio on Mac Mini)
4. Either:
   a. Inject transcript as message content (transparent to downstream), or
   b. Call `journalctl add --source voice "transcript"` directly

Option (a) is more general — any voice message becomes text. Option (b) is journal-specific. Recommend (a) with journal routing handled by HAL-prime's prompt.

Until then, voice notes can be transcribed manually or Kai can type entries. The system works without voice — voice just lowers friction.

## Build Order

1. **journalctl module** — store, CLI, window synthesis, caching
2. **Advisor integration** — update personas with journal integrations
3. **Roundtable consolidation** — new briefing subcommand, cron migration
4. **Voice pipeline** — gateway modification (separate task, needs gateway access)

## Dependencies

- Python 3.11+, uv, SQLite
- Claude CLI (`claude -p`) for window synthesis (same as diary.py)
- Existing halos infrastructure: console_scripts pattern, store/ directory, briefings framework
