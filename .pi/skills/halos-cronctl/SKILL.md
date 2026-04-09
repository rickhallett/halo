---
name: halos-cronctl
description: "Manage the macOS crontab for scheduled halos jobs — briefings, advisor check-ins, health checks, overnight execution. Use when viewing, editing, or installing cron schedules."
---

# cronctl — Cron Management

All commands run from `/Users/mrkai/code/halo` using `uv run cronctl`.

## Commands

```bash
uv run cronctl show                     # display current schedule
uv run cronctl install --execute        # regenerate crontab from job definitions and install
uv run cronctl list                     # list job definitions
```

## Job Definitions

Jobs are defined in `cron/jobs/*.yaml`. Each job specifies:
- Schedule (cron expression)
- Command to run
- Enabled flag
- Description

## Current Schedule

| Time | Job | Purpose |
|------|-----|---------|
| 05:45 | nightctl summary | Overnight agent-job summary |
| 06:00 | morning briefing | Daily morning digest |
| 07:00 | Musashi check-in | Movement + zazen coaching |
| 09:00 | Karpathy check-in | Craft + AI engineering coaching |
| hourly | fleet health | Health check with auto-heal |
| 19:45 | Medici check-in | Financial + time economics review |
| 20:00 | Medici check-in | Financial review |
| 20:15 | Machiavelli check-in | Strategic review |
| 20:30 | Gibson check-in | Futures + pipeline review |
| 21:00 | nightly recap | Evening recap |
| 21:15 | dear diary | HAL autonomous reflection |

## Adding a New Cron Job

Create a YAML file in `cron/jobs/`:

```yaml
name: my-job
schedule: "0 8 * * *"    # 08:00 daily
command: "uv run hal-briefing morning"
enabled: true
description: "Morning briefing"
```

Then install: `uv run cronctl install --execute`

## macOS Cron Notes

- cronctl automatically adds PATH and HOME headers for macOS compatibility
- PATH includes `/opt/homebrew/bin` and `~/.local/bin`
- Jobs run with minimal environment — all paths must be absolute or handled by the PATH header
- To verify cron is running: `crontab -l`
- To check cron output: `grep CRON /var/log/system.log` or check syslog

## Pitfalls

- Always regenerate with `cronctl install --execute` — don't hand-edit crontab.
- Old schedule files may reference wrong paths (e.g., /home/mrkai/code/nanoclaw from Linux). Always regenerate from the correct machine.
- `uv` and `claude` are absent from cron's default PATH — cronctl handles this.
