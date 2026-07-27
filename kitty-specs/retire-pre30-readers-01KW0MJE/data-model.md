# Data Model: Retire pre-3.0 status/task readers from active runtime

**Mission**: retire-pre30-readers-01KW0MJE  
**Date**: 2026-06-26

---

## Post-Cutover Invariant

After this mission is merged, the following invariant holds for the active runtime:

> **All active `spec-kitty` task/status commands operate exclusively on the post-3.0 project shape: flat `tasks/WP*.md` files with lane state derived from `status.events.jsonl`. Any project that still has `tasks/{lane}/` subdirectories containing `.md` files is rejected at the command boundary before any read or mutation occurs.**

Formally:

```
∀ active command C, ∀ feature_path F:
  is_legacy_format(F) == True  →  C exits non-zero before touching F
  is_legacy_format(F) == False →  C proceeds as normal
```

**Exception — dashboard and `spec-kitty upgrade`**: These are read-only or upgrade-path consumers that intentionally retain pre-3.0 detection without rejecting. They are not affected by the invariant.

---

## Namespace Relocation Map

| Symbol | Pre-mission import path | Post-mission import path | Notes |
|--------|------------------------|--------------------------|-------|
| `is_legacy_format` | `specify_cli.legacy_detector` | `specify_cli.upgrade.legacy_detector` | Active runtime no longer exports it |
| `get_legacy_lane_counts` | `specify_cli.legacy_detector` | `specify_cli.upgrade.legacy_detector` | Zero active-runtime callers; upgrade-only use |
| `LEGACY_LANE_DIRS` | `specify_cli.legacy_detector` | `specify_cli.upgrade.legacy_detector` | Zero active-runtime callers; upgrade-only use |
| `Pre30LayoutError` | (new) | `specify_cli.upgrade.pre30_guard` | Raised by boundary guard |
| `check_pre30_layout` | (new) | `specify_cli.upgrade.pre30_guard` | Called at command entry |

**Removed re-exports** (previously available, now gone from active runtime surface):

| Shim module | Symbol removed |
|-------------|---------------|
| `specify_cli.task_utils` | `is_legacy_format` |
| `specify_cli.task_utils.support` | `is_legacy_format` (import + `__all__` entry) |
| `specify_cli.tasks_support` | `is_legacy_format` |
| `specify_cli.scripts.tasks.task_helpers` | `is_legacy_format` (re-export + `__all__` entry) |

---

## Boundary Guard Module Contract

Module: `src/specify_cli/upgrade/pre30_guard.py`

```python
class Pre30LayoutError(Exception):
    """Raised when a pre-3.0 lane-directory layout is detected at the command boundary."""
    feature_path: Path
    detected_dirs: list[str]  # Which lane subdirs were found with .md files

def check_pre30_layout(feature_path: Path) -> None:
    """Check feature_path for pre-3.0 lane-directory layout.

    Raises Pre30LayoutError if tasks/{lane}/ subdirectories containing .md
    files are detected. Returns cleanly if the project is post-3.0.

    Does NOT auto-invoke spec-kitty upgrade (C-002).
    """
```

**Command handlers** that call `check_pre30_layout` catch `Pre30LayoutError` and emit:
- Stderr message: `"Pre-3.0 layout detected (tasks/{lane}/ directories or frontmatter lane state). Run \`spec-kitty upgrade\` to migrate before continuing."`
- Exit code: 1 (NFR-006)
- No file mutation occurs before the guard fires.

---

## Active Runtime "Flat-Layout-Only" Post-State

After IC-03, the following functions operate exclusively on flat `tasks/WP*.md` layout:

### `locate_work_package` in `task_utils/support.py`

```python
# Post-mission: no use_legacy branch
def locate_work_package(repo_root: Path, feature: str, wp_id: str) -> WorkPackage:
    ...
    tasks_root = feature_path / "tasks"
    # Flat layout only: search tasks/*.md
    for path in tasks_root.glob("*.md"):
        if wp_pattern.match(path.name):
            lane = get_lane_from_frontmatter(path, warn_on_missing=False)
            candidates.append((lane, path, tasks_root))
    ...
```

### `_iter_work_packages` in `acceptance/__init__.py`

```python
# Post-mission: pre-3.0 projects are skipped with log entry (FR-007)
def _iter_work_packages(repo_root: Path, feature: str) -> Iterable[WorkPackage]:
    from specify_cli.upgrade.legacy_detector import is_legacy_format
    feature_path = _wp_tasks_read_dir(repo_root, feature)
    tasks_dir = feature_path / "tasks"
    if not tasks_dir.exists():
        raise AcceptanceError(...)
    if is_legacy_format(feature_path):
        logger.warning(
            "Pre-3.0 layout detected for '%s': run `spec-kitty upgrade` to migrate. "
            "Acceptance scan skipped for this mission.", feature
        )
        return  # yield nothing; caller sees empty iterator
    # Flat layout only
    for path in sorted(tasks_dir.glob("*.md")):
        ...
```

### `list_command` in `tasks_cli.py`

```python
# Post-mission: guard fires before list_command is reached for pre-3.0 projects
# No use_legacy branch inside list_command
```

---

## Dashboard Invariant (FR-006)

The dashboard retains a thin read-only annotation path. It does NOT perform lane-directory iteration as part of any mutation. Post-mission invariants:

| Component | is_legacy_format usage | Mutation? |
|-----------|----------------------|-----------|
| `scanner._build_kanban_stats` | Routes read to `_build_legacy_kanban_stats` (stat reporting only) | No |
| `scanner._process_wp_file` | Annotates `lane = default_lane` vs. raises `CanonicalStatusNotFoundError` | No |
| `scanner._get_kanban_task_data_for_feature` | `use_legacy` branch **REMOVED**; returns early with `is_legacy: true` annotation | No (reads nothing from legacy dirs) |
| `handlers/features.py` | `feature["is_legacy"] = is_legacy_format(...)` annotation | No |
