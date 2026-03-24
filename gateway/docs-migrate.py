#!/usr/bin/env python3
"""Documentation migration — reorganise docs/ based on audit findings.

Moves:
  - briefings: d2/briefings/ → d1/briefings/
  - completed plans: plans/ → d3/archive/
  - nanorepo-architecture.md (superseded) → d3/archive/

Deletes:
  - groups/telegram_main/nightctl-spec.md (duplicate of d2/nightctl-spec.md)
  - groups/main/CLAUDE.md (legacy unused group)

Run with --dry-run to preview, without to execute.
"""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DRY_RUN = "--dry-run" in sys.argv


def move(src: Path, dst: Path) -> None:
    rel_src = src.relative_to(ROOT)
    rel_dst = dst.relative_to(ROOT)
    if DRY_RUN:
        print(f"  MOVE  {rel_src} → {rel_dst}")
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f"  MOVED {rel_src} → {rel_dst}")


def delete(path: Path) -> None:
    rel = path.relative_to(ROOT)
    if DRY_RUN:
        print(f"  DEL   {rel}")
    else:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  DELETED {rel}")


def main():
    if DRY_RUN:
        print("DRY RUN — no files will be changed\n")
    else:
        print("EXECUTING migration\n")

    # 1. Briefings: d2/briefings/ → d1/briefings/
    print("1. Briefings → d1/")
    briefings_src = ROOT / "docs" / "d2" / "briefings"
    briefings_dst = ROOT / "docs" / "d1" / "briefings"
    if briefings_src.exists():
        for f in sorted(briefings_src.iterdir()):
            if f.is_file():
                move(f, briefings_dst / f.name)
        if not DRY_RUN and not list(briefings_src.iterdir()):
            briefings_src.rmdir()
            print(f"  REMOVED empty dir docs/d2/briefings/")
    else:
        print("  SKIP — docs/d2/briefings/ not found")

    # 2. Archive completed plans
    print("\n2. Archive completed plans → d3/archive/")
    plans_dir = ROOT / "docs" / "plans"
    archive_dir = ROOT / "docs" / "d3" / "archive"
    if plans_dir.exists():
        for f in sorted(plans_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                move(f, archive_dir / f.name)
        if not DRY_RUN and not list(plans_dir.iterdir()):
            plans_dir.rmdir()
            print(f"  REMOVED empty dir docs/plans/")

    # 3. Archive superseded nanorepo-architecture.md
    print("\n3. Archive superseded docs")
    nanorepo = ROOT / "docs" / "d2" / "nanorepo-architecture.md"
    if nanorepo.exists():
        move(nanorepo, archive_dir / "nanorepo-architecture.md")

    # 4. Delete stale/duplicate files
    print("\n4. Delete stale files")
    stale = [
        ROOT / "groups" / "telegram_main" / "nightctl-spec.md",
        ROOT / "groups" / "main" / "CLAUDE.md",
    ]
    for path in stale:
        if path.exists():
            delete(path)
        else:
            print(f"  SKIP — {path.relative_to(ROOT)} not found")

    # Check if groups/main/ is now empty and can be removed
    main_group = ROOT / "groups" / "main"
    if main_group.exists() and not DRY_RUN:
        remaining = list(main_group.iterdir())
        if not remaining:
            main_group.rmdir()
            print(f"  REMOVED empty dir groups/main/")

    print("\nDone." + (" (dry run — no changes made)" if DRY_RUN else ""))


if __name__ == "__main__":
    main()
