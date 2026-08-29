"""Tests for FR-005 (mission governance-at-the-gate WP03): ``DIRECTIVE_003``
moves off the ``implement`` action scope onto ``review``.

Requirements: FR-005, US1, SC-001, SC-003
(``research-outputs/governance-at-the-gate/spec.md``).

Brownfield-verified fact this module's headline test is built around: the
``review -> DIRECTIVE_003`` edge visible in today's generated
``packs/built-in/action.graph.yaml`` is synthesized by the CALIBRATOR
(``charter.offering.drg.migration.calibrator.calibrate_surfaces``), which
copies missing scope edges from ``implement`` onto ``review`` whenever
``|review scope| < 0.80 * |implement scope|``. That means deleting
``DIRECTIVE_003`` from ``implement/index.yaml`` ALONE also strips it from
``review`` (the calibrator has nothing left to copy) -- so a test that only
checks "review still has 003" is vacuous (the calibrator already delivers it
today, before any fix). The one non-vacuous, load-bearing assertion is the
COMBINED one below: ``implement`` lacks ``DIRECTIVE_003`` **and** ``review``
still delivers it -- which is only true once ``DIRECTIVE_003`` has been
explicitly added to ``review/index.yaml`` as its own scope source (not
merely calibrated in from a source that no longer carries it).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.context import build_charter_context_json

pytestmark = [pytest.mark.doctrine, pytest.mark.unit]

_DIRECTIVE_003 = "DIRECTIVE_003"


def _delivered_directive_ids(payload: dict[str, object]) -> set[str]:
    """Extract the ``id`` set from the action-scoped ``directives`` array.

    Deliberately reads the action-scoped ``directives`` array (delivery for
    THIS action), never the governance-wide ``all_directives`` array (every
    directive id the project resolver knows about, regardless of any
    action's scope) -- the two are distinct top-level keys and only the
    former answers "is DIRECTIVE_003 delivered to this action".
    """
    entries = payload.get("directives", [])
    assert isinstance(entries, list)
    return {
        str(entry["id"])  # type: ignore[index]
        for entry in entries
    }


def test_implement_lacks_003_but_review_still_delivers_it(tmp_path: Path) -> None:
    """The combined, load-bearing FR-005/SC-001/SC-003 assertion.

    ``charter context --action implement --json`` must no longer deliver
    ``DIRECTIVE_003`` (it was removed from ``implement/index.yaml`` and the
    class-level FR-004 gate now forbids a `required` decision-documentation
    directive from being scoped there again), AND
    ``charter context --action review --json`` must still deliver it (it was
    added to ``review/index.yaml`` directly -- load-bearing per the
    calibrator note above, not a residual calibrated copy).
    """
    implement_payload = build_charter_context_json(
        tmp_path, action="implement", mission_type="software-dev"
    )
    review_payload = build_charter_context_json(
        tmp_path, action="review", mission_type="software-dev"
    )

    implement_ids = _delivered_directive_ids(implement_payload)
    review_ids = _delivered_directive_ids(review_payload)

    assert _DIRECTIVE_003 not in implement_ids, (
        "DIRECTIVE_003 must no longer be scoped onto the implement action "
        f"(FR-005); delivered implement directives were: {sorted(implement_ids)}"
    )
    assert _DIRECTIVE_003 in review_ids, (
        "DIRECTIVE_003 must be delivered to the review action, sourced from "
        "review/index.yaml itself -- not merely a stale calibrator copy from "
        f"implement (FR-005); delivered review directives were: {sorted(review_ids)}"
    )


def test_plan_specify_tasks_retrospect_retain_003(tmp_path: Path) -> None:
    """Edge case guard: the OTHER retained ``DIRECTIVE_003`` bindings survive.

    US1 removes only the ``implement`` binding and adds ``review``;
    ``plan``/``specify``/``tasks``/``retrospect`` are intentionally retained
    (legitimate authoring/decision points) -- a plan must not strip them by
    analogy (spec.md Edge Cases). This is a regression guard, not new
    behaviour this WP introduces.
    """
    for action in ("plan", "specify", "tasks", "retrospect"):
        payload = build_charter_context_json(
            tmp_path, action=action, mission_type="software-dev"
        )
        ids = _delivered_directive_ids(payload)
        assert _DIRECTIVE_003 in ids, (
            f"DIRECTIVE_003 must remain scoped onto the retained '{action}' "
            f"action; delivered directives were: {sorted(ids)}"
        )
