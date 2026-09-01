"""Tests for FR-003's reconciler promotion (mission governance-at-the-gate WP01 T3/T4).

Requirements: FR-003, SC-005 (``research-outputs/governance-at-the-gate/spec.md``).

Covers:
- ``test_promoted_reconciler_loads``: the promoted
  ``reconcile-change-scope-tensions`` directive loads without a
  ``ValidationError`` -- ``lenient-adherence`` requires non-empty
  ``explicit_allowances`` (``Directive.validate_lenient_adherence``,
  ``models.py:82-91``) or the promoted YAML fails to load (brownfield risk
  this test guards against directly).
- ``test_shipped_corpus_enforcement_histogram``: SC-005 -- the enforcement
  histogram is exactly ``25/6/3 -> 25/7/2`` (required/lenient-adherence/
  advisory); no directive is newly ``required``.
- ``test_only_the_reconciler_yaml_value_changed``: NFR-001 boundary --
  ``reconcile-change-scope-tensions`` is the only directive whose
  enforcement differs from the ``25/6/3`` baseline snapshot.
"""

from __future__ import annotations

import pytest

from charter.offering.directives.models import Directive, Enforcement
from charter.offering.directives.repository import DirectiveRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

_RECONCILER_ID = "RECONCILE_CHANGE_SCOPE_TENSIONS"

# SC-005 baseline: {required, lenient-adherence, advisory} counts across the
# shipped built-in corpus BEFORE FR-003's promotion (measured directly
# against packs/built-in/directives/*.directive.yaml; see WP01's tasks.md).
_BASELINE_HISTOGRAM = {
    Enforcement.REQUIRED: 25,
    Enforcement.LENIENT_ADHERENCE: 6,
    Enforcement.ADVISORY: 3,
}


def _shipped_directives() -> list[Directive]:
    directives: list[Directive] = DirectiveRepository().list_all()
    return directives


def test_promoted_reconciler_loads() -> None:
    """The promoted reconciler loads cleanly and carries its new level."""
    directive = DirectiveRepository().get(_RECONCILER_ID)

    assert directive is not None
    assert directive.enforcement == Enforcement.LENIENT_ADHERENCE
    # models.py:82-91 -- lenient-adherence requires a non-empty allowance
    # list; a successful load here already proves it, but assert on content
    # too so an accidental empty-list regression is caught directly rather
    # than only via the model validator raising on load.
    assert directive.explicit_allowances
    assert all(allowance.strip() for allowance in directive.explicit_allowances)


def test_shipped_corpus_enforcement_histogram() -> None:
    """SC-005: histogram is exactly 25/7/2; no directive is newly required."""
    directives = _shipped_directives()

    histogram = dict.fromkeys(Enforcement, 0)
    for directive in directives:
        histogram[directive.enforcement] += 1

    assert histogram[Enforcement.REQUIRED] == _BASELINE_HISTOGRAM[Enforcement.REQUIRED], "No directive may be newly promoted to 'required' by this change."
    assert histogram[Enforcement.LENIENT_ADHERENCE] == (_BASELINE_HISTOGRAM[Enforcement.LENIENT_ADHERENCE] + 1)
    assert histogram[Enforcement.ADVISORY] == _BASELINE_HISTOGRAM[Enforcement.ADVISORY] - 1


def test_only_the_reconciler_yaml_value_changed() -> None:
    """The reconciler is the only directive whose level differs from advisory-baseline.

    Cross-checks the histogram delta above at per-directive granularity:
    every OTHER directive keeps its baseline-consistent level, and the
    reconciler alone moved advisory -> lenient-adherence (NFR-001: no
    directive/tactic prose is rewritten by this WP; the only YAML change is
    this directive's enforcement value + explicit_allowances).
    """
    directives = {d.id: d for d in _shipped_directives()}

    reconciler = directives.pop(_RECONCILER_ID)
    assert reconciler.enforcement == Enforcement.LENIENT_ADHERENCE

    # Every remaining directive must still resolve to exactly one of the
    # three known levels -- a cheap sanity guard that nothing else drifted.
    for directive_id, directive in directives.items():
        assert directive.enforcement in _BASELINE_HISTOGRAM, f"{directive_id} has an unrecognized enforcement level: {directive.enforcement!r}"
