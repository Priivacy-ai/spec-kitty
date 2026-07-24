"""Tests for ``spec-kitty sync import-history`` — WP-Y1 (#2262).

WP-Y1 is the command surface + mission selection + the fail-closed TeamSpace
audit gate. It reuses ``migration.mission_state`` helpers rather than
re-deriving them; envelope synthesis and the §3.6b pre-sync log re-drain land
in later slices, so ``--apply`` is an honest non-zero stub here (it must never
claim a materialize it cannot perform).

These tests drive the CLI wrapper only. The selection/audit authority stays in
``migration.mission_state`` and is monkeypatched at its seams, so the suite
needs no on-disk repo, no dossier, and no TeamSpace credentials.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_command
from specify_cli.cli.commands.sync import app

pytestmark = pytest.mark.fast

runner = CliRunner()


# ── seam helpers ─────────────────────────────────────────────────────────────


def _patch_checkout(monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    """Point the command's active-checkout resolver at a fixed repo root."""
    monkeypatch.setattr(
        sync_command,
        "_require_active_checkout",
        lambda: SimpleNamespace(repo_root=repo_root),
    )


def _patch_selection(
    monkeypatch: pytest.MonkeyPatch,
    *,
    mission_dirs: list[Path],
    blockers: list[dict[str, object]],
) -> None:
    """Stub the two migration seams the command reuses.

    Patched on ``migration.envelope_seam`` (the deliberate public surface) —
    the pipeline's lazy ``from specify_cli.migration.envelope_seam import ...``
    binds to the stubs at call time.
    """
    import specify_cli.migration.envelope_seam as envelope_seam

    monkeypatch.setattr(
        envelope_seam,
        "select_mission_dirs",
        lambda repo_root, *, scan_root, mission: list(mission_dirs),
    )
    monkeypatch.setattr(
        envelope_seam,
        "teamspace_audit_blockers",
        lambda repo_root, *, scan_root, mission_dirs: list(blockers),
    )


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ── wiring ───────────────────────────────────────────────────────────────────


def test_command_is_wired_with_its_flags():
    """``import-history --help`` renders and advertises its three flags."""
    result = runner.invoke(app, ["import-history", "--help"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.output)
    assert "--apply" in plain
    assert "--dry-run" in plain
    assert "--mission" in plain


def test_apply_and_dry_run_are_mutually_exclusive():
    """Both flags at once is a usage error (exit 2), caught before any I/O."""
    result = runner.invoke(app, ["import-history", "--apply", "--dry-run"])
    assert result.exit_code == 2
    assert "mutually exclusive" in _strip_ansi(result.output)


# ── stage 1: selection ───────────────────────────────────────────────────────


def test_no_missions_found_exits_zero(tmp_path, monkeypatch):
    _patch_checkout(monkeypatch, tmp_path)
    _patch_selection(monkeypatch, mission_dirs=[], blockers=[])
    result = runner.invoke(app, ["import-history"])
    assert result.exit_code == 0
    assert "No missions found" in _strip_ansi(result.output)


def test_selection_repair_error_exits_one(tmp_path, monkeypatch):
    """A ``MissionStateRepairError`` from selection fails closed (exit 1)."""
    import specify_cli.migration.envelope_seam as envelope_seam
    import specify_cli.migration.mission_state as mission_state

    _patch_checkout(monkeypatch, tmp_path)

    def _boom(repo_root, *, scan_root, mission):
        raise mission_state.MissionStateRepairError("selector could not resolve mission handle")

    monkeypatch.setattr(envelope_seam, "select_mission_dirs", _boom)
    result = runner.invoke(app, ["import-history", "--mission", "does-not-resolve"])
    assert result.exit_code == 1
    assert "selector could not resolve mission handle" in _strip_ansi(result.output)


# ── stage 2: fail-closed audit gate ──────────────────────────────────────────


def test_clean_missions_are_previewed_on_dry_run(tmp_path, monkeypatch):
    dirs = [tmp_path / "demo-mission-01AAAA", tmp_path / "demo-mission-01BBBB"]
    _patch_checkout(monkeypatch, tmp_path)
    _patch_selection(monkeypatch, mission_dirs=dirs, blockers=[])

    result = runner.invoke(app, ["import-history"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.output)
    # The dry-run now previews the synthesized plan, not just the selection.
    assert "2 mission(s)" in plain
    assert "demo-mission-01AAAA" in plain
    assert "demo-mission-01BBBB" in plain
    # A MissionCreated is synthesized per mission even with nothing on disk.
    assert "MissionCreated" in plain
    # Dry-run resolves the synthetic offline identity and uploads nothing.
    assert "synthetic offline id" in plain
    assert "nothing uploaded" in plain


def test_audit_blockers_block_import_and_name_the_finding(tmp_path, monkeypatch):
    dirs = [tmp_path / "demo-mission-01CCCC"]
    blockers = [
        {
            "mission_slug": "demo-mission-01CCCC",
            "artifact_path": "spec.md",
            "message": "spec.md failed dossier schema validation",
            "finding_code": "SCHEMA_INVALID",
        }
    ]
    _patch_checkout(monkeypatch, tmp_path)
    _patch_selection(monkeypatch, mission_dirs=dirs, blockers=blockers)

    result = runner.invoke(app, ["import-history"])
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Import blocked" in plain
    # The blocker is named (mission + message), not dumped as a raw dict.
    assert "demo-mission-01CCCC" in plain
    assert "spec.md failed dossier schema validation" in plain
    assert "{'mission_slug'" not in plain


# ── --apply: authed upload path (WP-Y5) ──────────────────────────────────────


def test_apply_fails_closed_when_unauthenticated(monkeypatch):
    """--apply refuses to upload without an access token (fail-closed)."""
    monkeypatch.setattr(sync_command, "_event_sync_access_token", lambda: "")
    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 1
    assert "Not authenticated" in _strip_ansi(result.output)


def _wire_apply_seams(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Wire the auth/config/receiver seams so --apply reaches apply_import."""
    monkeypatch.setattr(sync_command, "_event_sync_access_token", lambda: "tok")
    monkeypatch.setattr(sync_command, "_open_event_sync_runtime", lambda: SimpleNamespace(target=object()))
    monkeypatch.setattr(
        sync_command,
        "_load_event_sync_config",
        lambda: SimpleNamespace(resolve_runtime_target=lambda: SimpleNamespace(resolved_server_url="http://x")),
    )
    monkeypatch.setattr(sync_command, "_resolve_active_receiver", lambda *a, **k: SimpleNamespace(endpoint_url="http://x/batch"))
    _patch_checkout(monkeypatch, tmp_path)


def _canned_apply_result(report):
    """A one-mission, one-envelope ApplyResult carrying the given report."""
    from specify_cli.sync.history_import import ApplyResult, ImportIdentity, ImportPlan
    from specify_cli.sync.history_import.scan import MissionScan, PrefixSource

    scan = MissionScan(
        mission_slug="m-1",
        canonical_mission_id=None,
        mission_number=None,
        name="M One",
        mission_type="software-dev",
        purpose_tldr=None,
        purpose_context=None,
        target_branch="main",
        created_at=None,
        prefix_source=PrefixSource.SYNTHESIZED,
        work_packages=(),
        lane_transitions=(),
    )
    ident = ImportIdentity(
        project_uuid=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        project_slug="m-1",
        repo_slug="m-1",
        is_synthetic=False,
    )
    plan = ImportPlan(identity=ident, scans=(scan,), envelopes=({"event_id": "e0", "event_type": "MissionCreated"},))
    return ApplyResult(plan=plan, manifest=[], report=report)


def test_apply_uploads_and_reports_on_success(tmp_path, monkeypatch):
    """The wired --apply resolves the authed receiver, runs apply_import, and
    reports the upload tally (exit 0). apply_import is stubbed with a canned
    result here; its real behavior is covered in the pipeline/upload suites."""
    import specify_cli.sync.history_import as history_import
    from specify_cli.sync.history_import import UploadReport

    _wire_apply_seams(monkeypatch, tmp_path)
    canned = _canned_apply_result(UploadReport(success=1))
    monkeypatch.setattr(history_import, "apply_import", lambda *a, **k: canned)

    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.output)
    assert "Imported:" in plain
    assert "1 created" in plain


# ── --apply: the five except branches (T3, #2884) ─────────────────────────────


def _invoke_apply_raising(tmp_path, monkeypatch, exc: BaseException):
    """Wire the seams, make apply_import raise *exc*, invoke --apply."""
    import specify_cli.sync.history_import as history_import

    _wire_apply_seams(monkeypatch, tmp_path)

    def _boom(*args, **kwargs):
        raise exc

    monkeypatch.setattr(history_import, "apply_import", _boom)
    return runner.invoke(app, ["import-history", "--apply"])


def test_apply_renders_audit_blockers(tmp_path, monkeypatch):
    from specify_cli.sync.history_import import ImportAuditBlocked

    exc = ImportAuditBlocked([{"mission_slug": "m-bad", "message": "spec.md failed schema validation"}])
    result = _invoke_apply_raising(tmp_path, monkeypatch, exc)
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Import blocked" in plain
    assert "m-bad" in plain and "spec.md failed schema validation" in plain


def test_apply_renders_preflight_rejection(tmp_path, monkeypatch):
    from specify_cli.sync.history_import import PreflightRejected

    result = _invoke_apply_raising(tmp_path, monkeypatch, PreflightRejected({"reconciliation": {"reason": "bad shape"}}))
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Server preflight rejected the import" in plain
    assert "bad shape" in plain


def test_apply_renders_identity_error(tmp_path, monkeypatch):
    from specify_cli.sync.history_import import ImportIdentityError

    result = _invoke_apply_raising(tmp_path, monkeypatch, ImportIdentityError("no persisted project UUID"))
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Identity error" in plain
    assert "no persisted project UUID" in plain


def test_apply_renders_mission_scan_error(tmp_path, monkeypatch):
    from specify_cli.sync.history_import import MissionScanError

    result = _invoke_apply_raising(tmp_path, monkeypatch, MissionScanError("m-corrupt", "corrupt status log: bad row"))
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Error:" in plain
    assert "m-corrupt" in plain and "corrupt status log" in plain


def test_apply_renders_mission_state_repair_error(tmp_path, monkeypatch):
    from specify_cli.migration.mission_state import MissionStateRepairError

    result = _invoke_apply_raising(tmp_path, monkeypatch, MissionStateRepairError("Mission not found: 'nope'"))
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Error:" in plain
    assert "Mission not found" in plain


# ── --apply: report-state rendering (rejected / pending / partial) ────────────


def _invoke_apply_with_report(tmp_path, monkeypatch, report):
    import specify_cli.sync.history_import as history_import

    _wire_apply_seams(monkeypatch, tmp_path)
    canned = _canned_apply_result(report)
    monkeypatch.setattr(history_import, "apply_import", lambda *a, **k: canned)
    return runner.invoke(app, ["import-history", "--apply"])


def test_apply_renders_rejected_tally_and_samples(tmp_path, monkeypatch):
    from specify_cli.sync.history_import import UploadReport

    report = UploadReport(success=1, rejected=2, rejected_samples=["e1: nope", "e2: bad payload"])
    result = _invoke_apply_with_report(tmp_path, monkeypatch, report)
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "2 rejected" in plain
    assert "e1: nope" in plain and "e2: bad payload" in plain
    assert "not attempted" not in plain  # total failure is NOT the partial state


def test_apply_renders_pending_tally_as_non_final(tmp_path, monkeypatch):
    from specify_cli.sync.history_import import UploadReport

    report = UploadReport(success=1, pending=3)
    result = _invoke_apply_with_report(tmp_path, monkeypatch, report)
    assert result.exit_code == 0  # pending is non-final, not a failure
    plain = _strip_ansi(result.output)
    assert "3 pending" in plain
    assert "queued (pending)" in plain
    assert "not yet" in plain  # explicitly distinct from confirmed success


def test_apply_renders_partial_upload_as_distinct_state(tmp_path, monkeypatch):
    """B1: a mid-run delivery failure renders the explicit partial state — a
    safe ordered prefix was delivered, N events never attempted — distinct
    from success and from total failure, and exits non-zero."""
    from specify_cli.sync.history_import import UploadReport

    report = UploadReport(
        success=2,
        rejected=1,
        rejected_samples=["e2: nope"],
        partial=True,
        delivered_through_chunk=1,
        undelivered_event_count=5,
    )
    result = _invoke_apply_with_report(tmp_path, monkeypatch, report)
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Partial upload" in plain
    assert "safe ordered" in plain and "prefix" in plain
    assert "5 event(s) not attempted" in plain
    assert "e2: nope" in plain
