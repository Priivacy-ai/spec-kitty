"""``status_event_row``-scoped audit shape tests (WP10, C-8 / FR-014, FR-016).

Two distinct guarantees live here, both scoped to the ``status_event_row``
artifact type (NOT ``meta.json`` — that artifact is covered by the separate,
``meta.json``-scoped ``tests/audit/test_shape_registry_writer_parity.py``,
which is a subset-of-annotations tautology and cannot see this artifact):

* **T030 (red-first, #3543)** — a ``status_event_row`` carrying a
  ``review_result`` must audit with **0 ``UNKNOWN_SHAPE``** findings. On base
  ``review_result`` is absent from the ``status_event_row`` frozenset, so the
  row is flagged ``UNKNOWN_SHAPE``: RED. After registration (T031): GREEN.

* **T032 (drift)** — every top-level key a persisted ``status_event_row``
  actually carries (i.e. the exact key set the ``StatusEvent`` writer emits)
  must be registered. This is genuinely falsifiable: a persisted-but-
  unregistered key turns it red. A companion test injects a bogus key and
  asserts the audit *would* flag it, pinning the falsifiability rather than
  trusting a tautology.

Neither test repurposes the ``meta.json``-scoped writer-parity test.
"""

from __future__ import annotations

import pytest

from specify_cli.audit.shape_registry import (
    KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT,
    check_unknown_keys,
    status_event_row_artifact_type,
)
from specify_cli.status.models import Lane, ReviewResult, StatusEvent

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_ARTIFACT = "status_event_row"


def _review_carrying_event() -> StatusEvent:
    """A canonical ``in_review -> approved`` transition carrying a verdict.

    Built through the real ``StatusEvent`` value object so ``to_dict`` emits
    exactly the on-disk row shape a persisted ``status.events.jsonl`` line
    carries — including the ``review_result`` key that is the residual under
    test.
    """
    return StatusEvent(
        event_id="01JAAAAAAAAAAAAAAAAAAAAAAA",
        mission_slug="worktree-root-resolution-01M0B59R",
        wp_id="WP10",
        from_lane=Lane.IN_REVIEW,
        to_lane=Lane.APPROVED,
        at="2026-08-18T21:00:00+00:00",
        actor="claude",
        force=False,
        execution_mode="worktree",
        review_ref="approval://abc",
        review_result=ReviewResult(
            reviewer="reviewer-rachel",
            verdict="approved",
            reference="approval://abc",
        ),
        mission_id="01M0B59RAAAAAAAAAAAAAAAAAA",
    )


def _persisted_row() -> dict[str, object]:
    """The exact dict a persisted ``status_event_row`` carries on disk."""
    row: dict[str, object] = dict(_review_carrying_event().to_dict())
    return row


@pytest.mark.regression
def test_review_result_row_audits_clean() -> None:
    """T030 (#3543): a review-carrying row must emit 0 ``UNKNOWN_SHAPE``.

    RED on base (``review_result`` unregistered → ``UNKNOWN_SHAPE``);
    GREEN after T031 registers the field.
    """
    row = _persisted_row()
    assert "review_result" in row, "generator must emit a review_result key"

    artifact_type = status_event_row_artifact_type(row)
    assert artifact_type == _ARTIFACT

    findings = check_unknown_keys(artifact_type, row, "status.events.jsonl")
    unknown = [f for f in findings if f.code == "UNKNOWN_SHAPE"]
    assert unknown == [], (
        "a review_result-carrying status_event_row must audit clean; "
        f"got UNKNOWN_SHAPE findings: {[f.detail for f in unknown]}"
    )


@pytest.mark.regression
def test_persisted_row_keys_all_registered() -> None:
    """T032 drift: every key a persisted row carries must be registered.

    Enumerates the real writer's key set (``StatusEvent.to_dict``) and asserts
    each is in the ``status_event_row`` frozenset. RED on base because the
    persisted ``review_result`` key is unregistered.
    """
    row = _persisted_row()
    known = KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT[_ARTIFACT]

    unregistered = sorted(set(row) - known)
    assert unregistered == [], (
        "persisted status_event_row carries keys absent from the registry: "
        f"{unregistered}"
    )


def test_drift_test_is_falsifiable() -> None:
    """T032 falsifiability proof: an unregistered key IS flagged.

    Guards against the tautology trap — proves the drift check has teeth by
    injecting a key the registry does not know and asserting the audit flags
    it ``UNKNOWN_SHAPE``. (Documented, deliberately not left in the fixture the
    positive test consumes.)
    """
    row = _persisted_row()
    row["totally_unregistered_key"] = "x"

    findings = check_unknown_keys(_ARTIFACT, row, "status.events.jsonl")
    flagged = [f for f in findings if f.code == "UNKNOWN_SHAPE"]
    assert any("totally_unregistered_key" in f.detail for f in flagged), (
        "the drift check must flag an unregistered persisted key"
    )
