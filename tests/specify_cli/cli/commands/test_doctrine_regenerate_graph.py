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
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from doctrine.drg.loader import load_built_in_graph
from specify_cli.cli.commands.doctrine import app as doctrine_app

if TYPE_CHECKING:
    from doctrine.drg.models import DRGGraph

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

DOCTRINE_ROOT = Path(__file__).resolve().parents[4] / "src" / "doctrine"


def _graph_files(doctrine_dir: Path) -> list[Path]:
    """Return the DRG graph source files under *doctrine_dir* (layout-agnostic).

    Mirrors :func:`doctrine.drg.loader.load_graph_or_dir` / the shape of
    :func:`built_in_graph_source`: the ``graph.yaml`` monolith when present,
    otherwise the ``*.graph.yaml`` fragments. This lets per-file byte-identity
    assertions survive the WP05 monolith->fragment flip with no edit (DD-11).
    """
    single = doctrine_dir / "graph.yaml"
    if single.is_file():
        return [single]
    return sorted(doctrine_dir.glob("*.graph.yaml"))

#: WP05 / FR-009 / C-003 — orphan-count regression ceiling.
#:
#: After repairing the phantom ``java-implementer`` reference and wiring the
#: refactoring-procedure → Fowler-catalog and mutation-workflow → mutation-tools
#: inbound edges, the shipped DRG carried 14 orphaned-but-valid doctrine
#: artifacts. Each is a deliberately-authored artifact with no single natural
#: referent and is documented (with per-orphan rationale) in
#: ``kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md``.
#:
#: 2026-07-16 (ceiling stays 14; empirical residual 10): an interim curation pass
#: had briefly raised this to 18 to *accept* 8 structural mission-type nodes
#: (``mission_type:{documentation,plan,research,software-dev}`` +
#: ``action:plan/{plan,research,review,specify}``) as edgeless residuals, because
#: the generator emitted mission-type nodes nodes-only pending a deferred
#: S0-continuation edge feature. **Mission ``mission-type-drg-edges-01KXKY2N``
#: (#2677) implemented that feature**: the generator now emits
#: ``mission_type:X → action:X/<step>`` ``requires`` edges from each type's
#: ``action_sequence`` (21 edges), so all 8 structural nodes are wired and leave
#: the orphan set — the 18 raise is reverted to 14. In the same pass 4 of the
#: original residuals were found already-wired (stale rows), taking the empirical
#: residual from 14 to **10**. Full narrative + the 10 surviving rows are in
#: ``drg-orphan-residual.md``.
#:
#: D-C2 / C-003 forbid deleting valid orphans to shrink this metric. This ceiling
#: is a regression guard against the count silently *growing* — a new orphan must
#: either be wired or added to the documented residual (and this ceiling raised
#: with a rationale). It is NOT a mandate to prune to reach a lower number. The
#: ceiling stays at the historical 14 baseline (empirical 10 leaves 4 slack, by
#: deliberate D-C2 choice — a growth guard, not a pin to the current count).
DOCUMENTED_ORPHAN_RESIDUAL = 14


def _count_orphans(graph: DRGGraph) -> int:
    """Return the number of nodes with no inbound or outbound edge.

    Operates on a loaded :class:`~doctrine.drg.models.DRGGraph` so the caller can
    read *whatever layout is on disk* through the seam (monolith today, fragments
    post-WP05) rather than re-parsing a hardcoded ``graph.yaml`` path.
    """
    urns = {node.urn for node in graph.nodes}
    incident: set[str] = set()
    for edge in graph.edges:
        incident.add(edge.source)
        incident.add(edge.target)
    return len(urns - incident)


def test_check_reports_committed_graph_fresh() -> None:
    """The shipped graph must be fresh — operator twin of the freshness gate.

    Freshness is asserted via the ``--check`` result (exit 0 + ``status ==
    'fresh'``), not the reported path shape: a ``payload['path'].endswith(
    'graph.yaml')`` assertion would break the instant WP05 replaces the monolith
    with ``*.graph.yaml`` fragments.
    """
    result = runner.invoke(
        doctrine_app, ["regenerate-graph", "--check", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "fresh"


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

    r1 = runner.invoke(doctrine_app, ["regenerate-graph"])
    assert r1.exit_code == 0, r1.output
    first = {p.name: p.read_bytes() for p in _graph_files(fake_doctrine)}
    assert first, "regenerate-graph produced no graph source files"

    r2 = runner.invoke(doctrine_app, ["regenerate-graph"])
    assert r2.exit_code == 0, r2.output
    second = {p.name: p.read_bytes() for p in _graph_files(fake_doctrine)}

    # DD-11: per-file byte-identity over the on-disk graph source (the
    # ``graph.yaml`` monolith today, ``*.graph.yaml`` fragments after WP05).
    assert first == second, "regenerate-graph is not idempotent (per-file byte drift)"


def test_check_detects_stale_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corrupted committed graph is reported stale with exit code 1."""
    fake_repo = tmp_path / "repo"
    fake_doctrine = fake_repo / "src" / "doctrine"
    fake_doctrine.parent.mkdir(parents=True)
    shutil.copytree(DOCTRINE_ROOT, fake_doctrine)
    monkeypatch.chdir(fake_repo)

    # Corrupt whichever graph source file is on disk (monolith today, a fragment
    # after WP05) so the committed graph drifts from a fresh regeneration.
    stale_target = _graph_files(fake_doctrine)[0]
    stale_target.write_text(
        stale_target.read_text(encoding="utf-8") + "\n# stale drift marker\n",
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
    orphans = _count_orphans(load_built_in_graph())
    assert orphans <= DOCUMENTED_ORPHAN_RESIDUAL, (
        f"DRG orphan count {orphans} exceeds documented residual "
        f"{DOCUMENTED_ORPHAN_RESIDUAL}; wire a real inbound edge or update "
        f"drg-orphan-residual.md and raise the ceiling with rationale."
    )


def test_phantom_java_implementer_node_is_absent() -> None:
    """The repaired java-implementer reference must not mint a phantom node."""
    graph = load_built_in_graph()
    urns = {node.urn for node in graph.nodes}
    assert "agent_profile:java-implementer" not in urns
    assert "agent_profile:java-jenny" in urns
