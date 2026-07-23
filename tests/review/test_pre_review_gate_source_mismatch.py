"""``GateOutcome.SOURCE_MISMATCH`` construction + fail-open assertion (T022/T023,
mission ``scopesource-gate-followup-01KY6S9P`` WP04, FR-009/FR-011).

Covers:

- ``_evaluate_via_scope_source`` constructs ``SOURCE_MISMATCH`` when the
  head-side identity (``scope_source_identity(scope_source, raw)``) differs
  from a KNOWN (non-``"unknown"``) ``baseline.source_identity`` — sensitive to
  BOTH the source class AND its parse-mode (data-model.md sec. 2 B2: "same
  class, different parse-mode" must also mismatch, not just a class-only
  token).
- ``baseline is None`` or ``baseline.source_identity == "unknown"`` degrades
  to the existing ``UNVERIFIED_BASELINE`` path — never a mismatch.
- A MATCHING identity falls through to the normal
  ``_classify_current_failures`` diff, unaffected.
- ``verdict_aggregation.aggregate_verdicts`` routes ``SOURCE_MISMATCH`` to
  ``WARN_PROCEED`` even with ``block_enabled=True`` (SC-004 fail-open demo) —
  asserted structurally against the member allowlists, never by editing them.
- ``tasks_move_task._mt_pre_review_gate_console_warning``'s ladder: the new
  ``SOURCE_MISMATCH`` branch names both identities; the explicit
  ``NO_NEW_FAILURES`` branch; and the defensive ``else`` for a hypothetical
  future outcome (T023).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from specify_cli.cli.commands.agent import tasks_move_task as tmt
from specify_cli.review import pre_review_gate
from specify_cli.review.baseline import BaselineFailure, BaselineTestResult
from specify_cli.review.pre_review_gate import GateOutcome, GateVerdict, ScopeResult
from specify_cli.review.scope_source import RawRunResult
from specify_cli.review.verdict_aggregation import (
    AggregateDecision,
    _TERMINAL_OUTCOMES,
    aggregate_verdicts,
)

pytestmark = [pytest.mark.fast]

_NONEMPTY_SCOPE = ScopeResult(
    test_targets=("anything",),
    matched_shard_groups=(),
    matched_composite_dirs=(),
    empty_cone_composite_dirs=(),
    excluded_scope_files=(),
)


@dataclass
class _StubScopeSourceBase:
    """A minimal, real (non-narrowing) ``ScopeSource`` implementer.

    Runs a genuinely trivial, always-clean subprocess (never a stubbed
    ``test_command() -> None`` short-circuit) so ``_evaluate_via_scope_source``
    actually reaches its post-run identity comparison — the branch under test.
    """

    mode: str = "junit_xml"

    def test_command(self) -> list[str] | None:
        return [sys.executable, "-c", "pass"]

    def file_to_scope(self, path: str) -> tuple[str, ...]:
        del path
        return ("anything",)

    def parse_mode(self, raw: RawRunResult) -> str:
        del raw
        return self.mode

    def parse_results(self, raw: RawRunResult) -> tuple[BaselineFailure, ...]:
        del raw
        return ()


class _StubSourceAlpha(_StubScopeSourceBase):
    """Distinguishable class name -- the class half of the identity token."""


class _StubSourceBeta(_StubScopeSourceBase):
    """A DIFFERENT class name from :class:`_StubSourceAlpha`."""


def _baseline_with_identity(source_identity: str) -> BaselineTestResult:
    return BaselineTestResult(
        wp_id="WP04",
        captured_at="2026-07-23T10:00:00Z",
        base_branch="main",
        base_commit="abc1234",
        test_runner="pytest",
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        failures=(),
        source_identity=source_identity,
    )


def _evaluate(scope_source: Any, baseline: BaselineTestResult | None) -> GateVerdict:
    return pre_review_gate.evaluate_pre_review_gate(
        ["anything/at/all.py"],
        repo_root=Path("."),
        baseline=baseline,
        scope_source=scope_source,
    )


# ---------------------------------------------------------------------------
# T022 -- construction
# ---------------------------------------------------------------------------


def test_known_mismatched_class_yields_source_mismatch() -> None:
    baseline = _baseline_with_identity("_StubSourceAlpha/junit_xml")
    verdict = _evaluate(_StubSourceBeta(), baseline)

    assert verdict.outcome is GateOutcome.SOURCE_MISMATCH
    assert "_StubSourceAlpha/junit_xml" in (verdict.reason or "")
    assert "_StubSourceBeta/junit_xml" in (verdict.reason or "")


def test_known_mismatched_parse_mode_is_also_a_mismatch_same_class() -> None:
    """B2 (data-model.md sec. 2): SAME class, DIFFERENT parse-mode must also
    mismatch -- a class-only token would miss this."""
    baseline = _baseline_with_identity("_StubSourceAlpha/junit_xml")
    verdict = _evaluate(_StubSourceAlpha(mode="text"), baseline)

    assert verdict.outcome is GateOutcome.SOURCE_MISMATCH
    assert "_StubSourceAlpha/junit_xml" in (verdict.reason or "")
    assert "_StubSourceAlpha/text" in (verdict.reason or "")


def test_matching_identity_falls_through_to_normal_classification() -> None:
    """No mismatch when the identities agree -- normal diff-baseline
    classification proceeds unaffected."""
    baseline = _baseline_with_identity("_StubSourceAlpha/junit_xml")
    verdict = _evaluate(_StubSourceAlpha(mode="junit_xml"), baseline)

    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert verdict.outcome is not GateOutcome.SOURCE_MISMATCH


def test_none_baseline_degrades_to_unverified_baseline_not_mismatch() -> None:
    verdict = _evaluate(_StubSourceAlpha(), None)

    assert verdict.outcome is GateOutcome.UNVERIFIED_BASELINE
    assert verdict.outcome is not GateOutcome.SOURCE_MISMATCH


def test_unknown_baseline_identity_never_mismatches_and_falls_through_to_normal_diff() -> None:
    """A straddling-upgrade baseline (captured before ``source_identity``
    existed) carries the field's own ``"unknown"`` default -- never a
    mismatch, even against a head identity that would otherwise differ. The
    SOURCE_MISMATCH check is SKIPPED entirely (not force-converted to
    ``UNVERIFIED_BASELINE``): a valid, non-sentinel ``"unknown"``-identity
    baseline still falls through to the SAME ``_classify_current_failures``
    diff every other valid baseline drives -- here, no failures on either
    side, so it's a clean ``NO_NEW_FAILURES``."""
    baseline = _baseline_with_identity("unknown")
    verdict = _evaluate(_StubSourceBeta(), baseline)

    assert verdict.outcome is not GateOutcome.SOURCE_MISMATCH
    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES


def test_sentinel_baseline_unknown_identity_degrades_to_unverified_baseline() -> None:
    """A REALISTIC capture-failed sentinel baseline (``failed == -1``,
    produced by ``baseline._make_sentinel`` -- which never sets
    ``source_identity``, so it carries the field's own ``"unknown"``
    default) skips the SOURCE_MISMATCH check (unknown identity) and falls
    through to ``_classify_current_failures``, which degrades ``failed ==
    -1`` to ``UNVERIFIED_BASELINE`` -- never a mismatch, even against a head
    identity that would otherwise differ."""
    baseline = BaselineTestResult(
        wp_id="WP04",
        captured_at="2026-07-23T10:00:00Z",
        base_branch="main",
        base_commit="",
        test_runner="pytest",
        total=0,
        passed=0,
        failed=-1,
        skipped=0,
        failures=(),
    )
    verdict = _evaluate(_StubSourceBeta(), baseline)

    assert verdict.outcome is GateOutcome.UNVERIFIED_BASELINE
    assert verdict.outcome is not GateOutcome.SOURCE_MISMATCH


# ---------------------------------------------------------------------------
# SC-004 -- fail-open by construction, asserted (never filter-edited)
# ---------------------------------------------------------------------------


def test_source_mismatch_is_absent_from_terminal_outcomes_allowlist() -> None:
    assert GateOutcome.SOURCE_MISMATCH not in _TERMINAL_OUTCOMES


def test_source_mismatch_never_blocks_even_with_block_enabled() -> None:
    """SC-004 demo: ``aggregate_verdicts`` routes a ``SOURCE_MISMATCH``
    verdict to ``WARN_PROCEED`` -- even with ``block_enabled=True`` -- because
    the block predicate is a ``NEW_FAILURES``-only member allowlist that
    SOURCE_MISMATCH is absent from. This is asserted, never enforced by
    editing ``_TERMINAL_OUTCOMES`` / the block predicate (FR-011)."""
    verdict = GateVerdict(
        outcome=GateOutcome.SOURCE_MISMATCH,
        scope=_NONEMPTY_SCOPE,
        reason="baseline captured under A; head ran under B",
    )

    aggregate = aggregate_verdicts([verdict], block_enabled=True, force=False)

    assert aggregate.decision is AggregateDecision.WARN_PROCEED
    assert aggregate.transition_applied is True
    assert aggregate.should_exit is False
    assert aggregate.blocking_verdicts == ()
    assert aggregate.terminal_verdict is None


# ---------------------------------------------------------------------------
# T023 -- console ladder
# ---------------------------------------------------------------------------


def test_console_warning_names_both_identities_for_source_mismatch() -> None:
    verdict = GateVerdict(
        outcome=GateOutcome.SOURCE_MISMATCH,
        scope=_NONEMPTY_SCOPE,
        reason=(
            "baseline captured under GateCoverageScopeSource/junit_xml; head ran under "
            "DeclaredCommandScopeSource/text — failure identities are not comparable"
        ),
    )

    line = tmt._mt_pre_review_gate_console_warning(verdict, block_enabled=False)

    assert "source_mismatch" in line
    assert "GateCoverageScopeSource/junit_xml" in line
    assert "DeclaredCommandScopeSource/text" in line


def test_console_warning_explicit_no_new_failures_branch() -> None:
    verdict = GateVerdict(outcome=GateOutcome.NO_NEW_FAILURES, scope=_NONEMPTY_SCOPE)

    line = tmt._mt_pre_review_gate_console_warning(verdict, block_enabled=False)

    assert "no new failures" in line


def test_console_warning_defensive_else_renders_outcome_value_for_an_unknown_member() -> None:
    """T023 defensive ``else``: a hypothetical FUTURE ``GateOutcome`` member —
    one this ladder has never seen — must render its raw value, never
    silently fall through as a clean pass. Simulated via a duck-typed
    stand-in (``GateVerdict.outcome`` carries no runtime enum enforcement)
    since ``GateOutcome`` itself cannot be extended without a code change."""

    class _FutureOutcome:
        value = "totally_new_outcome"

    verdict = GateVerdict(outcome=_FutureOutcome(), scope=_NONEMPTY_SCOPE)

    line = tmt._mt_pre_review_gate_console_warning(verdict, block_enabled=False)

    assert "totally_new_outcome" in line
    assert "no new failures" not in line
