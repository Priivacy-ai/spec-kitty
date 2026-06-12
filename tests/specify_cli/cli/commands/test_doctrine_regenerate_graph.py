"""CLI tests for ``spec-kitty doctrine regenerate-graph`` (WP09 / FR-009).

Covers the operator-facing regeneration surface:

1. ``--check --json`` reports the committed shipped graph as fresh (exit 0),
2. regenerate-twice produces byte-identical output (determinism),
3. ``--check`` against a deliberately corrupted graph reports stale (exit 1).

The committed ``src/doctrine/graph.yaml`` is never mutated: write-mode tests
target a temporary doctrine root assembled from the shipped one.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.doctrine import app as doctrine_app

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

DOCTRINE_ROOT = Path(__file__).resolve().parents[4] / "src" / "doctrine"


def test_check_reports_committed_graph_fresh() -> None:
    """The shipped graph must be fresh — operator twin of the freshness gate."""
    result = runner.invoke(
        doctrine_app, ["regenerate-graph", "--check", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "fresh"
    assert payload["path"].endswith("src/doctrine/graph.yaml")


def test_regenerate_twice_is_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Write-mode regeneration is deterministic across two runs."""
    # Assemble a working-tree-shaped doctrine root the resolver will discover.
    fake_repo = tmp_path / "repo"
    fake_doctrine = fake_repo / "src" / "doctrine"
    fake_doctrine.parent.mkdir(parents=True)
    shutil.copytree(DOCTRINE_ROOT, fake_doctrine)
    monkeypatch.chdir(fake_repo)

    graph_path = fake_doctrine / "graph.yaml"

    r1 = runner.invoke(doctrine_app, ["regenerate-graph"])
    assert r1.exit_code == 0, r1.output
    first = graph_path.read_bytes()

    r2 = runner.invoke(doctrine_app, ["regenerate-graph"])
    assert r2.exit_code == 0, r2.output
    second = graph_path.read_bytes()

    assert first == second, "regenerate-graph is not idempotent"


def test_check_detects_stale_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corrupted committed graph is reported stale with exit code 1."""
    fake_repo = tmp_path / "repo"
    fake_doctrine = fake_repo / "src" / "doctrine"
    fake_doctrine.parent.mkdir(parents=True)
    shutil.copytree(DOCTRINE_ROOT, fake_doctrine)
    monkeypatch.chdir(fake_repo)

    graph_path = fake_doctrine / "graph.yaml"
    graph_path.write_text(
        graph_path.read_text(encoding="utf-8") + "\n# stale drift marker\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        doctrine_app, ["regenerate-graph", "--check", "--json"]
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "stale"
