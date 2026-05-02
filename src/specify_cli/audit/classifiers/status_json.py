"""Classifier for status.json mission artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from ..detectors import detect_legacy_keys
from ..models import MissionFinding, Severity
from ..shape_registry import check_unknown_keys


def classify_status_json(
    mission_dir: Path,
    *,
    skip_drift: bool = False,
) -> list[MissionFinding]:
    """Classify status.json for legacy keys, unknown keys, and snapshot drift.

    The drift check is read-only: it uses ``materialize_to_json`` (which
    produces a deterministic string without writing any file) rather than
    ``materialize`` (which writes status.json to disk).  When
    ``skip_drift=True`` the drift check is skipped entirely — the engine
    passes this flag when ``status.events.jsonl`` has corruption that would
    cause the reducer to raise.

    Args:
        mission_dir: Path to the mission directory.
        skip_drift: If True, skip the snapshot drift check.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Never raises — all exceptions become findings.
    """
    path = mission_dir / "status.json"
    if not path.exists():
        return []

    findings: list[MissionFinding] = []

    try:
        raw_text = path.read_text(encoding="utf-8")
        obj: dict[str, object] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return [
            MissionFinding(
                code="CORRUPT_JSON",
                severity=Severity.ERROR,
                artifact_path="status.json",
                detail=f"JSON decode error: {exc.msg}",
            )
        ]

    # Legacy key detection
    findings.extend(detect_legacy_keys(obj, "status.json"))

    # Unknown key detection
    findings.extend(check_unknown_keys("status.json", obj, "status.json"))

    if skip_drift:
        return findings

    # Read-only drift check (C-001 compliance).
    # NEVER call reducer.materialize() — it writes status.json to disk.
    # materialize_snapshot() keeps parity with materialize() without writing.
    try:
        from specify_cli.status.reducer import materialize_snapshot, materialize_to_json

        snapshot = materialize_snapshot(mission_dir)
        computed_json = materialize_to_json(snapshot)
    except Exception as exc:
        findings.append(
            MissionFinding(
                code="SNAPSHOT_DRIFT",
                severity=Severity.ERROR,
                artifact_path="status.json",
                detail=f"reducer raised during drift check: {exc}",
            )
        )
        return findings

    # Normalise both sides: parse + re-serialise with identical options
    try:
        persisted_normalised = (
            json.dumps(json.loads(raw_text), sort_keys=True, indent=2) + "\n"
        )
    except Exception:
        # raw_text is already parsed above, so this branch is unreachable in practice
        persisted_normalised = raw_text

    if computed_json != persisted_normalised:
        findings.append(
            MissionFinding(
                code="SNAPSHOT_DRIFT",
                severity=Severity.ERROR,
                artifact_path="status.json",
                detail="reducer output does not match persisted status.json",
            )
        )

    return findings
