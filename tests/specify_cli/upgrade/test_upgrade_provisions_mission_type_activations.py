"""Fold for PR #3246: ``spec-kitty upgrade`` heals a missing
``mission_type_activations`` key for pre-rc39 (rc36-rc38) projects.

PR #3246 removed the implicit "all four built-ins" backfill and made mission
creation fail closed (``CharterPackConfigError``) whenever a project's
``.kittify/config.yaml`` lacks ``mission_type_activations``. Fresh
``spec-kitty init`` got a provisioner
(:func:`specify_cli.provisioning.default_charter.provision_default_mission_type_activations`),
but ``spec-kitty upgrade`` had no equivalent seeder for existing projects: the
only pre-existing seeder is the version-pinned
``3.2.0rc35_activate_builtin_mission_types`` migration, and
``MigrationRegistry.get_applicable``'s ``from_v < target <= to_v`` window
never selects a migration targeting a version at or below ``from_version`` —
so a project first initialised on rc36-rc38 (already past rc35) is stranded
on every subsequent ``upgrade``, even though the create-gate's own error
message tells the operator to run ``spec-kitty upgrade``.

This suite:

* pins the pre-fix defect directly at the create-gate (``existing_mission_types``
  / ``create_mission_core``) so the stranding is provable independent of any
  particular CLI wiring;
* proves ``spec-kitty upgrade`` now heals a stranded project (the exact
  ``from_version == target_version`` / no-applicable-migrations shape that
  the rc35 migration's version window can never reach);
* proves the heal is idempotent and never clobbers an authored empty list
  (mirroring ``tests/specify_cli/cli/commands/test_init_provisioning.py``'s
  fresh-init parity checks); and
* unit-pins the new ``_provision_missing_mission_type_activations`` CLI
  helper's dry-run and fail-closed behaviour in isolation.
"""

from __future__ import annotations

import subprocess
from kernel.clock import now_utc
from pathlib import Path

import pytest
import typer
from ruamel.yaml import YAML
from typer.testing import CliRunner

from charter.mission_type_profiles import existing_mission_types
from charter.pack_context import CharterPackConfigError
from specify_cli.cli.commands.upgrade import (
    _provision_missing_mission_type_activations,
    upgrade,
)
from specify_cli.core.mission_creation import create_mission_core
from specify_cli.provisioning import default_charter
from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.runner import MigrationRunner

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_SAFE_YAML = YAML(typ="safe")

_STRANDED_FROM_VERSION = "3.2.0rc37"  # past rc35, never re-selected by get_applicable


def _load_config(config_file: Path) -> dict:
    return _SAFE_YAML.load(config_file) or {}


def _write_stranded_project(project: Path, *, config_body: str = "vcs:\n  type: git\n") -> None:
    """Build a project pinned at ``_STRANDED_FROM_VERSION`` lacking the key.

    Mirrors a project first initialised on rc36-rc38: ``config.yaml`` has no
    ``mission_type_activations`` key, and ``metadata.yaml`` records a version
    already past the rc35 migration's ``target_version``.
    """
    kittify = project / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(config_body, encoding="utf-8")

    metadata = ProjectMetadata(
        version=_STRANDED_FROM_VERSION,
        initialized_at=now_utc(),
        python_version="3.11",
        platform="test",
        platform_version="test",
    )
    metadata.save(kittify)
    # Schema version must sit inside [MIN_SUPPORTED, MAX_SUPPORTED] or the
    # too-new/too-old CLI guards fire before the migration/provisioning path
    # this suite is exercising is ever reached.
    from specify_cli.migration.schema_version import MAX_SUPPORTED_SCHEMA

    MigrationRunner._stamp_schema_version(kittify, MAX_SUPPORTED_SCHEMA)


def _init_git_repo(repo: Path) -> None:
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)


_test_app = typer.Typer(add_completion=False)
_test_app.command()(upgrade)
_runner = CliRunner()


def _run_upgrade(args: list[str], cwd: Path) -> object:
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        return _runner.invoke(_test_app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# Pre-fix defect, pinned directly at the create-gate (independent of any
# particular upgrade-CLI wiring) — proves the stranding is real.
# ---------------------------------------------------------------------------


def test_stranded_project_fails_closed_at_the_create_gate(tmp_path: Path) -> None:
    """A config-absent-key project blocks mission creation with CharterPackConfigError."""
    project = tmp_path / "stranded"
    project.mkdir()
    _write_stranded_project(project)
    _init_git_repo(project)

    assert existing_mission_types(project) == []

    with pytest.raises(CharterPackConfigError, match="CHARTER_PACK_CONFIG_INVALID") as exc:
        create_mission_core(project, "stranded-mission", allow_worktree_context=True)
    assert "spec-kitty upgrade" in exc.value.body


# ---------------------------------------------------------------------------
# `spec-kitty upgrade` now heals the stranded project.
#
# from_version == target_version reproduces the exact "no applicable
# migration" shape MigrationRegistry.get_applicable produces once a project
# is already past rc35 — the CLI's "already up to date" branch, which
# bypasses MigrationRunner.upgrade() entirely and is the funnel the rc36-rc38
# stranding actually falls through.
# ---------------------------------------------------------------------------


def test_upgrade_heals_stranded_project_and_unblocks_mission_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "stranded"
    project.mkdir()
    _write_stranded_project(project)
    _init_git_repo(project)

    # Keep this test scoped to the provisioning fix: skip the (unrelated,
    # heavier) generated-surface repair that also runs on every upgrade.
    monkeypatch.setattr(
        "specify_cli.cli.commands.upgrade._run_upgrade_surface_repair",
        lambda *a, **k: None,
    )

    assert existing_mission_types(project) == []

    result = _run_upgrade(
        ["--target", _STRANDED_FROM_VERSION, "--force", "--no-worktrees"],
        cwd=project,
    )
    assert result.exit_code == 0, result.output

    config_data = _load_config(project / ".kittify" / "config.yaml")
    activations = config_data.get("mission_type_activations")
    assert activations, f"mission_type_activations still absent/empty after upgrade: {config_data}"

    assert existing_mission_types(project) != []

    created = create_mission_core(project, "healed-mission", allow_worktree_context=True)
    assert created.mission_slug.startswith("healed-mission-")


def test_upgrade_provisioning_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second real upgrade run leaves the healed activation list untouched."""
    project = tmp_path / "stranded"
    project.mkdir()
    _write_stranded_project(project)
    _init_git_repo(project)
    monkeypatch.setattr(
        "specify_cli.cli.commands.upgrade._run_upgrade_surface_repair",
        lambda *a, **k: None,
    )

    first = _run_upgrade(
        ["--target", _STRANDED_FROM_VERSION, "--force", "--no-worktrees"],
        cwd=project,
    )
    assert first.exit_code == 0, first.output
    config_file = project / ".kittify" / "config.yaml"
    after_first = config_file.read_text(encoding="utf-8")

    second = _run_upgrade(
        ["--target", _STRANDED_FROM_VERSION, "--force", "--no-worktrees"],
        cwd=project,
    )
    assert second.exit_code == 0, second.output
    after_second = config_file.read_text(encoding="utf-8")

    assert after_second == after_first


def test_upgrade_preserves_authored_empty_activation_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An authored empty list is a deliberate zero-types state, not a gap to heal."""
    project = tmp_path / "stranded"
    project.mkdir()
    _write_stranded_project(project, config_body="vcs:\n  type: git\nmission_type_activations: []\n")
    _init_git_repo(project)
    monkeypatch.setattr(
        "specify_cli.cli.commands.upgrade._run_upgrade_surface_repair",
        lambda *a, **k: None,
    )

    result = _run_upgrade(
        ["--target", _STRANDED_FROM_VERSION, "--force", "--no-worktrees"],
        cwd=project,
    )
    assert result.exit_code == 0, result.output

    config_data = _load_config(project / ".kittify" / "config.yaml")
    assert config_data["mission_type_activations"] == []
    # Still blocked -- an authored empty list is unchanged (C-008), so the
    # create-gate must still fail closed exactly as before the upgrade.
    assert existing_mission_types(project) == []
    with pytest.raises(CharterPackConfigError):
        create_mission_core(project, "still-empty-mission", allow_worktree_context=True)


# ---------------------------------------------------------------------------
# Unit-pin the new CLI helper in isolation (dry-run / fail-closed).
# ---------------------------------------------------------------------------


def test_provision_helper_is_noop_during_dry_run(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write_stranded_project(project)

    errors = _provision_missing_mission_type_activations(project, dry_run=True)

    assert errors == []
    config_data = _load_config(project / ".kittify" / "config.yaml")
    assert "mission_type_activations" not in config_data


def test_provision_helper_surfaces_missing_default_pack_as_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise_missing(name: str) -> Path:
        raise FileNotFoundError(f"missing pack {name!r}")

    monkeypatch.setattr(default_charter, "resolve_builtin_pack_path", _raise_missing)

    project = tmp_path / "project"
    project.mkdir()
    _write_stranded_project(project)

    errors = _provision_missing_mission_type_activations(project, dry_run=False)

    assert len(errors) == 1
    assert "default" in errors[0].lower()
