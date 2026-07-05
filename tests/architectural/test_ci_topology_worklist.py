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
RED until WP03 adds the composite groups. The freshness assertion
``census.worklist == live_derived_worklist()`` is GREEN today and closes the
SC-001 vacuous-pass gap: a stale or hand-trimmed census reds in CI (NFR-006).

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
    """The census ``worklist`` entries (dir + LOC + routing plan)."""
    entries: list[dict[str, Any]] = census["worklist"]
    return entries


def test_census_worklist_matches_live_derivation(census: dict[str, Any]) -> None:
    """NFR-006 freshness guard (GREEN today): census == live re-derivation.

    The committed worklist must equal :func:`_gate_coverage.live_derived_worklist`
    re-derived from the live source tree + parsed filter groups. A stale or
    hand-trimmed census then REDS in CI, so the SC-001 iteration below cannot be
    gamed by editing the artifact.
    """
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
    """Each worklist dir clears the committed ``t_loc`` floor (read from artifact)."""
    t_loc = census["t_loc"]
    assert isinstance(t_loc, int)
    for entry in worklist:
        assert entry["loc"] >= t_loc, (
            f"{entry['dir']} LOC {entry['loc']} < committed floor {t_loc}"
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
