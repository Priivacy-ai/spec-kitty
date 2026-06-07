"""MarkdownRulesWriter — generic Markdown section idempotency writer.

Manages a ``<!-- spec-kitty:orientation --> … <!-- /spec-kitty:orientation -->``
section in a Markdown file.  Supports two modes:

- ``append_mode=True``: the section lives *within* a larger existing file
  (e.g., CLAUDE.md, GEMINI.md).  Appends on first write; replaces in-place
  on subsequent writes.
- ``append_mode=False``: the file *is* the section (e.g.,
  ``.cursor/rules/spec-kitty.mdc``).  Writes the full rendered block as the
  file's entire content.

All writes are atomic: a temp file in the same directory is written first,
then ``os.replace()`` is used to make the swap visible to readers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..content import SECTION_CLOSE, SECTION_OPEN, SessionPresenceContent

__all__ = ["MarkdownRulesWriter"]


@dataclass
class MarkdownRulesWriter:
    """Generic Markdown-based harness writer with section idempotency.

    Parameters
    ----------
    harness_key:
        Identifies this harness in the writer registry (e.g. ``"gemini"``).
    rules_path:
        Path to the target file, relative to *project_root*.
    append_mode:
        ``True`` when the orientation section lives within a larger file;
        ``False`` when the file IS the section.
    check_dir:
        Optional directory path (relative to *project_root*) to check in
        ``can_write()`` instead of the parent of ``rules_path``.  Use this
        for harnesses whose rules file lives in a subdirectory that may not
        yet exist (e.g. ``.cursor/rules/spec-kitty.mdc`` → ``check_dir=".cursor"``).
        When ``None`` (default), ``can_write()`` checks the parent of ``rules_path``.
    """

    harness_key: str
    rules_path: str
    append_mode: bool
    check_dir: str | None = None

    def can_write(self, project_root: Path) -> bool:
        """Return ``True`` when the harness root (or rules parent) directory exists."""
        if self.check_dir is not None:
            return (project_root / self.check_dir).exists()
        return (project_root / self.rules_path).parent.exists()

    def has_presence(self, project_root: Path) -> bool:
        """Return ``True`` when the orientation section marker is present."""
        target = project_root / self.rules_path
        if not target.exists():
            return False
        try:
            return SECTION_OPEN in target.read_text(encoding="utf-8")
        except OSError:
            return False

    def write(self, project_root: Path, content: SessionPresenceContent) -> None:
        """Write or replace the orientation section.

        Idempotent — safe to call when the section is already present.
        A second call replaces the existing section in-place; no duplicates.
        """
        target = project_root / self.rules_path
        rendered = content.render()
        if self.append_mode:
            if target.exists():
                existing = target.read_text(encoding="utf-8")
                new_text = (
                    _replace_section(existing, rendered)
                    if SECTION_OPEN in existing
                    else existing.rstrip("\n") + "\n\n" + rendered
                )
            else:
                new_text = rendered
        else:
            new_text = rendered
        _atomic_write(target, new_text)

    def remove(self, project_root: Path) -> None:
        """Remove the orientation section.

        In ``append_mode=True``: strips the section, leaving the rest of the
        file intact.  In ``append_mode=False``: deletes the file entirely.
        No-op if the file does not exist or the section is not present.
        """
        target = project_root / self.rules_path
        if not target.exists():
            return
        if self.append_mode:
            existing = target.read_text(encoding="utf-8")
            if SECTION_OPEN not in existing:
                return
            new_text = _remove_section(existing)
            _atomic_write(target, new_text)
        else:
            target.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _atomic_write(target: Path, text: str) -> None:
    """Write *text* to *target* atomically via a sibling temp file.

    Creates parent directories if they do not exist.
    On failure the temp file is cleaned up and the exception re-raised.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _replace_section(text: str, replacement: str) -> str:
    """Replace the block from ``SECTION_OPEN`` to ``SECTION_CLOSE`` (inclusive).

    Falls back to appending *replacement* if either marker is not found.
    """
    start = text.find(SECTION_OPEN)
    end = text.find(SECTION_CLOSE, start)
    if start == -1 or end == -1:
        return text + "\n\n" + replacement
    end += len(SECTION_CLOSE)
    if text[end:end + 1] == "\n":
        end += 1
    return text[:start] + replacement + text[end:]


def _remove_section(text: str) -> str:
    """Remove the block from ``SECTION_OPEN`` to ``SECTION_CLOSE`` (inclusive).

    Returns *text* unchanged if either marker is not found.
    """
    start = text.find(SECTION_OPEN)
    end = text.find(SECTION_CLOSE, start)
    if start == -1 or end == -1:
        return text
    end += len(SECTION_CLOSE)
    if text[end:end + 1] == "\n":
        end += 1
    # Remove preceding blank line if present, keeping the rest clean.
    prefix = text[:start].rstrip("\n")
    suffix = text[end:]
    if prefix:
        return (prefix + "\n" + suffix).strip("\n") + "\n"
    return suffix
