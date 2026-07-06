"""SC-001 / FR-001 / NFR-006 — construction-derived worklist routing invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 (red-first). Iterates the committed
CI-topology census (``ci_topology_census.json``) and asserts every dir on the
FR-001 worklist routes to a **named, src-backed dorny filter group** and a
**focused integration shard** so a PR touching only that dir does NOT fall to
``unmatched -> run_all`` (SC-001). The LOC floor (``t_loc``) is read from the
census artifact, never inlined — the metric measures coverage, not the
implementer's constant (NFR-006).

Authored FAILING against today's topology: every worklist dir is unmapped by
construction (that is *why* it is on the worklist), so the routing assertions
RED until WP03 adds the composite groups. The freshness assertion compares
membership + routing via ``worklist_routing_index`` (order/LOC-insensitive,
issue #2416) and closes the SC-001 vacuous-pass gap: a stale or hand-trimmed
census reds in CI (NFR-006).

Consumes only the additive WP01 relations in
:mod:`tests.architectural._gate_coverage`; it does not re-derive the model.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_SRC_GLOB_PREFIX = "src/"


@pytest.fixture(scope="module")
def census() -> dict[str, Any]:
    """The committed construction-derived CI-topology census (SC-001 authority)."""
    raw = gc.CENSUS_PATH.read_text(encoding="utf-8")
    parsed: dict[str, Any] = json.loads(raw)
    return parsed


@pytest.fixture(scope="module")
def models() -> dict[str, gc.WorkflowModel]:
    """Parsed workflow relation models for the four suite-running workflows."""
    return gc.load_workflow_models()


@pytest.fixture(scope="module")
def worklist(census: dict[str, Any]) -> list[dict[str, Any]]:
    """The census ``worklist`` entries (dir + routing plan; no exact LOC, #2416)."""
    entries: list[dict[str, Any]] = census["worklist"]
    return entries


def test_census_worklist_matches_live_derivation(census: dict[str, Any]) -> None:
    """NFR-006 freshness guard: census matches live re-derivation on membership +
    committed routing plan (order/LOC-insensitive, issue #2416).

    Compared via :func:`_gate_coverage.worklist_routing_index`, so a pure line-count
    change on a worklist dir (or a LOC rank-swap between two members) no longer reds
    this gate. A stale or hand-trimmed census still REDS: dropping a dir, a
    floor-crossing, a new hot dir, or a routing hand-edit all change this index. The
    absence of exact ``loc`` is guarded by :func:`test_committed_census_carries_no_loc`.
    """
    assert gc.worklist_routing_index(census["worklist"]) == gc.worklist_routing_index(
        gc.live_derived_worklist(),
    )


def test_rank_altering_loc_churn_keeps_gate_green(
    monkeypatch: pytest.MonkeyPatch,
    census: dict[str, Any],
) -> None:
    """FR-001 + FR-007 (red-first, issue #2416): a LOC churn that flips the relative
    LOC rank of two worklist members — pure churn, no membership/routing change — must
    keep the freshness gate green. RED on the base branch (ordered list-equality compares
    exact loc + order); GREEN after the loc-drop + dir-keyed index compare.
    """
    real = gc.src_package_loc()
    a, b = "tracker", "doctrine"  # two worklist members; swapping flips their -loc rank
    live_dirs = {e["dir"] for e in gc.live_derived_worklist()}
    assert {a, b} <= live_dirs, "chosen pair must both be worklist members"
    assert a in real and b in real and real[a] != real[b]
    swapped = {**real, a: real[b], b: real[a]}
    monkeypatch.setattr(gc, "src_package_loc", lambda *args, **kwargs: swapped)
    # On the fixed code this compares membership + routing only (order/LOC-insensitive).
    assert census["worklist"] == gc.live_derived_worklist()


def test_census_mapped_dirs_matches_live_derivation(
    census: dict[str, Any],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """NFR-006 freshness guard: census ``mapped_dirs`` == live re-derivation.

    ``mapped_dirs`` is a construction-derived field (the src dirs a named
    src-backed dorny group claims). Post-shrink this is the live 55-dir set; a
    stale census (e.g. the pre-WP03 23-dir subset) then REDS here — the same
    close-by-construction guarantee the worklist freshness test gives.
    """
    assert census["mapped_dirs"] == sorted(gc.mapped_src_dirs(models))


def test_census_arch_blind_groups_matches_live_derivation(
    census: dict[str, Any],
) -> None:
    """NFR-006 freshness guard: census ``arch_blind_groups`` == live re-derivation.

    Post-shrink the differential arch matrix fires on every mapped src dir, so
    the live arch-blind set is empty; the census must agree (0 rows). A stale
    census still listing the eliminated Mode-B blind groups then REDS here,
    matching the ``test_no_src_dir_is_architecturally_blind`` invariant.
    """
    assert census["arch_blind_groups"] == gc.build_census()["arch_blind_groups"]
    assert {row["dir"] for row in census["arch_blind_groups"]} == set(
        gc.arch_blind_src_dirs(),
    )


def test_worklist_is_non_empty(worklist: list[dict[str, Any]]) -> None:
    """Guard against a vacuous iteration: the pre-WP03 worklist has real dirs."""
    assert worklist, "census worklist is empty — SC-001 iteration would be vacuous"


def test_every_worklist_dir_meets_loc_floor(
    census: dict[str, Any],
    worklist: list[dict[str, Any]],
) -> None:
    """Each committed worklist dir clears the committed ``t_loc`` floor, checked
    against the LIVE source tree rather than a stored snapshot (FR-006, #2416)."""
    t_loc = census["t_loc"]
    assert isinstance(t_loc, int)
    loc_by_dir = gc.src_package_loc()
    for entry in worklist:
        live_loc = loc_by_dir.get(entry["dir"], 0)
        assert live_loc >= t_loc, (
            f"{entry['dir']} live LOC {live_loc} < committed floor {t_loc}"
        )


def test_every_worklist_dir_routes_to_named_src_backed_group(
    worklist: list[dict[str, Any]],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """RED today: each worklist dir's target group must be a live src-backed group.

    Post-WP03 the composite groups (``agent_surface``, ``lifecycle``,
    ``closeout``, ``governance``, ``platform``, ``auth_audit_git``) exist as
    dorny filter groups; today they do not, so the target group is absent from
    the parsed ``filter_groups`` and this REDS.
    """
    groups = gc.aggregate_filter_groups(models)
    unrouted: list[str] = []
    for entry in worklist:
        target = entry["target_group"]
        globs = groups.get(target, ())
        src_backed = any(glob.startswith(_SRC_GLOB_PREFIX) for glob in globs)
        if target is None or not globs or not src_backed:
            unrouted.append(f"{entry['dir']}->{target!r}")
    assert not unrouted, (
        "worklist dirs whose target group is not a live src-backed filter group "
        f"(pre-WP03 RED, {len(unrouted)}): {unrouted}"
    )


def test_no_worklist_dir_falls_to_unmatched_run_all(
    worklist: list[dict[str, Any]],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """RED today: a confined touch of each worklist dir must be claimed, not run_all.

    ``mapped_src_dirs`` is exactly the set of dirs a named src-backed group
    claims; a dir absent from it trips ``unmatched -> run_all`` (SC-001's blast
    radius). Every worklist dir is unmapped today (that is the FR-001 gap), so
    this REDS until WP03 maps them.
    """
    mapped = gc.mapped_src_dirs(models)
    unmatched = [entry["dir"] for entry in worklist if entry["dir"] not in mapped]
    assert not unmatched, (
        "worklist dirs that still fall to unmatched->run_all on a confined touch "
        f"(pre-WP03 RED, {len(unmatched)}): {sorted(unmatched)}"
    )


def test_every_worklist_dir_declares_a_focused_shard(
    worklist: list[dict[str, Any]],
) -> None:
    """Each worklist dir carries a focused integration shard in its routing plan."""
    missing = [entry["dir"] for entry in worklist if not entry["target_shard"]]
    assert not missing, f"worklist dirs with no focused shard in the plan: {missing}"


# --- Non-vacuous freshness teeth (NFR-004 / C-004, issue #2416) -------------
# Each tooth mutates a copy of the LIVE derivation and asserts the real
# ``worklist_routing_index`` compare reds, proving the narrowed gate still bites
# after exact LOC was dropped from the comparison surface.


def test_freshness_index_reds_on_hand_trim() -> None:
    """FR-002: dropping a still-qualifying dir from the census reds the gate."""
    live = gc.live_derived_worklist()
    assert live, "worklist unexpectedly empty"
    trimmed = live[1:]
    assert gc.worklist_routing_index(trimmed) != gc.worklist_routing_index(live)


def test_freshness_index_reds_on_phantom_dir() -> None:
    """FR-004: a new hot dir absent from the census reds the gate."""
    live = gc.live_derived_worklist()
    phantom = [
        *live,
        {"dir": "zzz_phantom", "cone_roots": [], "target_group": "x", "target_shard": "y"},
    ]
    assert gc.worklist_routing_index(phantom) != gc.worklist_routing_index(live)


def test_freshness_index_reds_on_routing_edit() -> None:
    """FR-005: a hand-edited routing target reds the gate."""
    live = gc.live_derived_worklist()
    assert live, "worklist unexpectedly empty"
    tampered = [dict(entry) for entry in live]
    tampered[0] = {**tampered[0], "target_group": "WRONG_GROUP"}
    assert gc.worklist_routing_index(tampered) != gc.worklist_routing_index(live)


def test_freshness_index_reds_on_floor_crossing() -> None:
    """FR-003: a dir dropping below the floor leaves the live worklist; a census
    that still lists it reds. The raised floor ``t_high = min(member loc) + 1`` is
    derived dynamically so at least one member always leaves — non-vacuous and
    drift-proof even if today's sub-600 dirs grow later.
    """
    members = gc.live_derived_worklist()
    loc_by_dir = gc.src_package_loc()
    t_high = min(loc_by_dir[entry["dir"]] for entry in members) + 1
    fewer = gc.live_derived_worklist(t_loc=t_high)
    assert gc.worklist_routing_index(fewer) != gc.worklist_routing_index(members)


def test_committed_census_carries_no_loc(census: dict[str, Any]) -> None:
    """C-001 (durable, shape-independent): the committed census worklist stores NO
    exact ``loc``. Enforced directly here — NOT incidentally via a freshness test that
    is loc-blind after the #2416 fix — so a skipped/forgotten regen or a future
    reintroduction of the field reds regardless of the freshness test's shape.
    """
    stale = [entry["dir"] for entry in census["worklist"] if "loc" in entry]
    assert not stale, f"committed census entries still carry exact loc: {stale}"
