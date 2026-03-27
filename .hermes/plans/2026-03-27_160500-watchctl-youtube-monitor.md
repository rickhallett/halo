# watchctl — YouTube Channel Monitor with LLM-as-Judge Triage

**Date:** 2026-03-27
**Status:** Plan — not yet executed
**Pit domains exercised:** All 7

## Goal

Cron-driven pipeline that watches YouTube channels, pulls new video
transcripts, evaluates them via a codified rubric (LLM-as-judge),
and writes structured reports into the Obsidian vault. Daily Telegram
digest of new reports.

## Architecture

```
watchctl.yaml (channels + config)
        │
        ▼
   watchctl scan          ← cron, daily
        │
        ├─ 1. fetch_new_videos()     ← YouTube RSS/API per channel
        │     compare against store/watch.db (seen videos)
        │
        ├─ 2. fetch_transcript()     ← youtube-transcript-api
        │     for each new video
        │
        ├─ 3. evaluate()             ← LLM-as-judge against rubric.yaml
        │     structured JSON output validated against schema
        │
        ├─ 4. write_obsidian()       ← markdown note per video
        │     frontmatter, tags, wikilinks, dataview fields
        │
        ├─ 5. write_digest()         ← daily summary
        │     Telegram delivery via briefings.deliver pattern
        │
        └─ 6. mark_seen()            ← update store/watch.db
```

## Config: watchctl.yaml

```yaml
# Root-level config
obsidian_vault: "~/Documents/vault/main"
output_dir: "code/youtube-monitor"        # relative to vault
rubric: "./rubrics/watchctl-triage.yaml"  # relative to halo root
db_path: "./store/watch.db"

# LLM config
model: "claude-sonnet-4-5-20250514"       # cheap/fast for eval
max_transcript_chars: 80000               # truncate beyond this

# Delivery
telegram_enabled: true

# Channels
channels:
  - name: "Theo (t3.gg)"
    youtube_id: "UCbRP3c757lWg9M-U7TyEkXA"
    tags: ["engineering", "product"]

  - name: "Fireship"
    youtube_id: "UCsBjURrPoezykLs9EqgamOA"
    tags: ["engineering", "news"]

  - name: "Wes Roth"
    youtube_id: "UC_bric...TBD"
    tags: ["ai-news"]

  - name: "CJ"
    youtube_id: "...TBD"
    tags: ["engineering", "practical"]

  - name: "Jacob Bank / Relay"
    youtube_id: "...TBD"
    tags: ["agents", "product"]
```

We'll resolve the actual YouTube channel IDs during implementation.

## Config: rubrics/watchctl-triage.yaml

```yaml
name: "engineering-relevance"
version: 1
description: >
  Evaluate YouTube video content for signal density, actionable
  insights, and relevance to agentic engineering, software
  development, and AI tooling.

criteria:
  signal_density:
    weight: 3
    description: "Ratio of novel/actionable information to filler, hype, and repetition"
    scale: [1, 5]

  actionability:
    weight: 3
    description: "Can specific techniques, tools, or patterns be extracted and applied?"
    scale: [1, 5]

  technical_depth:
    weight: 2
    description: "Does it go beyond surface-level takes into implementation detail?"
    scale: [1, 5]

  relevance:
    weight: 2
    description: "How relevant to our domains: agentic engineering, dev tooling, AI workflows, career"
    scale: [1, 5]

output_schema:
  scores:          # per-criterion score + one-line justification
  overall_rating:  # 1-5 stars, weighted
  verdict:         # REQUIRED | WATCH | SKIM | SKIP
  summary:         # 5-10 sentence overview
  goodies:         # list of {tier: HIGH|MEDIUM|LOW, item: string}
  tags:            # suggested obsidian tags
  related_notes:   # suggested wikilinks if recognisable topics
```

## Obsidian Note Format

```markdown
---
title: "{{video_title}}"
channel: "{{channel_name}}"
date: {{publish_date}}
evaluated: {{eval_date}}
rating: {{overall_rating}}
verdict: {{verdict}}
tags: [youtube-monitor, {{channel_tag}}, {{...suggested_tags}}]
url: "{{video_url}}"
duration: {{duration}}
---

# {{video_title}}

**Channel:** {{channel_name}} | **Rating:** {{stars}} | **Verdict:** {{verdict}}
**URL:** {{url}}

## Summary

{{summary}}

## Evaluation

| Criterion | Score | Note |
|-----------|-------|------|
{{#each scores}}
| {{name}} | {{score}}/5 | {{justification}} |
{{/each}}

## Extractable Goodies

### High Value
{{#each goodies where tier=HIGH}}
- {{item}}
{{/each}}

### Medium Value
{{#each goodies where tier=MEDIUM}}
- {{item}}
{{/each}}

### Low Value
{{#each goodies where tier=LOW}}
- {{item}}
{{/each}}

## Related
{{#each related_notes}}
- [[{{note}}]]
{{/each}}
```

## Module Structure

```
halos/watchctl/
├── __init__.py          # docstring
├── cli.py               # argparse: scan, list, channels, report
├── config.py            # load watchctl.yaml
├── feed.py              # YouTube RSS feed parsing (no API key needed)
├── transcript.py        # youtube-transcript-api wrapper
├── evaluate.py          # LLM-as-judge: rubric loading, prompt, schema validation
├── obsidian.py          # note generation with frontmatter + wikilinks
├── digest.py            # daily digest formatter + telegram delivery
├── store.py             # SQLite: seen videos, evaluation results, cost tracking
└── rubric.py            # rubric YAML loader + weighted score computation
```

Plus:
- `watchctl.yaml` at halo root
- `rubrics/watchctl-triage.yaml` at halo root
- `tests/test_watchctl/` with tests per module

## CLI Commands

```bash
watchctl scan                  # run full pipeline (fetch → evaluate → write)
watchctl scan --dry-run        # show what would be evaluated, don't write
watchctl scan --channel "Theo" # single channel only
watchctl channels              # list configured channels
watchctl list [--days N]       # list recent evaluations
watchctl report <video-id>     # re-display a past evaluation
watchctl stats                 # cost tracking, score distributions
```

## Pit Domain Coverage

### 1. Specification Precision
- Rubric YAML is the run contract: explicit criteria, weights, scales
- Output schema defines exactly what the evaluator must produce
- Channel config has typed fields, not free text

### 2. Evaluation and Quality Judgment
- LLM-as-judge with codified rubric, not vibes
- Weighted scoring with per-criterion justification
- Score distributions tracked in store.db over time
- Rubric is versioned — changes are traceable

### 3. Decomposition and Orchestration
- Pipeline is 6 discrete stages, each independently testable
- LLM is only invoked at stage 3 (evaluate) — deterministic everywhere else
- CJ's principle: deterministic where possible, LLM where judgment is needed

### 4. Failure Pattern Recognition
- Transcript unavailable → logged, skipped, noted in digest
- LLM output fails schema validation → retry once, then log failure
- Rate limiting → backoff + partial completion
- Failures classified in store.db with taxonomy: TRANSCRIPT_UNAVAILABLE,
  EVAL_SCHEMA_INVALID, EVAL_TIMEOUT, FEED_ERROR, DELIVERY_FAILED

### 5. Trust and Guardrail Design
- LLM output validated against JSON schema before writing to vault
- Blast radius: worst case is a bad markdown note (low stakes)
- No destructive operations — append-only to vault and DB
- Dry-run mode for all operations

### 6. Context Architecture
- Persistent context: channel config, rubric, scoring history
- Run-local context: individual video transcript
- Clean separation — rubric doesn't leak between videos
- Rubric versioning means context provenance is traceable

### 7. Token and Cost Economics
- Use sonnet for evaluation (cheap), not opus (expensive)
- Track tokens + cost per evaluation in store.db
- Transcript truncation at configurable limit
- `watchctl stats` surfaces cost/quality data
- Future: compare sonnet vs haiku evaluations for cost/quality tradeoff

## Implementation Order

1. Scaffold module structure + config loader + pyproject.toml entry
2. feed.py — YouTube RSS parsing (no API key, just channel XML feeds)
3. transcript.py — wrap youtube-transcript-api (reuse skill script logic)
4. store.py — SQLite schema (seen_videos, evaluations, failures, costs)
5. rubric.py — YAML loader + weighted score computation
6. evaluate.py — LLM prompt construction, call, schema validation
7. obsidian.py — note template rendering + frontmatter
8. digest.py — daily summary + Telegram delivery
9. cli.py — argparse wiring
10. Tests for each module
11. Cron integration via cronctl
12. Resolve actual YouTube channel IDs

## Testing Strategy

Per CJ's rubric pattern:
- Unit tests for feed parsing, rubric loading, score computation,
  schema validation, obsidian note rendering
- Integration test with a fixture transcript → full pipeline
- Schema validation tests: malformed LLM output must be caught
- Failure taxonomy tests: each failure type is correctly classified

## Risks and Open Questions

- YouTube RSS feeds may not include all videos (shorts, unlisted).
  Mitigation: RSS is good enough for public uploads; revisit if gaps.
- Transcript availability varies. Some channels disable them.
  Mitigation: log + skip, surface in digest.
- Rubric drift — criteria may need updating as interests evolve.
  Mitigation: rubric is versioned YAML, easy to iterate.
- Cost: ~5 videos/day at sonnet rates is negligible (<$0.10/day).
- Obsidian vault path has spaces — all file operations must quote.

## Cron

```
# Daily at 07:00 UTC (before morning briefing)
0 7 * * * cd /Users/mrkai/code/halo && uv run watchctl scan 2>&1 | uv run logctl ingest --source watchctl
```
