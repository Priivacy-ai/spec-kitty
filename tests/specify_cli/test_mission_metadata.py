"""Contract tests for the polymorphic ``load_meta`` reader (FR-006a, WP08).

These tests pin the *observable return value* of each of the three legacy error
contracts the single ``load_meta`` absorbs -- never the reader's internal call
graph (CT4/D036).  Each "absorbs / allows" assertion is paired with its negative
control ("still raises") so an over-allow mutant cannot survive.

The three contracts:
  (a) canonical     -- None-on-missing, raise-on-malformed (defaults).
  (b) strict        -- raise-on-missing, utf-8-sig BOM-tolerant decode.
  (c) silent-empty  -- ``{}`` on missing *and* malformed; never raises.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.mission_metadata import (
    META_FILENAME,
    load_meta,
    load_meta_or_empty,
    load_meta_strict,
    write_meta,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Production-shaped identity: a real 26-char ULID + its 8-char mid8 prefix
# (testing-principles -- never a short placeholder slug).
_MISSION_ID = "01KVRJ6PQ7XB2M9K4D8N3FZ0YT"
_MID8 = _MISSION_ID[:8]  # "01KVRJ6P"
_MISSION_SLUG = f"single-authority-topology-cleanup-{_MID8}"


def _valid_meta() -> dict[str, Any]:
    """A complete, production-shaped meta.json mapping."""
    return {
        "mission_id": _MISSION_ID,
        "mission_number": None,
        "slug": _MISSION_SLUG,
        "mission_slug": _MISSION_SLUG,
        "friendly_name": "Single-Authority Topology Cleanup",
        "mission_type": "software-dev",
        "target_branch": "feat/single-authority-topology-cleanup",
        "created_at": "2026-06-23T07:37:56+00:00",
    }


def _seed_valid(feature_dir: Path) -> dict[str, Any]:
    """Write a valid meta.json via the production write seam; return its dict."""
    meta = _valid_meta()
    write_meta(feature_dir, meta)
    return meta


def _seed_malformed(feature_dir: Path) -> Path:
    """Write a *genuinely un-parseable* meta.json (identity-input trap guard).

    An empty file would hit the *missing*-content arm and mask the malformed
    branch; ``{"a":`` is truncated JSON that ``json.loads`` cannot parse.
    """
    meta_path = feature_dir / META_FILENAME
    meta_path.write_text('{"a":', encoding="utf-8")
    return meta_path


# ===================================================================
# Happy path -- shared by every contract
# ===================================================================


def test_load_meta_reads_valid_object(tmp_path: Path) -> None:
    meta = _seed_valid(tmp_path)
    assert load_meta(tmp_path) == meta


# ===================================================================
# Contract (a): canonical -- None-on-missing, raise-on-malformed (defaults)
# ===================================================================


def test_contract_a_missing_returns_none(tmp_path: Path) -> None:
    # allow_missing default True, on_malformed default "raise"
    assert load_meta(tmp_path) is None


def test_contract_a_malformed_raises(tmp_path: Path) -> None:
    # Negative control for the missing arm: an existing-but-malformed file
    # must NOT be absorbed to None -- it raises.
    _seed_malformed(tmp_path)
    with pytest.raises(ValueError, match="Malformed JSON"):
        load_meta(tmp_path)


def test_contract_a_non_object_top_level_raises(tmp_path: Path) -> None:
    (tmp_path / META_FILENAME).write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected JSON object"):
        load_meta(tmp_path)


# ===================================================================
# Contract (b): strict -- raise-on-missing + utf-8-sig BOM tolerance
# ===================================================================


def test_contract_b_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_meta(tmp_path, allow_missing=False)


def test_contract_b_strict_adapter_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_meta_strict(tmp_path)


def test_contract_b_present_returns_dict(tmp_path: Path) -> None:
    # Negative control for the missing arm: a present file does NOT raise.
    meta = _seed_valid(tmp_path)
    assert load_meta_strict(tmp_path) == meta


def test_contract_b_bom_tolerant_decode(tmp_path: Path) -> None:
    """A UTF-8 BOM-prefixed meta.json decodes cleanly under the strict adapter.

    Writing with ``utf-8-sig`` prepends the BOM; a plain ``utf-8`` json.loads
    would choke on it, so a successful parse proves the BOM-tolerant decode is
    preserved.
    """
    meta = _valid_meta()

    (tmp_path / META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8-sig"
    )
    assert load_meta_strict(tmp_path) == meta


def test_contract_b_bom_intolerant_when_disabled(tmp_path: Path) -> None:
    """Negative control: with ``bom_tolerant=False`` the BOM is NOT swallowed.

    The strict adapter coerces malformed content to ``{}`` (legacy isinstance
    guard), so a BOM that breaks the plain utf-8 decode yields ``{}`` rather
    than the parsed object -- proving the tolerance is opt-in, not unconditional.
    """
    meta = _valid_meta()

    (tmp_path / META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8-sig"
    )
    assert load_meta_strict(tmp_path, bom_tolerant=False) == {}


# ===================================================================
# Contract (c): silent -- {} on missing AND malformed; never raises
# ===================================================================


def test_contract_c_missing_returns_empty(tmp_path: Path) -> None:
    assert load_meta(tmp_path, on_malformed="empty") == {}


def test_contract_c_malformed_returns_empty(tmp_path: Path) -> None:
    # Negative control vs contract (a): the SAME malformed input that raises
    # under "raise" is absorbed to {} under "empty".
    _seed_malformed(tmp_path)
    assert load_meta(tmp_path, on_malformed="empty") == {}


def test_contract_c_adapter_missing_and_malformed_return_empty(tmp_path: Path) -> None:
    assert load_meta_or_empty(tmp_path) == {}
    _seed_malformed(tmp_path)
    assert load_meta_or_empty(tmp_path) == {}


def test_contract_c_adapter_valid_returns_object(tmp_path: Path) -> None:
    # Negative control: a valid file is NOT flattened to {} by the silent adapter.
    meta = _seed_valid(tmp_path)
    assert load_meta_or_empty(tmp_path) == meta


def test_contract_c_non_object_returns_empty(tmp_path: Path) -> None:
    (tmp_path / META_FILENAME).write_text('"a bare string"', encoding="utf-8")
    assert load_meta(tmp_path, on_malformed="empty") == {}


# ===================================================================
# on_malformed="none" -- absorb to None (third malformed policy)
# ===================================================================


def test_on_malformed_none_missing_returns_none(tmp_path: Path) -> None:
    assert load_meta(tmp_path, on_malformed="none") is None


def test_on_malformed_none_malformed_returns_none(tmp_path: Path) -> None:
    # Negative control vs "raise": malformed is absorbed to None, not raised.
    _seed_malformed(tmp_path)
    assert load_meta(tmp_path, on_malformed="none") is None


# ===================================================================
# Cross-contract behavior-neutrality: a valid object reads identically
# regardless of which contract is selected.
# ===================================================================


def test_valid_object_identical_across_contracts(tmp_path: Path) -> None:
    meta = _seed_valid(tmp_path)
    assert load_meta(tmp_path) == meta
    assert load_meta(tmp_path, allow_missing=False) == meta
    assert load_meta(tmp_path, on_malformed="empty") == meta
    assert load_meta(tmp_path, on_malformed="none") == meta
    assert load_meta_strict(tmp_path) == meta
    assert load_meta_or_empty(tmp_path) == meta
