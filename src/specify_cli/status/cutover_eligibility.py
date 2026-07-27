"""Single-authority "cut over" eligibility + verdict predicate.

Extracted (WP03 of mission runtime-state-birth-cutover-all-paths, FR-002 /
FR-003 / FR-009 / NFR-002 / NFR-003) from
``tests/specify_cli/migration/test_dogfood_corpus_backfilled.py`` — a PURE
MOVE, behavior-preserving. Two independent consumers import from here and
must never fork their own copy (anti-whack-a-field):

* the dogfood corpus lock
  (``tests/specify_cli/migration/test_dogfood_corpus_backfilled.py``), which
  asserts the *committed* corpus is fully cut over; and
* the diff-scoped pre-merge guard
  (``src/specify_cli/cli/commands/cutover_guard.py``), which decides, for
  each mission touched by a PR diff, whether it is cut over.

Definition (data-model.md "Cut Over" State): a mission is cut over iff ALL
hold —

1. ``meta.json.status_phase == "1"`` (present, not ``null``, key not absent);
2. the mission carries **event-log runtime evidence**
   (:func:`mission_carries_event_log_runtime` — read independently of
   frontmatter and independently of ``status_phase``);
3. the reduced snapshot is non-empty for every WP the evidence identifies as
   runtime-carrying; and
4. :func:`~specify_cli.migration.backfill_runtime_state.verify_backfill` does
   not report a mismatch — **necessary-not-sufficient**: for a natively-born
   mission it is vacuously ``ok`` with ``wp_count=0``, so it can never be the
   *sole* signal (the R2 vacuous-green trap).

A mission that never carries event-log runtime evidence at all (never
claimed) is **not** subject to this invariant — it legitimately reduces to an
empty snapshot and :func:`is_cut_over` reports it cut-over (nothing to
enforce). A mission WITH evidence but ``status_phase != "1"`` is un-cut-over
and MUST be caught by both consumers.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specify_cli.status.reducer import materialize_snapshot, wp_snapshot_state
from specify_cli.status.store import StoreError, read_event_stream

#: Snapshot runtime slots seeded by the backfill. A WP whose reduced snapshot has
#: any of these non-empty is a "runtime-carrying" WP.
RUNTIME_SLOTS: tuple[str, ...] = (
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


def status_phase(mission_dir: Path) -> int | None:
    """Return the parsed ``status_phase`` from ``meta.json`` (``None`` if absent)."""
    meta_path = mission_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8")).get("status_phase")
        return int(str(raw).strip())
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def read_mission_id(mission_dir: Path) -> str | None:
    """Return the ``mission_id`` from ``meta.json`` (``None`` if absent/unreadable)."""
    meta_path = mission_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8")).get("mission_id")
    except (TypeError, json.JSONDecodeError):
        return None
    mission_id = str(raw or "").strip()
    return mission_id or None


def runtime_wps(mission_dir: Path) -> dict[str, Mapping[str, Any]]:
    """Return the reduced WP states that carry at least one runtime slot."""
    snapshot = materialize_snapshot(mission_dir)
    return {
        wp_id: state
        for wp_id, state in snapshot.work_packages.items()
        if any(state.get(slot) not in (None, [], {}, "") for slot in RUNTIME_SLOTS)
    }


def mission_carries_event_log_runtime(mission_dir: Path) -> bool:
    """True iff *mission_dir*'s event log records independent runtime evidence.

    Evidence comes ONLY from ``status.events.jsonl`` — never from the retired
    frontmatter ``has_evictable_state()`` signal (every mission born after
    authoring retirement carries no frontmatter runtime state at all, so
    keying eligibility there makes the guard permanently blind to every
    future mission — a vacuous pass) and never from ``status_phase`` itself
    (circular: that field is exactly what this predicate's callers verify
    was flipped).

    "Carries runtime" means the log holds, for at least one WP, either:

    * an :class:`~specify_cli.status.InnerStateChanged` annotation — by
      construction an annotation is only ever appended with a non-empty
      runtime delta, so its mere presence IS runtime evidence; or
    * a lane transition whose ``policy_metadata`` is non-empty — the only
      transitions that carry ``policy_metadata`` are real ``planned ->
      claimed`` claims (live-emitted or backfill-seeded — both shapes are
      byte-identical on the wire).

    Deliberately narrower than "any transition at all": every WP receives a
    ``genesis -> planned`` / self-transition ``planned -> planned`` canonical
    bootstrap identity anchor at ``finalize-tasks`` time that carries no
    runtime signal whatsoever. A never-claimed WP legitimately reduces to an
    empty snapshot; a predicate keyed on "any event" would wrongly flag those
    bootstrap-only missions as eligible.
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


def eligible_runtime_missions(
    corpus: Path, *, exclude: Iterable[str] = ()
) -> list[Path]:
    """Every mission under *corpus* whose event log carries runtime evidence.

    *exclude* names mission directory basenames to skip entirely (e.g. a
    live, actively-running cutover mission that must not be judged against
    its own momentary phase).
    """
    excluded = frozenset(exclude)
    eligible: list[Path] = []
    for mission_dir in sorted(corpus.iterdir()):
        if not mission_dir.is_dir() or mission_dir.name in excluded:
            continue
        if mission_carries_event_log_runtime(mission_dir):
            eligible.append(mission_dir)
    return eligible


@dataclass(frozen=True)
class CutOverVerdict:
    """Fail-closed verdict for a single mission's cut-over status.

    ``cut_over`` is the caller-facing decision; ``reasons`` is a
    human-readable, non-empty explanation whenever ``cut_over`` is False (and
    empty otherwise). ``mission_slug`` is always the directory basename,
    independent of whether ``mission_id`` could be read.
    """

    mission_dir: Path
    mission_slug: str
    cut_over: bool
    reasons: tuple[str, ...] = ()


def is_cut_over(mission_dir: Path) -> CutOverVerdict:
    """Decide cut-over for *mission_dir* per the data-model.md definition.

    Fails closed on every uncertain path (absent ``mission_id``, a
    ``verify_backfill`` error, an empty snapshot despite event-log evidence):
    never returns ``cut_over=True`` on anything but a fully-verified,
    evidence-backed, phase-flipped mission.

    A mission with NO event-log runtime evidence at all (never claimed) is
    exempt from the invariant — it is reported cut-over because there is
    nothing here for the guard to enforce (module docstring).
    """
    # Import locally: backfill_runtime_state imports FROM specify_cli.status
    # at module scope, so importing it back at THIS module's top level would
    # create a circular import the first time anything under
    # specify_cli.status is initialized before specify_cli.migration is.
    from specify_cli.migration.backfill_runtime_state import verify_backfill  # noqa: PLC0415

    slug = mission_dir.name

    mission_id = read_mission_id(mission_dir)
    if not mission_id:
        return CutOverVerdict(
            mission_dir=mission_dir,
            mission_slug=slug,
            cut_over=False,
            reasons=("absent mission_id",),
        )

    if not mission_carries_event_log_runtime(mission_dir):
        return CutOverVerdict(
            mission_dir=mission_dir,
            mission_slug=slug,
            cut_over=True,
            reasons=(),
        )

    phase = status_phase(mission_dir)
    if (phase or 0) < 1:
        return CutOverVerdict(
            mission_dir=mission_dir,
            mission_slug=slug,
            cut_over=False,
            reasons=("status_phase not flipped despite event-log runtime evidence",),
        )

    wps = runtime_wps(mission_dir)
    if not wps:
        return CutOverVerdict(
            mission_dir=mission_dir,
            mission_slug=slug,
            cut_over=False,
            reasons=("reduced snapshot empty despite event-log runtime evidence",),
        )

    try:
        result = verify_backfill(mission_dir)
    except Exception as exc:  # noqa: BLE001 — fail closed on ANY verify error
        return CutOverVerdict(
            mission_dir=mission_dir,
            mission_slug=slug,
            cut_over=False,
            reasons=(f"verify_backfill errored: {exc}",),
        )

    if not result.ok:
        return CutOverVerdict(
            mission_dir=mission_dir,
            mission_slug=slug,
            cut_over=False,
            reasons=result.mismatches or ("verify_backfill not ok",),
        )

    return CutOverVerdict(mission_dir=mission_dir, mission_slug=slug, cut_over=True, reasons=())


def assert_birth_invariant_holds(corpus: Path, *, exclude: Iterable[str] = ()) -> None:
    """FR-010 / C-003: every eligible mission is flipped, populated, verifies.

    Shared assertion body run both over the real committed corpus and over a
    synthetic drifted fixture, proving the re-keyed lock genuinely REDS on
    drift rather than only ever observing an already-healthy corpus.

    ``verify_backfill`` is the fail-closed count+value parity check of the
    reduced snapshot against the OLD frontmatter/``tasks.md`` reader, so an
    ``ok`` result is the spot-check that the seeded snapshot equals the
    legacy view, not merely that *something* was seeded.
    """
    missions = eligible_runtime_missions(corpus, exclude=exclude)
    assert missions, "no eligible runtime-carrying missions found"

    unflipped = [
        mission.name for mission in missions if (status_phase(mission) or 0) < 1
    ]
    assert unflipped == [], f"eligible missions not cut over: {unflipped}"

    from specify_cli.migration.backfill_runtime_state import verify_backfill  # noqa: PLC0415

    for mission_dir in missions:
        wps = runtime_wps(mission_dir)
        assert wps, f"{mission_dir.name}: expected runtime-carrying WPs, snapshot empty"

        for wp_id in wps:
            state = wp_snapshot_state(mission_dir, wp_id)
            assert state, f"{mission_dir.name}:{wp_id}: wp_snapshot_state empty after backfill"
            assert any(
                state.get(slot) not in (None, [], {}, "") for slot in RUNTIME_SLOTS
            ), f"{mission_dir.name}:{wp_id}: no runtime slot populated in snapshot"

        result = verify_backfill(mission_dir)
        assert result.ok, (
            f"{mission_dir.name}: verify_backfill NOT ok after backfill: "
            + "; ".join(result.mismatches)
        )
