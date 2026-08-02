"""Tests for ``spec-kitty sync import-history`` — WP-Y1 (#2262).

WP-Y1 is the command surface + mission selection + the fail-closed Team Kitty
audit gate. It reuses ``migration.mission_state`` helpers rather than
re-deriving them; envelope synthesis and the §3.6b pre-sync log re-drain land
in later slices, so ``--apply`` is an honest non-zero stub here (it must never
claim a materialize it cannot perform).

These tests drive the CLI wrapper only. The selection/audit authority stays in
``migration.mission_state`` and is monkeypatched at its seams, so the suite
needs no on-disk repo, no dossier, and no Team Kitty credentials.
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
from specify_cli.delivery.config import EventSyncConfig, Mode
from specify_cli.delivery.receivers import _TEAMSPACE_GATES

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
    target = SimpleNamespace(
        resolved_server_url="http://x",
        team_slug="team",
    )
    monkeypatch.setattr(
        sync_command,
        "_open_event_sync_runtime",
        lambda: SimpleNamespace(target=target, close=lambda: None),
    )
    monkeypatch.setattr(
        sync_command,
        "_load_event_sync_config",
        lambda: EventSyncConfig.from_mode(Mode.TEAMSPACE),
    )
    monkeypatch.setattr(
        sync_command,
        "_resolve_active_receiver",
        lambda *a, **k: SimpleNamespace(endpoint_url="http://x/batch", gates=lambda: ()),
    )
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
    from specify_cli.sync.history_import.upload import ImportProvenanceEntry

    plan = ImportPlan(identity=ident, scans=(scan,), envelopes=({"event_id": "e0", "event_type": "MissionCreated"},))
    manifest = [ImportProvenanceEntry(event_id="e0", event_type="MissionCreated", envelope_sha256="deadbeef")]
    return ApplyResult(plan=plan, manifest=manifest, report=report)


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
    # The provenance manifest is surfaced, not silently discarded (#2884).
    assert "Provenance: 1 envelope(s) hashed" in plain


# ── --apply: mode-authority fail-closed (P1, #2884) ──────────────────────────
#
# ``_resolve_history_import_receiver`` used to hardcode
# ``EventSyncConfig.from_mode(Mode.TEAMSPACE)``, discarding whatever mode the
# operator persisted via ``spec-kitty sync mode``. An operator on
# EXTERNAL_RECEIVER / LOCAL_RETENTION / OPT_OUT would still get their full
# mission history uploaded to the SaaS. These tests drive the real
# ``_load_event_sync_config`` seam per mode to pin the fix.


def _config_for_mode(mode: Mode) -> EventSyncConfig:
    if mode is Mode.EXTERNAL_RECEIVER:
        return EventSyncConfig.from_mode(mode, external_endpoint="https://x.example/e")
    return EventSyncConfig.from_mode(mode)


@pytest.mark.parametrize("mode", [Mode.EXTERNAL_RECEIVER, Mode.LOCAL_RETENTION, Mode.OPT_OUT])
def test_apply_refuses_when_persisted_mode_is_not_teamspace(tmp_path, monkeypatch, mode):
    """A non-TEAMSPACE persisted mode refuses the upload outright (exit 1),
    naming both the requirement and the operator's current mode."""
    _wire_apply_seams(monkeypatch, tmp_path)
    monkeypatch.setattr(
        sync_command, "_load_event_sync_config", lambda: _config_for_mode(mode)
    )
    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "requires event-sync mode TEAMSPACE" in plain
    assert mode.name in plain


def test_apply_proceeds_when_persisted_mode_is_teamspace(tmp_path, monkeypatch):
    """The counterpart: a persisted TEAMSPACE mode is honored and --apply proceeds."""
    import specify_cli.sync.history_import as history_import
    from specify_cli.sync.history_import import UploadReport

    _wire_apply_seams(monkeypatch, tmp_path)
    monkeypatch.setattr(
        sync_command, "_load_event_sync_config", lambda: EventSyncConfig.from_mode(Mode.TEAMSPACE)
    )
    canned = _canned_apply_result(UploadReport(success=1))
    monkeypatch.setattr(history_import, "apply_import", lambda *a, **k: canned)

    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 0


# ── --apply: real gate evaluation, not the zero-gate stub (P1, #2884) ────────
#
# ``_wire_apply_seams`` stubs the receiver with ``gates=lambda: ()`` — zero
# gates, so ``evaluate_gates`` can never block and the ``gate_decision.blocked``
# branch (and the receiver-missing / no-endpoint branch) is untestable by
# construction. These tests wire the REAL ``_TEAMSPACE_GATES`` tuple (or a
# missing/unconfigured receiver) so the fail-closed branches are genuinely
# exercised.


def _wire_apply_seams_real_gates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, saas_enabled: bool, team_slug: str
) -> None:
    """Like ``_wire_apply_seams`` but the receiver declares the real Team Kitty
    gate tuple, so ``evaluate_gates`` genuinely evaluates saas/private/auth."""
    monkeypatch.setattr(sync_command, "_event_sync_access_token", lambda: "tok")
    target = SimpleNamespace(resolved_server_url="http://x", team_slug=team_slug)
    monkeypatch.setattr(
        sync_command,
        "_open_event_sync_runtime",
        lambda: SimpleNamespace(target=target, close=lambda: None),
    )
    monkeypatch.setattr(
        sync_command,
        "_load_event_sync_config",
        lambda: EventSyncConfig.from_mode(Mode.TEAMSPACE),
    )
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: saas_enabled)
    monkeypatch.setattr(
        sync_command,
        "_resolve_active_receiver",
        lambda *a, **k: SimpleNamespace(
            endpoint_url="http://x/batch", gates=lambda: _TEAMSPACE_GATES
        ),
    )
    _patch_checkout(monkeypatch, tmp_path)


def test_apply_fails_closed_when_real_gates_are_unsatisfied(tmp_path, monkeypatch):
    """A GateContext short on saas_enabled and private_teamspace genuinely blocks
    through the real Team Kitty gate tuple, naming both unsatisfied gates."""
    _wire_apply_seams_real_gates(monkeypatch, tmp_path, saas_enabled=False, team_slug="")
    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "gated" in plain
    assert "saas_enabled" in plain
    assert "private_teamspace" in plain


def test_apply_proceeds_when_real_gates_are_satisfied(tmp_path, monkeypatch):
    """The same real gate tuple, fully satisfied, lets --apply proceed (exit 0) —
    the positive counterpart pinning that the real-gate wiring isn't itself
    broken in a way that always blocks."""
    import specify_cli.sync.history_import as history_import
    from specify_cli.sync.history_import import UploadReport

    _wire_apply_seams_real_gates(monkeypatch, tmp_path, saas_enabled=True, team_slug="team")
    canned = _canned_apply_result(UploadReport(success=1))
    monkeypatch.setattr(history_import, "apply_import", lambda *a, **k: canned)

    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 0


def test_apply_fails_closed_when_receiver_is_none(tmp_path, monkeypatch):
    """No resolvable receiver (e.g. an unrecognized target) refuses to upload."""
    _wire_apply_seams(monkeypatch, tmp_path)
    monkeypatch.setattr(sync_command, "_resolve_active_receiver", lambda *a, **k: None)
    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 1
    assert "not configured" in _strip_ansi(result.output)


def test_apply_fails_closed_when_endpoint_url_missing(tmp_path, monkeypatch):
    """A receiver resolved but with no ``endpoint_url`` also refuses to upload."""
    _wire_apply_seams(monkeypatch, tmp_path)
    monkeypatch.setattr(
        sync_command,
        "_resolve_active_receiver",
        lambda *a, **k: SimpleNamespace(endpoint_url="", gates=lambda: ()),
    )
    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 1
    assert "not configured" in _strip_ansi(result.output)


# ── --apply: the except branches (T3, #2884) ─────────────────────────────────


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


def test_apply_renders_envelope_contract_violation(tmp_path, monkeypatch):
    """The offline envelope contract gate (raised from apply_import) fails
    closed with a clear message and exit 1, not a traceback (#2884)."""
    from specify_cli.core.contract_gate import ContractViolationError

    exc = ContractViolationError(field="from_lane", context="envelope", reason="forbidden field 'from_lane' present")
    result = _invoke_apply_raising(tmp_path, monkeypatch, exc)
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Envelope contract violation" in plain
    assert "from_lane" in plain


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


def test_apply_treats_pending_as_a_failure(tmp_path, monkeypatch):
    """Pending is a final failure (exit 1), and the message is honest about why:
    import event ids are deterministic, so a re-run reports these events as
    duplicates and exits 0 whether or not the projection ever materialized
    them — the dashboard/projection is the authoritative check, not a re-run."""
    from specify_cli.sync.history_import import UploadReport

    report = UploadReport(success=1, pending=3)
    result = _invoke_apply_with_report(tmp_path, monkeypatch, report)
    assert result.exit_code == 1  # no durable retry record exists for direct delivery
    plain = _strip_ansi(result.output)
    assert "3 pending" in plain
    assert "remain pending" in plain
    assert "not confirmed" in plain
    assert "duplicates" in plain
    assert "dashboard" in plain
    assert "receiver issue" not in plain  # dropped: not always an operator-fixable cause
    assert "sync now" not in plain


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


# ── _render_upload_report: extracted rendering seam (P2 nit, C901 relief) ────
#
# ``_run_import_apply`` delegated its partial/pending/rejected tail to this
# helper so the branches are directly testable without wiring the whole
# --apply CLI path. Driven straight with synthetic ``UploadReport`` values.


def test_render_upload_report_partial_only(capsys):
    from specify_cli.sync.history_import import UploadReport

    report = UploadReport(success=2, partial=True, delivered_through_chunk=1, undelivered_event_count=5)
    ok = sync_command._render_upload_report(report)
    plain = _strip_ansi(capsys.readouterr().out)
    assert ok is False
    assert "Partial upload" in plain
    assert "5 event(s) not attempted" in plain


def test_render_upload_report_pending_only_points_at_the_projection(capsys):
    """No re-run suggestion, no 'receiver issue' framing: the honest message
    names the dedup-duplicate outcome and points at the dashboard/projection."""
    from specify_cli.sync.history_import import UploadReport

    report = UploadReport(success=1, pending=3)
    ok = sync_command._render_upload_report(report)
    plain = _strip_ansi(capsys.readouterr().out)
    assert ok is False
    assert "remain pending" in plain
    assert "duplicates" in plain
    assert "dashboard" in plain
    assert "receiver issue" not in plain


def test_render_upload_report_rejected_prints_samples(capsys):
    from specify_cli.sync.history_import import UploadReport

    report = UploadReport(success=1, rejected=2, rejected_samples=["e1: nope", "e2: bad payload"])
    ok = sync_command._render_upload_report(report)
    plain = _strip_ansi(capsys.readouterr().out)
    assert ok is False
    assert "e1: nope" in plain
    assert "e2: bad payload" in plain


def test_render_upload_report_all_clean_returns_true_and_prints_nothing(capsys):
    from specify_cli.sync.history_import import UploadReport

    report = UploadReport(success=5)
    ok = sync_command._render_upload_report(report)
    plain = capsys.readouterr().out
    assert ok is True
    assert plain == ""
