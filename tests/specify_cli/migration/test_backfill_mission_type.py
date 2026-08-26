"""Unit tests for backfill_mission_type (rc3 M0 — mission_type backfill).

Covers WP01 T004 (AC-1, AC-2a, AC-2b, AC-3, AC-4, AC-6, AC-10, R-4) plus the
squad #3 anti-laziness additions (B1/FR-005 error-isolation, M1/R-1 dossier
rehash gating, M2 non-canonical byte-identity fixture, m1 unactivated-built-in
regression).

The write-vs-skip decision is keyed on
``MissionTypeProfileRepository.for_project(repo_root).get(key) is not None``
(the M3 §B tolerance authority, activation-independent) — NOT on charter
activation. Real built-in mission types (``software-dev``, ``research``)
resolve on a bare temp repo with no ``.kittify/`` provisioning at all, which
is exactly the point of the profile-resolution predicate (spec AC-5/R-4).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from charter.mission_type_profile_repository import MissionTypeProfileRepository
from specify_cli.mission import MissionNotFoundError
from specify_cli.migration.backfill_mission_type import (
    LEGACY_MISSION_KEY,
    MISSION_TYPE_KEY,
    backfill_mission_mission_type,
    backfill_mission_type_repo,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_meta(repo_root: Path, slug: str, meta: dict[str, object]) -> Path:
    """Write ``meta`` (insertion-order keys, NOT sorted) under kitty-specs/<slug>."""
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return feature_dir


def _read_meta(feature_dir: Path) -> dict[str, object]:
    result: dict[str, object] = json.loads(
        (feature_dir / "meta.json").read_text(encoding="utf-8")
    )
    return result


# ---------------------------------------------------------------------------
# AC-1 — resolving candidates all written
# ---------------------------------------------------------------------------


def test_resolving_candidates_all_written(tmp_path: Path) -> None:
    """A repo of legacy candidates whose values resolve a profile all get written."""
    _write_meta(tmp_path, "001-alpha", {"mission": "software-dev"})
    _write_meta(tmp_path, "002-beta", {"mission": "research"})

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 2
    by_slug = {r.slug: r for r in results}
    assert by_slug["001-alpha"].action == "wrote"
    assert by_slug["001-alpha"].mission_type == "software-dev"
    assert by_slug["002-beta"].action == "wrote"
    assert by_slug["002-beta"].mission_type == "research"

    for slug in ("001-alpha", "002-beta"):
        meta = _read_meta(tmp_path / "kitty-specs" / slug)
        assert MISSION_TYPE_KEY in meta


# ---------------------------------------------------------------------------
# AC-2a — already-typed mission untouched, byte-identical
# ---------------------------------------------------------------------------


def test_already_typed_mission_untouched_byte_identical(tmp_path: Path) -> None:
    """A mission with ``mission_type`` already present is skipped and unchanged.

    The fixture is authored in NON-canonical form (unsorted keys, no trailing
    newline discipline matching the canonical writer) so an accidental full
    rewrite via the canonical sorted-key writer would flip the byte-compare —
    a canonical-form fixture would make this assertion vacuous (squad #3 M2).
    """
    feature_dir = tmp_path / "kitty-specs" / "003-gamma"
    feature_dir.mkdir(parents=True)
    meta_path = feature_dir / "meta.json"
    # Deliberately unsorted keys ("zeta" < nothing alphabetically before
    # "mission_type" in this insertion order) and compact-ish formatting —
    # NOT what json.dumps(..., sort_keys=True, indent=2) would produce.
    raw_content = (
        '{\n  "zeta_field": "z",\n  "mission_type": "software-dev",\n'
        '  "mission": "software-dev",\n  "alpha_field": "a"\n}\n'
    )
    meta_path.write_text(raw_content, encoding="utf-8")
    before = meta_path.read_bytes()

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 1
    assert results[0].action == "skip"
    assert results[0].reason == "mission_type already present"
    assert meta_path.read_bytes() == before, "already-typed mission must not be rewritten"


# ---------------------------------------------------------------------------
# AC-2b — written mission gains key, fields preserved (JSON-semantic equality)
# ---------------------------------------------------------------------------


def test_written_mission_gains_key_fields_preserved(tmp_path: Path) -> None:
    feature_dir = _write_meta(
        tmp_path,
        "004-delta",
        {
            "mission": "software-dev",
            "mission_slug": "004-delta",
            "friendly_name": "Delta",
            "target_branch": "main",
        },
    )

    result = backfill_mission_mission_type(
        feature_dir,
        repo=_profile_repo(tmp_path),
    )

    assert result.action == "wrote"
    assert result.mission_type == "software-dev"

    meta = _read_meta(feature_dir)
    assert meta["mission_type"] == "software-dev"
    assert meta["mission"] == "software-dev"
    assert meta["mission_slug"] == "004-delta"
    assert meta["friendly_name"] == "Delta"
    assert meta["target_branch"] == "main"

    # Canonical sorted-key serialization (matches backfill_topology's idiom).
    raw = (feature_dir / "meta.json").read_text(encoding="utf-8")
    expected = json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    assert raw == expected


# ---------------------------------------------------------------------------
# AC-3 — idempotent second run
# ---------------------------------------------------------------------------


def test_idempotent_second_run_wrote_zero(tmp_path: Path) -> None:
    _write_meta(tmp_path, "005-epsilon", {"mission": "software-dev"})

    first = backfill_mission_type_repo(tmp_path)
    second = backfill_mission_type_repo(tmp_path)

    assert first[0].action == "wrote"
    assert second[0].action == "skip"
    assert second[0].reason == "mission_type already present"
    assert sum(1 for r in second if r.action == "wrote") == 0


# ---------------------------------------------------------------------------
# AC-4 — non-resolving candidate needs manual resolution, never written
# ---------------------------------------------------------------------------


def test_nonresolving_value_needs_manual_not_written(tmp_path: Path) -> None:
    """A genuine typo (``sofware-dev``) resolves no profile at any layer."""
    feature_dir = _write_meta(tmp_path, "006-zeta", {"mission": "sofware-dev"})

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 1
    result = results[0]
    assert result.action == "needs_manual_resolution"
    assert result.mission_type is None
    assert result.legacy_value == "sofware-dev"
    assert "sofware-dev" in (result.reason or "")

    meta = _read_meta(feature_dir)
    assert MISSION_TYPE_KEY not in meta, "non-resolving candidate must never be written"


# ---------------------------------------------------------------------------
# AC-6 — non-string legacy value is not a candidate, walk survives
# ---------------------------------------------------------------------------


def test_non_string_legacy_value_not_candidate_no_crash(tmp_path: Path) -> None:
    feature_dir = _write_meta(tmp_path, "007-eta", {"mission": 123})

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 1
    assert results[0].action == "skip"
    assert results[0].reason == "no legacy mission value"

    meta = _read_meta(feature_dir)
    assert MISSION_TYPE_KEY not in meta


def test_present_but_blank_mission_type_left_untouched(tmp_path: Path) -> None:
    # A present-but-blank mission_type is the deferred/out-of-scope ``typeless``
    # shape (spec Out of scope): the KEY is present, so the mission is NOT a
    # legacy-key-only candidate and must be left byte-identical even when a
    # resolving legacy value sits alongside it.
    feature_dir = _write_meta(
        tmp_path, "008-theta", {"mission_type": "", "mission": "software-dev"}
    )
    before = (feature_dir / "meta.json").read_bytes()

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 1
    assert results[0].action == "skip"
    assert results[0].reason == "mission_type already present"
    assert (feature_dir / "meta.json").read_bytes() == before


# ---------------------------------------------------------------------------
# AC-10 — mixed repo partition (>=4 missions)
# ---------------------------------------------------------------------------


def test_mixed_repo_partition(tmp_path: Path) -> None:
    _write_meta(tmp_path, "010-resolving", {"mission": "software-dev"})
    _write_meta(
        tmp_path,
        "011-already-typed",
        {"mission_type": "research", "mission": "research"},
    )
    _write_meta(tmp_path, "012-nonresolving", {"mission": "sofware-dev"})
    _write_meta(tmp_path, "013-nonstring", {"mission": 123})

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 4
    by_slug = {r.slug: r for r in results}

    assert by_slug["010-resolving"].action == "wrote"
    assert by_slug["010-resolving"].mission_type == "software-dev"

    assert by_slug["011-already-typed"].action == "skip"
    assert by_slug["011-already-typed"].reason == "mission_type already present"

    assert by_slug["012-nonresolving"].action == "needs_manual_resolution"
    assert by_slug["012-nonresolving"].mission_type is None

    assert by_slug["013-nonstring"].action == "skip"
    assert by_slug["013-nonstring"].reason == "no legacy mission value"

    actions = {r.action for r in results}
    assert actions == {"wrote", "skip", "needs_manual_resolution"}


# ---------------------------------------------------------------------------
# R-4 — write decision matches the profile repository, NOT activation
# ---------------------------------------------------------------------------


def test_write_decision_matches_profile_repository(tmp_path: Path) -> None:
    """An unactivated-but-resolving built-in type is still written (AC-5/R-4).

    ``research`` ships a governance profile but is NOT in this bare temp
    repo's (nonexistent) ``mission_type_activations`` roster — there is no
    ``.kittify/`` at all. The profile-resolution predicate must write it
    anyway; the rejected ``registered ∧ roster`` predicate would refuse.
    """
    feature_dir = _write_meta(tmp_path, "020-theta", {"mission": "research"})
    assert not (tmp_path / ".kittify").exists(), "must be a bare, unprovisioned repo"

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 1
    assert results[0].action == "wrote"
    assert results[0].mission_type == "research"
    meta = _read_meta(feature_dir)
    assert meta["mission_type"] == "research"


# ---------------------------------------------------------------------------
# B1/FR-005 — corrupt meta.json classifies error, walk continues
# ---------------------------------------------------------------------------


def test_corrupt_meta_classifies_error_walk_continues(tmp_path: Path) -> None:
    """A corrupt meta.json BETWEEN two resolving candidates never aborts the walk."""
    _write_meta(tmp_path, "030-before", {"mission": "software-dev"})

    corrupt_dir = tmp_path / "kitty-specs" / "031-corrupt"
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "meta.json").write_text("{not valid json", encoding="utf-8")

    _write_meta(tmp_path, "032-after", {"mission": "research"})

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 3
    by_slug = {r.slug: r for r in results}

    assert by_slug["030-before"].action == "wrote"
    assert by_slug["030-before"].mission_type == "software-dev"

    assert by_slug["031-corrupt"].action == "error"
    assert "corrupt json" in (by_slug["031-corrupt"].reason or "")

    assert by_slug["032-after"].action == "wrote"
    assert by_slug["032-after"].mission_type == "research"


# ---------------------------------------------------------------------------
# M1/R-1 — dossier rehash gating (fires on wrote ∧ ¬dry_run only)
# ---------------------------------------------------------------------------


def _profile_repo(repo_root: Path) -> MissionTypeProfileRepository:
    return MissionTypeProfileRepository.for_project(repo_root)


class TestDossierRehash:
    def test_fires_on_wrote_live_run(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, "040-live", {"mission": "software-dev"})

        import specify_cli.migration.backfill_mission_type as bmt_mod

        mock_fn = MagicMock(return_value=None)
        with patch.object(bmt_mod, "trigger_feature_dossier_sync_if_enabled", mock_fn):
            results = backfill_mission_type_repo(tmp_path)

        assert results[0].action == "wrote"
        mock_fn.assert_called_once()

    def test_does_not_fire_on_dry_run(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, "041-dry", {"mission": "software-dev"})

        import specify_cli.migration.backfill_mission_type as bmt_mod

        mock_fn = MagicMock(return_value=None)
        with patch.object(bmt_mod, "trigger_feature_dossier_sync_if_enabled", mock_fn):
            results = backfill_mission_type_repo(tmp_path, dry_run=True)

        assert results[0].action == "wrote"  # would-write reporting
        mock_fn.assert_not_called()

    def test_does_not_fire_for_skip_or_needs_manual(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, "042-skip", {"mission_type": "software-dev"})
        _write_meta(tmp_path, "043-manual", {"mission": "sofware-dev"})

        import specify_cli.migration.backfill_mission_type as bmt_mod

        mock_fn = MagicMock(return_value=None)
        with patch.object(bmt_mod, "trigger_feature_dossier_sync_if_enabled", mock_fn):
            backfill_mission_type_repo(tmp_path)

        mock_fn.assert_not_called()

    def test_raise_captured_as_dossier_warning_does_not_abort(self, tmp_path: Path) -> None:
        _write_meta(tmp_path, "044-explode", {"mission": "software-dev"})

        import specify_cli.migration.backfill_mission_type as bmt_mod

        with patch.object(
            bmt_mod,
            "trigger_feature_dossier_sync_if_enabled",
            side_effect=RuntimeError("dossier exploded"),
        ):
            results = backfill_mission_type_repo(tmp_path)

        assert len(results) == 1
        assert results[0].action == "wrote"
        assert results[0].dossier_warning is not None
        assert "dossier rehash failed" in results[0].dossier_warning


# ---------------------------------------------------------------------------
# Bonus coverage — no meta.json, unknown --mission slug structured error
# ---------------------------------------------------------------------------


def test_missing_meta_json_skipped(tmp_path: Path) -> None:
    (tmp_path / "kitty-specs" / "050-no-meta").mkdir(parents=True)

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 1
    assert results[0].action == "skip"
    assert results[0].reason == "meta.json not found"


def test_unknown_mission_slug_raises_structured_error(tmp_path: Path) -> None:
    """AC-9 domain-layer half: an unknown --mission slug is a structured error,
    never a silent ``wrote=0`` / empty-list false-green."""
    (tmp_path / "kitty-specs").mkdir(parents=True)

    with pytest.raises(MissionNotFoundError):
        backfill_mission_type_repo(tmp_path, mission_slug="does-not-exist")


def test_mission_slug_scopes_to_one(tmp_path: Path) -> None:
    _write_meta(tmp_path, "060-scoped", {"mission": "software-dev"})
    _write_meta(tmp_path, "061-other", {"mission": "research"})

    results = backfill_mission_type_repo(tmp_path, mission_slug="060-scoped")

    assert len(results) == 1
    assert results[0].slug == "060-scoped"
    assert results[0].action == "wrote"


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    feature_dir = _write_meta(tmp_path, "070-dryrun", {"mission": "software-dev"})
    before = (feature_dir / "meta.json").read_bytes()

    results = backfill_mission_type_repo(tmp_path, dry_run=True)

    assert results[0].action == "wrote"
    assert results[0].mission_type == "software-dev"
    assert (feature_dir / "meta.json").read_bytes() == before, "dry-run must not write"


# Ensure the LEGACY_MISSION_KEY constant matches the field name used above —
# guards against accidental drift between the fixtures and the module constant.
def test_legacy_mission_key_constant_matches_fixture_field() -> None:
    assert LEGACY_MISSION_KEY == "mission"
    assert MISSION_TYPE_KEY == "mission_type"
