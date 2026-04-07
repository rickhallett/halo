# Testing Patterns

**Analysis Date:** 2026-04-07

## Test Framework

**Runner:**
- pytest >= 9.0.2 (dev dependency group in `pyproject.toml`)
- pytest-cov >= 5.0 (optional dev dependency)
- Config: `pyproject.toml` `[tool.pytest.ini_options]`

**Assertion Library:**
- Plain `assert` statements (pytest native)
- `pytest.raises` for exception testing

**Run Commands:**
```bash
make test                # Run all tests: uv run pytest tests/ -v --tb=short
make test-cov            # With coverage: uv run pytest tests/ -v --tb=short --cov=halos --cov-report=term-missing
make gate                # Full gate: test + lint + typecheck (lint/typecheck are placeholders)
uv run pytest tests/     # Direct invocation
make test-memctl         # Per-module: uv run pytest tests/memctl/ -v
make test-nightctl       # Per-module: uv run pytest tests/nightctl/ -v
```

**Always run via `uv run pytest`** — never bare `pytest` or `pip install`. The repo uses uv exclusively.

## Test File Organization

**Location:** Separate `tests/` directory mirroring `halos/` module structure

**Naming:** `test_<feature>.py` (configured: `python_files = "test_*.py"`, `python_functions = "test_*"`)

**Structure:**
```
tests/
    __init__.py
    test_e2e_gauntlet.py          # Cross-module e2e scenarios
    test_journalctl.py            # Module-level tests (flat)
    test_docctl.py
    integration/
        __init__.py
        test_cross_module.py      # Cross-module integration (real serialisation, no mocks)
    memctl/
        __init__.py
        test_note.py
        test_index.py
        test_prune.py
        test_config.py
        test_enrich.py
        test_adversarial_fixes.py
    nightctl/
        __init__.py
        test_item.py
        test_acceptance.py        # 1:1 mapping to spec acceptance criteria
        test_cli.py
        test_config.py
        test_executor.py
        test_container.py
        test_archive.py
        test_cli_expanded.py
    backupctl/
        __init__.py
        test_engine.py
        test_config.py
        test_cli.py
        test_smoke.py
        test_sqlite_safety.py
    fleet/
        __init__.py
        conftest.py               # Only conftest.py in the codebase — kubectl fixtures
        test_pod_health.py
        test_advisor_identity.py
        test_nats_stream.py
        test_argocd.py
        test_chaos.py
    statusctl/
    calctl/
    ledgerctl/
    ...                           # Each halos module has a corresponding test directory
```

**Every test directory has an `__init__.py`.** Total: ~111 test files across ~20+ test directories.

## Test Structure

**Suite Organization — group by class, name descriptively:**
```python
# tests/memctl/test_note.py
class TestParse:
    def test_valid_note_all_fields(self):
        ...
    def test_missing_frontmatter_delimiters_no_dashes(self):
        ...

class TestValidate:
    def test_all_valid_no_errors(self):
        ...
    def test_missing_title(self):
        ...

class TestMarshal:
    def test_round_trip(self):
        ...
```

**Class naming:** `Test<ComponentOrBehaviour>` — e.g., `TestParse`, `TestItemCreate`, `TestLifecycle`, `TestPersistence`, `TestValidation`

**Method naming:** `test_<what_is_being_tested>` — descriptive, reads as a sentence. Examples:
- `test_valid_note_all_fields`
- `test_missing_frontmatter_delimiters_one_dash`
- `test_agent_job_can_skip_planning_with_context`
- `test_terminal_states_have_no_transitions`
- `test_concurrent_save_uses_thread_safe_temp_files`

**Section separators in test files:**
```python
# ---------------------------------------------------------------------------
# State machine: valid_transitions()
# ---------------------------------------------------------------------------
```

**Module-level docstrings describe test purpose and philosophy:**
```python
"""Tests for nightctl unified Item model."""

"""End-to-end gauntlet tests for nightctl unified work tracker and microHAL onboarding.

These are not unit tests. Each test simulates a realistic multi-step workflow
and deliberately tries to break things.
"""
```

## Fixtures

**pytest `tmp_path` is the primary fixture** — used extensively for filesystem isolation:
```python
def test_create_task(self, tmp_path):
    item = Item.create(tmp_path, title="Write docs", kind="task")
    assert item.kind == "task"
```

**Custom fixtures defined at module level (not conftest.py):**
```python
@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary database path."""
    return tmp_path / "test_journal.db"

@pytest.fixture
def tmp_cache(tmp_path):
    """Provide a temporary cache directory."""
    d = tmp_path / "journal-cache"
    d.mkdir()
    return d
```

**Only one conftest.py exists:** `tests/fleet/conftest.py` — provides kubectl helper fixtures for live cluster tests.

**Helper factories use `_make_*` pattern:**
```python
def _make_note(**overrides) -> Note:
    defaults = dict(id="20250101-120000-001", title="Test Note", ...)
    defaults.update(overrides)
    return Note(**defaults)

def _make_config(tmp_path: Path) -> BackupConfig:
    repo = tmp_path / "repo"
    repo.mkdir()
    return BackupConfig(repository=repo, ...)

def _make_nightctl_config(tmp_path):
    """Create a minimal nightctl config for testing. Returns Config object."""
```

**Constant test data at module level:**
```python
VALID_FRONTMATTER = """\
---
id: "20250101-120000-001"
title: "Test Note"
..."""

VALID_PLAN_XML = """\
<plan>
  <goal>Test goal</goal>
  ..."""
```

## Mocking

**Framework:** `unittest.mock` (stdlib) — `patch`, `MagicMock`, `monkeypatch`

**Patterns:**

**1. `@patch` decorator for subprocess/external dependencies:**
```python
@patch("halos.backupctl.engine._has_restic", return_value=True)
@patch("subprocess.run")
def test_list_restic_snapshots_parses_json(self, mock_run, mock_restic, tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps([...])
    mock_run.return_value = mock_result
    ...
```

**2. `monkeypatch` for module-level state and env vars:**
```python
def test_writes_json_line_to_file(self, tmp_path, monkeypatch):
    log_file = tmp_path / "test.log"
    monkeypatch.setattr("halos.common.log._LOG_FILE", str(log_file))
    ...
```

**3. Context manager `patch` for scoped mocking:**
```python
with patch("halos.journalctl.window.CACHE_DIR", tmp_cache), \
     patch("halos.journalctl.window._synthesise") as mock_synth:
    mock_synth.return_value = "Mocked summary of the week."
    result = window(days=7, db_path=tmp_db)
```

**4. Multiple `patch` with context managers for checker classes:**
```python
with patch("halos.statusctl.engine.ServiceCheck") as mock_svc, \
     patch("halos.statusctl.engine.ContainerCheck") as mock_ctr, \
     patch("halos.statusctl.engine.AgentCheck") as mock_agt, \
     patch("halos.statusctl.engine.HostCheck") as mock_host:
    for mock_cls in [mock_svc, mock_ctr, mock_agt, mock_host]:
        mock_cls.return_value.run.return_value = [fake_result]
    results = run_all_checks()
```

**What to Mock:**
- External process calls (`subprocess.run`)
- LLM/API calls (e.g., `_synthesise` in journalctl window)
- Module-level configuration state (`_LOG_FILE`, `DB_PATH`, `CACHE_DIR`)
- Feature flags (`_has_restic`)
- Checker classes in health/status systems

**What NOT to Mock:**
- Filesystem operations (use `tmp_path` instead)
- SQLite operations (create real in-memory or temp databases)
- YAML serialisation (test real round-trips)
- Domain model logic (test directly)
- Cross-module integration (see integration tests below)

## Test Types

**Unit Tests:**
- Majority of test suite
- Test individual functions, classes, and methods in isolation
- Located in `tests/<module>/test_<feature>.py`
- Example: `tests/memctl/test_note.py`, `tests/nightctl/test_item.py`

**Adversarial Fix Tests:**
- Pattern: `test_adversarial_fixes.py` in module test directories
- Tests written after adversarial review findings
- Named after the review finding ID: `class TestHashFileDoubleRead` with comment `"""H10: ..."""`
- Found in: `tests/memctl/`, `tests/agentctl/`, `tests/logctl/`, `tests/reportctl/`, `tests/todoctl/`, `tests/cronctl/`

**Acceptance Tests:**
- Map 1:1 to spec acceptance criteria
- Named `test_ac_NN_short_description`
- Example: `tests/nightctl/test_acceptance.py` maps to `docs/d2/spec-nightctl-merge.md`
- Run CLI via subprocess for true black-box testing

**Integration Tests:**
- `tests/integration/test_cross_module.py` — real serialisation, no mocks
- Verify module A's output is readable by module B
- Example: memctl writes index, reportctl reads it

**E2E Gauntlet Tests:**
- `tests/test_e2e_gauntlet.py` — multi-step workflow stress tests
- "If a test here passes trivially, it is wrong"
- Cover: lifecycle corruption, parallel stress, state machine exhaustion, race conditions, adversarial XML

**Smoke Tests:**
- Pattern: `test_smoke.py` in module directories
- Lightweight sanity checks
- Marker: `@pytest.mark.smoke`

**Fleet Tests (Live Cluster):**
- `tests/fleet/` — require live K8s cluster
- Auto-skip via `pytest.mark.skipif(not _cluster_available())`
- Session-scoped fixtures to avoid repeated kubectl calls
- Markers: `@pytest.mark.fleet`, `@pytest.mark.tier1` through `@pytest.mark.tier5`

## Test Markers

Defined in `pyproject.toml`:

| Marker | Purpose |
|--------|---------|
| `slow` | Long-running tests (deselect: `-m "not slow"`) |
| `smoke` | Lightweight smoke tests |
| `fleet` | Requires live K8s cluster |
| `tier1` | Plumbing smoke (fast, post-deploy) |
| `tier2` | NATS event flow verification |
| `tier3` | Chaos engineering (destructive) |
| `tier4` | Mock pipeline (cost-free integration) |
| `tier5` | Live Telegram liveness |
| `telegram` | Alias for tier5 |
| `chaos` | Alias for tier3 |

## Common Patterns

**Testing CLI output via capsys:**
```python
def test_add_via_cli(self, tmp_db, capsys):
    with self._patch_db(tmp_db):
        ret = cli_main(["add", "hello", "from", "cli"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Added entry #1" in captured.out
```

**Testing CLI via subprocess (acceptance tests):**
```python
def _run_cli(*args, config_path=None):
    cmd = [sys.executable, "-m", "halos.nightctl.cli"]
    if config_path:
        cmd += ["--config", config_path]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr
```

**Exception testing with structured data:**
```python
def test_invalid_transition_raises(self, tmp_path):
    item = Item.create(tmp_path, title="Test", kind="task")
    with pytest.raises(TransitionError) as exc_info:
        item.transition("done")
    assert "open" in str(exc_info.value)
    assert exc_info.value.current == "open"
    assert exc_info.value.attempted == "done"
    assert len(exc_info.value.allowed) > 0
```

**Concurrency testing with threading:**
```python
def test_concurrent_save_uses_thread_safe_temp_files(self, tmp_path):
    item = Item.create(items_dir, title="Concurrent save", kind="task")
    barrier = threading.Barrier(5)
    errors = []

    def worker(priority):
        try:
            barrier.wait()
            item.data["priority"] = priority
            item.save()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(p,)) for p in range(1, 6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
```

**SQLite test pattern — create real databases in tmp_path:**
```python
def test_creates_valid_backup(self, tmp_path):
    db_path = tmp_path / "source.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO items VALUES (1, 'alpha')")
    conn.commit()
    conn.close()
    # ... test against the real database
```

**Round-trip testing:**
```python
def test_round_trip(self):
    original = _make_note()
    text = marshal(original)
    restored = parse(text)
    assert restored.id == original.id
    assert restored.title == original.title
```

**Exhaustive state machine testing:**
```python
def test_terminal_states_have_no_transitions(self):
    for kind in VALID_KINDS:
        for terminal in TERMINAL_STATUSES:
            assert valid_transitions(terminal, kind) == []

def test_all_statuses_have_entries(self):
    for kind in VALID_KINDS:
        for status in VALID_STATUSES:
            result = valid_transitions(status, kind)
            assert isinstance(result, list)
```

**Full lifecycle tests — exercise complete happy paths:**
```python
def test_agent_job_lifecycle(self, tmp_path):
    """open -> planning -> plan-review -> in-progress -> running -> done"""
    item = Item.create(tmp_path, title="Research", kind="agent-job")
    item.transition("planning")
    item.data["plan"] = VALID_PLAN_XML
    item.transition("plan-review")
    item.transition("in-progress")
    item.transition("running")
    item.transition("done")
    assert item.status == "done"
```

## Coverage

**Requirements:** No enforced coverage threshold. Coverage is opt-in via `make test-cov`.

**View Coverage:**
```bash
make test-cov    # uv run pytest tests/ -v --tb=short --cov=halos --cov-report=term-missing
```

## Test Stats

- **~111 test files** across **~20+ module directories**
- **~166 source files** in the `halos/` package
- Fleet tests auto-skip when cluster is unavailable
- No CI pipeline currently configured (tests run locally via `make gate`)

---

*Testing analysis: 2026-04-07*
