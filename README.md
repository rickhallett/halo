<p align="center">
  <h1 align="center">Halo</h1>
  <p align="center">
    Autonomous event-sourced AI fleet
    <br />
    <em>27 modules. 1364 tests. Choreographed advisory council on Kubernetes.</em>
  </p>
</p>

<p align="center">
  <a href="https://github.com/rickhallett/halo/actions"><img src="https://github.com/rickhallett/halo/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/rickhallett/halo/blob/main/LICENSE"><img src="https://img.shields.io/github/license/rickhallett/halo" alt="License" /></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/k3s-homelab-326CE5?logo=k3s&logoColor=white" alt="k3s" />
  <img src="https://img.shields.io/badge/NATS-JetStream-27aae1?logo=nats.io&logoColor=white" alt="NATS" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
</p>

---

## What is Halo?

Halo is a personal AI agent system. 27 Python modules cover structured memory, work tracking, email triage, YouTube monitoring, daily briefing synthesis, spaced repetition, finance, journaling, and fleet management. Each module has its own CLI, its own SQLite store, and its own test suite.

The modules run locally on macOS for daily use. When deployed to Kubernetes (k3s on a Ryzen homelab), they gain distribution and a choreographed advisory council -- multiple advisor instances communicating through a NATS JetStream event stream called the Halostream.

`hal` is the unified CLI entry point. `hal night add`, `hal track add zazen`, `hal mail inbox`, `hal secrets vaults`. One command, every module.

## Architecture

```
  +-------------------------------------------------------------+
  |                       LOCAL (macOS)                         |
  |                                                             |
  |   +----------+  +----------+  +----------+                 |
  |   | nightctl |  | trackctl |  | briefings|   ...27 modules  |
  |   +----+-----+  +----+-----+  +----+-----+                 |
  |        +------------- +-------------+                       |
  |                       |                                     |
  |              +--------+--------+                            |
  |              |    hal CLI      |                            |
  |              +--------+--------+                            |
  |                       |                                     |
  |              +--------+--------+                            |
  |              | pytest (1364)   |                            |
  |              +--------+--------+                            |
  |                       |                                     |
  |              +--------+--------+                            |
  |              |  SQLite stores  |                            |
  |              +-----------------+                            |
  +-------------------------------------------------------------+
                          |
                     git push + SSH
                          |
  +-------------------------------------------------------------+
  |              K3S CLUSTER (Ryzen homelab, Tailscale)          |
  |                                                             |
  |   +------------------------------------------------------+  |
  |   |                 NATS JetStream                       |  |
  |   |           (the Halostream / event bus)               |  |
  |   +---+--------+--------+--------+--------+--------+----+  |
  |       |        |        |        |        |        |        |
  |   +---+---+ +--+----+ +-+-----+ +--+-----++  ...x8+        |
  |   |Musashi| |Draper | |Gibson | |Karpathy ||               |
  |   |pod    | |pod    | |pod    | |pod      ||               |
  |   +-------+ +-------+ +-------+ +---------+|               |
  |                                              |               |
  |   Four persistence layers per pod:                          |
  |   +------------------------------------------------------+  |
  |   | ConfigMap  - system prompts, advisor config (etcd)   |  |
  |   | Image      - halos Python code + Hermes (registry)   |  |
  |   | NFS        - advisor state, state.db, sessions       |  |
  |   | emptyDir   - store/, logs/ (disposable, rebuilt)     |  |
  |   +------------------------------------------------------+  |
  |                                                             |
  |   +------------------------------------------------------+  |
  |   | Manual deploy: build -> apply -> restart -> verify   |  |
  |   | No Argo CD. See docs/d2/k8s-fleet-lessons-learned.md |  |
  |   +------------------------------------------------------+  |
  +-------------------------------------------------------------+
```

Every module works locally without a network connection, without Docker, without Kubernetes. The cluster adds distribution and the advisory council. The code does not change. The topology changes.

## The Halostream (Event Sourcing)

All advisors communicate through a NATS JetStream event stream called the Halostream. The stream is the single source of truth. Every pod runs a background event consumer that maintains local SQLite projections -- disposable read models rebuilt from the event log on restart.

```
  WRITE: trackctl add zazen --duration 25
           -> writes to local SQLite
           -> publishes track.zazen.logged to NATS

  READ:  Each pod's consumer subscribes to halo.>
           -> receives event within seconds
           -> projects to local SQLite
           -> advisor queries locally (zero network latency)
```

### Event Types

| Category | Event Types | Publisher | Projection |
|---|---|---|---|
| Track | `track.*.logged`, `track.entry.edited/deleted` | trackctl CLI | per-domain track_*.db + projection.db |
| Night | `night.item.created/transitioned`, `night.job.completed/failed` | nightctl CLI + executor | projection.db:night_items, night_jobs |
| Journal | `journal.entry.added` | journalctl CLI | projection.db:journal_entries |
| Dev | `dev.commit.logged` | git_ingest (daily cron) | projection.db:dev_commits |
| Telephony | `advisor.inbound.received/outbound.sent` | Hermes gateway hook | projection.db:advisor_messages |
| System | `system.advisor.started/stopped`, `system.error` | event consumer lifecycle | projection.db:system_events |
| Mail | `mail.triage.executed` | mailctl triage | projection.db:mail_triage |
| Observation | `observation.aura.user/assistant` | aura_relay | projection.db:observation_messages |

### Query Tools

Advisors query projected data via local CLI tools:

| Tool | Purpose |
|---|---|
| `halo-devlog` | Git commit activity across repos (`--summary`, `--repo`, `--days`) |
| `halo-telephony` | Cross-advisor conversation history (`--advisor`, `--direction`, `--summary`) |
| `trackctl` | Personal metrics (streak, summary, list) |
| `journalctl` | Qualitative journal (recent, window) |
| `nightctl` | Work items (items, graph) |
| `observe` | Aura session messages |

There is no central coordinator. The evening council emerges from sequential reactions: each advisor watches for the previous advisor's submission event, contributes its perspective, and publishes its own. Plutarch (the dramaturg) synthesises the council's output.

Kill any pod. It restarts, replays from its last checkpoint on the stream, rebuilds its projection, and resumes. No data loss. No manual intervention.

### Persistence Layers (Critical for Deploy)

Each advisor pod has four independent persistence layers. A correct deploy must update all four in order:

| Layer | Backed by | Survives restart? | Updated by |
|---|---|---|---|
| **ConfigMap** | etcd (k3s) | Yes | `kubectl apply -f infra/k8s/fleet/` |
| **Container image** | Local registry (localhost:5000) | Yes | `docker build && docker push` |
| **NFS state** | NFS volume (advisor-state) | Yes | Advisor writes (state.db, sessions, system-prompt.md cache) |
| **emptyDir stores** | Pod-local tmpfs | No -- wiped on restart | Event consumer replay from NATS |

The system prompt follows a three-hop path: ConfigMap -> `/opt/defaults/system-prompt.md` -> (conditional copy) -> `/opt/data/system-prompt.md` (NFS) -> entrypoint reads into `HERMES_EPHEMERAL_SYSTEM_PROMPT`. If any hop fails, the advisor boots with no persona. See `docs/d2/k8s-fleet-lessons-learned.md` for the full deploy runbook.

## The Roundtable

| Seat | Name | Domain |
|------|------|--------|
| I | Musashi | Physical state and discipline |
| II | Draper | Copywriting, positioning, and pitch |
| III | Karpathy | Engineering craft and logic |
| IV | Gibson | Market terrain and futures |
| V | Machiavelli | Power dynamics and strategy |
| VI | Medici | Financial runway and economics |
| VII | Bankei | Rest, rhythm, and burnout detection |
| VIII | Hightower | Heavy Iron / K8s Operations |
| IX | Guido | Python craft / curriculum |
| -- | Plutarch | Dramaturg / council synthesis (not deployed) |

Additional advisors (Seneca, Socrates, Sun Tzu) are available in `data/advisors/`.

## Modules

The `halos/` package is the centre of gravity. 24 Python CLIs for structured work across domains.

| Module | Command | Purpose |
|--------|---------|---------|
| memctl | `memctl` | Structured memory governance |
| nightctl | `nightctl` | Work tracker with Eisenhower matrix |
| cronctl | `cronctl` | Cron job definitions and crontab generation |
| logctl | `logctl` | Structured log reading and search |
| reportctl | `reportctl` | Periodic digests |
| agentctl | `agentctl` | LLM session tracking and spin detection |
| advisorctl | `advisorctl` | Advisor fleet queries and audit |
| briefings | `hal-briefing` | Morning / nightly digests via Telegram |
| trackctl | `trackctl` | Personal metrics (zazen, movement, study) |
| dashctl | `dashctl` | TUI dashboard |
| halctl | `halctl` | Fleet management and health checks |
| mailctl | `mailctl` | Gmail operations via himalaya |
| watchctl | `watchctl` | YouTube channel monitor with LLM-as-judge triage |
| journalctl | `journalctl` | Qualitative journal with sliding-window synthesis |
| secretctl | `secretctl` | 1Password secret access |
| ledgerctl | `ledgerctl` | Finance ledger |
| drillctl | `drillctl` | Spaced repetition drill cards |
| docctl | `docctl` | Documentation index and validation |
| calctl | `calctl` | Calendar integration |
| statusctl | `statusctl` | System status queries |
| backupctl | `backupctl` | Backup management |
| eventsource | -- | NATS JetStream event sourcing core |
| halo-devlog | `halo-devlog` | Git commit activity query (Halostream) |
| halo-telephony | `halo-telephony` | Cross-advisor conversation query (Halostream) |

## Repository Structure

```
halo/
+-- halos/              27 Python CLI modules
+-- infra/              K8s manifests, NATS config, fleet deploy
+-- agent/              macOS agent server (listen/direct)
+-- docker/             Container entrypoint and defaults
+-- vendor/             Hermes agent (git submodule)
+-- data/               Advisor personas, client prompts
+-- docs/               Specs, analyses, runbooks (d1/d2/d3 hierarchy)
+-- memory/             Structured notes and reflections (memctl-managed)
+-- tests/              pytest suite (1364 tests)
+-- store/              SQLite databases (gitignored, per-domain)
+-- cron/               Cron job definitions (cronctl-managed)
+-- backlog/            Work items (nightctl-managed)
```

## Storage Model

- **SQLite** for queryable domain state (one DB per domain, WAL mode)
- **YAML** for human-readable config, work items, and cron jobs
- **Markdown** for prose, specs, advisor personas, and memory notes
- **NATS JetStream** for durable event log (stream: HALO, replayed on restart)

## Deploy

The fleet runs on k3s (Ryzen homelab, reachable via Tailscale). No Argo CD. Deploy is manual via SSH.

```bash
# 1. Push code
git push

# 2. Pull on Ryzen
ssh mrkai@ryzen32 "cd ~/code/halo && git pull"

# 3. Build and push image
ssh mrkai@ryzen32 "cd ~/code/halo && docker build -t localhost:5000/halo:dev . && docker push localhost:5000/halo:dev"

# 4. Apply manifests (ConfigMaps + Deployments -- image alone is not enough)
ssh mrkai@ryzen32 "cd ~/code/halo && sudo kubectl apply -f infra/k8s/fleet/"

# 5. Restart fleet
ssh mrkai@ryzen32 "sudo kubectl rollout restart deploy -n halo-fleet"

# 6. Verify
ssh mrkai@ryzen32 "sudo kubectl get pods -n halo-fleet --no-headers"
```

Full deploy runbook with gotchas: `docs/d2/k8s-fleet-lessons-learned.md`

## Getting Started

```bash
git clone https://github.com/rickhallett/halo.git
cd halo
uv sync

# Use any module
hal night items
hal track summary
hal mail inbox
```

## License

[MIT](LICENSE)
