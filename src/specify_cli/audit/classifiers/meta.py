"""Classifier for meta.json mission artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..detectors import detect_legacy_keys
from ..models import MissionFinding, Severity
from ..shape_registry import check_unknown_keys

# ULID character set: Crockford Base32 (excludes I, L, O, U)
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def classify_meta_json(mission_dir: Path) -> list[MissionFinding]:
    """Classify meta.json for legacy keys, identity issues, and unknown keys.

    Returns an empty list when meta.json is absent (the identity adapter
    handles IDENTITY_MISSING for orphan missions at the repo level).

    Args:
        mission_dir: Path to the mission directory (e.g. kitty-specs/NNN-slug/).

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Never raises — all exceptions become findings.
    """
    path = mission_dir / "meta.json"
    if not path.exists():
        return []

    findings: list[MissionFinding] = []

    try:
        obj: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [
            MissionFinding(
                code="CORRUPT_JSONL",
                severity=Severity.ERROR,
                artifact_path="meta.json",
                detail=f"JSON decode error: {exc.msg}",
            )
        ]

    # Legacy key detection (work_package_id is valid in meta, so no extra_keys)
    findings.extend(detect_legacy_keys(obj, "meta.json"))

    # Identity checks
    mission_id = obj.get("mission_id")
    if mission_id is None:
        findings.append(
            MissionFinding(
                code="IDENTITY_MISSING",
                severity=Severity.ERROR,
                artifact_path="meta.json",
                detail="missing mission_id field",
            )
        )
    elif not isinstance(mission_id, str) or not _ULID_RE.match(mission_id):
        findings.append(
            MissionFinding(
                code="IDENTITY_INVALID",
                severity=Severity.ERROR,
                artifact_path="meta.json",
                detail=f"mission_id is not a valid ULID: {mission_id!r}",
            )
        )

    # Unknown key detection
    findings.extend(check_unknown_keys("meta.json", obj, "meta.json"))

    return findings
