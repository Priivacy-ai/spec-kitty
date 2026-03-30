"""Tests for the transitive reference resolver."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from doctrine.shared.exceptions import DoctrineResolutionCycleError
from constitution.reference_resolver import (
    ResolvedReferenceGraph,
    resolve_references_transitively,
)

pytestmark = pytest.mark.fast


def _make_service(**repos):
    """Build a mock DoctrineService with provided repositories."""
    svc = MagicMock()
    for name, repo in repos.items():
        setattr(svc, name, repo)
    return svc


def _make_directive(tactic_refs: list[str]):
    d = MagicMock()
    d.tactic_refs = tactic_refs
    return d


def _make_tactic(references=None, steps=None):
    t = MagicMock()
    t.references = references or []
    t.steps = steps or []
    return t


def _make_ref(ref_type: str, ref_id: str):
    r = MagicMock()
    r.type = ref_type
    r.id = ref_id
    return r


def _make_repo(items: dict):
    """Mock repository where .get(id) returns items[id] or None."""
    repo = MagicMock()
    repo.get = lambda id_: items.get(id_)
    return repo


# ---------------------------------------------------------------------------
# Test 1: Empty input returns empty graph
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty_graph():
    svc = _make_service(
        directives=_make_repo({}),
        tactics=_make_repo({}),
        styleguides=_make_repo({}),
        toolguides=_make_repo({}),
        procedures=_make_repo({}),
    )
    graph = resolve_references_transitively([], svc)
    assert graph.directives == []
    assert graph.tactics == []
    assert graph.styleguides == []
    assert graph.toolguides == []
    assert graph.procedures == []
    assert graph.unresolved == []
    assert graph.is_complete is True


# ---------------------------------------------------------------------------
# Test 2: Simple chain: directive → tactic → styleguide
# ---------------------------------------------------------------------------


def test_simple_chain_directive_tactic_styleguide():
    sg1 = MagicMock()
    t1 = _make_tactic(references=[_make_ref("styleguide", "sg1")])
    d1 = _make_directive(tactic_refs=["t1"])

    svc = _make_service(
        directives=_make_repo({"d1": d1}),
        tactics=_make_repo({"t1": t1}),
        styleguides=_make_repo({"sg1": sg1}),
        toolguides=_make_repo({}),
        procedures=_make_repo({}),
    )

    graph = resolve_references_transitively(["d1"], svc)

    assert "d1" in graph.directives
    assert "t1" in graph.tactics
    assert "sg1" in graph.styleguides
    assert graph.unresolved == []
    assert graph.is_complete is True


# ---------------------------------------------------------------------------
# Test 3: Missing reference recorded in unresolved, traversal continues
# ---------------------------------------------------------------------------


def test_missing_tactic_recorded_in_unresolved():
    d1 = _make_directive(tactic_refs=["missing_tactic", "t2"])
    t2 = _make_tactic()

    svc = _make_service(
        directives=_make_repo({"d1": d1}),
        tactics=_make_repo({"t2": t2}),
        styleguides=_make_repo({}),
        toolguides=_make_repo({}),
        procedures=_make_repo({}),
    )

    graph = resolve_references_transitively(["d1"], svc)

    assert "d1" in graph.directives
    assert "t2" in graph.tactics
    assert ("tactics", "missing_tactic") in graph.unresolved
    assert graph.is_complete is False


# ---------------------------------------------------------------------------
# Test 4: Cycle between tactics — raises DoctrineResolutionCycleError
# ---------------------------------------------------------------------------


def test_cycle_between_tactics_raises():
    # T1 references T2, T2 references T1 — this is a configuration error.
    t1 = _make_tactic(references=[_make_ref("tactic", "t2")])
    t2 = _make_tactic(references=[_make_ref("tactic", "t1")])
    d1 = _make_directive(tactic_refs=["t1"])

    svc = _make_service(
        directives=_make_repo({"d1": d1}),
        tactics=_make_repo({"t1": t1, "t2": t2}),
        styleguides=_make_repo({}),
        toolguides=_make_repo({}),
        procedures=_make_repo({}),
    )

    with pytest.raises(DoctrineResolutionCycleError) as exc_info:
        resolve_references_transitively(["d1"], svc)

    cycle_ids = {node_id for _, node_id in exc_info.value.cycle}
    assert "t1" in cycle_ids or "t2" in cycle_ids


# ---------------------------------------------------------------------------
# Test 5: Multiple directives sharing a tactic — tactic appears once
# ---------------------------------------------------------------------------


def test_multiple_directives_sharing_tactic():
    t1 = _make_tactic()
    d1 = _make_directive(tactic_refs=["t1"])
    d2 = _make_directive(tactic_refs=["t1"])

    svc = _make_service(
        directives=_make_repo({"d1": d1, "d2": d2}),
        tactics=_make_repo({"t1": t1}),
        styleguides=_make_repo({}),
        toolguides=_make_repo({}),
        procedures=_make_repo({}),
    )

    graph = resolve_references_transitively(["d1", "d2"], svc)

    assert graph.tactics.count("t1") == 1
    assert "d1" in graph.directives
    assert "d2" in graph.directives


# ---------------------------------------------------------------------------
# Test 6: Step-level references followed — toolguide via step
# ---------------------------------------------------------------------------


def test_step_level_references_followed():
    step = MagicMock()
    step.references = [_make_ref("toolguide", "tg1")]
    tg1 = MagicMock()

    t1 = _make_tactic(references=[], steps=[step])
    d1 = _make_directive(tactic_refs=["t1"])

    svc = _make_service(
        directives=_make_repo({"d1": d1}),
        tactics=_make_repo({"t1": t1}),
        styleguides=_make_repo({}),
        toolguides=_make_repo({"tg1": tg1}),
        procedures=_make_repo({}),
    )

    graph = resolve_references_transitively(["d1"], svc)

    assert "tg1" in graph.toolguides
    assert graph.unresolved == []
    assert graph.is_complete is True


# ---------------------------------------------------------------------------
# Test 7: is_complete property
# ---------------------------------------------------------------------------


def test_is_complete_true_when_no_unresolved():
    graph = ResolvedReferenceGraph()
    assert graph.is_complete is True


def test_is_complete_false_when_unresolved_present():
    graph = ResolvedReferenceGraph(unresolved=[("tactics", "missing")])
    assert graph.is_complete is False


# ---------------------------------------------------------------------------
# Test 8: Unknown reference type is ignored gracefully
# ---------------------------------------------------------------------------


def test_unknown_reference_type_ignored():
    unknown_ref = _make_ref("unknown_type", "some_id")
    t1 = _make_tactic(references=[unknown_ref])
    d1 = _make_directive(tactic_refs=["t1"])

    svc = _make_service(
        directives=_make_repo({"d1": d1}),
        tactics=_make_repo({"t1": t1}),
        styleguides=_make_repo({}),
        toolguides=_make_repo({}),
        procedures=_make_repo({}),
    )

    graph = resolve_references_transitively(["d1"], svc)

    assert "d1" in graph.directives
    assert "t1" in graph.tactics
    assert graph.unresolved == []
    assert graph.is_complete is True


# ---------------------------------------------------------------------------
# Test: Procedure references followed
# ---------------------------------------------------------------------------


def test_procedure_reference_followed():
    proc1 = MagicMock()
    t1 = _make_tactic(references=[_make_ref("procedure", "proc1")])
    d1 = _make_directive(tactic_refs=["t1"])

    svc = _make_service(
        directives=_make_repo({"d1": d1}),
        tactics=_make_repo({"t1": t1}),
        styleguides=_make_repo({}),
        toolguides=_make_repo({}),
        procedures=_make_repo({"proc1": proc1}),
    )

    graph = resolve_references_transitively(["d1"], svc)

    assert "proc1" in graph.procedures
    assert graph.is_complete is True


# ---------------------------------------------------------------------------
# Test: Missing directive itself recorded in unresolved
# ---------------------------------------------------------------------------


def test_missing_directive_recorded_in_unresolved():
    svc = _make_service(
        directives=_make_repo({}),
        tactics=_make_repo({}),
        styleguides=_make_repo({}),
        toolguides=_make_repo({}),
        procedures=_make_repo({}),
    )

    graph = resolve_references_transitively(["nonexistent"], svc)

    assert ("directives", "nonexistent") in graph.unresolved
    assert graph.is_complete is False
