from __future__ import annotations

from pathlib import Path

from specify_cli.status.migrate import migrate_feature
from specify_cli.status.store import EVENTS_FILENAME, read_events
from tests.integration.test_migration_e2e import _setup_legacy_feature


def test_migration_all_planned_wps(tmp_path: Path) -> None:
    """Migration of all-planned WPs produces no events."""
    feature_dir = _setup_legacy_feature(
        tmp_path,
        wp_lanes={"WP01": "planned", "WP02": "planned"},
    )

    result = migrate_feature(feature_dir)
    assert result.status == "migrated"

    events_path = feature_dir / EVENTS_FILENAME
    if events_path.exists():
        events = read_events(feature_dir)
        assert len(events) == 0
