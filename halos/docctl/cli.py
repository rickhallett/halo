"""docctl - document assembly, governance, and template rendering CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import audit as auditmod
from . import briefing as briefingmod
from . import index as indexmod
from . import templates as tmplmod
from .doc import marshal_frontmatter, parse_frontmatter, validate_schema

console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _docs_root(args) -> Path:
    if hasattr(args, "docs") and args.docs:
        return Path(args.docs)
    return Path.cwd() / "docs"


def _templates_dir(args) -> Path:
    if hasattr(args, "templates_dir") and args.templates_dir:
        return Path(args.templates_dir)
    return None  # let templates.py use its default


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="docctl",
        description="Document assembly, governance, and template rendering",
    )
    parser.add_argument("--docs", default="", help="docs root directory (default: ./docs)")
    parser.add_argument("--json", action="store_true", dest="json_out", help="machine-readable JSON output")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command")

    # --- audit ---
    p_audit = sub.add_parser("audit", help="scan docs/ for frontmatter issues, tier mismatches, broken links")
    p_audit.add_argument("--fix", action="store_true", help="add missing frontmatter interactively")
    p_audit.add_argument("--no-links", action="store_true", help="skip broken link detection")

    # --- index ---
    p_index = sub.add_parser("index", help="INDEX.md management")
    idx_sub = p_index.add_subparsers(dest="index_cmd")
    idx_rebuild = idx_sub.add_parser("rebuild", help="regenerate INDEX.md for each docs/ subdirectory")
    idx_verify = idx_sub.add_parser("verify", help="check INDEX.md entries match actual files")

    # --- lint ---
    p_lint = sub.add_parser("lint", help="frontmatter schema validation (exit 1 on failures)")

    # --- templates ---
    p_templates = sub.add_parser("templates", help="list available templates")
    p_templates.add_argument("--templates-dir", default="", dest="templates_dir",
                              help="override templates directory")

    # --- render ---
    p_render = sub.add_parser("render", help="render a document or template to PDF/HTML/DOCX")
    p_render.add_argument("--template", default="", help="template name from templates/docs/")
    p_render.add_argument("--input", default="", help="input markdown file")
    p_render.add_argument("--vars", default="", help="YAML variables file")
    p_render.add_argument("--output", "-o", default="", help="output file path")
    p_render.add_argument("--format", default="pdf", choices=["pdf", "html", "docx", "pptx"],
                           help="output format (default: pdf)")
    p_render.add_argument("--templates-dir", default="", dest="templates_dir",
                           help="override templates directory")

    # --- slides ---
    p_slides = sub.add_parser("slides", help="render a Marp slide deck")
    p_slides.add_argument("--template", default="", help="template name from templates/docs/")
    p_slides.add_argument("--input", default="", help="input markdown file")
    p_slides.add_argument("--vars", default="", help="YAML variables file")
    p_slides.add_argument("--output", "-o", default="", help="output file path")
    p_slides.add_argument("--format", default="pdf", choices=["pdf", "html", "pptx"],
                           help="output format (default: pdf)")
    p_slides.add_argument("--templates-dir", default="", dest="templates_dir",
                           help="override templates directory")

    # --- summary ---
    sub.add_parser("summary", help="one-liner corpus summary for briefing integration")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "audit": cmd_audit,
        "index": cmd_index,
        "lint": cmd_lint,
        "templates": cmd_templates,
        "render": cmd_render,
        "slides": cmd_slides,
        "summary": cmd_summary,
    }
    dispatch[args.command](args)


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

def cmd_audit(args):
    docs_root = _docs_root(args)
    if not docs_root.exists():
        err_console.print(f"[red]docs root not found: {docs_root}[/red]")
        sys.exit(2)

    check_links = not args.no_links
    result = auditmod.run_audit(docs_root, check_links=check_links)

    if args.fix:
        _audit_fix(docs_root, result)
        return

    if args.json_out:
        data = [
            {"issue_type": f.issue_type, "file": f.file, "detail": f.detail}
            for f in result.findings
        ]
        json.dump(data, sys.stdout, indent=2)
        print()
        return

    if not result.findings:
        console.print("[green]audit: all clear[/green]")
        return

    counts = result.count_by_type()
    by_type = result.by_type()

    issue_labels = {
        "missing_frontmatter": "Missing Frontmatter",
        "tier_mismatch": "Tier Mismatch",
        "superseded_not_archived": "Superseded Not in d3",
        "broken_link": "Broken Links",
    }

    for issue_type, findings in by_type.items():
        label = issue_labels.get(issue_type, issue_type)
        t = Table(title=f"{label} ({len(findings)})", show_lines=False)
        t.add_column("File", style="cyan")
        t.add_column("Detail", style="yellow")
        for f in findings:
            t.add_row(f.file, f.detail)
        console.print(t)

    console.print()
    for issue_type, count in counts.items():
        label = issue_labels.get(issue_type, issue_type)
        console.print(f"  {label}: {count}")

    total = len(result.findings)
    console.print(f"\n  Total: {total} issue(s)")


def _audit_fix(docs_root: Path, result: auditmod.AuditResult):
    """Interactively add frontmatter to files flagged as missing it."""
    missing = [f for f in result.findings if f.issue_type == "missing_frontmatter"]
    if not missing:
        console.print("[green]No missing frontmatter to fix.[/green]")
        return

    console.print(f"[yellow]Found {len(missing)} file(s) with missing frontmatter.[/yellow]")

    for finding in missing:
        # Reconstruct full path
        # finding.file is relative to docs_root.parent
        full_path = docs_root.parent / finding.file
        if not full_path.exists():
            console.print(f"[red]File not found: {full_path}[/red]")
            continue

        inferred = auditmod.infer_frontmatter(full_path, docs_root)

        console.print(f"\n[bold]File:[/bold] {finding.file}")
        console.print(f"  Inferred title:    {inferred.title}")
        console.print(f"  Inferred category: {inferred.category}")
        console.print(f"  Inferred status:   {inferred.status}")
        console.print(f"  Inferred created:  {inferred.created}")

        answer = input("  Write this frontmatter? [y/N] ").strip().lower()
        if answer != "y":
            console.print("  Skipped.")
            continue

        text = full_path.read_text(encoding="utf-8")
        new_front = marshal_frontmatter(inferred)
        full_path.write_text(new_front + "\n" + text, encoding="utf-8")
        console.print(f"  [green]Written.[/green]")


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

def cmd_index(args):
    if args.index_cmd == "rebuild":
        _index_rebuild(args)
    elif args.index_cmd == "verify":
        _index_verify(args)
    else:
        err_console.print("Usage: docctl index {rebuild|verify}")
        sys.exit(1)


def _index_rebuild(args):
    docs_root = _docs_root(args)
    if not docs_root.exists():
        err_console.print(f"[red]docs root not found: {docs_root}[/red]")
        sys.exit(2)

    # Find all immediate subdirectories that match d1/d2/d3 pattern
    # Also rebuild for the root docs/ itself
    dirs_to_index = []
    for tier in ("d1", "d2", "d3"):
        tier_dir = docs_root / tier
        if tier_dir.exists():
            dirs_to_index.append(tier_dir)
    if not dirs_to_index:
        # Rebuild for docs/ root itself if no tier dirs found
        dirs_to_index.append(docs_root)

    for d in dirs_to_index:
        out = indexmod.write_index(d)
        console.print(f"Rebuilt: {out}")


def _index_verify(args):
    docs_root = _docs_root(args)
    if not docs_root.exists():
        err_console.print(f"[red]docs root not found: {docs_root}[/red]")
        sys.exit(2)

    dirs_to_verify = []
    for tier in ("d1", "d2", "d3"):
        tier_dir = docs_root / tier
        if tier_dir.exists():
            dirs_to_verify.append(tier_dir)
    if not dirs_to_verify:
        dirs_to_verify.append(docs_root)

    all_results = []
    for d in dirs_to_verify:
        results = indexmod.verify(d)
        for r in results:
            all_results.append((str(d.relative_to(docs_root)), r))

    if args.json_out:
        data = [{"dir": dr, "status": r.status, "file": r.file, "detail": r.detail}
                for dr, r in all_results]
        json.dump(data, sys.stdout, indent=2)
        print()
        return

    if not all_results:
        console.print("[green]index verify: all clear[/green]")
        return

    t = Table(title="Index Verification Issues", show_lines=False)
    t.add_column("Status", style="yellow")
    t.add_column("Dir", style="blue")
    t.add_column("File", style="cyan")
    t.add_column("Detail")
    for dr, r in all_results:
        t.add_row(r.status, dr, r.file, r.detail)
    console.print(t)

    if any(r.status != "OK" for _, r in all_results):
        sys.exit(1)


# ---------------------------------------------------------------------------
# lint
# ---------------------------------------------------------------------------

def cmd_lint(args):
    docs_root = _docs_root(args)
    if not docs_root.exists():
        err_console.print(f"[red]docs root not found: {docs_root}[/red]")
        sys.exit(2)

    md_files = [
        p for p in docs_root.rglob("*.md")
        if p.name != "INDEX.md"
    ]

    failures: list[tuple[str, list[str]]] = []
    for md_path in sorted(md_files):
        rel = str(md_path.relative_to(docs_root.parent))
        text = md_path.read_text(encoding="utf-8", errors="replace")
        meta, _ = parse_frontmatter(text)
        if meta is None:
            failures.append((rel, ["no frontmatter found"]))
            continue
        errs = validate_schema(meta)
        if errs:
            failures.append((rel, errs))

    if args.json_out:
        data = [{"file": f, "errors": errs} for f, errs in failures]
        json.dump(data, sys.stdout, indent=2)
        print()
    else:
        if not failures:
            console.print("[green]lint: all files pass schema validation[/green]")
        else:
            for fname, errs in failures:
                for e in errs:
                    console.print(f"[red]FAIL[/red]  {fname}: {e}")

    if failures:
        sys.exit(1)


# ---------------------------------------------------------------------------
# templates
# ---------------------------------------------------------------------------

def cmd_templates(args):
    tdir = _templates_dir(args)
    names = tmplmod.list_templates(tdir)
    if not names:
        console.print("[yellow]No templates found.[/yellow]")
        return
    if args.json_out:
        json.dump(names, sys.stdout, indent=2)
        print()
        return
    t = Table(title="Available Templates", show_lines=False)
    t.add_column("Name", style="cyan")
    for n in names:
        t.add_row(n)
    console.print(t)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def cmd_render(args):
    from . import renderer as rendermod

    tdir = _templates_dir(args)
    input_text = _resolve_input(args, tdir)

    fmt = args.format
    out_path = Path(args.output) if args.output else Path(f"output.{fmt}")

    try:
        rendermod.render(input_text, out_path, fmt=fmt)
    except RuntimeError as e:
        err_console.print(f"[red]{e}[/red]")
        sys.exit(1)

    console.print(f"Rendered: {out_path}")


# ---------------------------------------------------------------------------
# slides
# ---------------------------------------------------------------------------

def cmd_slides(args):
    from . import renderer as rendermod

    tdir = _templates_dir(args)
    input_text = _resolve_input(args, tdir)

    fmt = args.format
    out_path = Path(args.output) if args.output else Path(f"slides.{fmt}")

    try:
        rendermod.render(input_text, out_path, fmt=fmt, force_slides=True)
    except RuntimeError as e:
        err_console.print(f"[red]{e}[/red]")
        sys.exit(1)

    console.print(f"Rendered slides: {out_path}")


def _resolve_input(args, tdir) -> str:
    """Build the document text from either --template or --input."""
    if args.template and args.input:
        err_console.print("[red]Specify either --template or --input, not both.[/red]")
        sys.exit(1)

    provided_vars: dict = {}
    if args.vars:
        provided_vars = tmplmod.load_vars_file(Path(args.vars))

    if args.template:
        try:
            raw_text, var_defs = tmplmod.load_template(args.template, tdir)
        except FileNotFoundError as e:
            err_console.print(f"[red]{e}[/red]")
            sys.exit(1)

        errs = tmplmod.validate_vars(var_defs, provided_vars)
        if errs:
            err_console.print("[red]Variable validation failed:[/red]")
            for e in errs:
                err_console.print(f"  {e}")
            sys.exit(1)

        return tmplmod.render_template(raw_text, var_defs, provided_vars, tdir)

    elif args.input:
        in_path = Path(args.input)
        if not in_path.exists():
            err_console.print(f"[red]Input file not found: {in_path}[/red]")
            sys.exit(1)
        raw_text = in_path.read_text(encoding="utf-8")
        if provided_vars:
            # Render the file as a Jinja2 template with the provided vars
            _, var_defs = [], []
            return tmplmod.render_template(raw_text, [], provided_vars)
        return raw_text

    else:
        err_console.print("[red]Either --template or --input is required.[/red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def cmd_summary(args):
    docs_root = _docs_root(args)
    summary = briefingmod.text_summary(docs_root if docs_root.exists() else None)
    if args.json_out:
        json.dump({"summary": summary}, sys.stdout, indent=2)
        print()
    else:
        console.print(summary)
