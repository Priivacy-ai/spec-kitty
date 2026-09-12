"""Execute the shipped typecheck command; compiler failures must remain failures."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.doctrine.conftest import REPO_ROOT

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


@pytest.fixture(params=["frontend-freddy", "node-norris"])
def typecheck_command(request: pytest.FixtureRequest) -> str:
    profile = REPO_ROOT / "packs" / "built-in" / "agent_profiles" / f"{request.param}.agent.yaml"
    data = YAML(typ="safe").load(profile.read_text())
    return next(step["command"] for step in data["self-review-protocol"]["steps"] if step["name"] == "type-check")


def _compiler(path: Path, exit_code: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\nprintf '%s\\n' invoked >> compiler-calls\nexit {exit_code}\n")
    path.chmod(0o755)


def _run(command: str, root: Path) -> subprocess.CompletedProcess[str]:
    if os.name == "nt" or not shutil.which("node") or not shutil.which("npm"):
        pytest.skip("The shipped POSIX profile command requires sh, node and npm")
    return subprocess.run(["sh", "-c", command], cwd=root, env=os.environ.copy(), capture_output=True, text=True, timeout=30)


def test_project_typecheck_failure_cannot_fall_back_to_success(typecheck_command: str, tmp_path: Path) -> None:
    # Real npm script emits a failure; an alternative local compiler would pass.
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"typecheck": "node -e 'process.exit(23)'"}}))
    _compiler(tmp_path / "node_modules" / ".bin" / "tsc", 0)
    result = _run(typecheck_command, tmp_path)
    assert result.returncode == 23, result.stdout + result.stderr
    assert not (tmp_path / "compiler-calls").exists()


def test_available_local_compiler_failure_propagates(typecheck_command: str, tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {}}))
    _compiler(tmp_path / "node_modules" / ".bin" / "tsc", 19)
    result = _run(typecheck_command, tmp_path)
    assert result.returncode == 19, result.stdout + result.stderr
    assert (tmp_path / "compiler-calls").read_text().splitlines() == ["invoked"]


def test_available_local_compiler_success(typecheck_command: str, tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {}}))
    _compiler(tmp_path / "node_modules" / ".bin" / "tsc", 0)
    assert _run(typecheck_command, tmp_path).returncode == 0
