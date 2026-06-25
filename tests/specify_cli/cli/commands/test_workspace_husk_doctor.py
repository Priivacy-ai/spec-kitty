"""Focused per-helper tests for ``_workspace_husk_doctor`` (WP09, #2059).

Cover the status-label classification, the fix-emission branches (registration
refusal / remaining husks / clean), the report-emission branches (clean / error /
husks-present), and the run_workspaces dispatch exit contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import typer

from specify_cli.cli.commands import _workspace_husk_doctor as wh

pytestmark = [pytest.mark.fast]


# --- _workspace_husk_status_label --------------------------------------------


def test_status_label_unknown() -> None:
    assert "unknown registration" in wh._workspace_husk_status_label(None)


def test_status_label_registered() -> None:
    assert "registered (manual repair" in wh._workspace_husk_status_label(True)


def test_status_label_unregistered() -> None:
    assert "unregistered (safe" in wh._workspace_husk_status_label(False)


# --- report emission ---------------------------------------------------------


@dataclass
class _Husk:
    path: str = "/repo/.worktrees/husk-a"
    registered: bool | None = False


@dataclass
class _Report:
    healthy: bool = True
    husks: list[_Husk] = field(default_factory=list)
    registration_error: str | None = None
    worktrees_dir: str = "/repo/.worktrees"

    def to_dict(self) -> dict[str, Any]:
        return {"healthy": self.healthy, "husks": [h.path for h in self.husks]}


def test_report_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    monkeypatch.setattr(status_mod, "scan_workspace_husks", lambda _r: _Report(healthy=True))
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_report(tmp_path, json_output=False)
    assert exc.value.exit_code == 0


def test_report_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    monkeypatch.setattr(status_mod, "scan_workspace_husks", lambda _r: _Report(healthy=False))
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_report(tmp_path, json_output=True)
    assert exc.value.exit_code == 1


def test_report_error_no_husks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    report = _Report(healthy=False, husks=[], registration_error="git failed")
    monkeypatch.setattr(status_mod, "scan_workspace_husks", lambda _r: report)
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_report(tmp_path, json_output=False)
    assert exc.value.exit_code == 1


def test_report_husks_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    report = _Report(
        healthy=False, husks=[_Husk(registered=False), _Husk(registered=True)],
        registration_error="partial",
    )
    monkeypatch.setattr(status_mod, "scan_workspace_husks", lambda _r: report)
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_report(tmp_path, json_output=False)
    assert exc.value.exit_code == 1


# --- fix emission ------------------------------------------------------------


@dataclass
class _FixResult:
    removed: list[str] = field(default_factory=list)
    skipped_registered: list[str] = field(default_factory=list)
    skipped_appeared_valid: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"removed": self.removed}


def test_fix_registration_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    def _boom(_r: Path) -> Any:
        raise status_mod.WorkspaceHuskRegistrationError("git down")

    monkeypatch.setattr(status_mod, "fix_workspace_husks", _boom)
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_fix(tmp_path, json_output=False)
    assert exc.value.exit_code == 1


def test_fix_registration_error_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    def _boom(_r: Path) -> Any:
        raise status_mod.WorkspaceHuskRegistrationError("git down")

    monkeypatch.setattr(status_mod, "fix_workspace_husks", _boom)
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_fix(tmp_path, json_output=True)
    assert exc.value.exit_code == 1


def test_fix_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    report = _Report(husks=[])
    monkeypatch.setattr(
        status_mod, "fix_workspace_husks", lambda _r: (report, _FixResult(removed=["a"]))
    )
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_fix(tmp_path, json_output=False)
    assert exc.value.exit_code == 0


def test_fix_remaining_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    report = _Report(husks=[_Husk()])
    fix_result = _FixResult(skipped_registered=["reg-a"], skipped_appeared_valid=["v-a"])
    monkeypatch.setattr(status_mod, "fix_workspace_husks", lambda _r: (report, fix_result))
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_fix(tmp_path, json_output=True)
    assert exc.value.exit_code == 1


def test_fix_human_with_skips(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import specify_cli.status as status_mod

    report = _Report(husks=[])
    fix_result = _FixResult(
        removed=["r"], skipped_registered=["reg"], skipped_appeared_valid=["v"]
    )
    monkeypatch.setattr(status_mod, "fix_workspace_husks", lambda _r: (report, fix_result))
    with pytest.raises(typer.Exit) as exc:
        wh._emit_workspace_husk_fix(tmp_path, json_output=False)
    # Remaining (skipped) → exit 1.
    assert exc.value.exit_code == 1


# --- run_workspaces dispatch -------------------------------------------------


def test_run_workspaces_fix_branch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called: dict[str, Any] = {}
    monkeypatch.setattr(wh, "_emit_workspace_husk_fix", lambda r, j: called.setdefault("fix", (r, j)))
    wh.run_workspaces(tmp_path, fix=True, json_output=True)
    assert called["fix"] == (tmp_path, True)


def test_run_workspaces_report_branch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called: dict[str, Any] = {}
    monkeypatch.setattr(
        wh, "_emit_workspace_husk_report", lambda r, j: called.setdefault("report", (r, j))
    )
    wh.run_workspaces(tmp_path, fix=False, json_output=False)
    assert called["report"] == (tmp_path, False)


def test_workspace_husk_doctor_does_not_import_doctor() -> None:
    import ast

    source = Path(wh.__file__).read_text(encoding="utf-8")
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
    assert "specify_cli.cli.commands.doctor" not in absolute
    assert set(relative) <= {"_doctor_shared"}
