"""Durable guard: this repo's dogfood corpus is backfilled to the event log.

Locks the acceptance from mission #2816 WP03 / IC-01b. After the runtime-state
corpus cutover, every runtime-bearing dogfood mission under ``kitty-specs/``
carries its frontmatter/``tasks.md``-checkbox runtime state as **seed events**
(an ``InnerStateChanged`` annotation quartet + a seed ``planned -> claimed``
transition) and a ``meta.json`` ``status_phase = "1"`` flip. This guard fails
loudly if a later change empties, staples, or de-seeds the committed corpus —
the exact regression that would make WP04's *unconditional* snapshot readers
reduce to an empty snapshot and go red.

It is **read-only** over the committed corpus, resolved through the production
:func:`locate_project_root` surface (the same resolver the ``migrate
backfill-runtime-state`` CLI walks), so it observes exactly the corpus the
runtime would. The proof surface is the reduced snapshot + the WP01
:func:`verify_backfill` fail-closed parity check — not a synthetic fixture.

Scope notes:

* The actively-running cutover mission itself (:data:`_SELF_MISSION`) is
  intentionally **excluded** from the backfill (WP03 self-interference guard):
  it is event-sourced live via its own transitions and must not be seeded/flipped
  mid-flight. It is skipped here so this guard never depends on the live
  mission's momentary phase.
* Never-claimed / no-runtime missions legitimately reduce to an empty snapshot;
  the guard only asserts on missions that *carry* runtime state.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from specify_cli.core.paths import locate_project_root
from specify_cli.migration.backfill_runtime_state import (
    _claim_anchors,
    _seed_id,
    read_legacy_runtime,
    verify_backfill,
)
from specify_cli.status import emit as _emit
from specify_cli.status.reducer import materialize_snapshot, wp_snapshot_state

pytestmark = [pytest.mark.integration, pytest.mark.slow]

#: Snapshot runtime slots seeded by the backfill. A WP whose reduced snapshot has
#: any of these non-empty is a "runtime-carrying" WP.
_RUNTIME_SLOTS = (
    "shell_pid",
    "shell_pid_created_at",
    "agent",
    "assignee",
    "tracker_refs",
    "subtasks",
    "review",
    "role",
    "agent_profile",
    "agent_profile_version",
    "model",
    "provider",
)

#: The cutover mission itself — event-sourced live, intentionally NOT backfilled
#: (WP03 self-interference guard). Excluded from every assertion below.
_SELF_MISSION = "runtime-state-corpus-cutover-01KXZ0AX"

#: Non-vacuous floor. The corpus carried ~285 runtime-bearing missions at cutover;
#: a stale/emptied/de-seeded corpus (the regression this guards) collapses toward
#: zero. Kept well under the live count so ordinary corpus growth/archival never
#: makes this brittle, while a catastrophic emptying still fails loudly.
_MIN_BACKFILLED_RUNTIME_MISSIONS = 100

def _kitty_specs() -> Path:
    """Resolve the committed ``kitty-specs/`` corpus via the production resolver."""
    root = locate_project_root()
    corpus: Path | None = root / "kitty-specs" if root is not None else None
    if corpus is not None and corpus.is_dir():
        return corpus
    pytest.skip("no kitty-specs corpus resolvable for this project")
    raise AssertionError("unreachable")  # pragma: no cover — pytest.skip is NoReturn


def _status_phase(mission_dir: Path) -> int | None:
    """Return the parsed ``status_phase`` from ``meta.json`` (``None`` if absent)."""
    meta_path = mission_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8")).get("status_phase")
        return int(str(raw).strip())
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _runtime_wps(mission_dir: Path) -> dict[str, Mapping[str, Any]]:
    """Return the reduced WP states that carry at least one runtime slot."""
    snapshot = materialize_snapshot(mission_dir)
    return {
        wp_id: state
        for wp_id, state in snapshot.work_packages.items()
        if any(state.get(slot) not in (None, [], {}, "") for slot in _RUNTIME_SLOTS)
    }


def _backfilled_runtime_missions(corpus: Path) -> list[Path]:
    """All backfilled (``status_phase>=1``), runtime-carrying missions, minus self."""
    out: list[Path] = []
    for mission_dir in sorted(corpus.iterdir()):
        if not mission_dir.is_dir() or mission_dir.name == _SELF_MISSION:
            continue
        if (_status_phase(mission_dir) or 0) >= 1 and _runtime_wps(mission_dir):
            out.append(mission_dir)
    return out


def _eligible_runtime_missions(corpus: Path) -> list[Path]:
    """Every mission with anchored legacy runtime state requiring eviction."""
    eligible: list[Path] = []
    for mission_dir in sorted(corpus.iterdir()):
        if not mission_dir.is_dir() or mission_dir.name == _SELF_MISSION:
            continue
        runtime = read_legacy_runtime(mission_dir)
        anchors = _claim_anchors(mission_dir)
        if any(
            row.has_evictable_state() and wp_id in anchors
            for wp_id, row in runtime.items()
        ):
            eligible.append(mission_dir)
    return eligible


def _first_complete_wp_with_roster(missions: list[Path]) -> tuple[Path, str] | None:
    """Find the first (mission, wp) that is complete under the frontmatter-roster model.

    Complete means: a NON-EMPTY authored ``subtasks:`` frontmatter roster whose
    every id is ``done`` in the reduced snapshot. This is exactly the
    non-vacuous shape ``_infer_subtasks_complete`` treats as complete since
    #2816 IC-10 (roster from frontmatter, completion from the event-sourced
    snapshot).
    """
    from specify_cli.core.subtask_rows import authored_subtask_roster

    for mission_dir in missions:
        for wp_id, state in _runtime_wps(mission_dir).items():
            subtasks = state.get("subtasks") or {}
            done_ids = {tid for tid, status in subtasks.items() if str(status) == "done"}
            roster = authored_subtask_roster(mission_dir, wp_id)
            if roster and all(tid in done_ids for tid in roster):
                return mission_dir, wp_id
    return None


def test_corpus_is_backfilled_non_vacuous() -> None:
    """The committed corpus carries a substantial backfilled runtime population.

    Fails loudly on a stale/emptied/de-seeded corpus — the core WP04 regression
    (an empty snapshot reducing every runtime read to ``None``/``False``).
    """
    missions = _backfilled_runtime_missions(_kitty_specs())
    assert len(missions) >= _MIN_BACKFILLED_RUNTIME_MISSIONS, (
        f"only {len(missions)} backfilled runtime-carrying missions found "
        f"(expected >= {_MIN_BACKFILLED_RUNTIME_MISSIONS}); the dogfood corpus "
        "looks stale/emptied/de-seeded — WP03 backfill (#2816) regressed"
    )


@pytest.mark.timeout(600)
def test_all_eligible_missions_snapshot_non_empty_and_verify_ok() -> None:
    """Every eligible mission is flipped, populated, and verifies cleanly.

    ``verify_backfill`` is the WP01 fail-closed count+value parity check of the
    reduced snapshot against the OLD frontmatter/``tasks.md`` reader, so an ``ok``
    result is the spot-check that the seeded snapshot equals the legacy view
    (SC-001 / NFR-001), not merely that *something* was seeded.
    """
    missions = _eligible_runtime_missions(_kitty_specs())
    assert missions, "no eligible runtime-carrying missions found"

    unflipped = [mission.name for mission in missions if (_status_phase(mission) or 0) < 1]
    assert unflipped == [], f"eligible missions not cut over: {unflipped}"

    for mission_dir in missions:
        runtime_wps = _runtime_wps(mission_dir)
        assert runtime_wps, f"{mission_dir.name}: expected runtime-carrying WPs, snapshot empty"

        # T012.1 — wp_snapshot_state (#2817 accessor) is non-empty for each runtime WP.
        for wp_id in runtime_wps:
            state = wp_snapshot_state(mission_dir, wp_id)
            assert state, f"{mission_dir.name}:{wp_id}: wp_snapshot_state empty after backfill"
            assert any(
                state.get(slot) not in (None, [], {}, "") for slot in _RUNTIME_SLOTS
            ), f"{mission_dir.name}:{wp_id}: no runtime slot populated in snapshot"

        # Fail-closed parity vs the OLD reader (count + value) must be ok.
        result = verify_backfill(mission_dir)
        assert result.ok, (
            f"{mission_dir.name}: verify_backfill NOT ok after backfill: "
            + "; ".join(result.mismatches)
        )


def test_sampled_complete_wp_reads_complete_via_public_gate() -> None:
    """A complete WP reads complete through the public frontmatter-roster gate.

    Proves the committed corpus reads green under the #2816 IC-10 model: the
    subtask roster is the authored ``subtasks:`` frontmatter list and completion
    is resolved solely from the event-sourced snapshot. A WP with a non-empty
    authored roster whose every id is ``done`` in the snapshot must read complete
    through the public :func:`_infer_subtasks_complete` — the ``tasks.md``
    checkbox proxy and the phase-1 authority predicate are both retired.
    """
    missions = _backfilled_runtime_missions(_kitty_specs())
    found = _first_complete_wp_with_roster(missions)
    if found is None:
        pytest.skip("no complete-with-authored-roster WP in the backfilled corpus to sample")
        return
    mission_dir, wp_id = found

    assert _emit._infer_subtasks_complete(mission_dir, wp_id) is True, (
        f"{mission_dir.name}:{wp_id}: public subtask-completeness gate is not True "
        "despite a fully-done authored roster — the seeded corpus reads incomplete"
    )


def test_no_repo_root_event_file() -> None:
    """INV-5 / #2815: the backfill created no event file at the repository root.

    All seed writes resolve through ``canonicalize_feature_dir`` inside the
    library, so no ``status.events.jsonl`` ever lands beside the repo root.
    """
    root = locate_project_root()
    if root is None:
        pytest.skip("no spec-kitty project root resolvable")
    assert not (root / "status.events.jsonl").exists(), (
        "a status.events.jsonl exists at the repository root — a backfill write "
        "escaped canonicalize_feature_dir (INV-5 / #2815 regression)"
    )


def test_corpus_contains_no_authored_derived_resolved_binding_seed_rows() -> None:
    """C-011: historical authored recommendations never masquerade as actuals.

    An earlier in-mission backfill revision emitted deterministic
    ``resolved_binding`` seed rows copied from WP frontmatter. The binding ADR
    forbids that provenance. Closeout removed those rows precisely by their
    namespaced seed ids; this corpus guard prevents any rerun from restoring
    the fabricated actuals while leaving genuine runtime annotations untouched.
    """
    offenders: list[str] = []
    for mission_dir in sorted(_kitty_specs().iterdir()):
        meta_path = mission_dir / "meta.json"
        events_path = mission_dir / "status.events.jsonl"
        if not mission_dir.is_dir() or not meta_path.is_file() or not events_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        mission_id = str(meta.get("mission_id") or "").strip()
        if not mission_id:
            continue
        for line_number, raw_line in enumerate(
            events_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            payload = json.loads(raw_line)
            wp_id = str(payload.get("wp_id") or "").strip()
            if wp_id and payload.get("event_id") == _seed_id(
                mission_id,
                wp_id,
                "resolved_binding",
            ):
                offenders.append(f"{mission_dir.name}:{line_number}:{wp_id}")

    assert offenders == [], (
        "authored-derived resolved_binding seed rows reappeared in the corpus: "
        + ", ".join(offenders[:20])
    )
