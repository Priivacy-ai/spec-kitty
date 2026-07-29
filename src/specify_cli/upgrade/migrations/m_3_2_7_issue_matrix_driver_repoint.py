"""Migration 3.2.7: repoint the issue-matrix merge driver to the JSON artifact.

WP05 (write-side-seam-matrix-tracer-01KYP3MH) migrated ``issue-matrix`` to a
structured ``issue-matrix.json`` artifact -- ``issue-matrix.md`` is no longer
written by any canonical path (C-008). The #2804 gate-artifact merge driver
installed by ``m_3_2_6_gate_artifact_merge_drivers`` still mapped
``kitty-specs/**/issue-matrix.md`` to ``spec-kitty-issue-matrix``, so an
upgraded repo's ``.gitattributes`` never routed the real ``.json`` artifact to
any reconcile driver -- the row-aware rewrite (FR-008, WP11) would be inert on
every already-initialized consumer repo without this migration.

This is a NEW forward migration, not an edit of the historical ``m_3_2_6``
migration: that migration already ran (and is idempotent) for repos on 3.2.6,
and its ``issue-matrix.md`` line is now simply inert (no file matches it since
WP05 shipped). Mutating a historical migration in place would rewrite already-
applied history; a fresh migration is the correct additive fix (DIRECTIVE_044).
"""

from __future__ import annotations

from ..registry import MigrationRegistry
from ._merge_driver_seeding import DriverSpec, MergeDriverSeedingMigration

_DRIVERS: tuple[DriverSpec, ...] = (
    DriverSpec(
        config_key="spec-kitty-issue-matrix",
        name="Spec Kitty issue matrix row-aware merge",
        command="spec-kitty merge-driver-issue-matrix %O %A %B",
        pattern="kitty-specs/**/issue-matrix.json",
    ),
)


@MigrationRegistry.register
class IssueMatrixDriverRepointMigration(MergeDriverSeedingMigration):
    """Repoint the issue-matrix merge driver from ``.md`` to ``.json`` (FR-008)."""

    migration_id = "3.2.7_issue_matrix_driver_repoint"
    description = "Repoint the issue-matrix merge driver to issue-matrix.json"
    target_version = "3.2.7"
    drivers = _DRIVERS
    dry_run_summary = "Would repoint the issue-matrix merge driver to issue-matrix.json"
