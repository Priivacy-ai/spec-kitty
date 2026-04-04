"""Acceptance tests for cycle detection in doctrine artifact resolution.

These tests prove that cyclic cross-artifact references are caught and surfaced
as errors by the doctrine resolution entrypoint. A cycle in the reference graph
(e.g. Tactic A → Tactic B → Tactic A) would cause infinite resolution loops if
silently ignored, and is always a configuration error.

Test strategy
-------------
We construct minimal stub repositories whose artifacts deliberately form cycles,
then call ``resolve_references_transitively`` (the public resolution entrypoint)
and assert that it raises ``DoctrineResolutionCycleError``.

All tests are marked ``@pytest.mark.fast`` — no filesystem or subprocess I/O.
"""

from __future__ import annotations

import pytest

from doctrine.shared.exceptions import DoctrineResolutionCycleError
from charter.reference_resolver import resolve_references_transitively


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------


class _StubRef:
    """Minimal tactic reference stub."""

    def __init__(self, ref_type: str, ref_id: str) -> None:
        self.type = ref_type
        self.id = ref_id


class _StubTactic:
    """Minimal tactic stub with step-level and root-level references."""

    def __init__(
        self,
        tactic_id: str,
        root_refs: list[tuple[str, str]] | None = None,
        step_refs: list[tuple[str, str]] | None = None,
    ) -> None:
        self.id = tactic_id
        self.tactic_refs: list[str] = []
        self.references = [_StubRef(t, i) for t, i in (root_refs or [])]
        step = _StubStep(step_refs or [])
        self.steps = [step] if step_refs else []


class _StubStep:
    def __init__(self, refs: list[tuple[str, str]]) -> None:
        self.references = [_StubRef(t, i) for t, i in refs]


class _StubDirective:
    """Minimal directive stub."""

    def __init__(self, directive_id: str, tactic_refs: list[str]) -> None:
        self.id = directive_id
        self.tactic_refs = tactic_refs
        self.references: list[_StubRef] = []


class _StubRepository:
    """In-memory repository backed by a plain dict."""

    def __init__(self, items: dict[str, object]) -> None:
        self._items = items

    def get(self, artifact_id: str) -> object | None:
        return self._items.get(artifact_id)


class _StubDoctrineService:
    """Minimal DoctrineService stub wiring stub repositories."""

    def __init__(
        self,
        directives: dict[str, _StubDirective] | None = None,
        tactics: dict[str, _StubTactic] | None = None,
    ) -> None:
        self.directives = _StubRepository(directives or {})
        self.tactics = _StubRepository(tactics or {})
        self.styleguides = _StubRepository({})
        self.toolguides = _StubRepository({})
        self.procedures = _StubRepository({})


# ---------------------------------------------------------------------------
# Acceptance tests — all should FAIL before the fix, PASS after
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_direct_tactic_cycle_raises() -> None:
    """A direct tactic-to-tactic cycle (A → B → A) must raise DoctrineResolutionCycleError."""
    tactic_a = _StubTactic("TACTIC_A", root_refs=[("tactic", "TACTIC_B")])
    tactic_b = _StubTactic("TACTIC_B", root_refs=[("tactic", "TACTIC_A")])

    directive = _StubDirective("DIRECTIVE_001", tactic_refs=["TACTIC_A"])
    svc = _StubDoctrineService(
        directives={"DIRECTIVE_001": directive},
        tactics={"TACTIC_A": tactic_a, "TACTIC_B": tactic_b},
    )

    with pytest.raises(DoctrineResolutionCycleError) as exc_info:
        resolve_references_transitively(["DIRECTIVE_001"], svc)

    cycle_ids = {node_id for _, node_id in exc_info.value.cycle}
    assert "TACTIC_A" in cycle_ids
    assert "TACTIC_B" in cycle_ids


@pytest.mark.fast
def test_self_referencing_tactic_raises() -> None:
    """A tactic that references itself (A → A) must raise DoctrineResolutionCycleError."""
    tactic_a = _StubTactic("TACTIC_A", root_refs=[("tactic", "TACTIC_A")])
    directive = _StubDirective("DIRECTIVE_001", tactic_refs=["TACTIC_A"])
    svc = _StubDoctrineService(
        directives={"DIRECTIVE_001": directive},
        tactics={"TACTIC_A": tactic_a},
    )

    with pytest.raises(DoctrineResolutionCycleError) as exc_info:
        resolve_references_transitively(["DIRECTIVE_001"], svc)

    cycle_ids = {node_id for _, node_id in exc_info.value.cycle}
    assert "TACTIC_A" in cycle_ids


@pytest.mark.fast
def test_three_node_tactic_cycle_raises() -> None:
    """A three-node tactic cycle (A → B → C → A) must raise DoctrineResolutionCycleError."""
    tactic_a = _StubTactic("TACTIC_A", root_refs=[("tactic", "TACTIC_B")])
    tactic_b = _StubTactic("TACTIC_B", root_refs=[("tactic", "TACTIC_C")])
    tactic_c = _StubTactic("TACTIC_C", root_refs=[("tactic", "TACTIC_A")])

    directive = _StubDirective("DIRECTIVE_001", tactic_refs=["TACTIC_A"])
    svc = _StubDoctrineService(
        directives={"DIRECTIVE_001": directive},
        tactics={"TACTIC_A": tactic_a, "TACTIC_B": tactic_b, "TACTIC_C": tactic_c},
    )

    with pytest.raises(DoctrineResolutionCycleError):
        resolve_references_transitively(["DIRECTIVE_001"], svc)


@pytest.mark.fast
def test_step_level_tactic_cycle_raises() -> None:
    """A cycle introduced via step-level references must also be caught."""
    # Tactic A references B from a step; Tactic B references A from root.
    tactic_a = _StubTactic("TACTIC_A", step_refs=[("tactic", "TACTIC_B")])
    tactic_b = _StubTactic("TACTIC_B", root_refs=[("tactic", "TACTIC_A")])

    directive = _StubDirective("DIRECTIVE_001", tactic_refs=["TACTIC_A"])
    svc = _StubDoctrineService(
        directives={"DIRECTIVE_001": directive},
        tactics={"TACTIC_A": tactic_a, "TACTIC_B": tactic_b},
    )

    with pytest.raises(DoctrineResolutionCycleError):
        resolve_references_transitively(["DIRECTIVE_001"], svc)


@pytest.mark.fast
def test_acyclic_graph_does_not_raise() -> None:
    """A valid DAG (no cycles) must resolve without raising."""
    # A → B → C  (linear chain, no cycle)
    tactic_c = _StubTactic("TACTIC_C")
    tactic_b = _StubTactic("TACTIC_B", root_refs=[("tactic", "TACTIC_C")])
    tactic_a = _StubTactic("TACTIC_A", root_refs=[("tactic", "TACTIC_B")])

    directive = _StubDirective("DIRECTIVE_001", tactic_refs=["TACTIC_A"])
    svc = _StubDoctrineService(
        directives={"DIRECTIVE_001": directive},
        tactics={"TACTIC_A": tactic_a, "TACTIC_B": tactic_b, "TACTIC_C": tactic_c},
    )

    # Must not raise
    graph = resolve_references_transitively(["DIRECTIVE_001"], svc)
    assert "TACTIC_A" in graph.tactics
    assert "TACTIC_B" in graph.tactics
    assert "TACTIC_C" in graph.tactics


@pytest.mark.fast
def test_diamond_dag_does_not_raise() -> None:
    """A diamond-shaped DAG (A→B, A→C, B→D, C→D) must resolve without raising."""
    tactic_d = _StubTactic("TACTIC_D")
    tactic_b = _StubTactic("TACTIC_B", root_refs=[("tactic", "TACTIC_D")])
    tactic_c = _StubTactic("TACTIC_C", root_refs=[("tactic", "TACTIC_D")])
    tactic_a = _StubTactic(
        "TACTIC_A",
        root_refs=[("tactic", "TACTIC_B"), ("tactic", "TACTIC_C")],
    )

    directive = _StubDirective("DIRECTIVE_001", tactic_refs=["TACTIC_A"])
    svc = _StubDoctrineService(
        directives={"DIRECTIVE_001": directive},
        tactics={
            "TACTIC_A": tactic_a,
            "TACTIC_B": tactic_b,
            "TACTIC_C": tactic_c,
            "TACTIC_D": tactic_d,
        },
    )

    graph = resolve_references_transitively(["DIRECTIVE_001"], svc)
    assert set(graph.tactics) == {"TACTIC_A", "TACTIC_B", "TACTIC_C", "TACTIC_D"}
