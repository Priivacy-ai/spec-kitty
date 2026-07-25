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

WP10 re-key (FR-010 / C-003 / NFR-006 / IC-09): eligibility
(:func:`_eligible_runtime_missions`) used to key on the frontmatter
``has_evictable_state()`` signal. WP04/WP05 retired frontmatter runtime
authoring, so that signal goes permanently empty for every mission born after
the retirement — a future regression in the WP09 birth-cutover seam would
leave such a mission un-flipped/empty and this guard would never see it
(a vacuous pass). Eligibility is now keyed on independent evidence read
directly from ``status.events.jsonl`` (see
:func:`_mission_carries_event_log_runtime`) — never on the retired
frontmatter signal, and never on ``status_phase`` itself (circular: that is
exactly the field this guard verifies was flipped). See
``test_reked_lock_reds_on_born_un_reconciled_mission`` for the non-vacuity
proof.
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
from specify_cli.status import (
    Lane,
    StatusEvent,
    StoreError,
    append_events_atomic_verified,
    build_claim_policy_metadata,
    read_event_stream,
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


def _mission_carries_event_log_runtime(mission_dir: Path) -> bool:
    """True iff *mission_dir*'s event log records independent runtime evidence.

    WP10 re-key (FR-010 / IC-09): evidence comes ONLY from
    ``status.events.jsonl`` — never from
    :meth:`~specify_cli.migration.backfill_runtime_state.LegacyWPRuntime.has_evictable_state`
    (frontmatter, retired by WP05/FR-008: every mission born after authoring
    retirement carries NO frontmatter runtime at all, so keying eligibility
    there makes the guard permanently blind to every future mission — a
    vacuous pass) and never from ``status_phase`` (circular: that field is
    exactly what this guard verifies was flipped, so gating eligibility on it
    could never catch an un-flipped regression).

    "Carries runtime" means the log holds, for at least one WP, either:

    * an :class:`~specify_cli.status.InnerStateChanged` annotation — by
      construction (``_append_annotation`` / the public ``annotate`` /
      ``emit_inner_state_changed`` seam) an annotation is only ever appended
      with a non-empty runtime delta, so its mere presence IS runtime
      evidence; or
    * a lane transition whose ``policy_metadata`` is non-empty — the only
      transitions that carry ``policy_metadata`` are real ``planned ->
      claimed`` claims (:func:`~specify_cli.status.build_claim_policy_metadata`,
      live-emitted or backfill-seeded — both shapes are byte-identical on the
      wire).

    Deliberately narrower than "any transition at all": every WP receives a
    ``genesis -> planned`` / self-transition ``planned -> planned`` *canonical
    bootstrap* identity anchor at ``finalize-tasks`` time (confirmed
    empirically across the committed corpus) that carries no runtime signal
    whatsoever. A never-claimed WP legitimately reduces to an empty snapshot
    (module docstring); a predicate keyed on "any event" would wrongly flag
    those bootstrap-only missions as eligible and then fail the
    non-empty-snapshot assertion on perfectly healthy, merely-unclaimed corpus
    entries.
    """
    events_path = mission_dir / "status.events.jsonl"
    if not events_path.is_file():
        return False
    try:
        stream = read_event_stream(mission_dir)
    except StoreError:
        return False
    if stream.annotations:
        return True
    return any(bool(event.policy_metadata) for event in stream.transitions)


def _eligible_runtime_missions(corpus: Path) -> list[Path]:
    """Every mission whose event log carries independent runtime evidence.

    Re-keyed (WP10 / FR-010 / IC-09) off
    :func:`_mission_carries_event_log_runtime` — see that function's
    docstring for the hard-forbidden predicates this deliberately never
    reads.
    """
    eligible: list[Path] = []
    for mission_dir in sorted(corpus.iterdir()):
        if not mission_dir.is_dir() or mission_dir.name == _SELF_MISSION:
            continue
        if _mission_carries_event_log_runtime(mission_dir):
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


def _assert_birth_invariant_holds(corpus: Path) -> None:
    """FR-010 / C-003: every eligible mission is flipped, populated, verifies.

    Extracted so the SAME assertion runs both over the real committed corpus
    (below) and over a synthetic drifted fixture
    (``test_reked_lock_reds_on_born_un_reconciled_mission``), proving the
    re-keyed lock genuinely REDS on drift rather than only ever observing an
    already-healthy corpus.

    ``verify_backfill`` is the WP01 fail-closed count+value parity check of the
    reduced snapshot against the OLD frontmatter/``tasks.md`` reader, so an ``ok``
    result is the spot-check that the seeded snapshot equals the legacy view
    (SC-001 / NFR-001), not merely that *something* was seeded.
    """
    missions = _eligible_runtime_missions(corpus)
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


@pytest.mark.timeout(600)
def test_all_eligible_missions_snapshot_non_empty_and_verify_ok() -> None:
    """Every eligible mission (real committed corpus) is flipped and populated.

    See :func:`_assert_birth_invariant_holds` for the assertion body shared
    with the anti-vacuity fixture test.
    """
    _assert_birth_invariant_holds(_kitty_specs())


def test_reked_lock_reds_on_born_un_reconciled_mission(tmp_path: Path) -> None:
    """T049 anti-vacuity proof (FR-010 / IC-09) — the whole point of WP10.

    Builds a synthetic mission that is authoring-retired (no frontmatter
    runtime state anywhere on disk — the FR-008/WP05 shape) but whose event
    log carries a genuine LIVE claim (real ``policy_metadata``, exactly the
    shape a born mission gets at the WP09 birth-cutover seam) while
    ``status_phase`` was never flipped — a drifted, un-birth-stamped mission.

    Two things must both hold, or the re-key is wrong:

    1. The HARD-FORBIDDEN frontmatter predicate (``has_evictable_state()``)
       does NOT see this mission as eligible at all — proving that keying
       eligibility there (the pre-WP10 shape) would make the guard silently
       skip it (a vacuous pass), never asserting anything and never redding.
    2. The re-keyed :func:`_eligible_runtime_missions` DOES see it, and
       :func:`_assert_birth_invariant_holds` REDS on it (the un-flipped
       ``status_phase`` assertion fires) — proving the re-keyed lock is a
       genuine, non-vacuous guard against exactly this future regression.
    """
    corpus = tmp_path / "kitty-specs"
    corpus.mkdir()
    mission_dir = corpus / "drifted-un-birth-stamped-01KZQXTR"
    mission_dir.mkdir()
    tasks = mission_dir / "tasks"
    tasks.mkdir()

    mission_id = "01KZQXTRH8T2X6R4N9YV3D5C7B"
    # No status_phase key at all in meta.json — genuinely un-flipped/un-birthed.
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_slug": mission_dir.name,
                "mission_type": "software-dev",
            }
        ),
        encoding="utf-8",
    )
    # Authoring-retired WP frontmatter (FR-008/WP05 shape): no shell_pid /
    # agent / assignee / tracker_refs anywhere — zero evictable state on disk.
    (tasks / "WP01-demo.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Drifted Demo\nexecution_mode: code_change\n---\n\n# WP01\n",
        encoding="utf-8",
    )
    # No tasks.md checkbox rows either — post-retirement, subtask completion
    # is entirely event-sourced (the checkbox proxy is retired, not merely
    # frontmatter). A checkbox row (even unchecked) would make the legacy
    # reader's ``subtasks`` dict non-empty and defeat the anti-vacuity proof
    # below (Sonar-safe finding: verified empirically against the real reader).
    (mission_dir / "tasks.md").write_text("# Tasks\n\n## WP01 Demo\n\n", encoding="utf-8")
    # A genuine LIVE claim — the exact wire shape a real born mission carries
    # (real policy_metadata, not a backfill seed).
    claim = StatusEvent(
        event_id="01DRIFTDRIFTDRIFTDRIFTDRIF",
        mission_slug=mission_dir.name,
        mission_id=mission_id,
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.CLAIMED,
        at="2026-07-25T09:00:00+00:00",
        actor="claude:sonnet:pedro",
        force=False,
        execution_mode="worktree",
        policy_metadata=build_claim_policy_metadata(
            shell_pid=55221,
            shell_pid_created_at="2026-07-25T08:59:00+00:00",
            agent="claude:sonnet:pedro",
        ),
    )
    append_events_atomic_verified(mission_dir, [claim])

    # (1) Anti-vacuity call-out: the HARD-FORBIDDEN predicate is blind here.
    legacy = read_legacy_runtime(mission_dir)
    anchors = _claim_anchors(mission_dir)
    forbidden_predicate_would_see_it = any(
        row.has_evictable_state() and wp_id in anchors for wp_id, row in legacy.items()
    )
    assert forbidden_predicate_would_see_it is False, (
        "fixture must be invisible to the retired has_evictable_state() "
        "predicate, or this is not proving the vacuity WP10 closes"
    )

    # (2) The re-keyed predicate sees it...
    assert mission_dir in _eligible_runtime_missions(corpus)

    # ...and the lock genuinely REDS on it (non-vacuous).
    with pytest.raises(AssertionError, match="not cut over"):
        _assert_birth_invariant_holds(corpus)


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
