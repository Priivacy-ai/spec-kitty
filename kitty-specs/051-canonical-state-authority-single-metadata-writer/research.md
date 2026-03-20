# Research: Canonical State Authority & Single Metadata Writer

**Feature**: 051-canonical-state-authority-single-metadata-writer
**Date**: 2026-03-18

## Research Question 1: Complete meta.json Write Site Inventory

### Decision
18 write sites across 11 files must be migrated to the new `feature_metadata.py` API.

### Findings

**Direct write sites (non-migration):**

| # | File | Lines | Function | Fields | Format | Bugs |
|---|------|-------|----------|--------|--------|------|
| 1 | `upgrade/feature_meta.py` | 33-39 | `write_feature_meta()` | Full dict | `indent=2, ensure_ascii=False` + `\n` | None (golden standard) |
| 2 | `acceptance.py` | 538 | `_check_and_accept_feature()` | accepted_at, accepted_by, acceptance_mode, accepted_from_commit, accept_commit, acceptance_history (cap 20) | `indent=2, sort_keys=True` + `\n` | Missing ensure_ascii |
| 3 | `scripts/tasks/acceptance_support.py` | 620 | `_check_and_accept_feature()` | Same as #2 | Same as #2 | Same as #2 |
| 4 | `orchestrator_api/commands.py` | 787 | `_handle_auto_accept_command()` | accepted_at, accepted_by | `indent=2, sort_keys=True` | **Missing trailing newline** |
| 5 | `cli/commands/implement.py` | 591 | `_detect_and_lock_vcs()` | vcs (jj→git conversion) | `indent=2` + `\n` | Missing sort_keys, ensure_ascii |
| 6 | `cli/commands/implement.py` | 601 | `_detect_and_lock_vcs()` | vcs, vcs_locked_at | `indent=2` + `\n` | Missing sort_keys, ensure_ascii |
| 7 | `scripts/tasks/tasks_cli.py` | 573 | `_save_merge_metadata()` | merge_history (cap 20), merged_at, merged_by, merged_into, merged_strategy, merged_push | `indent=2, sort_keys=True` + `\n` | Missing ensure_ascii |
| 8 | `scripts/tasks/tasks_cli.py` | 592 | `_finalize_merge_metadata()` | merged_commit, history[-1] mutation | `indent=2, sort_keys=True` + `\n` | Missing ensure_ascii |
| 9 | `cli/commands/agent/feature.py` | 632 | `specify_command()` | feature_number, slug, feature_slug, friendly_name, mission, target_branch, created_at | `indent=2` | **Missing trailing newline x2** |
| 10 | `cli/commands/agent/feature.py` | 658 | `specify_command()` | documentation_state init | `indent=2` | **Missing trailing newline** |

**doc_state.py sites (8 functions, all same pattern):**

| # | Function | Lines | Fields | Format |
|---|----------|-------|--------|--------|
| 11 | `set_iteration_mode()` | 101-103 | documentation_state.iteration_mode | `json.dump(meta, f, indent=2)` |
| 12 | `set_divio_types_selected()` | 135-137 | documentation_state.divio_types_selected | Same |
| 13 | `set_generators_configured()` | 179-181 | documentation_state.generators_configured | Same |
| 14 | `set_audit_metadata()` | 217-219 | documentation_state.last_audit_date, coverage_percentage | Same |
| 15 | `write_documentation_state()` | 283-285 | documentation_state (full replacement) | Same |
| 16 | `initialize_documentation_state()` | ~319 | documentation_state (new) | Via #15 |
| 17 | `update_documentation_state()` | ~352 | documentation_state (partial) | Via #15 |
| 18 | `ensure_documentation_state()` | 392-394 | documentation_state (migration) | Same |

**Migration files (keep as-is, not migrated):**

| File | Lines | Notes |
|------|-------|-------|
| `m_2_0_6_consistency_sweep.py` | 154 | Uses `write_feature_meta()` already |
| `m_0_13_8_target_branch.py` | 107-110 | Direct write, but migrations are frozen code |

### Rationale
Migrations are frozen (historical, shouldn't be modified). The 10 direct sites + 8 doc_state sites in active code are the migration targets.

### Alternatives Considered
- Migrating migration files too — rejected because migrations are immutable snapshots.

---

## Research Question 2: Activity Log Dependency in Acceptance

### Decision
Replace Activity Log parsing in acceptance with `materialize()` from `status/reducer.py`.

### Findings

**Current acceptance logic** (identical in `acceptance.py:355-392` and `acceptance_support.py:457-492`):

```python
# 1. Parse Activity Log entries from WP markdown body
entries = activity_entries(wp.body)
lanes_logged = {entry["lane"] for entry in entries}
latest_lane = entries[-1]["lane"] if entries else None

# 2. Three validation rules:
# Rule A: Activity Log must not be empty
if not entries:
    activity_issues.append(f"{wp_id}: Activity Log missing entries")

# Rule B: Current lane must appear in log
if wp.current_lane not in lanes_logged:
    activity_issues.append(f"{wp_id}: Activity Log missing entry for lane={wp.current_lane}")

# Rule C: If WP is done, latest entry must be done
if wp.current_lane == "done" and entries[-1]["lane"] != "done":
    activity_issues.append(f"{wp_id}: latest Activity Log entry not lane=done")
```

**Replacement using canonical state:**

```python
# Use materialize() to get canonical snapshot
from specify_cli.status.reducer import materialize
snapshot = materialize(feature_dir)

# Check all WPs are in done lane from canonical state
for wp_id in expected_wp_ids:
    wp_state = snapshot.get(wp_id)
    if wp_state is None:
        issues.append(f"{wp_id}: no canonical state found")
    elif wp_state.lane != "done":
        issues.append(f"{wp_id}: lane is {wp_state.lane}, expected done")
```

### Rationale
- Activity Log is a human narrative view, not a data source
- Canonical state (event log) is deterministic and immutable
- Removes fragile regex parsing dependency
- Makes acceptance logic 3 rules → 1 rule (is lane done?)

### Alternatives Considered
- Keep Activity Log as a secondary validation — rejected because it creates confusion about which source is authoritative.
- Read `status.json` directly instead of `materialize()` — viable but `materialize()` handles missing/stale snapshots by re-reducing.

---

## Research Question 3: TypedDict Schema for meta.json

### Decision
Use TypedDict for stable top-level fields with runtime validation at boundaries, following the existing `doc_state.py` precedent.

### Findings

**Existing precedent** (`doc_state.py:44-63`):
```python
class GeneratorConfig(TypedDict):
    name: Literal["sphinx", "jsdoc", "rustdoc"]
    language: str
    config_path: str

class DocumentationState(TypedDict):
    iteration_mode: Literal["initial", "gap_filling", "feature_specific"]
    divio_types_selected: List[str]
    generators_configured: List[GeneratorConfig]
    target_audience: str
    last_audit_date: Optional[str]
    coverage_percentage: float
```

**Proposed top-level TypedDict:**
```python
class FeatureMetaRequired(TypedDict):
    feature_number: str
    slug: str
    feature_slug: str
    friendly_name: str
    mission: str
    target_branch: str
    created_at: str

class FeatureMetaOptional(TypedDict, total=False):
    vcs: str
    vcs_locked_at: str
    accepted_at: str
    accepted_by: str
    acceptance_mode: str
    accepted_from_commit: str
    accept_commit: str
    acceptance_history: list[dict[str, Any]]
    merged_at: str
    merged_by: str
    merged_into: str
    merged_strategy: str
    merged_push: bool
    merged_commit: str
    merge_history: list[dict[str, Any]]
    documentation_state: dict[str, Any]
```

### Rationale
- `total=False` on optional fields handles the heterogeneous shape
- Required fields always present (validated on write)
- Unknown fields preserved via dict pass-through (forward compatibility)
- Follows doc_state.py pattern exactly

### Alternatives Considered
- Pydantic model — rejected (no Pydantic in codebase, adds dependency)
- Dataclass — rejected (meta.json is dict-shaped, callers already use dict)
- No TypedDict (pure dict) — rejected (loses static type checking benefits)

---

## Research Question 4: Atomic Write Pattern

### Decision
Use `os.replace()` with temp file in same directory.

### Findings

The `status/reducer.py` `materialize()` function does NOT currently use atomic writes — it calls `write_text()` directly. However, `os.replace()` is the standard Python pattern:

```python
import os
import tempfile

def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via temp-file-then-rename."""
    fd, tmp = tempfile.mkstemp(
        dir=path.parent,
        prefix=".meta-",
        suffix=".tmp",
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp, str(path))
    except BaseException:
        os.close(fd) if not os.get_inheritable(fd) else None
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
```

### Rationale
- `os.replace()` is atomic on POSIX and near-atomic on Windows
- Temp file in same directory ensures same filesystem (rename won't cross mount points)
- No new dependencies needed

### Alternatives Considered
- `shutil.move()` — not atomic, may copy across filesystems
- Write-in-place — current approach, risks corruption on interrupt

---

## Research Question 5: Formatting Standardization

### Decision
Standardize all meta.json writes to: `json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"`

### Findings

**Current inconsistencies:**
- `ensure_ascii`: 2 sites use `False`, 16 sites use default `True`
- `sort_keys`: 5 sites use `True`, 13 sites omit
- Trailing newline: 3 sites missing (`orchestrator_api`, `feature.py` x2)

**Proposed standard** (extends golden standard from `write_feature_meta()`):
- `indent=2` — already universal
- `ensure_ascii=False` — from existing helper, preserves Unicode
- `sort_keys=True` — deterministic diffs (addition over existing helper)
- `+ "\n"` — POSIX compliance (from existing helper)

### Rationale
- Extends existing convention rather than inventing new one
- Adding `sort_keys=True` to the existing helper's format is the only change
- Fixes 3 existing bugs (missing newlines)
- Makes git diffs cleaner (no key reordering noise)

### Alternatives Considered
- Keep `ensure_ascii=True` for broader compatibility — rejected because the existing helper already uses `False`, and Unicode is better for international branch/user names.
