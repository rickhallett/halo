"""Pandoc/Marp wrapper for document rendering.

Handles format detection and subprocess invocation. Pandoc and Marp are
expected as system packages - this module does not install them.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


PANDOC_FORMATS = {"pdf", "html", "docx", "pptx"}
MARP_FORMATS = {"pdf", "html", "pptx"}


def _require(binary: str) -> str:
    """Return binary path or raise with install hint."""
    path = shutil.which(binary)
    if not path:
        hints = {
            "pandoc": "install pandoc: https://pandoc.org/installing.html",
            "marp": "install marp-cli: npm install -g @marp-team/marp-cli",
        }
        hint = hints.get(binary, f"install {binary}")
        raise RuntimeError(f"{binary!r} not found on PATH - {hint}")
    return path


def is_slides(text: str) -> bool:
    """Detect whether a document is a Marp slide deck (marp: true in frontmatter)."""
    import re
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return False
    try:
        import yaml
        front = yaml.safe_load(m.group(1)) or {}
        return bool(front.get("marp", False))
    except Exception:
        return False


def render_pandoc(
    input_text: str,
    output_path: Path,
    fmt: str = "pdf",
) -> None:
    """Render markdown text to output_path using pandoc."""
    if fmt not in PANDOC_FORMATS:
        raise ValueError(f"unsupported pandoc format: {fmt!r} (valid: {sorted(PANDOC_FORMATS)})")

    pandoc = _require("pandoc")

    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8",
                                     delete=False) as tmp:
        tmp.write(input_text)
        tmp_path = tmp.name

    try:
        cmd = [pandoc, tmp_path, "-o", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"pandoc failed (exit {result.returncode}):\n{result.stderr.strip()}"
            )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def render_marp(
    input_text: str,
    output_path: Path,
    fmt: str = "pdf",
) -> None:
    """Render markdown slides to output_path using marp-cli."""
    if fmt not in MARP_FORMATS:
        raise ValueError(f"unsupported marp format: {fmt!r} (valid: {sorted(MARP_FORMATS)})")

    marp = _require("marp")

    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8",
                                     delete=False) as tmp:
        tmp.write(input_text)
        tmp_path = tmp.name

    try:
        flag = {"pdf": "--pdf", "html": "--html", "pptx": "--pptx"}[fmt]
        cmd = [marp, tmp_path, flag, "-o", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"marp failed (exit {result.returncode}):\n{result.stderr.strip()}"
            )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def render(
    input_text: str,
    output_path: Path,
    fmt: str = "pdf",
    force_slides: bool = False,
) -> None:
    """Auto-detect renderer (pandoc or marp) and render to output_path."""
    use_marp = force_slides or is_slides(input_text)
    if use_marp:
        render_marp(input_text, output_path, fmt)
    else:
        render_pandoc(input_text, output_path, fmt)
