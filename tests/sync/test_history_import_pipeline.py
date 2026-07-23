"""Tests for the import-history orchestration — ``build_import_plan`` (#2262).

Drives the whole read-only pipeline (SELECT → AUDIT → SCAN → IDENTITY →
SYNTHESIZE) end to end: real fixtures for the happy path, patched migration
seams for the empty/blocked branches, and the apply path to prove the real
project UUID is threaded onto every envelope (INV-5).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import specify_cli.migration.mission_state as mission_state
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.sync.history_import.pipeline import (
    ImportAuditBlocked,
    apply_import,
    build_import_plan,
    describe_plan,
)

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS = _REPO_ROOT / "kitty-specs"
_LEGACY = _SPECS / "032-identity-aware-cli-event-sync"
_PREFIXED = _SPECS / "single-mission-surface-resolver-01KVGCE8"

_FIXTURES = _LEGACY.is_dir() and _PREFIXED.is_dir()


def _patch_selection(monkeypatch, *, mission_dirs, blockers):
    monkeypatch.setattr(mission_state, "_select_mission_dirs", lambda root, *, scan_root, mission: list(mission_dirs))
    monkeypatch.setattr(mission_state, "_teamspace_audit_blockers", lambda root, *, scan_root, mission_dirs: list(blockers))


# ── happy path over real fixtures ─────────────────────────────────────────────


@pytest.mark.skipif(not _FIXTURES, reason="fixtures not present")
def test_build_plan_over_real_fixtures(tmp_path, monkeypatch):
    _patch_selection(monkeypatch, mission_dirs=[_LEGACY, _PREFIXED], blockers=[])

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


@pytest.mark.skipif(not _FIXTURES, reason="fixtures not present")
def test_apply_plan_threads_the_real_uuid(tmp_path, monkeypatch):
    (tmp_path / ".kittify").mkdir()  # a real (uninitialized) checkout
    _patch_selection(monkeypatch, mission_dirs=[_LEGACY], blockers=[])

    plan = build_import_plan(tmp_path, mission=None, apply=True)

    assert plan.identity is not None and plan.identity.is_synthetic is False
    assert plan.envelopes
    assert all(env["project_uuid"] == str(plan.identity.project_uuid) for env in plan.envelopes)


# ── describe_plan rendering ───────────────────────────────────────────────────


@pytest.mark.skipif(not _FIXTURES, reason="fixtures not present")
def test_describe_plan_lists_missions_and_breakdown(tmp_path, monkeypatch):
    _patch_selection(monkeypatch, mission_dirs=[_LEGACY], blockers=[])
    plan = build_import_plan(tmp_path, mission=None, apply=False)

    lines = describe_plan(plan)
    text = "\n".join(lines)
    assert "032-identity-aware-cli-event-sync" in text
    assert "MissionCreated" in text
    assert "event(s)" in text


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


@pytest.mark.skipif(not _FIXTURES, reason="fixtures not present")
def test_apply_import_uploads_every_envelope_under_the_real_uuid(tmp_path, monkeypatch):
    (tmp_path / ".kittify").mkdir()  # a real (uninitialized) checkout → apply mints the UUID
    _patch_selection(monkeypatch, mission_dirs=[_LEGACY], blockers=[])
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
