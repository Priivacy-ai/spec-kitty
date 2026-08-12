"""The architectural test family must remain reachable from live CI.

Authority: open CI-integrity epic #1931.  This is deliberately only the
negative route invariant; the retired performance-shape assertion about which
job the family may depend on was not a correctness contract.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = pytest.mark.architectural


def test_architectural_suite_has_a_running_job() -> None:
    running = {
        (gate.workflow, gate.job)
        for gate in gc.load_gates()
        if "architectural" in gc.positive_marker_tokens(gate.marker_expr)
    }
    assert running, "no live CI job positively selects the architectural family"
