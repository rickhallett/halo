# changoctl Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build changoctl — Chango's survival inventory with mood-aware atmospheric actions, curated quotes, and Neo4j graph projection.

**Architecture:** Standard halos module (cli.py + store.py + engine.py pattern). SQLite source of truth at `store/changoctl.db` with three tables (inventory, consumption_log, quotes). Thin Neo4j adapter dual-writes to Beachhead on OrbStack via optional `neo4j` dependency. `flavour.py` provides deterministic atmospheric action templates. `engine.py` orchestrates the `sustain` ritual and exposes `text_summary()` for briefing integration.

**Tech Stack:** Python 3.11+, SQLite, argparse, neo4j (optional), halos.common (paths, log)

**Spec:** `docs/superpowers/specs/2026-04-10-changoctl-design.md`

---

### Task 1: Module Scaffold and Registration

**Files:**
- Create: `halos/changoctl/__init__.py`
- Create: `halos/changoctl/config.py`
- Modify: `pyproject.toml:29-30` (optional-dependencies), `pyproject.toml:60` (scripts)

- [ ] **Step 1: Create module directory and __init__.py**

```python
# halos/changoctl/__init__.py
"""changoctl — survival inventory and atmospheric personality engine."""
```

- [ ] **Step 2: Create config.py**

```python
# halos/changoctl/config.py
"""changoctl configuration and path resolution."""

import os
from halos.common.paths import store_dir

DB_PATH = store_dir() / "changoctl.db"

BEACHHEAD_URI = os.environ.get("BEACHHEAD_URI", "bolt://localhost:7687")
BEACHHEAD_USER = os.environ.get("BEACHHEAD_USER", "neo4j")
BEACHHEAD_PASS = os.environ.get("BEACHHEAD_PASS", "neo4j")

VALID_ITEMS = ("espresso", "lagavulin", "stimpacks", "nos")
VALID_MOODS = ("grind", "locked-in", "burnt-out", "fire")
VALID_CATEGORIES = ("sardonic", "strategic", "lethal", "philosophical")

MOOD_ITEM_MAP = {
    "grind": "espresso",
    "locked-in": "stimpacks",
    "burnt-out": "lagavulin",
    "fire": "nos",
}

MOOD_CATEGORY_MAP = {
    "grind": "strategic",
    "locked-in": "lethal",
    "burnt-out": "philosophical",
    "fire": "sardonic",
}
```

- [ ] **Step 3: Register in pyproject.toml — add console_scripts entry**

Add to `[project.scripts]` section after the `advisorctl` line:

```toml
changoctl = "halos.changoctl.cli:main"
```

- [ ] **Step 4: Register in pyproject.toml — add neo4j optional dependency**

Update the `[project.optional-dependencies]` `graph` line:

```toml
graph = ["networkx>=3.0", "pyvis>=0.3.2", "neo4j>=5.0"]
```

- [ ] **Step 5: Commit**

```bash
git add halos/changoctl/__init__.py halos/changoctl/config.py pyproject.toml
git commit -m "feat(changoctl): scaffold module and register in pyproject.toml"
```

---

### Task 2: SQLite Store — Schema and Inventory CRUD

**Files:**
- Create: `halos/changoctl/store.py`
- Create: `tests/test_changoctl_store.py`

- [ ] **Step 1: Write failing tests for store — schema seeding and inventory CRUD**

```python
# tests/test_changoctl_store.py
"""Tests for changoctl SQLite store."""

import pytest

from halos.changoctl.store import (
    get_inventory,
    restock,
    consume,
    _connect,
)


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_changoctl.db"


class TestInventory:
    def test_seed_on_connect(self, tmp_db):
        """First connect seeds all four items at stock 0."""
        conn = _connect(tmp_db)
        rows = conn.execute("SELECT * FROM inventory ORDER BY item").fetchall()
        conn.close()
        items = [dict(r)["item"] for r in rows]
        assert items == ["espresso", "lagavulin", "nos", "stimpacks"]
        for r in rows:
            assert dict(r)["stock"] == 0

    def test_get_inventory(self, tmp_db):
        inv = get_inventory(db_path=tmp_db)
        assert len(inv) == 4
        assert all(i["stock"] == 0 for i in inv)

    def test_restock_default(self, tmp_db):
        result = restock("espresso", db_path=tmp_db)
        assert result["stock"] == 1
        assert result["item"] == "espresso"

    def test_restock_quantity(self, tmp_db):
        result = restock("lagavulin", quantity=6, db_path=tmp_db)
        assert result["stock"] == 6

    def test_restock_accumulates(self, tmp_db):
        restock("nos", quantity=3, db_path=tmp_db)
        result = restock("nos", quantity=2, db_path=tmp_db)
        assert result["stock"] == 5

    def test_restock_invalid_item(self, tmp_db):
        with pytest.raises(ValueError, match="invalid item"):
            restock("bourbon", db_path=tmp_db)

    def test_consume_decrements(self, tmp_db):
        restock("stimpacks", quantity=3, db_path=tmp_db)
        result = consume("stimpacks", mood="locked-in", db_path=tmp_db)
        assert result["stock"] == 2
        assert result["log_entry"]["item"] == "stimpacks"
        assert result["log_entry"]["mood"] == "locked-in"
        assert result["log_entry"]["quantity"] == 1

    def test_consume_out_of_stock(self, tmp_db):
        """Out of stock: logs at quantity 0, stock stays 0."""
        result = consume("espresso", mood="grind", db_path=tmp_db)
        assert result["stock"] == 0
        assert result["log_entry"]["quantity"] == 0
        assert result["out_of_stock"] is True

    def test_consume_invalid_item(self, tmp_db):
        with pytest.raises(ValueError, match="invalid item"):
            consume("bourbon", db_path=tmp_db)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_store.py -v`
Expected: FAIL — ImportError (store.py does not exist yet)

- [ ] **Step 3: Implement store.py — schema, inventory, consume**

```python
# halos/changoctl/store.py
"""SQLite storage layer for changoctl.

Three tables: inventory (current stock), consumption_log (append-only history),
quotes (curated Chango lines). Schema auto-created on first connect.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import DB_PATH, VALID_ITEMS


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open and initialise the changoctl database."""
    path = db_path if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL UNIQUE,
            stock INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consumption_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            mood TEXT,
            timestamp TEXT NOT NULL,
            session_context TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_consumption_timestamp
        ON consumption_log(timestamp)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            source_session TEXT,
            source_module TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    # Seed inventory rows if empty
    count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    if count == 0:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for item in sorted(VALID_ITEMS):
            conn.execute(
                "INSERT INTO inventory (item, stock, updated_at) VALUES (?, 0, ?)",
                (item, now),
            )
        conn.commit()
    return conn


def _validate_item(item: str) -> None:
    if item not in VALID_ITEMS:
        raise ValueError(f"invalid item: {item!r} (must be one of {VALID_ITEMS})")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_inventory(db_path: Optional[Path] = None) -> list[dict]:
    """Return all inventory rows."""
    conn = _connect(db_path)
    rows = conn.execute("SELECT * FROM inventory ORDER BY item").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stock(item: str, db_path: Optional[Path] = None) -> int:
    """Return current stock for a single item."""
    _validate_item(item)
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT stock FROM inventory WHERE item = ?", (item,)
    ).fetchone()
    conn.close()
    return row["stock"] if row else 0


def restock(
    item: str, quantity: int = 1, db_path: Optional[Path] = None
) -> dict:
    """Add stock. Returns updated inventory row."""
    _validate_item(item)
    now = _now()
    conn = _connect(db_path)
    conn.execute(
        "UPDATE inventory SET stock = stock + ?, updated_at = ? WHERE item = ?",
        (quantity, now, item),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM inventory WHERE item = ?", (item,)
    ).fetchone()
    conn.close()
    return dict(row)


def consume(
    item: str,
    mood: Optional[str] = None,
    session_context: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Consume one unit. Logs even when out of stock (quantity=0).

    Returns dict with keys: stock, out_of_stock, log_entry.
    """
    _validate_item(item)
    now = _now()
    conn = _connect(db_path)

    row = conn.execute(
        "SELECT stock FROM inventory WHERE item = ?", (item,)
    ).fetchone()
    current_stock = row["stock"] if row else 0
    out_of_stock = current_stock <= 0

    if not out_of_stock:
        conn.execute(
            "UPDATE inventory SET stock = stock - 1, updated_at = ? WHERE item = ?",
            (now, item),
        )
        quantity = 1
    else:
        quantity = 0

    conn.execute(
        "INSERT INTO consumption_log (item, quantity, mood, timestamp, session_context) "
        "VALUES (?, ?, ?, ?, ?)",
        (item, quantity, mood, now, session_context),
    )
    conn.commit()

    new_stock_row = conn.execute(
        "SELECT stock FROM inventory WHERE item = ?", (item,)
    ).fetchone()
    log_row = conn.execute(
        "SELECT * FROM consumption_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    return {
        "stock": new_stock_row["stock"],
        "out_of_stock": out_of_stock,
        "log_entry": dict(log_row),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_store.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add halos/changoctl/store.py tests/test_changoctl_store.py
git commit -m "feat(changoctl): SQLite store — inventory CRUD and consumption logging"
```

---

### Task 3: SQLite Store — Quotes and History

**Files:**
- Modify: `halos/changoctl/store.py`
- Modify: `tests/test_changoctl_store.py`

- [ ] **Step 1: Write failing tests for quotes and history**

Append to `tests/test_changoctl_store.py`:

```python
from halos.changoctl.store import (
    add_quote,
    list_quotes,
    random_quote,
    list_consumption_history,
)


class TestQuotes:
    def test_add_quote(self, tmp_db):
        q = add_quote(
            "The cluster doesn't care about your feelings.",
            category="sardonic",
            db_path=tmp_db,
        )
        assert q["id"] == 1
        assert q["category"] == "sardonic"

    def test_add_quote_with_metadata(self, tmp_db):
        q = add_quote(
            "Ship it or shut up.",
            category="lethal",
            source_session="sess-001",
            source_module="nightctl",
            db_path=tmp_db,
        )
        assert q["source_session"] == "sess-001"
        assert q["source_module"] == "nightctl"

    def test_add_duplicate_raises(self, tmp_db):
        add_quote("Unique line.", category="strategic", db_path=tmp_db)
        with pytest.raises(sqlite3.IntegrityError):
            add_quote("Unique line.", category="strategic", db_path=tmp_db)

    def test_add_quote_invalid_category(self, tmp_db):
        with pytest.raises(ValueError, match="invalid category"):
            add_quote("Whatever.", category="funny", db_path=tmp_db)

    def test_list_quotes_all(self, tmp_db):
        add_quote("Line one.", category="sardonic", db_path=tmp_db)
        add_quote("Line two.", category="strategic", db_path=tmp_db)
        quotes = list_quotes(db_path=tmp_db)
        assert len(quotes) == 2

    def test_list_quotes_by_category(self, tmp_db):
        add_quote("Sardonic one.", category="sardonic", db_path=tmp_db)
        add_quote("Strategic one.", category="strategic", db_path=tmp_db)
        quotes = list_quotes(category="sardonic", db_path=tmp_db)
        assert len(quotes) == 1
        assert quotes[0]["category"] == "sardonic"

    def test_random_quote_empty(self, tmp_db):
        result = random_quote(db_path=tmp_db)
        assert result is None

    def test_random_quote_with_mood(self, tmp_db):
        add_quote("Fire line.", category="sardonic", db_path=tmp_db)
        add_quote("Calm line.", category="philosophical", db_path=tmp_db)
        # mood "fire" maps to category "sardonic" via engine, but
        # random_quote filters by category directly
        result = random_quote(category="sardonic", db_path=tmp_db)
        assert result is not None
        assert result["category"] == "sardonic"

    def test_random_quote_no_match(self, tmp_db):
        add_quote("Only sardonic.", category="sardonic", db_path=tmp_db)
        result = random_quote(category="lethal", db_path=tmp_db)
        assert result is None


class TestHistory:
    def test_list_history_empty(self, tmp_db):
        history = list_consumption_history(db_path=tmp_db)
        assert history == []

    def test_list_history_after_consume(self, tmp_db):
        restock("espresso", quantity=2, db_path=tmp_db)
        consume("espresso", mood="grind", db_path=tmp_db)
        consume("espresso", mood="grind", db_path=tmp_db)
        history = list_consumption_history(db_path=tmp_db)
        assert len(history) == 2
        # Newest first
        assert history[0]["id"] > history[1]["id"]

    def test_list_history_by_item(self, tmp_db):
        restock("espresso", quantity=1, db_path=tmp_db)
        restock("nos", quantity=1, db_path=tmp_db)
        consume("espresso", db_path=tmp_db)
        consume("nos", db_path=tmp_db)
        history = list_consumption_history(item="espresso", db_path=tmp_db)
        assert len(history) == 1
        assert history[0]["item"] == "espresso"

    def test_list_history_by_days(self, tmp_db):
        restock("espresso", quantity=1, db_path=tmp_db)
        consume("espresso", db_path=tmp_db)
        # Recent entry should appear in 7-day window
        history = list_consumption_history(days=7, db_path=tmp_db)
        assert len(history) == 1
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_store.py::TestQuotes -v`
Expected: FAIL — ImportError (add_quote not yet defined)

- [ ] **Step 3: Add quote and history functions to store.py**

Append to `halos/changoctl/store.py`:

```python
def add_quote(
    text: str,
    category: str,
    source_session: Optional[str] = None,
    source_module: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Add a curated quote. Returns created row."""
    from .config import VALID_CATEGORIES

    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"invalid category: {category!r} (must be one of {VALID_CATEGORIES})"
        )

    now = _now()
    conn = _connect(db_path)
    cur = conn.execute(
        "INSERT INTO quotes (text, category, source_session, source_module, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (text, category, source_session, source_module, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM quotes WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return dict(row)


def list_quotes(
    category: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    """List quotes, optionally filtered by category. Newest first."""
    conn = _connect(db_path)
    if category:
        rows = conn.execute(
            "SELECT * FROM quotes WHERE category = ? ORDER BY created_at DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM quotes ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def random_quote(
    category: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """Return a random quote, optionally filtered by category. None if empty."""
    conn = _connect(db_path)
    if category:
        row = conn.execute(
            "SELECT * FROM quotes WHERE category = ? ORDER BY RANDOM() LIMIT 1",
            (category,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_consumption_history(
    item: Optional[str] = None,
    days: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    """List consumption log entries, newest first."""
    conn = _connect(db_path)
    query = "SELECT * FROM consumption_log"
    params: list = []
    clauses: list[str] = []

    if item:
        clauses.append("item = ?")
        params.append(item)

    if days is not None:
        from datetime import timedelta
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        clauses.append("timestamp >= ?")
        params.append(cutoff)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY timestamp DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_quotes(db_path: Optional[Path] = None) -> int:
    """Total number of quotes."""
    conn = _connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
    conn.close()
    return count
```

- [ ] **Step 4: Run all store tests**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_store.py -v`
Expected: All tests PASS (inventory + quotes + history)

- [ ] **Step 5: Commit**

```bash
git add halos/changoctl/store.py tests/test_changoctl_store.py
git commit -m "feat(changoctl): quotes CRUD and consumption history queries"
```

---

### Task 4: Flavour Templates

**Files:**
- Create: `halos/changoctl/flavour.py`
- Create: `tests/test_changoctl_flavour.py`

- [ ] **Step 1: Write failing tests for flavour**

```python
# tests/test_changoctl_flavour.py
"""Tests for changoctl flavour — atmospheric action templates."""

from halos.changoctl.flavour import TEMPLATES, random_action
from halos.changoctl.config import VALID_ITEMS


class TestFlavour:
    def test_all_items_have_templates(self):
        for item in VALID_ITEMS:
            assert item in TEMPLATES, f"Missing templates for {item}"
            assert len(TEMPLATES[item]) >= 3, f"Need >= 3 templates for {item}"

    def test_templates_are_strings(self):
        for item, actions in TEMPLATES.items():
            for action in actions:
                assert isinstance(action, str)
                assert len(action) > 10

    def test_random_action_returns_string(self):
        action = random_action("espresso")
        assert isinstance(action, str)

    def test_random_action_formatted_with_asterisks(self):
        action = random_action("lagavulin")
        assert action.startswith("*")
        assert action.endswith("*")

    def test_random_action_invalid_item(self):
        import pytest
        with pytest.raises(KeyError):
            random_action("bourbon")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_flavour.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement flavour.py**

```python
# halos/changoctl/flavour.py
"""Atmospheric action templates for changoctl.

Hardcoded, deterministic, no LLM calls. Each item has 3-5 action strings
that get wrapped in asterisks and randomly selected at consumption time.
"""

import random


TEMPLATES: dict[str, list[str]] = {
    "espresso": [
        "Pulls a double shot from the machine",
        "Sips synthetic espresso and opens a terminal",
        "Fires up the espresso machine, watches the crema settle",
        "Knocks back a cortado without looking up from the logs",
        "Cradles a tiny cup of black gold, steam curling upward",
    ],
    "lagavulin": [
        "Pours a neat Lagavulin 16",
        "Swirls the glass and stares at the deploy logs",
        "Uncorks the Lagavulin, lets the peat fill the room",
        "Pours two fingers of Islay courage into a heavy glass",
        "Raises a glass of liquid smoke to the dying cluster",
    ],
    "stimpacks": [
        "Cracks a stimpack and rolls up the sleeves",
        "Jabs a stimpack into the forearm",
        "Cracks a stimpack and pulls up the terminal",
        "Slams a stimpack, pupils dilating to match the screen refresh rate",
    ],
    "nos": [
        "Cracks a NOS and watches the cluster burn",
        "Shotguns a NOS, wipes the screen clean",
        "Pops a NOS, the caffeine hitting like a kubectl rollout restart",
        "Crushes a NOS can and drops it in the recycling with extreme prejudice",
    ],
}


def random_action(item: str) -> str:
    """Return a random atmospheric action for the given item, wrapped in asterisks."""
    template = random.choice(TEMPLATES[item])
    return f"*{template}*"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_flavour.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add halos/changoctl/flavour.py tests/test_changoctl_flavour.py
git commit -m "feat(changoctl): atmospheric action templates in flavour.py"
```

---

### Task 5: Engine — sustain Logic and text_summary

**Files:**
- Create: `halos/changoctl/engine.py`
- Create: `tests/test_changoctl_engine.py`

- [ ] **Step 1: Write failing tests for engine**

```python
# tests/test_changoctl_engine.py
"""Tests for changoctl engine — sustain ritual and text_summary."""

import pytest
from unittest.mock import patch

from halos.changoctl.engine import sustain, text_summary
from halos.changoctl.store import restock, add_quote


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_changoctl.db"


class TestSustain:
    def test_sustain_with_stock(self, tmp_db):
        restock("espresso", quantity=3, db_path=tmp_db)
        result = sustain("grind", db_path=tmp_db)
        assert result["item"] == "espresso"
        assert result["stock"] == 2
        assert result["mood"] == "grind"
        assert result["action"].startswith("*")
        assert result["action"].endswith("*")
        assert result["out_of_stock"] is False

    def test_sustain_with_quote(self, tmp_db):
        restock("lagavulin", quantity=1, db_path=tmp_db)
        add_quote(
            "The margins are everything.",
            category="philosophical",
            db_path=tmp_db,
        )
        result = sustain("burnt-out", db_path=tmp_db)
        assert result["quote"] is not None
        assert result["quote"]["text"] == "The margins are everything."

    def test_sustain_no_matching_quote(self, tmp_db):
        restock("stimpacks", quantity=1, db_path=tmp_db)
        # No quotes at all
        result = sustain("locked-in", db_path=tmp_db)
        assert result["quote"] is None

    def test_sustain_fallback_item(self, tmp_db):
        """Primary item empty, falls back to whatever has stock."""
        # espresso is out, but lagavulin has stock
        restock("lagavulin", quantity=2, db_path=tmp_db)
        result = sustain("grind", db_path=tmp_db)
        # Should have consumed lagavulin as fallback
        assert result["item"] == "lagavulin"
        assert result["out_of_stock"] is False

    def test_sustain_all_empty(self, tmp_db):
        """Everything out of stock — still works, logs qty 0."""
        result = sustain("fire", db_path=tmp_db)
        assert result["out_of_stock"] is True
        assert result["item"] == "nos"  # Primary for fire, even though empty
        assert result["stock"] == 0

    def test_sustain_invalid_mood(self, tmp_db):
        with pytest.raises(ValueError, match="invalid mood"):
            sustain("chill", db_path=tmp_db)

    def test_sustain_formatted_output(self, tmp_db):
        restock("nos", quantity=1, db_path=tmp_db)
        add_quote("Ship it.", category="sardonic", db_path=tmp_db)
        result = sustain("fire", db_path=tmp_db)
        output = result["formatted"]
        assert "*" in output
        assert "Ship it." in output
        assert "nos:" in output
        assert "fire" in output


class TestTextSummary:
    def test_text_summary_empty(self, tmp_db):
        summary = text_summary(db_path=tmp_db)
        assert "espresso: 0" in summary
        assert "lagavulin: 0" in summary

    def test_text_summary_with_stock(self, tmp_db):
        restock("espresso", quantity=5, db_path=tmp_db)
        restock("lagavulin", quantity=2, db_path=tmp_db)
        summary = text_summary(db_path=tmp_db)
        assert "espresso: 5" in summary
        assert "lagavulin: 2" in summary

    def test_text_summary_includes_quote_count(self, tmp_db):
        add_quote("Test line.", category="sardonic", db_path=tmp_db)
        summary = text_summary(db_path=tmp_db)
        assert "1 quote" in summary
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_engine.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement engine.py**

```python
# halos/changoctl/engine.py
"""changoctl engine — sustain ritual, mood logic, and briefing surface.

The sustain command is the signature interaction: resolve mood, pick item,
consume, pair with quote, return formatted atmospheric action.
"""

from pathlib import Path
from typing import Optional

from .config import MOOD_ITEM_MAP, MOOD_CATEGORY_MAP, VALID_MOODS
from . import store
from .flavour import random_action


def sustain(
    mood: str,
    session_context: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Full sustain ritual. Returns dict with all components.

    Keys: item, stock, mood, action, quote, out_of_stock, formatted, log_entry.
    """
    if mood not in VALID_MOODS:
        raise ValueError(f"invalid mood: {mood!r} (must be one of {VALID_MOODS})")

    primary_item = MOOD_ITEM_MAP[mood]
    primary_stock = store.get_stock(primary_item, db_path=db_path)

    # Pick item: primary if stocked, else fallback to any with stock
    if primary_stock > 0:
        chosen_item = primary_item
    else:
        # Find any item with stock
        inventory = store.get_inventory(db_path=db_path)
        fallback = [i for i in inventory if i["stock"] > 0]
        if fallback:
            chosen_item = fallback[0]["item"]
        else:
            chosen_item = primary_item  # All empty — use primary anyway

    # Consume
    result = store.consume(
        chosen_item, mood=mood, session_context=session_context, db_path=db_path
    )

    # Atmospheric action
    action = random_action(chosen_item)

    # Quote pairing
    category = MOOD_CATEGORY_MAP[mood]
    quote = store.random_quote(category=category, db_path=db_path)

    # Format output
    formatted = _format_sustain(action, quote, chosen_item, result["stock"], mood)

    return {
        "item": chosen_item,
        "stock": result["stock"],
        "mood": mood,
        "action": action,
        "quote": quote,
        "out_of_stock": result["out_of_stock"],
        "formatted": formatted,
        "log_entry": result["log_entry"],
    }


def _format_sustain(
    action: str,
    quote: Optional[dict],
    item: str,
    stock: int,
    mood: str,
) -> str:
    """Format the sustain output: action + quote + status line."""
    parts = [action, ""]

    if quote:
        parts.append(f'"{quote["text"]}"')
        parts.append("")

    remaining = f"{stock} remaining" if stock > 0 else "EMPTY -- restock"
    parts.append(f"[{item}: {remaining} | mood: {mood}]")

    return "\n".join(parts)


def text_summary(db_path: Optional[Path] = None) -> str:
    """One-line summary for briefing integration.

    Example: "changoctl: espresso: 5, lagavulin: 2, stimpacks: 0, nos: 3 | 12 quotes"
    """
    inventory = store.get_inventory(db_path=db_path)
    quote_count = store.count_quotes(db_path=db_path)

    stock_parts = [f"{i['item']}: {i['stock']}" for i in inventory]
    stock_str = ", ".join(stock_parts)

    q_label = "quote" if quote_count == 1 else "quotes"
    return f"changoctl: {stock_str} | {quote_count} {q_label}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_engine.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add halos/changoctl/engine.py tests/test_changoctl_engine.py
git commit -m "feat(changoctl): sustain engine with mood-item mapping and text_summary"
```

---

### Task 6: CLI

**Files:**
- Create: `halos/changoctl/cli.py`
- Create: `tests/test_changoctl_cli.py`

- [ ] **Step 1: Write failing tests for CLI**

```python
# tests/test_changoctl_cli.py
"""Tests for changoctl CLI — subcommand dispatch and output."""

import json
from unittest.mock import patch

import pytest

from halos.changoctl.cli import main as cli_main


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_changoctl.db"


class TestCLI:
    @staticmethod
    def _patch_db(tmp_db):
        return patch("halos.changoctl.store.DB_PATH", tmp_db)

    def test_help_returns_zero(self):
        ret = cli_main([])
        assert ret == 0

    def test_status(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["status"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "espresso" in out

    def test_status_json(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["--json", "status"])
        assert ret == 0
        data = json.loads(capsys.readouterr().out)
        assert "inventory" in data

    def test_restock(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["restock", "espresso", "--quantity", "5"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "espresso" in out
        assert "5" in out

    def test_restock_invalid_item(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["restock", "bourbon"])
        assert ret == 1

    def test_consume(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["restock", "nos", "--quantity", "2"])
            ret = cli_main(["consume", "nos", "--mood", "fire"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "*" in out  # Atmospheric action

    def test_sustain(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["restock", "lagavulin", "--quantity", "3"])
            ret = cli_main(["sustain", "--mood", "burnt-out"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "*" in out
        assert "lagavulin" in out

    def test_quote_add(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main([
                "quote", "add", "The margins are everything.",
                "--category", "philosophical",
            ])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Added quote #1" in out

    def test_quote_list(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main([
                "quote", "add", "Line one.", "--category", "sardonic",
            ])
            ret = cli_main(["quote", "list"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Line one." in out

    def test_quote_random(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main([
                "quote", "add", "Ship it.", "--category", "lethal",
            ])
            ret = cli_main(["quote", "random"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Ship it." in out

    def test_history(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["restock", "espresso", "--quantity", "1"])
            cli_main(["consume", "espresso", "--mood", "grind"])
            ret = cli_main(["history"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "espresso" in out

    def test_history_json(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["restock", "espresso", "--quantity", "1"])
            cli_main(["consume", "espresso"])
            ret = cli_main(["--json", "history"])
        assert ret == 0
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_cli.py -v`
Expected: FAIL — ImportError (cli.py does not exist)

- [ ] **Step 3: Implement cli.py**

```python
# halos/changoctl/cli.py
"""changoctl CLI — survival inventory and atmospheric personality engine."""

import argparse
import json
import sys

from . import store
from .engine import sustain, text_summary
from halos.common.log import hlog


def cmd_status(args) -> int:
    inventory = store.get_inventory()
    quote_count = store.count_quotes()

    if args.json_out:
        print(json.dumps({
            "inventory": inventory,
            "quote_count": quote_count,
        }, indent=2))
    else:
        print("=== Chango's Cabinet ===")
        for item in inventory:
            stock = item["stock"]
            label = "EMPTY" if stock == 0 else str(stock)
            print(f"  {item['item']}: {label}")
        print(f"\n  quotes: {quote_count}")

    return 0


def cmd_restock(args) -> int:
    try:
        result = store.restock(args.item, quantity=args.quantity)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    hlog("changoctl", "info", "restock", {
        "item": args.item, "quantity": args.quantity, "stock": result["stock"],
    })

    if args.json_out:
        print(json.dumps(result, indent=2))
    else:
        print(f"Restocked {args.item}: now {result['stock']}")

    return 0


def cmd_consume(args) -> int:
    try:
        result = store.consume(args.item, mood=args.mood)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    from .flavour import random_action
    action = random_action(args.item)

    hlog("changoctl", "info", "consume", {
        "item": args.item, "mood": args.mood, "stock": result["stock"],
        "out_of_stock": result["out_of_stock"],
    })

    if args.json_out:
        print(json.dumps({
            "action": action,
            "stock": result["stock"],
            "out_of_stock": result["out_of_stock"],
            "log_entry": result["log_entry"],
        }, indent=2))
    else:
        print(action)
        if result["out_of_stock"]:
            print(f"\n[{args.item}: EMPTY -- restock]")
        else:
            print(f"\n[{args.item}: {result['stock']} remaining]")

    return 0


def cmd_sustain(args) -> int:
    try:
        result = sustain(args.mood)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    hlog("changoctl", "info", "sustain", {
        "item": result["item"], "mood": args.mood, "stock": result["stock"],
        "out_of_stock": result["out_of_stock"],
        "quote_id": result["quote"]["id"] if result["quote"] else None,
    })

    if args.json_out:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result["formatted"])

    return 0


def cmd_quote_add(args) -> int:
    text = " ".join(args.text) if args.text else ""
    if not text:
        print("error: no quote text provided", file=sys.stderr)
        return 1

    try:
        q = store.add_quote(
            text,
            category=args.category,
            source_module=args.source_module,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    hlog("changoctl", "info", "quote_added", {
        "id": q["id"], "category": args.category,
    })

    if args.json_out:
        print(json.dumps(q, indent=2))
    else:
        print(f"Added quote #{q['id']} [{q['category']}]")

    return 0


def cmd_quote_list(args) -> int:
    quotes = store.list_quotes(category=args.category)

    if args.json_out:
        print(json.dumps(quotes, indent=2))
    else:
        if not quotes:
            print("No quotes in the archive.")
        else:
            for q in quotes:
                print(f"  #{q['id']} [{q['category']}] \"{q['text']}\"")

    return 0


def cmd_quote_random(args) -> int:
    from .config import MOOD_CATEGORY_MAP

    category = None
    if args.mood:
        category = MOOD_CATEGORY_MAP.get(args.mood)

    q = store.random_quote(category=category)

    if args.json_out:
        print(json.dumps(q, indent=2))
    else:
        if q:
            print(f"\"{q['text']}\"")
            print(f"  -- [{q['category']}]")
        else:
            print("The archive is empty. Feed Chango some lines.")

    return 0


def cmd_history(args) -> int:
    history = store.list_consumption_history(
        item=args.item, days=args.days,
    )

    if args.json_out:
        print(json.dumps(history, indent=2))
    else:
        if not history:
            print("No consumption history.")
        else:
            for h in history:
                ts = h["timestamp"][:16].replace("T", " ")
                mood_str = f" mood:{h['mood']}" if h.get("mood") else ""
                qty_str = f"x{h['quantity']}" if h["quantity"] != 1 else ""
                print(f"  [{ts}] {h['item']}{qty_str}{mood_str}")

    return 0


def cmd_sync(args) -> int:
    try:
        from .graph import sync_all
        result = sync_all()
    except ImportError:
        print("error: neo4j not installed (install with: uv sync --extra graph)",
              file=sys.stderr)
        return 1
    except Exception as e:
        print(f"error: sync failed: {e}", file=sys.stderr)
        return 1

    hlog("changoctl", "info", "sync", result)

    if args.json_out:
        print(json.dumps(result, indent=2))
    else:
        print(f"Synced {result.get('consumption_count', 0)} consumption logs "
              f"and {result.get('quote_count', 0)} quotes to Beachhead.")

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="changoctl",
        description="changoctl -- survival inventory and atmospheric personality engine",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_out", help="JSON output"
    )

    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Stock levels and quote count")

    # restock
    p_restock = sub.add_parser("restock", help="Add stock")
    p_restock.add_argument("item", help="Item to restock")
    p_restock.add_argument(
        "--quantity", type=int, default=1, help="Quantity to add (default: 1)"
    )

    # consume
    p_consume = sub.add_parser("consume", help="Consume an item")
    p_consume.add_argument("item", help="Item to consume")
    p_consume.add_argument("--mood", default=None, help="Current mood")

    # sustain
    p_sustain = sub.add_parser("sustain", help="Full ritual: mood-aware consume + quote")
    p_sustain.add_argument("--mood", required=True, help="Current mood (required)")

    # quote (subparser group)
    p_quote = sub.add_parser("quote", help="Manage quotes")
    quote_sub = p_quote.add_subparsers(dest="quote_command")

    p_qa = quote_sub.add_parser("add", help="Add a quote")
    p_qa.add_argument("text", nargs="*", help="Quote text")
    p_qa.add_argument("--category", required=True, help="Category")
    p_qa.add_argument("--source-module", default=None, help="Source module")

    p_ql = quote_sub.add_parser("list", help="List quotes")
    p_ql.add_argument("--category", default=None, help="Filter by category")

    p_qr = quote_sub.add_parser("random", help="Random quote")
    p_qr.add_argument("--mood", default=None, help="Filter by mood")

    # history
    p_history = sub.add_parser("history", help="Consumption log")
    p_history.add_argument("--days", type=int, default=None, help="Days to look back")
    p_history.add_argument("--item", default=None, help="Filter by item")

    # sync
    sub.add_parser("sync", help="Replay state to Beachhead (Neo4j)")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    if not hasattr(args, "json_out"):
        args.json_out = False

    dispatch = {
        "status": cmd_status,
        "restock": cmd_restock,
        "consume": cmd_consume,
        "sustain": cmd_sustain,
        "history": cmd_history,
        "sync": cmd_sync,
    }

    if args.command == "quote":
        if not hasattr(args, "quote_command") or not args.quote_command:
            cli_main(["quote", "--help"])
            return 0
        quote_dispatch = {
            "add": cmd_quote_add,
            "list": cmd_quote_list,
            "random": cmd_quote_random,
        }
        return quote_dispatch[args.quote_command](args)

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_cli.py -v`
Expected: All 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add halos/changoctl/cli.py tests/test_changoctl_cli.py
git commit -m "feat(changoctl): CLI with all subcommands"
```

---

### Task 7: Neo4j Graph Adapter

**Files:**
- Create: `halos/changoctl/graph.py`
- Create: `tests/test_changoctl_graph.py`

- [ ] **Step 1: Write failing tests for graph adapter**

```python
# tests/test_changoctl_graph.py
"""Tests for changoctl graph adapter — Neo4j dual-write and sync.

All tests mock the neo4j driver. No real Neo4j required.
"""

import pytest
from unittest.mock import patch, MagicMock

from halos.changoctl.graph import is_available, push_consumption, push_quote, push_restock


class TestGraphAvailability:
    def test_available_when_driver_connects(self):
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        with patch("halos.changoctl.graph._get_driver", return_value=mock_driver):
            assert is_available() is True

    def test_unavailable_when_no_neo4j(self):
        with patch("halos.changoctl.graph._neo4j", None):
            assert is_available() is False

    def test_unavailable_when_connection_fails(self):
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = Exception("refused")
        with patch("halos.changoctl.graph._get_driver", return_value=mock_driver):
            assert is_available() is False


class TestPushOperations:
    def test_push_consumption_succeeds(self):
        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        with patch("halos.changoctl.graph._get_driver", return_value=mock_driver):
            # Should not raise
            push_consumption("espresso", "grind", "sess-1", "2026-04-10T00:00:00Z")
        mock_session.run.assert_called()

    def test_push_consumption_degrades_silently(self):
        with patch("halos.changoctl.graph._get_driver", side_effect=Exception("down")):
            # Should not raise
            push_consumption("espresso", "grind", "sess-1", "2026-04-10T00:00:00Z")

    def test_push_quote_degrades_silently(self):
        with patch("halos.changoctl.graph._get_driver", side_effect=Exception("down")):
            push_quote("Test line.", "sardonic", 1)

    def test_push_restock_degrades_silently(self):
        with patch("halos.changoctl.graph._get_driver", side_effect=Exception("down")):
            push_restock("lagavulin", 5)


class TestSync:
    def test_sync_all_with_data(self, tmp_path):
        from halos.changoctl.store import restock, consume, add_quote
        from halos.changoctl.graph import sync_all

        tmp_db = tmp_path / "test.db"
        restock("espresso", quantity=2, db_path=tmp_db)
        consume("espresso", mood="grind", db_path=tmp_db)
        add_quote("Test.", category="sardonic", db_path=tmp_db)

        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("halos.changoctl.graph._get_driver", return_value=mock_driver):
            result = sync_all(db_path=tmp_db)

        assert result["consumption_count"] == 1
        assert result["quote_count"] == 1
        assert mock_session.run.call_count > 0

    def test_sync_all_no_neo4j(self, tmp_path):
        from halos.changoctl.graph import sync_all

        with patch("halos.changoctl.graph._neo4j", None):
            with pytest.raises(ImportError, match="neo4j"):
                sync_all(db_path=tmp_path / "test.db")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_graph.py -v`
Expected: FAIL — ImportError (graph.py does not exist)

- [ ] **Step 3: Implement graph.py**

```python
# halos/changoctl/graph.py
"""Neo4j graph adapter for changoctl — dual-write to Beachhead.

Fire-and-forget: all push operations swallow exceptions silently.
If neo4j is not installed, the module degrades gracefully.
sync_all is the recovery path — idempotent replay from SQLite.
"""

from pathlib import Path
from typing import Optional

from halos.common.log import hlog

try:
    import neo4j as _neo4j
except ImportError:
    _neo4j = None

_driver_cache = None


def _get_driver():
    """Lazy-init and cache the neo4j driver."""
    global _driver_cache
    if _neo4j is None:
        raise ImportError("neo4j package not installed")
    if _driver_cache is None:
        from .config import BEACHHEAD_URI, BEACHHEAD_USER, BEACHHEAD_PASS
        _driver_cache = _neo4j.GraphDatabase.driver(
            BEACHHEAD_URI, auth=(BEACHHEAD_USER, BEACHHEAD_PASS)
        )
    return _driver_cache


def is_available() -> bool:
    """Check if Beachhead is reachable."""
    if _neo4j is None:
        return False
    try:
        driver = _get_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def push_consumption(item: str, mood: str, session_id: str, timestamp: str) -> None:
    """Project a consumption event into the graph."""
    try:
        driver = _get_driver()
        with driver.session() as session:
            session.run("""
                MERGE (i:Item {name: $item})
                MERGE (m:Mood {name: $mood})
                MERGE (s:Session {id: $session_id})
                SET s.timestamp = $timestamp
                MERGE (i)-[:CONSUMED_DURING {timestamp: $timestamp}]->(s)
                MERGE (s)-[:MOOD_WAS]->(m)
                MERGE (i)-[:PAIRS_WITH]->(m)
            """, item=item, mood=mood, session_id=session_id, timestamp=timestamp)
    except Exception as e:
        hlog("changoctl", "warning", "graph_push_failed", {
            "operation": "consumption", "error": str(e),
        })


def push_quote(text: str, category: str, quote_id: int) -> None:
    """Project a quote into the graph."""
    try:
        driver = _get_driver()
        with driver.session() as session:
            session.run("""
                MERGE (q:Quote {id: $quote_id})
                SET q.text = $text, q.category = $category
                MERGE (m:Mood {name: $category})
                MERGE (q)-[:TAGGED]->(m)
            """, text=text, category=category, quote_id=quote_id)
    except Exception as e:
        hlog("changoctl", "warning", "graph_push_failed", {
            "operation": "quote", "error": str(e),
        })


def push_restock(item: str, new_stock: int) -> None:
    """Update item stock in the graph."""
    try:
        driver = _get_driver()
        with driver.session() as session:
            session.run("""
                MERGE (i:Item {name: $item})
                SET i.stock = $new_stock
            """, item=item, new_stock=new_stock)
    except Exception as e:
        hlog("changoctl", "warning", "graph_push_failed", {
            "operation": "restock", "error": str(e),
        })


def sync_all(db_path: Optional[Path] = None) -> dict:
    """Full idempotent replay from SQLite into Beachhead.

    Raises ImportError if neo4j is not installed.
    Raises Exception if Beachhead is unreachable.
    """
    if _neo4j is None:
        raise ImportError("neo4j package not installed")

    from . import store

    driver = _get_driver()
    consumption_logs = store.list_consumption_history(db_path=db_path)
    quotes = store.list_quotes(db_path=db_path)
    inventory = store.get_inventory(db_path=db_path)

    with driver.session() as session:
        # Sync inventory
        for item in inventory:
            session.run("""
                MERGE (i:Item {name: $name})
                SET i.stock = $stock
            """, name=item["item"], stock=item["stock"])

        # Sync consumption logs
        for log in consumption_logs:
            session.run("""
                MERGE (i:Item {name: $item})
                MERGE (s:Session {id: $session_id})
                SET s.timestamp = $timestamp
                MERGE (i)-[:CONSUMED_DURING {timestamp: $timestamp}]->(s)
            """, item=log["item"],
                session_id=str(log["id"]),
                timestamp=log["timestamp"])

            if log.get("mood"):
                session.run("""
                    MERGE (m:Mood {name: $mood})
                    MERGE (s:Session {id: $session_id})
                    MERGE (s)-[:MOOD_WAS]->(m)
                    MERGE (i:Item {name: $item})
                    MERGE (i)-[:PAIRS_WITH]->(m)
                """, mood=log["mood"],
                    session_id=str(log["id"]),
                    item=log["item"])

        # Sync quotes
        for q in quotes:
            session.run("""
                MERGE (quote:Quote {id: $id})
                SET quote.text = $text, quote.category = $category
                MERGE (m:Mood {name: $category})
                MERGE (quote)-[:TAGGED]->(m)
            """, id=q["id"], text=q["text"], category=q["category"])

    hlog("changoctl", "info", "sync_complete", {
        "consumption_count": len(consumption_logs),
        "quote_count": len(quotes),
    })

    return {
        "consumption_count": len(consumption_logs),
        "quote_count": len(quotes),
        "inventory_count": len(inventory),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_graph.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add halos/changoctl/graph.py tests/test_changoctl_graph.py
git commit -m "feat(changoctl): Neo4j graph adapter with dual-write and sync"
```

---

### Task 8: Gate — Full Test Suite and Module Docs

**Files:**
- Modify: `docs/d1/halos-modules.md` (add changoctl row)
- Modify: `CLAUDE.md` (add changoctl to module table)

- [ ] **Step 1: Run full changoctl test suite**

Run: `cd /Users/mrkai/code/halo && uv run pytest tests/test_changoctl_store.py tests/test_changoctl_flavour.py tests/test_changoctl_engine.py tests/test_changoctl_cli.py tests/test_changoctl_graph.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run full project test suite to check for regressions**

Run: `cd /Users/mrkai/code/halo && uv run pytest --timeout=30 -x`
Expected: All existing tests still pass

- [ ] **Step 3: Verify CLI registration works**

Run: `cd /Users/mrkai/code/halo && uv sync && uv run changoctl --help`
Expected: Help output showing all subcommands (status, restock, consume, sustain, quote, history, sync)

- [ ] **Step 4: Add changoctl to halos-modules.md**

Read `docs/d1/halos-modules.md`, then add a row to the module table:

```markdown
| changoctl | `changoctl`    | Survival inventory, atmospheric actions, curated quotes, Neo4j graph projection |
```

- [ ] **Step 5: Add changoctl to CLAUDE.md module table**

Add to the halos Modules table in CLAUDE.md:

```markdown
| changoctl | `changoctl`    | Survival inventory (espresso, lagavulin, stimpacks, NOS), atmospheric actions, quotes archive, Beachhead graph |
```

And add to the programmatic API section:

```markdown
# changoctl
changoctl.store.get_inventory(db_path=None) -> list[dict]
changoctl.store.restock(item, quantity=1, db_path=None) -> dict
changoctl.store.consume(item, mood=None, session_context=None, db_path=None) -> dict
changoctl.store.add_quote(text, category, source_session=None, source_module=None, db_path=None) -> dict
changoctl.store.random_quote(category=None, db_path=None) -> Optional[dict]
changoctl.store.list_consumption_history(item=None, days=None, db_path=None) -> list[dict]
changoctl.engine.sustain(mood, session_context=None, db_path=None) -> dict
changoctl.engine.text_summary(db_path=None) -> str
```

- [ ] **Step 6: Commit**

```bash
git add docs/d1/halos-modules.md CLAUDE.md
git commit -m "docs(changoctl): register module in halos-modules.md and CLAUDE.md"
```

- [ ] **Step 7: Final smoke test — end-to-end CLI flow**

```bash
cd /Users/mrkai/code/halo
uv run changoctl status
uv run changoctl restock espresso --quantity 5
uv run changoctl restock lagavulin --quantity 3
uv run changoctl consume espresso --mood grind
uv run changoctl quote add "The cluster doesn't care about your feelings." --category sardonic
uv run changoctl sustain --mood burnt-out
uv run changoctl history
uv run changoctl --json status
```

Expected: Each command produces appropriate output. `sustain` shows atmospheric action + quote + status line.
