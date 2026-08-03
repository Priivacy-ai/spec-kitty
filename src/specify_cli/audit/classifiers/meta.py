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

    # post-#2091 canonical reader: load_meta's on_malformed="raise" (default)
    # wraps BOTH a JSON decode error and a non-object top level as ValueError,
    # FR-007: fail-closed reader routing. Malformed meta surfaces typed
    # MissionMetaReadError instead of raw ValueError. Examine cause to distinguish
    # JSON decode errors from other read failures.
    #
    # Exception-chaining shape (core/paths.py load_meta_fail_closed + WP08
    # review defect #4): MissionMetaReadError.cause is ALWAYS the intermediate
    # ValueError raised by mission_metadata._parse_meta_text -- never the
    # underlying OSError/JSONDecodeError/UnicodeDecodeError directly.
    # _parse_meta_text chains the original decode/read exception as THAT
    # ValueError's own __cause__ (a double-hop), so the real
    # OSError/JSONDecodeError/UnicodeDecodeError lives at
    # ``exc.cause.__cause__``, not ``exc.cause``. Checking ``isinstance(exc.cause,
    # OSError)`` was therefore always False -- a dead branch that misreported an
    # unreadable meta.json as "top-level JSON value must be an object".
    #
    # UnicodeDecodeError (#3163): non-UTF-8 bytes in meta.json raise
    # UnicodeDecodeError, a ValueError subclass but NOT an OSError subclass --
    # it must be checked alongside OSError below, or it falls into the
    # non-object-JSON branch and reports the wrong diagnosis (a decode
    # failure is not "top-level JSON value must be an object").
    from specify_cli.core.paths import load_meta_fail_closed, MissionMetaReadError
    try:
        obj = load_meta_fail_closed(mission_dir)
    except MissionMetaReadError as exc:
        underlying = exc.cause.__cause__ if isinstance(exc.cause, ValueError) else None
        if isinstance(underlying, json.JSONDecodeError):
            detail = f"JSON decode error: {underlying.msg}"
        elif isinstance(underlying, (OSError, UnicodeDecodeError)):
            detail = f"cannot read meta.json: {underlying}"
        else:
            detail = "top-level JSON value must be an object"
        return [
            MissionFinding(
                code="CORRUPT_JSON",
                severity=Severity.ERROR,
                artifact_path="meta.json",
                detail=detail,
            )
        ]

    if obj is None:
        # Unreachable in practice (existence already verified above); keeps
        # mypy happy about load_meta's `dict[str, Any] | None` return type.
        return []

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
