# Guido Curriculum: IPython Scripts to Jupyter Notebooks

**Date:** 2026-04-16
**Status:** APPROVED
**Scope:** Migration utility + infrastructure

## Problem

30 curriculum scripts use `IPython.embed()` / `checkpoint()` as interactive REPL breakpoints. This works but:
- No persistent output (you lose REPL history on exit)
- No Markdown rendering for lesson text (everything is `print()`)
- No cell-by-cell re-execution
- VS Code already has full Jupyter stack installed

## Decision Record

| Question | Answer | Rationale |
|---|---|---|
| Layout | Alongside (`notebooks-weeks-NN/` next to `scripts-weeks-NN/`) | Keep originals until validated |
| Converter location | One-shot `curriculum/convert_to_notebooks.py` | Migration tool, not permanent infra |
| Parse quality | Level 2 (structured Markdown) | Print blocks parsed into headers, code fences, lists |
| nbstripout | Yes | Keeps notebook diffs readable in git |
| Kernel | Single `guido-curriculum` kernel | All scripts are stdlib-only |

## Architecture

### 1. Infrastructure (15 min)

```
curriculum/
  pyproject.toml          # Add ipykernel dep (exists in scripts-weeks-01-02, promote to root)
  .python-version         # 3.11+ (promote from scripts-weeks-01-02)
```

- `uv sync` in `curriculum/`
- `uv run python -m ipykernel install --user --name guido-curriculum --display-name "Guido Curriculum"`
- `uv tool install nbstripout && nbstripout --install` (or add to .gitattributes)

### 2. Converter Script

**Input:** `.py` file with checkpoint/embed pattern
**Output:** `.ipynb` file via `nbformat`

#### Cell boundary detection

Two patterns, same logic:

```
# Pattern A (weeks 01-02): from _repl import checkpoint → checkpoint(header="...")
# Pattern B (weeks 03-06): from IPython import embed → embed(header="...")
```

Both are cell-boundary markers. Lines between markers become cells.

#### Cell classification

For each block between boundaries:
1. **Consecutive `print()` lines** → Markdown cell (parse content)
2. **Everything else** → Code cell
3. **Mixed blocks** → Split: print-run becomes Markdown, code-run becomes Code

#### Print-to-Markdown parsing (Level 2)

| Print pattern | Markdown output |
|---|---|
| `print("=" * 60)` | Delete (visual divider) |
| `print("CHECKPOINT N: ...")` | `## Checkpoint N: ...` |
| `print("TRY THESE:")` / `print("TRY:")` | `**Try these:**` |
| `print("  1. code")` (indented) | Detect as code example → fence block |
| `print("KEY INSIGHT: ...")` | `> **Key insight:** ...` |
| `print()` | Blank line |
| `print("text")` | Plain text |

#### Lines to strip entirely

- `#!/usr/bin/env python3`
- `from _repl import checkpoint`
- `from IPython import embed`
- `checkpoint(header=...)` / `embed(header=...)` (boundary markers, not content)
- `import IPython` (if standalone)

#### Docstring handling

Module docstring → first Markdown cell (title + description). Strip `Run: uv run python ...` instruction, replace with notebook usage note.

### 3. Output structure

```
curriculum/
  notebooks-weeks-01-02/
    day01_defaultdict_basics.ipynb
    day02_defaultdict_patterns.ipynb
    ...
  notebooks-weeks-03-04/
    day01_logging_levels.ipynb
    ...
  notebooks-weeks-05-06/
    day01_pathlib_fundamentals.ipynb
    ...
```

### 4. Cleanup

- Delete `_repl.py` from notebooks dirs (not needed)
- Update `data/advisors/guido/profile.md` curriculum paths
- Add `*.ipynb` filter to `.gitattributes` for nbstripout

## Files touched

| File | Action |
|---|---|
| `curriculum/convert_to_notebooks.py` | CREATE — the converter |
| `curriculum/pyproject.toml` | CREATE — root-level, ipykernel dep |
| `curriculum/.python-version` | CREATE — 3.14 |
| `curriculum/notebooks-weeks-01-02/*.ipynb` | CREATE — 10 notebooks |
| `curriculum/notebooks-weeks-03-04/*.ipynb` | CREATE — 10 notebooks |
| `curriculum/notebooks-weeks-05-06/*.ipynb` | CREATE — 10 notebooks |
| `data/advisors/guido/profile.md` | EDIT — update paths |
| `.gitattributes` | EDIT — add nbstripout filter |

## Implementation order

1. Create `curriculum/pyproject.toml` with ipykernel
2. Register kernel
3. Write converter script
4. Run converter on all 3 week-blocks
5. Spot-check: open 3 notebooks (1 per block) in VS Code, verify cells render
6. Install nbstripout, configure .gitattributes
7. Update profile.md paths
8. Commit

## What's NOT in scope

- Rewriting lesson content (editorial pass is separate)
- Converting drillctl (reads JSON, no change needed)
- Future weeks authoring workflow (author directly as .ipynb)
- Deleting original scripts (wait until notebooks validated in daily use)
