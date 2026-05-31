"""Key-based detectors and JSONL corruption detector for the audit engine.

This module provides three low-level detector functions used by classifiers
and the audit engine:

- ``detect_legacy_keys`` — finds keys in ``LEGACY_KEYS`` (and an optional
  extra set) that indicate pre-migration artifact shapes.
- ``detect_forbidden_keys`` — finds keys in ``FORBIDDEN_KEYS`` that must
  never appear in canonical artifacts.
- ``detect_corrupt_jsonl`` — reads a JSONL file and returns a finding for
  the first line that cannot be parsed.

Key constants are exposed as module-level ``frozenset`` objects so callers
and the shape registry can import them without re-defining them.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import MissionFinding, Severity

# ---------------------------------------------------------------------------
# Key sets (immutable)
# ---------------------------------------------------------------------------

# Keys that are legacy in ALL artifact types (meta.json, WP frontmatter, event rows).
# Presence of any of these keys in a parsed dict indicates a pre-migration shape.
LEGACY_KEYS: frozenset[str] = frozenset(
    {
        "feature_slug",
        "feature_number",
        "mission_key",
        "legacy_aggregate_id",
    }
)

# Keys that are legacy ONLY in status event rows (FR-012).
#
# ``work_package_id`` IS the canonical key in WP frontmatter (tasks/WP*.md),
# so it must NOT be flagged when processing frontmatter — only in event rows.
# Callers processing event rows must pass
# ``extra_keys=STATUS_EVENT_ONLY_LEGACY_KEYS`` to ``detect_legacy_keys()``.
STATUS_EVENT_ONLY_LEGACY_KEYS: frozenset[str] = frozenset(
    {
        "work_package_id",
    }
)

# Keys that must never appear in canonical **status-transition** rows.
# Their presence in a status-transition row indicates it was written by a
# pre-migration producer that used a ``type`` / ``name`` discriminator instead
# of canonical ``to_lane`` / ``from_lane``.
#
# Row-family scoping (mission ``unblock-sync-identity-boundary-canary``, WP01):
# ``status.events.jsonl`` carries two distinct row families — status-transition
# rows and mission-lifecycle rows (``aggregate_type == "Mission"`` plus an
# ``event_type`` discriminator). The FORBIDDEN_KEYS rule applies only to the
# non-lifecycle family. ``detect_forbidden_keys`` consults
# :func:`specify_cli.audit.shape_registry.is_mission_lifecycle_row` to skip
# legitimate lifecycle rows while still flagging malformed transition rows
# that carry ``event_type`` / ``event_name``.
FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "event_type",
        "event_name",
    }
)


# ---------------------------------------------------------------------------
# Detector functions
# ---------------------------------------------------------------------------


def detect_legacy_keys(
    obj: dict[str, object],
    artifact_path: str,
    *,
    extra_keys: frozenset[str] = frozenset(),
) -> list[MissionFinding]:
    """Return one ``LEGACY_KEY`` finding for each legacy key present in *obj*.

    Args:
        obj: Parsed artifact dict (e.g. ``meta.json`` contents).
        artifact_path: Relative path to the artifact, used as ``artifact_path``
            in findings (forward-slash, relative to mission directory).
        extra_keys: Additional keys to treat as legacy.  Pass
            ``STATUS_EVENT_ONLY_LEGACY_KEYS`` when processing status event rows
            so that ``work_package_id`` is also flagged.  Omit (or pass an
            empty ``frozenset``) for ``meta.json`` and WP frontmatter.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects,
        one per matched key.  Empty list when none are found.
    """
    combined = LEGACY_KEYS | extra_keys
    findings: list[MissionFinding] = []
    for key in obj:
        if key in combined:
            findings.append(
                MissionFinding(
                    code="LEGACY_KEY",
                    severity=Severity.WARNING,
                    artifact_path=artifact_path,
                    detail=f"legacy key: {key!r}",
                )
            )
    return findings


def detect_forbidden_keys(
    obj: dict[str, object],
    artifact_path: str,
) -> list[MissionFinding]:
    """Return one ``FORBIDDEN_KEY`` finding for each forbidden key in *obj*.

    Row-family scoping: rows classified as mission-lifecycle rows or
    DecisionPoint event envelopes by ``shape_registry`` are skipped entirely
    — they legitimately carry ``event_type``. All other rows are checked
    against :data:`FORBIDDEN_KEYS`, so a malformed status-transition row
    that carries ``event_type`` without an accepted event-row shape is still
    flagged.

    Args:
        obj: Parsed artifact dict.
        artifact_path: Relative path to the artifact.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Empty list when none are found or when *obj* is an accepted event row.
    """
    # Local import to avoid a module-load cycle with ``shape_registry``,
    # which imports ``FORBIDDEN_KEYS`` / ``LEGACY_KEYS`` from this module.
    from .shape_registry import is_decisionpoint_status_event_row, is_mission_lifecycle_row

    if is_mission_lifecycle_row(obj) or is_decisionpoint_status_event_row(obj):
        return []

    findings: list[MissionFinding] = []
    for key in obj:
        if key in FORBIDDEN_KEYS:
            findings.append(
                MissionFinding(
                    code="FORBIDDEN_KEY",
                    severity=Severity.WARNING,
                    artifact_path=artifact_path,
                    detail=f"forbidden key: {key!r}",
                )
            )
    return findings


def detect_corrupt_jsonl(path: Path, artifact_path: str) -> list[MissionFinding]:
    """Return a ``CORRUPT_JSONL`` finding for the first unparseable line.

    The function stops at the **first** corrupt line to avoid producing O(n)
    findings on a badly damaged file.  Blank lines (and lines containing only
    whitespace) are silently skipped.  If *path* does not exist the function
    returns an empty list.

    Args:
        path: Absolute (or resolvable) path to the ``.jsonl`` file.
        artifact_path: Relative path used as ``artifact_path`` in findings.

    Returns:
        A list containing at most one :class:`~specify_cli.audit.models.MissionFinding`.
        The ``detail`` field includes the 1-based line number and the
        :class:`json.JSONDecodeError` message, but not the raw corrupt content.
    """
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue  # blank line — skip silently
            try:
                json.loads(stripped)
            except json.JSONDecodeError as exc:
                return [
                    MissionFinding(
                        code="CORRUPT_JSONL",
                        severity=Severity.ERROR,
                        artifact_path=artifact_path,
                        detail=f"line {line_number}: {exc.msg}",
                    )
                ]

    return []
