"""Historical-import pipeline for ``spec-kitty sync import-history`` (#2262).

A first sync registers a remote project/build but leaves it with zero
materialized missions — the SaaS materializer refuses to fabricate a
WorkPackage from a status event with no prior create. This package emits the
missing ``MissionCreated → WPCreated[] → WPStatusChanged[]`` prefix so
historical local work populates the projection.

Stages (see issue #2262 §3.3):

* WP-Y2 — :mod:`.scan`: the hybrid SCAN — read the on-disk lifecycle prefix
  where present, synthesize it from ``meta.json`` + ``tasks/WP*.md`` where
  absent, and drop local-only lifecycle events.

Later slices add SYNTHESIZE (ordered deterministic envelope stream),
PROVENANCE, PREFLIGHT, UPLOAD, and REPORT.
"""

from __future__ import annotations

from specify_cli.sync.history_import.scan import (
    MissionScan,
    PrefixSource,
    ScannedWorkPackage,
    scan_mission,
    scan_missions,
)

__all__ = [
    "MissionScan",
    "PrefixSource",
    "ScannedWorkPackage",
    "scan_mission",
    "scan_missions",
]
