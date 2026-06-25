"""Focused per-helper tests for ``_command_surface_doctor`` (WP05, #2059).

Exercise the decomposed helpers of ``skills`` / ``command-files`` /
``tool-surfaces`` and ``_repair_command_skill_state`` directly so each branch
is covered without relying solely on broad CLI integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import typer

from specify_cli.cli.commands import _command_surface_doctor as cs

pytestmark = [pytest.mark.fast]


# --- _slash_gap_for_path -----------------------------------------------------


def test_slash_gap_for_path_missing(tmp_path: Path) -> None:
    gap = cs._slash_gap_for_path("claude", "specify", tmp_path / "nope.md", "9.9")
    assert gap is not None
    assert gap.status == "missing"


def test_slash_gap_for_path_stale(tmp_path: Path) -> None:
    f = tmp_path / "spec-kitty.specify.md"
    f.write_text("no marker here\n# body", encoding="utf-8")
    gap = cs._slash_gap_for_path("claude", "specify", f, "9.9.9")
    assert gap is not None
    assert gap.status == "stale"


def test_slash_gap_for_path_healthy(tmp_path: Path) -> None:
    from specify_cli.runtime.agent_commands import _VERSION_MARKER_PREFIX

    f = tmp_path / "spec-kitty.specify.md"
    f.write_text(f"{_VERSION_MARKER_PREFIX} 9.9.9 -->\n# body", encoding="utf-8")
    assert cs._slash_gap_for_path("claude", "specify", f, "9.9.9") is None


# --- _repair_refusal ---------------------------------------------------------


@dataclass
class _FakeReport:
    drift: list[str] = field(default_factory=list)
    unsafe: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)


def test_repair_refusal_drift() -> None:
    assert "edited-file drift" in (cs._repair_refusal(_FakeReport(drift=["x"])) or "")


def test_repair_refusal_unsafe() -> None:
    assert "outside the project" in (cs._repair_refusal(_FakeReport(unsafe=["x"])) or "")


def test_repair_refusal_orphans() -> None:
    assert "unmanaged" in (cs._repair_refusal(_FakeReport(orphans=["x"])) or "")


def test_repair_refusal_clean() -> None:
    assert cs._repair_refusal(_FakeReport()) is None


# --- _repair_command_skill_state ---------------------------------------------


def test_repair_command_skill_state_noop_when_clean(tmp_path: Path) -> None:
    result = cs._repair_command_skill_state(tmp_path, [], [], _FakeReport(), False)
    assert result == ([], [], [], False)


def test_repair_command_skill_state_refuses_on_drift(tmp_path: Path) -> None:
    repaired, pruned, errors, vibe = cs._repair_command_skill_state(
        tmp_path, ["codex"], [], _FakeReport(drift=["a"], gaps=["b"]), False
    )
    assert repaired == [] and pruned == []
    assert errors and "edited-file drift" in errors[0]


def test_repair_command_skill_state_installs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.skills import command_installer

    installed: list[str] = []
    monkeypatch.setattr(
        command_installer, "install", lambda _p, agent: installed.append(agent)
    )
    repaired, pruned, errors, vibe = cs._repair_command_skill_state(
        tmp_path, ["codex"], [], _FakeReport(gaps=["x"]), False
    )
    assert "codex" in repaired
    assert errors == []


# --- _install_command_skill_agents -------------------------------------------


def test_install_command_skill_agents_error_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.skills import command_installer

    def _boom(_p: Path, _agent: str) -> None:
        raise RuntimeError("install failed")

    monkeypatch.setattr(command_installer, "install", _boom)
    repaired, vibe, errors = cs._install_command_skill_agents(tmp_path, ["codex"])
    assert repaired == []
    assert errors and "codex" in errors[0]


# --- render helpers (smoke for coverage) -------------------------------------


def test_print_command_skill_paths_empty_and_nonempty() -> None:
    cs._print_command_skill_paths("Title", [])  # no-op branch
    cs._print_command_skill_paths("Title", ["a", "b"])


def test_print_command_skill_report_ok() -> None:
    cs._print_command_skill_report({"ok": True, "entries": 3}, fix=False)


def test_print_command_skill_report_issues() -> None:
    payload: dict[str, Any] = {
        "ok": False,
        "entries": 2,
        "drift": ["d"],
        "gaps": ["g"],
        "orphans": ["o"],
        "stale": ["s"],
        "unsafe": ["u"],
        "uninstalled_agents": ["codex"],
        "repaired_agents": ["vibe"],
        "pruned": ["p"],
        "repaired_vibe_config": True,
        "repair_errors": ["err"],
        "vibe_config_missing": True,
    }
    cs._print_command_skill_report(payload, fix=False)


def test_print_command_files_table() -> None:
    issues = [
        {"agent": "claude", "command": "plan", "file": "x.md", "severity": "error", "issue": "missing"},
        {"agent": "codex", "command": "tasks", "file": "y.md", "severity": "warning", "issue": "stale"},
    ]
    cs._print_command_files_table(issues)


def test_print_slash_command_report_branches() -> None:
    # No configured agents -> healthy short-circuit.
    assert cs._print_slash_command_report([], [], fix=False) is True
    # Configured + no gaps.
    assert cs._print_slash_command_report(["claude"], [], fix=False) is True
    # Configured + gaps.
    gaps = [cs.SlashCommandGap("claude", "plan", Path("/tmp/x.md"), "missing")]
    assert cs._print_slash_command_report(["claude"], gaps, fix=False) is False


def test_print_slash_command_payload_error_branch() -> None:
    cs._print_slash_command_payload({"errors": ["boom"]}, fix=False)


def test_print_slash_command_payload_gaps_branch() -> None:
    payload = {
        "errors": [],
        "configured_agents": ["claude"],
        "gaps": [
            {"agent_key": "claude", "command": "plan", "expected_path": "/tmp/x.md", "status": "missing"}
        ],
        "repaired": ["/tmp/x.md"],
    }
    cs._print_slash_command_payload(payload, fix=True)


# --- _resolve_or_exit / run_command_files ------------------------------------


def test_resolve_or_exit_not_in_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cs, "locate_project_root", lambda: None)
    with pytest.raises(typer.Exit) as exc:
        cs._resolve_or_exit(1)
    assert exc.value.exit_code == 1


def test_resolve_or_exit_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> Path:
        raise RuntimeError("no root")

    monkeypatch.setattr(cs, "locate_project_root", _boom)
    with pytest.raises(typer.Exit) as exc:
        cs._resolve_or_exit(2)
    assert exc.value.exit_code == 2


def test_run_command_files_healthy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cs, "locate_project_root", lambda: tmp_path)
    import specify_cli.runtime.doctor as rt

    monkeypatch.setattr(rt, "check_command_file_health", lambda _p: [])
    with pytest.raises(typer.Exit) as exc:
        cs.run_command_files(json_output=False)
    assert exc.value.exit_code == 0


def test_run_command_files_issues_human(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cs, "locate_project_root", lambda: tmp_path)
    import specify_cli.runtime.doctor as rt

    issues = [{"agent": "claude", "command": "plan", "file": "x.md", "severity": "error", "issue": "m"}]
    monkeypatch.setattr(rt, "check_command_file_health", lambda _p: issues)
    with pytest.raises(typer.Exit) as exc:
        cs.run_command_files(json_output=False)
    assert exc.value.exit_code == 1


def test_run_command_files_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cs, "locate_project_root", lambda: tmp_path)
    import specify_cli.runtime.doctor as rt

    monkeypatch.setattr(rt, "check_command_file_health", lambda _p: [{"x": 1}])
    with pytest.raises(typer.Exit) as exc:
        cs.run_command_files(json_output=True)
    assert exc.value.exit_code == 1


# --- skills entrypoint -------------------------------------------------------


def test_run_skills_audit_not_in_project_json() -> None:
    with pytest.raises(typer.Exit) as exc:
        cs.run_skills_audit(fix=False, json_output=True, project_path=None)
    assert exc.value.exit_code == 2


def test_load_skills_state_or_exit_config_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.core.agent_config import AgentConfigError

    def _boom(_p: Path) -> Any:
        raise AgentConfigError("bad config")

    monkeypatch.setattr(cs, "_load_command_skill_state", _boom)
    with pytest.raises(typer.Exit) as exc:
        cs._load_skills_state_or_exit(tmp_path, json_output=True)
    assert exc.value.exit_code == 2


def test_load_skills_state_or_exit_manifest_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(_p: Path) -> Any:
        raise RuntimeError("manifest broken")

    monkeypatch.setattr(cs, "_load_command_skill_state", _boom)
    with pytest.raises(typer.Exit) as exc:
        cs._load_skills_state_or_exit(tmp_path, json_output=False)
    assert exc.value.exit_code == 2


# --- tool-surfaces entrypoint ------------------------------------------------


def test_resolve_tool_surfaces_project_none_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cs, "locate_project_root", lambda: None)
    with pytest.raises(typer.Exit) as exc:
        cs._resolve_tool_surfaces_project(json_output=True)
    assert exc.value.exit_code == 2


def test_resolve_tool_surfaces_project_raises_human(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom() -> Path:
        raise RuntimeError("x")

    monkeypatch.setattr(cs, "locate_project_root", _boom)
    with pytest.raises(typer.Exit) as exc:
        cs._resolve_tool_surfaces_project(json_output=False)
    assert exc.value.exit_code == 2


def test_run_tool_surfaces_audit_unknown_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cs, "locate_project_root", lambda: tmp_path)
    with pytest.raises(typer.Exit) as exc:
        cs.run_tool_surfaces_audit(
            kind=["totally-unknown-kind"], tool=None, fix=False, json_output=True
        )
    assert exc.value.exit_code == 2


def test_print_tool_surface_human_rejects_non_outcome() -> None:
    # The render guard asserts the input is a ToolSurfaceOutcome.
    with pytest.raises(AssertionError):
        cs._print_tool_surface_human(object())


@dataclass
class _FakeManifest:
    entries: list[Any] = field(default_factory=list)


def _clean_state() -> Any:
    return (_FakeManifest(), _FakeReport(), [], [], [], False)


def test_assemble_skills_payload_no_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cs, "_load_and_optionally_repair_slash_commands", lambda _p, _f: {"ok": True}
    )
    payload = cs._assemble_skills_payload(tmp_path, fix=False, state=_clean_state())
    assert payload["ok"] is True
    assert payload["slash_commands"] == {"ok": True}


def test_assemble_skills_payload_fix_reloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cs,
        "_repair_command_skill_state",
        lambda *_a: (["codex"], [], [], False),
    )
    monkeypatch.setattr(cs, "_load_command_skill_state", lambda _p: _clean_state())
    monkeypatch.setattr(
        cs, "_load_and_optionally_repair_slash_commands", lambda _p, _f: {"ok": True}
    )
    # report has gaps so repair runs.
    state = (_FakeManifest(), _FakeReport(gaps=["g"]), [], [], ["codex"], False)
    payload = cs._assemble_skills_payload(tmp_path, fix=True, state=state)
    assert payload["ok"] is True


def test_assemble_skills_payload_post_fix_verify_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cs, "_repair_command_skill_state", lambda *_a: (["codex"], [], [], False)
    )

    def _boom(_p: Path) -> Any:
        raise RuntimeError("verify boom")

    monkeypatch.setattr(cs, "_load_command_skill_state", _boom)
    monkeypatch.setattr(
        cs, "_load_and_optionally_repair_slash_commands", lambda _p, _f: {"ok": True}
    )
    state = (_FakeManifest(), _FakeReport(gaps=["g"]), [], [], ["codex"], False)
    payload = cs._assemble_skills_payload(tmp_path, fix=True, state=state)
    assert any("post-fix verify failed" in e for e in payload["repair_errors"])  # type: ignore[union-attr]


def test_run_skills_audit_json_happy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cs, "_load_skills_state_or_exit", lambda _p, _j: _clean_state())
    monkeypatch.setattr(
        cs,
        "_assemble_skills_payload",
        lambda *_a, **_k: {"ok": True, "slash_commands": {"ok": True}},
    )
    with pytest.raises(typer.Exit) as exc:
        cs.run_skills_audit(fix=False, json_output=True, project_path=tmp_path)
    assert exc.value.exit_code == 0


def test_run_skills_audit_human_unhealthy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cs, "_load_skills_state_or_exit", lambda _p, _j: _clean_state())
    monkeypatch.setattr(
        cs,
        "_assemble_skills_payload",
        lambda *_a, **_k: {
            "ok": False,
            "entries": 0,
            "drift": [],
            "gaps": ["g"],
            "orphans": [],
            "stale": [],
            "unsafe": [],
            "uninstalled_agents": [],
            "repaired_agents": [],
            "pruned": [],
            "repaired_vibe_config": False,
            "repair_errors": [],
            "vibe_config_missing": False,
            "slash_commands": {"ok": True, "errors": [], "configured_agents": [], "gaps": [], "repaired": []},
        },
    )
    with pytest.raises(typer.Exit) as exc:
        cs.run_skills_audit(fix=False, json_output=False, project_path=tmp_path)
    assert exc.value.exit_code == 1


def test_run_tool_surfaces_audit_json_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cs, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(cs, "_configured_tool_keys", lambda _p: ["codex"])

    class _Report:
        ok = True

    class _Outcome:
        report = _Report()

        def to_json(self) -> dict[str, Any]:
            return {"ok": True}

    import specify_cli.tool_surface.service as svc

    monkeypatch.setattr(svc, "run_tool_surfaces", lambda *a, **k: _Outcome())
    monkeypatch.setattr(svc, "surface_kind_from_token", lambda t: t)
    with pytest.raises(typer.Exit) as exc:
        cs.run_tool_surfaces_audit(kind=None, tool=None, fix=False, json_output=True)
    assert exc.value.exit_code == 0


def test_command_surface_does_not_import_doctor() -> None:
    import ast

    source = Path(cs.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    relative: list[str] = []
    absolute: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                relative.append(node.module or "")
            elif node.module:
                absolute.append(node.module)
        elif isinstance(node, ast.Import):
            absolute.extend(alias.name for alias in node.names)
    # Must not import the CLI doctor orchestrator module (one-way graph). The
    # runtime health-checker ``specify_cli.runtime.doctor`` is a different module
    # and is allowed.
    assert "specify_cli.cli.commands.doctor" not in absolute
    assert "doctor" not in relative
    assert set(relative) <= {"_doctor_shared"}
