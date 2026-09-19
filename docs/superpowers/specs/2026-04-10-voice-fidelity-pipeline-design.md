# Voice Fidelity Pipeline — Design Specification

**Date:** 2026-04-10
**Status:** Draft
**Author:** Chango + Boss
**Repo:** Standalone (new repo, separate from halo)
**Codename:** SoundsRight

---

## 1. Problem

AI-generated content sounds generic. When a client — a practitioner, creator, someone with a recognisable voice — needs AI-produced content, the output must sound like *them*, not like a wellness content mill with the temperature turned up.

Full RLHF is a quarter-million-dollar infrastructure problem for a single voice. This pipeline delivers 80% of that quality through structured rubrics, preference scoring, and retrieval-augmented style transfer — no weight updates required.

Strategic rationale: [The voice-fidelity pipeline](https://oceanheart.ai/blog/2026-04-10-voice-fidelity-pipeline/) (draft).

## 2. Scope

A standalone, multi-tenant pipeline for client-specific voice alignment. Full vertical: ingest text, analyse style, derive scoring rubric, generate content in the client's voice, score output (LLM-as-judge + human), collect preference pairs, close the feedback loop via few-shot retrieval.

### In scope (v1)

- Multi-tenant client management
- Text corpus ingestion and LLM-driven style analysis
- Dynamic rubric derivation from corpus analysis (per-client, versioned)
- Style-conditioned content generation with few-shot retrieval
- LLM-as-judge baseline scoring
- Human scoring via web UI (Jinja2 + HTMX, token auth, mobile-friendly)
- Preference pair derivation from score deltas
- Feedback loop: high-scored artifacts feed back as few-shot examples
- Async job queue (Celery + Redis) for all LLM operations
- Cost tracking per artifact, per stage
- CLI operator interface (`voicectl`)
- Docker Compose local dev, K8s deployment on Ryzen (namespace: `soundsright`)

### Not in scope (v1)

- Audio/video transcription (text-native input only)
- Fine-tuning / LoRA / DPO weight updates (pipeline produces the preference dataset for future use)
- Observability stack (Prometheus, Grafana, OTEL)
- CI/CD pipeline
- Helm charts (raw K8s manifests)
- Multi-region deployment

### First client

Aura Enache — Daoist practitioner, UHT UK certified instructor. Content Alchemist agent produces Instagram-ready content from her voice corpus.

## 3. Stack

| Concern | Technology |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI |
| Queue | Redis + Celery (4 dedicated queues) |
| Database | PostgreSQL + pgvector (shared instance with Jeany, separate database) |
| Web UI | Jinja2 + HTMX (server-rendered) |
| CLI | `voicectl` (argparse or click) |
| LLM | Anthropic SDK (frontier model for analysis, derivation, generation, judging) |
| Containers | Docker, Docker Compose |
| Orchestration | k3s on Ryzen bare metal (namespace: `soundsright`) |
| Deploy | Mutagen sync → build on Ryzen → localhost:5000 → kubectl apply |
| Secrets | 1Password via secretctl or K8s Secrets |
| Deps | uv (Python dependency management) |

Architecture pattern inherited from [Jeany](https://github.com/rickhallett/jeany) — Celery task queues, shared Pydantic models, cost tracking as first-class concern. Deployed as a **modular monolith**: one FastAPI process, one Celery worker (processing four queues), code logically separated by domain directory. Avoids microservice sprawl on shared bare-metal Ryzen.

## 4. Data Model

### Tables

```sql
-- Multi-tenant root
CREATE TABLE clients (
    id                      UUID PRIMARY KEY,
    name                    TEXT NOT NULL,
    slug                    TEXT UNIQUE NOT NULL,
    score_delta_threshold   INT DEFAULT 3,       -- min aggregate score delta for preference pair derivation
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Raw text corpus
CREATE TABLE corpus_entries (
    id          UUID PRIMARY KEY,
    client_id   UUID REFERENCES clients(id),
    source_type TEXT NOT NULL,           -- social_post, blog, transcript, voice_note
    raw_text    TEXT NOT NULL,
    embedding   VECTOR(1536),            -- pgvector: for semantic retrieval of relevant examples
    metadata    JSONB DEFAULT '{}',      -- source url, date, platform
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Structured style analysis (LLM output)
CREATE TABLE style_analyses (
    id          UUID PRIMARY KEY,
    client_id   UUID REFERENCES clients(id),
    version     INT NOT NULL,
    analysis    JSONB NOT NULL,          -- tone registers, vocab signatures, cadence, etc.
    model       TEXT NOT NULL,
    cost_usd    NUMERIC,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(client_id, version)
);

-- Per-client, versioned rubric dimensions (derived from analysis)
CREATE TABLE rubric_dimensions (
    id          UUID PRIMARY KEY,
    client_id   UUID REFERENCES clients(id),
    rubric_version INT NOT NULL,
    name        TEXT NOT NULL,           -- vocabulary_fidelity
    label       TEXT NOT NULL,           -- Vocabulary Fidelity
    description TEXT NOT NULL,           -- what the scorer evaluates
    weight      FLOAT DEFAULT 1.0,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Generated content artifacts
CREATE TABLE artifacts (
    id              UUID PRIMARY KEY,
    client_id       UUID REFERENCES clients(id),
    prompt          TEXT NOT NULL,
    generated_text  TEXT NOT NULL,
    embedding       VECTOR(1536),            -- pgvector: for semantic few-shot retrieval
    model           TEXT NOT NULL,
    rubric_version  INT NOT NULL,
    status          TEXT DEFAULT 'pending_score',  -- pending_score, scored, rejected
    cost_usd        NUMERIC,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Per-dimension scores on artifacts
CREATE TABLE scores (
    id              UUID PRIMARY KEY,
    artifact_id     UUID REFERENCES artifacts(id),
    dimension_id    UUID REFERENCES rubric_dimensions(id),
    score           INT NOT NULL CHECK (score BETWEEN 1 AND 10),
    scorer_type     TEXT NOT NULL,       -- human, llm_judge
    scorer_id       TEXT NOT NULL,       -- client slug or model name
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Server-side token auth with revocation
CREATE TABLE auth_tokens (
    id          UUID PRIMARY KEY,
    client_id   UUID REFERENCES clients(id),
    token       TEXT UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,             -- NULL = active, set = revoked
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Derived preference pairs for future DPO/fine-tuning
CREATE TABLE preference_pairs (
    id              UUID PRIMARY KEY,
    client_id       UUID REFERENCES clients(id),
    chosen_id       UUID REFERENCES artifacts(id),
    rejected_id     UUID REFERENCES artifacts(id),
    derived_from    TEXT NOT NULL,       -- score_delta, explicit_comparison
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

### Key design decisions

- **Rubric dimensions are per-client, versioned.** Re-derivation creates a new version. Old artifacts retain their rubric version so scores remain comparable.
- **Scores are per-dimension, not per-artifact.** Aggregate score is computed, never stored.
- **Preference pairs are derived from score deltas.** Threshold is per-client (`score_delta_threshold`, default 3). When two artifacts differ by >= threshold on aggregate score, the higher is "chosen" and the lower is "rejected." No explicit A/B comparison required from the client.
- **Semantic retrieval via pgvector.** Corpus entries and artifacts are embedded at creation time. The generator retrieves topically relevant few-shot examples via cosine similarity — not just highest-scored. Prevents overfitting to a single topic when all top-scored artifacts cluster around one subject.
- **Cost tracking on every LLM operation.** Stored on `style_analyses`, `artifacts`. Queryable per-client, per-stage.
- **Server-side token auth with revocation.** Tokens stored in `auth_tokens` with `expires_at` and `revoked_at`. Operator can revoke instantly via `voicectl client token revoke <token>`. No stateless JWT — the DB is the source of truth for token validity.
- **Modular monolith.** One FastAPI process, one Celery worker, one container image. Code is logically separated by domain directory (`corpus/`, `rubric/`, `generator/`, `scorer/`, `web/`) but deployed as a single unit. Avoids microservice memory overhead on shared bare-metal Ryzen.

## 5. Service Architecture

```
soundsright/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app — mounts all domain routers
│   ├── celery_app.py        # Celery app — registers all domain tasks
│   ├── db.py                # SQLAlchemy models + connection + pgvector setup
│   ├── models.py            # Pydantic models (shared across domains)
│   ├── cost.py              # Cost tracking utilities
│   │
│   ├── corpus/              # Domain: corpus management + style analysis
│   │   ├── __init__.py
│   │   ├── router.py        # FastAPI router — CRUD corpus entries, trigger analysis
│   │   ├── analyser.py      # LLM-driven style analysis
│   │   └── tasks.py         # Celery tasks (analyse corpus)
│   │
│   ├── rubric/              # Domain: rubric derivation
│   │   ├── __init__.py
│   │   ├── router.py        # FastAPI router — CRUD rubric dimensions, trigger derivation
│   │   ├── deriver.py       # LLM-driven dimension extraction
│   │   └── tasks.py         # Celery tasks (derive rubric)
│   │
│   ├── generator/           # Domain: content generation in client voice
│   │   ├── __init__.py
│   │   ├── router.py        # FastAPI router — submit generation jobs, list artifacts
│   │   ├── engine.py        # Semantic few-shot retrieval + style-conditioned generation
│   │   └── tasks.py         # Celery tasks (generate content)
│   │
│   ├── scorer/              # Domain: scoring API + LLM-as-judge
│   │   ├── __init__.py
│   │   ├── router.py        # FastAPI router — submit/retrieve scores, preference pairs
│   │   ├── judge.py         # LLM-as-judge baseline scoring
│   │   └── tasks.py         # Celery tasks (auto-score)
│   │
│   └── web/                 # Domain: client-facing scoring UI
│       ├── __init__.py
│       ├── router.py        # FastAPI router — Jinja2 template views + HTMX endpoints
│       ├── auth.py          # Token validation, revocation checks
│       ├── templates/       # Jinja2 (login, dashboard, artifact list, score, history)
│       └── static/          # CSS, HTMX
│
├── cli/
│   └── voicectl/            # CLI for operator pipeline control
│       ├── __init__.py
│       ├── cli.py           # Entry point
│       └── commands/        # Subcommand modules
│
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── k8s/                 # Raw manifests for soundsright namespace
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── Makefile
├── pyproject.toml
└── README.md
```

**Deployment model:** One FastAPI process serves all API routes and the scoring web UI. One Celery worker process handles all four queues (`-Q corpus,rubric,generate,score`). One Dockerfile, one container image. Code is logically separated by domain directory but deployed as a single unit.

### Celery queues

| Queue | Work type | Typical duration |
|---|---|---|
| `corpus` | Style analysis | 1-3 min per corpus |
| `rubric` | Dimension derivation | 30s-2min per run |
| `generate` | Content generation | 5-30s per artifact |
| `score` | LLM-as-judge auto-scoring | 5-15s per artifact |

All four queues are processed by a single Celery worker (`-Q corpus,rubric,generate,score`). Clients can submit unbounded generation jobs — they queue and process without blocking other stages. If a single worker becomes a bottleneck under load, scale by adding workers that subscribe to specific queues.

### Docker Compose services (local dev)

```
postgres          # Own instance (or shared with Jeany via DATABASE_URL)
redis             # Own instance (or shared with Jeany via REDIS_URL)
app               # FastAPI :8080 (all API routes + scoring web UI)
worker            # Celery -Q corpus,rubric,generate,score
```

## 6. CLI Interface

`voicectl` — operator-facing pipeline control:

```bash
# Client management
voicectl client add "Aura Enache" --slug aura
voicectl client list

# Corpus
voicectl corpus ingest aura --source ./texts/        # bulk from directory
voicectl corpus ingest aura --text "paste raw text"   # single entry
voicectl corpus list aura
voicectl corpus analyse aura                          # enqueue style analysis

# Rubric
voicectl rubric derive aura                           # enqueue derivation
voicectl rubric show aura                             # current dimensions
voicectl rubric history aura                          # version history

# Generation
voicectl generate aura --topic "morning qi gong routine"
voicectl generate aura --topics ./topics.txt --count 5
voicectl jobs list
voicectl jobs status <job-id>

# Scoring
voicectl score auto aura                              # enqueue LLM-as-judge
voicectl score list aura                              # score summary
voicectl score export aura --format pairs             # JSONL preference pairs

# Server
voicectl serve                                        # start web UI :8080

# Cost
voicectl cost aura                                    # total spend
voicectl cost aura --by stage                         # per-stage breakdown

# Auth
voicectl client token aura                            # generate scoring UI link
voicectl client token revoke <token>                  # revoke a specific token
voicectl client token list aura                       # list active tokens
```

Every LLM-triggering command enqueues a Celery task and returns immediately. `voicectl jobs` tracks progress.

## 7. Scoring Web UI

Five pages, Jinja2 + HTMX, served from scorer service.

### Pages

1. **Login** — token-based auth via URL parameter (`/score/aura?token=xxx`). No passwords. Operator generates links via `voicectl client token aura`. Tokens expire (configurable, default 30 days).

2. **Dashboard** — artifacts waiting for scoring (count), recent scores submitted, voice-fidelity trend over time (average aggregate score).

3. **Artifact list** — all artifacts for the client, filterable by status (unscored / scored). No enforced ordering — client picks what to score. HTMX pagination.

4. **Score an artifact** — core screen:
   - Generated text displayed prominently
   - Prompt/topic that produced it
   - One slider (1-10) per rubric dimension with description visible as guidance
   - Optional free-text field ("what's off about this one?")
   - Submit via HTMX — no page reload, next unscored artifact loads automatically

5. **Score history** — read-only table of past scores with artifact previews.

### Constraints

- Mobile-friendly (Aura will score from her phone)
- Minimal chrome — generated text is the star
- No client-side state — every interaction is a server round-trip via HTMX
- Token auth with configurable expiry

## 8. Pipeline Flow

```
                    INGEST (sync)
                        │
                   corpus_entries
                        │
                  ANALYSE (async)
                        │
                  style_analyses
                        │
                 DERIVE RUBRIC (async)
                        │
                rubric_dimensions
                        │
              GENERATE (async, unbounded)
                   │              │
              artifacts      LLM-as-judge
                   │          auto-score
                   │              │
              ┌────┴──────────────┘
              │
         Human scoring
         (web UI)
              │
           scores
              │
     Preference pair
       derivation
              │
     preference_pairs
              │
     ┌────────┴────────┐
     │                  │
  Few-shot           JSONL export
  retrieval          (future DPO /
  improvement         fine-tuning)
     │
     └──→ GENERATE (better few-shot examples)
```

The feedback loop closes when scored artifacts feed back into the generator's few-shot retrieval pool. High-scored artifacts become the examples that condition future generation. No weight updates — the model sees better examples and produces better output.

## 9. Infrastructure

### Local dev

Docker Compose. SoundsRight runs its own Postgres and Redis containers by default. If Jeany's Compose stack is already running, configure `DATABASE_URL` and `REDIS_URL` to point at the shared instances (separate database `soundsright`, separate Redis db number). Either mode works — the services don't care where the backing stores live.

### Production (Ryzen k3s)

- **Namespace:** `soundsright`
- **Deploy pipeline:** Mutagen sync Mac → Ryzen → build on local disk → push `localhost:5000/soundsright:dev` → `kubectl apply -n soundsright`
- **Shared infra:** Postgres + Redis from existing Ryzen services
- **Secrets:** K8s Secrets (API keys, token signing key)
- **Cost ceiling:** `COST_CEILING_USD` env var. Every LLM call checks cumulative spend. Hard stop when hit.

### Resource budget

Single Ryzen box shared with halo fleet + Jeany. Conservative resource limits per service — the pipeline is bursty (generation runs) not steady-state.

## 10. Research Question

> Can rubric-scored preference pairs plus prompt engineering get 80% of fine-tuning quality?

This pipeline is designed to answer that question empirically. If the answer is yes — ship it. If Aura consistently scores 6/10 on tone and prompt-level techniques can't push past it, the preference dataset is already collected and formatted for DPO/LoRA fine-tuning. No cold start either way.

## 11. Success Criteria

- Aura can score generated content from her phone in under 30 seconds per artifact
- LLM-as-judge baseline scores correlate with Aura's human scores (within 2 points on aggregate)
- After 20+ scored artifacts, the generator's output quality (as measured by Aura's scores) trends upward
- Cost per generated artifact is tracked and visible
- A second client can be onboarded without code changes (multi-tenant)
