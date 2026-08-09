"""Self-test for the shared non-vacuity examined-floor guard (#3273).

``related_validator.validate_related`` and
``relative_link_fixer.check_dead_body_links`` both route their "examined
count fell below the floor" ``RuntimeError`` through
``scripts.docs._guards.assert_examined_floor``. These tests exercise the
helper directly so its branches — below-floor raise, at/above-floor no-raise,
and the ``gate``/``noun``/``fr_id``/``extra`` parameterization surfacing in
the message — are covered independently of either caller.
"""

from __future__ import annotations

import pytest

from scripts.docs._guards import assert_examined_floor


def test_below_floor_raises_with_expected_substrings() -> None:
    """A count under the minimum raises, and the message carries the shape
    both callers' tests assert on: the count, the minimum, the FR id, and the
    "non-vacuity guard" / "expected at least" phrasing."""
    with pytest.raises(RuntimeError) as excinfo:
        assert_examined_floor(
            0, 1, gate="my_gate", noun="widget(s) examined", fr_id="FR-999"
        )

    message = str(excinfo.value)
    assert "my_gate" in message
    assert "0 widget(s) examined" in message
    assert "expected at least 1" in message
    assert "FR-999 non-vacuity guard" in message


def test_at_floor_does_not_raise() -> None:
    """A count exactly at the minimum clears the floor."""
    assert_examined_floor(1, 1, gate="my_gate", noun="thing(s)", fr_id="FR-999")


def test_above_floor_does_not_raise() -> None:
    """A count above the minimum clears the floor."""
    assert_examined_floor(5, 1, gate="my_gate", noun="thing(s)", fr_id="FR-999")


def test_extra_detail_appears_in_message_when_provided() -> None:
    """The optional ``extra`` caveat is appended inside the parenthetical."""
    with pytest.raises(RuntimeError, match="possible misconfiguration"):
        assert_examined_floor(
            0,
            1,
            gate="my_gate",
            noun="thing(s)",
            fr_id="FR-999",
            extra="possible misconfiguration",
        )


def test_no_extra_detail_omits_trailing_comma() -> None:
    """Without ``extra`` the parenthetical has no dangling ``", "`` suffix."""
    with pytest.raises(RuntimeError) as excinfo:
        assert_examined_floor(0, 1, gate="my_gate", noun="thing(s)", fr_id="FR-999")

    message = str(excinfo.value)
    assert "non-vacuity guard)" in message
    assert "non-vacuity guard," not in message


def test_gate_noun_fr_id_are_parameterized_per_caller() -> None:
    """Different callers get distinct, correctly-substituted messages."""
    with pytest.raises(RuntimeError) as excinfo:
        assert_examined_floor(
            2,
            3,
            gate="check_dead_body_links",
            noun="doc file(s) found under docs/",
            fr_id="FR-004",
        )

    message = str(excinfo.value)
    assert message.startswith("check_dead_body_links:")
    assert "doc file(s) found under docs/" in message
    assert "FR-004 non-vacuity guard" in message
