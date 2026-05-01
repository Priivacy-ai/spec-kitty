"""Regression tests for curated Matt Pocock skill doctrine imports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
import pytest

from doctrine.drg.loader import load_graph, merge_layers
from doctrine.drg.models import NodeKind, Relation
from doctrine.drg.query import resolve_transitive_refs
from doctrine.drg.validator import assert_valid
from doctrine.missions import MissionTemplateRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTRINE_ROOT = REPO_ROOT / "src" / "doctrine"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_curated_doctrine_artifacts_exist_with_expected_kinds() -> None:
    expected_paths = [
        "procedures/shipped/disciplined-defect-diagnosis.procedure.yaml",
        "paradigms/shipped/deep-module-design.paradigm.yaml",
        "tactics/shipped/architecture/deepening-opportunity-assessment.tactic.yaml",
        "tactics/shipped/architecture/interface-variation-design.tactic.yaml",
        "procedures/shipped/domain-aware-decision-interview.procedure.yaml",
        "procedures/shipped/issue-triage-state-machine.procedure.yaml",
        "styleguides/shipped/deployable-skill-authoring.styleguide.yaml",
        "templates/triage/agent-brief-template.md",
        "templates/triage/out-of-scope-record-template.md",
    ]

    missing = [relative for relative in expected_paths if not (DOCTRINE_ROOT / relative).exists()]
    assert missing == []

    assert _load_yaml(DOCTRINE_ROOT / expected_paths[0])["id"] == "disciplined-defect-diagnosis"
    assert _load_yaml(DOCTRINE_ROOT / expected_paths[1])["id"] == "deep-module-design"
    assert _load_yaml(DOCTRINE_ROOT / expected_paths[6])["id"] == "deployable-skill-authoring"


def test_shipped_graph_links_curated_artifacts_and_templates() -> None:
    graph = merge_layers(load_graph(DOCTRINE_ROOT / "graph.yaml"), None)
    assert_valid(graph)

    expected_nodes = {
        "procedure:disciplined-defect-diagnosis": NodeKind.PROCEDURE,
        "paradigm:deep-module-design": NodeKind.PARADIGM,
        "tactic:deepening-opportunity-assessment": NodeKind.TACTIC,
        "tactic:interface-variation-design": NodeKind.TACTIC,
        "procedure:domain-aware-decision-interview": NodeKind.PROCEDURE,
        "procedure:issue-triage-state-machine": NodeKind.PROCEDURE,
        "styleguide:deployable-skill-authoring": NodeKind.STYLEGUIDE,
        "template:agent-brief-template": NodeKind.TEMPLATE,
        "template:out-of-scope-record-template": NodeKind.TEMPLATE,
    }

    for urn, kind in expected_nodes.items():
        node = graph.get_node(urn)
        assert node is not None, urn
        assert node.kind is kind

    result = resolve_transitive_refs(
        graph,
        start_urns={"procedure:issue-triage-state-machine"},
        relations={Relation.REQUIRES, Relation.SUGGESTS},
        max_depth=1,
    )
    assert result.templates == ["agent-brief-template", "out-of-scope-record-template"]
    assert "disciplined-defect-diagnosis" in result.procedures


def test_software_dev_action_indexes_expose_design_and_triage_doctrine() -> None:
    repo = MissionTemplateRepository.default()

    plan_index = repo.get_action_index("software-dev", "plan")
    assert plan_index is not None
    assert "deepening-opportunity-assessment" in plan_index.parsed["tactics"]
    assert "interface-variation-design" in plan_index.parsed["tactics"]
    assert "domain-aware-decision-interview" in plan_index.parsed["procedures"]

    tasks_index = repo.get_action_index("software-dev", "tasks")
    assert tasks_index is not None
    assert "issue-triage-state-machine" in tasks_index.parsed["procedures"]


def test_diagnosis_procedure_preserves_hypothesis_and_feedback_loop_discipline() -> None:
    procedure = _load_yaml(
        DOCTRINE_ROOT / "procedures" / "shipped" / "disciplined-defect-diagnosis.procedure.yaml"
    )

    step_text = "\n".join(step["title"] + " " + step.get("description", "") for step in procedure["steps"])
    assert "feedback loop" in step_text
    assert "hypotheses" in step_text
    assert "tag" in step_text
    assert "regression test" in step_text
    assert any(pattern["name"] == "Fixing without a feedback loop" for pattern in procedure["anti_patterns"])
