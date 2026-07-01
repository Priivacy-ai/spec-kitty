"""CLI tests for ``spec-kitty doctrine new`` (FR-016, WP09 T048).

The scaffolder MUST write a YAML file that:

1. lands at ``<root>/<singular>/<id>.<kind>.yaml`` for project mode,
2. carries a pre-filled stub passing the canonical Pydantic schema for that
   kind, so a subsequent ``doctrine validate`` exits 0 on first emit, and
3. refuses to overwrite an existing file.

These behaviours are pinned here so a future schema tightening (e.g. an
extra required field on ``Styleguide``) fails fast in CI instead of
silently producing invalid stubs.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.doctrine import app as doctrine_app

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()


def _make_project_root(tmp_path: Path) -> Path:
    """Create the minimum ``.kittify/`` skeleton so ``locate_project_root`` succeeds."""
    (tmp_path / ".kittify").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_new_styleguide_writes_stub_under_project_doctrine_root(tmp_path: Path) -> None:
    """``doctrine new styleguide foo`` lands the stub at the canonical path."""
    project = _make_project_root(tmp_path)

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            doctrine_app, ["new", "styleguide", "foo"], catch_exceptions=False
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.stdout
    target = project / ".kittify" / "doctrine" / "styleguide" / "foo.styleguide.yaml"
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    # The stub MUST carry the schema-version + id fields the operator
    # will fill in around.  We avoid pinning the exact placeholder text
    # so wording can evolve without bricking this test.
    assert "schema_version" in text
    assert "id: foo" in text


def test_new_validates_stub_against_schema_so_validate_passes(tmp_path: Path) -> None:
    """The scaffolded stub MUST pass ``doctrine validate`` on first emit."""
    project = _make_project_root(tmp_path)

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result_new = runner.invoke(
            doctrine_app, ["new", "tactic", "my-tactic"], catch_exceptions=False
        )
        assert result_new.exit_code == 0, result_new.stdout

        target = (
            project / ".kittify" / "doctrine" / "tactic" / "my-tactic.tactic.yaml"
        )
        assert target.exists()

        result_validate = runner.invoke(
            doctrine_app, ["validate", str(target)], catch_exceptions=False
        )
    finally:
        os.chdir(old_cwd)

    assert result_validate.exit_code == 0, result_validate.stdout
    assert "OK" in result_validate.stdout


@pytest.mark.parametrize(
    ("kind", "artifact_id", "plural", "filename"),
    [
        ("agent_profile", "sample-agent", "agent_profiles", "sample-agent.agent.yaml"),
        (
            "mission_step_contract",
            "sample-step",
            "mission_step_contracts",
            "sample-step.step-contract.yaml",
        ),
    ],
)
def test_new_special_kind_suffixes_validate_on_first_emit(
    tmp_path: Path,
    kind: str,
    artifact_id: str,
    plural: str,
    filename: str,
) -> None:
    """Special-kind scaffold filenames MUST match ``doctrine validate`` suffixes."""
    project = _make_project_root(tmp_path)

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result_new = runner.invoke(
            doctrine_app, ["new", kind, artifact_id], catch_exceptions=False
        )
        assert result_new.exit_code == 0, result_new.stdout

        target = project / ".kittify" / "doctrine" / plural / filename
        assert target.exists()

        result_validate = runner.invoke(
            doctrine_app, ["validate", str(target)], catch_exceptions=False
        )
    finally:
        os.chdir(old_cwd)

    assert result_validate.exit_code == 0, result_validate.stdout
    assert "OK" in result_validate.stdout


def test_new_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    """Re-running ``doctrine new`` on the same id fails with a clear message."""
    project = _make_project_root(tmp_path)

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        first = runner.invoke(
            doctrine_app, ["new", "directive", "MY_DIRECTIVE"], catch_exceptions=False
        )
        assert first.exit_code == 0, first.stdout

        second = runner.invoke(
            doctrine_app, ["new", "directive", "MY_DIRECTIVE"], catch_exceptions=False
        )
    finally:
        os.chdir(old_cwd)

    assert second.exit_code == 1
    assert "Refusing to overwrite" in second.stdout


def test_new_rejects_unknown_kind(tmp_path: Path) -> None:
    """An unsupported artifact kind exits 2 with the valid-kinds list."""
    project = _make_project_root(tmp_path)

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            doctrine_app, ["new", "guideline", "foo"], catch_exceptions=False
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 2
    assert "Unknown artifact kind" in result.stdout
    # The valid-kinds list MUST surface so operators can self-correct.
    assert "directive" in result.stdout
    assert "styleguide" in result.stdout


def test_new_with_pack_targets_explicit_pack_root(tmp_path: Path) -> None:
    """``--pack`` writes inside the supplied pack directory, not the project root."""
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()

    # No project root needed — pack mode bypasses locate_project_root.
    result = runner.invoke(
        doctrine_app,
        ["new", "paradigm", "test-paradigm", "--pack", str(pack_dir)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.stdout
    target = pack_dir / "paradigms" / "test-paradigm.paradigm.yaml"
    assert target.exists()
