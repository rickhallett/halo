# halOS Module Registry

Operational modules that comprise the HAL agent operating layer.

| Module | Binary | Purpose | Status |
|--------|--------|---------|--------|
| memctl | tools/memctl/memctl | Structured memory: atomic notes, YAML schema, hash-verified index, pruning | Active |
| nightctl | tools/nightctl/nightctl | Overnight batch jobs: deferred execution, windowed scheduling, run records | Active |
| cronctl | tools/cronctl/cronctl | Cron management: YAML job definitions, crontab generation, enable/disable | Active |
| todoctl | tools/todoctl/todoctl | Backlog tracking: prioritised YAML items, status workflow, blocking | Active |

## Shared Design Principles

All modules follow the same conventions:
- Filesystem-first, no database
- YAML schema with controlled vocabulary
- CLI-driven writes, never direct file edits
- Config at repo root ({module}.yaml)
- Derived manifests/indices are rebuildable
- Archive not delete
- --dry-run available on all mutating commands
- --json for machine-readable output
