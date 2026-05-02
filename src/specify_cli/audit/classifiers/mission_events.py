"""Classifier for mission-events.jsonl mission artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from ..detectors import detect_forbidden_keys, detect_legacy_keys
from ..models import MissionFinding, Severity
from ..shape_registry import check_unknown_keys


def _classify_jsonl_file(
    path: Path,
    artifact_path: str,
    artifact_type: str,
) -> list[MissionFinding]:
    """Shared JSONL classifier helper.

    Reads *path* line by line.  For each non-blank line:
    - On decode error: emits ``CORRUPT_JSONL`` and continues (collects all).
    - On valid line: runs legacy-key, forbidden-key, and unknown-key checks.

    Args:
        path: Absolute path to the JSONL file.
        artifact_path: Relative artifact path used in findings.
        artifact_type: Key into ``KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT``.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Never raises.
    """
    if not path.exists():
        return []

    findings: list[MissionFinding] = []

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            MissionFinding(
                code="CORRUPT_JSONL",
                severity=Severity.ERROR,
                artifact_path=artifact_path,
                detail=f"could not read file: {exc}",
            )
        ]

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        try:
            obj: dict[str, object] = json.loads(stripped)
        except json.JSONDecodeError as exc:
            findings.append(
                MissionFinding(
                    code="CORRUPT_JSONL",
                    severity=Severity.ERROR,
                    artifact_path=artifact_path,
                    detail=f"line {line_number}: {exc.msg}",
                )
            )
            continue

        if not isinstance(obj, dict):
            findings.append(
                MissionFinding(
                    code="CORRUPT_JSONL",
                    severity=Severity.ERROR,
                    artifact_path=artifact_path,
                    detail=f"line {line_number}: expected JSON object, got {type(obj).__name__}",
                )
            )
            continue

        findings.extend(detect_legacy_keys(obj, artifact_path))
        findings.extend(detect_forbidden_keys(obj, artifact_path))
        findings.extend(check_unknown_keys(artifact_type, obj, artifact_path))

    return findings


def classify_mission_events_jsonl(mission_dir: Path) -> list[MissionFinding]:
    """Classify mission-events.jsonl for legacy keys, forbidden keys, and corruption.

    Args:
        mission_dir: Path to the mission directory.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Returns ``[]`` when the file is absent.
    """
    path = mission_dir / "mission-events.jsonl"
    return _classify_jsonl_file(path, "mission-events.jsonl", "mission_event_row")
