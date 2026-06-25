"""Direct unit tests for the setup-plan phase helpers (#2056 WP06, T022/T025).

The pre-decomposition ``setup_plan`` was a 507-LOC monolith; WP06 split it into
≤15-CC phase helpers. These tests exercise each helper's branches in isolation:
the SaaS auth refusal + boundary preflight gates, feature-dir resolution, the
spec gate, the plan-template scaffold, the plan-commit branch, the documentation
wiring no-op, and the result emitter. The relocated planning-commit helpers
(``_kind_for_artifact``, ``_artifact_absent_at_placement``, etc.) keep their
existing coverage via ``test_kind_for_artifact.py`` and
``test_agent_mission_commit_to_branch.py``; the end-to-end command stays pinned
by ``test_agent_feature.py``, ``test_mission_planning_entry.py`` and the WP01
golden harness.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands.agent import mission_setup_plan as seam

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# _enforce_saas_sync_auth_refusal
# ---------------------------------------------------------------------------


def test_auth_refusal_noop_when_sync_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    # No exception even with no auth scope available.
    seam._enforce_saas_sync_auth_refusal(json_output=True)


def test_auth_refusal_exits_when_unauthenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr(
        "specify_cli.sync.queue.read_queue_scope_from_session", lambda: None
    )
    monkeypatch.setattr(
        "specify_cli.sync.queue.read_queue_scope_from_credentials", lambda: None
    )
    with pytest.raises(typer.Exit) as exc:
        seam._enforce_saas_sync_auth_refusal(json_output=True)
    assert exc.value.exit_code == 2


def test_auth_refusal_passes_with_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr(
        "specify_cli.sync.queue.read_queue_scope_from_session", lambda: "scope-x"
    )
    # Returns without raising (scope resolved).
    seam._enforce_saas_sync_auth_refusal(json_output=True)


# ---------------------------------------------------------------------------
# _enforce_saas_sync_boundary_preflight
# ---------------------------------------------------------------------------


def test_boundary_preflight_noop_when_sync_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    seam._enforce_saas_sync_boundary_preflight(tmp_path)


def test_boundary_preflight_exits_on_incoherence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    class _Result:
        ok = False

        def render(self, _console: object) -> None:
            return None

    monkeypatch.setattr("specify_cli.sync.preflight.run_preflight", lambda **_k: _Result())
    with pytest.raises(typer.Exit) as exc:
        seam._enforce_saas_sync_boundary_preflight(tmp_path)
    assert exc.value.exit_code == 2


# ---------------------------------------------------------------------------
# _resolve_setup_plan_feature_dir
# ---------------------------------------------------------------------------


def test_resolve_feature_dir_auto_selects_sole(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    monkeypatch.setattr(seam, "_sole_mission_slug_or_none", lambda _r: "001-demo")
    monkeypatch.setattr(mission_mod, "_find_feature_directory", lambda _r, _c, explicit_feature=None: tmp_path / explicit_feature)
    out = seam._resolve_setup_plan_feature_dir(tmp_path, None, json_output=True)
    assert out == tmp_path / "001-demo"


def test_resolve_feature_dir_emits_detection_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    def _boom(*_a: object, **_k: object) -> Path:
        raise ValueError("ambiguous")

    monkeypatch.setattr(seam, "_sole_mission_slug_or_none", lambda _r: None)
    monkeypatch.setattr(mission_mod, "_find_feature_directory", _boom)
    monkeypatch.setattr(seam, "_build_setup_plan_detection_error", lambda *a, **k: {"error": "ambiguous"})
    with pytest.raises(typer.Exit):
        seam._resolve_setup_plan_feature_dir(tmp_path, None, json_output=True)


# ---------------------------------------------------------------------------
# _enforce_spec_gate
# ---------------------------------------------------------------------------


def test_spec_gate_exits_when_spec_missing(tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"  # not created
    with pytest.raises(typer.Exit):
        seam._enforce_spec_gate(
            spec_file, feature_dir, "001-demo", tmp_path,
            target_branch="main", current_branch="main", json_output=True,
        )


def test_spec_gate_blocks_when_not_substantive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"
    spec_file.write_text("# stub")
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: True)
    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: False)
    blocked = seam._enforce_spec_gate(
        spec_file, feature_dir, "001-demo", tmp_path,
        target_branch="main", current_branch="main", json_output=True,
    )
    assert blocked is True


def test_spec_gate_passes_when_committed_and_substantive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"
    spec_file.write_text("# real")
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: True)
    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: True)
    blocked = seam._enforce_spec_gate(
        spec_file, feature_dir, "001-demo", tmp_path,
        target_branch="main", current_branch="main", json_output=True,
    )
    assert blocked is False


# ---------------------------------------------------------------------------
# _scaffold_plan_template
# ---------------------------------------------------------------------------


def test_scaffold_plan_template_noop_when_exists(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("populated")
    seam._scaffold_plan_template(plan_file, tmp_path)  # must not overwrite
    assert plan_file.read_text() == "populated"


def test_scaffold_plan_template_copies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod
    from types import SimpleNamespace

    template_src = tmp_path / "tmpl.md"
    template_src.write_text("TEMPLATE")
    monkeypatch.setattr(mission_mod, "resolve_template", lambda *a, **k: SimpleNamespace(path=template_src))
    plan_file = tmp_path / "plan.md"
    seam._scaffold_plan_template(plan_file, tmp_path)
    assert plan_file.read_text() == "TEMPLATE"


# ---------------------------------------------------------------------------
# _run_documentation_wiring (non-doc mission no-op)
# ---------------------------------------------------------------------------


def test_documentation_wiring_noop_for_non_doc_mission(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "get_mission_type", lambda _fd: "software-dev")
    gap, gens = seam._run_documentation_wiring(tmp_path, "001-demo", tmp_path, target_branch="main", json_output=True)
    assert gap is None
    assert gens == []


# ---------------------------------------------------------------------------
# _emit_setup_plan_result
# ---------------------------------------------------------------------------


def test_emit_result_human(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=True,
        plan_blocked_reason=None,
        plan_commit_result=None,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=False,
    )
    assert "Plan scaffolded" in capsys.readouterr().out


def test_emit_result_json_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: dict[str, object] = {}
    monkeypatch.setattr(seam, "_emit_json", lambda p: emitted.update(p))
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=False,
        plan_blocked_reason="not substantive",
        plan_commit_result=None,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert emitted["result"] == "blocked"
    assert emitted["blocked_reason"] == "not substantive"
    assert "branch_context" in emitted


def test_emit_result_json_committed_surfaces_hash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: dict[str, object] = {}
    monkeypatch.setattr(seam, "_emit_json", lambda p: emitted.update(p))
    commit = seam.CommitToBranchResult(status="committed", placement_ref="main", commit_hash="abc1234")
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=True,
        plan_blocked_reason=None,
        plan_commit_result=commit,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert emitted["commit_created"] is True
    assert emitted["commit_hash"] == "abc1234"
    assert emitted["commit_status"] == "committed"
