"""Bootstrap canonical status state for work packages in a feature.

Scans WP files in a feature directory, checks the canonical event log
for existing state, and emits initial ``planned`` events for any WP
that lacks one.  After seeding, materializes ``status.json`` so the
snapshot is immediately consistent.

This module uses the existing ``emit_status_transition`` pipeline --
it does **not** reimplement event emission or validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from specify_cli.frontmatter import FrontmatterError
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.models import TransitionRequest
from specify_cli.status.reducer import materialize
from specify_cli.status.store import read_events
from specify_cli.status.wp_metadata import read_wp_frontmatter

logger = logging.getLogger(__name__)

# Possible detail values stored in BootstrapResult.wp_details
_INITIALIZED = "initialized"
_ALREADY_EXISTS = "already_exists"
_WOULD_SEED = "would_seed"
_SKIPPED_MALFORMED = "skipped_malformed"


@dataclass
class BootstrapResult:
    """Outcome of a bootstrap operation."""

    total_wps: int = 0
    already_initialized: int = 0
    newly_seeded: int = 0
    skipped: int = 0
    wp_details: dict[str, str] = field(default_factory=dict)


def _collect_wp_ids(tasks_dir: Path, result: BootstrapResult) -> list[str]:
    """Return valid WP IDs discovered in ``tasks_dir`` and record skips."""
    wp_ids: list[str] = []
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        try:
            meta, _body = read_wp_frontmatter(wp_file)
        except (FrontmatterError, ValidationError):
            logger.warning("Skipping %s: malformed frontmatter", wp_file.name)
            result.skipped += 1
            result.wp_details[wp_file.stem] = _SKIPPED_MALFORMED
            continue

        wp_id = meta.work_package_id
        if not wp_id:
            logger.warning(
                "Skipping %s: missing or invalid work_package_id",
                wp_file.name,
            )
            result.skipped += 1
            result.wp_details[wp_file.stem] = _SKIPPED_MALFORMED
            continue

        wp_ids.append(wp_id)
    return wp_ids


def _classify_wp_ids(
    wp_ids: list[str],
    initialized_wp_ids: set[str],
    result: BootstrapResult,
) -> list[str]:
    """Update ``result`` counts/details and return WPs that still need seeding."""
    wps_to_seed: list[str] = []
    for wp_id in wp_ids:
        if wp_id in initialized_wp_ids:
            result.already_initialized += 1
            result.wp_details[wp_id] = _ALREADY_EXISTS
            continue
        wps_to_seed.append(wp_id)
    return wps_to_seed


def bootstrap_canonical_state(
    feature_dir: Path,
    mission_slug: str,
    *,
    dry_run: bool = False,
) -> BootstrapResult:
    """Ensure every WP in a feature has canonical status state.

    Scans ``feature_dir/tasks/`` for ``WP*.md`` files, reads each
    file's frontmatter to extract ``work_package_id``, then checks
    the canonical event log for existing events.  Uninitialized WPs
    receive a ``planned`` event via :func:`emit_status_transition`.

    After all events are emitted (unless *dry_run*), calls
    :func:`materialize` to write a fresh ``status.json``.

    Args:
        feature_dir: Path to the kitty-specs feature directory.
        mission_slug: Feature identifier (e.g. ``"060-feature-name"``).
        dry_run: If ``True``, report what would happen without mutating
            any files.

    Returns:
        A :class:`BootstrapResult` with counts and per-WP detail strings.
    """
    result = BootstrapResult()

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return result

    wp_ids = _collect_wp_ids(tasks_dir, result)
    if not wp_ids:
        return result

    result.total_wps = len(wp_ids)

    # Read existing events and build set of WP IDs that already have state
    existing_events = read_events(feature_dir)
    initialized_wp_ids: set[str] = {e.wp_id for e in existing_events}

    wps_to_seed = _classify_wp_ids(wp_ids, initialized_wp_ids, result)

    if dry_run:
        for wp_id in wps_to_seed:
            result.wp_details[wp_id] = _WOULD_SEED
        result.newly_seeded = len(wps_to_seed)
        return result

    # Emit planned events for uninitialized WPs
    for wp_id in wps_to_seed:
        emit_status_transition(
            TransitionRequest(
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id=wp_id,
                to_lane="planned",
                actor="finalize-tasks",
                force=True,
                reason="canonical bootstrap",
            )
        )
        result.newly_seeded += 1
        result.wp_details[wp_id] = _INITIALIZED

    # Materialize snapshot after all events are emitted.
    # emit_status_transition already calls materialize per event, but
    # we call it once more to guarantee the final snapshot is coherent
    # across all newly seeded WPs.
    if wps_to_seed:
        materialize(feature_dir)

    return result
