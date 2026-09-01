"""Committed-authority module — single acceptable-ending fold + terminal verdict.

Mission next-committed-state-authority-01M1CA8W (issues #2947, #3780), WP01
IC-01/IC-02. Factors ONE authority atom that both fixes in this mission
consume (D11, DIRECTIVE_044): a single status reduction per WP yielding lane
+ ``reason_source``, folded through the shipped
``specify_cli.status_lanes.is_acceptable_ending`` /
``has_operator_provenance`` authority — consumed here, never reimplemented
(C-001).

Wording note on "committed": everywhere this module says "committed" (the
module name, ``committed_wp_lane``, the ``WpEnding``/verdict docstrings) it
means the PRIMARY-surface (repo-root checkout) working tree — read via
``placement_seam(...).read_dir(MissionArtifactKind.PRIMARY_METADATA)`` — as
opposed to the (possibly stale) coordination checkout. It is deliberately
NOT a git-ref-level read (no commit SHA, no ``git show``): the current
on-disk state of the PRIMARY checkout is treated as authoritative because it
is the surface merge writes to and coordination checkouts are torn down
after (D9/D14). This is intentional and fail-safe (a missing/corrupt file on
that surface degrades rather than reading a stale ref), but a later reader
should not infer git-commit-level immutability from "committed" here.

Fail-loud contract (D6/C-003): a genuinely-absent committed status event log
raises :class:`~specify_cli.status.lane_reader.CanonicalStatusNotFoundError`
— this module's ``_require_event_log`` mirrors
``specify_cli.status.lane_reader._require_event_log`` exactly. A naive
``wp_snapshot_state`` swap would swallow this silently (see
``research.md``/``tracer-design-decisions.md`` D6) — that trap is why the
gate is explicit and separate from the reduction below.

Single-reduction contract (C-004): each public function performs exactly ONE
``reduce()`` call per read. ``wp_ending`` reduces once per WP;
``mission_terminal_verdict`` reduces once for the WHOLE mission and folds
every WP from that single reduced snapshot (never re-reducing per WP).

Primary-surface contract (D9/D14/BLOCKER-1): ``mission_terminal_verdict`` and
``committed_wp_lane`` read ``mission_number`` via the sanctioned
``read_primary_meta`` primitive and the committed status surface via the
sanctioned ``runtime_bridge_identity._primary_runtime_feature_dir`` identity
seam — never a hand-composed primary path. ``primary_feature_dir_for_mission``
was deleted; manual path composition trips
``tests/architectural/test_no_read_side_bypass.py``, which does not sanction
``src/runtime/next/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from specify_cli.status import (
    CanonicalStatusNotFoundError,
    Lane,
    has_event_log,
    read_event_stream,
    reduce,
)
from specify_cli.status_lanes import has_operator_provenance, is_acceptable_ending

#: The mission-terminal-verdict outcomes (FR-009): ``mission_number`` present
#: and every WP an acceptable ending -> ``"terminal"``; ``mission_number``
#: present and NOT every WP acceptable -> ``"blocked_conflict"``;
#: ``mission_number`` absent, OR the committed status log is genuinely absent
#: on the PRIMARY surface -> ``"none"`` (a genuinely-absent log is NOT a
#: conflict — C-003/D9).
TerminalVerdict = Literal["terminal", "blocked_conflict", "none"]


@dataclass(frozen=True)
class WpEnding:
    """One WP's committed-authority ending: lane, acceptability, provenance source.

    ``reason_source`` is the raw reduced-snapshot discriminator
    (``specify_cli.status_lanes.OPERATOR_REASON_SOURCE`` or a synthetic
    marker); ``None`` for a non-canceled WP, or a legacy snapshot lacking the
    slot (mirrors :func:`~specify_cli.status_lanes.has_operator_provenance`'s
    own ``None``-tolerant contract).
    """

    lane: str
    acceptable: bool
    reason_source: str | None


def _require_event_log(feature_dir: Path) -> None:
    """Raise ``CanonicalStatusNotFoundError`` when no committed event log exists.

    Local mirror of ``specify_cli.status.lane_reader._require_event_log``
    (D6/C-003): the explicit gate that preserves the fail-loud contract ahead
    of the single reduction below, so a genuinely-absent log raises instead of
    silently folding to an empty snapshot.
    """
    if not has_event_log(feature_dir):
        from specify_cli.status.uninitialized_hint import (
            feature_event_log_missing_error,
        )

        raise CanonicalStatusNotFoundError(feature_event_log_missing_error(feature_dir))


def _fold_wp_state(wp_state: dict[str, Any] | None) -> WpEnding:
    """Pure fold: one reduced WP state -> ``WpEnding`` via the shipped authority.

    The ONE acceptable-ending fold (D11/IC-01): both ``wp_ending`` (per-WP)
    and ``mission_terminal_verdict`` (all-WP) route through this single
    private helper, so ``is_acceptable_ending``/``has_operator_provenance``
    is called from exactly one place.
    """
    lane = (
        str(wp_state.get("lane", Lane.GENESIS))
        if wp_state is not None
        else str(Lane.UNINITIALIZED)
    )
    reason_source_raw = wp_state.get("reason_source") if wp_state is not None else None
    reason_source = reason_source_raw if isinstance(reason_source_raw, str) else None
    acceptable = is_acceptable_ending(lane, has_provenance=has_operator_provenance(wp_state))
    return WpEnding(lane=lane, acceptable=acceptable, reason_source=reason_source)


def wp_ending(feature_dir: Path, wp_id: str) -> WpEnding:
    """Return the committed-authority ending for one WP (IC-01).

    Performs exactly ONE status reduction (C-004), fronted by the explicit
    fail-loud event-log gate (C-003/D6). ``acceptable`` folds the reduced
    lane + provenance through the single shipped authority
    (:func:`~specify_cli.status_lanes.is_acceptable_ending` /
    :func:`~specify_cli.status_lanes.has_operator_provenance` — consumed,
    never reimplemented, C-001).

    Raises ``CanonicalStatusNotFoundError`` when *feature_dir* carries no
    committed event log at all.
    """
    _require_event_log(feature_dir)
    stream = read_event_stream(feature_dir)
    snapshot = reduce(stream.transitions, stream.annotations)
    return _fold_wp_state(snapshot.work_packages.get(wp_id))


def mission_terminal_verdict(repo_root: Path, mission_slug: str) -> TerminalVerdict:
    """Return the mission's committed-authority terminal verdict (IC-02).

    Reads ``mission_number`` from the PRIMARY meta
    (:func:`~specify_cli.missions._read_path_resolver.read_primary_meta`) and
    the committed status surface from the PRIMARY feature dir
    (``runtime_bridge_identity._primary_runtime_feature_dir`` — the sanctioned
    identity seam, D14/BLOCKER-1) — never the coordination checkout, and never
    a hand-composed primary path. Keys ONLY on the committed
    ``mission_number`` (assigned at merge time, ``merge/ordering.py``); never
    ``merge-state.json`` / ``MERGE_HEAD`` (C-005). A genuinely-absent
    committed status log is ``"none"``, not a conflict (D9/C-003).

    "Committed" here means the PRIMARY checkout's current working tree, not
    a git ref (see the module docstring's wording note) -- both reads below
    are plain filesystem reads of that checkout as it stands right now.
    """
    from specify_cli.missions._read_path_resolver import read_primary_meta

    primary_meta, _declares_coordination = read_primary_meta(repo_root, mission_slug)
    if primary_meta.get("mission_number") is None:
        return "none"

    from runtime.next.runtime_bridge_identity import _primary_runtime_feature_dir

    feature_dir = _primary_runtime_feature_dir(repo_root, mission_slug)
    if not has_event_log(feature_dir):
        return "none"

    stream = read_event_stream(feature_dir)
    snapshot = reduce(stream.transitions, stream.annotations)
    if not snapshot.work_packages:
        return "none"

    endings = [_fold_wp_state(state) for state in snapshot.work_packages.values()]
    return "terminal" if all(ending.acceptable for ending in endings) else "blocked_conflict"


def committed_wp_lane(repo_root: Path, mission_slug: str, wp_id: str) -> str | None:
    """Return the committed PRIMARY-surface lane for *wp_id*, or ``None``.

    ``None`` means PRIMARY is not the authoritative status surface for this
    mission, so the caller (``agent tasks status``'s board, D10/IC-04) must
    fall back to its own coordination-aware read. That is the case whenever
    the mission is **not merged** — keyed on the committed ``mission_number``
    (assigned at merge, ``merge/ordering.py``), exactly as
    :func:`mission_terminal_verdict` keys it (#2947). An in-flight
    coordination-topology mission's status lives only on the coordination
    worktree until merge folds it back onto PRIMARY; crucially, its PRIMARY
    surface may still carry an event log (planning-phase events, or a decoy),
    so ``has_event_log`` alone is NOT a sound merged-signal — without the
    ``mission_number`` gate the board would read that PRIMARY decoy and
    misreport an in-flight WP's lane (e.g. a genuine COORD ``in_progress`` as
    a stale PRIMARY ``blocked``). ``None`` is also returned when the
    committed log is genuinely absent on PRIMARY.

    "Committed"/"PRIMARY surface" means the current working tree of the
    PRIMARY checkout, not a git ref (see the module docstring's wording
    note) — this reads whatever is on disk there right now.
    """
    from specify_cli.missions._read_path_resolver import read_primary_meta
    from runtime.next.runtime_bridge_identity import _primary_runtime_feature_dir

    primary_meta, _declares_coordination = read_primary_meta(repo_root, mission_slug)
    if primary_meta.get("mission_number") is None:
        # Not merged: PRIMARY is not authoritative (an in-flight mission's
        # PRIMARY event log, if any, is a planning/decoy log). Defer to the
        # board's coordination-aware read.
        return None

    feature_dir = _primary_runtime_feature_dir(repo_root, mission_slug)
    if not has_event_log(feature_dir):
        return None
    return wp_ending(feature_dir, wp_id).lane
