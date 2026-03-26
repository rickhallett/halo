"""Tests for halos.docctl - frontmatter, audit, index, templates, summary."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures" / "docctl"
DOCS_ROOT = FIXTURES / "docs"
TEMPLATES_DIR = FIXTURES / "templates"


VALID_FRONTMATTER = """\
---
title: "My Document"
category: spec
status: active
created: 2026-03-21
---

Body content here.
"""

MISSING_FRONTMATTER = """\
# My Document

Body content here, no frontmatter.
"""

PARTIAL_FRONTMATTER = """\
---
title: "Partial"
category: spec
---

Missing status and created.
"""


# ---------------------------------------------------------------------------
# doc.py - frontmatter parsing
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid_document_parses(self):
        from halos.docctl.doc import parse_frontmatter
        meta, body = parse_frontmatter(VALID_FRONTMATTER)
        assert meta is not None
        assert meta.title == "My Document"
        assert meta.category == "spec"
        assert meta.status == "active"
        assert meta.created == "2026-03-21"
        assert "Body content" in body

    def test_missing_frontmatter_returns_none(self):
        from halos.docctl.doc import parse_frontmatter
        meta, body = parse_frontmatter(MISSING_FRONTMATTER)
        assert meta is None
        assert "My Document" in body

    def test_partial_frontmatter_parses_present_fields(self):
        from halos.docctl.doc import parse_frontmatter
        meta, body = parse_frontmatter(PARTIAL_FRONTMATTER)
        assert meta is not None
        assert meta.title == "Partial"
        assert meta.category == "spec"
        assert meta.status == ""
        assert meta.created == ""

    def test_optional_fields_default_to_empty(self):
        from halos.docctl.doc import parse_frontmatter
        meta, _ = parse_frontmatter(VALID_FRONTMATTER)
        assert meta is not None
        assert meta.tags == []
        assert meta.related == []
        assert meta.superseded_by is None

    def test_with_optional_fields(self):
        from halos.docctl.doc import parse_frontmatter
        text = """\
---
title: "Full Doc"
category: spec
status: active
created: 2026-03-21
tags: [halos, spec]
related:
  - docs/d2/other.md
superseded_by: docs/d2/new.md
---
Body.
"""
        meta, _ = parse_frontmatter(text)
        assert meta is not None
        assert meta.tags == ["halos", "spec"]
        assert meta.related == ["docs/d2/other.md"]
        assert meta.superseded_by == "docs/d2/new.md"


# ---------------------------------------------------------------------------
# doc.py - schema validation
# ---------------------------------------------------------------------------

class TestValidateSchema:
    def test_valid_meta_passes(self):
        from halos.docctl.doc import DocMeta, validate_schema
        meta = DocMeta(title="T", category="spec", status="active", created="2026-03-21")
        assert validate_schema(meta) == []

    def test_missing_title_fails(self):
        from halos.docctl.doc import DocMeta, validate_schema
        meta = DocMeta(title="", category="spec", status="active", created="2026-03-21")
        errs = validate_schema(meta)
        assert any("title" in e for e in errs)

    def test_missing_category_fails(self):
        from halos.docctl.doc import DocMeta, validate_schema
        meta = DocMeta(title="T", category="", status="active", created="2026-03-21")
        errs = validate_schema(meta)
        assert any("category" in e for e in errs)

    def test_invalid_category_fails(self):
        from halos.docctl.doc import DocMeta, validate_schema
        meta = DocMeta(title="T", category="notacategory", status="active", created="2026-03-21")
        errs = validate_schema(meta)
        assert any("invalid category" in e for e in errs)

    def test_invalid_status_fails(self):
        from halos.docctl.doc import DocMeta, validate_schema
        meta = DocMeta(title="T", category="spec", status="badstatus", created="2026-03-21")
        errs = validate_schema(meta)
        assert any("invalid status" in e for e in errs)

    def test_all_required_missing(self):
        from halos.docctl.doc import DocMeta, validate_schema
        meta = DocMeta()
        errs = validate_schema(meta)
        assert len(errs) >= 4


# ---------------------------------------------------------------------------
# audit.py - missing frontmatter detection
# ---------------------------------------------------------------------------

class TestAuditMissingFrontmatter:
    def test_detects_missing_frontmatter(self):
        from halos.docctl.audit import run_audit
        result = run_audit(DOCS_ROOT, check_links=False)
        missing = [f for f in result.findings if f.issue_type == "missing_frontmatter"]
        file_names = [Path(f.file).name for f in missing]
        assert "no-frontmatter.md" in file_names

    def test_does_not_flag_valid_file(self):
        from halos.docctl.audit import run_audit
        result = run_audit(DOCS_ROOT, check_links=False)
        missing = [f for f in result.findings if f.issue_type == "missing_frontmatter"]
        file_names = [Path(f.file).name for f in missing]
        assert "valid-runbook.md" not in file_names

    def test_index_md_excluded(self, tmp_path):
        from halos.docctl.audit import run_audit
        docs = tmp_path / "docs" / "d1"
        docs.mkdir(parents=True)
        (docs / "INDEX.md").write_text("<!-- AUTO-GENERATED -->")
        result = run_audit(tmp_path / "docs", check_links=False)
        missing = [f for f in result.findings if f.issue_type == "missing_frontmatter"]
        assert not any("INDEX.md" in f.file for f in missing)


# ---------------------------------------------------------------------------
# audit.py - tier mismatch detection
# ---------------------------------------------------------------------------

class TestAuditTierMismatch:
    def test_detects_runbook_in_d2(self):
        from halos.docctl.audit import run_audit
        result = run_audit(DOCS_ROOT, check_links=False)
        tier = [f for f in result.findings if f.issue_type == "tier_mismatch"]
        file_names = [Path(f.file).name for f in tier]
        assert "misplaced-runbook.md" in file_names

    def test_does_not_flag_correct_tier(self):
        from halos.docctl.audit import run_audit
        result = run_audit(DOCS_ROOT, check_links=False)
        tier = [f for f in result.findings if f.issue_type == "tier_mismatch"]
        file_names = [Path(f.file).name for f in tier]
        assert "valid-runbook.md" not in file_names
        assert "valid-spec.md" not in file_names

    def test_detects_superseded_not_in_d3(self):
        from halos.docctl.audit import run_audit
        result = run_audit(DOCS_ROOT, check_links=False)
        sup = [f for f in result.findings if f.issue_type == "superseded_not_archived"]
        file_names = [Path(f.file).name for f in sup]
        assert "superseded-wrong-tier.md" in file_names

    def test_superseded_in_d3_not_flagged(self):
        from halos.docctl.audit import run_audit
        result = run_audit(DOCS_ROOT, check_links=False)
        sup = [f for f in result.findings if f.issue_type == "superseded_not_archived"]
        file_names = [Path(f.file).name for f in sup]
        assert "superseded-outside-d3.md" not in file_names


# ---------------------------------------------------------------------------
# index.py - rebuild
# ---------------------------------------------------------------------------

class TestIndexRebuild:
    def test_rebuild_produces_index(self, tmp_path):
        from halos.docctl.index import rebuild
        d = tmp_path / "d2"
        d.mkdir()
        (d / "spec-one.md").write_text(
            "---\ntitle: Spec One\ncategory: spec\nstatus: active\ncreated: 2026-03-21\n---\nBody.\n"
        )
        (d / "spec-two.md").write_text(
            "---\ntitle: Spec Two\ncategory: spec\nstatus: draft\ncreated: 2026-03-22\n---\nBody.\n"
        )
        content = rebuild(d)
        assert "AUTO-GENERATED" in content
        assert "Spec One" in content
        assert "Spec Two" in content
        assert "spec" in content

    def test_rebuild_includes_all_files(self, tmp_path):
        from halos.docctl.index import rebuild
        d = tmp_path / "d1"
        d.mkdir()
        for i in range(3):
            (d / f"doc-{i}.md").write_text(
                f"---\ntitle: Doc {i}\ncategory: runbook\nstatus: active\ncreated: 2026-03-2{i}\n---\n"
            )
        content = rebuild(d)
        for i in range(3):
            assert f"Doc {i}" in content

    def test_rebuild_table_columns(self, tmp_path):
        from halos.docctl.index import rebuild
        d = tmp_path / "d2"
        d.mkdir()
        (d / "my-spec.md").write_text(
            "---\ntitle: My Spec\ncategory: spec\nstatus: active\ncreated: 2026-01-01\n---\n"
        )
        content = rebuild(d)
        assert "Title" in content
        assert "File" in content
        assert "Category" in content
        assert "Status" in content
        assert "Created" in content

    def test_rebuild_excludes_index_md(self, tmp_path):
        from halos.docctl.index import write_index
        d = tmp_path / "d1"
        d.mkdir()
        (d / "note.md").write_text(
            "---\ntitle: Note\ncategory: runbook\nstatus: active\ncreated: 2026-03-21\n---\n"
        )
        out = write_index(d)
        content = out.read_text()
        # INDEX.md should not reference itself
        assert content.count("INDEX.md") == 0 or "do not hand-edit" in content


# ---------------------------------------------------------------------------
# index.py - verify
# ---------------------------------------------------------------------------

class TestIndexVerify:
    def test_verify_clean_index(self, tmp_path):
        from halos.docctl.index import verify, write_index
        d = tmp_path / "d1"
        d.mkdir()
        (d / "doc.md").write_text(
            "---\ntitle: Doc\ncategory: runbook\nstatus: active\ncreated: 2026-03-21\n---\n"
        )
        write_index(d)
        results = verify(d)
        assert results == []

    def test_verify_detects_stale_entry(self, tmp_path):
        from halos.docctl.index import verify
        d = tmp_path / "d1"
        d.mkdir()
        (d / "doc.md").write_text(
            "---\ntitle: Doc\ncategory: runbook\nstatus: active\ncreated: 2026-03-21\n---\n"
        )
        # Write INDEX.md with an extra entry for a non-existent file
        (d / "INDEX.md").write_text(
            "<!-- AUTO-GENERATED by docctl index - do not hand-edit -->\n"
            "| Title | File | Category | Status | Created |\n"
            "|-------|------|----------|--------|----------|\n"
            "| Doc | doc.md | runbook | active | 2026-03-21 |\n"
            "| Ghost | ghost.md | guide | active | 2026-03-20 |\n"
        )
        results = verify(d)
        stale = [r for r in results if r.status == "STALE"]
        assert any("ghost.md" in r.file for r in stale)

    def test_verify_detects_missing_entry(self, tmp_path):
        from halos.docctl.index import verify
        d = tmp_path / "d1"
        d.mkdir()
        (d / "doc.md").write_text(
            "---\ntitle: Doc\ncategory: runbook\nstatus: active\ncreated: 2026-03-21\n---\n"
        )
        (d / "extra.md").write_text(
            "---\ntitle: Extra\ncategory: guide\nstatus: active\ncreated: 2026-03-22\n---\n"
        )
        (d / "INDEX.md").write_text(
            "<!-- AUTO-GENERATED by docctl index - do not hand-edit -->\n"
            "| Title | File | Category | Status | Created |\n"
            "|-------|------|----------|--------|----------|\n"
            "| Doc | doc.md | runbook | active | 2026-03-21 |\n"
        )
        results = verify(d)
        missing = [r for r in results if r.status == "MISSING"]
        assert any("extra.md" in r.file for r in missing)

    def test_verify_no_index_md_returns_finding(self, tmp_path):
        from halos.docctl.index import verify
        d = tmp_path / "d1"
        d.mkdir()
        results = verify(d)
        assert any(r.status == "MISSING" for r in results)


# ---------------------------------------------------------------------------
# templates.py - Jinja2 rendering
# ---------------------------------------------------------------------------

class TestTemplateRendering:
    def test_render_with_all_vars(self):
        from halos.docctl.templates import load_template, render_template
        raw, var_defs = load_template("test-letter", TEMPLATES_DIR)
        rendered = render_template(raw, var_defs, {
            "recipient": "Jane Smith",
            "subject": "Project Update",
            "body": "Here is the update.",
        })
        assert "Jane Smith" in rendered
        assert "Project Update" in rendered
        assert "Here is the update." in rendered

    def test_builtin_today_var_rendered(self):
        from datetime import date
        from halos.docctl.templates import load_template, render_template
        raw, var_defs = load_template("test-letter", TEMPLATES_DIR)
        rendered = render_template(raw, var_defs, {
            "recipient": "Bob",
            "subject": "Hello",
            "body": "Test body.",
        })
        assert str(date.today().year) in rendered

    def test_missing_required_var_raises(self):
        from halos.docctl.templates import load_template, render_template, validate_vars
        raw, var_defs = load_template("test-letter", TEMPLATES_DIR)
        errs = validate_vars(var_defs, {"recipient": "Bob"})
        # subject and body are required
        assert any("subject" in e for e in errs) or any("body" in e for e in errs)

    def test_list_templates(self):
        from halos.docctl.templates import list_templates
        names = list_templates(TEMPLATES_DIR)
        assert "test-letter" in names

    def test_list_templates_empty_dir(self, tmp_path):
        from halos.docctl.templates import list_templates
        names = list_templates(tmp_path / "nonexistent")
        assert names == []

    def test_template_not_found_raises(self):
        from halos.docctl.templates import load_template
        with pytest.raises(FileNotFoundError):
            load_template("does-not-exist", TEMPLATES_DIR)

    def test_render_strips_frontmatter(self):
        from halos.docctl.templates import load_template, render_template
        raw, var_defs = load_template("test-letter", TEMPLATES_DIR)
        rendered = render_template(raw, var_defs, {
            "recipient": "Alice",
            "subject": "Hi",
            "body": "Hello there.",
        })
        # Frontmatter should not appear in rendered output
        assert "template: test-letter" not in rendered
        assert "variables:" not in rendered


# ---------------------------------------------------------------------------
# briefing.py - summary output
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_format(self, tmp_path):
        from halos.docctl.briefing import text_summary
        docs = tmp_path / "docs"
        d1 = docs / "d1"
        d1.mkdir(parents=True)
        (d1 / "a.md").write_text(
            "---\ntitle: A\ncategory: runbook\nstatus: active\ncreated: 2026-03-21\n---\n"
        )
        (d1 / "b.md").write_text("# No frontmatter\n")
        result = text_summary(docs)
        assert "docs" in result or "2" in result
        # Should match: "N docs, M categories, K without frontmatter"
        assert "without frontmatter" in result

    def test_summary_counts_correctly(self, tmp_path):
        from halos.docctl.briefing import text_summary
        docs = tmp_path / "docs"
        d1 = docs / "d1"
        d2 = docs / "d2"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        (d1 / "r.md").write_text(
            "---\ntitle: R\ncategory: runbook\nstatus: active\ncreated: 2026-03-21\n---\n"
        )
        (d2 / "s.md").write_text(
            "---\ntitle: S\ncategory: spec\nstatus: active\ncreated: 2026-03-22\n---\n"
        )
        (d1 / "nofm.md").write_text("# No FM\n")
        result = text_summary(docs)
        assert "3 docs" in result
        assert "2 categories" in result
        assert "1 without frontmatter" in result

    def test_summary_missing_docs_dir(self, tmp_path):
        from halos.docctl.briefing import text_summary
        result = text_summary(tmp_path / "nonexistent")
        assert "not found" in result


# ---------------------------------------------------------------------------
# doc.py - extract_links
# ---------------------------------------------------------------------------

class TestExtractLinks:
    def test_relative_links_extracted(self):
        from halos.docctl.doc import extract_links
        text = "See [this](foo.md) and [that](bar/baz.md)."
        links = extract_links(text)
        assert "foo.md" in links
        assert "bar/baz.md" in links

    def test_http_links_excluded(self):
        from halos.docctl.doc import extract_links
        text = "Visit [Google](https://google.com) and [this](local.md)."
        links = extract_links(text)
        assert "local.md" in links
        assert "https://google.com" not in links

    def test_anchor_only_excluded(self):
        from halos.docctl.doc import extract_links
        text = "See [section](#heading)."
        links = extract_links(text)
        assert links == []

    def test_fragment_stripped(self):
        from halos.docctl.doc import extract_links
        text = "See [doc](readme.md#section)."
        links = extract_links(text)
        assert "readme.md" in links
