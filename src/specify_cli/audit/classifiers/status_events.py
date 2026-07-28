"""Classifier for status.events.jsonl mission artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..detectors import (
    STATUS_EVENT_ONLY_LEGACY_KEYS,
    detect_forbidden_keys,
    detect_legacy_keys,
)
from ..models import MissionFinding, Severity
from ..shape_registry import check_unknown_keys, status_event_row_artifact_type
from ._details import format_exception_detail
from specify_cli.status.models import decode_actor

# Actor format research (from real event logs and tests):
#
# Modern format examples:
#   "finalize-tasks"      — system actor (kebab word)
#   "migration"           — system actor (single word)
#   "claude"              — agent (single word)
#   "human"               — actor (single word)
#   "user"                — actor (single word, legacy)
#   "claude:opus"         — namespaced (agent:variant)
#   "human:rob"           — namespaced (human:name)
#
# Structured resolved-binding actors are also canonical for lane transitions:
#   {"role": "reviewer", "profile": "reviewer-renata", "tool": "codex", "model": null}
#
# Old/drift format examples:
#   Pure integers, empty strings, malformed structured bindings, or strings
#   with spaces or unusual characters.
#
# We accept:
#   - Any value matching ^[a-z][a-z0-9_:-]*$ (word chars, hyphens, colons, no spaces)
# We flag as drift:
#   - Anything else (e.g. uppercase, spaces, empty string, numeric-only)
_ACTOR_RE = re.compile(r"^[a-z][a-z0-9_:-]*$")


def _is_valid_transition_actor(actor: object) -> bool:
    """Return whether a lane-transition actor matches the canonical contract."""
    if isinstance(actor, str):
        return bool(_ACTOR_RE.match(actor))
    if not isinstance(actor, dict):
        return False
    try:
        decode_actor(actor)
    except ValueError:
        return False
    return True


def classify_status_events_jsonl(
    mission_dir: Path,
) -> tuple[list[MissionFinding], bool]:
    """Classify status.events.jsonl for legacy keys, forbidden keys, and corruption.

    Unlike other classifiers this function returns a 2-tuple so the engine can
    pass ``skip_drift=True`` to the status_json classifier when corruption is
    detected.

    Args:
        mission_dir: Path to the mission directory.

    Returns:
        ``(findings, has_corrupt_jsonl)`` — findings is a list of
        :class:`~specify_cli.audit.models.MissionFinding` objects;
        ``has_corrupt_jsonl`` is True if at least one line failed to parse.
        Never raises — all exceptions become findings.
    """
    path = mission_dir / "status.events.jsonl"
    if not path.exists():
        return [], False

    findings: list[MissionFinding] = []
    has_corrupt_jsonl = False

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            MissionFinding(
                code="CORRUPT_JSONL",
                severity=Severity.ERROR,
                artifact_path="status.events.jsonl",
                detail=f"could not read file: {format_exception_detail(exc)}",
            )
        ], True

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
                    artifact_path="status.events.jsonl",
                    detail=f"line {line_number}: {exc.msg}",
                )
            )
            has_corrupt_jsonl = True
            continue

        if not isinstance(obj, dict):
            findings.append(
                MissionFinding(
                    code="CORRUPT_JSONL",
                    severity=Severity.ERROR,
                    artifact_path="status.events.jsonl",
                    detail=f"line {line_number}: expected JSON object, got {type(obj).__name__}",
                )
            )
            has_corrupt_jsonl = True
            continue

        # Legacy key detection — include work_package_id for event rows
        findings.extend(
            detect_legacy_keys(
                obj,
                "status.events.jsonl",
                extra_keys=STATUS_EVENT_ONLY_LEGACY_KEYS,
            )
        )

        # Forbidden key detection
        findings.extend(detect_forbidden_keys(obj, "status.events.jsonl"))

        # Actor drift applies only to lane transitions.  Other event families
        # share this JSONL file and carry their own structured provenance.
        actor = obj.get("actor")
        is_transition = "from_lane" in obj and "to_lane" in obj
        if actor is not None and is_transition and not _is_valid_transition_actor(actor):
            findings.append(
                MissionFinding(
                    code="ACTOR_DRIFT",
                    severity=Severity.WARNING,
                    artifact_path="status.events.jsonl",
                    detail=f"actor format unexpected: {actor!r}",
                )
            )

        # Unknown key detection
        findings.extend(
            check_unknown_keys(
                status_event_row_artifact_type(obj),
                obj,
                "status.events.jsonl",
            )
        )

    return findings, has_corrupt_jsonl
