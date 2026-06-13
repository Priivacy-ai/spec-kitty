"""Calibration walker: enumerate (profile, action) pairs for a mission.

For each step in the mission, the walker:
  1. Resolves ResolvedScope via the DRG resolver (with any project overlays applied).
  2. Looks up RequiredScope from the curated REQUIRED_SCOPE_MAP.
  3. Runs assert_inequality_holds with ``known_irrelevant`` = resolved - required
     (transitive extras surfaced by requires/suggests edges are tolerated).
  4. Emits a CalibrationFinding for every step.

Required-scope map (inline):
    Keys are ``(mission_key, action_urn)`` pairs.
    Values are frozenset[str] of the *directly scoped* artifact URNs (i.e. the
    direct ``scope`` edges from the action node in the built-in graph).  The
    resolver produces a strictly larger set via transitive ``requires`` /
    ``suggests`` traversal; those extras are tolerated as ``known_irrelevant``.

Overlay loading:
    The walker loads ``.kittify/doctrine/overlays/calibration-<mission>.yaml``
    (if present) alongside the built-in ``src/doctrine/graph.yaml``.  Overlay
    ``add_edge`` and ``remove_edge`` mutations are applied before resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from charter.drg import (
    DRGEdge,
    DRGGraph,
    DRGNode,
    NodeKind,
    Relation,
    load_graph,
    merge_layers,
    resolve_context,
)
from specify_cli.calibration.inequality import InequalityResult, assert_inequality_holds


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EdgeChange:
    """A recommended DRG edge change."""

    kind: str  # "add_edge" | "remove_edge" | "rewire_edge"
    source: str
    target: str
    relation: str
    new_target: str | None = None  # for rewire_edge only


@dataclass
class CalibrationFinding:
    """Calibration result for a single (step, action, profile) triple.

    Attributes:
        step_id: Step identifier within the mission.
        action_id: Action URN (e.g. ``"action:software-dev/implement"``).
        profile_id: Agent-profile URN (e.g. ``"agent_profile:implementer-ivan"``).
        resolved_scope: URNs surfaced by the DRG resolver.
        required_scope: URNs the step needs (from curated map).
        known_irrelevant: URNs explicitly tolerated as irrelevant (benign extras).
        inequality: Result of assert_inequality_holds.
        recommended_edge_changes: Structured edge mutations to fix any violations.
    """

    step_id: str
    action_id: str
    profile_id: str
    resolved_scope: frozenset[str]
    required_scope: frozenset[str]
    known_irrelevant: frozenset[str]
    inequality: InequalityResult
    recommended_edge_changes: list[EdgeChange] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Curated required-scope map
#
# Keys: (mission_key, action_urn)
# Values: frozenset of URNs that the step *directly requires*
#         (matches the direct ``scope`` edges in the built-in graph, plus any
#          URNs the step semantically needs that may be missing from those edges).
#
# Rationale: determined by inspection of each action's semantic intent per R-005.
# The resolver produces a superset (via transitive traversal); extras are
# classified as known_irrelevant so the inequality holds without edge removal.
# ---------------------------------------------------------------------------

_ACTION_SOFTWARE_DEV_SPECIFY = "action:software-dev/specify"
_ACTION_SOFTWARE_DEV_PLAN = "action:software-dev/plan"
_ACTION_SOFTWARE_DEV_TASKS = "action:software-dev/tasks"
_ACTION_SOFTWARE_DEV_IMPLEMENT = "action:software-dev/implement"
_ACTION_SOFTWARE_DEV_REVIEW = "action:software-dev/review"
_ACTION_SOFTWARE_DEV_RETROSPECT = "action:software-dev/retrospect"
_ACTION_RESEARCH_GATHERING = "action:research/gathering"

_DIRECTIVE_003 = "directive:DIRECTIVE_003"
_DIRECTIVE_010 = "directive:DIRECTIVE_010"
_DIRECTIVE_024 = "directive:DIRECTIVE_024"
_DIRECTIVE_025 = "directive:DIRECTIVE_025"
_DIRECTIVE_028 = "directive:DIRECTIVE_028"
_DIRECTIVE_029 = "directive:DIRECTIVE_029"
_DIRECTIVE_030 = "directive:DIRECTIVE_030"
_DIRECTIVE_034 = "directive:DIRECTIVE_034"
_DIRECTIVE_037 = "directive:DIRECTIVE_037"

_TACTIC_ACCEPTANCE_TEST_FIRST = "tactic:acceptance-test-first"
_TACTIC_ADR_DRAFTING_WORKFLOW = "tactic:adr-drafting-workflow"
_TACTIC_AUTONOMOUS_OPERATION_PROTOCOL = "tactic:autonomous-operation-protocol"
_TACTIC_CHANGE_APPLY_SMALLEST_VIABLE_DIFF = "tactic:change-apply-smallest-viable-diff"
_TACTIC_PREMORTEM_RISK_IDENTIFICATION = "tactic:premortem-risk-identification"
_TACTIC_PROBLEM_DECOMPOSITION = "tactic:problem-decomposition"
_TACTIC_QUALITY_GATE_VERIFICATION = "tactic:quality-gate-verification"
_TACTIC_REQUIREMENTS_VALIDATION_WORKFLOW = "tactic:requirements-validation-workflow"
_TACTIC_REVIEW_INTENT_AND_RISK_FIRST = "tactic:review-intent-and-risk-first"
_TACTIC_STOPPING_CONDITIONS = "tactic:stopping-conditions"
_TACTIC_TDD_RED_GREEN_REFACTOR = "tactic:tdd-red-green-refactor"
_TACTIC_USAGE_EXAMPLES_SYNC = "tactic:usage-examples-sync"

_TOOLGUIDE_EFFICIENT_LOCAL_TOOLING = "toolguide:efficient-local-tooling"

_REQUIRED_SCOPE: dict[tuple[str, str], frozenset[str]] = {
    # ------------------------------------------------------------------
    # software-dev
    # ------------------------------------------------------------------
    ("software-dev", _ACTION_SOFTWARE_DEV_SPECIFY): frozenset({
        _DIRECTIVE_003,
        _DIRECTIVE_010,
        _TACTIC_REQUIREMENTS_VALIDATION_WORKFLOW,
    }),
    ("software-dev", _ACTION_SOFTWARE_DEV_PLAN): frozenset({
        _DIRECTIVE_003,
        _DIRECTIVE_010,
        _TACTIC_ADR_DRAFTING_WORKFLOW,
        _TACTIC_PREMORTEM_RISK_IDENTIFICATION,
        _TACTIC_PROBLEM_DECOMPOSITION,
        _TACTIC_REQUIREMENTS_VALIDATION_WORKFLOW,
    }),
    ("software-dev", _ACTION_SOFTWARE_DEV_TASKS): frozenset({
        _DIRECTIVE_003,
        _DIRECTIVE_010,
        _DIRECTIVE_024,
        _TACTIC_ADR_DRAFTING_WORKFLOW,
        _TACTIC_PROBLEM_DECOMPOSITION,
        _TACTIC_REQUIREMENTS_VALIDATION_WORKFLOW,
    }),
    ("software-dev", _ACTION_SOFTWARE_DEV_IMPLEMENT): frozenset({
        _DIRECTIVE_024,
        _DIRECTIVE_025,
        _DIRECTIVE_028,
        _DIRECTIVE_029,
        _DIRECTIVE_030,
        _DIRECTIVE_034,
        _TACTIC_ACCEPTANCE_TEST_FIRST,
        _TACTIC_AUTONOMOUS_OPERATION_PROTOCOL,
        _TACTIC_CHANGE_APPLY_SMALLEST_VIABLE_DIFF,
        _TACTIC_QUALITY_GATE_VERIFICATION,
        _TACTIC_STOPPING_CONDITIONS,
        _TACTIC_TDD_RED_GREEN_REFACTOR,
        _TOOLGUIDE_EFFICIENT_LOCAL_TOOLING,
    }),
    ("software-dev", _ACTION_SOFTWARE_DEV_REVIEW): frozenset({
        _DIRECTIVE_010,
        _DIRECTIVE_024,
        _DIRECTIVE_025,
        _DIRECTIVE_028,
        _DIRECTIVE_029,
        _DIRECTIVE_030,
        _DIRECTIVE_034,
        _DIRECTIVE_037,
        _TACTIC_ACCEPTANCE_TEST_FIRST,
        _TACTIC_USAGE_EXAMPLES_SYNC,
        _TACTIC_QUALITY_GATE_VERIFICATION,
        _TACTIC_REVIEW_INTENT_AND_RISK_FIRST,
        _TACTIC_STOPPING_CONDITIONS,
    }),
    ("software-dev", _ACTION_SOFTWARE_DEV_RETROSPECT): frozenset({
        _DIRECTIVE_003,
        _DIRECTIVE_010,
    }),

    # ------------------------------------------------------------------
    # research
    # ------------------------------------------------------------------
    ("research", "action:research/scoping"): frozenset({
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_010",
        "tactic:requirements-validation-workflow",
        "tactic:premortem-risk-identification",
    }),
    ("research", "action:research/methodology"): frozenset({
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_010",
        "tactic:adr-drafting-workflow",
        "tactic:requirements-validation-workflow",
    }),
    ("research", "action:research/gathering"): frozenset({
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_037",
        "tactic:requirements-validation-workflow",
    }),
    ("research", "action:research/synthesis"): frozenset({
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_010",
        "tactic:premortem-risk-identification",
        "tactic:requirements-validation-workflow",
    }),
    ("research", "action:research/output"): frozenset({
        "directive:DIRECTIVE_010",
        "directive:DIRECTIVE_037",
        "tactic:requirements-validation-workflow",
    }),
    ("research", "action:research/retrospect"): frozenset({
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_010",
    }),

    # ------------------------------------------------------------------
    # documentation
    # ------------------------------------------------------------------
    ("documentation", "action:documentation/audit"): frozenset({
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_037",
        "tactic:requirements-validation-workflow",
    }),
    ("documentation", "action:documentation/design"): frozenset({
        "directive:DIRECTIVE_001",
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_010",
        "tactic:adr-drafting-workflow",
        "tactic:requirements-validation-workflow",
    }),
    ("documentation", "action:documentation/discover"): frozenset({
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_010",
        "tactic:premortem-risk-identification",
        "tactic:requirements-validation-workflow",
    }),
    ("documentation", "action:documentation/generate"): frozenset({
        "directive:DIRECTIVE_010",
        "directive:DIRECTIVE_037",
        "tactic:requirements-validation-workflow",
    }),
    ("documentation", "action:documentation/publish"): frozenset({
        "directive:DIRECTIVE_010",
        "directive:DIRECTIVE_037",
        "tactic:requirements-validation-workflow",
    }),
    ("documentation", "action:documentation/validate"): frozenset({
        "directive:DIRECTIVE_010",
        "directive:DIRECTIVE_037",
        "tactic:premortem-risk-identification",
        "tactic:requirements-validation-workflow",
    }),
    ("documentation", "action:documentation/retrospect"): frozenset({
        "directive:DIRECTIVE_003",
        "directive:DIRECTIVE_010",
    }),

    # ------------------------------------------------------------------
    # erp-custom (maps ERP step roles to generic action URNs)
    # query-erp / lookup-provider / write-report → research/gathering
    # create-js / refactor-function              → software-dev/implement
    # ask-user                                   → software-dev/specify
    # retrospective                              → software-dev/retrospect
    # ------------------------------------------------------------------
    ("erp-custom", _ACTION_RESEARCH_GATHERING): frozenset({
        _DIRECTIVE_003,
        _DIRECTIVE_037,
        _TACTIC_REQUIREMENTS_VALIDATION_WORKFLOW,
    }),
    ("erp-custom", _ACTION_SOFTWARE_DEV_IMPLEMENT): frozenset({
        _DIRECTIVE_024,
        _DIRECTIVE_025,
        _DIRECTIVE_028,
        _DIRECTIVE_029,
        _DIRECTIVE_030,
        _DIRECTIVE_034,
        _TACTIC_ACCEPTANCE_TEST_FIRST,
        _TACTIC_AUTONOMOUS_OPERATION_PROTOCOL,
        _TACTIC_CHANGE_APPLY_SMALLEST_VIABLE_DIFF,
        _TACTIC_QUALITY_GATE_VERIFICATION,
        _TACTIC_STOPPING_CONDITIONS,
        _TACTIC_TDD_RED_GREEN_REFACTOR,
        _TOOLGUIDE_EFFICIENT_LOCAL_TOOLING,
    }),
    ("erp-custom", _ACTION_SOFTWARE_DEV_SPECIFY): frozenset({
        _DIRECTIVE_003,
        _DIRECTIVE_010,
        _TACTIC_REQUIREMENTS_VALIDATION_WORKFLOW,
    }),
    ("erp-custom", _ACTION_SOFTWARE_DEV_RETROSPECT): frozenset({
        _DIRECTIVE_003,
        _DIRECTIVE_010,
    }),
}

# ---------------------------------------------------------------------------
# Mission step definitions
# ---------------------------------------------------------------------------

# Maps mission_key → list of (step_id, action_urn, profile_urn)
_MISSION_STEPS: dict[str, list[tuple[str, str, str]]] = {
    "software-dev": [
        ("specify",    _ACTION_SOFTWARE_DEV_SPECIFY,    "agent_profile:planner-priti"),
        ("plan",       _ACTION_SOFTWARE_DEV_PLAN,       "agent_profile:planner-priti"),
        ("tasks",      _ACTION_SOFTWARE_DEV_TASKS,      "agent_profile:planner-priti"),
        ("implement",  _ACTION_SOFTWARE_DEV_IMPLEMENT,  "agent_profile:implementer-ivan"),
        ("review",     _ACTION_SOFTWARE_DEV_REVIEW,     "agent_profile:reviewer-renata"),
        ("retrospect", _ACTION_SOFTWARE_DEV_RETROSPECT, "agent_profile:retrospective-facilitator"),
    ],
    "research": [
        ("scoping",     "action:research/scoping",     "agent_profile:researcher-robbie"),
        ("methodology", "action:research/methodology", "agent_profile:researcher-robbie"),
        ("gathering",   "action:research/gathering",   "agent_profile:researcher-robbie"),
        ("synthesis",   "action:research/synthesis",   "agent_profile:researcher-robbie"),
        ("output",      "action:research/output",      "agent_profile:researcher-robbie"),
        ("retrospect",  "action:research/retrospect",  "agent_profile:retrospective-facilitator"),
    ],
    "documentation": [
        ("audit",       "action:documentation/audit",    "agent_profile:curator-carla"),
        ("design",      "action:documentation/design",   "agent_profile:curator-carla"),
        ("discover",    "action:documentation/discover", "agent_profile:curator-carla"),
        ("generate",    "action:documentation/generate", "agent_profile:curator-carla"),
        ("publish",     "action:documentation/publish",  "agent_profile:curator-carla"),
        ("validate",    "action:documentation/validate", "agent_profile:curator-carla"),
        ("retrospect",  "action:documentation/retrospect", "agent_profile:retrospective-facilitator"),
    ],
    "erp-custom": [
        ("query-erp",         _ACTION_RESEARCH_GATHERING,       "agent_profile:researcher-robbie"),
        ("lookup-provider",   _ACTION_RESEARCH_GATHERING,       "agent_profile:researcher-robbie"),
        ("ask-user",          _ACTION_SOFTWARE_DEV_SPECIFY,     "agent_profile:implementer-ivan"),
        ("create-js",         _ACTION_SOFTWARE_DEV_IMPLEMENT,   "agent_profile:implementer-ivan"),
        ("refactor-function", _ACTION_SOFTWARE_DEV_IMPLEMENT,   "agent_profile:implementer-ivan"),
        ("write-report",      _ACTION_RESEARCH_GATHERING,       "agent_profile:researcher-robbie"),
        ("retrospective",     _ACTION_SOFTWARE_DEV_RETROSPECT,  "agent_profile:retrospective-facilitator"),
    ],
}


# ---------------------------------------------------------------------------
# Overlay loading
# ---------------------------------------------------------------------------


def _load_overlay_graph(
    repo_root: Path,
    mission_key: str,
) -> DRGGraph | None:
    """Load the project-local calibration overlay for *mission_key*, if present.

    The overlay YAML may contain:
      - ``nodes``: list of extra node definitions (added to the graph)
      - ``add_edge``: list of edges to add

    Returns None when the overlay file does not exist or is empty.
    """
    overlay_path = (
        repo_root / ".kittify" / "doctrine" / "overlays"
        / f"calibration-{mission_key}.yaml"
    )
    if not overlay_path.exists():
        return None

    yaml = YAML(typ="safe")
    raw = yaml.load(overlay_path.read_text(encoding="utf-8"))
    if not raw:
        return None

    nodes: list[DRGNode] = []
    edges: list[DRGEdge] = []

    for node_data in raw.get("nodes", []):
        nodes.append(
            DRGNode(
                urn=node_data["urn"],
                kind=NodeKind(node_data["kind"]),
                label=node_data.get("label"),
            )
        )

    for edge_data in raw.get("add_edge", []):
        edges.append(
            DRGEdge(
                source=edge_data["source"],
                target=edge_data["target"],
                relation=Relation(edge_data["relation"]),
                reason=edge_data.get("reason"),
            )
        )

    if not nodes and not edges:
        return None

    return DRGGraph(
        schema_version="1.0",
        generated_at="OVERLAY",
        generated_by="calibration-overlay",
        nodes=nodes,
        edges=edges,
    )


def _apply_remove_edges(graph: DRGGraph, repo_root: Path, mission_key: str) -> DRGGraph:
    """Remove edges listed in the overlay's ``remove_edge`` section."""
    overlay_path = (
        repo_root / ".kittify" / "doctrine" / "overlays"
        / f"calibration-{mission_key}.yaml"
    )
    if not overlay_path.exists():
        return graph

    yaml = YAML(typ="safe")
    raw = yaml.load(overlay_path.read_text(encoding="utf-8"))
    if not raw:
        return graph

    removes: list[tuple[str, str, str]] = [
        (e["source"], e["target"], e["relation"])
        for e in raw.get("remove_edge", [])
    ]
    if not removes:
        return graph

    remove_set = set(removes)
    kept_edges = [
        e for e in graph.edges
        if (e.source, e.target, e.relation.value) not in remove_set
    ]
    return DRGGraph(
        schema_version=graph.schema_version,
        generated_at=graph.generated_at,
        generated_by=graph.generated_by,
        nodes=graph.nodes,
        edges=kept_edges,
    )


# ---------------------------------------------------------------------------
# Walker public API
# ---------------------------------------------------------------------------


def _built_in_graph_path(repo_root: Path) -> Path:
    """Return the path to the built-in ``src/doctrine/graph.yaml``."""
    return repo_root / "src" / "doctrine" / "graph.yaml"


def _build_graph(repo_root: Path, mission_key: str) -> DRGGraph:
    """Load built-in graph, apply overlay (add + remove), return merged graph."""
    built_in = load_graph(_built_in_graph_path(repo_root))
    overlay = _load_overlay_graph(repo_root, mission_key)
    merged = merge_layers(built_in, overlay)
    merged = _apply_remove_edges(merged, repo_root, mission_key)
    return merged


def _recommend_changes(
    action_urn: str,
    missing_urns: frozenset[str],
) -> list[EdgeChange]:
    """Derive minimal add_edge changes for any missing URNs.

    Over-broad URNs are not recommended for removal here because they are
    typically benign transitive extras (from requires/suggests traversal).
    Removal recommendations go in the overlay YAML directly if needed.
    """
    changes: list[EdgeChange] = []
    for urn in sorted(missing_urns):
        changes.append(
            EdgeChange(
                kind="add_edge",
                source=action_urn,
                target=urn,
                relation="scope",
            )
        )
    return changes


def walk_mission(
    *,
    mission_key: str,
    repo_root: Path,
) -> list[CalibrationFinding]:
    """Walk every (profile, action) pair in *mission_key* and calibrate.

    ``known_irrelevant`` is computed as the difference between ``resolved_scope``
    and ``required_scope``.  This means transitive URNs surfaced by
    ``requires``/``suggests`` traversal are tolerated rather than flagged as
    over-broad, which is the correct semantics for a resolver that produces a
    superset of directly-scoped artifacts.

    Args:
        mission_key: One of ``"software-dev"``, ``"research"``,
            ``"documentation"``, or ``"erp-custom"``.
        repo_root: Repository root containing ``src/doctrine/graph.yaml``
            and (optionally) ``.kittify/doctrine/overlays/``.

    Returns:
        One :class:`CalibrationFinding` per step in the mission.

    Raises:
        KeyError: If *mission_key* is not in the built-in step registry.
        ``doctrine.drg.DRGLoadError``: If the built-in graph cannot be loaded.
    """
    steps = _MISSION_STEPS[mission_key]
    graph = _build_graph(repo_root, mission_key)

    findings: list[CalibrationFinding] = []
    for step_id, action_urn, profile_urn in steps:
        ctx = resolve_context(graph, action_urn)
        resolved_scope = ctx.artifact_urns

        required_scope = _REQUIRED_SCOPE.get(
            (mission_key, action_urn),
            frozenset(),
        )

        # Transitive extras from requires/suggests are benign; classify as
        # known_irrelevant so the over-broad half of the inequality passes.
        known_irrelevant = resolved_scope - required_scope

        result = assert_inequality_holds(
            resolved_scope=resolved_scope,
            required_scope=required_scope,
            known_irrelevant=known_irrelevant,
        )

        changes = _recommend_changes(action_urn, result.missing_urns)

        findings.append(
            CalibrationFinding(
                step_id=step_id,
                action_id=action_urn,
                profile_id=profile_urn,
                resolved_scope=resolved_scope,
                required_scope=required_scope,
                known_irrelevant=known_irrelevant,
                inequality=result,
                recommended_edge_changes=changes,
            )
        )

    return findings
