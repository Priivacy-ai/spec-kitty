"""Non-fakeable tests for the schema-diagram drift guard (WP08).

The four required forcing tests (contracts/diagram-drift-guard.md):
1. completeness over ALL ArtifactKind (synthetic member fails until dispositioned),
2. omit-a-field (a diagram missing a model field fails),
3. nested depth-2 (a field added to AgentProfileSchema -> AgentSpecialization fails),
4. AntiPattern (class) vs anti_pattern (DRG node-kind string) kept distinct.

Injection goes through the guard's patchable seams because the models are
``frozen=True, extra="forbid"`` and the enums cannot be extended at runtime.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.docs.diagram_drift import binding_table, guard
from tests.docs.diagram_drift.binding_table import DiagramBinding, ModelKind
from charter.offering.drg.models import DRGNode

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]

_DRGNODE_FIXTURE = """
```plantuml
@startyaml
title DRGNode missing a field
DRGNode:
  urn: "<kind>:<id>"
  kind: "<NodeKind>"
  label: "<str>"
  provenance: "<Provenance>"
@endyaml
```
"""


def test_authored_corpus_has_no_drift() -> None:
    """The REAL authored diagrams match their models exactly (the fidelity gate)."""
    findings = guard.collect_findings(_REPO_ROOT)
    assert findings == [], "unexpected drift:\n" + "\n".join(findings)


def test_every_artifact_kind_has_a_valid_disposition() -> None:
    for value in guard.artifact_kind_values():
        assert value in binding_table.ARTIFACT_KIND_DISPOSITIONS, value
        assert binding_table.ARTIFACT_KIND_DISPOSITIONS[value] in {
            "diagrammed",
            "consciously-omitted",
        }


def test_synthetic_artifact_kind_fails_until_dispositioned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = guard.artifact_kind_values()
    monkeypatch.setattr(guard, "artifact_kind_values", lambda: [*real, "synthetic_new_kind"])
    findings = guard.collect_findings(_REPO_ROOT)
    assert any("synthetic_new_kind" in f and "NO disposition" in f for f in findings), findings


def test_deleting_a_disposition_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    # Forces the completeness derivation to actually read list(ArtifactKind):
    # a stand-in key set would not notice the missing anti_pattern row.
    monkeypatch.delitem(binding_table.ARTIFACT_KIND_DISPOSITIONS, "anti_pattern")
    findings = guard.collect_findings(_REPO_ROOT)
    assert any("anti_pattern" in f and "NO disposition" in f for f in findings), findings


def test_omit_a_field_in_a_diagram_fails(tmp_path: Path) -> None:
    (tmp_path / "fixture.md").write_text(_DRGNODE_FIXTURE, encoding="utf-8")
    binding = DiagramBinding("fixture.md", "DRGNode", DRGNode, ModelKind.PYDANTIC)
    findings = guard.collect_findings(tmp_path, (binding,))
    assert any("DRGNode" in f and "missing-in-diagram=['tags']" in f for f in findings), findings


def test_nested_depth2_field_add_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    real_field_set = guard.model_field_set

    def fake_field_set(binding: DiagramBinding) -> set[str]:
        fields = real_field_set(binding)
        if binding.anchor == "AgentSpecialization":
            return fields | {"new-nested-field"}
        return fields

    monkeypatch.setattr(guard, "model_field_set", fake_field_set)
    findings = guard.collect_findings(_REPO_ROOT)
    assert any(
        "AgentSpecialization" in f and "new-nested-field" in f for f in findings
    ), findings


def test_antipattern_class_is_distinct_from_anti_pattern_node_kind() -> None:
    from pydantic import BaseModel

    from charter.offering.styleguides.models import AntiPattern

    # The styleguides AntiPattern is a real BaseModel example type...
    assert issubclass(AntiPattern, BaseModel)
    # ...but the ArtifactKind/NodeKind anti_pattern is a bare string with no backing
    # class, so it is dispositioned as consciously-omitted and NOT bound to a model.
    assert binding_table.ARTIFACT_KIND_DISPOSITIONS["anti_pattern"] == "consciously-omitted"
    assert all(b.model is not AntiPattern for b in binding_table.BINDINGS)
