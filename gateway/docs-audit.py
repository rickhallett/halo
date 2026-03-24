#!/usr/bin/env python3
"""Documentation audit — repeatable snapshot of docs structure, size, and placement.

Usage: python3 docs-audit.py [--tree] [--full]
  --tree   Include full file tree with first-line context
  --full   Include non-docs markdown files
"""

import os
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
IGNORE = {"node_modules", ".git", "__pycache__", ".venv", "dist"}


def walk_md(base: Path, exclude_dirs: set[str] | None = None) -> list[dict]:
    """Collect all .md files with metadata."""
    exclude_dirs = exclude_dirs or set()
    results = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORE and d not in exclude_dirs]
        for f in files:
            if not f.endswith(".md"):
                continue
            fp = Path(root) / f
            stat = fp.stat()
            lines = fp.read_text(errors="replace").splitlines()
            first_line = ""
            for line in lines[:20]:
                stripped = line.strip().lstrip("#").strip()
                if stripped:
                    first_line = stripped[:80]
                    break
            results.append({
                "path": str(fp.relative_to(ROOT)),
                "lines": len(lines),
                "bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                "first_line": first_line,
                "dir": str(Path(root).relative_to(ROOT)),
            })
    return sorted(results, key=lambda x: x["path"])


def print_table(rows: list[dict], title: str) -> None:
    """Print a formatted table."""
    print(f"\n{'=' * 100}")
    print(f"  {title}")
    print(f"{'=' * 100}")
    fmt = "{:<60} {:>5} {:>7} {:>12}  {}"
    print(fmt.format("PATH", "LINES", "BYTES", "MODIFIED", "TITLE"))
    print("-" * 100)
    total_lines = 0
    total_bytes = 0
    for r in rows:
        print(fmt.format(r["path"], r["lines"], r["bytes"], r["modified"], r["first_line"][:40]))
        total_lines += r["lines"]
        total_bytes += r["bytes"]
    print("-" * 100)
    print(fmt.format(f"TOTAL ({len(rows)} files)", total_lines, total_bytes, "", ""))


def print_by_dir(rows: list[dict]) -> None:
    """Print summary grouped by directory."""
    from collections import defaultdict
    dirs = defaultdict(lambda: {"files": 0, "lines": 0, "bytes": 0})
    for r in rows:
        d = r["dir"]
        dirs[d]["files"] += 1
        dirs[d]["lines"] += r["lines"]
        dirs[d]["bytes"] += r["bytes"]
    print(f"\n{'=' * 70}")
    print("  BY DIRECTORY")
    print(f"{'=' * 70}")
    fmt = "{:<40} {:>5} {:>6} {:>8}"
    print(fmt.format("DIRECTORY", "FILES", "LINES", "BYTES"))
    print("-" * 70)
    for d in sorted(dirs.keys()):
        v = dirs[d]
        print(fmt.format(d, v["files"], v["lines"], v["bytes"]))


def print_tree(base: Path) -> None:
    """Print tree-like view with first meaningful line from each file."""
    print(f"\n{'=' * 100}")
    print(f"  FILE TREE (with context)")
    print(f"{'=' * 100}")
    for root, dirs, files in sorted(os.walk(base)):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE)
        level = len(Path(root).relative_to(base).parts)
        indent = "  " * level
        dirname = Path(root).name
        if level == 0:
            print(f"{base.name}/")
        else:
            print(f"{indent}{dirname}/")
        for f in sorted(files):
            fp = Path(root) / f
            context = ""
            if f.endswith((".md", ".yaml", ".yml", ".ts", ".py", ".js")):
                try:
                    lines = fp.read_text(errors="replace").splitlines()[:20]
                    for line in lines:
                        stripped = line.strip().lstrip("#").strip()
                        if stripped and not stripped.startswith("import") and not stripped.startswith("//"):
                            context = f"  — {stripped[:60]}"
                            break
                except Exception:
                    pass
            size = fp.stat().st_size
            print(f"{indent}  {f} ({size:,}b){context}")


def main():
    args = set(sys.argv[1:])
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"Documentation Audit — {ts}")

    # Docs directory
    docs_rows = walk_md(ROOT / "docs")
    print_table(docs_rows, "docs/ DIRECTORY")
    print_by_dir(docs_rows)

    if "--full" in args:
        # All other markdown
        other_rows = walk_md(ROOT, exclude_dirs={"docs"})
        # Filter to non-trivial files
        other_rows = [r for r in other_rows if r["lines"] > 10]
        print_table(other_rows, "OTHER MARKDOWN (>10 lines)")

    if "--tree" in args:
        print_tree(ROOT / "docs")

    # Summary
    print(f"\n{'=' * 70}")
    print("  OBSERVATIONS")
    print(f"{'=' * 70}")
    large = [r for r in docs_rows if r["lines"] > 400]
    if large:
        print(f"\n  Large files (>400 lines):")
        for r in large:
            print(f"    {r['path']} ({r['lines']} lines) — {r['first_line'][:50]}")

    stale_candidates = [r for r in docs_rows if r["modified"] < "2026-03-16"]
    if stale_candidates:
        print(f"\n  Potentially stale (modified before 2026-03-16):")
        for r in stale_candidates:
            print(f"    {r['path']} (modified {r['modified']})")

    misplaced = []
    for r in docs_rows:
        if "/d1/" in r["path"] and r["lines"] > 300:
            misplaced.append((r["path"], "d1 file >300 lines — may belong in d2"))
        if "/d2/" in r["path"] and "spec" not in r["path"].lower() and r["lines"] < 50:
            misplaced.append((r["path"], "d2 file <50 lines — may belong in d1"))
        if "/d2/" in r["path"] and "briefing" in r["path"].lower():
            misplaced.append((r["path"], "briefing in d2 — should be d1 or dedicated dir"))
    if misplaced:
        print(f"\n  Potential misplacement:")
        for path, reason in misplaced:
            print(f"    {path} — {reason}")


if __name__ == "__main__":
    main()
