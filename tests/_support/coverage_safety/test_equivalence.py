"""Unit tests for the mutation / anti-vacuity helper (T008).

Pure and in-process: the "check" is a plain callable that raises on failure,
so no subprocess or real suite runs here.
"""

from __future__ import annotations

import pytest

from tests._support.coverage_safety.equivalence import (
    Mutation,
    MutationNotCaughtError,
    assert_mutation_caught,
)

pytestmark = [pytest.mark.fast]


def _transition_check(transitions: dict[str, str]) -> None:
    """A representative collapsed-test assertion body."""
    assert transitions["planned"] == "claimed"


_GOOD = {"planned": "claimed", "claimed": "in_progress"}


def _break_first_edge(t: dict[str, str]) -> dict[str, str]:
    t["planned"] = "WRONG"
    return t


def test_caught_mutation_passes_silently() -> None:
    # The check catches the planted regression → no raise (returns None).
    assert_mutation_caught(
        _transition_check,
        _GOOD,
        Mutation(name="planned->claimed dropped", apply=_break_first_edge),
    )


def test_vacuous_test_is_detected() -> None:
    # A mutation the check does NOT look at → the test is vacuous for it.
    def mutate_unwatched_edge(t: dict[str, str]) -> dict[str, str]:
        t["claimed"] = "WRONG"  # the check never asserts on this edge
        return t

    with pytest.raises(MutationNotCaughtError) as exc_info:
        assert_mutation_caught(
            _transition_check,
            _GOOD,
            Mutation(name="claimed->in_progress dropped", apply=mutate_unwatched_edge),
        )
    assert "claimed->in_progress dropped" in str(exc_info.value)
    assert exc_info.value.mutation_name == "claimed->in_progress dropped"


def test_good_data_is_not_mutated_by_the_helper() -> None:
    # The helper deep-copies before mutating; the caller's good data survives.
    good = {"planned": "claimed"}
    assert_mutation_caught(
        _transition_check,
        good,
        Mutation(name="break", apply=_break_first_edge),
    )
    assert good == {"planned": "claimed"}


def test_check_failing_on_good_data_propagates() -> None:
    # If the check rejects good data, that is a mis-wired test, not a caught
    # mutation — the original AssertionError must propagate (not be masked as
    # MutationNotCaughtError).
    def always_fails(_data: dict[str, str]) -> None:
        raise AssertionError("bad on good data")

    with pytest.raises(AssertionError, match="bad on good data"):
        assert_mutation_caught(
            always_fails,
            _GOOD,
            Mutation(name="irrelevant", apply=_break_first_edge),
        )
