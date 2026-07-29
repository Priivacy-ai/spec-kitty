"""CLI tests for ``spec-kitty doctrine asset`` (WP05, T026/T027).

The asset operator surface is a *read-only* window over the WP04 resolution
repository (:class:`doctrine.assets.repository.AssetRepository`, reached through
:class:`doctrine.service.DoctrineService` ``.assets``):

* ``asset list [--json]`` enumerates every resolvable asset with its source tier.
* ``asset path <id> [--json]`` resolves one identifier to a filesystem path,
  exiting 0 on success and non-zero — with the id named — on an unknown id (A-7).

Nothing here installs anything (C-002); these tests assert resolution only.
They run in-process against the dev layout; the falsifiable clean-environment
proof (SC-003) lives in ``tests/docs/test_asset_resolution_wheel.py``.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.doctrine import app as doctrine_app

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

#: The single built-in asset shipped today (WP04). Its blob is the structural
#: docs-lint script; the manifest declares this stable identifier.
_SHIPPED_ASSET_ID = "common-docs-structural-lint"


def test_asset_path_resolves_shipped_asset() -> None:
    """``asset path <shipped-id>`` prints an existing filesystem path, exit 0."""
    from pathlib import Path

    result = runner.invoke(
        doctrine_app,
        ["asset", "path", _SHIPPED_ASSET_ID],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    resolved = Path(result.output.strip())
    assert resolved.is_file(), f"resolved path does not exist: {resolved}"
    assert resolved.name == "docs_structural_lint.py"


def test_asset_path_json_carries_id_path_and_tier() -> None:
    """``asset path <id> --json`` emits a machine-readable id/path/tier record."""
    result = runner.invoke(
        doctrine_app,
        ["asset", "path", _SHIPPED_ASSET_ID, "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["id"] == _SHIPPED_ASSET_ID
    assert payload["tier"] == "builtin"
    assert payload["path"].endswith("docs_structural_lint.py")


def test_asset_path_unknown_id_exits_nonzero_naming_it() -> None:
    """An unknown asset id exits non-zero and names the offending id (A-7)."""
    result = runner.invoke(
        doctrine_app,
        ["asset", "path", "no-such-asset-xyz"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "no-such-asset-xyz" in result.output


def test_asset_list_includes_shipped_asset_and_tier() -> None:
    """``asset list`` names the shipped asset and its built-in tier."""
    result = runner.invoke(
        doctrine_app,
        ["asset", "list"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert _SHIPPED_ASSET_ID in result.output
    assert "builtin" in result.output


def test_asset_list_json_is_a_record_list() -> None:
    """``asset list --json`` yields a list of id/tier/path records."""
    result = runner.invoke(
        doctrine_app,
        ["asset", "list", "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    shipped = next(row for row in payload if row["id"] == _SHIPPED_ASSET_ID)
    assert shipped["tier"] == "builtin"
    assert shipped["path"].endswith("docs_structural_lint.py")
