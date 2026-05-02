"""Shape registry: known top-level keys per artifact type.

Defines ``KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT`` — a mapping from artifact type
name to the set of top-level keys that are expected in that artifact type.

``check_unknown_keys()`` uses this registry to emit ``UNKNOWN_SHAPE`` findings
for any top-level key that is not in the known set, not a legacy key, and not
a forbidden key (those have dedicated finding codes).
"""

from __future__ import annotations

from .detectors import FORBIDDEN_KEYS, LEGACY_KEYS
from .models import MissionFinding, Severity

# ---------------------------------------------------------------------------
# Known key sets per artifact type
# ---------------------------------------------------------------------------

KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT: dict[str, frozenset[str]] = {
    "meta.json": frozenset(
        {
            "mission_id",
            "mission_number",
            "mission_slug",
            "slug",
            "friendly_name",
            "purpose_tldr",
            "purpose_context",
            "mission_type",
            "target_branch",
            "vcs",
            "created_at",
            "source_description",
        }
    ),
    "status.json": frozenset(
        {
            "mission_slug",
            "feature_slug",  # back-compat alias
            "mission_number",
            "mission_type",
            "materialized_at",
            "event_count",
            "last_event_id",
            "work_packages",
            "summary",
            "retrospective",
        }
    ),
    "status_event_row": frozenset(
        {
            "actor",
            "at",
            "event_id",
            "evidence",
            "execution_mode",
            "feature_slug",
            "force",
            "from_lane",
            "reason",
            "review_ref",
            "to_lane",
            "wp_id",
            "mission_id",
            "mission_slug",
            "policy_metadata",
            # skip rows (legacy discriminator keys — present in some old rows):
            "event_type",
            "event_name",
        }
    ),
    "wp_frontmatter": frozenset(
        {
            "work_package_id",
            "title",
            "dependencies",
            "subtasks",
            "execution_mode",
            "owned_files",
            "authoritative_surface",
            "planning_base_branch",
            "merge_target_branch",
            "branch_strategy",
            "agent_profile",
            "role",
            "agent",
            "model",
            "history",
            "requirement_refs",
            # older shapes:
            "id",
            "status",
            "lane",
            "actor",
            "evidence",
            "review_ref",
            "reason",
            "force",
            "depends_on",
            # newer fields (083+):
            "tags",
        }
    ),
    # mission-events.jsonl rows (MissionNextInvoked and similar mission-level events)
    "mission_event_row": frozenset(
        {
            "mission",
            "payload",
            "timestamp",
            "type",
            # event_type-based rows (alternate schema)
            "event_type",
            "at",
            "event_id",
        }
    ),
    # decisions/events.jsonl rows (DecisionPoint* events)
    "decision_event_row": frozenset(
        {
            "at",
            "event_id",
            "event_type",
            "payload",
            "timestamp",
            "type",
        }
    ),
    # handoff/events.jsonl rows (handoff lane-transition-style events)
    "handoff_event_row": frozenset(
        {
            "actor",
            "at",
            "event_id",
            "evidence",
            "execution_mode",
            "feature_slug",
            "force",
            "from_lane",
            "mission_id",
            "mission_slug",
            "policy_metadata",
            "reason",
            "review_ref",
            "to_lane",
            "wp_id",
        }
    ),
}


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------


def check_unknown_keys(
    artifact_type: str,
    obj: dict[str, object],
    artifact_path: str,
) -> list[MissionFinding]:
    """Return ``UNKNOWN_SHAPE`` findings for unrecognised top-level keys.

    A key is considered *unknown* when it is:
    - not in ``KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT[artifact_type]``, AND
    - not in ``LEGACY_KEYS`` (those emit ``LEGACY_KEY`` findings), AND
    - not in ``FORBIDDEN_KEYS`` (those emit ``FORBIDDEN_KEY`` findings).

    If *artifact_type* is not in ``KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT``, the
    function returns an empty list — an unregistered artifact type is not
    itself an error.

    Args:
        artifact_type: One of the keys in ``KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT``
            (e.g. ``"meta.json"``, ``"status_event_row"``).
        obj: Parsed artifact dict whose top-level keys are inspected.
        artifact_path: Relative path to the artifact for finding records.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects
        with code ``"UNKNOWN_SHAPE"`` and severity ``INFO``.
    """
    known = KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT.get(artifact_type)
    if known is None:
        return []

    findings: list[MissionFinding] = []
    for key in obj:
        if key not in known and key not in LEGACY_KEYS and key not in FORBIDDEN_KEYS:
            findings.append(
                MissionFinding(
                    code="UNKNOWN_SHAPE",
                    severity=Severity.INFO,
                    artifact_path=artifact_path,
                    detail=f"unknown key: {key!r} (artifact_type={artifact_type!r})",
                )
            )
    return findings
