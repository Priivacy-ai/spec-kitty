"""Fresh-init integration test: ``.kittify/metadata.yaml`` carries
``spec_kitty.schema_version`` and ``spec_kitty.schema_capabilities``
after ``spec-kitty init``.

Issue #840 / WP02 (charter-e2e-hardening-tranche-2): pre-fix, init never
stamped these fields. The migration runner only set them on upgrade, leaving
fresh projects classified as ``UNMIGRATED`` and blocked by the schema gate
on the next non-upgrade command.

The assertion compares against the canonical constants from
``specify_cli.migration.runner`` so a future bump of the target schema
version automatically flows through both production code and the test.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console
from ruamel.yaml import YAML
from typer import Typer
from typer.testing import CliRunner

from specify_cli.cli.commands import init as _init_module
from specify_cli.cli.commands.init import register_init_command
from specify_cli.migration.runner import (
    _TARGET_SCHEMA_CAPABILITIES,
    _TARGET_SCHEMA_VERSION,
)

pytestmark = pytest.mark.fast


def _make_init_app() -> Typer:
    """Return a minimal Typer app with the init command registered."""
    app = Typer()
    console = Console(file=io.StringIO(), force_terminal=False)
    register_init_command(
        app,
        console=console,
        show_banner=lambda: None,
        activate_mission=lambda proj, mtype, mdisplay, _con: mdisplay,
        ensure_executable_scripts=lambda path, tracker=None: None,
    )
    return app


def _fake_copy_pkg(project_path: Path) -> Path:
    kittify = project_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    return kittify / "templates" / "command-templates"


def test_fresh_init_stamps_schema_version_and_capabilities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``spec-kitty init`` must populate the canonical schema fields in
    ``.kittify/metadata.yaml`` so fresh projects pass the migration gate.
    """
    app = _make_init_app()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        _init_module, "get_local_repo_root", lambda override_path=None: None
    )
    monkeypatch.setattr(
        _init_module, "copy_specify_base_from_package", _fake_copy_pkg
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", "fresh-schema-proj", "--ai", "codex", "--non-interactive"],
    )

    assert result.exit_code == 0, f"init failed: {result.output}"

    metadata_path = tmp_path / "fresh-schema-proj" / ".kittify" / "metadata.yaml"
    assert metadata_path.exists(), (
        f"init did not produce metadata.yaml at {metadata_path}"
    )

    yaml_io = YAML()
    with metadata_path.open("r", encoding="utf-8") as fh:
        data = yaml_io.load(fh)

    assert data is not None, "metadata.yaml is empty after init"
    spec_kitty_section = data.get("spec_kitty")
    assert spec_kitty_section is not None, (
        "metadata.yaml missing top-level 'spec_kitty' section"
    )

    # schema_version comes from the canonical migration-runner constant.
    assert "schema_version" in spec_kitty_section, (
        "metadata.yaml missing spec_kitty.schema_version after fresh init"
    )
    assert spec_kitty_section["schema_version"] == _TARGET_SCHEMA_VERSION, (
        "spec_kitty.schema_version drifted from canonical "
        f"_TARGET_SCHEMA_VERSION={_TARGET_SCHEMA_VERSION}"
    )

    # schema_capabilities must match the canonical 4-item list, order-sensitive.
    assert "schema_capabilities" in spec_kitty_section, (
        "metadata.yaml missing spec_kitty.schema_capabilities after fresh init"
    )
    capabilities = spec_kitty_section["schema_capabilities"]
    assert list(capabilities) == list(_TARGET_SCHEMA_CAPABILITIES), (
        "spec_kitty.schema_capabilities does not match canonical "
        f"_TARGET_SCHEMA_CAPABILITIES={_TARGET_SCHEMA_CAPABILITIES}"
    )
