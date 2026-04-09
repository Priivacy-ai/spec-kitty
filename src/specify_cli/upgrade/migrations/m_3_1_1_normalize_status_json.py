"""Normalize status.json files to use deterministic materialized_at.

Before 3.1.1, ``materialize()`` stamped a wall-clock ``datetime.now(UTC)``
into every ``status.json`` on every invocation — even when the event log had
not changed.  This left 60+ files dirty in git after routine CLI use.

The fix (reducer.py, FR-001/NFR-001) makes ``materialized_at`` deterministic:
- Features with events: last event's ``at`` timestamp
- Features with no events: ``""`` (stable empty string)

This one-shot migration normalises every existing ``status.json`` in the
project so that it reflects the new deterministic format.  After the migration
the skip-write guard in ``materialize()`` will keep the files stable
indefinitely.

See GitHub issue #524.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.status.reducer import SNAPSHOT_FILENAME, materialize, materialize_to_json, reduce
from specify_cli.status.store import read_events

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


def _iter_feature_dirs(project_path: Path) -> list[Path]:
    kitty_specs = project_path / "kitty-specs"
    if not kitty_specs.exists():
        return []
    return [p for p in sorted(kitty_specs.iterdir()) if p.is_dir()]


def _needs_normalisation(feature_dir: Path) -> bool:
    """Return True when status.json differs from the canonical reduced snapshot.

    This check must stay read-only. Calling ``materialize()`` here would rewrite
    ``status.json`` during detect()/dry_run evaluation and hide stale files from
    the migration.
    """
    status_path = feature_dir / SNAPSHOT_FILENAME
    if not status_path.exists():
        return False
    try:
        snapshot = reduce(read_events(feature_dir))
        identity = resolve_mission_identity(feature_dir)
        snapshot.mission_number = identity.mission_number
        snapshot.mission_type = identity.mission_type
        expected = materialize_to_json(snapshot)
        actual = status_path.read_text(encoding="utf-8")
        return actual != expected
    except Exception:
        return False


@MigrationRegistry.register
class NormalizeStatusJsonMigration(BaseMigration):
    """Normalise status.json files to use deterministic materialized_at."""

    migration_id = "3.1.1_normalize_status_json"
    description = "Normalise status.json: replace wall-clock materialized_at with deterministic value (issue #524)"
    target_version = "3.1.1"

    def detect(self, project_path: Path) -> bool:
        """True when any kitty-specs/*/status.json is out of date."""
        return any(_needs_normalisation(fd) for fd in _iter_feature_dirs(project_path))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if (project_path / "kitty-specs").exists() or (project_path / ".kittify").exists():
            return True, ""
        return False, "No kitty-specs/ directory found"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        changes: list[str] = []
        errors: list[str] = []

        for feature_dir in _iter_feature_dirs(project_path):
            status_path = feature_dir / SNAPSHOT_FILENAME
            if not status_path.exists():
                continue
            try:
                if dry_run:
                    if _needs_normalisation(feature_dir):
                        changes.append(f"{feature_dir.name}: would normalise status.json")
                else:
                    before = status_path.read_text(encoding="utf-8")
                    materialize(feature_dir)
                    after = status_path.read_text(encoding="utf-8")
                    if before != after:
                        changes.append(f"{feature_dir.name}: normalised status.json")
            except Exception as exc:
                errors.append(f"{feature_dir.name}: {exc}")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
        )
