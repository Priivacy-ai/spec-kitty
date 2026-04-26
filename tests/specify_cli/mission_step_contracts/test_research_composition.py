"""Composition tests for the five `research` mission step contracts.

This file mirrors ``test_software_dev_composition.py`` but at the substrate
level: it asserts the four pieces that the mission-composition runtime needs
in order to dispatch a `research/<action>` invocation actually line up:

1. The shipped step contract for each research action loads through
   :class:`MissionStepContractRepository`.
2. ``_ACTION_PROFILE_DEFAULTS`` carries the agreed default profile for each
   `("research", action)` pair.
3. Each action's doctrine bundle (``src/doctrine/missions/research/actions/
   <action>/index.yaml``) exists and parses to non-empty governance content.
4. The merged DRG resolves a non-empty governance context for each
   `action:research/<action>` URN at the same depth the composer uses.
5. Sentinel: the existing ``software-dev`` profile-default entries were not
   touched while adding the research entries.

These tests intentionally read the live shipped DRG via
``charter._drg_helpers.load_validated_graph`` and the production resolver
``doctrine.drg.query.resolve_context`` (mission spec C-007 forbids mocking
either surface). The composer's higher-level dispatch surfaces
(``_dispatch_via_composition``, ``StepContractExecutor.execute``,
``ProfileInvocationExecutor.invoke``, ``_load_frozen_template``) are also
not mocked here -- this gate proves the *substrate* is wired, not dispatch.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from charter._drg_helpers import load_validated_graph
from doctrine.drg.query import resolve_context
from doctrine.mission_step_contracts.repository import MissionStepContractRepository
from specify_cli.mission_step_contracts.executor import _ACTION_PROFILE_DEFAULTS


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Five canonical research actions covered by the research mission runtime.
RESEARCH_ACTIONS: tuple[str, ...] = (
    "scoping",
    "methodology",
    "gathering",
    "synthesis",
    "output",
)

# Expected default agent profile for each research action -- matches the
# additions to ``_ACTION_PROFILE_DEFAULTS`` in WP04 (T017).
EXPECTED_RESEARCH_PROFILES: dict[str, str] = {
    "scoping": "researcher-robbie",
    "methodology": "researcher-robbie",
    "gathering": "researcher-robbie",
    "synthesis": "researcher-robbie",
    "output": "reviewer-renata",
}

# Mirror the literal default of ``StepContractExecutionContext.resolution_depth``
# (see ``src/specify_cli/mission_step_contracts/executor.py``). The composer
# calls ``resolve_context(graph, action_urn, depth=context.resolution_depth)``
# so this is the depth that has to produce non-empty governance context for
# the research actions.
COMPOSITION_DEPTH: int = 2

# Sentinel: the software-dev profile defaults predate this WP. Any drift here
# (rename, removal, profile substitution) is out-of-scope for WP04 and
# indicates a regression elsewhere.
EXPECTED_SOFTWARE_DEV_PROFILES: dict[str, str] = {
    "specify": "researcher-robbie",
    "plan": "architect-alphonso",
    "tasks": "architect-alphonso",
    "implement": "implementer-ivan",
    "review": "reviewer-renata",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Locate the repository root that holds ``src/doctrine/graph.yaml``."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "src" / "doctrine" / "graph.yaml").is_file():
            return parent
    raise RuntimeError(
        "Could not locate repo root containing src/doctrine/graph.yaml"
    )


def _action_index_path(action: str) -> Path:
    """Resolve the shipped action doctrine bundle index for a research action."""
    return (
        _repo_root()
        / "src"
        / "doctrine"
        / "missions"
        / "research"
        / "actions"
        / action
        / "index.yaml"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("action", RESEARCH_ACTIONS)
def test_all_research_contracts_load(action: str) -> None:
    """Each research step contract loads cleanly through the repository."""
    repo = MissionStepContractRepository()
    contract = repo.get_by_action("research", action)

    assert contract is not None, (
        f"Missing shipped contract for research/{action}; expected a file at "
        f"src/doctrine/mission_step_contracts/shipped/research-{action}.step-contract.yaml"
    )
    assert contract.mission == "research"
    assert contract.action == action


@pytest.mark.parametrize("action", RESEARCH_ACTIONS)
def test_research_profile_defaults_resolved(action: str) -> None:
    """``_ACTION_PROFILE_DEFAULTS`` returns the agreed default for each action."""
    expected = EXPECTED_RESEARCH_PROFILES[action]
    assert _ACTION_PROFILE_DEFAULTS[("research", action)] == expected, (
        f"Expected profile_id {expected!r} for ('research', {action!r}) in "
        f"_ACTION_PROFILE_DEFAULTS; got "
        f"{_ACTION_PROFILE_DEFAULTS.get(('research', action))!r}."
    )


@pytest.mark.parametrize("action", RESEARCH_ACTIONS)
def test_research_doctrine_bundle_resolved(action: str) -> None:
    """Each action's doctrine bundle exists and declares non-empty content.

    The bundle is the YAML index file at
    ``src/doctrine/missions/research/<action>/index.yaml``. The DRG extractor
    (``doctrine.drg.migration.extractor``) compiles ``directives``, ``tactics``,
    ``styleguides``, ``toolguides``, and ``procedures`` from this file into
    ``scope`` edges from the ``action:research/<action>`` node. If every
    list is empty, the action node has no scoped artifacts and the composer
    will see an empty resolved context.
    """
    index_path = _action_index_path(action)
    assert index_path.is_file(), (
        f"Missing action doctrine bundle index: {index_path}"
    )

    with index_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, dict), (
        f"Expected dict from {index_path}; got {type(data).__name__}"
    )
    assert data.get("action") == action, (
        f"Bundle action mismatch in {index_path}: declared "
        f"{data.get('action')!r}, expected {action!r}"
    )

    # At least one of the scope-bearing fields must be non-empty so the DRG
    # has something to scope to the action node.
    scope_fields = (
        "directives",
        "tactics",
        "styleguides",
        "toolguides",
        "procedures",
    )
    total = sum(len(data.get(field) or []) for field in scope_fields)
    assert total > 0, (
        f"Action doctrine bundle {index_path} declares no directives, "
        f"tactics, styleguides, toolguides, or procedures; the composer "
        f"would resolve an empty governance context for "
        f"action:research/{action}."
    )


@pytest.mark.parametrize("action", RESEARCH_ACTIONS)
def test_research_drg_node_resolves_non_empty_context(action: str) -> None:
    """Each `action:research/<action>` node resolves a non-empty context.

    Uses the *real* composition resolver
    (``doctrine.drg.query.resolve_context``) and the *real*
    ``charter._drg_helpers.load_validated_graph`` -- neither is mocked
    (mission spec C-007). The depth matches the composer's default
    (``StepContractExecutionContext.resolution_depth = 2``).
    """
    graph = load_validated_graph(_repo_root())
    urn = f"action:research/{action}"

    node = graph.get_node(urn)
    assert node is not None, (
        f"Missing DRG node {urn}; the composer cannot dispatch research/{action}."
    )

    ctx = resolve_context(graph, urn, depth=COMPOSITION_DEPTH)
    assert ctx.artifact_urns, (
        f"resolve_context returned an empty artifact_urns set for {urn} at "
        f"depth={COMPOSITION_DEPTH}; the composer would receive nothing for "
        f"this research action."
    )


def test_no_software_dev_regression() -> None:
    """Sentinel: the software-dev profile-default entries are unchanged.

    WP04 only adds ``("research", *)`` keys. If any software-dev value here
    drifted, that's a regression introduced outside the WP04 owned-files
    surface and must be investigated separately.
    """
    for action, expected in EXPECTED_SOFTWARE_DEV_PROFILES.items():
        actual = _ACTION_PROFILE_DEFAULTS.get(("software-dev", action))
        assert actual == expected, (
            f"Software-dev default drift for action {action!r}: "
            f"expected {expected!r}, got {actual!r}. WP04 must not modify "
            f"software-dev entries."
        )
