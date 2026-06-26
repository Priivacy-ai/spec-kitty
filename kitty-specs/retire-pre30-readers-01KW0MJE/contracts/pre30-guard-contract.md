# Contract: Pre-3.0 Layout Boundary Guard

**Mission**: retire-pre30-readers-01KW0MJE  
**Covers**: FR-001, FR-002, C-002, NFR-003, NFR-004, NFR-006  
**Module**: `specify_cli.upgrade.pre30_guard`

---

## Detection Predicate

A project is classified as pre-3.0 if and only if:

```
∃ lane ∈ {"planned", "doing", "for_review", "done"}:
  Path(feature_path / "tasks" / lane).is_dir()
  AND len(list(Path(feature_path / "tasks" / lane).glob("*.md"))) > 0
```

This is identical to the existing `is_legacy_format()` predicate, which is preserved in `specify_cli.upgrade.legacy_detector` after relocation (C-003).

**Note**: Empty lane directories (containing only `.gitkeep`) are NOT classified as pre-3.0. This matches the existing behaviour — empty lane subdirs do not trigger the guard.

---

## Trigger Point

The guard is called **after** mission slug resolution and `feature_path` is resolved, but **before** any WP file is read or any event is emitted.

Pseudo-code for a Typer command entry:

```python
repo_root = locate_project_root()
mission_slug = _find_mission_slug(...)
feature_path = resolve_feature_dir_for_mission(repo_root, mission_slug)

# Boundary guard — must be the next call
try:
    check_pre30_layout(feature_path)
except Pre30LayoutError as e:
    _output_error(json_output, str(e))
    raise typer.Exit(1)

# ... rest of command body
```

For `tasks_cli.py` (standalone scripts layer), the equivalent is:

```python
from specify_cli.upgrade.pre30_guard import check_pre30_layout, Pre30LayoutError

feature_path = resolve_feature_dir_for_mission(repo_root, feature)
try:
    check_pre30_layout(feature_path)
except Pre30LayoutError as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
```

---

## Exit Code

**1** (non-zero, NFR-006). Consistent with typer's `raise typer.Exit(1)` pattern used throughout `agent/tasks.py`.

---

## Error Message

The guard must produce a message that satisfies FR-002 (instructs user to run `spec-kitty upgrade`, identifies what triggered the rejection):

```
Pre-3.0 layout detected (tasks/{lane}/ directories or frontmatter lane state).
Run `spec-kitty upgrade` to migrate before continuing.
```

Where `{lane}` is replaced with the first detected lane subdirectory (e.g., `tasks/planned/`).

**Acceptance criteria** (from spec Scenario A):
- Message contains the phrase `"Pre-3.0 layout detected"` — checked by NFR-004 tests
- Message contains `"spec-kitty upgrade"` — checked by NFR-004 tests
- Delivered to stderr (not stdout) so it does not pollute JSON piping

---

## Mutation Guard (NFR-006)

The guard fires **before** any of the following occur:
- `locate_work_package` call
- `emit_status_transition` call
- `append_activity_log` call
- Any `WP.path.write_text` call
- Any `run_git` call

Implementation enforcement: in `agent/tasks.py`, `check_pre30_layout` is called before the `wp = locate_work_package(...)` line in each `@app.command` body. No test fixture for a pre-3.0 project should observe any file modification after the guard fires.

---

## Cold-Start Performance (NFR-003)

`check_pre30_layout` calls `is_legacy_format(feature_path)` which performs at most 4 `Path.is_dir()` calls and 1 `Path.glob("*.md")` call per lane directory on a warm filesystem. Measured overhead is well under 1 ms on a local SSD. The ≤5 ms budget is satisfied.

The guard is not called on every filesystem event or import — only once per command invocation.

---

## Contracts NOT in scope

- The guard does NOT check frontmatter-lane state (pre-3.0 frontmatter `lane` values). It detects lane-directory layout only. Frontmatter-lane detection is a pre-2.0 concept already handled by `spec-kitty upgrade --migration 0.9.0_frontmatter_only_lanes`.
- The guard does NOT suppress or replace the normal "no kitty-specs found" / "mission not found" errors — those fire before the guard, at mission resolution time.

---

## Testing Contract (NFR-004)

File: `tests/upgrade/test_pre30_guard.py`

| Test ID | Description | Fixture | Expected outcome |
|---------|-------------|---------|-----------------|
| T-GUARD-01 | **Positive**: pre-3.0 project rejected | `tmp_path/kitty-specs/001-test/tasks/planned/WP01.md` exists | `Pre30LayoutError` raised; `str(e)` contains `"Pre-3.0 layout detected"` and `"spec-kitty upgrade"` |
| T-GUARD-02 | **Negative**: post-3.0 project passes | `tmp_path/kitty-specs/001-test/tasks/WP01.md` exists (flat) | No exception raised; function returns `None` |
| T-GUARD-03 | **Edge**: empty lane directory passes | `tmp_path/kitty-specs/001-test/tasks/planned/` exists but contains no `.md` files | No exception raised |
| T-GUARD-04 | **Edge**: no tasks directory passes | `tmp_path/kitty-specs/001-test/` has no `tasks/` directory | No exception raised |

T-GUARD-01 and T-GUARD-02 are the mandatory NFR-004 pair. T-GUARD-03 and T-GUARD-04 are recommended for full branch coverage.
