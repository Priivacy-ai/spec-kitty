"""Acceptance test for the canonical per-mission event-rebuild entry (WP13, #1754).

T051 — ATDD-first. Authored RED before the T047-T050 implementation.

Covers:
- FR-032: a single canonical per-mission event-rebuild entry on ``mission_state``
  returning event counts (``events_generated`` / ``events_corrected`` /
  ``errors`` / ``warnings``).
- NFR-004 (behavior preservation): a legacy mission rebuilds to the *same*
  ``status.events.jsonl`` bytes and the *same* counts whether the rebuild goes
  through the canonical entry or the underlying ``rebuild_state`` implementation.
- FR-033: the deprecated package-level re-export
  (``specify_cli.migration.rebuild_event_log`` / ``RebuildResult``) is gone, so
  the ``__all__`` declared-but-undefined nuisance is resolved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Fixture builders (mirror tests/specify_cli/migration/test_rebuild_state.py)
# ---------------------------------------------------------------------------


def _make_feature(tmp_path: Path, slug: str, wps: list[dict]) -> Path:
    feature_dir = tmp_path / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": slug, "title": f"Feature {slug}"}, indent=2),
        encoding="utf-8",
    )
    for wp in wps:
        name = wp["name"]
        lane = wp.get("lane", "planned")
        lines = [
            "---",
            "# no work_package_id",
            f"wp_code: {name!r}",
            f"title: {name} Title",
            f"lane: {lane!r}",
            "dependencies: []",
            "---",
            "",
            f"# {name} body",
        ]
        (tasks_dir / f"{name}-some-title.md").write_text("\n".join(lines), encoding="utf-8")
    return feature_dir


def _read_events_text(feature_dir: Path) -> str:
    path = feature_dir / "status.events.jsonl"
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ---------------------------------------------------------------------------
# FR-032 — canonical entry exists, returns the count-shaped result
# ---------------------------------------------------------------------------


def test_canonical_entry_exists_and_returns_counts(tmp_path: Path) -> None:
    from specify_cli.migration import mission_state

    assert hasattr(mission_state, "rebuild_mission_event_log"), (
        "FR-032: mission_state must expose a canonical per-mission "
        "event-rebuild entry."
    )

    feature_dir = _make_feature(
        tmp_path,
        "057-legacy",
        [{"name": "WP01", "lane": "in_progress"}, {"name": "WP02", "lane": "done"}],
    )

    result = mission_state.rebuild_mission_event_log(feature_dir, "057-legacy")

    # Count-shaped reporting contract (the per-feature contract the runner relies on).
    assert isinstance(result.events_generated, int)
    assert isinstance(result.events_corrected, int)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)
    # A mid-flight mission with two non-planned WPs generates synthetic chains.
    assert result.events_generated > 0
    assert (feature_dir / "status.events.jsonl").exists()


def test_canonical_entry_accepts_wp_id_map(tmp_path: Path) -> None:
    from specify_cli.migration import mission_state

    feature_dir = _make_feature(tmp_path, "058-legacy", [{"name": "WP01", "lane": "claimed"}])
    result = mission_state.rebuild_mission_event_log(
        feature_dir, "058-legacy", wp_id_map={"WP01": "WP01-ULID"}
    )
    assert result.events_generated >= 0
    assert not result.errors


# ---------------------------------------------------------------------------
# NFR-004 — behavior preservation against the underlying implementation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "wps",
    [
        [{"name": "WP01", "lane": "in_progress"}],
        [{"name": "WP01", "lane": "done"}, {"name": "WP02", "lane": "for_review"}],
        [{"name": "WP01", "lane": "planned"}, {"name": "WP02", "lane": "claimed"}],
    ],
)
def test_behavior_preserved_vs_underlying_impl(tmp_path: Path, wps: list[dict]) -> None:
    """The canonical entry produces byte-identical output and equal counts.

    Rebuild the *same* legacy fixture (identical slug, separate directories)
    twice: once through the underlying ``rebuild_state`` implementation
    directly, once through the canonical ``mission_state`` entry. Assert the
    resulting event log bytes and the reported counts are identical. This is the
    NFR-004 behavior-preservation proof: routing the callers off the deprecated
    symbol changes nothing about the migrated output.
    """
    from specify_cli.migration import mission_state
    from specify_cli.migration.rebuild_state import rebuild_event_log

    legacy_root = tmp_path / "legacy"
    canonical_root = tmp_path / "canonical"
    legacy_dir = _make_feature(legacy_root, "059-legacy", wps)
    canonical_dir = _make_feature(canonical_root, "059-legacy", wps)

    legacy_result = rebuild_event_log(legacy_dir, "059-legacy", {})
    canonical_result = mission_state.rebuild_mission_event_log(canonical_dir, "059-legacy")

    assert canonical_result.events_generated == legacy_result.events_generated
    assert canonical_result.events_corrected == legacy_result.events_corrected
    assert bool(canonical_result.errors) == bool(legacy_result.errors)

    # Identical slug + identical fixture => byte-identical event log output,
    # proving the canonical seam changes nothing about the migrated bytes.
    assert _read_events_text(canonical_dir) == _read_events_text(legacy_dir)


# ---------------------------------------------------------------------------
# FR-033 — deprecated package re-export removed (no declared-but-undefined name)
# ---------------------------------------------------------------------------


def test_deprecated_package_reexport_removed() -> None:
    import specify_cli.migration as migration_pkg

    assert "rebuild_event_log" not in migration_pkg.__all__
    assert "RebuildResult" not in migration_pkg.__all__

    with pytest.raises(AttributeError):
        _ = migration_pkg.rebuild_event_log  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        _ = migration_pkg.RebuildResult  # type: ignore[attr-defined]
