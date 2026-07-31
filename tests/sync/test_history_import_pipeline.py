"""Tests for the import-history orchestration — ``build_import_plan`` (#2262).

Drives the whole read-only pipeline (SELECT → AUDIT → SCAN → IDENTITY →
SYNTHESIZE) end to end: synthetic dual-shape on-disk fixtures for the happy
path, patched migration seams for the empty/blocked branches, and the apply
path to prove the real project UUID is threaded onto every envelope (INV-5).

The happy-path / apply-path fixtures are built under ``tmp_path`` via the
shared builders in ``test_history_import_scan`` (``_build_legacy_shape_mission``
/ ``_build_prefixed_shape_mission``) rather than pinned to specific
``kitty-specs/`` dogfood missions in this repo. Those directories are
scheduled for archival/relocation by the dogfood-corpus cutover (#2917); a
mission-keyed ``skipif`` would then silently skip forever instead of failing
(#2884 adversarial-review finding) — including the end-to-end apply test
below, which is the ONLY proof that a real synthesized stream survives
``validate_import_envelopes`` (the real outbound-envelope contract gate) and
uploads cleanly.
"""

from __future__ import annotations

import pytest

import specify_cli.migration.envelope_seam as envelope_seam
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.sync.history_import.pipeline import (
    ImportAuditBlocked,
    apply_import,
    build_import_plan,
    describe_plan,
)
from tests.sync.test_history_import_scan import (
    _build_legacy_shape_mission,
    _build_prefixed_shape_mission,
)

pytestmark = pytest.mark.fast

# ── fixed ULID-shaped ids (real ``python-ulid`` output, hardcoded for a
# deterministic, production-realistic ``mission_id`` per test) ───────────────
_PLAN_LEGACY_MISSION_ID = "01KYFVD16B6AAJKDMT8SHR6VWP"
_PLAN_PREFIXED_MISSION_ID = "01KYFVD16B6AAJKDMT8SHR6VWQ"
_APPLY_UUID_MISSION_ID = "01KYFVD16B6AAJKDMT8SHR6VWR"
_DESCRIBE_PLAN_MISSION_ID = "01KYFVD16B6AAJKDMT8SHR6VWS"
_E2E_LEGACY_MISSION_ID = "01KYFVD16B6AAJKDMT8SHR6VWT"
_E2E_PREFIXED_MISSION_ID = "01KYFVD16B6AAJKDMT8SHR6VWV"

# Reused across the happy-path / apply / e2e fixtures below: six legacy WPs
# (SYNTHESIZED prefix) drives the same WP-count floor the pipeline previously
# asserted against the real ``032-identity-aware-cli-event-sync`` fixture.
_LEGACY_WP_SPECS = [
    ("WP01", "ProjectIdentity Module", []),
    ("WP02", "Emitter Identity Injection", ["WP01"]),
    ("WP03", "AuthClient Team Slug", ["WP01"]),
    ("WP04", "Sync Runtime Lazy Singleton", ["WP02"]),
    ("WP05", "Fix Duplicate Emissions", ["WP02", "WP03"]),
    ("WP06", "Integration Tests", ["WP04", "WP05"]),
]
_PREFIXED_WP_SPECS = [
    (
        "WP01",
        "Surface-resolution audit (read-only inventory)",
        [],
        "kitty-specs/plan-prefixed-mission/tasks/WP01-surface-resolution-audit.md",
        "2026-06-19T17:11:46.841180Z",
    ),
    (
        "WP02",
        "Differential equivalence test (the deletion safety gate)",
        [],
        "kitty-specs/plan-prefixed-mission/tasks/WP02-differential-equivalence-test.md",
        "2026-06-19T17:11:46.855890Z",
    ),
]


def _legacy_lane_rows(mission_id: str, mission_slug: str) -> list[dict]:
    return [
        {
            "actor": "migration",
            "at": "2026-02-07T00:00:00Z",
            "event_id": "01KJ5V38V9HRA67BAXKNQDG0H7",
            "evidence": None,
            "execution_mode": "direct_repo",
            "force": True,
            "from_lane": "planned",
            "mission_id": mission_id,
            "mission_slug": mission_slug,
            "policy_metadata": None,
            "reason": "historical_frontmatter_to_jsonl:v1",
            "review_ref": None,
            "to_lane": "done",
            "wp_id": "WP01",
        },
        {
            "actor": "migration",
            "at": "2026-02-07T00:00:00Z",
            "event_id": "01KJ5V38VBW3NMHJEHCCKB3V7C",
            "evidence": None,
            "execution_mode": "direct_repo",
            "force": True,
            "from_lane": "planned",
            "mission_id": mission_id,
            "mission_slug": mission_slug,
            "policy_metadata": None,
            "reason": "historical_frontmatter_to_jsonl:v1",
            "review_ref": None,
            "to_lane": "done",
            "wp_id": "WP02",
        },
        {
            "actor": "migration",
            "at": "2026-02-07T00:00:00Z",
            "event_id": "01KJ5V38VD6E2V3WJE9KVG9M82",
            "evidence": None,
            "execution_mode": "direct_repo",
            "force": True,
            "from_lane": "planned",
            "mission_id": mission_id,
            "mission_slug": mission_slug,
            "policy_metadata": None,
            "reason": "historical_frontmatter_to_jsonl:v1",
            "review_ref": None,
            "to_lane": "in_progress",
            "wp_id": "WP03",
        },
    ]


def _patch_selection(monkeypatch, *, mission_dirs, blockers):
    # The pipeline binds these lazily from the envelope_seam surface, so the
    # seam module is where stubs go (not mission_state's underscore internals).
    monkeypatch.setattr(envelope_seam, "select_mission_dirs", lambda root, *, scan_root, mission: list(mission_dirs))
    monkeypatch.setattr(envelope_seam, "teamspace_audit_blockers", lambda root, *, scan_root, mission_dirs: list(blockers))


# ── happy path over a synthetic dual-shape corpus ─────────────────────────────


def test_build_plan_over_synthetic_dual_shape_corpus(tmp_path, monkeypatch):
    """SELECT→AUDIT→SCAN→IDENTITY→SYNTHESIZE over BOTH hybrid-SCAN shapes
    (§3.4) — a legacy (SYNTHESIZED) mission and a prefixed (ON_DISK) mission,
    same dual-shape guarantee the real dogfood fixtures used to exercise."""
    legacy_dir = _build_legacy_shape_mission(
        tmp_path,
        slug="087-plan-legacy-mission",
        mission_id=_PLAN_LEGACY_MISSION_ID,
        wp_specs=_LEGACY_WP_SPECS,
        lane_rows=_legacy_lane_rows(_PLAN_LEGACY_MISSION_ID, "087-plan-legacy-mission"),
    )
    prefixed_dir = _build_prefixed_shape_mission(
        tmp_path,
        slug="plan-prefixed-mission",
        mission_id=_PLAN_PREFIXED_MISSION_ID,
        wp_specs=_PREFIXED_WP_SPECS,
    )
    _patch_selection(monkeypatch, mission_dirs=[legacy_dir, prefixed_dir], blockers=[])

    plan = build_import_plan(tmp_path, mission=None, apply=False)

    assert not plan.is_empty
    assert plan.mission_count == 2
    assert plan.identity is not None and plan.identity.is_synthetic  # uninitialized dry-run
    counts = plan.event_type_counts()
    assert counts.get("MissionCreated") == 2
    assert counts.get("WPCreated", 0) >= 6
    assert counts.get("WPStatusChanged", 0) >= 1
    assert plan.total_events == sum(counts.values())


# ── empty / blocked branches ──────────────────────────────────────────────────


def test_empty_selection_yields_empty_plan(tmp_path, monkeypatch):
    _patch_selection(monkeypatch, mission_dirs=[], blockers=[])
    plan = build_import_plan(tmp_path, mission=None, apply=False)
    assert plan.is_empty
    assert plan.identity is None
    assert plan.envelopes == ()


def test_audit_blockers_raise_before_synthesis(tmp_path, monkeypatch):
    blockers = [{"mission_slug": "m-01", "message": "bad row"}]
    _patch_selection(monkeypatch, mission_dirs=[tmp_path / "m-01"], blockers=blockers)
    with pytest.raises(ImportAuditBlocked) as excinfo:
        build_import_plan(tmp_path, mission=None, apply=False)
    assert excinfo.value.blockers == blockers


# ── apply threads the real UUID (INV-5) ───────────────────────────────────────


def test_apply_plan_threads_the_real_uuid(tmp_path, monkeypatch):
    (tmp_path / ".kittify").mkdir()  # a real (uninitialized) checkout
    mission_dir = _build_legacy_shape_mission(
        tmp_path,
        slug="087-apply-uuid-mission",
        mission_id=_APPLY_UUID_MISSION_ID,
        wp_specs=_LEGACY_WP_SPECS,
        lane_rows=_legacy_lane_rows(_APPLY_UUID_MISSION_ID, "087-apply-uuid-mission"),
    )
    _patch_selection(monkeypatch, mission_dirs=[mission_dir], blockers=[])

    plan = build_import_plan(tmp_path, mission=None, apply=True)

    assert plan.identity is not None and plan.identity.is_synthetic is False
    assert plan.envelopes
    assert all(env["project_uuid"] == str(plan.identity.project_uuid) for env in plan.envelopes)


# ── describe_plan rendering ───────────────────────────────────────────────────


def test_describe_plan_lists_missions_and_breakdown(tmp_path, monkeypatch):
    mission_dir = _build_legacy_shape_mission(
        tmp_path,
        slug="087-describe-plan-mission",
        mission_id=_DESCRIBE_PLAN_MISSION_ID,
        wp_specs=_LEGACY_WP_SPECS,
        lane_rows=_legacy_lane_rows(_DESCRIBE_PLAN_MISSION_ID, "087-describe-plan-mission"),
    )
    _patch_selection(monkeypatch, mission_dirs=[mission_dir], blockers=[])
    plan = build_import_plan(tmp_path, mission=None, apply=False)

    lines = describe_plan(plan)
    text = "\n".join(lines)
    assert "087-describe-plan-mission" in text
    assert "MissionCreated" in text
    assert "event(s)" in text


def test_describe_plan_makes_skipped_wps_impossible_to_miss():
    """A scan with malformed-frontmatter skips must mark BOTH the summary line
    and the mission row — a skip can never read as clean success (B3, #2884)."""
    import uuid

    from specify_cli.sync.history_import.identity import ImportIdentity
    from specify_cli.sync.history_import.pipeline import ImportPlan
    from specify_cli.sync.history_import.scan import MissionScan, PrefixSource

    scan = MissionScan(
        mission_slug="m-skips",
        canonical_mission_id=None,
        mission_number=None,
        name="M Skips",
        mission_type="software-dev",
        purpose_tldr=None,
        purpose_context=None,
        target_branch="main",
        created_at=None,
        prefix_source=PrefixSource.SYNTHESIZED,
        work_packages=(),
        lane_transitions=(),
        skipped_wp_files=("WP07.md", "WP11.md"),
    )
    identity = ImportIdentity(
        project_uuid=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        project_slug="p",
        repo_slug="p",
        is_synthetic=True,
    )
    plan = ImportPlan(
        identity=identity,
        scans=(scan,),
        # canonical-event-exempt(exception-flow): minimal wire-envelope fixture for report rendering
        envelopes=({"event_id": "e0", "event_type": "MissionCreated"},),
    )

    text = "\n".join(describe_plan(plan))
    assert "2 WP file(s) SKIPPED" in text  # the summary line itself is marked
    assert "2 WPs SKIPPED (malformed frontmatter: WP07.md, WP11.md)" in text  # the mission row names them


def test_describe_plan_makes_skipped_event_rows_impossible_to_miss():
    """Same fail-loud contract as the WP-file skip, for the on-disk lifecycle
    prefix (#2884 finding A): a dropped WPCreated/MissionCreated row must mark
    BOTH the summary line and the mission row, never read as clean success."""
    import uuid

    from specify_cli.sync.history_import.identity import ImportIdentity
    from specify_cli.sync.history_import.pipeline import ImportPlan
    from specify_cli.sync.history_import.scan import MissionScan, PrefixSource

    scan = MissionScan(
        mission_slug="m-event-skips",
        canonical_mission_id=None,
        mission_number=None,
        name="M Event Skips",
        mission_type="software-dev",
        purpose_tldr=None,
        purpose_context=None,
        target_branch="main",
        created_at=None,
        prefix_source=PrefixSource.ON_DISK,
        work_packages=(),
        lane_transitions=(),
        skipped_event_rows=3,
    )
    identity = ImportIdentity(
        project_uuid=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        project_slug="p",
        repo_slug="p",
        is_synthetic=True,
    )
    plan = ImportPlan(
        identity=identity,
        scans=(scan,),
        # canonical-event-exempt(exception-flow): minimal wire-envelope fixture for report rendering
        envelopes=({"event_id": "e0", "event_type": "MissionCreated"},),
    )

    text = "\n".join(describe_plan(plan))
    assert "3 lifecycle row(s) SKIPPED" in text  # the summary line itself is marked
    assert "3 lifecycle row(s) SKIPPED (malformed on-disk prefix)" in text  # the mission row names it


def test_describe_empty_plan(tmp_path, monkeypatch):
    _patch_selection(monkeypatch, mission_dirs=[], blockers=[])
    plan = build_import_plan(tmp_path, mission=None, apply=False)
    assert describe_plan(plan) == ["No missions eligible for import."]


# ── apply_import: plan → provenance → preflight → upload ──────────────────────


class _AcceptingResponse:
    status_code = 200

    def json(self):
        return {"accepted": True, "event_count": 0, "reconciliation": {}}


def _accepting_poster(url, *, data, headers, timeout):
    return _AcceptingResponse()


def test_apply_import_uploads_every_envelope_under_the_real_uuid(tmp_path, monkeypatch):
    """The end-to-end proof (#2884): synthesize from a synthetic dual-shape
    corpus → the REAL ``validate_import_envelopes`` contract gate → the REAL
    ``build_teamspace_envelope`` output → upload against a stub receiver,
    asserting every envelope lands under the real project UUID. This is the
    only test that runs a real synthesized stream through the offline
    contract gate — an envelope-shape drift (e.g. ``schema_version`` off the
    pinned contract version) would fail here first."""
    (tmp_path / ".kittify").mkdir()  # a real (uninitialized) checkout → apply mints the UUID
    # The project records its own consent, in its own repo (#3030 FR-019/FR-028).
    # ``ensure_identity`` preserves ``sync:`` as a foreign section while minting the
    # uuid, so this is the real project-local grant rather than a stubbed resolver —
    # and it keeps the end-to-end proof end-to-end.
    (tmp_path / ".kittify" / "config.yaml").write_text("sync:\n  enabled: true\n", encoding="utf-8")
    legacy_dir = _build_legacy_shape_mission(
        tmp_path,
        slug="087-e2e-legacy-mission",
        mission_id=_E2E_LEGACY_MISSION_ID,
        wp_specs=_LEGACY_WP_SPECS,
        lane_rows=_legacy_lane_rows(_E2E_LEGACY_MISSION_ID, "087-e2e-legacy-mission"),
    )
    prefixed_dir = _build_prefixed_shape_mission(
        tmp_path,
        slug="e2e-prefixed-mission",
        mission_id=_E2E_PREFIXED_MISSION_ID,
        wp_specs=_PREFIXED_WP_SPECS,
    )
    _patch_selection(monkeypatch, mission_dirs=[legacy_dir, prefixed_dir], blockers=[])
    stub = StubReceiver()

    result = apply_import(
        tmp_path,
        mission=None,
        receiver=stub,
        server_url="http://teamspace.test",
        auth_token="tok",
        poster=_accepting_poster,
    )

    assert result.plan.identity is not None and result.plan.identity.is_synthetic is False  # INV-5
    assert result.report.ok
    assert result.report.success == result.plan.total_events
    assert set(stub.received_event_ids()) == {env["event_id"] for env in result.plan.envelopes}
    assert len(result.manifest) == result.plan.total_events
