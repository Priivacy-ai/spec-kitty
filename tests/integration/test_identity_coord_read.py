"""RED-first identity-routing tests on the divergent sentinel-husk fixture (WP01 T009).

Mission ``coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V`` —
Lane B (#2186). Proves that the routed identity reads resolve their domain value
(lifecycle ``mission_id`` / mission ``type``) from the PRIMARY checkout, not the
STATUS-only ``-coord`` husk, on a fixture whose husk carries a PRESENT-but-WRONG
``meta.json`` (the FR-009 sentinel: ``mission_id = 6KERGF2ZNFBPR91YEZMARG99KS``,
``mission_type = research``) distinct from PRIMARY (``mission_id =
01KW2E7AFC0000000000000001``, ``mission_type = software-dev``).

Each assertion targets a RETURNED DOMAIN VALUE (the written lifecycle record's
``mission_id`` / the mission ``type`` passed to ``get_or_start_run``), NOT a
resolved-path equality and NOT the fixture's ``assert_reads_primary`` /
``assert_both_legs`` path-equality helpers (per T009). Reverting any routed read
to the coord-aware resolver surfaces the sentinel/wrong type → the test goes RED.

**NFR-004 (no primary-dir stub):** these tests drive the REAL helper functions
against a REAL ``git worktree`` coord fixture. No test hands a primary dir
directly to the function under test — the routing decision (PRIMARY vs coord-aware)
is exercised inside production code.

================================================================================
T004 — Lane B (#2186) ROUTE / KEEP / owned-by-implement-loop ownership table
================================================================================

Every Lane B identity site, cross-checked against the implement-loop sibling's
ROUTE+KEEP list and re-resolved against the merged base. No site is left in the
gap between the two missions (FR-005).

| Site (re-resolved on lane-a)                          | Verdict | Coverage |
|-------------------------------------------------------|---------|----------|
| next_cmd.py `_pair_previous_lifecycle_record`  (~:190)| ROUTE   | this file: test_pairing_* (end-to-end domain value) |
| next_cmd.py `_write_issuance_lifecycle_record` (~:260)| ROUTE   | this file: test_issuance_* (end-to-end domain value) |
| next_cmd.py `_handle_answer` get_mission_type    | ROUTE   | this file: test_answer_flow_type_* (captured type) |
| implement.py `implement` json-output identity (~:1404)| ROUTE   | FR-007 call-shape arm (static): clean post-route; |
|                                                       |         |  shares the next_cmd primary-fold pattern |
| workflow.py sparse-checkout preflight mission_id      | ROUTE   | FR-007 call-shape arm (static) |
| workflow.py get_mission_type leg (own anchor)         | ROUTE   | FR-007 call-shape arm (static) |
| workflow.py review-prompt metadata mission_id         | ROUTE   | FR-007 call-shape arm (static) |
| agent_utils/status.py:132 `show_kanban_status`        | owned by WP03 (T021) — NOT routed here; the FR-007 |
|   identity arm's scope INCLUDES it (statically gated) | identity arm covers its scope but the route lands in WP03 |
| STATUS event-log reads (read_events / status legs)    | KEEP    | coord-aware (C-001) — touching them re-opens #2155 |

The implement-loop sibling's ROUTE+KEEP legs (`workflow.py:2110/2116/2121/2124`,
review-cycle `:2610/:2647`, KEEP `:1015`) are LINE-DISJOINT from the identity legs
above (squad-verified, architect lens) — this WP touches only the #2186 identity
legs, never the implement-loop ROUTE legs (C-009-mirror).

The implement.py/workflow.py sites live inside large orchestration entry points
(`implement()` / workflow `execute`) that require a full mission + worktree to
drive end-to-end; their RED-first behavioral coverage in a focused integration
test is impractical, so their regression coverage here is the FR-007 call-shape
arm (static: verified clean post-route, and the WP03-owned status.py:132 still
flags — proving the arm has live teeth) plus the identical primary-fold pattern
the next_cmd sites prove behaviorally below.
"""

from __future__ import annotations

import types
from typing import NoReturn

import pytest

from specify_cli.invocation.lifecycle import read_lifecycle_records, write_started
from tests.integration.coord_topology_fixture import (
    SENTINEL_HUSK_MISSION_ID,
    SENTINEL_HUSK_MISSION_TYPE,
    CoordTopologyContext,
    coord_topology_mission_sentinel_meta,
)

# Re-export the fixture so pytest discovers it in this module.
__all__ = ["coord_topology_mission_sentinel_meta"]

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_AGENT = "claude"
# The PRIMARY mission_id the fixture resolves (distinct from the husk sentinel).
_PRIMARY_MISSION_ID = "01KW2E7AFC0000000000000001"
_PRIMARY_MISSION_TYPE = "software-dev"


def _make_decision() -> types.SimpleNamespace:
    """A minimal duck-typed ``decision`` that issues a public step action.

    ``_write_issuance_lifecycle_record`` requires a truthy ``action`` +
    ``mission_state`` and ``kind == "step"``; ``wp_id`` rides along onto the
    record. Realistic values (a real implementing step, a real WP id).
    """
    return types.SimpleNamespace(
        action="implement_wp",
        mission_state="implementing",
        kind="step",
        wp_id="WP01",
    )


# ---------------------------------------------------------------------------
# Pre-condition sanity: the sentinel husk diverges from PRIMARY (the triad is
# asserted inside the fixture builder; this re-states the falsifiability premise).
# ---------------------------------------------------------------------------


def test_sentinel_husk_meta_diverges_from_primary(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
) -> None:
    """The husk meta carries the sentinel id/type, distinct from PRIMARY — so a
    wrong-leg read returns a SILENT-WRONG-VALUE the domain-value asserts can catch.
    """
    ctx = coord_topology_mission_sentinel_meta
    assert ctx.coord_husk_meta_path is not None
    assert ctx.coord_husk_meta_path.exists()
    assert ctx.mission_id == _PRIMARY_MISSION_ID
    assert SENTINEL_HUSK_MISSION_ID != _PRIMARY_MISSION_ID
    assert SENTINEL_HUSK_MISSION_TYPE != _PRIMARY_MISSION_TYPE


# ---------------------------------------------------------------------------
# next_cmd `_write_issuance_lifecycle_record` (ROUTE — :253 resolve_mission_identity)
# ---------------------------------------------------------------------------


def test_issuance_lifecycle_record_uses_primary_mission_id(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
) -> None:
    """The ``started`` lifecycle record is written with the PRIMARY ``mission_id``.

    RED-first: before routing, ``_write_issuance_lifecycle_record`` resolved
    ``feature_dir`` via ``resolve_feature_dir_for_mission`` → the coord husk →
    ``resolve_mission_identity`` returns the SENTINEL id. Reverting the routed read
    surfaces ``6KERGF2ZNFBPR91YEZMARG99KS`` in the written record and FAILS the
    PRIMARY-id assertion (returned domain value, not a path equality).
    """
    from specify_cli.cli.commands.next_cmd import _write_issuance_lifecycle_record

    ctx = coord_topology_mission_sentinel_meta

    _write_issuance_lifecycle_record(_AGENT, ctx.slug, ctx.repo, _make_decision())

    records = read_lifecycle_records(ctx.repo)
    started = [r for r in records if r.phase == "started"]
    assert started, "issuance must write exactly one started lifecycle record"
    written_id = started[-1].mission_id
    assert written_id == _PRIMARY_MISSION_ID, (
        "lifecycle started record must carry the PRIMARY mission_id read off the "
        f"PRIMARY meta.json.\n  Expected : {_PRIMARY_MISSION_ID}\n"
        f"  Got      : {written_id}\n"
        "Got the husk sentinel — the identity read regressed to the coord-aware "
        "resolver (the STATUS-only husk meta)."
    )
    assert written_id != SENTINEL_HUSK_MISSION_ID


# ---------------------------------------------------------------------------
# next_cmd `_pair_previous_lifecycle_record` (ROUTE — :187 resolve_mission_identity)
# ---------------------------------------------------------------------------


def test_pairing_lifecycle_completion_uses_primary_mission_id(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
) -> None:
    """The paired ``completed`` record carries the PRIMARY ``mission_id``.

    A ``started`` record is seeded DIRECTLY with the PRIMARY id (isolating the
    pairing read). ``_pair_previous_lifecycle_record`` resolves the mission_id from
    its OWN identity read, finds the matching unpaired started, and writes a
    completion. Routed → PRIMARY id matches → completion written with PRIMARY id.

    RED-first: reverting the routed read resolves the SENTINEL id; the unpaired
    started (PRIMARY id) no longer matches → NO completion is written → the
    "exactly one completion with PRIMARY id" assertion FAILS.
    """
    from specify_cli.cli.commands.next_cmd import _pair_previous_lifecycle_record

    ctx = coord_topology_mission_sentinel_meta

    # Seed an unpaired started record with the PRIMARY mission_id (real store I/O).
    write_started(
        ctx.repo,
        canonical_action_id="implementing::implement_wp",
        agent=_AGENT,
        mission_id=_PRIMARY_MISSION_ID,
        wp_id="WP01",
    )

    _pair_previous_lifecycle_record(_AGENT, ctx.slug, "success", ctx.repo)

    records = read_lifecycle_records(ctx.repo)
    completions = [r for r in records if r.phase == "completed"]
    assert len(completions) == 1, (
        "pairing must write exactly one completed record. Zero means the pairing "
        "identity read resolved the husk SENTINEL id and found no matching started "
        "(the routed read regressed to the coord-aware resolver)."
    )
    assert completions[0].mission_id == _PRIMARY_MISSION_ID


# ---------------------------------------------------------------------------
# #2278 — the lifecycle ``mission_id`` field is a ULID, never a slug. A legacy
# mission whose identity resolves NO ``mission_id`` must fail closed (skip the
# observability record) rather than persist the slug — the #2138/FR-004 contract
# applied to the next_cmd invocation-lifecycle pairing key (both write sites).
# ---------------------------------------------------------------------------


def test_issuance_lifecycle_record_fails_closed_without_mission_id(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ``started`` record is written keyed on the slug when no ULID is minted.

    RED-first: the pre-fix code did ``identity.mission_id or identity.mission_slug``
    and wrote a ``started`` record stamping the slug into the ULID-typed
    ``mission_id`` field. Fail-closed → zero records (the lifecycle log is
    observability, not a hard dependency).
    """
    import specify_cli.mission_metadata as mm
    from specify_cli.cli.commands.next_cmd import _write_issuance_lifecycle_record

    ctx = coord_topology_mission_sentinel_meta
    legacy_identity = types.SimpleNamespace(mission_id=None, mission_slug=ctx.slug)
    monkeypatch.setattr(mm, "resolve_mission_identity", lambda _dir: legacy_identity)

    _write_issuance_lifecycle_record(_AGENT, ctx.slug, ctx.repo, _make_decision())

    records = read_lifecycle_records(ctx.repo)
    assert [r for r in records if r.phase == "started"] == [], (
        "fail-closed: no started lifecycle record may be written when the mission "
        "has no canonical mission_id (the pre-fix code wrote one keyed on the slug)."
    )
    assert all(r.mission_id != ctx.slug for r in records), (
        "the mission slug must never land in the ULID-typed mission_id field (#2278)."
    )


def test_pairing_lifecycle_completion_fails_closed_without_mission_id(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No completion is paired/stamped against a slug-keyed started when no ULID.

    RED-first: pre-fix resolved ``mission_id = slug``, paired the seeded slug-keyed
    started, and wrote a completion stamping the slug. Fail-closed → it returns
    before pairing, so no completion is written.
    """
    import specify_cli.mission_metadata as mm
    from specify_cli.cli.commands.next_cmd import _pair_previous_lifecycle_record

    ctx = coord_topology_mission_sentinel_meta
    # Seed a slug-keyed unpaired started — what the buggy issuance path would leave.
    write_started(
        ctx.repo,
        canonical_action_id="implementing::implement_wp",
        agent=_AGENT,
        mission_id=ctx.slug,
        wp_id="WP01",
    )
    legacy_identity = types.SimpleNamespace(mission_id=None, mission_slug=ctx.slug)
    monkeypatch.setattr(mm, "resolve_mission_identity", lambda _dir: legacy_identity)

    _pair_previous_lifecycle_record(_AGENT, ctx.slug, "success", ctx.repo)

    records = read_lifecycle_records(ctx.repo)
    assert [r for r in records if r.phase == "completed"] == [], (
        "fail-closed: no completion may be written when the mission has no canonical "
        "mission_id (the pre-fix code paired the slug-keyed started and stamped it)."
    )


# ---------------------------------------------------------------------------
# next_cmd `_handle_answer` get_mission_type (ROUTE — :619)
# ---------------------------------------------------------------------------


class _StopProbe(BaseException):
    """Raised by the fake runtime bridge to short-circuit after capturing type.

    Subclasses ``BaseException`` (not ``Exception``) so it propagates THROUGH the
    ``except Exception`` handler in ``_handle_answer`` — the capture has already
    happened, and we only want to stop before the real runtime work.
    """


def test_answer_flow_get_mission_type_reads_primary_type(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_handle_answer`` reads the PRIMARY mission TYPE for ``get_or_start_run``.

    The runtime bridge's ``get_or_start_run`` is faked to CAPTURE the
    ``mission_type`` argument (a returned domain value) and short-circuit. Routed →
    ``get_mission_type`` reads the PRIMARY meta.json → ``software-dev``.

    RED-first: reverting the routed read lands on the husk (sentinel
    ``mission_type = research``) → the captured type is ``research`` → FAILS.
    """
    from specify_cli.cli.commands import next_cmd

    ctx = coord_topology_mission_sentinel_meta
    captured: dict[str, str] = {}

    def _fake_get_or_start_run(
        mission_slug: str, repo_root: object, mission_type: str
    ) -> NoReturn:
        captured["mission_type"] = mission_type
        raise _StopProbe

    fake_bridge = types.SimpleNamespace(get_or_start_run=_fake_get_or_start_run)
    monkeypatch.setattr(next_cmd, "_runtime_bridge_module", lambda: fake_bridge)

    with pytest.raises(_StopProbe):
        next_cmd._handle_answer(
            agent=_AGENT,
            mission_slug=ctx.slug,
            answer="yes",
            decision_id=None,
            repo_root=ctx.repo,
        )

    assert captured.get("mission_type") == _PRIMARY_MISSION_TYPE, (
        "get_or_start_run must receive the PRIMARY mission type read off the PRIMARY "
        f"meta.json.\n  Expected : {_PRIMARY_MISSION_TYPE}\n"
        f"  Got      : {captured.get('mission_type')!r}\n"
        "Got the husk sentinel type — get_mission_type regressed to the coord-aware "
        "resolver (the STATUS-only husk)."
    )
    assert captured["mission_type"] != SENTINEL_HUSK_MISSION_TYPE
