"""CLI surface tests for ``spec-kitty migrate repin-hooks`` (#254).

Mirrors the ``patch(locate_project_root)`` pattern in
``tests/migration/test_backfill_identity_cli.py`` — ``repin-hooks`` has no
``--project-root`` option (it operates on the CURRENT repo like
``backfill-identity``/``backfill-topology``/``rebaseline-dossier-hashes``),
so the project root is substituted at the resolver, not via a CLI flag.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrate_app

pytestmark = [pytest.mark.integration]


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    (repo / ".kittify").mkdir()
    return repo


def test_help_flag_registers_subcommand() -> None:
    result = CliRunner().invoke(migrate_app, ["repin-hooks", "--help"])
    assert result.exit_code == 0
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "repin-hooks" in plain
    assert "--json" in plain


def test_json_output_reports_current_interpreter(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    with patch(
        "specify_cli.cli.commands.migrate_cmd.locate_project_root",
        return_value=repo,
    ):
        result = CliRunner().invoke(migrate_app, ["repin-hooks", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"] == "repinned"
    assert payload["interpreter"] == os.path.abspath(sys.executable)

    hook_path = Path(payload["hook_path"])
    assert hook_path.is_file()
    assert os.path.abspath(sys.executable) in hook_path.read_text(encoding="utf-8")


def test_exits_1_when_project_root_not_found() -> None:
    with patch(
        "specify_cli.cli.commands.migrate_cmd.locate_project_root",
        return_value=None,
    ):
        result = CliRunner().invoke(migrate_app, ["repin-hooks"])

    assert result.exit_code == 1
