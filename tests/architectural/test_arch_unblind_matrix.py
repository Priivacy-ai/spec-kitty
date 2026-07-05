"""SC-002 / NFR-002 — architectural un-blind differential matrix invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 (red-first). Asserts the
differential-matrix relation (:func:`_gate_coverage.differential_arch_matrix`)
selects the architectural + adversarial suite over **100 %** of
``src/specify_cli/*`` dirs — 0 arch-blind (SC-002).

Authored FAILING against today's topology: the arch/adversarial suite runs only
as the ``architectural`` matrix shard of ``integration-tests-core-misc``, gated
by the ``core_misc``/``execution_context``/``acceptance`` filter outputs, so 13
mapped dirs never fire it (Mode-B blindness). WP03's always-on arch job (Option
A — no filter group) flips every dir to arch-selected by construction.

Consumes only the additive WP01 relation; it does not re-derive the model.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]


def test_matrix_spans_every_src_package_dir() -> None:
    """The differential matrix is defined over 100 % of src/specify_cli dirs."""
    matrix = gc.differential_arch_matrix()
    assert set(matrix) == set(gc.src_package_loc()), (
        "differential arch matrix does not span every src/specify_cli/* dir"
    )


def test_no_src_dir_is_architecturally_blind() -> None:
    """RED today: 0 dirs may be arch-blind (SC-002 / NFR-002).

    Today 13 mapped dirs are arch-blind because the arch suite is gated behind
    ``core_misc``/``execution_context``/``acceptance`` filter outputs. WP03's
    always-on arch pole (no filter group) turns every dir arch-selected.
    """
    blind = gc.arch_blind_src_dirs()
    assert blind == (), (
        f"src dirs the architectural suite never fires on (pre-WP03 RED, "
        f"{len(blind)}): {list(blind)}"
    )


def test_every_dir_is_arch_selected() -> None:
    """RED today: the differential matrix must be all-True (100 % coverage)."""
    matrix = gc.differential_arch_matrix()
    not_selected = sorted(name for name, selected in matrix.items() if not selected)
    assert not not_selected, (
        "src dirs not arch-selected by the differential matrix (pre-WP03 RED, "
        f"{len(not_selected)}): {not_selected}"
    )
