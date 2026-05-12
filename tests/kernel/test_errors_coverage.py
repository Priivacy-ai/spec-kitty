"""Coverage tests for ``src/kernel/errors.py`` — the canonical
``KittyInternalConsistencyError`` base introduced during the post-merge
remediation of mission ``review-merge-gate-hardening-3-2-x-01KRC57C``.

The error class is tiny (≈10 lines) but it is the foundation for every
subsystem-specific exception that wants uniform CLI/TUI/UI rendering. The
type contract (constructor signature, attribute exposure, isinstance
relationships) is what consumers depend on; these tests pin it.
"""

from __future__ import annotations

import pytest

from kernel.errors import KittyInternalConsistencyError


def test_is_exception_subclass() -> None:
    """The base must remain catchable as a plain Exception so older code
    that catches ``Exception`` (correctly) still surfaces it as a bug if
    it didn't intend to swallow internal-consistency errors."""
    assert issubclass(KittyInternalConsistencyError, Exception)


def test_carries_code_and_body() -> None:
    """Constructor accepts ``code`` (required) and ``body`` (defaulted)
    and exposes both as attributes."""
    err = KittyInternalConsistencyError("MY_CODE", "structured remediation text")
    assert err.code == "MY_CODE"
    assert err.body == "structured remediation text"


def test_body_defaults_to_empty_string() -> None:
    """``body`` is optional — when omitted, defaults to ``""`` (not
    ``None``), so consumers can render it without a None-check."""
    err = KittyInternalConsistencyError("BARE_CODE")
    assert err.code == "BARE_CODE"
    assert err.body == ""


def test_str_is_the_code() -> None:
    """str(exc) returns the code (passed up to Exception.__init__), so
    short-form logging surfaces the JSON-stable diagnostic without the
    full body."""
    err = KittyInternalConsistencyError("CODE_ONLY", "long detail")
    assert str(err) == "CODE_ONLY"


def test_can_be_raised_and_caught() -> None:
    """End-to-end raise/catch sanity check."""
    with pytest.raises(KittyInternalConsistencyError) as excinfo:
        raise KittyInternalConsistencyError("ABORT_NOW", body="why and how")
    assert excinfo.value.code == "ABORT_NOW"
    assert "why and how" in excinfo.value.body


def test_caught_as_base_exception() -> None:
    """A subsystem-specific subclass must be catchable as the base — this
    is the central UX contract that lets CLI/TUI/UI render any
    KittyInternalConsistencyError uniformly without knowing the subclass."""

    class _MyDomainError(KittyInternalConsistencyError):
        pass

    with pytest.raises(KittyInternalConsistencyError):
        raise _MyDomainError("SUBCLASSED_CODE", "subclass body")
