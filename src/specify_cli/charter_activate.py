"""``spec-kitty charter activate`` — in-flight warning on action_sequence change.

FR-008: When a charter override is activated that removes a step from the
current action_sequence, ``spec-kitty charter activate`` emits a structured
warning for each in-flight mission that has a WP currently in the lane
corresponding to the removed step, before completing activation.

The warning is **non-blocking**: activation completes after warning emission.

FR-014: Activation now writes to ``config.yaml`` via ``CharterPackManager``
instead of writing ``.kittify/overrides/`` files that nothing reads.

Layer note
----------
This module lives in ``specify_cli`` (not ``charter``); it is permitted to
import both ``charter.*`` and ``specify_cli.status.*``.  The layer rule
(kernel <- doctrine <- charter <- specify_cli) is not violated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

__all__ = [
    "AffectedMission",
    "StepRemovalWarning",
    "find_removed_steps",
    "scan_inflight_missions",
    "emit_step_removal_warnings",
    "activate_mission_type_override",
]

# ---------------------------------------------------------------------------
# Lanes that correspond to "in-flight" status (non-terminal, active work)
# ---------------------------------------------------------------------------

#: Lanes that count as "in-flight" for the purpose of step-removal warnings.
_INFLIGHT_LANES: frozenset[str] = frozenset(
    {
        "in_progress",
        "for_review",
        "in_review",
        "claimed",
    }
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AffectedMission:
    """A single WP in a mission that is in-flight for a removed step."""

    mission_slug: str
    wp_id: str
    current_lane: str


@dataclass
class StepRemovalWarning:
    """Warning for a single removed step with the set of affected missions."""

    removed_step_id: str
    affected_missions: list[AffectedMission] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core logic — T088
# ---------------------------------------------------------------------------


def find_removed_steps(
    current_sequence: list[str],
    incoming_sequence: list[str],
) -> list[str]:
    """Return step IDs that are in current but not in incoming.

    Parameters
    ----------
    current_sequence:
        The active action sequence before the override is applied.
    incoming_sequence:
        The action sequence being activated (the override).

    Returns
    -------
    list[str]
        Ordered list of removed step IDs (preserves order from current_sequence).
    """
    incoming_set = set(incoming_sequence)
    return [step for step in current_sequence if step not in incoming_set]


# ---------------------------------------------------------------------------
# In-flight mission scanner — T089
# ---------------------------------------------------------------------------


def scan_inflight_missions(
    removed_steps: list[str],
    kitty_specs_dir: Path,
) -> list[StepRemovalWarning]:
    """Scan all missions for WPs in-flight for the removed steps.

    For each removed step ID, inspect every mission in ``kitty_specs_dir``
    for WPs in a non-terminal (in-flight) lane.

    The step→lane mapping uses a simplified heuristic: any WP in an
    in-flight lane (``in_progress``, ``for_review``, ``in_review``,
    ``claimed``) is considered potentially affected by any step removal.
    This is conservative and keeps the implementation free of per-step
    lane-to-step reverse mapping (which would require knowing the mission's
    current position in the action sequence at runtime, a circular
    dependency).

    Parameters
    ----------
    removed_steps:
        Step IDs removed by the incoming override.
    kitty_specs_dir:
        The ``kitty-specs/`` directory in the repository root.

    Returns
    -------
    list[StepRemovalWarning]
        One entry per removed step.  ``affected_missions`` is empty when
        no in-flight WPs are found for that step.
    """
    if not removed_steps:
        return []

    from specify_cli.status.store import read_events  # noqa: PLC0415 — lazy; avoids heavy import
    from specify_cli.status.reducer import reduce  # noqa: PLC0415

    # Collect all in-flight WPs across all missions once, then map them to
    # each removed step (conservative: all removed steps get the same set).
    all_inflight: list[AffectedMission] = []

    if kitty_specs_dir.is_dir():
        for mission_dir in sorted(kitty_specs_dir.iterdir()):
            if not mission_dir.is_dir():
                continue

            events_file = mission_dir / "status.events.jsonl"
            if not events_file.exists():
                continue

            # Determine mission slug from meta.json (prefer) or directory name.
            mission_slug = _read_mission_slug(mission_dir)

            try:
                events = read_events(mission_dir)
            except Exception:  # noqa: BLE001, S112 — best-effort scan; skip corrupt files
                continue

            if not events:
                continue

            snapshot = reduce(events)

            for wp_id, wp_state in snapshot.work_packages.items():
                lane = wp_state.get("lane", "")
                if lane in _INFLIGHT_LANES:
                    all_inflight.append(
                        AffectedMission(
                            mission_slug=mission_slug,
                            wp_id=wp_id,
                            current_lane=lane,
                        )
                    )

    # Build one StepRemovalWarning per removed step, sharing the inflight list.
    warnings: list[StepRemovalWarning] = []
    for step_id in removed_steps:
        warnings.append(
            StepRemovalWarning(
                removed_step_id=step_id,
                affected_missions=list(all_inflight),  # copy per step
            )
        )

    return warnings


def _read_mission_slug(mission_dir: Path) -> str:
    """Extract mission_slug from meta.json, falling back to directory name."""
    meta_path = mission_dir / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            slug = meta.get("mission_slug") or meta.get("feature_slug")
            if slug:
                return str(slug)
        except Exception:  # noqa: BLE001 — best-effort
            pass
    return mission_dir.name


# ---------------------------------------------------------------------------
# Warning emitter — T090
# ---------------------------------------------------------------------------


def emit_step_removal_warnings(
    warnings: list[StepRemovalWarning],
    console: Console,
) -> None:
    """Print structured warnings to *console* for each removed step.

    Produces output matching the format documented in FR-008:

    .. code-block:: text

        ⚠ Step 'review' removed by mission-type override.
          Affected missions:
          - 083-my-feature (WP03, currently in lane 'in_review')

    Only emits output when ``warnings`` contains at least one entry with
    at least one affected mission.  Silent when all steps have no affected
    missions.

    Parameters
    ----------
    warnings:
        Output of :func:`scan_inflight_missions`.
    console:
        Rich console to write warnings to.
    """
    for warning in warnings:
        if not warning.affected_missions:
            continue
        console.print(
            f"[yellow]⚠ Step '{warning.removed_step_id}' removed by mission-type override.[/yellow]"
        )
        console.print("  Affected missions:")
        for mission in warning.affected_missions:
            console.print(
                f"  - {mission.mission_slug} "
                f"({mission.wp_id}, currently in lane '{mission.current_lane}')"
            )


# ---------------------------------------------------------------------------
# Activation via CharterPackManager — FR-014
# ---------------------------------------------------------------------------


def activate_mission_type_override(
    mission_type_id: str,
    incoming_sequence: list[str],
    repo_root: Path,
    console: Console,
) -> None:
    """Activate a mission-type override by writing to config.yaml (FR-014).

    Implements the full FR-008 contract:

    1. Resolve the current active action sequence for *mission_type_id*.
    2. Compute removed steps (present in current, absent in incoming).
    3. Scan in-flight missions; emit structured warnings for each removed
       step that has affected WPs — **before** completing activation.
    4. Write the mission-type activation to ``.kittify/config.yaml`` via
       ``CharterPackManager`` (FR-014: closes the reader gap).
    5. Print ``Activation complete.``

    The warning is non-blocking: activation always completes.

    Parameters
    ----------
    mission_type_id:
        The mission type to activate (e.g. ``"software-dev"``).
    incoming_sequence:
        The new action_sequence being activated.
    repo_root:
        Repository root (contains ``kitty-specs/`` and ``.kittify/``).
    console:
        Rich console for warning and status output.

    Raises
    ------
    ValueError
        When ``incoming_sequence`` is empty or contains duplicates.
    """
    if not incoming_sequence:
        raise ValueError("incoming_sequence must be non-empty.")
    if len(incoming_sequence) != len(set(incoming_sequence)):
        raise ValueError("incoming_sequence must contain unique step IDs.")

    # --- T088: compute current sequence and removed steps -------------------
    try:
        from charter.mission_type_profiles import resolve_action_sequence  # noqa: PLC0415
        current_sequence = resolve_action_sequence(mission_type_id, repo_root)
    except Exception:  # noqa: BLE001 — graceful fallback when type not yet activated
        current_sequence = []

    removed = find_removed_steps(current_sequence, incoming_sequence)

    # --- T089 + T090: scan in-flight missions and emit warnings -------------
    if removed:
        kitty_specs_dir = repo_root / "kitty-specs"
        step_warnings = scan_inflight_missions(removed, kitty_specs_dir)
        emit_step_removal_warnings(step_warnings, console)

    # --- FR-014: write to config.yaml via CharterPackManager ----------------
    from charter.pack_manager import CharterPackManager  # noqa: PLC0415
    from charter.invocation_context import ProjectContext  # noqa: PLC0415

    ctx = ProjectContext.from_repo(repo_root)
    CharterPackManager().activate(ctx, "mission-type", mission_type_id, cascade=False)

    console.print("[green]Activation complete.[/green]")
