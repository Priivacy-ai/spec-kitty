"""Type-coercion contract for ``meta.json`` ``mission_number`` (FR-044 / T008).

Proves the WP02 ``_coerce_mission_number`` read-boundary coercion matrix:

========================  ========================  ======================
Raw value in meta.json    Coerced to                Rationale
========================  ========================  ======================
``42`` (int)              ``42``                    Canonical form
``"42"`` (str)            ``42``                    Legacy str, strip zeros
``"042"`` (str)           ``42``                    Leading-zero legacy
``"007"`` (str)           ``7``                     Leading-zero legacy
``None``                  ``None``                  Pre-merge (null)
``""`` (empty str)        ``None``                  Empty = missing
``-1`` (int)              ``-1``                    Passes through raw
``"pending"``             ``ValueError``            Sentinel rejected
``"TBD"``                 ``ValueError``            Sentinel rejected
``"unassigned"``          ``ValueError``            Sentinel rejected
``"abc"``                 ``ValueError``            Unparseable string
``True`` / ``False``      ``TypeError``             Bool is not an int here
``1.5`` (float)           ``TypeError``             Float is not permitted
========================  ========================  ======================

Both the low-level helper (``_coerce_mission_number``) and the full loader
(``resolve_mission_identity`` reading an on-disk ``meta.json``) are exercised
so the contract is verified at both layers of the read path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.mission_metadata import (
    _coerce_mission_number,
    resolve_mission_identity,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Direct helper — _coerce_mission_number
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (42, 42),
        ("42", 42),
        ("042", 42),
        ("007", 7),
        ("0", 0),
        ("00", 0),
        (0, 0),
        (None, None),
        ("", None),
        ("   ", None),  # whitespace-only counts as missing
        (-1, -1),  # passes through — downstream may reject
        (9999, 9999),
    ],
    ids=[
        "int-42",
        "str-42",
        "str-042-stripped",
        "str-007-stripped",
        "str-zero",
        "str-double-zero",
        "int-zero",
        "none",
        "empty-str",
        "whitespace-str",
        "negative-int-passthrough",
        "large-int",
    ],
)
def test_coerce_mission_number_happy_path(raw: object, expected: int | None) -> None:
    """Valid forms round-trip to the expected ``int | None``."""
    assert _coerce_mission_number(raw) == expected


@pytest.mark.parametrize(
    "sentinel",
    ["pending", "unassigned", "TBD", " pending ", " TBD "],
    ids=["pending", "unassigned", "tbd", "padded-pending", "padded-tbd"],
)
def test_coerce_mission_number_rejects_sentinels(sentinel: str) -> None:
    """Sentinel strings must raise ``ValueError`` with actionable guidance."""
    with pytest.raises(ValueError) as exc_info:
        _coerce_mission_number(sentinel)
    # The error message must include backfill guidance so the operator knows
    # how to unstick the migration.
    assert "backfill-identity" in str(exc_info.value)


@pytest.mark.parametrize("bad", ["abc", "42x", "1.5", "-", "--"])
def test_coerce_mission_number_rejects_unparseable_strings(bad: str) -> None:
    """Strings that do not parse as an integer raise ``ValueError``."""
    with pytest.raises(ValueError):
        _coerce_mission_number(bad)


@pytest.mark.parametrize("bad", [True, False])
def test_coerce_mission_number_rejects_bool(bad: bool) -> None:
    """``bool`` is a subclass of ``int`` but must be rejected — it is always a bug."""
    with pytest.raises(TypeError):
        _coerce_mission_number(bad)


@pytest.mark.parametrize("bad", [1.5, 2.0, [1], {"n": 1}])
def test_coerce_mission_number_rejects_non_int_types(bad: object) -> None:
    """Non-int / non-str / non-None types raise ``TypeError``."""
    with pytest.raises(TypeError):
        _coerce_mission_number(bad)


# ---------------------------------------------------------------------------
# Full read boundary — resolve_mission_identity over an on-disk meta.json
# ---------------------------------------------------------------------------


def _write_meta(feature_dir: Path, mission_number: object, mission_id: str | None = None) -> Path:
    """Write a minimal ``meta.json`` with the given raw ``mission_number`` value.

    ``None``-valued keys are still serialised (so ``resolve_mission_identity``
    sees them as present-with-null, matching real pre-merge meta.json files).
    """
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "slug": feature_dir.name,
        "mission_slug": feature_dir.name,
        "friendly_name": "Coercion Test",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-04-11T12:00:00+00:00",
        "mission_number": mission_number,
    }
    if mission_id is not None:
        meta["mission_id"] = mission_id
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return feature_dir


@pytest.mark.parametrize(
    ("raw_value", "expected_number"),
    [
        (42, 42),
        ("42", 42),
        ("042", 42),
        ("007", 7),
        (None, None),
        ("", None),
    ],
)
def test_resolve_identity_coerces_mission_number(
    tmp_path: Path,
    raw_value: object,
    expected_number: int | None,
) -> None:
    """``resolve_mission_identity`` reads and coerces via the same helper."""
    feature_dir = _write_meta(tmp_path / "080-test", raw_value)
    identity = resolve_mission_identity(feature_dir)
    assert identity.mission_number == expected_number


def test_resolve_identity_raises_on_sentinel_in_meta(tmp_path: Path) -> None:
    """Reading a meta.json with ``"pending"`` surfaces the ValueError to the caller."""
    feature_dir = _write_meta(tmp_path / "080-test", "pending")
    with pytest.raises(ValueError, match="backfill-identity"):
        resolve_mission_identity(feature_dir)


def test_resolve_identity_negative_int_passes_through(tmp_path: Path) -> None:
    """Negative integers round-trip at the read boundary (downstream rejects them)."""
    feature_dir = _write_meta(tmp_path / "080-test", -1)
    identity = resolve_mission_identity(feature_dir)
    assert identity.mission_number == -1


def test_resolve_identity_preserves_mission_id_when_present(tmp_path: Path) -> None:
    """The coercion must not destroy an accompanying ``mission_id``."""
    ulid = "01KNRQK0R1ZDS8Z57M1TRXF0XR"
    feature_dir = _write_meta(tmp_path / "080-test", "042", mission_id=ulid)
    identity = resolve_mission_identity(feature_dir)
    assert identity.mission_number == 42
    assert identity.mission_id == ulid
