"""Consumed behavior of the operational-context boundary."""

from __future__ import annotations

import pytest

from charter.activation.invocation_context import (
    ContextPreconditionError,
    build_operational_context,
)


pytestmark = pytest.mark.unit


def test_explicit_operational_context_round_trip() -> None:
    """Caller-owned context values survive assembly and guard access."""
    context = build_operational_context(
        active_model="opus",
        active_profile="python-pedro",
        active_role="implementer",
        current_activity="implement",
        tech_stack=frozenset({"python", "pytest"}),
    )

    assert context.active_model == "opus"
    assert context.require_active_profile() == "python-pedro"
    assert context.require_active_role() == "implementer"
    assert context.current_activity == "implement"
    assert context.tech_stack == frozenset({"python", "pytest"})


def test_missing_required_context_fails_with_actionable_identity() -> None:
    """A missing routing identity fails closed at the consumed guard."""
    with pytest.raises(ContextPreconditionError) as exc_info:
        build_operational_context().require_active_profile()

    error = exc_info.value
    assert error.field == "active_profile"
    assert error.hint
    assert "build_operational_context" in str(error)
