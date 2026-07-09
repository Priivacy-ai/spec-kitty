"""Canonical resolution of a mission's merge target branch (FR-012).

Pre-WP07, ``mission.py`` resolved the planning / merge target branch by
inspecting the current checkout via ``_show_branch_context``. When an
operator ran ``spec-kitty agent mission finalize-tasks`` from a
``prep/...`` branch (a common workaround pattern for the legacy
``main``-pin guard), the prep branch name leaked into every WP's
``merge_target_branch`` frontmatter. The prep branch was later deleted
once the human moved on, at which point lane allocation crashed because
its parent ref was gone.

WP07 closes this leak. ``mission create`` already persists the canonical
target in ``meta.json`` (``target_branch`` field) at the moment the
operator was definitively on the right base. We read that value here and
refuse to fall back to ``git branch --show-current``.

Public surface:

* :class:`PlanningBranchResolutionFailed` — structured error raised when
  ``meta.json`` does not carry a usable target_branch. The CLI surface
  catches this and prints an actionable message that mentions the
  ``--target-branch`` override.
* :func:`resolve_planning_branch_from_meta` — pure helper that takes a
  mission meta dict and returns the canonical target branch.
* :func:`load_mission_target_branch` — convenience helper that reads
  ``meta.json`` from disk and resolves.

FR-012 acceptance: every WP frontmatter and ``lanes.json`` carries the
canonical merge target regardless of which branch ``finalize-tasks``
runs from.

Spec reference:
``kitty-specs/mission-coordination-branch-atomic-event-log-01KSPTVW/spec.md``
FR-012, SC-04.
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping

from specify_cli.mission_metadata import load_meta

__all__ = [
    "PlanningBranchResolutionFailed",
    "resolve_planning_branch_from_meta",
    "load_mission_target_branch",
]


class PlanningBranchResolutionFailed(RuntimeError):
    """``meta.json`` is missing both ``target_branch`` and ``merge_target_branch``.

    Stable error code: ``PLANNING_BRANCH_NOT_PERSISTED``.

    Raised when the mission was created before WP03's branch-context
    persistence landed, or when ``meta.json`` was hand-edited in a way
    that dropped the field. Callers can offer the user the
    ``--target-branch`` escape hatch in response.
    """

    error_code: str = "PLANNING_BRANCH_NOT_PERSISTED"

    def __init__(self, message: str) -> None:
        super().__init__(message)


def resolve_planning_branch_from_meta(meta: Mapping[str, object]) -> str:
    """Return the canonical merge target from a meta.json dict.

    Reads ``target_branch`` (canonical key) first; falls back to
    ``merge_target_branch`` (legacy alias seen in older fixtures).
    Whitespace-only values are treated as absent.

    FR-008 / #2139 triage note: this function is a pure ``Mapping`` transform
    (not a ``feature_dir`` reader) with a contract that deliberately diverges
    from ``read_target_branch_from_meta`` on two axes -- the
    ``merge_target_branch`` legacy-alias fallback, and strict
    ``isinstance(raw, str)`` type-checking (a non-string ``target_branch``,
    e.g. ``42``, is treated as absent here, whereas the authority coerces via
    ``str(value)``). It already fail-closes via
    :class:`PlanningBranchResolutionFailed` rather than a silent
    ``"main"``/``""`` default, so it does not exhibit the divergence FR-008
    targets; it is intentionally left as its own contract rather than routed
    through the authority (routing would drop the legacy-alias fallback and
    break the existing type-strict test coverage in
    ``test_mission_finalize_tasks.py``).

    Raises:
        PlanningBranchResolutionFailed: When neither field carries a
            non-empty string. The caller is expected to surface this as
            a CLI error and direct the user to ``--target-branch``.
    """
    raw = meta.get("target_branch")
    if not isinstance(raw, str) or not raw.strip():
        raw = meta.get("merge_target_branch")
    if not isinstance(raw, str) or not raw.strip():
        raise PlanningBranchResolutionFailed(
            "meta.json is missing target_branch / merge_target_branch. "
            "This mission was created before branch context was persisted. "
            "Re-run with --target-branch <ref> to override, or "
            "re-create the mission so meta.json records the canonical target."
        )
    return raw.strip()


def load_mission_target_branch(feature_dir: Path) -> str:
    """Read ``meta.json`` from ``feature_dir`` and return the canonical target.

    The lookup is read-only and tolerant of missing/corrupt files —
    those cases surface as :class:`PlanningBranchResolutionFailed` so
    the CLI emits a single, consistent diagnostic.
    """
    meta_path = feature_dir / "meta.json"
    try:
        data = load_meta(feature_dir, allow_missing=False, on_malformed="raise")
    except FileNotFoundError as exc:
        raise PlanningBranchResolutionFailed(
            f"meta.json not found at {meta_path}. "
            "Re-run with --target-branch <ref> to override."
        ) from exc
    except ValueError as exc:
        raise PlanningBranchResolutionFailed(
            f"meta.json at {meta_path} is unreadable: {exc}. "
            "Re-run with --target-branch <ref> to override."
        ) from exc
    if data is None:
        # Unreachable: allow_missing=False + on_malformed="raise" never
        # returns None. Narrows the type for mypy without an assert.
        raise PlanningBranchResolutionFailed(
            f"meta.json at {meta_path} is not a JSON object."
        )
    return resolve_planning_branch_from_meta(data)
