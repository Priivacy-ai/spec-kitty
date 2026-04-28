"""Mission brief file management for intake flows.

Provides two local artefacts written by ``spec-kitty intake``:

* ``.kittify/mission-brief.md``  — plan document with provenance header for the LLM
* ``.kittify/brief-source.yaml`` — SHA-256 fingerprint + metadata for traceability

Neither file should be committed to version control; both are gitignored.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


MISSION_BRIEF_FILENAME = "mission-brief.md"
BRIEF_SOURCE_FILENAME = "brief-source.yaml"


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def write_mission_brief(
    repo_root: Path,
    content: str,
    source_file: str,
    *,
    source_agent: str | None = None,
) -> tuple[Path, Path]:
    """Write ``.kittify/mission-brief.md`` and ``.kittify/brief-source.yaml``.

    The brief file is prefixed with two HTML comment lines that record
    provenance, followed by a blank line, then the original content.
    The YAML sidecar captures the source path, ingestion timestamp, and
    SHA-256 hash of the *raw* content (before the header is prepended).

    Args:
        repo_root: Project root directory.
        content: Raw plan document content.
        source_file: Human-readable source path or label (e.g. ``"stdin"``).
        source_agent: Optional harness/agent identifier (e.g. ``"opencode"``).
            When ``None``, the ``source_agent`` key is omitted from
            ``brief-source.yaml`` entirely (no null written).

    Returns a tuple of ``(brief_path, source_path)``.
    """
    kittify = repo_root / ".kittify"
    kittify.mkdir(exist_ok=True)
    brief_path = kittify / MISSION_BRIEF_FILENAME
    source_path = kittify / BRIEF_SOURCE_FILENAME

    # Clean any partial state from a previous interrupted write.
    if brief_path.exists() != source_path.exists():
        brief_path.unlink(missing_ok=True)
        source_path.unlink(missing_ok=True)

    brief_hash = hashlib.sha256(content.encode()).hexdigest()
    ingested_at = datetime.now(tz=UTC).isoformat()

    header = f"<!-- spec-kitty intake: ingested from {source_file} at {ingested_at} -->\n<!-- brief_hash: {brief_hash} -->"
    brief_text = header + "\n\n" + content

    source_data: dict[str, str] = {
        "source_file": source_file,
        "ingested_at": ingested_at,
        "brief_hash": brief_hash,
    }
    if source_agent is not None:
        source_data["source_agent"] = source_agent

    # Write using temp files + replace() for atomic writes.
    tmp_brief = kittify / f".tmp-brief-{os.getpid()}.md"
    tmp_source = kittify / f".tmp-source-{os.getpid()}.yaml"
    try:
        tmp_brief.write_text(brief_text, encoding="utf-8")
        tmp_source.write_text(
            yaml.safe_dump(source_data, default_flow_style=False),
            encoding="utf-8",
        )
        tmp_brief.replace(brief_path)
        tmp_source.replace(source_path)
    except Exception:
        tmp_brief.unlink(missing_ok=True)
        tmp_source.unlink(missing_ok=True)
        raise

    return brief_path, source_path


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def read_mission_brief(repo_root: Path) -> str | None:
    """Return the full contents of ``.kittify/mission-brief.md`` or ``None``."""
    path = repo_root / ".kittify" / MISSION_BRIEF_FILENAME
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return None


def read_brief_source(repo_root: Path) -> dict[str, Any] | None:
    """Return parsed YAML from ``.kittify/brief-source.yaml`` or ``None``."""
    path = repo_root / ".kittify" / BRIEF_SOURCE_FILENAME
    if not path.exists():
        return None
    try:
        result = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return result if isinstance(result, dict) else None
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Clear helper
# ---------------------------------------------------------------------------


def clear_mission_brief(repo_root: Path) -> None:
    """Remove both brief artefacts if they exist (idempotent)."""
    for filename in (MISSION_BRIEF_FILENAME, BRIEF_SOURCE_FILENAME):
        path = repo_root / ".kittify" / filename
        if path.exists():
            path.unlink()
