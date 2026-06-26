---
work_package_id: WP01
title: Module relocation and guard scaffolding
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- C-002
- C-003
- NFR-003
- NFR-004
- NFR-006
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-retire-pre30-readers-01KW0MJE
base_commit: 2cbcb058177eee3a119018ebff570a71c737563b
created_at: '2026-06-26T01:07:12.735663+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: claude
shell_pid: '838253'
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/
create_intent:
- src/specify_cli/upgrade/legacy_detector.py
- src/specify_cli/upgrade/pre30_guard.py
- tests/upgrade/test_pre30_guard.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/upgrade/legacy_detector.py
- src/specify_cli/upgrade/pre30_guard.py
- tests/upgrade/test_pre30_guard.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 – Module relocation and guard scaffolding

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Copy `legacy_detector.py` into the `specify_cli.upgrade` namespace so that the boundary guard and dashboard can import from a stable upgrade-only location, then implement the command-boundary guard module (`pre30_guard.py`) with `Pre30LayoutError` and `check_pre30_layout`, and add a complete NFR-004 test suite covering all four guard cases.

## Context

The mission retires pre-3.0 lane-directory readers from the active runtime. The first step establishes the two new modules that all subsequent WPs depend on:

1. **`specify_cli/upgrade/legacy_detector.py`** — The existing `src/specify_cli/legacy_detector.py` moved into the `upgrade/` namespace. Downstream WPs (WP02–WP04) import `is_legacy_format` from this new path. The original file is deleted in WP03 after all active-runtime importers are removed.

2. **`specify_cli/upgrade/pre30_guard.py`** — New module: exports `Pre30LayoutError` and `check_pre30_layout`. This is the single hard-reject chokepoint wired into every mutation command entry in WP02. It must NOT auto-invoke `spec-kitty upgrade` (C-002); it only emits the canonical message and raises.

3. **`tests/upgrade/test_pre30_guard.py`** — Four tests covering the guard contract (NFR-004). These must be green before WP02 wires the guard.

**Sequence dependency**: This WP has no predecessors. WP02 depends on it for imports; WP03 and WP04 depend on it for the upgrade-namespace import path.

**Off-limits**: Do not touch `src/specify_cli/upgrade/migrations/m_0_9_0_frontmatter_only_lanes.py`, `runner.py`, or `registry.py`. The migration has its own private `_is_legacy_format` method and must not be modified (FR-009).

---

### Subtask T001: Copy legacy_detector.py to the upgrade namespace

**Purpose**: Place `is_legacy_format`, `get_legacy_lane_counts`, and `LEGACY_LANE_DIRS` under `specify_cli.upgrade.legacy_detector` so upgrade code and the new guard have a stable import path independent of the active runtime package surface.

**Steps**:
1. Read `src/specify_cli/legacy_detector.py` in full.
2. Write an identical copy to `src/specify_cli/upgrade/legacy_detector.py`. Make only these minimal changes:
   - Update the module docstring to say: `"""Legacy layout detector — migration/upgrade namespace. Canonical import: specify_cli.upgrade.legacy_detector."""`
   - Keep `__all__ = ["is_legacy_format", "get_legacy_lane_counts", "LEGACY_LANE_DIRS"]` unchanged.
   - Keep all function signatures, logic, and constants byte-for-byte identical to the original.
3. Confirm `src/specify_cli/upgrade/__init__.py` exists (it should; do NOT add the new symbols to it — they are accessed via direct module import only, not via the upgrade package `__init__`).
4. Run a quick sanity import check:
   ```bash
   python3 -c "from specify_cli.upgrade.legacy_detector import is_legacy_format, get_legacy_lane_counts, LEGACY_LANE_DIRS; print('OK')"
   ```

**Files**: `src/specify_cli/upgrade/legacy_detector.py` (new, ~80 lines matching the original)

**Validation**: Import check prints `OK`. `ruff check src/specify_cli/upgrade/legacy_detector.py` returns zero issues.

---

### Subtask T002: Create src/specify_cli/upgrade/pre30_guard.py

**Purpose**: Implement the command-boundary guard that WP02 will wire into every mutation command. It must detect pre-3.0 lane-directory layouts, raise a structured error, and never auto-invoke `spec-kitty upgrade`.

**Steps**:
1. Create `src/specify_cli/upgrade/pre30_guard.py` with the following surface:

   ```python
   """Command-boundary guard for pre-3.0 project layout detection.

   Raises Pre30LayoutError when a mission directory still uses lane-directory
   layout (tasks/planned/, tasks/doing/, etc.). Called after feature_path is
   resolved, before any WP mutation.
   """
   from __future__ import annotations

   from pathlib import Path

   from specify_cli.upgrade.legacy_detector import is_legacy_format

   __all__ = ["Pre30LayoutError", "check_pre30_layout"]

   _DETECTED_DIRS_ATTR = "detected_dirs"


   class Pre30LayoutError(Exception):
       """Raised when a pre-3.0 lane-directory layout is detected."""

       def __init__(self, feature_path: Path, detected_dirs: list[str]) -> None:
           self.feature_path = feature_path
           self.detected_dirs = detected_dirs
           lane_hint = detected_dirs[0] if detected_dirs else "tasks/{lane}/"
           super().__init__(
               f"Pre-3.0 layout detected (tasks/{lane_hint}/ directories or "
               f"frontmatter lane state).\n"
               f"Run `spec-kitty upgrade` to migrate before continuing."
           )


   def check_pre30_layout(feature_path: Path) -> None:
       """Raise Pre30LayoutError if feature_path has a pre-3.0 lane-directory layout.

       Call this after feature_path is resolved but before any WP mutation.
       Returns None if the layout is post-3.0 (no exception raised).
       """
       if not is_legacy_format(feature_path):
           return
       tasks_dir = feature_path / "tasks"
       detected = [
           d.name
           for d in tasks_dir.iterdir()
           if d.is_dir() and list(d.glob("*.md"))
       ]
       raise Pre30LayoutError(feature_path=feature_path, detected_dirs=detected)
   ```

2. Check that the function logic matches the contract in `kitty-specs/retire-pre30-readers-01KW0MJE/contracts/pre30-guard-contract.md`:
   - Error message contains `"Pre-3.0 layout detected"` — checked by tests.
   - Error message contains `"spec-kitty upgrade"` — checked by tests.
   - Function returns `None` cleanly for post-3.0 shapes.
   - No auto-invocation of upgrade (C-002).
   - At most 4 `Path.is_dir()` calls via `is_legacy_format` + 1 `iterdir()` — well under NFR-003 5 ms budget.

3. Run `ruff check src/specify_cli/upgrade/pre30_guard.py` and `mypy src/specify_cli/upgrade/pre30_guard.py`. Resolve any issues before proceeding.

**Files**: `src/specify_cli/upgrade/pre30_guard.py` (new, ~50 lines)

**Validation**: `ruff` + `mypy` pass with zero issues. Import:
```bash
python3 -c "from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout; print('OK')"
```

---

### Subtask T003: Create tests/upgrade/test_pre30_guard.py (NFR-004)

**Purpose**: Cover all four contract cases (T-GUARD-01..04) from `contracts/pre30-guard-contract.md` to satisfy NFR-004 (≥2 positive+negative guard tests).

**Steps**:
1. Create `tests/upgrade/test_pre30_guard.py`:

   ```python
   """Tests for the pre-3.0 layout boundary guard (NFR-004)."""
   from pathlib import Path

   import pytest

   from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout


   def _make_feature_dir(tmp_path: Path) -> Path:
       feature = tmp_path / "kitty-specs" / "001-test"
       feature.mkdir(parents=True)
       return feature


   def test_guard_rejects_pre30_project(tmp_path: Path) -> None:
       """T-GUARD-01: pre-3.0 lane directory with .md files raises Pre30LayoutError."""
       feature = _make_feature_dir(tmp_path)
       planned = feature / "tasks" / "planned"
       planned.mkdir(parents=True)
       (planned / "WP01.md").write_text("---\nwork_package_id: WP01\n---\n")

       with pytest.raises(Pre30LayoutError) as exc_info:
           check_pre30_layout(feature)

       message = str(exc_info.value)
       assert "Pre-3.0 layout detected" in message
       assert "spec-kitty upgrade" in message


   def test_guard_passes_post30_project(tmp_path: Path) -> None:
       """T-GUARD-02: flat tasks/WP01.md (post-3.0) passes without exception."""
       feature = _make_feature_dir(tmp_path)
       tasks = feature / "tasks"
       tasks.mkdir(parents=True)
       (tasks / "WP01.md").write_text("---\nwork_package_id: WP01\n---\n")

       check_pre30_layout(feature)  # Must not raise


   def test_guard_passes_empty_lane_directory(tmp_path: Path) -> None:
       """T-GUARD-03: empty lane directory (no .md files) passes without exception."""
       feature = _make_feature_dir(tmp_path)
       planned = feature / "tasks" / "planned"
       planned.mkdir(parents=True)
       (planned / ".gitkeep").write_text("")

       check_pre30_layout(feature)  # Must not raise


   def test_guard_passes_no_tasks_directory(tmp_path: Path) -> None:
       """T-GUARD-04: no tasks/ directory at all passes without exception."""
       feature = _make_feature_dir(tmp_path)
       check_pre30_layout(feature)  # Must not raise
   ```

2. Verify `tests/upgrade/` directory exists (it should; if not, create it with `__init__.py` if other tests in the directory use one; otherwise leave empty).

3. Run:
   ```bash
   pytest tests/upgrade/test_pre30_guard.py -v
   ```
   All four tests must pass.

**Files**: `tests/upgrade/test_pre30_guard.py` (new, ~55 lines)

**Validation**: `pytest tests/upgrade/test_pre30_guard.py -v` — 4 passed, 0 failed.

---

### Subtask T004: Quality gate — ruff + mypy on all new files

**Purpose**: Confirm zero new Ruff/mypy violations before WP02 builds on top of these modules.

**Steps**:
1. Run:
   ```bash
   ruff check src/specify_cli/upgrade/legacy_detector.py src/specify_cli/upgrade/pre30_guard.py
   mypy src/specify_cli/upgrade/legacy_detector.py src/specify_cli/upgrade/pre30_guard.py
   ```
2. Fix any issues found. Common pitfalls:
   - Missing type annotations on function parameters.
   - Import ordering (ruff `I001`).
   - Unused imports.
3. Re-run until both pass with zero issues.

**Files**: No new files; only quality checks on T001–T003 outputs.

**Validation**: Both commands exit 0 with no output (or only "Success: no issues found").

---

## Definition of Done

- [ ] `src/specify_cli/upgrade/legacy_detector.py` exists with identical logic to the original and updated module docstring.
- [ ] `python3 -c "from specify_cli.upgrade.legacy_detector import is_legacy_format, get_legacy_lane_counts, LEGACY_LANE_DIRS"` exits 0.
- [ ] `src/specify_cli/upgrade/pre30_guard.py` exists with `Pre30LayoutError` and `check_pre30_layout`.
- [ ] `check_pre30_layout` raises `Pre30LayoutError` for pre-3.0 fixtures; returns None for post-3.0.
- [ ] `Pre30LayoutError` message contains `"Pre-3.0 layout detected"` and `"spec-kitty upgrade"`.
- [ ] `tests/upgrade/test_pre30_guard.py` exists with T-GUARD-01..04 tests; all pass.
- [ ] `ruff check` and `mypy` pass with zero violations on both new modules.
- [ ] Off-limits files untouched: `m_0_9_0_frontmatter_only_lanes.py`, `runner.py`, `registry.py`.

## Risks

- **`upgrade/__init__.py` re-exports**: If it re-exports symbols in a way that creates circular imports when `pre30_guard.py` imports from `upgrade.legacy_detector`, adjust to direct module imports only. The guard does NOT need to appear in `upgrade/__init__.py`.
- **`is_legacy_format` semantics**: The guard reuses the exact predicate from the relocated detector. Confirm that `is_legacy_format` checks for `.md` files (not just directory existence) — empty lane directories must NOT trigger the guard (T-GUARD-03).

## Reviewer Guidance

- Verify the relocated `legacy_detector.py` is byte-for-byte identical in logic to the original (diff them).
- Verify `check_pre30_layout` calls `is_legacy_format` (not a reimplemented predicate).
- Confirm no auto-upgrade call (C-002) anywhere in `pre30_guard.py`.
- Confirm T-GUARD-03 and T-GUARD-04 (edge cases) exist and pass — empty lane dirs must not reject.

---

To implement: `spec-kitty agent action implement WP01 --agent claude`
