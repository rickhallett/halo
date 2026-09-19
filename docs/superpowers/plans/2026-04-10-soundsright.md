# SoundsRight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-tenant voice-fidelity pipeline that ingests text corpora, derives scoring rubrics, generates content in a client's voice, and closes a feedback loop via human and LLM-as-judge scoring.

**Architecture:** Modular monolith — one FastAPI app with domain routers (corpus, rubric, generator, scorer, web), one Celery worker processing four queues, PostgreSQL + pgvector for storage and semantic retrieval, Jinja2 + HTMX for the client-facing scoring UI. Deployed as a single container on Ryzen k3s.

**Tech Stack:** Python 3.11+, FastAPI, Celery, Redis, PostgreSQL + pgvector, SQLAlchemy, Pydantic, Jinja2, HTMX, Anthropic SDK, uv, Docker Compose

**Spec:** `docs/superpowers/specs/2026-04-10-voice-fidelity-pipeline-design.md`

---

## File Map

```
soundsright/                          # New repo root
├── app/
│   ├── __init__.py                   # Package marker
│   ├── main.py                       # FastAPI app, mounts all routers
│   ├── celery_app.py                 # Celery app, autodiscovers tasks
│   ├── config.py                     # Settings via pydantic-settings (DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY, COST_CEILING_USD, etc.)
│   ├── db.py                         # SQLAlchemy engine, session, Base, pgvector registration
│   ├── models.py                     # SQLAlchemy ORM models (all tables)
│   ├── schemas.py                    # Pydantic request/response schemas
│   ├── cost.py                       # Cost tracking: check ceiling, record cost
│   ├── embed.py                      # Embedding utility: text → VECTOR(1536) via OpenAI
│   │
│   ├── corpus/
│   │   ├── __init__.py
│   │   ├── router.py                 # FastAPI router: POST /corpus/entries, POST /corpus/analyse, GET /corpus/entries
│   │   ├── analyser.py               # LLM style analysis: corpus text → structured JSON
│   │   └── tasks.py                  # Celery task: analyse_corpus
│   │
│   ├── rubric/
│   │   ├── __init__.py
│   │   ├── router.py                 # FastAPI router: POST /rubric/derive, GET /rubric/dimensions, GET /rubric/history
│   │   ├── deriver.py                # LLM rubric derivation: style analysis → dimensions
│   │   └── tasks.py                  # Celery task: derive_rubric
│   │
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── router.py                 # FastAPI router: POST /generate, GET /artifacts
│   │   ├── engine.py                 # Few-shot retrieval (pgvector cosine similarity) + style-conditioned generation
│   │   └── tasks.py                  # Celery task: generate_content
│   │
│   ├── scorer/
│   │   ├── __init__.py
│   │   ├── router.py                 # FastAPI router: POST /scores, GET /scores, GET /preference-pairs
│   │   ├── judge.py                  # LLM-as-judge: score artifact against rubric dimensions
│   │   ├── pairs.py                  # Preference pair derivation from score deltas
│   │   └── tasks.py                  # Celery task: auto_score, derive_pairs
│   │
│   └── web/
│       ├── __init__.py
│       ├── router.py                 # FastAPI router: scoring UI views (GET /score/{slug}, POST /score/{slug}/submit)
│       ├── auth.py                   # Token validation middleware: check auth_tokens table
│       ├── templates/
│       │   ├── base.html             # Base template: head, body, HTMX script tag, minimal CSS
│       │   ├── login.html            # Token entry / redirect landing
│       │   ├── dashboard.html        # Unscored count, recent scores, trend
│       │   ├── artifacts.html        # Artifact list with HTMX pagination
│       │   ├── score.html            # Score an artifact: sliders per dimension, free-text, submit
│       │   └── history.html          # Score history table
│       └── static/
│           └── style.css             # Minimal mobile-first CSS
│
├── cli/
│   └── voicectl/
│       ├── __init__.py
│       ├── cli.py                    # Click group: voicectl
│       └── commands/
│           ├── __init__.py
│           ├── client.py             # voicectl client {add,list,token,token revoke,token list}
│           ├── corpus.py             # voicectl corpus {ingest,list,analyse}
│           ├── rubric.py             # voicectl rubric {derive,show,history}
│           ├── generate.py           # voicectl generate
│           ├── jobs.py               # voicectl jobs {list,status}
│           ├── score.py              # voicectl score {auto,list,export}
│           ├── cost.py               # voicectl cost
│           └── serve.py              # voicectl serve
│
├── migrations/
│   └── 001_initial.sql               # Full schema: all tables + pgvector extension
│
├── infra/
│   ├── docker-compose.yml            # postgres, redis, app, worker
│   ├── Dockerfile                    # Single image: app + worker + CLI
│   └── k8s/
│       ├── namespace.yaml
│       ├── deployment.yaml           # app + worker containers in one pod
│       ├── service.yaml
│       └── secrets.yaml
│
├── tests/
│   ├── conftest.py                   # Fixtures: test DB, test Redis, test client, factory helpers
│   ├── test_models.py                # ORM model tests
│   ├── test_corpus.py                # Corpus router + analyser tests
│   ├── test_rubric.py                # Rubric router + deriver tests
│   ├── test_generator.py             # Generator router + engine tests
│   ├── test_scorer.py                # Scorer router + judge + pairs tests
│   ├── test_web.py                   # Web UI router + auth tests
│   ├── test_cli.py                   # CLI command tests
│   └── test_cost.py                  # Cost ceiling tests
│
├── Makefile                          # dev, test, lint, migrate, serve
├── pyproject.toml                    # uv project: soundsright
└── README.md
```

---

## Task 1: Repository Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `cli/__init__.py` (empty)
- Create: `cli/voicectl/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Create the repo directory**

```bash
mkdir -p ~/code/soundsright
cd ~/code/soundsright
git init
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "soundsright"
version = "0.1.0"
description = "Voice-fidelity pipeline: client-specific AI alignment via structured rubrics and preference scoring"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "celery[redis]>=5.4.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "pgvector>=0.3.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "anthropic>=0.40.0",
    "openai>=1.50.0",
    "httpx>=0.27.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.9",
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "factory-boy>=3.3.0",
]

[project.scripts]
voicectl = "cli.voicectl.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 3: Create app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://soundsright:soundsright@localhost:5432/soundsright"
    redis_url: str = "redis://localhost:6379/1"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    cost_ceiling_usd: float = 50.0
    token_expiry_days: int = 30
    embedding_model: str = "text-embedding-3-small"
    generation_model: str = "claude-sonnet-4-20250514"
    judge_model: str = "claude-sonnet-4-20250514"
    analysis_model: str = "claude-sonnet-4-20250514"

    model_config = {"env_prefix": "SOUNDSRIGHT_", "env_file": ".env"}


settings = Settings()
```

- [ ] **Step 4: Create app/__init__.py**

```python
# SoundsRight — voice-fidelity pipeline
```

- [ ] **Step 5: Create Makefile**

```makefile
.PHONY: dev test lint migrate serve

dev:
	docker compose up -d

test:
	uv run pytest -v

lint:
	@echo "lint: no linter configured"

migrate:
	uv run python -m app.db migrate

serve:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

- [ ] **Step 6: Create empty package markers**

```bash
mkdir -p app/corpus app/rubric app/generator app/scorer app/web app/web/templates app/web/static
mkdir -p cli/voicectl/commands
mkdir -p tests migrations infra/k8s
touch app/corpus/__init__.py app/rubric/__init__.py app/generator/__init__.py
touch app/scorer/__init__.py app/web/__init__.py
touch cli/__init__.py cli/voicectl/__init__.py cli/voicectl/commands/__init__.py
touch tests/__init__.py
```

- [ ] **Step 7: Install dependencies**

```bash
cd ~/code/soundsright
uv sync
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: repo scaffold — pyproject.toml, config, directory structure"
```

---

## Task 2: Database Schema + ORM Models

**Files:**
- Create: `migrations/001_initial.sql`
- Create: `app/db.py`
- Create: `app/models.py`
- Create: `app/schemas.py`
- Create: `tests/conftest.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the migration SQL**

Create `migrations/001_initial.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE clients (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                    TEXT NOT NULL,
    slug                    TEXT UNIQUE NOT NULL,
    score_delta_threshold   INT DEFAULT 3,
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE corpus_entries (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id   UUID REFERENCES clients(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    raw_text    TEXT NOT NULL,
    embedding   VECTOR(1536),
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE style_analyses (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id   UUID REFERENCES clients(id) ON DELETE CASCADE,
    version     INT NOT NULL,
    analysis    JSONB NOT NULL,
    model       TEXT NOT NULL,
    cost_usd    NUMERIC,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(client_id, version)
);

CREATE TABLE rubric_dimensions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
    rubric_version  INT NOT NULL,
    name            TEXT NOT NULL,
    label           TEXT NOT NULL,
    description     TEXT NOT NULL,
    weight          FLOAT DEFAULT 1.0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE artifacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
    prompt          TEXT NOT NULL,
    generated_text  TEXT NOT NULL,
    embedding       VECTOR(1536),
    model           TEXT NOT NULL,
    rubric_version  INT NOT NULL,
    status          TEXT DEFAULT 'pending_score',
    cost_usd        NUMERIC,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    artifact_id     UUID REFERENCES artifacts(id) ON DELETE CASCADE,
    dimension_id    UUID REFERENCES rubric_dimensions(id) ON DELETE CASCADE,
    score           INT NOT NULL CHECK (score BETWEEN 1 AND 10),
    scorer_type     TEXT NOT NULL,
    scorer_id       TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE auth_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id   UUID REFERENCES clients(id) ON DELETE CASCADE,
    token       TEXT UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE preference_pairs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
    chosen_id       UUID REFERENCES artifacts(id) ON DELETE CASCADE,
    rejected_id     UUID REFERENCES artifacts(id) ON DELETE CASCADE,
    derived_from    TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_corpus_entries_client ON corpus_entries(client_id);
CREATE INDEX idx_artifacts_client_status ON artifacts(client_id, status);
CREATE INDEX idx_scores_artifact ON scores(artifact_id);
CREATE INDEX idx_auth_tokens_token ON auth_tokens(token);
CREATE INDEX idx_preference_pairs_client ON preference_pairs(client_id);
```

- [ ] **Step 2: Create app/db.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migration():
    """Run the initial migration SQL against the database."""
    import pathlib

    sql_path = pathlib.Path(__file__).parent.parent / "migrations" / "001_initial.sql"
    sql = sql_path.read_text()
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(sql))
        conn.commit()
```

- [ ] **Step 3: Create app/models.py with all ORM models**

```python
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    score_delta_threshold = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    corpus_entries = relationship("CorpusEntry", back_populates="client")
    style_analyses = relationship("StyleAnalysis", back_populates="client")
    rubric_dimensions = relationship("RubricDimension", back_populates="client")
    artifacts = relationship("Artifact", back_populates="client")
    auth_tokens = relationship("AuthToken", back_populates="client")
    preference_pairs = relationship("PreferencePair", back_populates="client")


class CorpusEntry(Base):
    __tablename__ = "corpus_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"))
    source_type = Column(Text, nullable=False)
    raw_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    client = relationship("Client", back_populates="corpus_entries")


class StyleAnalysis(Base):
    __tablename__ = "style_analyses"
    __table_args__ = (UniqueConstraint("client_id", "version"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"))
    version = Column(Integer, nullable=False)
    analysis = Column(JSONB, nullable=False)
    model = Column(Text, nullable=False)
    cost_usd = Column(Numeric)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    client = relationship("Client", back_populates="style_analyses")


class RubricDimension(Base):
    __tablename__ = "rubric_dimensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"))
    rubric_version = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    label = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    client = relationship("Client", back_populates="rubric_dimensions")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"))
    prompt = Column(Text, nullable=False)
    generated_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    model = Column(Text, nullable=False)
    rubric_version = Column(Integer, nullable=False)
    status = Column(Text, default="pending_score")
    cost_usd = Column(Numeric)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    client = relationship("Client", back_populates="artifacts")
    scores = relationship("Score", back_populates="artifact")


class Score(Base):
    __tablename__ = "scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"))
    dimension_id = Column(UUID(as_uuid=True), ForeignKey("rubric_dimensions.id", ondelete="CASCADE"))
    score = Column(Integer, nullable=False)
    scorer_type = Column(Text, nullable=False)
    scorer_id = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (CheckConstraint("score >= 1 AND score <= 10"),)

    artifact = relationship("Artifact", back_populates="scores")
    dimension = relationship("RubricDimension")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"))
    token = Column(Text, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    client = relationship("Client", back_populates="auth_tokens")


class PreferencePair(Base):
    __tablename__ = "preference_pairs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"))
    chosen_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"))
    rejected_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"))
    derived_from = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    client = relationship("Client", back_populates="preference_pairs")
    chosen = relationship("Artifact", foreign_keys=[chosen_id])
    rejected = relationship("Artifact", foreign_keys=[rejected_id])
```

- [ ] **Step 4: Create app/schemas.py with Pydantic schemas**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# --- Clients ---

class ClientCreate(BaseModel):
    name: str
    slug: str


class ClientOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    score_delta_threshold: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Corpus ---

class CorpusEntryCreate(BaseModel):
    source_type: str = "text"
    raw_text: str
    metadata: dict = Field(default_factory=dict)


class CorpusEntryOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    source_type: str
    raw_text: str
    metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Style Analysis ---

class StyleAnalysisOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    version: int
    analysis: dict
    model: str
    cost_usd: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Rubric ---

class RubricDimensionOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    rubric_version: int
    name: str
    label: str
    description: str
    weight: float
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Artifacts ---

class GenerateRequest(BaseModel):
    topic: str


class ArtifactOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    prompt: str
    generated_text: str
    model: str
    rubric_version: int
    status: str
    cost_usd: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Scores ---

class ScoreCreate(BaseModel):
    dimension_id: uuid.UUID
    score: int = Field(ge=1, le=10)


class ScoreSubmission(BaseModel):
    scores: list[ScoreCreate]
    feedback: str = ""


class ScoreOut(BaseModel):
    id: uuid.UUID
    artifact_id: uuid.UUID
    dimension_id: uuid.UUID
    score: int
    scorer_type: str
    scorer_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Preference Pairs ---

class PreferencePairOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    chosen_id: uuid.UUID
    rejected_id: uuid.UUID
    derived_from: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Auth ---

class TokenOut(BaseModel):
    token: str
    expires_at: datetime
    url: str


# --- Jobs ---

class JobStatus(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
```

- [ ] **Step 5: Create tests/conftest.py with test fixtures**

```python
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app as fastapi_app
from app.models import Client


TEST_DB_URL = "postgresql://soundsright:soundsright@localhost:5432/soundsright_test"


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DB_URL)
    # Create pgvector extension and tables
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        conn.commit()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create a test client (Aura)."""
    c = Client(name="Aura Enache", slug="aura")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def app_client(db_session):
    """FastAPI test client with DB session override."""
    from fastapi.testclient import TestClient

    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as tc:
        yield tc
    fastapi_app.dependency_overrides.clear()
```

- [ ] **Step 6: Write test_models.py — verify ORM models create and query**

```python
from app.models import Client, CorpusEntry


def test_create_client(db_session):
    c = Client(name="Test Client", slug="test-client")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    assert c.id is not None
    assert c.slug == "test-client"
    assert c.score_delta_threshold == 3


def test_create_corpus_entry(db_session, client):
    entry = CorpusEntry(
        client_id=client.id,
        source_type="social_post",
        raw_text="The breath moves before the body moves.",
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)

    assert entry.id is not None
    assert entry.client_id == client.id
    assert entry.embedding is None  # not yet embedded
```

- [ ] **Step 7: Run tests to verify they fail (no app/main.py yet)**

Run: `cd ~/code/soundsright && uv run pytest tests/test_models.py -v`
Expected: ImportError for `app.main`

- [ ] **Step 8: Create minimal app/main.py to unblock imports**

```python
from fastapi import FastAPI

app = FastAPI(title="SoundsRight", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 9: Run tests again — should pass if test DB is available**

Run: `cd ~/code/soundsright && uv run pytest tests/test_models.py -v`
Expected: 2 passed (requires Postgres running with `soundsright_test` database)

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: database schema, ORM models, Pydantic schemas, test fixtures"
```

---

## Task 3: Celery App + Cost Tracking + Embedding Utility

**Files:**
- Create: `app/celery_app.py`
- Create: `app/cost.py`
- Create: `app/embed.py`
- Create: `tests/test_cost.py`

- [ ] **Step 1: Write test for cost ceiling check**

```python
from unittest.mock import patch

from app.cost import check_cost_ceiling, record_cost


def test_check_cost_ceiling_under_limit():
    """Cost check passes when cumulative spend is under ceiling."""
    with patch("app.cost._get_cumulative_cost", return_value=10.0):
        # Should not raise
        check_cost_ceiling(estimated_cost=5.0, ceiling=50.0)


def test_check_cost_ceiling_over_limit():
    """Cost check raises when cumulative spend would exceed ceiling."""
    import pytest

    with patch("app.cost._get_cumulative_cost", return_value=48.0):
        with pytest.raises(RuntimeError, match="Cost ceiling"):
            check_cost_ceiling(estimated_cost=5.0, ceiling=50.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cost.py -v`
Expected: FAIL — `app.cost` does not exist

- [ ] **Step 3: Create app/cost.py**

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Artifact, StyleAnalysis


def _get_cumulative_cost(db: Session) -> float:
    """Sum all cost_usd across artifacts and style analyses."""
    artifact_cost = db.execute(
        select(func.coalesce(func.sum(Artifact.cost_usd), 0))
    ).scalar()
    analysis_cost = db.execute(
        select(func.coalesce(func.sum(StyleAnalysis.cost_usd), 0))
    ).scalar()
    return float(artifact_cost + analysis_cost)


def check_cost_ceiling(
    estimated_cost: float = 0.0,
    ceiling: float | None = None,
    db: Session | None = None,
) -> None:
    """Raise RuntimeError if cumulative cost + estimated would exceed ceiling."""
    ceiling = ceiling if ceiling is not None else settings.cost_ceiling_usd
    if db is not None:
        cumulative = _get_cumulative_cost(db)
    else:
        cumulative = 0.0
    if cumulative + estimated_cost > ceiling:
        raise RuntimeError(
            f"Cost ceiling exceeded: {cumulative:.2f} + {estimated_cost:.2f} > {ceiling:.2f}"
        )


def record_cost(db: Session, model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate and return USD cost for a model call. Does not persist — caller stores it."""
    # Approximate pricing per 1M tokens (update as needed)
    pricing = {
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
        "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    }
    rates = pricing.get(model_name, {"input": 5.0, "output": 15.0})
    cost = (input_tokens * rates["input"] / 1_000_000) + (
        output_tokens * rates["output"] / 1_000_000
    )
    return round(cost, 6)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_cost.py -v`
Expected: 2 passed

- [ ] **Step 5: Create app/celery_app.py**

```python
from celery import Celery

from app.config import settings

celery = Celery("soundsright", broker=settings.redis_url)
celery.conf.update(
    result_backend=settings.redis_url,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Autodiscover tasks in all domain packages
celery.autodiscover_tasks(
    ["app.corpus", "app.rubric", "app.generator", "app.scorer"]
)
```

- [ ] **Step 6: Create app/embed.py**

```python
from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_text(text: str) -> list[float]:
    """Embed a single text string, return a 1536-dimensional vector."""
    client = _get_client()
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: Celery app, cost tracking, embedding utility"
```

---

## Task 4: Docker Compose + Migration Runner

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `infra/Dockerfile`
- Modify: `app/db.py` — add `migrate` function using raw SQL
- Modify: `Makefile` — add `migrate` target

- [ ] **Step 1: Create infra/docker-compose.yml**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: soundsright
      POSTGRES_PASSWORD: soundsright
      POSTGRES_DB: soundsright
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U soundsright"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  app:
    build:
      context: ..
      dockerfile: infra/Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
    ports:
      - "8080:8080"
    environment:
      SOUNDSRIGHT_DATABASE_URL: postgresql://soundsright:soundsright@postgres:5432/soundsright
      SOUNDSRIGHT_REDIS_URL: redis://redis:6379/1
      SOUNDSRIGHT_ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      SOUNDSRIGHT_OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      SOUNDSRIGHT_COST_CEILING_USD: ${COST_CEILING_USD:-50}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build:
      context: ..
      dockerfile: infra/Dockerfile
    command: celery -A app.celery_app:celery worker --loglevel=info -Q corpus,rubric,generate,score
    environment:
      SOUNDSRIGHT_DATABASE_URL: postgresql://soundsright:soundsright@postgres:5432/soundsright
      SOUNDSRIGHT_REDIS_URL: redis://redis:6379/1
      SOUNDSRIGHT_ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      SOUNDSRIGHT_OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      SOUNDSRIGHT_COST_CEILING_USD: ${COST_CEILING_USD:-50}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 2: Create infra/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Install the project
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 3: Update app/db.py — add import for sqlalchemy.text**

Add to the top of `app/db.py`:

```python
import pathlib

import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate():
    """Run migration SQL files in order."""
    migrations_dir = pathlib.Path(__file__).parent.parent / "migrations"
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        sql = sql_file.read_text()
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print(f"Applied: {sql_file.name}")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 4: Update Makefile**

Replace the `migrate` target:

```makefile
migrate:
	uv run python -c "from app.db import migrate; migrate()"
```

- [ ] **Step 5: Test locally — start Compose and run migration**

```bash
cd ~/code/soundsright
docker compose -f infra/docker-compose.yml up -d postgres redis
make migrate
```

Expected: "Applied: 001_initial.sql"

- [ ] **Step 6: Run model tests against real DB**

```bash
uv run pytest tests/test_models.py -v
```

Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: Docker Compose (postgres, redis, app, worker), Dockerfile, migration runner"
```

---

## Task 5: Corpus Domain — Router + Analyser + Celery Task

**Files:**
- Create: `app/corpus/router.py`
- Create: `app/corpus/analyser.py`
- Create: `app/corpus/tasks.py`
- Modify: `app/main.py` — mount corpus router
- Create: `tests/test_corpus.py`

- [ ] **Step 1: Write corpus router tests**

```python
import uuid


def test_create_corpus_entry(app_client, client):
    response = app_client.post(
        f"/api/corpus/{client.slug}/entries",
        json={"source_type": "social_post", "raw_text": "The breath moves before the body."},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["raw_text"] == "The breath moves before the body."
    assert data["client_id"] == str(client.id)


def test_list_corpus_entries(app_client, client, db_session):
    from app.models import CorpusEntry

    db_session.add(
        CorpusEntry(client_id=client.id, source_type="blog", raw_text="Sample text")
    )
    db_session.commit()

    response = app_client.get(f"/api/corpus/{client.slug}/entries")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_corpus_entry_unknown_client(app_client):
    response = app_client.post(
        "/api/corpus/nonexistent/entries",
        json={"source_type": "text", "raw_text": "test"},
    )
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_corpus.py -v`
Expected: FAIL — no route for `/api/corpus/`

- [ ] **Step 3: Create app/corpus/router.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, CorpusEntry
from app.schemas import CorpusEntryCreate, CorpusEntryOut

router = APIRouter(prefix="/api/corpus", tags=["corpus"])


def _get_client(slug: str, db: Session) -> Client:
    client = db.query(Client).filter(Client.slug == slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{slug}' not found")
    return client


@router.post("/{slug}/entries", response_model=CorpusEntryOut, status_code=201)
def create_entry(slug: str, body: CorpusEntryCreate, db: Session = Depends(get_db)):
    client = _get_client(slug, db)
    entry = CorpusEntry(
        client_id=client.id,
        source_type=body.source_type,
        raw_text=body.raw_text,
        metadata_=body.metadata,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{slug}/entries", response_model=list[CorpusEntryOut])
def list_entries(slug: str, db: Session = Depends(get_db)):
    client = _get_client(slug, db)
    return db.query(CorpusEntry).filter(CorpusEntry.client_id == client.id).all()


@router.post("/{slug}/analyse", status_code=202)
def trigger_analysis(slug: str, db: Session = Depends(get_db)):
    client = _get_client(slug, db)
    from app.corpus.tasks import analyse_corpus

    task = analyse_corpus.delay(str(client.id))
    return {"task_id": task.id, "status": "queued"}
```

- [ ] **Step 4: Create app/corpus/analyser.py**

```python
import json

import anthropic

from app.config import settings


def analyse_style(corpus_texts: list[str]) -> tuple[dict, float]:
    """Analyse a collection of texts and return structured style analysis + cost.

    Returns:
        (analysis_dict, cost_usd)
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    combined = "\n\n---\n\n".join(corpus_texts[:50])  # Cap at 50 entries per analysis

    response = client.messages.create(
        model=settings.analysis_model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""Analyse the following collection of texts written by a single author.
Produce a structured style analysis as JSON with these fields:

- tone_registers: array of objects with "register" (name) and "description" (when/how this tone appears)
- vocabulary_signatures: array of distinctive words/phrases this author uses repeatedly
- domain_terminology: array of specialised terms with their correct usage context
- cadence_patterns: description of sentence rhythm, paragraph structure, pacing
- warmth_authority_ratio: description of balance between warmth and authority
- distinctive_markers: array of other notable style elements

Texts:

{combined}

Return ONLY valid JSON, no markdown fences.""",
            }
        ],
    )

    cost_usd = (
        response.usage.input_tokens * 3.0 / 1_000_000
        + response.usage.output_tokens * 15.0 / 1_000_000
    )

    analysis = json.loads(response.content[0].text)
    return analysis, round(cost_usd, 6)
```

- [ ] **Step 5: Create app/corpus/tasks.py**

```python
from app.celery_app import celery
from app.config import settings
from app.db import SessionLocal
from app.models import Client, CorpusEntry, StyleAnalysis


@celery.task(name="corpus.analyse", queue="corpus")
def analyse_corpus(client_id: str) -> dict:
    """Analyse all corpus entries for a client and store the style analysis."""
    from app.corpus.analyser import analyse_style
    from app.cost import check_cost_ceiling

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return {"error": f"Client {client_id} not found"}

        entries = (
            db.query(CorpusEntry)
            .filter(CorpusEntry.client_id == client_id)
            .order_by(CorpusEntry.created_at)
            .all()
        )
        if not entries:
            return {"error": "No corpus entries found"}

        check_cost_ceiling(estimated_cost=0.10, db=db)

        texts = [e.raw_text for e in entries]
        analysis, cost_usd = analyse_style(texts)

        # Determine next version number
        latest = (
            db.query(StyleAnalysis)
            .filter(StyleAnalysis.client_id == client_id)
            .order_by(StyleAnalysis.version.desc())
            .first()
        )
        version = (latest.version + 1) if latest else 1

        sa = StyleAnalysis(
            client_id=client_id,
            version=version,
            analysis=analysis,
            model=settings.analysis_model,
            cost_usd=cost_usd,
        )
        db.add(sa)
        db.commit()

        return {"version": version, "cost_usd": cost_usd}
    finally:
        db.close()
```

- [ ] **Step 6: Mount corpus router in app/main.py**

```python
from fastapi import FastAPI

from app.corpus.router import router as corpus_router

app = FastAPI(title="SoundsRight", version="0.1.0")
app.include_router(corpus_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Run corpus tests**

Run: `uv run pytest tests/test_corpus.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: corpus domain — router, analyser, Celery task"
```

---

## Task 6: Rubric Domain — Router + Deriver + Celery Task

**Files:**
- Create: `app/rubric/router.py`
- Create: `app/rubric/deriver.py`
- Create: `app/rubric/tasks.py`
- Modify: `app/main.py` — mount rubric router
- Create: `tests/test_rubric.py`

- [ ] **Step 1: Write rubric router tests**

```python
from app.models import RubricDimension, StyleAnalysis


def test_list_dimensions_empty(app_client, client):
    response = app_client.get(f"/api/rubric/{client.slug}/dimensions")
    assert response.status_code == 200
    assert response.json() == []


def test_list_dimensions_with_data(app_client, client, db_session):
    db_session.add(
        RubricDimension(
            client_id=client.id,
            rubric_version=1,
            name="vocabulary_fidelity",
            label="Vocabulary Fidelity",
            description="Does the output use the client's actual words?",
        )
    )
    db_session.commit()

    response = app_client.get(f"/api/rubric/{client.slug}/dimensions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "vocabulary_fidelity"


def test_rubric_history(app_client, client, db_session):
    db_session.add(
        StyleAnalysis(
            client_id=client.id,
            version=1,
            analysis={"tone_registers": []},
            model="test-model",
            cost_usd=0.01,
        )
    )
    db_session.commit()

    response = app_client.get(f"/api/rubric/{client.slug}/history")
    assert response.status_code == 200
    assert len(response.json()) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_rubric.py -v`
Expected: FAIL — no route for `/api/rubric/`

- [ ] **Step 3: Create app/rubric/router.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, RubricDimension, StyleAnalysis
from app.schemas import RubricDimensionOut, StyleAnalysisOut

router = APIRouter(prefix="/api/rubric", tags=["rubric"])


def _get_client(slug: str, db: Session) -> Client:
    client = db.query(Client).filter(Client.slug == slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{slug}' not found")
    return client


@router.get("/{slug}/dimensions", response_model=list[RubricDimensionOut])
def list_dimensions(slug: str, version: int | None = None, db: Session = Depends(get_db)):
    client = _get_client(slug, db)
    query = db.query(RubricDimension).filter(RubricDimension.client_id == client.id)
    if version is not None:
        query = query.filter(RubricDimension.rubric_version == version)
    else:
        # Latest version
        latest = (
            db.query(RubricDimension.rubric_version)
            .filter(RubricDimension.client_id == client.id)
            .order_by(RubricDimension.rubric_version.desc())
            .first()
        )
        if latest:
            query = query.filter(RubricDimension.rubric_version == latest[0])
    return query.all()


@router.get("/{slug}/history", response_model=list[StyleAnalysisOut])
def rubric_history(slug: str, db: Session = Depends(get_db)):
    client = _get_client(slug, db)
    return (
        db.query(StyleAnalysis)
        .filter(StyleAnalysis.client_id == client.id)
        .order_by(StyleAnalysis.version.desc())
        .all()
    )


@router.post("/{slug}/derive", status_code=202)
def trigger_derivation(slug: str, db: Session = Depends(get_db)):
    client = _get_client(slug, db)
    from app.rubric.tasks import derive_rubric

    task = derive_rubric.delay(str(client.id))
    return {"task_id": task.id, "status": "queued"}
```

- [ ] **Step 4: Create app/rubric/deriver.py**

```python
import json

import anthropic

from app.config import settings


def derive_dimensions(style_analysis: dict) -> tuple[list[dict], float]:
    """Derive scoring rubric dimensions from a style analysis.

    Returns:
        (list of dimension dicts, cost_usd)
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model=settings.analysis_model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""Given this style analysis of a specific author, propose 4-7 scoring dimensions
that would distinguish content written by this person from generic content on the same topics.

Each dimension must be a JSON object with:
- "name": snake_case identifier
- "label": Human-readable label
- "description": 2-3 sentences explaining what a scorer should evaluate. Include what a high score (8-10) vs low score (1-3) looks like.
- "weight": float, default 1.0 (increase for dimensions more central to this author's identity)

Style analysis:
{json.dumps(style_analysis, indent=2)}

Return a JSON array of dimension objects. Return ONLY valid JSON, no markdown fences.""",
            }
        ],
    )

    cost_usd = (
        response.usage.input_tokens * 3.0 / 1_000_000
        + response.usage.output_tokens * 15.0 / 1_000_000
    )

    dimensions = json.loads(response.content[0].text)
    return dimensions, round(cost_usd, 6)
```

- [ ] **Step 5: Create app/rubric/tasks.py**

```python
from app.celery_app import celery
from app.config import settings
from app.db import SessionLocal
from app.models import Client, RubricDimension, StyleAnalysis


@celery.task(name="rubric.derive", queue="rubric")
def derive_rubric(client_id: str) -> dict:
    """Derive rubric dimensions from the latest style analysis."""
    from app.cost import check_cost_ceiling
    from app.rubric.deriver import derive_dimensions

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return {"error": f"Client {client_id} not found"}

        latest_analysis = (
            db.query(StyleAnalysis)
            .filter(StyleAnalysis.client_id == client_id)
            .order_by(StyleAnalysis.version.desc())
            .first()
        )
        if not latest_analysis:
            return {"error": "No style analysis found — run corpus analyse first"}

        check_cost_ceiling(estimated_cost=0.05, db=db)

        dimensions, cost_usd = derive_dimensions(latest_analysis.analysis)

        # Determine next rubric version
        latest_dim = (
            db.query(RubricDimension)
            .filter(RubricDimension.client_id == client_id)
            .order_by(RubricDimension.rubric_version.desc())
            .first()
        )
        rubric_version = (latest_dim.rubric_version + 1) if latest_dim else 1

        for dim in dimensions:
            db.add(
                RubricDimension(
                    client_id=client_id,
                    rubric_version=rubric_version,
                    name=dim["name"],
                    label=dim["label"],
                    description=dim["description"],
                    weight=dim.get("weight", 1.0),
                )
            )
        db.commit()

        return {
            "rubric_version": rubric_version,
            "dimensions": len(dimensions),
            "cost_usd": cost_usd,
        }
    finally:
        db.close()
```

- [ ] **Step 6: Mount rubric router in app/main.py**

```python
from fastapi import FastAPI

from app.corpus.router import router as corpus_router
from app.rubric.router import router as rubric_router

app = FastAPI(title="SoundsRight", version="0.1.0")
app.include_router(corpus_router)
app.include_router(rubric_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Run rubric tests**

Run: `uv run pytest tests/test_rubric.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: rubric domain — router, deriver, Celery task"
```

---

## Task 7: Generator Domain — Router + Engine + Celery Task

**Files:**
- Create: `app/generator/router.py`
- Create: `app/generator/engine.py`
- Create: `app/generator/tasks.py`
- Modify: `app/main.py` — mount generator router
- Create: `tests/test_generator.py`

- [ ] **Step 1: Write generator router tests**

```python
from app.models import Artifact, RubricDimension, StyleAnalysis


def test_list_artifacts_empty(app_client, client):
    response = app_client.get(f"/api/generator/{client.slug}/artifacts")
    assert response.status_code == 200
    assert response.json() == []


def test_list_artifacts_with_data(app_client, client, db_session):
    db_session.add(
        Artifact(
            client_id=client.id,
            prompt="morning routine",
            generated_text="Begin with three breaths.",
            model="test-model",
            rubric_version=1,
        )
    )
    db_session.commit()

    response = app_client.get(f"/api/generator/{client.slug}/artifacts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["prompt"] == "morning routine"


def test_list_artifacts_filter_by_status(app_client, client, db_session):
    db_session.add(
        Artifact(
            client_id=client.id,
            prompt="test",
            generated_text="text",
            model="m",
            rubric_version=1,
            status="scored",
        )
    )
    db_session.add(
        Artifact(
            client_id=client.id,
            prompt="test2",
            generated_text="text2",
            model="m",
            rubric_version=1,
            status="pending_score",
        )
    )
    db_session.commit()

    response = app_client.get(
        f"/api/generator/{client.slug}/artifacts?status=pending_score"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_generator.py -v`
Expected: FAIL — no route for `/api/generator/`

- [ ] **Step 3: Create app/generator/engine.py**

```python
import json

import anthropic
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.embed import embed_text
from app.models import Artifact, CorpusEntry, StyleAnalysis


def retrieve_few_shot_examples(
    db: Session, client_id: str, topic: str, limit: int = 5
) -> list[str]:
    """Retrieve topically relevant corpus entries and high-scored artifacts via pgvector cosine similarity."""
    topic_embedding = embed_text(topic)

    # Retrieve relevant corpus entries
    corpus_results = (
        db.query(CorpusEntry)
        .filter(
            CorpusEntry.client_id == client_id,
            CorpusEntry.embedding.isnot(None),
        )
        .order_by(CorpusEntry.embedding.cosine_distance(topic_embedding))
        .limit(limit)
        .all()
    )

    # Retrieve high-scored artifacts (status = "scored") that are topically relevant
    artifact_results = (
        db.query(Artifact)
        .filter(
            Artifact.client_id == client_id,
            Artifact.status == "scored",
            Artifact.embedding.isnot(None),
        )
        .order_by(Artifact.embedding.cosine_distance(topic_embedding))
        .limit(3)
        .all()
    )

    examples = [e.raw_text for e in corpus_results]
    examples += [a.generated_text for a in artifact_results]
    return examples


def generate_content(
    db: Session, client_id: str, topic: str
) -> tuple[str, float]:
    """Generate content in the client's voice using style analysis + few-shot examples.

    Returns:
        (generated_text, cost_usd)
    """
    # Get latest style analysis
    analysis = (
        db.query(StyleAnalysis)
        .filter(StyleAnalysis.client_id == client_id)
        .order_by(StyleAnalysis.version.desc())
        .first()
    )
    analysis_json = json.dumps(analysis.analysis, indent=2) if analysis else "{}"

    # Get few-shot examples
    examples = retrieve_few_shot_examples(db, client_id, topic)
    examples_block = "\n\n---\n\n".join(examples) if examples else "(no examples available yet)"

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model=settings.generation_model,
        max_tokens=2048,
        system=f"""You are writing content in the voice of a specific person. Your output must sound
exactly like them — their vocabulary, their cadence, their tone. Not a generic version. Them.

Style analysis of this person:
{analysis_json}

Examples of how this person actually writes and speaks:
{examples_block}

Match their style precisely. Use their actual vocabulary. Mirror their sentence rhythm.
No generic filler. No wellness slop. No "in today's fast-paced world" energy.""",
        messages=[
            {"role": "user", "content": f"Write a piece about: {topic}"}
        ],
    )

    cost_usd = (
        response.usage.input_tokens * 3.0 / 1_000_000
        + response.usage.output_tokens * 15.0 / 1_000_000
    )

    return response.content[0].text, round(cost_usd, 6)
```

- [ ] **Step 4: Create app/generator/router.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Artifact, Client
from app.schemas import ArtifactOut, GenerateRequest

router = APIRouter(prefix="/api/generator", tags=["generator"])


def _get_client(slug: str, db: Session) -> Client:
    client = db.query(Client).filter(Client.slug == slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{slug}' not found")
    return client


@router.get("/{slug}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(
    slug: str, status: str | None = None, db: Session = Depends(get_db)
):
    client = _get_client(slug, db)
    query = db.query(Artifact).filter(Artifact.client_id == client.id)
    if status:
        query = query.filter(Artifact.status == status)
    return query.order_by(Artifact.created_at.desc()).all()


@router.post("/{slug}/generate", status_code=202)
def trigger_generation(
    slug: str, body: GenerateRequest, db: Session = Depends(get_db)
):
    client = _get_client(slug, db)
    from app.generator.tasks import generate_content_task

    task = generate_content_task.delay(str(client.id), body.topic)
    return {"task_id": task.id, "status": "queued"}
```

- [ ] **Step 5: Create app/generator/tasks.py**

```python
from app.celery_app import celery
from app.config import settings
from app.db import SessionLocal
from app.models import Artifact, Client, RubricDimension


@celery.task(name="generator.generate", queue="generate")
def generate_content_task(client_id: str, topic: str) -> dict:
    """Generate content in the client's voice and store as artifact."""
    from app.cost import check_cost_ceiling
    from app.embed import embed_text
    from app.generator.engine import generate_content

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return {"error": f"Client {client_id} not found"}

        # Get current rubric version
        latest_dim = (
            db.query(RubricDimension)
            .filter(RubricDimension.client_id == client_id)
            .order_by(RubricDimension.rubric_version.desc())
            .first()
        )
        rubric_version = latest_dim.rubric_version if latest_dim else 0

        check_cost_ceiling(estimated_cost=0.05, db=db)

        generated_text, cost_usd = generate_content(db, client_id, topic)

        # Embed the generated text for future retrieval
        embedding = embed_text(generated_text)

        artifact = Artifact(
            client_id=client_id,
            prompt=topic,
            generated_text=generated_text,
            embedding=embedding,
            model=settings.generation_model,
            rubric_version=rubric_version,
            cost_usd=cost_usd,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        # Auto-enqueue LLM-as-judge scoring
        from app.scorer.tasks import auto_score

        auto_score.delay(str(artifact.id))

        return {"artifact_id": str(artifact.id), "cost_usd": cost_usd}
    finally:
        db.close()
```

- [ ] **Step 6: Mount generator router in app/main.py**

```python
from fastapi import FastAPI

from app.corpus.router import router as corpus_router
from app.generator.router import router as generator_router
from app.rubric.router import router as rubric_router

app = FastAPI(title="SoundsRight", version="0.1.0")
app.include_router(corpus_router)
app.include_router(rubric_router)
app.include_router(generator_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Run generator tests**

Run: `uv run pytest tests/test_generator.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: generator domain — router, engine (pgvector retrieval), Celery task"
```

---

## Task 8: Scorer Domain — Router + Judge + Preference Pairs + Celery Tasks

**Files:**
- Create: `app/scorer/router.py`
- Create: `app/scorer/judge.py`
- Create: `app/scorer/pairs.py`
- Create: `app/scorer/tasks.py`
- Modify: `app/main.py` — mount scorer router
- Create: `tests/test_scorer.py`

- [ ] **Step 1: Write scorer tests**

```python
from app.models import Artifact, RubricDimension, Score


def test_list_scores_empty(app_client, client, db_session):
    artifact = Artifact(
        client_id=client.id,
        prompt="test",
        generated_text="text",
        model="m",
        rubric_version=1,
    )
    db_session.add(artifact)
    db_session.commit()

    response = app_client.get(f"/api/scorer/artifacts/{artifact.id}/scores")
    assert response.status_code == 200
    assert response.json() == []


def test_submit_scores(app_client, client, db_session):
    dim = RubricDimension(
        client_id=client.id,
        rubric_version=1,
        name="tone",
        label="Tone Match",
        description="Does the tone match?",
    )
    artifact = Artifact(
        client_id=client.id,
        prompt="test",
        generated_text="text",
        model="m",
        rubric_version=1,
    )
    db_session.add_all([dim, artifact])
    db_session.commit()
    db_session.refresh(dim)
    db_session.refresh(artifact)

    response = app_client.post(
        f"/api/scorer/artifacts/{artifact.id}/scores",
        json={
            "scores": [{"dimension_id": str(dim.id), "score": 7}],
            "feedback": "Close but needs more warmth",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["score"] == 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer.py -v`
Expected: FAIL — no route for `/api/scorer/`

- [ ] **Step 3: Create app/scorer/judge.py**

```python
import json

import anthropic

from app.config import settings


def judge_artifact(
    generated_text: str, dimensions: list[dict]
) -> tuple[list[dict], float]:
    """LLM-as-judge: score an artifact against rubric dimensions.

    Args:
        generated_text: The content to evaluate
        dimensions: List of dicts with "id", "name", "label", "description"

    Returns:
        (list of {"dimension_id": str, "score": int}, cost_usd)
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    dims_block = "\n".join(
        f"- {d['label']} ({d['name']}): {d['description']}" for d in dimensions
    )

    response = client.messages.create(
        model=settings.judge_model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""Score the following generated content on each dimension (1-10).

Dimensions:
{dims_block}

Content to evaluate:
{generated_text}

Return a JSON array of objects with "name" (the dimension name) and "score" (integer 1-10).
Return ONLY valid JSON, no markdown fences.""",
            }
        ],
    )

    cost_usd = (
        response.usage.input_tokens * 3.0 / 1_000_000
        + response.usage.output_tokens * 15.0 / 1_000_000
    )

    scores_raw = json.loads(response.content[0].text)

    # Map scores back to dimension IDs
    name_to_id = {d["name"]: d["id"] for d in dimensions}
    scores = []
    for s in scores_raw:
        dim_id = name_to_id.get(s["name"])
        if dim_id:
            scores.append({
                "dimension_id": dim_id,
                "score": max(1, min(10, int(s["score"]))),
            })

    return scores, round(cost_usd, 6)
```

- [ ] **Step 4: Create app/scorer/pairs.py**

```python
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Artifact, Client, PreferencePair, Score


def derive_preference_pairs(db: Session, client_id: str) -> int:
    """Derive preference pairs from score deltas for a client.

    Returns the number of new pairs created.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return 0

    threshold = client.score_delta_threshold

    # Get all scored artifacts with their aggregate scores
    scored_artifacts = (
        db.query(
            Artifact.id,
            func.avg(Score.score).label("avg_score"),
        )
        .join(Score, Score.artifact_id == Artifact.id)
        .filter(
            Artifact.client_id == client_id,
            Artifact.status == "scored",
            Score.scorer_type == "human",
        )
        .group_by(Artifact.id)
        .all()
    )

    if len(scored_artifacts) < 2:
        return 0

    # Get existing pairs to avoid duplicates
    existing = set()
    for pair in db.query(PreferencePair).filter(PreferencePair.client_id == client_id).all():
        existing.add((str(pair.chosen_id), str(pair.rejected_id)))

    new_pairs = 0
    for i, (id_a, score_a) in enumerate(scored_artifacts):
        for id_b, score_b in scored_artifacts[i + 1 :]:
            delta = abs(float(score_a) - float(score_b))
            if delta >= threshold:
                chosen = id_a if score_a > score_b else id_b
                rejected = id_b if score_a > score_b else id_a
                key = (str(chosen), str(rejected))
                if key not in existing:
                    db.add(
                        PreferencePair(
                            client_id=client_id,
                            chosen_id=chosen,
                            rejected_id=rejected,
                            derived_from="score_delta",
                        )
                    )
                    existing.add(key)
                    new_pairs += 1

    db.commit()
    return new_pairs
```

- [ ] **Step 5: Create app/scorer/router.py**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Artifact, Client, PreferencePair, Score
from app.schemas import PreferencePairOut, ScoreOut, ScoreSubmission

router = APIRouter(prefix="/api/scorer", tags=["scorer"])


@router.get("/artifacts/{artifact_id}/scores", response_model=list[ScoreOut])
def list_scores(artifact_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(Score).filter(Score.artifact_id == artifact_id).all()


@router.post(
    "/artifacts/{artifact_id}/scores", response_model=list[ScoreOut], status_code=201
)
def submit_scores(
    artifact_id: uuid.UUID,
    body: ScoreSubmission,
    db: Session = Depends(get_db),
):
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    created_scores = []
    for s in body.scores:
        score = Score(
            artifact_id=artifact_id,
            dimension_id=s.dimension_id,
            score=s.score,
            scorer_type="human",
            scorer_id=artifact.client.slug,
        )
        db.add(score)
        created_scores.append(score)

    artifact.status = "scored"
    db.commit()
    for s in created_scores:
        db.refresh(s)

    # Trigger preference pair derivation
    from app.scorer.pairs import derive_preference_pairs

    derive_preference_pairs(db, str(artifact.client_id))

    return created_scores


@router.get("/{slug}/preference-pairs", response_model=list[PreferencePairOut])
def list_preference_pairs(slug: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.slug == slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{slug}' not found")
    return (
        db.query(PreferencePair)
        .filter(PreferencePair.client_id == client.id)
        .order_by(PreferencePair.created_at.desc())
        .all()
    )
```

- [ ] **Step 6: Create app/scorer/tasks.py**

```python
from app.celery_app import celery
from app.db import SessionLocal
from app.models import Artifact, RubricDimension, Score


@celery.task(name="scorer.auto_score", queue="score")
def auto_score(artifact_id: str) -> dict:
    """LLM-as-judge: auto-score an artifact against its rubric dimensions."""
    from app.cost import check_cost_ceiling
    from app.scorer.judge import judge_artifact

    db = SessionLocal()
    try:
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            return {"error": f"Artifact {artifact_id} not found"}

        dimensions = (
            db.query(RubricDimension)
            .filter(
                RubricDimension.client_id == artifact.client_id,
                RubricDimension.rubric_version == artifact.rubric_version,
            )
            .all()
        )
        if not dimensions:
            return {"error": "No rubric dimensions found for this version"}

        check_cost_ceiling(estimated_cost=0.02, db=db)

        dim_dicts = [
            {
                "id": str(d.id),
                "name": d.name,
                "label": d.label,
                "description": d.description,
            }
            for d in dimensions
        ]

        scores, cost_usd = judge_artifact(artifact.generated_text, dim_dicts)

        for s in scores:
            db.add(
                Score(
                    artifact_id=artifact_id,
                    dimension_id=s["dimension_id"],
                    score=s["score"],
                    scorer_type="llm_judge",
                    scorer_id=artifact.model,
                )
            )
        db.commit()

        return {"scores": len(scores), "cost_usd": cost_usd}
    finally:
        db.close()
```

- [ ] **Step 7: Mount scorer router in app/main.py**

```python
from fastapi import FastAPI

from app.corpus.router import router as corpus_router
from app.generator.router import router as generator_router
from app.rubric.router import router as rubric_router
from app.scorer.router import router as scorer_router

app = FastAPI(title="SoundsRight", version="0.1.0")
app.include_router(corpus_router)
app.include_router(rubric_router)
app.include_router(generator_router)
app.include_router(scorer_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Run scorer tests**

Run: `uv run pytest tests/test_scorer.py -v`
Expected: 2 passed

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: scorer domain — router, LLM-as-judge, preference pair derivation, Celery task"
```

---

## Task 9: Web UI — Token Auth + Jinja2/HTMX Scoring Interface

**Files:**
- Create: `app/web/auth.py`
- Create: `app/web/router.py`
- Create: `app/web/templates/base.html`
- Create: `app/web/templates/login.html`
- Create: `app/web/templates/dashboard.html`
- Create: `app/web/templates/artifacts.html`
- Create: `app/web/templates/score.html`
- Create: `app/web/templates/history.html`
- Create: `app/web/static/style.css`
- Modify: `app/main.py` — mount web router + static files + templates
- Create: `tests/test_web.py`

- [ ] **Step 1: Write web auth + routing tests**

```python
import secrets
from datetime import datetime, timedelta, timezone

from app.models import Artifact, AuthToken, RubricDimension


def _create_token(db_session, client, days=30):
    token = secrets.token_urlsafe(32)
    auth = AuthToken(
        client_id=client.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=days),
    )
    db_session.add(auth)
    db_session.commit()
    return token


def test_score_page_requires_token(app_client, client):
    response = app_client.get(f"/score/{client.slug}", follow_redirects=False)
    assert response.status_code in (401, 403)


def test_score_page_with_valid_token(app_client, client, db_session):
    token = _create_token(db_session, client)
    response = app_client.get(
        f"/score/{client.slug}?token={token}", follow_redirects=False
    )
    assert response.status_code == 200


def test_score_page_with_expired_token(app_client, client, db_session):
    token = _create_token(db_session, client, days=-1)
    response = app_client.get(
        f"/score/{client.slug}?token={token}", follow_redirects=False
    )
    assert response.status_code in (401, 403)


def test_score_page_with_revoked_token(app_client, client, db_session):
    token = _create_token(db_session, client)
    auth = db_session.query(AuthToken).filter(AuthToken.token == token).first()
    auth.revoked_at = datetime.now(timezone.utc)
    db_session.commit()

    response = app_client.get(
        f"/score/{client.slug}?token={token}", follow_redirects=False
    )
    assert response.status_code in (401, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_web.py -v`
Expected: FAIL — no route for `/score/`

- [ ] **Step 3: Create app/web/auth.py**

```python
from datetime import datetime, timezone

from fastapi import HTTPException, Query
from sqlalchemy.orm import Session

from app.models import AuthToken, Client


def validate_token(slug: str, token: str, db: Session) -> Client:
    """Validate a scoring token and return the associated client.

    Raises HTTPException(403) if token is invalid, expired, or revoked.
    """
    auth = (
        db.query(AuthToken)
        .join(Client)
        .filter(Client.slug == slug, AuthToken.token == token)
        .first()
    )

    if not auth:
        raise HTTPException(status_code=403, detail="Invalid token")

    if auth.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Token has been revoked")

    if auth.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Token has expired")

    return auth.client
```

- [ ] **Step 4: Create app/web/router.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Artifact, RubricDimension, Score
from app.schemas import ScoreSubmission
from app.web.auth import validate_token

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/score/{slug}", response_class=HTMLResponse)
def dashboard(
    request: Request,
    slug: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    client = validate_token(slug, token, db)

    unscored_count = (
        db.query(Artifact)
        .filter(Artifact.client_id == client.id, Artifact.status == "pending_score")
        .count()
    )

    recent_scores = (
        db.query(Score)
        .join(Artifact)
        .filter(Artifact.client_id == client.id, Score.scorer_type == "human")
        .order_by(Score.created_at.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "client": client,
            "token": token,
            "unscored_count": unscored_count,
            "recent_scores": recent_scores,
        },
    )


@router.get("/score/{slug}/artifacts", response_class=HTMLResponse)
def artifact_list(
    request: Request,
    slug: str,
    token: str = Query(...),
    status: str = "pending_score",
    page: int = 1,
    db: Session = Depends(get_db),
):
    client = validate_token(slug, token, db)
    per_page = 20
    offset = (page - 1) * per_page

    query = db.query(Artifact).filter(Artifact.client_id == client.id)
    if status:
        query = query.filter(Artifact.status == status)

    artifacts = query.order_by(Artifact.created_at.desc()).offset(offset).limit(per_page).all()
    total = query.count()

    return templates.TemplateResponse(
        "artifacts.html",
        {
            "request": request,
            "client": client,
            "token": token,
            "artifacts": artifacts,
            "status": status,
            "page": page,
            "total": total,
            "has_next": offset + per_page < total,
        },
    )


@router.get("/score/{slug}/artifact/{artifact_id}", response_class=HTMLResponse)
def score_artifact(
    request: Request,
    slug: str,
    artifact_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    client = validate_token(slug, token, db)

    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact or artifact.client_id != client.id:
        raise HTTPException(status_code=404, detail="Artifact not found")

    dimensions = (
        db.query(RubricDimension)
        .filter(
            RubricDimension.client_id == client.id,
            RubricDimension.rubric_version == artifact.rubric_version,
        )
        .all()
    )

    return templates.TemplateResponse(
        "score.html",
        {
            "request": request,
            "client": client,
            "token": token,
            "artifact": artifact,
            "dimensions": dimensions,
        },
    )


@router.post("/score/{slug}/artifact/{artifact_id}/submit", response_class=HTMLResponse)
async def submit_score(
    request: Request,
    slug: str,
    artifact_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    client = validate_token(slug, token, db)

    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact or artifact.client_id != client.id:
        raise HTTPException(status_code=404, detail="Artifact not found")

    form = await request.form()

    dimensions = (
        db.query(RubricDimension)
        .filter(
            RubricDimension.client_id == client.id,
            RubricDimension.rubric_version == artifact.rubric_version,
        )
        .all()
    )

    for dim in dimensions:
        score_val = form.get(f"score_{dim.id}")
        if score_val:
            db.add(
                Score(
                    artifact_id=artifact_id,
                    dimension_id=dim.id,
                    score=int(score_val),
                    scorer_type="human",
                    scorer_id=client.slug,
                )
            )

    artifact.status = "scored"
    db.commit()

    # Trigger preference pair derivation
    from app.scorer.pairs import derive_preference_pairs

    derive_preference_pairs(db, str(client.id))

    # Load next unscored artifact via HTMX
    next_artifact = (
        db.query(Artifact)
        .filter(
            Artifact.client_id == client.id,
            Artifact.status == "pending_score",
        )
        .order_by(Artifact.created_at)
        .first()
    )

    if next_artifact:
        new_dimensions = (
            db.query(RubricDimension)
            .filter(
                RubricDimension.client_id == client.id,
                RubricDimension.rubric_version == next_artifact.rubric_version,
            )
            .all()
        )
        return templates.TemplateResponse(
            "score.html",
            {
                "request": request,
                "client": client,
                "token": token,
                "artifact": next_artifact,
                "dimensions": new_dimensions,
                "success": True,
            },
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "client": client,
            "token": token,
            "unscored_count": 0,
            "recent_scores": [],
            "success": "All artifacts scored!",
        },
    )


@router.get("/score/{slug}/history", response_class=HTMLResponse)
def score_history(
    request: Request,
    slug: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    client = validate_token(slug, token, db)

    scored_artifacts = (
        db.query(Artifact)
        .filter(Artifact.client_id == client.id, Artifact.status == "scored")
        .order_by(Artifact.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "client": client,
            "token": token,
            "artifacts": scored_artifacts,
        },
    )
```

- [ ] **Step 5: Create app/web/templates/base.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}SoundsRight{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@2.0.0"></script>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav>
        <a href="/score/{{ client.slug }}?token={{ token }}">Dashboard</a>
        <a href="/score/{{ client.slug }}/artifacts?token={{ token }}">Artifacts</a>
        <a href="/score/{{ client.slug }}/history?token={{ token }}">History</a>
    </nav>
    <main>
        {% if success %}
        <div class="success">{{ success }}</div>
        {% endif %}
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

- [ ] **Step 6: Create app/web/templates/dashboard.html**

```html
{% extends "base.html" %}
{% block title %}Dashboard — SoundsRight{% endblock %}
{% block content %}
<h1>Welcome, {{ client.name }}</h1>
<div class="stats">
    <div class="stat">
        <span class="stat-value">{{ unscored_count }}</span>
        <span class="stat-label">Waiting for your review</span>
    </div>
</div>
{% if unscored_count > 0 %}
<a href="/score/{{ client.slug }}/artifacts?token={{ token }}&status=pending_score" class="btn">
    Start Scoring
</a>
{% endif %}
{% endblock %}
```

- [ ] **Step 7: Create app/web/templates/artifacts.html**

```html
{% extends "base.html" %}
{% block title %}Artifacts — SoundsRight{% endblock %}
{% block content %}
<h1>Artifacts</h1>
<div class="filters">
    <a href="?token={{ token }}&status=pending_score" class="{% if status == 'pending_score' %}active{% endif %}">Unscored</a>
    <a href="?token={{ token }}&status=scored" class="{% if status == 'scored' %}active{% endif %}">Scored</a>
</div>
<div class="artifact-list">
    {% for artifact in artifacts %}
    <div class="artifact-card">
        <div class="artifact-topic">{{ artifact.prompt }}</div>
        <div class="artifact-preview">{{ artifact.generated_text[:200] }}...</div>
        {% if artifact.status == 'pending_score' %}
        <a href="/score/{{ client.slug }}/artifact/{{ artifact.id }}?token={{ token }}" class="btn btn-small">Score</a>
        {% endif %}
    </div>
    {% endfor %}
</div>
{% if has_next %}
<a href="?token={{ token }}&status={{ status }}&page={{ page + 1 }}" class="btn">Load More</a>
{% endif %}
{% endblock %}
```

- [ ] **Step 8: Create app/web/templates/score.html**

```html
{% extends "base.html" %}
{% block title %}Score — SoundsRight{% endblock %}
{% block content %}
<div class="score-page">
    <div class="artifact-display">
        <div class="artifact-topic">Topic: {{ artifact.prompt }}</div>
        <div class="artifact-text">{{ artifact.generated_text }}</div>
    </div>

    <form hx-post="/score/{{ client.slug }}/artifact/{{ artifact.id }}/submit?token={{ token }}"
          hx-target="main"
          hx-swap="innerHTML">
        <div class="dimensions">
            {% for dim in dimensions %}
            <div class="dimension">
                <label for="score_{{ dim.id }}">
                    <strong>{{ dim.label }}</strong>
                    <span class="dim-desc">{{ dim.description }}</span>
                </label>
                <div class="slider-row">
                    <input type="range" id="score_{{ dim.id }}" name="score_{{ dim.id }}"
                           min="1" max="10" value="5"
                           oninput="this.nextElementSibling.textContent = this.value">
                    <span class="slider-value">5</span>
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="feedback">
            <label for="feedback">What's off about this one? (optional)</label>
            <textarea id="feedback" name="feedback" rows="3"></textarea>
        </div>

        <button type="submit" class="btn">Submit Scores</button>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 9: Create app/web/templates/history.html**

```html
{% extends "base.html" %}
{% block title %}History — SoundsRight{% endblock %}
{% block content %}
<h1>Score History</h1>
<div class="history-list">
    {% for artifact in artifacts %}
    <div class="history-card">
        <div class="artifact-topic">{{ artifact.prompt }}</div>
        <div class="artifact-preview">{{ artifact.generated_text[:150] }}...</div>
        <div class="scores-summary">
            {% for score in artifact.scores %}
            {% if score.scorer_type == 'human' %}
            <span class="score-badge">{{ score.dimension.label }}: {{ score.score }}/10</span>
            {% endif %}
            {% endfor %}
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}
```

- [ ] **Step 10: Create app/web/templates/login.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SoundsRight</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <main class="login">
        <h1>SoundsRight</h1>
        <p>Please use the scoring link provided to you.</p>
    </main>
</body>
</html>
```

- [ ] **Step 11: Create app/web/static/style.css**

```css
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 640px;
    margin: 0 auto;
    padding: 1rem;
    background: #fafafa;
    color: #1a1a1a;
}

nav {
    display: flex;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid #e0e0e0;
    margin-bottom: 1.5rem;
}

nav a { color: #555; text-decoration: none; font-size: 0.9rem; }
nav a:hover { color: #1a1a1a; }

h1 { font-size: 1.5rem; margin-bottom: 1rem; }

.stats { margin: 1.5rem 0; }
.stat { text-align: center; }
.stat-value { font-size: 3rem; font-weight: 700; display: block; }
.stat-label { color: #666; font-size: 0.9rem; }

.btn {
    display: inline-block;
    background: #1a1a1a;
    color: white;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
    text-decoration: none;
}
.btn:hover { background: #333; }
.btn-small { padding: 0.4rem 0.8rem; font-size: 0.85rem; }

.artifact-card, .history-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.artifact-topic { font-weight: 600; margin-bottom: 0.5rem; }
.artifact-preview { color: #555; font-size: 0.9rem; line-height: 1.5; }
.artifact-text { line-height: 1.8; font-size: 1.05rem; margin: 1rem 0; white-space: pre-wrap; }

.dimension { margin-bottom: 1.5rem; }
.dimension label { display: block; margin-bottom: 0.5rem; }
.dim-desc { display: block; color: #666; font-size: 0.85rem; font-weight: normal; margin-top: 0.25rem; }

.slider-row { display: flex; align-items: center; gap: 1rem; }
.slider-row input[type="range"] { flex: 1; }
.slider-value { font-weight: 700; font-size: 1.2rem; min-width: 2rem; text-align: center; }

.feedback { margin: 1.5rem 0; }
.feedback label { display: block; margin-bottom: 0.5rem; color: #555; }
.feedback textarea { width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 6px; font-family: inherit; }

.success { background: #e8f5e9; color: #2e7d32; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; }

.filters { display: flex; gap: 1rem; margin-bottom: 1rem; }
.filters a { color: #555; text-decoration: none; padding: 0.4rem 0.8rem; border-radius: 4px; }
.filters a.active { background: #1a1a1a; color: white; }

.score-badge {
    display: inline-block;
    background: #f0f0f0;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    margin: 0.25rem 0.25rem 0 0;
}

.login { text-align: center; padding-top: 4rem; }
```

- [ ] **Step 12: Mount web router and static files in app/main.py**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.corpus.router import router as corpus_router
from app.generator.router import router as generator_router
from app.rubric.router import router as rubric_router
from app.scorer.router import router as scorer_router
from app.web.router import router as web_router

app = FastAPI(title="SoundsRight", version="0.1.0")
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
app.include_router(corpus_router)
app.include_router(rubric_router)
app.include_router(generator_router)
app.include_router(scorer_router)
app.include_router(web_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 13: Run web tests**

Run: `uv run pytest tests/test_web.py -v`
Expected: 4 passed

- [ ] **Step 14: Commit**

```bash
git add -A
git commit -m "feat: web UI — Jinja2/HTMX scoring interface with token auth"
```

---

## Task 10: CLI — voicectl

**Files:**
- Create: `cli/voicectl/cli.py`
- Create: `cli/voicectl/commands/client.py`
- Create: `cli/voicectl/commands/corpus.py`
- Create: `cli/voicectl/commands/rubric.py`
- Create: `cli/voicectl/commands/generate.py`
- Create: `cli/voicectl/commands/jobs.py`
- Create: `cli/voicectl/commands/score.py`
- Create: `cli/voicectl/commands/cost.py`
- Create: `cli/voicectl/commands/serve.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

```python
from unittest.mock import patch

from click.testing import CliRunner

from cli.voicectl.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "voicectl" in result.output.lower() or "Usage" in result.output


def test_client_list(db_session):
    from app.models import Client

    db_session.add(Client(name="Aura", slug="aura"))
    db_session.commit()

    runner = CliRunner()
    with patch("cli.voicectl.commands.client.SessionLocal", return_value=db_session):
        result = runner.invoke(main, ["client", "list"])
    assert result.exit_code == 0
    assert "aura" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — no `cli.voicectl.cli` module

- [ ] **Step 3: Create cli/voicectl/cli.py**

```python
import click

from cli.voicectl.commands.client import client_group
from cli.voicectl.commands.corpus import corpus_group
from cli.voicectl.commands.cost import cost_cmd
from cli.voicectl.commands.generate import generate_cmd
from cli.voicectl.commands.jobs import jobs_group
from cli.voicectl.commands.rubric import rubric_group
from cli.voicectl.commands.score import score_group
from cli.voicectl.commands.serve import serve_cmd


@click.group()
def main():
    """voicectl — SoundsRight pipeline operator CLI."""
    pass


main.add_command(client_group, "client")
main.add_command(corpus_group, "corpus")
main.add_command(rubric_group, "rubric")
main.add_command(generate_cmd, "generate")
main.add_command(jobs_group, "jobs")
main.add_command(score_group, "score")
main.add_command(cost_cmd, "cost")
main.add_command(serve_cmd, "serve")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create cli/voicectl/commands/client.py**

```python
import secrets
from datetime import datetime, timedelta, timezone

import click
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AuthToken, Client


@click.group()
def client_group():
    """Client management."""
    pass


@client_group.command("add")
@click.argument("name")
@click.option("--slug", required=True)
def add_client(name: str, slug: str):
    """Add a new client."""
    db = SessionLocal()
    try:
        c = Client(name=name, slug=slug)
        db.add(c)
        db.commit()
        click.echo(f"Created client: {name} ({slug})")
    finally:
        db.close()


@client_group.command("list")
def list_clients():
    """List all clients."""
    db = SessionLocal()
    try:
        clients = db.query(Client).all()
        for c in clients:
            click.echo(f"{c.slug:20s} {c.name}")
    finally:
        db.close()


@client_group.command("token")
@click.argument("slug")
@click.option("--days", default=30, help="Token expiry in days")
def create_token(slug: str, days: int):
    """Generate a scoring UI link for a client."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)

        token = secrets.token_urlsafe(32)
        auth = AuthToken(
            client_id=client.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=days),
        )
        db.add(auth)
        db.commit()

        click.echo(f"Token: {token}")
        click.echo(f"URL:   http://localhost:8080/score/{slug}?token={token}")
        click.echo(f"Expires: {auth.expires_at.isoformat()}")
    finally:
        db.close()


@client_group.command("token-revoke")
@click.argument("token")
def revoke_token(token: str):
    """Revoke a specific token."""
    db = SessionLocal()
    try:
        auth = db.query(AuthToken).filter(AuthToken.token == token).first()
        if not auth:
            click.echo("Token not found", err=True)
            raise SystemExit(1)
        auth.revoked_at = datetime.now(timezone.utc)
        db.commit()
        click.echo("Token revoked.")
    finally:
        db.close()


@client_group.command("token-list")
@click.argument("slug")
def list_tokens(slug: str):
    """List active tokens for a client."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)
        tokens = (
            db.query(AuthToken)
            .filter(
                AuthToken.client_id == client.id,
                AuthToken.revoked_at.is_(None),
                AuthToken.expires_at > datetime.now(timezone.utc),
            )
            .all()
        )
        for t in tokens:
            click.echo(f"{t.token[:16]}...  expires {t.expires_at.date()}")
    finally:
        db.close()
```

- [ ] **Step 5: Create cli/voicectl/commands/corpus.py**

```python
import pathlib

import click

from app.db import SessionLocal
from app.embed import embed_text
from app.models import Client, CorpusEntry


@click.group()
def corpus_group():
    """Corpus management."""
    pass


@corpus_group.command("ingest")
@click.argument("slug")
@click.option("--source", type=click.Path(exists=True), help="Directory of text files")
@click.option("--text", help="Raw text to ingest")
def ingest(slug: str, source: str | None, text: str | None):
    """Ingest text into a client's corpus."""
    if not source and not text:
        click.echo("Provide --source or --text", err=True)
        raise SystemExit(1)

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)

        entries = []
        if source:
            for f in sorted(pathlib.Path(source).glob("*.txt")):
                entries.append(("text", f.read_text()))
            for f in sorted(pathlib.Path(source).glob("*.md")):
                entries.append(("text", f.read_text()))
        if text:
            entries.append(("text", text))

        for source_type, raw_text in entries:
            embedding = embed_text(raw_text)
            db.add(
                CorpusEntry(
                    client_id=client.id,
                    source_type=source_type,
                    raw_text=raw_text,
                    embedding=embedding,
                )
            )

        db.commit()
        click.echo(f"Ingested {len(entries)} entries for {slug}")
    finally:
        db.close()


@corpus_group.command("list")
@click.argument("slug")
def list_entries(slug: str):
    """List corpus entries for a client."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)
        entries = db.query(CorpusEntry).filter(CorpusEntry.client_id == client.id).all()
        click.echo(f"{len(entries)} entries")
        for e in entries:
            preview = e.raw_text[:80].replace("\n", " ")
            click.echo(f"  [{e.source_type}] {preview}...")
    finally:
        db.close()


@corpus_group.command("analyse")
@click.argument("slug")
def analyse(slug: str):
    """Enqueue corpus style analysis."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)
        from app.corpus.tasks import analyse_corpus

        task = analyse_corpus.delay(str(client.id))
        click.echo(f"Queued analysis: {task.id}")
    finally:
        db.close()
```

- [ ] **Step 6: Create cli/voicectl/commands/rubric.py**

```python
import click

from app.db import SessionLocal
from app.models import Client, RubricDimension, StyleAnalysis


@click.group()
def rubric_group():
    """Rubric management."""
    pass


@rubric_group.command("derive")
@click.argument("slug")
def derive(slug: str):
    """Enqueue rubric derivation from latest style analysis."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)
        from app.rubric.tasks import derive_rubric

        task = derive_rubric.delay(str(client.id))
        click.echo(f"Queued derivation: {task.id}")
    finally:
        db.close()


@rubric_group.command("show")
@click.argument("slug")
def show(slug: str):
    """Show current rubric dimensions."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)

        latest = (
            db.query(RubricDimension.rubric_version)
            .filter(RubricDimension.client_id == client.id)
            .order_by(RubricDimension.rubric_version.desc())
            .first()
        )
        if not latest:
            click.echo("No rubric derived yet.")
            return

        dims = (
            db.query(RubricDimension)
            .filter(
                RubricDimension.client_id == client.id,
                RubricDimension.rubric_version == latest[0],
            )
            .all()
        )
        click.echo(f"Rubric v{latest[0]} — {len(dims)} dimensions:")
        for d in dims:
            click.echo(f"  {d.label} ({d.name}) — weight {d.weight}")
            click.echo(f"    {d.description}")
    finally:
        db.close()


@rubric_group.command("history")
@click.argument("slug")
def history(slug: str):
    """Show rubric version history."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)
        analyses = (
            db.query(StyleAnalysis)
            .filter(StyleAnalysis.client_id == client.id)
            .order_by(StyleAnalysis.version.desc())
            .all()
        )
        for a in analyses:
            click.echo(f"  v{a.version}  {a.created_at.date()}  model={a.model}  cost=${a.cost_usd}")
    finally:
        db.close()
```

- [ ] **Step 7: Create cli/voicectl/commands/generate.py**

```python
import click

from app.db import SessionLocal
from app.models import Client


@click.command()
@click.argument("slug")
@click.option("--topic", help="Single topic to generate")
@click.option("--topics", type=click.Path(exists=True), help="File with topics (one per line)")
@click.option("--count", default=1, help="Number of artifacts per topic")
def generate_cmd(slug: str, topic: str | None, topics: str | None, count: int):
    """Generate content in a client's voice."""
    if not topic and not topics:
        click.echo("Provide --topic or --topics", err=True)
        raise SystemExit(1)

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)

        from app.generator.tasks import generate_content_task

        topic_list = []
        if topic:
            topic_list.append(topic)
        if topics:
            import pathlib

            topic_list.extend(
                line.strip()
                for line in pathlib.Path(topics).read_text().splitlines()
                if line.strip()
            )

        queued = 0
        for t in topic_list:
            for _ in range(count):
                generate_content_task.delay(str(client.id), t)
                queued += 1

        click.echo(f"Queued {queued} generation jobs for {slug}")
    finally:
        db.close()
```

- [ ] **Step 8: Create cli/voicectl/commands/jobs.py**

```python
import click
from celery.result import AsyncResult

from app.celery_app import celery


@click.group()
def jobs_group():
    """Job management."""
    pass


@jobs_group.command("list")
def list_jobs():
    """List recent jobs (requires Celery result backend)."""
    # Note: Celery doesn't natively list all tasks. This queries active/reserved.
    inspector = celery.control.inspect()
    active = inspector.active() or {}
    reserved = inspector.reserved() or {}

    click.echo("Active:")
    for worker, tasks in active.items():
        for t in tasks:
            click.echo(f"  {t['id'][:12]}  {t['name']}  started={t.get('time_start', '?')}")

    click.echo("Reserved:")
    for worker, tasks in reserved.items():
        for t in tasks:
            click.echo(f"  {t['id'][:12]}  {t['name']}")


@jobs_group.command("status")
@click.argument("task_id")
def job_status(task_id: str):
    """Check status of a specific job."""
    result = AsyncResult(task_id, app=celery)
    click.echo(f"Task:   {task_id}")
    click.echo(f"Status: {result.status}")
    if result.ready():
        click.echo(f"Result: {result.result}")
```

- [ ] **Step 9: Create cli/voicectl/commands/score.py**

```python
import json

import click

from app.db import SessionLocal
from app.models import Artifact, Client, PreferencePair


@click.group()
def score_group():
    """Scoring operations."""
    pass


@score_group.command("auto")
@click.argument("slug")
def auto_score(slug: str):
    """Enqueue LLM-as-judge scoring on unscored artifacts."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)

        from app.scorer.tasks import auto_score as auto_score_task

        artifacts = (
            db.query(Artifact)
            .filter(
                Artifact.client_id == client.id,
                Artifact.status == "pending_score",
            )
            .all()
        )
        for a in artifacts:
            auto_score_task.delay(str(a.id))

        click.echo(f"Queued auto-score for {len(artifacts)} artifacts")
    finally:
        db.close()


@score_group.command("list")
@click.argument("slug")
def list_scores(slug: str):
    """List score summary for a client."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)

        artifacts = (
            db.query(Artifact)
            .filter(Artifact.client_id == client.id, Artifact.status == "scored")
            .all()
        )
        for a in artifacts:
            human_scores = [s for s in a.scores if s.scorer_type == "human"]
            avg = sum(s.score for s in human_scores) / len(human_scores) if human_scores else 0
            click.echo(f"  {str(a.id)[:8]}  avg={avg:.1f}  {a.prompt[:50]}")
    finally:
        db.close()


@score_group.command("export")
@click.argument("slug")
@click.option("--format", "fmt", default="pairs", type=click.Choice(["pairs", "scores"]))
def export_scores(slug: str, fmt: str):
    """Export preference pairs or raw scores as JSONL."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)

        if fmt == "pairs":
            pairs = (
                db.query(PreferencePair)
                .filter(PreferencePair.client_id == client.id)
                .all()
            )
            for p in pairs:
                chosen = db.query(Artifact).filter(Artifact.id == p.chosen_id).first()
                rejected = db.query(Artifact).filter(Artifact.id == p.rejected_id).first()
                click.echo(
                    json.dumps(
                        {
                            "chosen": chosen.generated_text if chosen else "",
                            "rejected": rejected.generated_text if rejected else "",
                            "prompt": chosen.prompt if chosen else "",
                            "derived_from": p.derived_from,
                        }
                    )
                )
    finally:
        db.close()
```

- [ ] **Step 10: Create cli/voicectl/commands/cost.py**

```python
import click
from sqlalchemy import func

from app.db import SessionLocal
from app.models import Artifact, Client, StyleAnalysis


@click.command()
@click.argument("slug")
@click.option("--by", "by_stage", type=click.Choice(["stage"]), help="Breakdown by stage")
def cost_cmd(slug: str, by_stage: str | None):
    """Show cost for a client."""
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.slug == slug).first()
        if not client:
            click.echo(f"Client '{slug}' not found", err=True)
            raise SystemExit(1)

        analysis_cost = (
            db.query(func.coalesce(func.sum(StyleAnalysis.cost_usd), 0))
            .filter(StyleAnalysis.client_id == client.id)
            .scalar()
        )
        generation_cost = (
            db.query(func.coalesce(func.sum(Artifact.cost_usd), 0))
            .filter(Artifact.client_id == client.id)
            .scalar()
        )

        total = float(analysis_cost) + float(generation_cost)

        if by_stage:
            click.echo(f"Analysis:   ${float(analysis_cost):.4f}")
            click.echo(f"Generation: ${float(generation_cost):.4f}")
            click.echo(f"Total:      ${total:.4f}")
        else:
            click.echo(f"Total cost for {slug}: ${total:.4f}")
    finally:
        db.close()
```

- [ ] **Step 11: Create cli/voicectl/commands/serve.py**

```python
import click


@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8080)
def serve_cmd(host: str, port: int):
    """Start the SoundsRight web server."""
    import uvicorn

    uvicorn.run("app.main:app", host=host, port=port, reload=True)
```

- [ ] **Step 12: Run CLI tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 2 passed

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "feat: voicectl CLI — client, corpus, rubric, generate, jobs, score, cost, serve"
```

---

## Task 11: K8s Manifests

**Files:**
- Create: `infra/k8s/namespace.yaml`
- Create: `infra/k8s/deployment.yaml`
- Create: `infra/k8s/service.yaml`
- Create: `infra/k8s/secrets.yaml`

- [ ] **Step 1: Create infra/k8s/namespace.yaml**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: soundsright
```

- [ ] **Step 2: Create infra/k8s/deployment.yaml**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: soundsright
  namespace: soundsright
spec:
  replicas: 1
  selector:
    matchLabels:
      app: soundsright
  template:
    metadata:
      labels:
        app: soundsright
    spec:
      containers:
        - name: app
          image: localhost:5000/soundsright:dev
          command: ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
          ports:
            - containerPort: 8080
          envFrom:
            - secretRef:
                name: soundsright-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10

        - name: worker
          image: localhost:5000/soundsright:dev
          command: ["uv", "run", "celery", "-A", "app.celery_app:celery", "worker", "--loglevel=info", "-Q", "corpus,rubric,generate,score"]
          envFrom:
            - secretRef:
                name: soundsright-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

- [ ] **Step 3: Create infra/k8s/service.yaml**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: soundsright
  namespace: soundsright
spec:
  selector:
    app: soundsright
  ports:
    - port: 8080
      targetPort: 8080
  type: ClusterIP
```

- [ ] **Step 4: Create infra/k8s/secrets.yaml (template)**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: soundsright-secrets
  namespace: soundsright
type: Opaque
stringData:
  SOUNDSRIGHT_DATABASE_URL: "postgresql://soundsright:CHANGEME@postgres:5432/soundsright"
  SOUNDSRIGHT_REDIS_URL: "redis://redis:6379/1"
  SOUNDSRIGHT_ANTHROPIC_API_KEY: "CHANGEME"
  SOUNDSRIGHT_OPENAI_API_KEY: "CHANGEME"
  SOUNDSRIGHT_COST_CEILING_USD: "50"
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: K8s manifests — namespace, deployment, service, secrets template"
```

---

## Task 12: Integration Test — Full Pipeline Smoke Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
"""
Integration test: exercises the full pipeline with mocked LLM calls.
Requires Postgres + Redis running.
"""
from unittest.mock import patch

from app.models import (
    Artifact,
    Client,
    CorpusEntry,
    RubricDimension,
    Score,
    StyleAnalysis,
)


def test_full_pipeline(db_session):
    """Ingest → analyse → derive rubric → score → preference pairs."""
    # 1. Create client
    client = Client(name="Test Creator", slug="test-creator")
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)

    # 2. Ingest corpus entries
    for text in [
        "The breath moves before the body moves. In stillness, we find the origin.",
        "When you practice skin breathing, you are not doing. You are allowing.",
        "Qi Gong is not exercise. It is a conversation with your nervous system.",
    ]:
        db_session.add(
            CorpusEntry(client_id=client.id, source_type="text", raw_text=text)
        )
    db_session.commit()

    # 3. Style analysis (mocked)
    analysis = StyleAnalysis(
        client_id=client.id,
        version=1,
        analysis={
            "tone_registers": [{"register": "meditative", "description": "Soft, unhurried"}],
            "vocabulary_signatures": ["breath", "stillness", "origin", "allowing"],
            "domain_terminology": ["Qi Gong", "skin breathing", "nervous system"],
            "cadence_patterns": "Short declarative sentences. Pause-heavy rhythm.",
            "warmth_authority_ratio": "70% warmth, 30% authority",
        },
        model="test",
        cost_usd=0.01,
    )
    db_session.add(analysis)
    db_session.commit()

    # 4. Derive rubric dimensions (manually for test)
    dims = [
        RubricDimension(
            client_id=client.id,
            rubric_version=1,
            name="vocabulary_fidelity",
            label="Vocabulary Fidelity",
            description="Uses the client's actual words",
        ),
        RubricDimension(
            client_id=client.id,
            rubric_version=1,
            name="tone_match",
            label="Tone Match",
            description="Warmth-to-authority ratio matches",
        ),
    ]
    db_session.add_all(dims)
    db_session.commit()
    for d in dims:
        db_session.refresh(d)

    # 5. Create artifacts (simulating generation)
    good_artifact = Artifact(
        client_id=client.id,
        prompt="morning routine",
        generated_text="Begin with three breaths. Feel the stillness before you move.",
        model="test",
        rubric_version=1,
    )
    bad_artifact = Artifact(
        client_id=client.id,
        prompt="morning routine",
        generated_text="Start your day with an energizing workout to unlock your potential!",
        model="test",
        rubric_version=1,
    )
    db_session.add_all([good_artifact, bad_artifact])
    db_session.commit()
    db_session.refresh(good_artifact)
    db_session.refresh(bad_artifact)

    # 6. Score artifacts
    for dim in dims:
        db_session.add(Score(artifact_id=good_artifact.id, dimension_id=dim.id, score=9, scorer_type="human", scorer_id="test-creator"))
        db_session.add(Score(artifact_id=bad_artifact.id, dimension_id=dim.id, score=2, scorer_type="human", scorer_id="test-creator"))
    good_artifact.status = "scored"
    bad_artifact.status = "scored"
    db_session.commit()

    # 7. Derive preference pairs
    from app.scorer.pairs import derive_preference_pairs

    new_pairs = derive_preference_pairs(db_session, str(client.id))
    assert new_pairs == 1  # 9 avg vs 2 avg, delta = 7 > threshold 3

    # 8. Verify the pair
    from app.models import PreferencePair

    pair = db_session.query(PreferencePair).filter(PreferencePair.client_id == client.id).first()
    assert pair is not None
    assert pair.chosen_id == good_artifact.id
    assert pair.rejected_id == bad_artifact.id
    assert pair.derived_from == "score_delta"
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/test_integration.py -v`
Expected: 1 passed

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: full pipeline integration test — ingest through preference pairs"
```

---

## Task 13: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
# SoundsRight

Voice-fidelity pipeline: client-specific AI alignment via structured rubrics and preference scoring.

Ingest a client's text corpus. Analyse their style. Derive scoring dimensions. Generate content in their voice. Score it (LLM-as-judge + human). Close the feedback loop.

## Quick Start

```bash
# Start backing services
docker compose -f infra/docker-compose.yml up -d

# Run migrations
make migrate

# Create a client
voicectl client add "Aura Enache" --slug aura

# Ingest corpus text
voicectl corpus ingest aura --source ./texts/

# Analyse style
voicectl corpus analyse aura

# Derive rubric
voicectl rubric derive aura

# Generate content
voicectl generate aura --topic "morning qi gong routine"

# Generate scoring link for client
voicectl client token aura

# Start the web server
voicectl serve
```

## Architecture

Modular monolith: one FastAPI process, one Celery worker, PostgreSQL + pgvector, Redis.

See `docs/superpowers/specs/2026-04-10-voice-fidelity-pipeline-design.md` for the full design specification.

## Development

```bash
uv sync           # Install dependencies
make dev          # Start Docker Compose
make test         # Run tests
make migrate      # Run database migrations
make serve        # Start dev server
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with quick start and architecture overview"
```
