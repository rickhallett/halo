.PHONY: gate test lint typecheck

# The gate: must pass before any commit is considered done
gate: test lint typecheck

# ── Halos (Python) ──────────────────────────────────────
test:
	uv run pytest tests/ -v --tb=short

test-cov:
	uv run pytest tests/ -v --tb=short --cov=halos --cov-report=term-missing

lint:
	@echo "lint: no linter configured for halos (Python). Placeholder."

typecheck:
	@echo "typecheck: no type checker configured for halos (Python). Placeholder."

# ── Per-module test shortcuts ───────────────────────────
test-memctl:
	uv run pytest tests/memctl/ -v

test-nightctl:
	uv run pytest tests/nightctl/ -v

test-cronctl:
	uv run pytest tests/cronctl/ -v
