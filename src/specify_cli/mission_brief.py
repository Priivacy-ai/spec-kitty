"""Mission brief file management for intake flows.

Provides two local artefacts written by ``spec-kitty intake``:

* ``.kittify/mission-brief.md``  — plan document with provenance header for the LLM
* ``.kittify/brief-source.yaml`` — SHA-256 fingerprint + metadata for traceability

Neither file should be committed to version control; both are gitignored.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
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
) -> tuple[Path, Path]:
    """Write ``.kittify/mission-brief.md`` and ``.kittify/brief-source.yaml``.

    The brief file is prefixed with two HTML comment lines that record
    provenance, followed by a blank line, then the original content.
    The YAML sidecar captures the source path, ingestion timestamp, and
    SHA-256 hash of the *raw* content (before the header is prepended).

    Returns a tuple of ``(brief_path, source_path)``.
    """
    kittify = repo_root / ".kittify"
    kittify.mkdir(exist_ok=True)

    brief_hash = hashlib.sha256(content.encode()).hexdigest()
    ingested_at = datetime.now(tz=timezone.utc).isoformat()

    header = (
        f"<!-- spec-kitty intake: ingested from {source_file} at {ingested_at} -->\n"
        f"<!-- brief_hash: {brief_hash} -->"
    )
    brief_text = header + "\n\n" + content

    brief_path = kittify / MISSION_BRIEF_FILENAME
    brief_path.write_text(brief_text, encoding="utf-8")

    source_data: dict[str, str] = {
        "source_file": source_file,
        "ingested_at": ingested_at,
        "brief_hash": brief_hash,
    }
    source_path = kittify / BRIEF_SOURCE_FILENAME
    source_path.write_text(yaml.dump(source_data, default_flow_style=False), encoding="utf-8")

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
        result: dict[str, Any] | None = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return result
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
