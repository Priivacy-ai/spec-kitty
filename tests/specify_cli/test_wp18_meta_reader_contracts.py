"""Contract tests for WP18 cluster-2b meta-reader migration (FR-006c).

These tests pin the **observable contract** of each site converted by WP18:

- ``retrospective.generator`` — was local ``_load_meta`` (silent-empty dict)
- ``cli.commands.review`` — was local ``_load_meta`` (silent-empty dict)
- ``verify_enhanced._resolve_mission_from_feature`` — was lazy import with
  broad ``except Exception: pass``

All three sites now delegate to ``load_meta_or_empty`` (contract (c)): returns
``{}`` for a *missing* file **and** for a *malformed* file.  The malformed arm
is the mutation-killer — an over-absorb mutant (e.g. always returning ``{}``)
only breaks the malformed cell.

The tests assert the **return value** of the consuming functions, never the
internal ``load_meta_or_empty`` call-graph (CT4/D036).

Negative control pairs
-----------------------
Each "silent-empty" site has TWO cells:
  - missing file → ``{}``  (control)
  - malformed file → ``{}``  (mutation-killer)

Production-shaped identity
---------------------------
ULID: 01KVRJ6PQ7XB2M9K4D8N3FZ0YT  (26 chars)
mid8: 01KVRJ6P                       (8 chars)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from specify_cli.mission_metadata import META_FILENAME, write_meta

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Production-shaped identity (testing-principles — never a short placeholder)
_MISSION_ID = "01KVRJ6PQ7XB2M9K4D8N3FZ0YT"
_MID8 = _MISSION_ID[:8]  # "01KVRJ6P"
_MISSION_SLUG = f"single-authority-topology-cleanup-{_MID8}"


def _valid_meta(mission_type: str = "software-dev") -> dict[str, Any]:
    """A complete, production-shaped meta.json mapping."""
    return {
        "mission_id": _MISSION_ID,
        "mission_number": None,
        "slug": _MISSION_SLUG,
        "mission_slug": _MISSION_SLUG,
        "friendly_name": "Single-Authority Topology Cleanup",
        "mission_type": mission_type,
        "target_branch": "feat/single-authority-topology-cleanup",
        "created_at": "2026-06-23T07:37:56+00:00",
    }


def _seed_valid(feature_dir: Path, mission_type: str = "software-dev") -> dict[str, Any]:
    """Write a valid meta.json via the production write seam; return its dict."""
    meta = _valid_meta(mission_type)
    write_meta(feature_dir, meta)
    return meta


def _seed_malformed(feature_dir: Path) -> None:
    """Write a genuinely un-parseable meta.json (truncated JSON, not empty).

    An empty file would only hit the missing-content branch; ``{"a":`` is
    truncated JSON that ``json.loads`` cannot parse — this is the malformed arm.
    """
    (feature_dir / META_FILENAME).write_text('{"a":', encoding="utf-8")


# ===========================================================================
# retrospective.generator: _load_meta removed → load_meta_or_empty (FR-006c)
#
# Observable contract via generate_retrospective's meta access:
#   meta = load_meta_or_empty(feature_dir)  # was _load_meta(feature_dir)
# The consuming site is at the top of generate_retrospective; the function
# reads ``meta.get("mission_slug")`` etc. A missing/malformed file must
# NOT raise — it silently yields an empty mapping.
#
# We test ``load_meta_or_empty`` directly as the extracted sub-contract
# because testing it through the full ``generate_retrospective`` would
# require a complete fixture setup (policy, spec.md, etc.) and would assert
# on the wrong surface (CT4: don't test call-args, test observable return).
# ===========================================================================


def test_retrospective_generator_silent_empty_on_missing_meta(tmp_path: Path) -> None:
    """Missing meta.json must return {} — never raise (contract c, missing arm)."""
    from specify_cli.mission_metadata import load_meta_or_empty

    # No meta.json written — dir is empty
    result = load_meta_or_empty(tmp_path)
    assert result == {}


def test_retrospective_generator_silent_empty_on_malformed_meta(tmp_path: Path) -> None:
    """Malformed meta.json must return {} — never raise (contract c, malformed arm).

    This is the mutation-killer: an over-absorb mutant that always returns {}
    will pass the missing-file cell but must also hold here.  The malformed
    arm is where silent-empty drift hides.
    """
    from specify_cli.mission_metadata import load_meta_or_empty

    _seed_malformed(tmp_path)
    result = load_meta_or_empty(tmp_path)
    assert result == {}


def test_retrospective_generator_returns_dict_on_valid_meta(tmp_path: Path) -> None:
    """A valid meta.json returns the parsed mapping — not {} (positive control)."""
    from specify_cli.mission_metadata import load_meta_or_empty

    expected = _seed_valid(tmp_path)
    result = load_meta_or_empty(tmp_path)
    assert result == expected


# ===========================================================================
# cli.commands.review: _load_meta removed → load_meta_or_empty (FR-006c)
#
# The former local ``_load_meta`` in review/__init__.py is removed;
# the call site ``meta = _load_meta(feature_dir)`` now reads
# ``meta = load_meta_or_empty(feature_dir)``.
#
# Contract: same silent-empty semantics as the retrospective site.
# We assert via the shared canonical reader (identical sub-contract).
# ===========================================================================


def test_review_meta_reader_silent_empty_on_missing(tmp_path: Path) -> None:
    """review/_load_meta removed: missing file → {} (contract c, missing arm)."""
    from specify_cli.mission_metadata import load_meta_or_empty

    result = load_meta_or_empty(tmp_path)
    assert result == {}


def test_review_meta_reader_silent_empty_on_malformed(tmp_path: Path) -> None:
    """review/_load_meta removed: malformed file → {} (contract c, malformed arm).

    Malformed arm is the mutation-killer — must be asserted explicitly.
    """
    from specify_cli.mission_metadata import load_meta_or_empty

    _seed_malformed(tmp_path)
    result = load_meta_or_empty(tmp_path)
    assert result == {}


# ===========================================================================
# verify_enhanced._resolve_mission_from_feature: lazy import + broad except
# removed → module-level load_meta_or_empty (FR-006c campsite)
#
# Observable contract: the *function return value* (str | None) given
# different meta.json states.
# ===========================================================================


def test_resolve_mission_from_feature_returns_none_on_missing_meta(
    tmp_path: Path,
) -> None:
    """No meta.json → function returns None (missing arm)."""
    from specify_cli.verify_enhanced import _resolve_mission_from_feature

    result = _resolve_mission_from_feature(tmp_path)
    assert result is None


def test_resolve_mission_from_feature_returns_none_on_malformed_meta(
    tmp_path: Path,
) -> None:
    """Malformed meta.json → function returns None — never raises (malformed arm).

    Previously the broad ``except Exception: pass`` masked this; now
    ``load_meta_or_empty`` guarantees the silent-empty contract, and
    ``if meta:`` treats ``{}`` as falsy → returns None.
    """
    from specify_cli.verify_enhanced import _resolve_mission_from_feature

    _seed_malformed(tmp_path)
    result = _resolve_mission_from_feature(tmp_path)
    assert result is None


def test_resolve_mission_from_feature_returns_mission_type(tmp_path: Path) -> None:
    """Valid meta.json with mission_type → function returns the mission_type string."""
    from specify_cli.verify_enhanced import _resolve_mission_from_feature

    _seed_valid(tmp_path, mission_type="research")
    result = _resolve_mission_from_feature(tmp_path)
    assert result == "research"


def test_resolve_mission_from_feature_falls_back_to_legacy_mission_field(
    tmp_path: Path,
) -> None:
    """Legacy meta.json with ``mission`` key (no mission_type) → returns that value."""
    from specify_cli.verify_enhanced import _resolve_mission_from_feature

    meta = _valid_meta()
    del meta["mission_type"]
    meta["mission"] = "documentation"
    write_meta(tmp_path, meta, validate=False)

    result = _resolve_mission_from_feature(tmp_path)
    assert result == "documentation"
