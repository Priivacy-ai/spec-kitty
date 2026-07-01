"""Regression test: legacy curation subcommands must be unknown.

Guards against reintroduction of the curation CLI surface deleted in
Phase 1 (WP01 of mission
``excise-doctrine-curation-and-inline-references-01KP54J6``).

See EPIC #461 / Phase 1 issue #463 / WP issue #476.

The ``doctrine`` parent group itself IS registered — it carries the
DRG-era org-layer authoring commands (fetch, new, validate, pack, org)
added by mission ``layered-doctrine-org-layer-01KRNPEE``.  Only the
pre-DRG curation commands (curate, promote, reset, status) must remain
absent.

Note: ``test_doctrine_parent_group_is_unregistered`` was removed because
its premise became stale.  The test was written before the layered-doctrine
mission re-added the group with entirely different commands; treating it as
authoritative caused the entire DRG authoring surface to be incorrectly
deregistered (see PR #1352 discussion).
"""

from __future__ import annotations

from typer.testing import CliRunner

from specify_cli import app


import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_doctrine_curate_is_unknown_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctrine", "curate"])
    assert result.exit_code != 0


def test_doctrine_promote_is_unknown_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctrine", "promote"])
    assert result.exit_code != 0


def test_doctrine_group_is_registered() -> None:
    """The doctrine parent group must be reachable — it carries DRG authoring commands."""
    runner = CliRunner()
    result = runner.invoke(app, ["doctrine", "--help"])
    assert result.exit_code == 0
