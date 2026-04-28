"""Tests for ``charter generate --json`` ``next_step`` tracking instruction.

Covers WP04 of mission ``charter-e2e-hardening-tranche-2-01KQ9NVQ`` (#841):
the JSON envelope must surface a ``next_step`` field that tells the operator
(and the strict E2E) when the freshly-generated charter still needs a
``git add`` before ``charter bundle validate`` will accept it.

The contract for this field lives at::

    kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/contracts/
        charter-bundle-validate.json::definitions/generate_tracking_instruction
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import charter_bundle
from specify_cli.cli.commands.charter import app as charter_app

# Marked for mutmut sandbox skip — uses ``subprocess`` (`git`).
pytestmark = pytest.mark.non_sandbox

runner = CliRunner()


def _git_init(repo_root: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=str(repo_root),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(repo_root),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo_root),
        check=True,
    )


def _generate(repo_root: Path, *, force: bool = False) -> dict[str, object]:
    """Invoke ``charter generate --json`` against ``repo_root``."""
    args = ["generate", "--json"]
    if force:
        args.append("--force")
    with patch(
        "specify_cli.cli.commands.charter.find_repo_root"
    ) as mock_find_root:
        mock_find_root.return_value = repo_root
        result = runner.invoke(charter_app, args)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    return payload  # type: ignore[no-any-return]


def test_generate_emits_git_add_next_step_when_charter_untracked(
    tmp_path: Path,
) -> None:
    """Fresh git project + ``charter generate --json`` must instruct the
    operator to ``git add`` the freshly-written ``charter.md``."""
    _git_init(tmp_path)
    payload = _generate(tmp_path)

    assert payload["result"] == "success"
    assert payload["success"] is True
    next_step = payload["next_step"]
    assert isinstance(next_step, dict)
    assert next_step["action"] == "git_add"
    paths = next_step["paths"]
    assert isinstance(paths, list)
    assert paths == [".kittify/charter/charter.md"]
    # Reason is operator-facing rationale per the contract.
    assert "tracked" in next_step["reason"]
    assert payload["charter_path"] == ".kittify/charter/charter.md"


def test_generate_emits_no_action_when_charter_already_tracked(
    tmp_path: Path,
) -> None:
    """Re-generating against a project where charter.md is already tracked
    must emit ``next_step.action == "no_action_required"``."""
    _git_init(tmp_path)

    # First generation: produces an untracked charter.md.
    first = _generate(tmp_path)
    assert first["next_step"] == {  # type: ignore[comparison-overlap]
        "action": "git_add",
        "paths": [".kittify/charter/charter.md"],
        "reason": "bundle validate requires charter.md to be tracked",
    }

    # Stage and commit the charter so it becomes git-tracked.
    subprocess.run(
        ["git", "add", ".kittify/charter/charter.md"],
        cwd=str(tmp_path),
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "track charter"],
        cwd=str(tmp_path),
        check=True,
    )

    # Second generation (must use --force because charter.md already
    # exists on disk): charter.md is already tracked.
    second = _generate(tmp_path, force=True)
    assert second["next_step"] == {"action": "no_action_required"}


def test_generate_then_bundle_validate_operator_path_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end operator path:

    1. ``git init`` a fresh project.
    2. ``charter generate --json`` and read ``next_step``.
    3. Follow ``next_step.git_add`` verbatim (stage + commit the listed paths).
    4. Materialize the derived bundle files + ``.gitignore`` (the strict E2E
       does this in a separate step; here we focus on the agreement between
       generate's tracking instruction and bundle validate's tracked-file
       invariant).
    5. ``charter bundle validate --json`` exits 0 and reports the bundle as
       compliant.
    """
    _git_init(tmp_path)
    payload = _generate(tmp_path)

    next_step = payload["next_step"]
    assert isinstance(next_step, dict)
    assert next_step["action"] == "git_add"
    paths = next_step["paths"]
    assert isinstance(paths, list)
    assert paths  # non-empty when action is git_add

    # 3. Follow the instruction verbatim.
    subprocess.run(
        ["git", "add", *[str(p) for p in paths]],
        cwd=str(tmp_path),
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "follow next_step.git_add"],
        cwd=str(tmp_path),
        check=True,
    )

    # 4. Materialize the derived bundle files + .gitignore so
    # ``bundle validate`` finds the full bundle. ``charter generate``
    # already wrote the derived files via ``sync_charter`` — the
    # operator only needs to ensure .gitignore lists them.
    derived = [
        ".kittify/charter/governance.yaml",
        ".kittify/charter/directives.yaml",
        ".kittify/charter/metadata.yaml",
    ]
    for rel in derived:
        assert (tmp_path / rel).exists(), f"expected sync to write {rel}"
    gitignore = tmp_path / ".gitignore"
    existing = (
        gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    )
    gitignore_lines = sorted(set(existing.splitlines()) | set(derived))
    gitignore.write_text("\n".join(gitignore_lines) + "\n", encoding="utf-8")

    # 5. Validate the bundle.
    monkeypatch.chdir(tmp_path)
    validate_result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert validate_result.exit_code == 0, validate_result.output
    validate_payload = json.loads(validate_result.stdout)
    assert validate_payload["bundle_compliant"] is True
    assert validate_payload["result"] == "success"
    assert validate_payload["tracked_files"]["missing"] == []
