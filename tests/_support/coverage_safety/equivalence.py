"""Equivalence / mutation-check helper (T008, C-001).

When a test is collapsed or parametrized (e.g. the FSM-collapse in WP03), the
risk is *vacuity*: the new test passes but no longer catches the regression the
original caught. This helper gives restructured tests a repeatable, in-process
way to prove they still bite:

1. Run the target check against the *good* data-under-test → it must PASS.
2. Inject a single known-bad :class:`Mutation` into a copy of the data → the
   same check must now FAIL **and name the mutation** (anti-vacuity).

If the mutated run still passes, the test is vacuous: :func:`assert_mutation_caught`
raises :class:`MutationNotCaughtError` naming the planted mutation so the
author knows exactly which regression slips through.

The helper is pure and in-process: the "check" is a plain callable that raises
on failure (e.g. an ``assert`` body), so no subprocess or real suite is run in
the helper's own unit tests (Risks & Mitigations). See ``README.md`` for the
recipe.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

__all__ = [
    "Mutation",
    "MutationNotCaughtError",
    "assert_mutation_caught",
]

T = TypeVar("T")

# A check is any callable that raises on failure (typically AssertionError) and
# returns normally on success. This matches the body of an ordinary pytest
# assertion extracted into a function.
Check = Callable[[T], None]


@dataclass(frozen=True)
class Mutation(Generic[T]):
    """A single known-bad change to apply to the data-under-test.

    *name* identifies the regression class this mutation simulates (it appears
    in the failure message so a vacuous test names the exact gap). *apply*
    receives a deep copy of the good data and returns the mutated data — it
    must NOT mutate its argument in place for the caller's benefit, though
    operating on the provided copy is fine.
    """

    name: str
    apply: Callable[[T], T]


class MutationNotCaughtError(AssertionError):
    """Raised when a planted mutation does NOT make the check fail.

    A passing mutated run means the test is vacuous w.r.t. *mutation* — it
    would not catch that regression. Subclasses :class:`AssertionError` so it
    surfaces as a normal test failure.
    """

    def __init__(self, mutation_name: str) -> None:
        self.mutation_name = mutation_name
        super().__init__(
            "Anti-vacuity check FAILED (C-001): the planted mutation "
            f"{mutation_name!r} did NOT make the test fail. The collapsed/"
            "parametrized test is vacuous for this regression class — it would "
            "pass even when the behaviour is broken. Strengthen the assertion "
            "so the mutation is caught."
        )


def assert_mutation_caught(
    check: Check[T],
    good_data: T,
    mutation: Mutation[T],
) -> None:
    """Prove *check* passes on *good_data* and fails on the mutated copy.

    Steps:

    1. ``check(good_data)`` must return normally — a sanity gate; if the check
       fails on good data, the test is mis-wired (re-raised as-is so the
       original failure is visible).
    2. A deep copy of *good_data* is passed through ``mutation.apply`` and
       ``check`` is run on the result. The check MUST raise. If it returns
       normally, the test is vacuous → :class:`MutationNotCaughtError`.

    Returns ``None`` when the mutation is caught (the test is non-vacuous).
    """
    # Step 1 — the check must accept good data. Let any failure propagate; a
    # check that rejects good data is a broken test, not a caught mutation.
    check(good_data)

    # Step 2 — apply the mutation to an isolated copy and expect a failure.
    mutated = mutation.apply(copy.deepcopy(good_data))
    try:
        check(mutated)
    except AssertionError:
        return  # mutation caught — the test is non-vacuous.
    raise MutationNotCaughtError(mutation.name)
