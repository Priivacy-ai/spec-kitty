"""Migration: repair feature metadata/state drift and legacy worktree assets."""

from __future__ import annotations

import io
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.agent_utils.directories import AGENT_DIRS
from specify_cli.frontmatter import FrontmatterError, FrontmatterManager
from specify_cli.runtime.doctor import check_stale_legacy_assets
from specify_cli.status.legacy_bridge import update_all_views
from specify_cli.status.migrate import feature_requires_historical_migration, migrate_feature
from specify_cli.status.phase import resolve_phase
from specify_cli.status.reducer import SNAPSHOT_FILENAME, materialize, reduce
from specify_cli.status.store import EVENTS_FILENAME, StoreError, read_events
from specify_cli.status.transitions import CANONICAL_LANES, resolve_lane_alias
from specify_cli.status.validate import (
    validate_derived_views,
    validate_materialization_drift,
)
from specify_cli.upgrade.feature_meta import (
    build_baseline_feature_meta,
    load_feature_meta,
    write_feature_meta,
)

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

_PROMPT_LINE_RE = re.compile(r"^(\*\*Prompt\*\*:\s*`?)([^`\n]+)(`?)$", re.MULTILINE)


@MigrationRegistry.register
class ConsistencySweepMigration(BaseMigration):
    """Repair version-stamped projects that still have structural drift."""

    migration_id = "2.0.6_consistency_sweep"
    description = "Repair feature metadata/state drift and clean legacy worktree assets"
    target_version = "2.0.6"

    def detect(self, project_path: Path) -> bool:
        """Return True when project state still needs 2.0.6 consistency repair."""
        if check_stale_legacy_assets(project_path).passed is False:
            return True
        if _has_legacy_worktree_assets(project_path):
            return True

        for feature_dir in _iter_feature_dirs(project_path):
            if _feature_requires_repair(feature_dir, project_path):
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Consistency repair only needs a spec project root."""
        if (project_path / ".kittify").exists() or (project_path / "kitty-specs").exists():
            return True, ""
        return False, "No .kittify/ or kitty-specs/ directory found"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Run the 2.0.6 consistency sweep."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        runtime_changes, runtime_warnings = _migrate_runtime_assets(project_path, dry_run)
        changes.extend(runtime_changes)
        warnings.extend(runtime_warnings)

        worktree_changes, worktree_errors = _cleanup_legacy_worktree_assets(project_path, dry_run)
        changes.extend(worktree_changes)
        errors.extend(worktree_errors)

        for feature_dir in _iter_feature_dirs(project_path):
            feature_changes, feature_warnings = _repair_feature(feature_dir, project_path, dry_run)
            changes.extend(feature_changes)
            warnings.extend(feature_warnings)

        if not changes and not warnings and not errors:
            changes.append("Project already consistent for 2.0.6")

        return MigrationResult(
            success=not errors,
            changes_made=changes,
            warnings=warnings,
            errors=errors,
        )


def _iter_feature_dirs(project_path: Path) -> list[Path]:
    kitty_specs = project_path / "kitty-specs"
    if not kitty_specs.exists():
        return []
    return [
        path
        for path in sorted(kitty_specs.iterdir())
        if path.is_dir()
    ]


def _feature_requires_repair(feature_dir: Path, repo_root: Path) -> bool:
    try:
        meta = load_feature_meta(feature_dir)
    except json.JSONDecodeError:
        return True
    if meta is None:
        return True
    desired_meta = build_baseline_feature_meta(
        feature_dir,
        repo_root,
        existing_meta=meta,
    )
    if meta != desired_meta:
        return True
    if _tasks_md_has_legacy_prompt_refs(feature_dir):
        return True
    if _has_orphan_status_snapshot(feature_dir):
        return True
    if _wp_frontmatter_needs_normalization(feature_dir):
        return True
    if _status_events_need_repair(feature_dir):
        return True
    if _feature_has_status_drift(feature_dir, repo_root):
        return True
    return False


def _repair_feature(
    feature_dir: Path,
    repo_root: Path,
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    changes: list[str] = []
    warnings: list[str] = []

    meta = None
    try:
        meta = load_feature_meta(feature_dir)
    except json.JSONDecodeError as exc:
        warnings.append(f"{feature_dir.name}: invalid meta.json ({exc})")

    desired_meta = build_baseline_feature_meta(
        feature_dir,
        repo_root,
        existing_meta=meta,
    )
    if meta != desired_meta:
        action = "Would write" if dry_run else "Wrote"
        changes.append(f"{feature_dir.name}: {action.lower()} baseline meta.json")
        if not dry_run:
            write_feature_meta(feature_dir, desired_meta)

    normalized_count, normalize_warnings = _normalize_wp_frontmatter(feature_dir, dry_run)
    warnings.extend(f"{feature_dir.name}: {warning}" for warning in normalize_warnings)
    if normalized_count:
        verb = "Would normalize" if dry_run else "Normalized"
        changes.append(f"{feature_dir.name}: {verb.lower()} {normalized_count} work package files")

    orphan_change, orphan_warning = _cleanup_orphan_status_snapshot(feature_dir, dry_run)
    if orphan_change:
        changes.append(f"{feature_dir.name}: {orphan_change}")
    if orphan_warning:
        warnings.append(f"{feature_dir.name}: {orphan_warning}")

    needs_event_repair = _status_events_need_repair(feature_dir)
    events_rebuilt = False
    if needs_event_repair:
        if dry_run:
            changes.append(f"{feature_dir.name}: would reconstruct status.events.jsonl from frontmatter history")
        else:
            migration_result = migrate_feature(feature_dir, dry_run=False)
            if migration_result.status == "migrated":
                events_rebuilt = True
                changes.append(f"{feature_dir.name}: reconstructed status.events.jsonl")
            elif migration_result.status == "failed":
                warnings.append(f"{feature_dir.name}: {migration_result.error}")

    unreadable_change, unreadable_warning = _cleanup_unreadable_events_log(feature_dir, dry_run)
    if unreadable_change:
        changes.append(f"{feature_dir.name}: {unreadable_change}")
    if unreadable_warning:
        warnings.append(f"{feature_dir.name}: {unreadable_warning}")

    has_event_log = _feature_has_event_log(feature_dir)
    if has_event_log or unreadable_change:
        if dry_run:
            if needs_event_repair or unreadable_change:
                changes.append(f"{feature_dir.name}: would regenerate status.json and tasks.md views")
            elif _feature_has_status_drift(feature_dir, repo_root):
                changes.append(f"{feature_dir.name}: would regenerate status.json and tasks.md views")
        else:
            snapshot = materialize(feature_dir)
            update_all_views(feature_dir, snapshot, repo_root=repo_root)
            if events_rebuilt or unreadable_change or _feature_has_status_drift(feature_dir, repo_root):
                changes.append(f"{feature_dir.name}: regenerated status.json and compatibility views")

    prompt_rewrites = _rewrite_tasks_prompt_refs(feature_dir, dry_run)
    if prompt_rewrites:
        verb = "Would rewrite" if dry_run else "Rewrote"
        changes.append(f"{feature_dir.name}: {verb.lower()} {prompt_rewrites} legacy prompt reference(s)")

    return changes, warnings


def _normalize_wp_frontmatter(feature_dir: Path, dry_run: bool) -> tuple[int, list[str]]:
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return 0, []

    manager = FrontmatterManager()
    normalized = 0
    warnings: list[str] = []

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        try:
            original = wp_file.read_text(encoding="utf-8-sig")
            frontmatter, body = manager.read(wp_file)
        except FrontmatterError as exc:
            warnings.append(f"{wp_file.name}: {exc}")
            continue

        raw_lane = frontmatter.get("lane") or "planned"
        canonical_lane = resolve_lane_alias(str(raw_lane))
        if canonical_lane in CANONICAL_LANES:
            frontmatter["lane"] = canonical_lane

        rendered = _render_frontmatter(manager, frontmatter, body)
        if original == rendered:
            continue

        normalized += 1
        if not dry_run:
            wp_file.write_text(rendered, encoding="utf-8")

    return normalized, warnings


def _render_frontmatter(manager: FrontmatterManager, frontmatter: dict, body: str) -> str:
    buffer = io.StringIO()
    buffer.write("---\n")
    manager.yaml.dump(manager._normalize_frontmatter(frontmatter), buffer)
    buffer.write("---\n")
    buffer.write(body)
    return buffer.getvalue()


def _rewrite_tasks_prompt_refs(feature_dir: Path, dry_run: bool) -> int:
    tasks_md = feature_dir / "tasks.md"
    tasks_dir = feature_dir / "tasks"
    if not tasks_md.exists() or not tasks_dir.exists():
        return 0

    content = tasks_md.read_text(encoding="utf-8")
    rewrites = 0

    def replacer(match: re.Match[str]) -> str:
        nonlocal rewrites
        prefix, prompt_path, suffix = match.groups()
        if "tasks/" not in prompt_path:
            return match.group(0)

        wp_match = re.search(r"(WP\d{2})", prompt_path)
        if wp_match is None:
            return match.group(0)

        candidates = sorted(tasks_dir.glob(f"{wp_match.group(1)}*.md"))
        if not candidates:
            return match.group(0)

        tasks_index = prompt_path.find("tasks/")
        if tasks_index == -1:
            return match.group(0)

        new_path = prompt_path[:tasks_index] + "tasks/" + candidates[0].name
        if new_path == prompt_path:
            return match.group(0)

        rewrites += 1
        return f"{prefix}{new_path}{suffix}"

    updated = _PROMPT_LINE_RE.sub(replacer, content)
    if rewrites and not dry_run:
        tasks_md.write_text(updated, encoding="utf-8")
    return rewrites


def _status_events_need_repair(feature_dir: Path) -> bool:
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists() or not list(tasks_dir.glob("WP*.md")):
        return False

    events_path = feature_dir / EVENTS_FILENAME
    if not events_path.exists():
        return feature_requires_historical_migration(feature_dir)

    content = events_path.read_text(encoding="utf-8").strip()
    if not content:
        return feature_requires_historical_migration(feature_dir)

    try:
        events = read_events(feature_dir)
    except StoreError:
        return True

    if not events:
        return feature_requires_historical_migration(feature_dir)
    if any(event.reason and "historical_frontmatter_to_jsonl:v1" in event.reason for event in events):
        return False
    if any(not event.actor.startswith("migration") for event in events):
        return False
    return feature_requires_historical_migration(feature_dir)


def _feature_has_event_log(feature_dir: Path) -> bool:
    events_path = feature_dir / EVENTS_FILENAME
    return events_path.exists() and bool(events_path.read_text(encoding="utf-8").strip())


def _feature_has_status_drift(feature_dir: Path, repo_root: Path) -> bool:
    if not _feature_has_event_log(feature_dir):
        return False

    if validate_materialization_drift(feature_dir):
        return True

    try:
        snapshot = reduce(read_events(feature_dir))
    except StoreError:
        return True

    phase, _source = resolve_phase(repo_root, snapshot.feature_slug or feature_dir.name)
    findings = validate_derived_views(feature_dir, snapshot.work_packages, phase)
    return bool(findings)


def _tasks_md_has_legacy_prompt_refs(feature_dir: Path) -> bool:
    tasks_md = feature_dir / "tasks.md"
    if not tasks_md.exists():
        return False
    for line in tasks_md.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith("**Prompt**:"):
            continue
        if any(segment in line for segment in ("tasks/planned/", "tasks/doing/", "tasks/for_review/", "tasks/done/")):
            return True
    return False


def _wp_frontmatter_needs_normalization(feature_dir: Path) -> bool:
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return False
    manager = FrontmatterManager()
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        content = wp_file.read_text(encoding="utf-8-sig", errors="ignore")
        if re.search(r'^lane:\s*["\']', content, re.MULTILINE):
            return True
        if re.search(r"^lane:\s*doing\s*$", content, re.MULTILINE):
            return True
        try:
            frontmatter, _body = manager.read(wp_file)
        except FrontmatterError:
            return True
        raw_lane = frontmatter.get("lane")
        if raw_lane is None or not str(raw_lane).strip():
            return True
    return False


def _has_orphan_status_snapshot(feature_dir: Path) -> bool:
    status_path = feature_dir / SNAPSHOT_FILENAME
    events_path = feature_dir / EVENTS_FILENAME
    if not status_path.exists() or events_path.exists():
        return False
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        data.get("event_count") == 0
        and data.get("work_packages") == {}
        and data.get("summary") == {lane: 0 for lane in CANONICAL_LANES}
        and data.get("feature_slug", "") in {"", feature_dir.name}
    )


def _cleanup_orphan_status_snapshot(feature_dir: Path, dry_run: bool) -> tuple[str | None, str | None]:
    status_path = feature_dir / SNAPSHOT_FILENAME
    if not _has_orphan_status_snapshot(feature_dir):
        if status_path.exists() and not (feature_dir / EVENTS_FILENAME).exists() and not (feature_dir / "tasks").exists():
            return None, "status.json has no matching event log and could not be auto-repaired"
        return None, None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"{SNAPSHOT_FILENAME}.orphan.bak.{timestamp}"
    if not dry_run:
        status_path.rename(feature_dir / backup_name)
    return f"archived orphan {SNAPSHOT_FILENAME} to {backup_name}", None


def _cleanup_unreadable_events_log(feature_dir: Path, dry_run: bool) -> tuple[str | None, str | None]:
    events_path = feature_dir / EVENTS_FILENAME
    if not events_path.exists():
        return None, None

    content = events_path.read_text(encoding="utf-8").strip()
    if not content:
        return None, None

    try:
        read_events(feature_dir)
        return None, None
    except StoreError as exc:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_name = f"{EVENTS_FILENAME}.unreadable.bak.{timestamp}"
        if not dry_run:
            events_path.rename(feature_dir / backup_name)
        return (
            f"archived unreadable {EVENTS_FILENAME} to {backup_name}",
            f"status.events.jsonl was unreadable and has been quarantined ({exc})",
        )


def _migrate_runtime_assets(project_path: Path, dry_run: bool) -> tuple[list[str], list[str]]:
    kittify_dir = project_path / ".kittify"
    if not kittify_dir.exists():
        return [], []

    try:
        from specify_cli.runtime.migrate import execute_migration

        report = execute_migration(project_path, dry_run=dry_run)
    except Exception as exc:  # pragma: no cover - defensive guard
        return [], [f"runtime asset cleanup skipped: {exc}"]

    changes: list[str] = []
    moved = len(report.moved)
    removed = len(report.removed)
    if moved or removed:
        verb = "Would migrate" if dry_run else "Migrated"
        changes.append(
            f"{verb.lower()} {removed} identical and {moved} customized legacy runtime asset(s)"
        )
    return changes, []


def _has_legacy_worktree_assets(project_path: Path) -> bool:
    return any(_iter_worktree_cleanup_roots(project_path))


def _iter_worktree_cleanup_roots(project_path: Path) -> list[Path]:
    if ".worktrees" in project_path.parts:
        return [project_path]

    worktrees_dir = project_path / ".worktrees"
    if not worktrees_dir.exists():
        return []
    return [path for path in sorted(worktrees_dir.iterdir()) if path.is_dir()]


def _cleanup_legacy_worktree_assets(project_path: Path, dry_run: bool) -> tuple[list[str], list[str]]:
    changes: list[str] = []
    errors: list[str] = []
    cleaned = 0

    for root in _iter_worktree_cleanup_roots(project_path):
        root_cleaned = False
        for agent_dir, subdir in AGENT_DIRS:
            commands_dir = root / agent_dir / subdir
            if commands_dir.is_symlink() or commands_dir.exists():
                root_cleaned = True
                if dry_run:
                    changes.append(f"[{root.name}] would remove {agent_dir}/{subdir}/")
                else:
                    try:
                        if commands_dir.is_symlink():
                            commands_dir.unlink()
                        else:
                            shutil.rmtree(commands_dir)
                        parent = commands_dir.parent
                        if parent.exists() and not any(parent.iterdir()):
                            parent.rmdir()
                    except OSError as exc:
                        errors.append(f"[{root.name}] failed to remove {agent_dir}/{subdir}/: {exc}")

        scripts_dir = root / ".kittify" / "scripts"
        if scripts_dir.is_symlink() or scripts_dir.exists():
            root_cleaned = True
            if dry_run:
                changes.append(f"[{root.name}] would remove .kittify/scripts/")
            else:
                try:
                    if scripts_dir.is_symlink():
                        scripts_dir.unlink()
                    else:
                        shutil.rmtree(scripts_dir)
                except OSError as exc:
                    errors.append(f"[{root.name}] failed to remove .kittify/scripts/: {exc}")

        if root_cleaned:
            cleaned += 1

    if cleaned:
        verb = "Would clean" if dry_run else "Cleaned"
        changes.append(f"{verb.lower()} {cleaned} worktree(s) with legacy command/script assets")
    return changes, errors
