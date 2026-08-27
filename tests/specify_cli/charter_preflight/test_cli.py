"""Tests for the ``spec-kitty charter preflight`` typer command (WP03 / T020).

Covers:

* ``--json`` emits the binding shape (parseable, sorted keys).
* Exit-code matrix from ``contracts/charter-preflight-json.md``:
  passed → 0; non-passed without ``--strict`` → 0; non-passed with
  ``--strict`` → 1; hard error → 2.
"""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.charter_runtime.preflight import cli as charter_preflight_cli_module
from specify_cli.cli.commands.charter import app as charter_app
from specify_cli.task_utils import find_repo_root

from ._fixtures import (
    init_git_repo,
    make_fresh_repo,
    seed_bundle_files,
    seed_charter,
    write_metadata,
)


pytestmark = [pytest.mark.integration]

_runner = CliRunner()


def test_command_is_registered() -> None:
    """``preflight`` must be discoverable via ``spec-kitty charter --help``."""
    result = _runner.invoke(charter_app, ["--help"])
    assert "preflight" in result.stdout


def test_passed_exit_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fresh repo → JSON has ``passed=true`` → exit 0."""
    make_fresh_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(charter_app, ["preflight", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["passed"] is True
    assert payload["blocked_reason"] is None


def test_non_strict_blocked_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Blocked without ``--strict`` → exit 0 (contract row 1)."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)
    # No manifest -> drg missing.

    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(charter_app, ["preflight", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["passed"] is False
    assert payload["blocked_reason"] is not None


def test_strict_blocked_exits_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``--strict`` + non-passing → exit 1."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)

    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(charter_app, ["preflight", "--json", "--strict"])
    assert result.exit_code == 1, result.stdout


def test_hard_error_exits_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No repo root found → exit 2 (no JSON payload).

    ``find_repo_root()`` walks unboundedly in production. Bound the walk to
    this test's own tmp tree (issue #128): nothing above ``tmp_path`` is under
    test control, and under a full parallel run a sibling test's shared
    ancestor can transiently gain a ``.git``/``.kittify``, which would flip
    this "nothing found" verdict non-deterministically (same class of bug as
    #130/#139's ``_find_project_root``).
    """
    # tmp_path is not a git repo and has no .kittify ancestor -> find_repo_root raises.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        charter_preflight_cli_module,
        "find_repo_root",
        partial(find_repo_root, stop=tmp_path),
    )
    result = _runner.invoke(charter_app, ["preflight", "--json"])
    assert result.exit_code == 2, result.stdout


def test_json_is_sorted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``--json`` output uses sorted keys so it is byte-stable."""
    make_fresh_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(charter_app, ["preflight", "--json"])
    assert result.exit_code == 0
    payload_str = result.stdout.strip().splitlines()[-1]
    # If keys are sorted, re-dumping the parsed dict yields the same string.
    parsed = json.loads(payload_str)
    assert json.dumps(parsed, sort_keys=True, ensure_ascii=False) == payload_str
