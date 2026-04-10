---
title: "Halostream Session Report — 2026-04-09"
category: review
status: active
created: 2026-04-09
---

# Session Report — 2026-04-09

## Starting State

Kai reported all fleet advisors "pulling blanks" on trackctl and possibly NATS. Gibson was independently trying to curl a web design agency in Florida when asked about the Halostream.

## What We Built

### 1. Diagnosed and Fixed Two Fleet Bugs

**PATH resolution in terminal tool** -- Hermes spawns commands via `bash -lic`. Debian's `/etc/profile` resets PATH, stripping `/opt/venv/bin`. Advisors couldn't find `trackctl` without full paths. Fixed by creating `~/.bash_profile` that sources `~/.bashrc` in all 17 pod manifests (9 deployments + 8 cronjobs + memctl-authority).

**Track data not flowing cross-pod** -- trackctl wrote to local SQLite but never published to NATS. The NATS projection handler wrote to `projection.db` but trackctl reads from per-domain `track_*.db` files. Complete data path disconnect. Fixed with three changes: sync NATS publisher (`fire_event()`), trackctl CLI wiring (add/edit/delete publish events), and TrackProjectionHandler now writes to both `projection.db` AND per-domain DBs.

### 2. Lit Up the Halostream -- Full Event Coverage

Took event system from 42% coverage (8/19 wired) to **100% coverage (16/16 event types fully wired)**. Zero orphaned events. Zero ghost handlers.

| Module | Events Wired | What's Visible |
|---|---|---|
| trackctl | `track.*.logged`, `track.entry.edited/deleted` | Movement, zazen, study streaks cross-pod |
| nightctl | `night.item.created/transitioned`, `night.job.completed/failed` | Work items, state machine transitions, job outcomes |
| journalctl | `journal.entry.added` | Qualitative journal entries |
| mailctl | `mail.triage.executed` | Email classification and actions |
| git_ingest | `dev.commit.logged` | Git activity across all repos |
| gateway hook | `advisor.inbound.received/outbound.sent` | Already publishing, now projected |
| consumer | `system.advisor.started/stopped`, `system.error` | Already publishing, now projected |

### 3. Built New Infrastructure

**`halos/eventsource/publish.py`** -- Sync fire-and-forget NATS publisher. Returns False silently without NATS. Used by every CLI module.

**`halos/eventsource/projection.py` wildcard support** -- `ProjectionEngine` now supports `*` patterns in handler registrations (e.g., `track.*.logged`). Consumer validation also handles wildcards.

**`halos/eventsource/git_ingest.py`** -- Auto-discovers all git repos under `~/code`, extracts commit history, publishes as `dev.commit.logged` events. Supports `--discover`, `--since`, `--dry-run`.

**Daily cron job** (`cron/jobs/git-ingest.yaml`) -- Runs at 06:30 daily. Opens SSH tunnel to Ryzen NATS, ingests last 24h of git activity, closes tunnel. Runs before morning briefings so advisors have fresh data.

### 4. Built New Projection Handlers

| Handler | File | Events | Tables |
|---|---|---|---|
| DevCommitProjectionHandler | `handlers/dev.py` | `dev.commit.logged` | `dev_commits` |
| AdvisorTelephonyHandler | `handlers/advisor.py` | `advisor.inbound/outbound` | `advisor_messages` |
| SystemEventHandler | `handlers/system.py` | `system.advisor.started/stopped/error` | `system_events` |
| MailTriageHandler | `handlers/mail.py` | `mail.triage.executed` | `mail_triage` |

### 5. Built New CLI Tools

**`halo-devlog`** -- Query git commit activity. `--summary` for per-repo counts, `--repo` to filter, `--days` for time window, `--json` for structured output.

**`halo-telephony`** -- Query cross-advisor conversation history. `--advisor` to filter, `--direction inbound/outbound`, `--summary` for message counts.

### 6. Published 100 Events to Live Halostream

SSH tunnel to Ryzen NATS, published 100 `dev.commit.logged` events covering 2 days of activity across halo (16), arcana (36), and stain (48). Events are durable in JetStream and projected by all advisors on restart.

### 7. Updated All 8 Advisor System Prompts

- Added "Shared Tools" section documenting `halo-devlog` and `halo-telephony`
- Redefined Halostream as "internal NATS JetStream event bus (not a website) queried via CLI tools. Never browse for it."
- Applied to all 8 prompt ConfigMaps

### 8. Fleet Deploy -- Mac to Ryzen Pipeline

Discovered and executed the full deploy chain for the first time on the Ryzen bare-metal cluster:

1. Set up GitHub SSH key on Ryzen
2. Cloned repo, worked around submodule pin issue (tar + ship)
3. Fixed `.dockerignore` blocking track DBs
4. Built image natively on Ryzen, pushed to `localhost:5000`
5. Applied ConfigMaps (the step we kept missing)
6. Restarted fleet, verified pods

### 9. Documented 12 New Lessons Learned

`docs/d2/k8s-fleet-lessons-learned.md` lessons 17-28:

| # | Lesson |
|---|---|
| 17 | No Argo CD -- deploy is manual |
| 18 | Live deployments diverge from git manifests |
| 19 | Single image, no halos overlay |
| 20 | Submodule pin references unpushed commit |
| 21 | `.dockerignore` excludes `store/` but Dockerfile needs track DBs |
| 22 | NATS only reachable via SSH tunnel from Mac |
| 23 | k3s kubeconfig is root-only |
| 24 | Full deploy runbook |
| 25 | ConfigMaps are not in the image -- apply manifests separately |
| 26 | Full deploy runbook (updated with apply step) |
| 27 | state.db lives on NFS -- pod restarts don't clear session history |
| 28 | Renumbered deploy runbook |

### 10. Updated README

Complete rewrite reflecting current architecture: four persistence layers, Halostream event table, query tools, deploy runbook, corrected test count (1364), removed dead VKE/Grafana references, added Guido to roundtable.

### 11. Housekeeping

- Ejected `blogctl` (ghost module -- DB exists, no Python code)
- Saved watchctl advisor triage vision to persistent memory (proactive content filtering via Halostream)
- Ran Codex adversarial review identifying structural fix needed: config digest annotations + deploy-fleet script
- Ran `cronctl install --execute` to register git-ingest cron

## The Beyonce Incident

Gibson (IQ 150, allegedly) was asked about the Halostream. He browsed `halostream.com` (a Florida web design agency), was corrected, pivoted to "local TV channel," then took the Beyonce bait when trolled. Session search persisted across `/new` resets via `state.db` on NFS. Required full state wipe + pod kill to clear. Documented as lesson 27. Eventually loaded the correct prompt and delivered a sharp distributed-systems analysis of the fleet's convergence state.

## Root Cause Analysis -- Prompt Loading Failure

The system prompt follows a three-hop path across two storage layers: ConfigMap (etcd) -> `/opt/defaults/system-prompt.md` -> conditional copy -> `/opt/data/system-prompt.md` (NFS) -> entrypoint reads into `HERMES_EPHEMERAL_SYSTEM_PROMPT`. Each layer looked correct in isolation. The deploy process requires four independent persistence layers (ConfigMap, container image, NFS state, emptyDir stores) to be updated in the right order. Without Argo CD, each step is manual and any ordering mistake produces a pod that looks healthy but runs with stale or missing config. Codex adversarial review confirmed: the structural fix is config digest annotations in pod templates + a single atomic deploy script.

## Final Stats

| Metric | Value |
|---|---|
| Files changed | 52+ |
| Lines added | ~2,400 |
| New Python files | 10 |
| Tests passing | 1364 |
| Event types wired | 16/16 (100%) |
| Manifests updated | 25+ |
| Lessons documented | 12 |
| Advisors with updated prompts | 8 |
| Events published to live stream | 100 |
| Beyonce references in codebase | 1 (beyonce.txt, untracked, unexplained) |

## Open Items

- **deploy-fleet script** -- Codex recommended: single atomic deploy command with config digest verification
- **Config digest annotations** -- Pod template annotations that force rollout on ConfigMap change
- **watchctl Halostream integration** -- Proactive content triage (parked in memory)
- **Submodule pin** -- `vendor/hermes-agent` pinned to unpushed local commit

## Commits

*   `0679347` docs: Update README with current architecture and add deploy lessons 25-27
*   `bf323c5` docs: Purge stale Argo CD and Vultr CR references
*   `92916f6` infra: Expose API server (port 8642) on all fleet advisors
*   `895d5a7` feat(advisorctl): Add --local mode and musashi audit rubric
*   `75adafe` docs: Add deploy lessons ref to CLAUDE.md key docs table
*   `aa47d83` docs: align README with portfolio standard (badges, accuracy, structure)
*   `289520c` docs: Add Ryzen bare-metal deploy lessons (17-24)
*   `511fd53` fix(docker): Allow track_*.db through .dockerignore
*   `117cb0c` feat(eventsource): Light up the Halostream — full event coverage
