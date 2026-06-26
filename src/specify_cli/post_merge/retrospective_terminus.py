"""Post-merge retrospective postcondition check (WP07 — FR-007, Issue #1888).

Ensures the retrospective learning-capture fires on the ``spec-kitty merge``
completion path, not only on the ``spec-kitty next`` terminal-decision branch.

Public API:
    run_retrospective_postcondition(mission_slug, repo_root) -> None

Design invariants:
    * Fail-open: retrospective failure MUST NOT abort the merge.
    * Idempotent: if ``retrospective.yaml`` already exists the function returns
      immediately without emitting any event.
    * On failure, a ``retrospective.capture_failed`` event is appended to
      ``kitty-specs/<slug>/status.events.jsonl`` so the gap is auditable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from specify_cli.core.constants import RETROSPECTIVE_FILENAME

logger = logging.getLogger(__name__)

FailureCategory = Literal[
    "missing_artifacts",
    "generator_exception",
    "schema_validation_error",
    "io_error",
    "other",
]

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_retrospective_postcondition(
    *,
    mission_slug: str,
    repo_root: Path,
) -> None:
    """Run the post-merge retrospective postcondition check.

    Checks whether ``kitty-specs/<slug>/retrospective.yaml`` exists after a
    successful merge.  If it does not, invokes
    ``_run_retrospective_learning_capture`` from the runtime bridge to attempt
    best-effort capture (fail-open: failure is recorded but does NOT abort).

    This function is the canonical call-site for FR-007.  It consolidates the
    previously dead ``run_terminus`` path with the live runtime-bridge capture
    path so that merge completion always triggers the learning loop.

    Args:
        mission_slug: The mission slug (e.g. ``"017-my-feature"``).
        repo_root: Absolute path to the repository root (primary checkout).

    Note:
        ``run_terminus`` (the old dead-code stub in the lifecycle module) is
        superseded by this function.  Do not add new callers of ``run_terminus``.
    """
    # Late import to keep module-level import graph clean and to avoid heavy
    # optional deps being pulled in unconditionally at CLI startup.
    # FR-001/003 (#2119): route through the single durable-home authority so the
    # post-merge terminus reads/writes the retrospective in the PRIMARY home for
    # every topology — never the materialized ``-coord`` husk (the #1771 leak).
    from specify_cli.retrospective.writer import resolve_retrospective_home  # noqa: PLC0415

    feature_dir = resolve_retrospective_home(repo_root, mission_slug)

    # T031 — Merge-completion postcondition: check for retrospective.yaml.
    retro_path = feature_dir / RETROSPECTIVE_FILENAME
    if retro_path.exists():
        logger.debug(
            "retrospective.yaml already exists for mission %s — postcondition satisfied (no-op)",
            mission_slug,
        )
        return

    # Resolve mission_id (T034 — use canonical path from feature_dir, not a
    # stale NNN-slug-based path).  Legacy missions pre-083 may lack a ULID
    # mission_id; fall back to empty string so the event is still valid.
    mission_id = _resolve_mission_id(feature_dir)

    # T032 — Call the live capture path (not a duplicate implementation).
    try:
        _invoke_capture(
            mission_id=mission_id,
            mission_slug=mission_slug,
            feature_dir=feature_dir,
            repo_root=repo_root,
        )
    except Exception as exc:  # noqa: BLE001 — fail-open: record but don't abort
        logger.warning(
            "post-merge retrospective capture failed for mission %s: %s",
            mission_slug,
            exc,
        )
        # T033 — Emit capture_failed event so the gap is auditable.
        _emit_capture_failed(
            mission_id=mission_id,
            mission_slug=mission_slug,
            repo_root=repo_root,
            exc=exc,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_mission_id(feature_dir: Path) -> str:
    """Return the ULID mission_id from meta.json, or empty string for legacy missions."""
    # T034 — use the canonical feature_dir path (already resolved by the caller);
    # never reconstruct a path with a NNN- numeric prefix.
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        return ""
    try:
        import json  # noqa: PLC0415

        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return str(data.get("mission_id") or "")
    except Exception:  # noqa: BLE001
        return ""


def _invoke_capture(
    *,
    mission_id: str,
    mission_slug: str,
    feature_dir: Path,
    repo_root: Path,
) -> None:
    """Delegate to the runtime-bridge capture implementation (T032).

    Reuses ``_run_retrospective_learning_capture`` from
    ``runtime.next.runtime_bridge`` — does NOT duplicate the implementation.
    ``block_on_failure=False`` keeps the merge fail-open.
    """
    from runtime.next.runtime_bridge import (  # noqa: PLC0415
        _run_retrospective_learning_capture,
    )

    _run_retrospective_learning_capture(
        mission_id=mission_id,
        mission_slug=mission_slug,
        feature_dir=feature_dir,
        repo_root=repo_root,
        block_on_failure=False,
    )


def _emit_capture_failed(
    *,
    mission_id: str,
    mission_slug: str,
    repo_root: Path,
    exc: Exception,
) -> None:
    """Emit a ``retrospective.capture_failed`` event (T033).

    Appends the event to ``kitty-specs/<slug>/status.events.jsonl`` so the
    gap is auditable.  This helper is intentionally best-effort: if the emit
    itself fails we log and swallow so the merge is never aborted.
    """
    try:
        from specify_cli.retrospective.lifecycle_events import (  # noqa: PLC0415
            Actor,
            emit_capture_failed,
        )

        _classify = _classify_exc(exc)
        system_actor = Actor(kind="runtime", id="spec-kitty-merge-postcondition")

        emit_capture_failed(
            mission_id=mission_id,
            mission_slug=mission_slug,
            repo_root=repo_root,
            failure_category=_classify,
            failure_message=f"post-merge retrospective capture: {exc!s}",
            remediation_hint=(
                "Run `spec-kitty agent retrospect synthesize --mission <slug>` "
                "to retry retrospective capture after merge."
            ),
            policy_source={"source": "merge_postcondition"},
            attempted_provenance_kind="runtime_post_completion",
            missing_artifacts=None,
            actor=system_actor,
            execution_mode="main",
        )
    except Exception as emit_exc:  # noqa: BLE001
        logger.warning(
            "could not emit capture_failed event for mission %s: %s",
            mission_slug,
            emit_exc,
        )


def _classify_exc(exc: Exception) -> FailureCategory:
    """Map an exception to a failure_category string."""
    if isinstance(exc, (FileNotFoundError, IsADirectoryError)):
        return "missing_artifacts"
    if isinstance(exc, (OSError, PermissionError)):
        return "io_error"
    return "generator_exception"
