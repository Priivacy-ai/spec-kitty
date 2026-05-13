"""Regression tests for the silent-swallow finding (S1/S2) from the
post-merge mission review of ``review-merge-gate-hardening-3-2-x-01KRC57C``.

The chokepoint at ``src/charter/_io.py`` correctly raises ``CharterEncodingError``
(a subclass of ``KittyInternalConsistencyError``) when encoding detection
cannot resolve unambiguously. The audit surfaced that the two CALL SITES
inside the charter subsystem wrap the call in ``except Exception`` and return
empty results — defeating FR-018's fail-loud guarantee at the consumer
boundary.

These tests verify that the diagnostic propagates through the call sites:

* ``_load_yaml_asset`` (compiler.py) — used to compile charter assets
* ``read_interview_answers`` (interview.py) — used to load interview state

The tests target *behavior*, not file line numbers. A future refactor that
moves the function or changes its name should still pass these tests as
long as the diagnostic propagation contract is honored.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter._io import CharterEncodingError
from kernel.errors import KittyInternalConsistencyError


def _write_ambiguous_yaml(path: Path) -> None:
    """Write bytes that the chokepoint cannot resolve confidently — the
    detector returns a ``best`` candidate whose ``chaos`` keeps the
    confidence below the 0.85 threshold, triggering CHARTER_ENCODING_AMBIGUOUS.

    The full high-bit range (0x80..0xFF) appended to a YAML-ish prefix gives
    charset-normalizer no coherent text in any candidate encoding, so the
    fail-loud branch fires under ``unsafe=False``.
    """
    high_bytes = bytes(range(0x80, 0x100))
    data = b"name: x\n" + high_bytes + b"\nvalue: 1\n"
    path.write_bytes(data)


def test_compiler_load_yaml_asset_propagates_encoding_error(tmp_path: Path) -> None:
    """``_load_yaml_asset`` must NOT swallow ``CharterEncodingError``.

    This is the S2 finding: ``compiler.py`` wraps the chokepoint call in
    ``except Exception`` and returns an empty dict, hiding the diagnostic.
    """
    from charter.compiler import _load_yaml_asset

    bad = tmp_path / "bad.yaml"
    _write_ambiguous_yaml(bad)

    # Must propagate as KittyInternalConsistencyError (the canonical base);
    # CharterEncodingError IS-A KittyInternalConsistencyError, so this is
    # the tightest contract a future refactor must continue to satisfy.
    with pytest.raises(KittyInternalConsistencyError) as excinfo:
        _load_yaml_asset(bad)

    # Confirm we got the specific subclass and the diagnostic body.
    assert isinstance(excinfo.value, CharterEncodingError)
    assert excinfo.value.code == "CHARTER_ENCODING_AMBIGUOUS"
    assert excinfo.value.body  # non-empty operator guidance


def test_interview_read_propagates_encoding_error(tmp_path: Path) -> None:
    """``read_interview_answers`` must NOT swallow ``CharterEncodingError``.

    This is the S1 finding: ``interview.py`` wraps the chokepoint call in
    ``except Exception`` and returns ``None``, making "ambiguous encoding"
    look identical to "file missing".
    """
    from charter.interview import read_interview_answers

    bad = tmp_path / "bad-interview.yaml"
    _write_ambiguous_yaml(bad)

    with pytest.raises(KittyInternalConsistencyError) as excinfo:
        read_interview_answers(bad)

    assert isinstance(excinfo.value, CharterEncodingError)
    assert excinfo.value.code == "CHARTER_ENCODING_AMBIGUOUS"


def test_compiler_load_yaml_asset_still_handles_unrelated_yaml_errors(
    tmp_path: Path,
) -> None:
    """Tighter exception handling must still tolerate non-encoding parse
    issues. The pre-existing behavior is to return an empty dict when YAML
    parsing fails on an otherwise readable file; that resilience stays.
    """
    from charter.compiler import _load_yaml_asset

    # Valid UTF-8 but malformed YAML — encoding succeeds, parse fails.
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("name: [unclosed\n", encoding="utf-8")

    # Should NOT raise — pre-existing behavior is empty dict.
    result = _load_yaml_asset(malformed)
    assert isinstance(result, dict)
    # The function annotates _source_path even when content is empty.
    assert result.get("_source_path") == str(malformed)


def test_interview_read_returns_none_for_missing_file(tmp_path: Path) -> None:
    """Missing files remain a None-return — only encoding/consistency errors
    propagate."""
    from charter.interview import read_interview_answers

    missing = tmp_path / "does-not-exist.yaml"
    assert read_interview_answers(missing) is None


def test_interview_read_returns_none_for_malformed_utf8_yaml(tmp_path: Path) -> None:
    """Malformed but decodable YAML preserves the legacy None-return contract."""
    from charter.interview import read_interview_answers

    malformed = tmp_path / "malformed-interview.yaml"
    malformed.write_text("responses: [unclosed\n", encoding="utf-8")

    assert read_interview_answers(malformed) is None


def test_unsafe_bypass_propagates_through_compiler(tmp_path: Path) -> None:
    """When the operator opts into ``--unsafe`` semantics, the chokepoint
    does NOT raise — the compiler call site must support this propagation.

    This is the D3 finding: compiler.py:594 calls ``load_charter_file(path)``
    with no ``unsafe`` parameter, so even when an operator passes ``--unsafe``
    through the CLI, the bypass is silently ignored at this call site.
    """
    from charter.compiler import _load_yaml_asset

    bad = tmp_path / "bad.yaml"
    _write_ambiguous_yaml(bad)

    # Pre-fix behavior: _load_yaml_asset accepts no `unsafe` kwarg →
    # passing one is a TypeError, and there is no way for the operator to
    # opt past CHARTER_ENCODING_AMBIGUOUS at this call site.
    # Post-fix behavior: _load_yaml_asset accepts `unsafe` and propagates it.
    result = _load_yaml_asset(bad, unsafe=True)
    assert isinstance(result, dict)
    # The bypass should have produced a non-empty parse (cp1252 decoded).
    # We can't assert exact content because the bytes happen to be invalid
    # YAML once decoded, but the empty-dict-from-encoding-failure path
    # is no longer hit.
    # What we DO assert: no KittyInternalConsistencyError was raised
    # (the pytest.raises wrapper above would have caught it).
