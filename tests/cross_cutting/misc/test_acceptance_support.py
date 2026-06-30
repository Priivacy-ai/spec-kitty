from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import acceptance as acc
from specify_cli import app as cli_app
from specify_cli.task_utils import support as th

pytestmark = [pytest.mark.integration]

ACCEPTANCE_MODE_CHECKLIST = "checklist"
runner = CliRunner()


def _write_acceptance_meta(feature_repo: Path, mission_slug: str) -> None:
    feature_dir = feature_repo / "kitty-specs" / mission_slug
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01KNXQS9ATWWFXS3K5ZJ9E5008",
                "mission_slug": mission_slug,
                "mission_number": 1,
                "slug": mission_slug,
                "friendly_name": "Demo Feature",
                "mission_type": "software-dev",
                "target_branch": "main",
                "created_at": "2026-05-27T00:00:00+00:00",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _approve_wp(feature_repo: Path, mission_slug: str, wp_id: str) -> None:
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.models import ReviewResult

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    for lane in ("claimed", "in_progress", "for_review", "in_review"):
        emit_status_transition(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            to_lane=lane,
            actor="test-agent",
            repo_root=feature_repo,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )
    emit_status_transition(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        to_lane="approved",
        actor="reviewer-agent",
        evidence={
            "review": {
                "reviewer": "reviewer-agent",
                "verdict": "approved",
                "reference": f"review:{wp_id}",
            }
        },
        review_result=ReviewResult(
            reviewer="reviewer-agent",
            verdict="approved",
            reference=f"review:{wp_id}",
        ),
        repo_root=feature_repo,
        ensure_sync_daemon=False,
        sync_dossier=False,
    )


def _force_lane(feature_repo: Path, mission_slug: str, wp_id: str, to_lane: str) -> None:
    """Force ``wp_id`` into ``to_lane`` via the canonical status engine.

    Replaces the retired standalone ``tasks update --force`` seed path. A forced
    transition (actor + reason) bypasses edge/guard checks exactly as the
    standalone CLI's ``--force`` flag did, so the lane outcome is identical while
    the engine — not the standalone surface — does the writing.
    """
    from specify_cli.status.emit import emit_status_transition

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    emit_status_transition(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        to_lane=to_lane,
        actor="test-agent",
        force=True,
        reason="test fixture seed",
        repo_root=feature_repo,
        ensure_sync_daemon=False,
        sync_dossier=False,
    )


def test_collect_feature_summary_reports_metadata_issue(feature_repo: Path, mission_slug: str) -> None:
    # WP files now live in flat tasks/ directory
    wp_path = feature_repo / "kitty-specs" / mission_slug / "tasks" / "WP01.md"
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    # Move WP01 into an active lane (in_progress) via the canonical engine.
    _force_lane(feature_repo, mission_slug, "WP01", "in_progress")

    summary = acc.collect_feature_summary(feature_repo, mission_slug)
    assert any("missing assignee" in issue for issue in summary.metadata_issues)


def test_detect_mission_slug_prefers_explicit(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Auto-detection removed; must pass explicit_feature
    assert acc.detect_mission_slug(feature_repo, explicit_feature=mission_slug) == mission_slug


def test_detect_mission_slug_raises_without_explicit(feature_repo: Path, mission_slug: str) -> None:
    # Without explicit_feature, must raise AcceptanceError (auto-detection removed)
    with pytest.raises(acc.AcceptanceError, match="Mission slug is required"):
        acc.detect_mission_slug(feature_repo)


def test_perform_acceptance_without_commit(feature_repo: Path, mission_slug: str) -> None:
    from tests.utils import run

    _force_lane(feature_repo, mission_slug, "WP01", "in_progress")
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)
    _force_lane(feature_repo, mission_slug, "WP01", "done")

    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert summary.lanes["planned"] == []
    assert summary.lanes.get("doing", summary.lanes.get("in_progress", [])) == []
    assert summary.lanes["for_review"] == []
    assert summary.metadata_issues == []
    assert summary.activity_issues == []

    result = acc.perform_acceptance(
        summary, mode=ACCEPTANCE_MODE_CHECKLIST, actor="Tester", auto_commit=False
    )
    payload = result.to_dict()
    assert payload["accepted_by"] == "Tester"
    assert payload["mode"] == ACCEPTANCE_MODE_CHECKLIST


def test_accept_command_reports_approved_wps_without_closing(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import specify_cli.status.emit as status_emit
    from tests.utils import run, write_wp

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    write_wp(feature_repo, mission_slug, "planned", "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add second WP and meta"], cwd=feature_repo)

    _approve_wp(feature_repo, mission_slug, "WP01")
    _approve_wp(feature_repo, mission_slug, "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Approve WPs"], cwd=feature_repo)
    # Accept commits the acceptance meta through the protected-primary router
    # (01KVMBD6). A flattened mission (no coordination_branch) commits to the
    # current ref; 'main' is protected and would be refused, so run accept from
    # the mission branch (kitty/mission-<slug> is never protected) — mirrors the
    # sibling diagnose tests and real usage. The local-only auth gate does not
    # fire in CI (remote-less, SaaS-config-less fixture).
    run(["git", "checkout", "-b", f"kitty/mission-{mission_slug}"], cwd=feature_repo)

    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--mode",
            "local",
            "--actor",
            "tester",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "to_lane in {'approved', 'done'} requires evidence" not in result.output
    payload = json.loads(result.output)
    assert payload["accepted_wps"] == ["WP01", "WP02"]
    assert payload["approved_wps"] == ["WP01", "WP02"]
    assert payload["done_wps"] == []
    assert payload["merge_pending_wps"] == ["WP01", "WP02"]
    assert payload["summary"]["lanes"]["approved"] == ["WP01", "WP02"]
    assert payload["summary"]["lanes"]["done"] == []

    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert summary.lanes["approved"] == ["WP01", "WP02"]
    assert summary.lanes["done"] == []


def test_accept_diagnose_json_reports_missing_events_bootstrap_issue(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.utils import run

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    _write_acceptance_meta(feature_repo, mission_slug)
    (feature_dir / "status.events.jsonl").unlink()
    run(["git", "add", "-A"], cwd=feature_repo)
    run(["git", "commit", "-m", "Add meta and remove status event log"], cwd=feature_repo)

    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--diagnose",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["diagnose"] is True
    assert any("status.events.jsonl" in issue for issue in payload["activity_issues"])
    assert any("finalize-tasks" in issue for issue in payload["activity_issues"])
    assert "Traceback" not in result.output


def test_accept_no_commit_reports_merge_pending_without_mutation(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import specify_cli.status.emit as status_emit
    from specify_cli.status.store import read_events
    from tests.utils import run

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add meta"], cwd=feature_repo)
    _approve_wp(feature_repo, mission_slug, "WP01")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Approve WP01"], cwd=feature_repo)

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    before_events = len(read_events(feature_dir))
    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--mode",
            "local",
            "--actor",
            "tester",
            "--json",
            "--no-commit",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["accepted_wps"] == ["WP01"]
    assert payload["approved_wps"] == ["WP01"]
    assert payload["done_wps"] == []
    assert payload["merge_pending_wps"] == ["WP01"]
    assert len(read_events(feature_dir)) == before_events
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert summary.lanes["approved"] == ["WP01"]


def test_accept_diagnose_json_reports_skipped_checks_without_mutation(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.lane_test_utils import write_single_lane_manifest
    from tests.utils import run

    _write_acceptance_meta(feature_repo, mission_slug)
    feature_dir = feature_repo / "kitty-specs" / mission_slug
    write_single_lane_manifest(feature_dir)
    run(["git", "branch", "-M", "main"], cwd=feature_repo)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add lane metadata"], cwd=feature_repo)
    run(["git", "checkout", "-b", f"kitty/mission-{mission_slug}"], cwd=feature_repo)

    before_meta = (feature_dir / "meta.json").read_text(encoding="utf-8")
    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--diagnose",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["diagnose"] is True
    assert any(item["check"] == "acceptance_matrix" for item in payload["blocked_checks"])
    assert any(item["check"] == "negative_invariants" for item in payload["skipped_checks"])
    assert any("acceptance-matrix.json" in item for item in payload["recommended_fix_order"])
    assert (feature_dir / "meta.json").read_text(encoding="utf-8") == before_meta
    assert "acceptance-matrix.json" not in {path.name for path in feature_dir.iterdir()}
    status = run(["git", "status", "--short"], cwd=feature_repo)
    assert status.stdout == ""


def test_accept_diagnose_json_blocks_corrupt_lanes_json(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.lane_test_utils import write_single_lane_manifest
    from tests.utils import run

    _write_acceptance_meta(feature_repo, mission_slug)
    feature_dir = feature_repo / "kitty-specs" / mission_slug
    write_single_lane_manifest(feature_dir)
    (feature_dir / "lanes.json").write_text("{not-json", encoding="utf-8")
    run(["git", "branch", "-M", "main"], cwd=feature_repo)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add corrupt lane metadata"], cwd=feature_repo)
    run(["git", "checkout", "-b", f"kitty/mission-{mission_slug}"], cwd=feature_repo)

    before_meta = (feature_dir / "meta.json").read_text(encoding="utf-8")
    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--diagnose",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert any(item["check"] == "lanes_manifest" for item in payload["blocked_checks"])
    assert any(item["check"] == "acceptance_matrix_presence" for item in payload["skipped_checks"])
    assert any("lanes.json" in item for item in payload["recommended_fix_order"])
    assert (feature_dir / "meta.json").read_text(encoding="utf-8") == before_meta
    status = run(["git", "status", "--short"], cwd=feature_repo)
    assert status.stdout == ""


def test_accept_diagnose_does_not_mutate_matrix_metadata_or_events(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import specify_cli.status.emit as status_emit
    from specify_cli.acceptance.matrix import AcceptanceMatrix, NegativeInvariant, write_acceptance_matrix
    from specify_cli.status.store import read_events
    from tests.lane_test_utils import write_single_lane_manifest
    from tests.utils import run

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    feature_dir = feature_repo / "kitty-specs" / mission_slug
    write_single_lane_manifest(feature_dir)
    write_acceptance_matrix(
        feature_dir,
        AcceptanceMatrix(
            mission_slug=mission_slug,
            negative_invariants=[
                NegativeInvariant(
                    "NI-01",
                    "Legacy route stays absent",
                    "grep_absence",
                    verification_command="legacy_route_that_does_not_exist",
                )
            ],
        ),
    )
    _approve_wp(feature_repo, mission_slug, "WP01")
    run(["git", "branch", "-M", "main"], cwd=feature_repo)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Prepare accepted lane mission"], cwd=feature_repo)
    run(["git", "checkout", "-b", f"kitty/mission-{mission_slug}"], cwd=feature_repo)

    matrix_path = feature_dir / "acceptance-matrix.json"
    before_matrix = matrix_path.read_text(encoding="utf-8")
    before_meta = (feature_dir / "meta.json").read_text(encoding="utf-8")
    before_events = len(read_events(feature_dir))

    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--diagnose",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["diagnose"] is True
    assert payload["ok"] is False
    assert any(item["check"] == "negative_invariants" for item in payload["skipped_checks"])
    assert any("Acceptance matrix verdict is 'pending'" in item["detail"] for item in payload["failed_checks"])
    assert matrix_path.read_text(encoding="utf-8") == before_matrix
    assert (feature_dir / "meta.json").read_text(encoding="utf-8") == before_meta
    assert len(read_events(feature_dir)) == before_events
    status = run(["git", "status", "--short"], cwd=feature_repo)
    assert status.stdout == ""


def test_accept_diagnose_does_not_execute_custom_negative_invariants(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import specify_cli.status.emit as status_emit
    from specify_cli.acceptance.matrix import AcceptanceMatrix, NegativeInvariant, write_acceptance_matrix
    from tests.lane_test_utils import write_single_lane_manifest
    from tests.utils import run

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    feature_dir = feature_repo / "kitty-specs" / mission_slug
    side_effect_path = feature_repo / "diagnose-side-effect.txt"
    write_single_lane_manifest(feature_dir)
    command = (
        f"{shlex.quote(sys.executable)} -c "
        "\"from pathlib import Path; Path('diagnose-side-effect.txt').write_text('mutated')\""
    )
    write_acceptance_matrix(
        feature_dir,
        AcceptanceMatrix(
            mission_slug=mission_slug,
            negative_invariants=[
                NegativeInvariant(
                    "NI-01",
                    "Diagnostic command must not run",
                    "custom_command",
                    verification_command=command,
                )
            ],
        ),
    )
    _approve_wp(feature_repo, mission_slug, "WP01")
    run(["git", "branch", "-M", "main"], cwd=feature_repo)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Prepare custom invariant mission"], cwd=feature_repo)
    run(["git", "checkout", "-b", f"kitty/mission-{mission_slug}"], cwd=feature_repo)

    before_matrix = (feature_dir / "acceptance-matrix.json").read_text(encoding="utf-8")
    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--diagnose",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert any(item["check"] == "negative_invariants" for item in payload["skipped_checks"])
    assert not side_effect_path.exists()
    assert (feature_dir / "acceptance-matrix.json").read_text(encoding="utf-8") == before_matrix
    status = run(["git", "status", "--short"], cwd=feature_repo)
    assert status.stdout == ""


def test_accept_does_not_require_done_evidence_for_approved_wp(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accept records mission acceptance; merge owns approved -> done closure."""
    import specify_cli.status.emit as status_emit
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.store import read_events
    from tests.utils import run

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add meta"], cwd=feature_repo)

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    for lane in ("claimed", "in_progress", "for_review", "in_review"):
        emit_status_transition(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id="WP01",
            to_lane=lane,
            actor="test-agent",
            repo_root=feature_repo,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )
    emit_status_transition(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id="WP01",
        to_lane="approved",
        actor="force-user",
        force=True,
        reason="Expedited approval without review",
        repo_root=feature_repo,
        ensure_sync_daemon=False,
        sync_dossier=False,
    )
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Force-approve WP01"], cwd=feature_repo)
    # Run accept from the mission branch: a flattened mission's acceptance commit
    # is refused on the protected primary 'main' (01KVMBD6). kitty/mission-<slug>
    # is never protected. Mirrors the sibling tests; the auth gate does not fire
    # in CI (remote-less fixture).
    run(["git", "checkout", "-b", f"kitty/mission-{mission_slug}"], cwd=feature_repo)

    before_events = len(read_events(feature_dir))
    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        ["accept", "--mission", mission_slug, "--mode", "local", "--actor", "tester", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["accepted_wps"] == ["WP01"]
    assert payload["approved_wps"] == ["WP01"]
    assert payload["done_wps"] == []
    assert payload["merge_pending_wps"] == ["WP01"]
    assert len(read_events(feature_dir)) == before_events
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert summary.lanes["approved"] == ["WP01"]


def test_accept_protected_branch_materialize_then_retry(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T018 / WP04 / FR-001 / FR-003 / FR-009 — L2 rewrite.

    On a protected primary, ``_commit_acceptance_meta`` (the internal commit
    seam) must materialize-then-retry through ``commit_for_mission``, not
    raise-and-exit.  Tested at the function level to isolate the seam from
    pre-existing CLI resolver issues that affect the whole test class.

    Assertions:
    1. ``assert_not_protected_branch`` is NOT the decision gate in ``accept.py``
       (FR-009 provenance: the decision flows through ``ProtectionPolicy.resolve``).
    2. ``commit_for_mission`` is called from ``_commit_acceptance_meta`` when a
       protected policy is active — the materialize-then-retry path is live.
    3. The spy result is honoured: ``accept_commit`` is recorded from the
       ``CommitRouterResult.commit_hash`` (no raise/exit from the protection guard).
    4. Mutation-verification comment: reverting to the old raise-and-exit (re-adding
       ``assert_not_protected_branch → raise`` in ``_commit_acceptance_meta``) would
       make assertion 2 fail because the spy would never be reached.
    """
    from specify_cli.acceptance import AcceptanceSummary, _commit_acceptance_meta  # type: ignore[attr-defined]
    from specify_cli.coordination.commit_router import CommitRouterResult
    from specify_cli.git.protection_policy import ProtectionPolicy
    from specify_cli.task_utils import LANES
    from tests.utils import run

    # --- Setup: create meta.json and commit it so record_acceptance can write ---
    _write_acceptance_meta(feature_repo, mission_slug)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add meta for acceptance unit test"], cwd=feature_repo)

    feature_dir = feature_repo / "kitty-specs" / mission_slug

    # Build an ok summary (no outstanding issues).
    full_lanes = {lane: [] for lane in LANES}
    full_lanes["approved"] = ["WP01"]
    summary = AcceptanceSummary(
        feature=mission_slug,
        repo_root=feature_repo,
        feature_dir=feature_dir,
        tasks_dir=feature_dir / "tasks",
        branch="main",
        worktree_root=feature_repo,
        primary_repo_root=feature_repo,
        lanes=full_lanes,
        work_packages=[],
        metadata_issues=[],
        activity_issues=[],
        unchecked_tasks=[],
        needs_clarification=[],
        missing_artifacts=[],
        optional_missing=[],
        git_dirty=[],
        path_violations=[],
        warnings=[],
    )

    # --- FR-009 provenance assertion ---
    # assert_not_protected_branch must NOT be the decision gate in accept.py.
    import specify_cli.cli.commands.accept as _accept_mod
    assert not hasattr(_accept_mod, "assert_not_protected_branch"), (
        "assert_not_protected_branch must NOT be the decision gate in accept.py "
        "(FR-009 provenance: protection flows through ProtectionPolicy, "
        "not the old assert_not_protected_branch surface)"
    )

    # --- FR-009: protection decision flows through ProtectionPolicy.resolve ---
    protected_policy = ProtectionPolicy(
        protected_branches=frozenset({"main"}),
        operator_hatch_active=False,
    )
    resolve_call_count: list[str] = []

    def _spy_resolve(cls: type, repo_root: Path) -> ProtectionPolicy:  # type: ignore[misc]
        resolve_call_count.append("called")
        return protected_policy

    monkeypatch.setattr(
        ProtectionPolicy,
        "resolve",
        classmethod(_spy_resolve),
    )

    # --- Spy: track that commit_for_mission is called (materialize-then-retry) ---
    commit_calls: list[dict[str, object]] = []

    def _spy_commit_for_mission(  # type: ignore[no-untyped-def]
        *,
        repo_root: Path,
        mission_slug: str,
        files: tuple[Path, ...],
        message: str,
        policy: object,
        **kwargs: object,
    ) -> CommitRouterResult:
        commit_calls.append({"message": message, "files": list(files)})
        return CommitRouterResult(
            status="committed",
            placement_ref="kitty/coord-ref",
            commit_hash="abc1234deadbeef0",
        )

    monkeypatch.setattr(
        "specify_cli.coordination.commit_router.commit_for_mission",
        _spy_commit_for_mission,
    )

    # --- Execute: call the acceptance commit seam directly ---
    parent_commit, accept_commit, commit_created = _commit_acceptance_meta(
        summary, actor_name="tester", mode="local"
    )

    # 1. ProtectionPolicy.resolve was called — provenance is through the policy,
    #    not a direct re-read (FR-009 / FR-007).
    assert len(resolve_call_count) >= 1, (
        "ProtectionPolicy.resolve must be called by _commit_acceptance_meta "
        "for the protection decision (FR-009 provenance)"
    )

    # 2. commit_for_mission was invoked — materialize-then-retry path is live.
    assert len(commit_calls) >= 1, (
        "commit_for_mission must be called by _commit_acceptance_meta when the "
        "primary is protected; the old raise-and-exit deadlock path is removed (T016). "
        "Mutation-verify: re-adding assert_not_protected_branch→raise in "
        "_commit_acceptance_meta would cause this assertion to fail."
    )

    # 3. The commit hash from the spy result is honoured as accept_commit.
    assert accept_commit == "abc1234deadbeef0", (
        f"accept_commit must come from CommitRouterResult.commit_hash, got {accept_commit!r}"
    )
    assert commit_created is True, "commit_created must be True on a successful commit"


# NOTE: the standalone-encoding tests (``test_collect_feature_summary_encoding_error``
# and ``test_normalize_feature_encoding``) were retired with the standalone tasks
# surface (WP03/FR-004). The canonical ``ArtifactEncodingError`` /
# ``normalize_feature_encoding`` behavior is now covered on the real ``spec-kitty
# accept`` surface by tests/specify_cli/cli/commands/test_accept_normalize_encoding.py.


# T039: Test that done WPs don't require assignee (Bug #119)
def test_acceptance_succeeds_for_done_wp_without_assignee(feature_repo: Path, mission_slug: str) -> None:
    """Done WPs should not require assignee."""
    from tests.utils import run

    # Move WP01 to done without assignee
    wp_path = feature_repo / "kitty-specs" / mission_slug / "tasks" / "WP01.md"
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    _force_lane(feature_repo, mission_slug, "WP01", "done")
    run(["git", "commit", "-am", "Move to done without assignee"], cwd=feature_repo)

    # Strict validation should NOT complain about missing assignee for done lane
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert not any("missing assignee" in issue for issue in summary.metadata_issues), (
        "Done WPs should not require assignee"
    )


# T040: Test that doing/for_review WPs still require assignee (Bug #119)
def test_assignee_still_required_for_active_lanes(feature_repo: Path, mission_slug: str) -> None:
    """Doing and for_review WPs should still require assignee."""
    from tests.utils import run

    wp_path = feature_repo / "kitty-specs" / mission_slug / "tasks" / "WP01.md"

    # Test doing lane
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    _force_lane(feature_repo, mission_slug, "WP01", "in_progress")
    run(["git", "commit", "-am", "Move to doing without assignee"], cwd=feature_repo)

    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert any("missing assignee" in issue for issue in summary.metadata_issues), (
        "Doing lane should still require assignee"
    )

    # Test for_review lane
    _force_lane(feature_repo, mission_slug, "WP01", "for_review")
    run(["git", "commit", "-am", "Move to for_review without assignee"], cwd=feature_repo)

    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert any("missing assignee" in issue for issue in summary.metadata_issues), (
        "For_review lane should still require assignee"
    )


# T041: Test required fields still enforced for active lanes
def test_required_fields_still_enforced(feature_repo: Path, mission_slug: str) -> None:
    """Agent and shell_pid should still be required for active lanes.

    Note: lane is now tracked via the event log (not frontmatter), so removing
    lane: from frontmatter no longer produces a metadata_issue.
    """
    from tests.utils import run

    wp_path = feature_repo / "kitty-specs" / mission_slug / "tasks" / "WP01.md"

    # Test missing agent - move to doing first, then remove agent field manually
    _force_lane(feature_repo, mission_slug, "WP01", "in_progress")
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)

    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines_no_agent = [line for line in front.splitlines() if not line.startswith("agent:")]
    wp_path.write_text(th.build_document("\n".join(lines_no_agent), body, padding), encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert any("missing agent" in issue for issue in summary.metadata_issues), "Agent should still be required"

    # Test missing shell_pid - restore agent, remove shell_pid
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines_with_agent = front.splitlines()
    if not any(line.startswith("agent:") for line in lines_with_agent):
        lines_with_agent.insert(0, "agent: test-agent")
    lines_no_pid = [line for line in lines_with_agent if not line.startswith("shell_pid:")]
    wp_path.write_text(th.build_document("\n".join(lines_no_pid), body, padding), encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert any("missing shell_pid" in issue for issue in summary.metadata_issues), "Shell_pid should still be required"


def test_lenient_downgrades_path_conventions_to_warning(
    feature_repo: Path, mission_slug: str
) -> None:
    """``--lenient`` makes missing mission path conventions advisory (issue #1892).

    Without ``--lenient`` (``strict_metadata=True``) a mission that declares
    ``paths`` it cannot find still blocks acceptance via ``path_violations``;
    with ``--lenient`` the same shortfall is surfaced as a non-blocking warning,
    so repos with a non-default layout can be accepted.
    """
    from types import SimpleNamespace
    from unittest.mock import patch

    # feature_repo has no src/ tests/ contracts/ directories, so a software-dev
    # mission's declared path conventions are unmet.
    fake_mission = SimpleNamespace(
        name="Software Dev Kitty",
        config=SimpleNamespace(
            paths={"workspace": "src", "tests": "tests", "deliverables": "contracts"}
        ),
    )

    with patch("specify_cli.acceptance.get_mission_for_feature", return_value=fake_mission):
        strict = acc.collect_feature_summary(
            feature_repo, mission_slug, strict_metadata=True, mutate_matrix=False
        )
        lenient = acc.collect_feature_summary(
            feature_repo, mission_slug, strict_metadata=False, mutate_matrix=False
        )

    # Strict: missing conventions block acceptance as path_violations.
    assert strict.path_violations
    assert any("expects" in violation for violation in strict.path_violations)

    # Lenient: not blocking; surfaced as a warning instead.
    assert lenient.path_violations == []
    assert any("expects" in warning for warning in lenient.warnings)


# --- Direct canonical-surface unit coverage (restored from #2167 review) -----
# These three exercise the canonical ``specify_cli.acceptance`` / ``task_utils``
# functions directly — they were never coupled to the retired standalone tasks
# CLI surface (they already used the ``acc`` / ``support`` imports). They were
# dropped when the surface's test files were reconciled; restored here so the
# canonical functions keep a direct unit pin rather than only transitive CLI
# coverage (normalize_feature_encoding return value, the offending-path message,
# and detect_conflicting_wp_status' conflict detection).


def test_collect_feature_summary_encoding_error(feature_repo: Path, mission_slug: str) -> None:
    plan_path = feature_repo / "kitty-specs" / mission_slug / "plan.md"
    data = plan_path.read_bytes() + b"\x92"
    plan_path.write_bytes(data)

    with pytest.raises(acc.ArtifactEncodingError) as excinfo:
        acc.collect_feature_summary(feature_repo, mission_slug)

    assert str(plan_path) in str(excinfo.value)


def test_normalize_feature_encoding(feature_repo: Path, mission_slug: str) -> None:
    plan_path = feature_repo / "kitty-specs" / mission_slug / "plan.md"
    data = plan_path.read_bytes() + b"\x92"
    plan_path.write_bytes(data)

    cleaned = acc.normalize_feature_encoding(feature_repo, mission_slug)
    assert plan_path in cleaned
    # Should now be readable as UTF-8 without errors.
    plan_path.read_text(encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, mission_slug)
    assert summary.feature == mission_slug


def test_detect_conflicting_wp_status() -> None:
    status_lines = [
        " M kitty-specs/001-demo/tasks/planned/WP01.md",
        " M kitty-specs/001-demo/tasks/doing/WP02.md",
        "?? README.md",
    ]
    conflicts = th.detect_conflicting_wp_status(
        status_lines,
        "001-demo",
        Path("kitty-specs/001-demo/tasks/planned/WP01.md"),
        Path("kitty-specs/001-demo/tasks/doing/WP01.md"),
    )
    assert conflicts == [" M kitty-specs/001-demo/tasks/doing/WP02.md"]
