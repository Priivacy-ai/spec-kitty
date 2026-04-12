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

from specify_cli.status.reducer import SNAPSHOT_FILENAME, reduce
from specify_cli.status.store import read_events

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


def _iter_feature_dirs(project_path: Path) -> list[Path]:
    kitty_specs = project_path / "kitty-specs"
    if not kitty_specs.exists():
        return []
    return [p for p in sorted(kitty_specs.iterdir()) if p.is_dir()]


def _needs_normalisation(feature_dir: Path) -> bool:
    """Return True when status.json has a stale ``materialized_at`` value.

    This check must stay read-only. Calling ``materialize()`` here would rewrite
    ``status.json`` during detect()/dry_run evaluation and hide stale files from
    the migration.
    """
    status_path = feature_dir / SNAPSHOT_FILENAME
    if not status_path.exists():
        return False
    try:
        actual = json.loads(status_path.read_text(encoding="utf-8"))
        snapshot = reduce(read_events(feature_dir))
        expected_materialized_at = snapshot.materialized_at
        return actual.get("materialized_at") != expected_materialized_at
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
                    if _needs_normalisation(feature_dir):
                        current = json.loads(status_path.read_text(encoding="utf-8"))
                        snapshot = reduce(read_events(feature_dir))
                        current["materialized_at"] = snapshot.materialized_at
                        status_path.write_text(
                            json.dumps(current, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8",
                        )
                        changes.append(f"{feature_dir.name}: normalised status.json")
            except Exception as exc:
                errors.append(f"{feature_dir.name}: {exc}")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
        )
