"""Focused per-helper tests for ``_daemon_doctor`` (WP10, #2059).

Cover orphan-daemons detection (0 vs 1, JSON + human) and the restart-daemon
four-state exit contract by injecting a fake restart result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import typer

from specify_cli.cli.commands import _daemon_doctor as dd

pytestmark = [pytest.mark.fast]


@dataclass
class _OwnerRecord:
    pid: int = 1234
    port: int = 9400
    package_version: str = "3.2.0"
    executable_path: str = "/usr/bin/spec-kitty"
    source_checkout_path: str = "/repo"
    server_url: str = "http://127.0.0.1:9400"
    auth_scope: str = "team"
    queue_db_path: str = "/tmp/queue.db"
    started_at: str = "2026-01-01T00:00:00Z"


# --- run_orphan_daemons ------------------------------------------------------


def test_orphan_daemons_none_json(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.sync.owner as owner_mod

    monkeypatch.setattr(owner_mod, "list_orphan_records", lambda: [])
    monkeypatch.setattr(owner_mod, "owner_record_path", lambda: Path("/tmp/owner.json"))
    with pytest.raises(typer.Exit) as exc:
        dd.run_orphan_daemons(json_output=True)
    assert exc.value.exit_code == 0


def test_orphan_daemons_present_json(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.sync.owner as owner_mod

    monkeypatch.setattr(owner_mod, "list_orphan_records", lambda: [_OwnerRecord()])
    monkeypatch.setattr(owner_mod, "owner_record_path", lambda: Path("/tmp/owner.json"))
    with pytest.raises(typer.Exit) as exc:
        dd.run_orphan_daemons(json_output=True)
    assert exc.value.exit_code == 1


def test_orphan_daemons_none_human(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.sync.owner as owner_mod

    monkeypatch.setattr(owner_mod, "list_orphan_records", lambda: [])
    monkeypatch.setattr(owner_mod, "owner_record_path", lambda: Path("/tmp/owner.json"))
    with pytest.raises(typer.Exit) as exc:
        dd.run_orphan_daemons(json_output=False)
    assert exc.value.exit_code == 0


def test_orphan_daemons_present_human(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.sync.owner as owner_mod

    monkeypatch.setattr(
        owner_mod, "list_orphan_records", lambda: [_OwnerRecord(), _OwnerRecord(pid=5678)]
    )
    monkeypatch.setattr(owner_mod, "owner_record_path", lambda: Path("/tmp/owner.json"))
    with pytest.raises(typer.Exit) as exc:
        dd.run_orphan_daemons(json_output=False)
    assert exc.value.exit_code == 1


# --- run_restart_daemon (four-state) -----------------------------------------


@dataclass
class _RestartResult:
    exit_code: int


@pytest.mark.parametrize("code", [0, 1, 2, 3])
def test_restart_daemon_four_states(
    monkeypatch: pytest.MonkeyPatch, code: int, tmp_path: Path
) -> None:
    import specify_cli.sync.restart as restart_mod

    monkeypatch.setattr(restart_mod, "restart_daemon", lambda _r: _RestartResult(code))
    monkeypatch.setattr(restart_mod, "render_restart_result", lambda _r, json_output: "{}")
    with pytest.raises(typer.Exit) as exc:
        dd.run_restart_daemon(json_output=True)
    assert exc.value.exit_code == code


def test_restart_daemon_repo_root_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # locate_project_root raising falls back to cwd; the contract is unaffected.
    import specify_cli.core.paths as paths_mod
    import specify_cli.sync.restart as restart_mod

    def _boom(*_a: Any, **_k: Any) -> Path:
        raise RuntimeError("no repo")

    monkeypatch.setattr(paths_mod, "locate_project_root", _boom)
    monkeypatch.setattr(restart_mod, "restart_daemon", lambda _r: _RestartResult(0))
    monkeypatch.setattr(restart_mod, "render_restart_result", lambda _r, json_output: "{}")
    with pytest.raises(typer.Exit) as exc:
        dd.run_restart_daemon(json_output=True)
    assert exc.value.exit_code == 0


def test_daemon_doctor_does_not_import_doctor() -> None:
    import ast

    source = Path(dd.__file__).read_text(encoding="utf-8")
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
