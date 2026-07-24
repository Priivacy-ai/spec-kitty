"""Migration 3.3.0: install the coordination gate-artifact git merge drivers (#2804).

``acceptance-matrix.json`` and ``issue-matrix.md`` are filled on the target at
accept time and left as placeholder scaffolds on the mission branch. Under the
squash mission→target integration (``git merge --squash -X theirs``) the mission
branch's scaffold won, so the merged branch kept empty gate artifacts even though
the done-gate had just passed against the filled ones — silent audit-trail loss
(#2804).

The drivers registered here override ``-X theirs`` on those two paths and keep
whichever side carries real evidence. This migration seeds them for
already-initialized repos; fresh repos get them from the ``init`` seed and this
project from its committed ``.gitattributes``.
"""

from __future__ import annotations

from ..registry import MigrationRegistry
from ._merge_driver_seeding import DriverSpec, MergeDriverSeedingMigration

_DRIVERS: tuple[DriverSpec, ...] = (
    DriverSpec(
        config_key="spec-kitty-acceptance-matrix",
        name="Spec Kitty acceptance matrix filled-side merge",
        command="spec-kitty merge-driver-acceptance-matrix %O %A %B",
        pattern="kitty-specs/**/acceptance-matrix.json",
    ),
    DriverSpec(
        config_key="spec-kitty-issue-matrix",
        name="Spec Kitty issue matrix filled-side merge",
        command="spec-kitty merge-driver-issue-matrix %O %A %B",
        pattern="kitty-specs/**/issue-matrix.md",
    ),
)


@MigrationRegistry.register
class GateArtifactMergeDriverMigration(MergeDriverSeedingMigration):
    """Install git merge drivers for acceptance-matrix.json and issue-matrix.md (#2804)."""

    migration_id = "3.3.0_gate_artifact_merge_drivers"
    description = "Install semantic git merge drivers for acceptance-matrix.json and issue-matrix.md"
    target_version = "3.3.0"
    drivers = _DRIVERS
    dry_run_summary = "Would install gate-artifact merge drivers and .gitattributes entries"
