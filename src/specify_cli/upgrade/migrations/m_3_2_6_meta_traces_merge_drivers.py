"""Migration 3.2.6: install the meta.json + traces/*.md git merge drivers.

Sibling of ``m_3_1_1_event_log_merge_driver.py``. #2709 / FR-003 / FR-004 / C-006:
the squash mission→target integration (``git merge --squash -X theirs``) must
reconcile target-newer ``meta.json`` acceptance/VCS provenance and ``traces/*.md``
sections instead of clobbering them. Custom merge drivers override ``-X theirs``
on their registered paths, so this migration seeds the ``.gitattributes`` mapping
plus the local ``merge.<driver>.*`` config for both drivers.

The seeding body itself lives in ``_merge_driver_seeding.py`` and is shared with
the other driver-seeding migrations (DIRECTIVE_044 — parametrized, not cloned).

coord-write-placement-closure-01KYCF83 WP06 (out-of-owned-files leeway,
documented in the move-task note) added the THIRD driver entry below:
``decisions.events.jsonl`` reuses the pre-existing ``spec-kitty-event-log``
driver (same config/command as ``m_3_1_1``'s ``status.events.jsonl`` entry —
the append-only event-log union algorithm is filename-agnostic) rather than a
fourth dedicated command. ``MergeDriverSeedingMigration.detect()`` checks each
driver's ``.gitattributes`` line independently (not a version-gate), so
already-upgraded repos still pick up this new line on their next upgrade run.
"""

from __future__ import annotations

from ..registry import MigrationRegistry
from ._merge_driver_seeding import DriverSpec, MergeDriverSeedingMigration

_DRIVERS: tuple[DriverSpec, ...] = (
    DriverSpec(
        config_key="spec-kitty-meta",
        name="Spec Kitty mission meta field merge",
        command="spec-kitty merge-driver-meta %O %A %B",
        pattern="kitty-specs/**/meta.json",
    ),
    DriverSpec(
        config_key="spec-kitty-traces",
        name="Spec Kitty mission traces union merge",
        command="spec-kitty merge-driver-traces %O %A %B",
        pattern="kitty-specs/**/traces/*.md",
    ),
    DriverSpec(
        config_key="spec-kitty-event-log",
        name="Spec Kitty event log union merge",
        command="spec-kitty merge-driver-event-log %O %A %B",
        pattern="kitty-specs/**/decisions.events.jsonl",
    ),
)


@MigrationRegistry.register
class MetaTracesMergeDriverMigration(MergeDriverSeedingMigration):
    """Install git merge drivers for meta.json, traces/*.md, and
    decisions.events.jsonl (#2709; the third driver added by WP06)."""

    migration_id = "3.2.6_meta_traces_merge_drivers"
    description = (
        "Install semantic git merge drivers for meta.json, traces/*.md, and "
        "decisions.events.jsonl"
    )
    target_version = "3.2.6"
    drivers = _DRIVERS
    dry_run_summary = "Would install meta.json + traces/*.md + decisions.events.jsonl merge drivers and .gitattributes entries"
