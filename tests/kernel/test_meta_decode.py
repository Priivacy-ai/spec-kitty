"""``tests/kernel/`` coverage for :mod:`kernel.meta_decode` — the L1 malformed
authority (``kernel-tests`` CI job coverage floor, 90%, #3259 landing pass).

:mod:`tests.architectural.test_meta_decode_l1` already pins the *behavioral*
contract for ``decode_meta`` in depth. This file duplicates a focused slice of
that coverage **specifically under `tests/kernel/`**: the ``kernel-tests`` CI
job (``.github/workflows/ci-quality.yml``) measures ``--cov=src/kernel``
against ``tests/kernel/`` only, so a module fully exercised from
``tests/architectural/`` still reads as uncovered for that job's 90% floor.
Keep this file's cases in sync with the architectural suite's intent, not
byte-identical — the architectural file remains the deeper behavioral pin;
this one exists to satisfy the kernel job's own coverage measurement.
"""

from __future__ import annotations

import pytest

from kernel.meta_decode import MetaDecodeError, decode_meta

pytestmark = pytest.mark.fast

_BAD_JSON = "{not valid json"
_NON_OBJECT = "[1, 2, 3]"
_BAD_BYTES = b"\xff\xfe\x00"


def test_meta_decode_error_is_value_error() -> None:
    """Every existing ``except ValueError`` boundary must keep catching L1."""
    assert issubclass(MetaDecodeError, ValueError)


@pytest.mark.parametrize(
    "raw",
    ['{"a": 1, "b": "two"}', b'{"a": 1, "b": "two"}'],
    ids=["str", "bytes"],
)
def test_valid_dict_returns_mapping(raw: str | bytes) -> None:
    """Happy path: a valid JSON object decodes to the equivalent mapping,
    for both ``str`` and ``bytes`` input (the explicit bytes-decode arm)."""
    assert decode_meta(raw) == {"a": 1, "b": "two"}


def test_raise_is_the_default_policy() -> None:
    with pytest.raises(MetaDecodeError):
        decode_meta(_BAD_JSON)


def test_raise_policy_bad_json_raises_meta_decode_error() -> None:
    with pytest.raises(MetaDecodeError):
        decode_meta(_BAD_JSON, on_malformed="raise")


def test_raise_policy_non_object_names_the_type() -> None:
    """The non-object raise arm surfaces the offending type for diagnostics."""
    with pytest.raises(MetaDecodeError, match="Expected JSON object, got list"):
        decode_meta(_NON_OBJECT, on_malformed="raise")


def test_raise_policy_bad_bytes_raises_meta_decode_error() -> None:
    """Invalid UTF-8 bytes hit the explicit ``raw.decode("utf-8")`` arm, not
    ``json.loads``'s own encoding auto-detection (module docstring, D2)."""
    with pytest.raises(MetaDecodeError):
        decode_meta(_BAD_BYTES, on_malformed="raise")


@pytest.mark.parametrize("raw", [_BAD_JSON, _NON_OBJECT, _BAD_BYTES], ids=["bad-json", "non-object", "bad-bytes"])
def test_empty_policy_absorbs_to_empty_dict(raw: str | bytes) -> None:
    """``on_malformed="empty"`` -- the ``_absorb`` ``{}`` arm -- for each
    malformed class (bad JSON syntax, non-object top level, bad UTF-8 bytes)."""
    assert decode_meta(raw, on_malformed="empty") == {}


@pytest.mark.parametrize("raw", [_BAD_JSON, _NON_OBJECT, _BAD_BYTES], ids=["bad-json", "non-object", "bad-bytes"])
def test_none_policy_absorbs_to_none(raw: str | bytes) -> None:
    """``on_malformed="none"`` -- the ``_absorb`` ``None`` arm -- for each
    malformed class."""
    assert decode_meta(raw, on_malformed="none") is None


@pytest.mark.parametrize("on_malformed", ["raise", "empty", "none"])
def test_valid_dict_unaffected_by_policy(on_malformed: str) -> None:
    """A valid object is returned verbatim regardless of the malformed policy
    -- the policy only governs the malformed arms."""
    assert decode_meta('{"k": true}', on_malformed=on_malformed) == {"k": True}  # type: ignore[arg-type]


def test_raise_bad_bytes_caught_by_value_error_boundary() -> None:
    """Bad bytes raise ``MetaDecodeError`` -- a plain ``except ValueError`` (as
    at L3 ``load_meta_fail_closed``) must catch it by inheritance."""
    caught: ValueError | None = None
    try:
        decode_meta(_BAD_BYTES, on_malformed="raise")
    except ValueError as exc:  # the L3 boundary shape, verbatim
        caught = exc
    assert isinstance(caught, MetaDecodeError)
