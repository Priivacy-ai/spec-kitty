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
from ruamel.yaml import YAML
from typer.testing import CliRunner

from specify_cli.cli.commands.doctrine import app as doctrine_app

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

DOCTRINE_ROOT = Path(__file__).resolve().parents[4] / "src" / "doctrine"

#: WP05 / FR-009 / C-003 — orphan-count regression ceiling.
#:
#: After repairing the phantom ``java-implementer`` reference and wiring the
#: refactoring-procedure → Fowler-catalog and mutation-workflow → mutation-tools
#: inbound edges, the shipped DRG carries 14 orphaned-but-valid doctrine
#: artifacts. Each is a deliberately-authored artifact with no single natural
#: referent and is documented (with per-orphan rationale) in
#: ``kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md``.
#:
#: D-C2 / C-003 forbid deleting valid orphans to shrink this metric. This ceiling
#: is a regression guard against the count silently *growing* — a new orphan must
#: either be wired or added to the documented residual (and this ceiling raised
#: with a rationale). It is NOT a mandate to prune to reach a lower number.
DOCUMENTED_ORPHAN_RESIDUAL = 14


def _count_orphans(graph_path: Path) -> int:
    """Return the number of nodes with no inbound or outbound edge."""
    data = YAML(typ="safe").load(graph_path)
    urns = {node["urn"] for node in data["nodes"]}
    incident: set[str] = set()
    for edge in data["edges"]:
        incident.add(edge["source"])
        incident.add(edge["target"])
    return len(urns - incident)


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


def test_shipped_graph_orphan_count_within_documented_residual() -> None:
    """Orphan count must not exceed the documented residual (WP05 / C-003).

    Guards against orphan growth without forcing valid-artifact deletion: a new
    orphan must be wired or added to the documented residual (raising the
    ceiling with rationale), per the no-bulk-delete correction (D-C2).
    """
    orphans = _count_orphans(DOCTRINE_ROOT / "graph.yaml")
    assert orphans <= DOCUMENTED_ORPHAN_RESIDUAL, (
        f"DRG orphan count {orphans} exceeds documented residual "
        f"{DOCUMENTED_ORPHAN_RESIDUAL}; wire a real inbound edge or update "
        f"drg-orphan-residual.md and raise the ceiling with rationale."
    )


def test_phantom_java_implementer_node_is_absent() -> None:
    """The repaired java-implementer reference must not mint a phantom node."""
    data = YAML(typ="safe").load(DOCTRINE_ROOT / "graph.yaml")
    urns = {node["urn"] for node in data["nodes"]}
    assert "agent_profile:java-implementer" not in urns
    assert "agent_profile:java-jenny" in urns
