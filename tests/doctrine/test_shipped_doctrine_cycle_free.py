"""Integration test: shipped doctrine artifacts must form a cycle-free reference graph.

This test exercises the actual resolution entrypoint (``resolve_references_transitively``)
against the full set of shipped doctrine artifacts loaded through the real
``DoctrineService``. It provides a build-time guarantee that no cycle exists in
the shipped artifact set — catching misconfiguration before it reaches users.

Unlike ``test_directive_consistency.py::test_tactic_reference_graph_has_no_cycles``
(which inspects raw YAML files directly), this test goes through the exact same
``DoctrineService`` + ``_Walker`` code path that runs at execution time, so it
also validates that the resolution infrastructure itself handles the shipped set
correctly.

Not marked ``@pytest.mark.fast`` because it performs filesystem I/O (reads shipped
YAML files). It runs in the default (non-fast) pytest sweep and in CI.
"""

from __future__ import annotations

import pytest

from doctrine.service import DoctrineService
from doctrine.shared.exceptions import DoctrineResolutionCycleError
from charter.reference_resolver import resolve_references_transitively


@pytest.fixture(scope="module")
def shipped_service() -> DoctrineService:
    """DoctrineService loaded from shipped-only artifacts (no project overrides)."""
    return DoctrineService()


def test_shipped_directives_resolve_without_cycles(shipped_service: DoctrineService) -> None:
    """Resolving ALL shipped directives must not raise DoctrineResolutionCycleError.

    This is the primary build-time safety net: if any shipped directive or its
    transitively referenced tactics form a cycle, this test fails immediately,
    preventing the artifact set from reaching users.
    """
    all_directive_ids = [d.id for d in shipped_service.directives.list_all()]
    assert all_directive_ids, "No shipped directives found — check doctrine package installation"

    # If a cycle exists in the shipped artifact set, this call raises.
    # A passing test proves the shipped artifacts form a valid DAG.
    try:
        graph = resolve_references_transitively(all_directive_ids, shipped_service)
    except DoctrineResolutionCycleError as exc:
        pytest.fail(
            f"Cycle detected in shipped doctrine artifacts — this is a packaging error.\n"
            f"Cycle path: {' → '.join(f'{t}/{i}' for t, i in exc.cycle)}"
        )

    # Verify the resolved graph is structurally sound.
    assert graph.tactics is not None
    assert graph.directives is not None


def test_shipped_tactics_individually_cycle_free(shipped_service: DoctrineService) -> None:
    """Each shipped tactic must be individually resolvable without forming a cycle.

    Walks each tactic in isolation (via a synthetic directive pointing to it)
    to verify that no tactic-only subgraph contains a cycle even when directives
    are excluded from the starting set.
    """
    all_tactics = shipped_service.tactics.list_all()
    assert all_tactics, "No shipped tactics found"

    cycles_found: list[str] = []

    for tactic in all_tactics:
        # Build a minimal synthetic DoctrineService with only this tactic and its
        # transitively reachable neighbours — we reuse the real service which already
        # has everything loaded.
        #
        # We trigger resolution by fabricating a directive that points to this tactic.
        # The real directive resolver will fall back gracefully if the synthetic ID is
        # not found; we instead call the tactic handler directly via a single-element
        # directive that only references this tactic.
        #
        # Simpler: just walk from this tactic via the real service.
        from charter.reference_resolver import _Walker  # noqa: PLC0415

        walker = _Walker(shipped_service)
        try:
            walker.walk("tactics", tactic.id)
        except DoctrineResolutionCycleError as exc:
            cycle_str = " → ".join(f"{t}/{i}" for t, i in exc.cycle)
            cycles_found.append(f"{tactic.id}: {cycle_str}")

    assert not cycles_found, (
        "Cycles detected in shipped tactic subgraphs:\n" + "\n".join(cycles_found)
    )


def test_shipped_resolution_graph_all_resolved(shipped_service: DoctrineService) -> None:
    """Resolving all shipped directives must leave no unresolved references.

    Validates that every tactic_ref, styleguide ref, toolguide ref, etc. pointed
    to by shipped directives actually exists in the shipped artifact set.
    This is a consistency check: if an artifact references a non-existent peer,
    the graph is incomplete.
    """
    all_directive_ids = [d.id for d in shipped_service.directives.list_all()]
    graph = resolve_references_transitively(all_directive_ids, shipped_service)

    if graph.unresolved:
        unresolved_str = "\n".join(f"  {t}/{i}" for t, i in graph.unresolved)
        pytest.fail(
            f"Shipped doctrine has unresolved cross-references "
            f"(dangling pointers in the artifact graph):\n{unresolved_str}"
        )
