"""WP04 (#3530): the org ``drg/fragment.yaml`` layer reaches the executor path.

The mission-step composition dispatch resolved its DRG through
``StepContractExecutor._load_graph_degrading_malformed_org_pack``, which threaded
only ``org_roots`` (a pack's root-level ``*.graph.yaml``) and never the
``org_fragments`` layer. So a pack shipping only ``drg/fragment.yaml`` -- this
repo's own ``packs/internal`` shape -- was silently dropped on this path: the
branch-named silent drop this WP closes.

Red-first: :func:`test_valid_fragment_only_pack_node_reaches_merged_graph`
FAILS before T017 (the fragment node never reaches the merged graph) and passes
after ``org_fragments`` is threaded. This is deliberately a *valid* fragment --
the pre-existing degrade test in ``test_executor.py`` uses a *malformed* one and
only covers the graceful-degrade, never a valid fragment's nodes being folded.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from charter.drg import resolve_existing_org_roots
from charter.mission_steps import MissionStepContract, MissionStepContractStep
from doctrine.drg.validator import DRGValidationError
from specify_cli.mission_step_contracts.executor import (
    StepContractExecutionContext,
    StepContractExecutor,
)

pytestmark = pytest.mark.fast

_EXECUTOR_LOGGER = "specify_cli.mission_step_contracts.executor"
_TARGET_URN = "directive:OPERATOR_SIGNAL_CONTRACT"
_DROP_WARNING = "without this org pack's contribution"


def _register_pack(repo_root: Path, org_root: Path, *, name: str = "test-org") -> None:
    kit = repo_root / ".kittify"
    kit.mkdir(parents=True, exist_ok=True)
    (kit / "config.yaml").write_text(
        yaml.safe_dump(
            {"doctrine": {"org": {"packs": [{"name": name, "local_path": str(org_root)}]}}}
        ),
        encoding="utf-8",
    )


def _write_fragment_pack(
    repo_root: Path,
    *,
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]] | None = None,
    register: bool = True,
) -> Path:
    """Materialise a fragment-only org pack (``drg/fragment.yaml``, no root graph)."""
    org_root = repo_root.parent / "org-pack"
    (org_root / "drg").mkdir(parents=True, exist_ok=True)
    (org_root / "drg" / "fragment.yaml").write_text(
        yaml.safe_dump(
            {
                "pack_name": "test-org",
                "source_kind": "local_path",
                "source_ref": "org-pack",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": nodes,
                "edges": edges or [],
            }
        ),
        encoding="utf-8",
    )
    if register:
        _register_pack(repo_root, org_root)
    return org_root


def test_valid_fragment_only_pack_node_reaches_merged_graph(tmp_path: Path) -> None:
    """A valid fragment-only pack's node must reach the executor's merged DRG.

    Red-first before T017: without ``org_fragments`` threading, this directive
    -- authored only in ``drg/fragment.yaml`` -- never entered the graph the
    composition dispatch resolves against.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_fragment_pack(
        repo,
        nodes=[
            {
                "id": "OPERATOR_SIGNAL_CONTRACT",
                "kind": "directives",
                "title": "Operator-Signal Contract",
            }
        ],
    )
    roots = resolve_existing_org_roots(repo)

    graph = StepContractExecutor._load_graph_degrading_malformed_org_pack(repo, roots)

    assert _TARGET_URN in {str(node.urn) for node in graph.nodes}


def test_fragment_node_and_edge_are_folded_once_not_twice(tmp_path: Path) -> None:
    """No-double-fold: a pack in BOTH ``org_roots`` and ``org_fragments`` folds once.

    The fix threads ``org_fragments`` at the caller, NOT at the ``org_roots=``
    seam. Fixing at the seam would double-fold for the four callers that already
    pass both lists. This pins the caller-level guarantee: the fragment's node
    and edge appear exactly ``n`` (== 1) times in the merged graph, never ``2n``,
    even though ``resolve_existing_org_roots`` also returns this pack's root.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_fragment_pack(
        repo,
        nodes=[
            {"id": "FRAG_DIR_A", "kind": "directives", "title": "Frag Directive A"},
            {"id": "FRAG_DIR_B", "kind": "directives", "title": "Frag Directive B"},
        ],
        edges=[{"source": "FRAG_DIR_A", "target": "FRAG_DIR_B", "relation": "refines"}],
    )
    roots = resolve_existing_org_roots(repo)
    assert roots, "pack must be resolved into org_roots for the dual-path check"

    graph = StepContractExecutor._load_graph_degrading_malformed_org_pack(repo, roots)

    node_count = sum(1 for node in graph.nodes if str(node.urn) == "directive:FRAG_DIR_A")
    edge_count = sum(
        1
        for edge in graph.edges
        if (str(edge.source), str(edge.target), edge.relation.value)
        == ("directive:FRAG_DIR_A", "directive:FRAG_DIR_B", "refines")
    )

    assert node_count == 1
    assert edge_count == 1


def test_fragment_only_pack_does_not_emit_false_drop_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Warning honesty: a folded fragment-only pack is not warned as dropped.

    ``load_graph_or_dir`` cannot read a fragment-shaped pack (root graphs only),
    but its content DOES arrive via ``org_fragments``. Emitting the
    "without this org pack's contribution" WARNING would misattribute a folded
    pack as a dropped one, so the pre-probe degrades to DEBUG for it.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_fragment_pack(
        repo,
        nodes=[
            {
                "id": "OPERATOR_SIGNAL_CONTRACT",
                "kind": "directives",
                "title": "Operator-Signal Contract",
            }
        ],
    )
    roots = resolve_existing_org_roots(repo)

    with caplog.at_level(logging.WARNING, logger=_EXECUTOR_LOGGER):
        StepContractExecutor._load_graph_degrading_malformed_org_pack(repo, roots)

    assert not [r for r in caplog.records if _DROP_WARNING in r.getMessage()]


def test_graphless_and_fragmentless_root_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Warning honesty: a root with no graph AND no loadable fragment warns.

    The honesty suppression is narrow -- it applies only when the fragment
    genuinely folds. A root that contributes nothing (no root ``*.graph.yaml``
    and no ``drg/fragment.yaml``) is a real drop and still emits the WARNING.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    empty_root = tmp_path / "empty-pack"
    empty_root.mkdir()

    with caplog.at_level(logging.WARNING, logger=_EXECUTOR_LOGGER):
        StepContractExecutor._load_graph_degrading_malformed_org_pack(
            repo, [empty_root]
        )

    warnings = [r for r in caplog.records if _DROP_WARNING in r.getMessage()]
    assert len(warnings) == 1


class _StubInvocationExecutor:
    """Never invoked: merged-graph validation fails before any step dispatch."""


def test_org_governance_selection_fails_loud_on_executor_path(
    tmp_path: Path,
) -> None:
    """The executor's own DRG build fails loud on a bad org governance selection.

    An org-tier ``governance-profile.yaml`` selecting a nonexistent artifact is
    minted as a dangling ``mission_type --scope--> <artifact>`` edge (WP04's real
    fix). The executor builds its graph through
    ``_load_graph_degrading_malformed_org_pack`` ->
    :func:`charter._drg_helpers.load_validated_graph`, whose ``assert_valid``
    raises :class:`~doctrine.drg.validator.DRGValidationError` naming the dangling
    target -- no dedicated governance-scope guard needed. Driven here through the
    production graph-build path (no injected ``graph``), so the merged-graph
    validation is the real escalation exercised; the stub invocation executor is
    never reached.
    """
    org_root = _write_fragment_pack(
        tmp_path,
        nodes=[{"id": "FRAG_MARKER", "kind": "directives", "title": "marker"}],
    )
    gov_dir = org_root / "mission_types" / "plan"
    gov_dir.mkdir(parents=True)
    (gov_dir / "governance-profile.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "plan",
                "mission_type": "plan",
                "selected_directives": ["THIS_DIRECTIVE_DOES_NOT_EXIST"],
            }
        ),
        encoding="utf-8",
    )

    contract = MissionStepContract(
        id="c",
        schema_version="1.0",
        action="composer",
        mission="fixture",
        steps=[MissionStepContractStep(id="s", description="d")],
        gates=[],
    )
    executor = StepContractExecutor(
        repo_root=tmp_path,
        invocation_executor=_StubInvocationExecutor(),  # type: ignore[arg-type]
    )

    with pytest.raises(DRGValidationError, match=r"THIS_DIRECTIVE_DOES_NOT_EXIST"):
        executor.execute(
            StepContractExecutionContext(
                repo_root=tmp_path,
                mission="fixture",
                action="composer",
                actor="pytest",
                profile_hint="implementer-fixture",
            ),
            contract=contract,
        )
