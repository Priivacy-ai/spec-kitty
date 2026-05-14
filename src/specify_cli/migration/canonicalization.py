"""Transformer-flavor rule pipeline for migration canonicalization.

Implements the ``chain-of-responsibility-rule-pipeline`` tactic (Transformer
flavor) as a typed Protocol + runner. Each rule is a pure function that checks
its own applicability, optionally transforms the state, and returns a
``CanonicalStepResult``. The runner threads state forward, accumulates actions,
and short-circuits on the first error.

Tactic references:
- ``chain-of-responsibility-rule-pipeline`` (Transformer flavor): each rule
  has contract ``(state, ctx) -> StepResult(state', actions, error?)``.
  Order matters; runner short-circuits on ``error``.
- ``refactoring-extract-first-order-concept``: each rule is a first-order
  concept with a single responsibility.

Usage::

    from specify_cli.migration.canonicalization import (
        CanonicalRule,
        CanonicalStepResult,
        CanonicalPipelineResult,
        MigrationContext,
        apply_rules,
    )

    _MY_RULES: tuple[CanonicalRule[Row], ...] = (
        _rule_one,
        _rule_two,
    )

    result = apply_rules(_MY_RULES, dict(data), ctx)

.. note::
    ``MigrationContext.generated_ids`` is the **one** mutable element on the
    context — by design, rules append minted IDs so the caller observes them.
    This is a documented exception to the immutability invariant; rules MUST
    use ``.append()`` only and MUST NOT replace the list reference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar
from collections.abc import Sequence

__all__ = [
    "CanonicalPipelineResult",
    "CanonicalRule",
    "CanonicalStepResult",
    "MigrationContext",
    "apply_rules",
]

State = TypeVar("State")


@dataclass(frozen=True)
class MigrationContext:
    """Per-pipeline context threaded alongside the state.

    Generic across migration shapes (status events, frontmatter, sync
    envelopes).  The mission identity fields are required and immutable.

    ``generated_ids`` is the one exception: rules that mint new event IDs
    append to this list so the caller can observe them.  It is a mutable
    list on an otherwise frozen dataclass — safe because the caller owns the
    list and rules use ``.append()`` only.
    """

    mission_slug: str
    mission_id: str
    line_number: int
    generated_ids: list[str] | None = field(default=None)


@dataclass(frozen=True)
class CanonicalStepResult(Generic[State]):
    """Output of a single rule application.

    Invariants:
    - ``error is not None`` → runner short-circuits.
    - ``error is None`` and ``actions == ()`` is the passthrough idiom.
    - ``actions`` is a tuple (not list) — immutable; safe to thread across
      rule boundaries without defensive copying.
    """

    state: State
    actions: tuple[str, ...] = ()
    error: str | None = None

    @classmethod
    def passthrough(cls, state: State) -> CanonicalStepResult[State]:
        """Return a no-op result: rule did not apply."""
        return cls(state=state, actions=(), error=None)


@dataclass(frozen=True)
class CanonicalPipelineResult(Generic[State]):
    """Output of the runner after all rules complete (or short-circuit).

    Invariants:
    - ``error is None`` → ``state is not None``; pipeline completed.
    - ``error is not None`` → ``state is None``; ``actions`` includes
      whatever rules ran before the short-circuit.
    """

    state: State | None
    actions: tuple[str, ...]
    error: str | None


class CanonicalRule(Protocol[State]):
    """Per-step contract for the Transformer-flavor rule pipeline.

    Each rule MUST be a pure function: no I/O, no globals, no in-place
    mutation of ``state`` beyond the returned value.

    - A rule that does not apply returns ``CanonicalStepResult.passthrough(state)``.
    - A rule that detects a hard error returns a ``CanonicalStepResult`` with
      ``error`` set; the runner short-circuits immediately.
    """

    def __call__(
        self, state: State, ctx: MigrationContext
    ) -> CanonicalStepResult[State]:
        """Apply this rule to *state* with *ctx*; return the step result."""
        ...  # pragma: no cover


def apply_rules(
    rules: Sequence[CanonicalRule[State]],
    state: State,
    ctx: MigrationContext,
) -> CanonicalPipelineResult[State]:
    """Thread *state* through *rules*; short-circuit on the first error.

    Accumulates ``actions`` from all rules that ran before the short-circuit
    (or all rules if the pipeline completes successfully).
    """
    accumulated_actions: list[str] = []
    current = state
    for rule in rules:
        result = rule(current, ctx)
        accumulated_actions.extend(result.actions)
        if result.error is not None:
            return CanonicalPipelineResult(
                state=None,
                actions=tuple(accumulated_actions),
                error=result.error,
            )
        current = result.state
    return CanonicalPipelineResult(
        state=current,
        actions=tuple(accumulated_actions),
        error=None,
    )
