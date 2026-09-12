"""FR-003 (#3338) — the recommended diagnostic must be reachable on a wedged project.

The failed ``backfill-runtime-state`` migration aborts with a message telling the
operator to run ``spec-kitty migrate backfill-runtime-state --mission <slug> --dry-run``
to inspect the cause.  Before this work package only the bare ``("migrate",)`` path
was registered SAFE, and ``classify()`` fails closed on the missing subcommand path
(``("migrate", "backfill-runtime-state")``) -> UNSAFE -> BLOCK_PROJECT_MIGRATION.  The
recommended diagnostic was therefore gated behind the very failure it diagnoses.

This module pins the fail-closed ``--dry-run`` predicate that ungates the diagnostic:

* ``--dry-run`` present in ``raw_args``            -> SAFE (diagnostic reachable)
* ``--dry-run`` absent (the mutating form)         -> UNSAFE (stays blocked)
* the predicate raising for any reason             -> UNSAFE (fail closed)
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from specify_cli.compat.safety import (
    SAFETY_REGISTRY,
    Safety,
    classify,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

#: The command path the failed migration recommends the operator runs.
_DIAGNOSTIC_PATH: tuple[str, ...] = ("migrate", "backfill-runtime-state")


def _inv(
    command_path: tuple[str, ...],
    raw_args: tuple[str, ...] = (),
) -> SimpleNamespace:
    """Build a minimal Invocation-like object for classify()."""
    return SimpleNamespace(command_path=command_path, raw_args=raw_args)


# ---------------------------------------------------------------------------
# Registration: the diagnostic path carries a predicate (not unconditional SAFE)
# ---------------------------------------------------------------------------


def test_diagnostic_path_is_registered_with_a_predicate() -> None:
    """The subcommand path is registered, and with a callable predicate.

    A bare ``None`` registration would make the *mutating* form SAFE too, which
    would defeat the fail-closed guard — so the value must be callable.
    """
    assert _DIAGNOSTIC_PATH in SAFETY_REGISTRY, (
        f"{_DIAGNOSTIC_PATH!r} must be registered so classify() does not fail "
        "closed on the recommended diagnostic."
    )
    predicate = SAFETY_REGISTRY[_DIAGNOSTIC_PATH]
    assert callable(predicate), (
        "The diagnostic must be gated by a --dry-run predicate, not registered "
        "as unconditionally SAFE (that would open the mutating migration path)."
    )


# ---------------------------------------------------------------------------
# SAFE iff --dry-run present
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_args",
    [
        ("--dry-run",),
        ("--mission", "some-slug", "--dry-run"),
        ("--dry-run", "--mission", "some-slug"),
    ],
)
def test_dry_run_form_is_safe(raw_args: tuple[str, ...]) -> None:
    """With ``--dry-run`` present the diagnostic classifies SAFE (reachable)."""
    result = classify(_inv(_DIAGNOSTIC_PATH, raw_args))
    assert result == Safety.SAFE, (
        f"Expected SAFE for raw_args={raw_args!r} (diagnostic must be reachable "
        "on a blocked project), got {result!r}."
    )


# ---------------------------------------------------------------------------
# UNSAFE when --dry-run absent (the mutating form stays blocked)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_args",
    [
        (),
        ("--mission", "some-slug"),
        ("--force",),
    ],
)
def test_mutating_form_is_unsafe(raw_args: tuple[str, ...]) -> None:
    """Without ``--dry-run`` the mutating migration form remains UNSAFE."""
    result = classify(_inv(_DIAGNOSTIC_PATH, raw_args))
    assert result == Safety.UNSAFE, (
        f"Expected UNSAFE for raw_args={raw_args!r} (mutating form must stay "
        "blocked under schema mismatch), got {result!r}."
    )


# ---------------------------------------------------------------------------
# Fail closed: any predicate exception -> UNSAFE
# ---------------------------------------------------------------------------


def test_predicate_failure_is_unsafe() -> None:
    """A malformed invocation (raw_args missing) must classify UNSAFE, not crash.

    ``classify()`` swallows predicate exceptions and returns UNSAFE; the predicate
    inspecting a missing ``raw_args`` attribute is the realistic fail-closed path.
    """
    broken = SimpleNamespace(command_path=_DIAGNOSTIC_PATH)  # no raw_args attribute
    result = classify(broken)  # type: ignore[arg-type]
    assert result == Safety.UNSAFE, (
        "A predicate that raises while inspecting the invocation must fall back "
        "to UNSAFE (fail closed)."
    )
