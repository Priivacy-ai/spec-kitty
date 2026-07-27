---
work_package_id: WP01
title: Surface Resolver Implementation
dependencies: []
requirement_refs:
- C-003
- FR-001
- NFR-001
- NFR-003
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-merge-done-surface-resolver-01KTDVHZ
base_commit: 85864091d3faf01e11020111131edc326cc05c58
created_at: '2026-06-06T07:54:52.822624+00:00'
subtasks:
- T005
- T006
- T007
- T008
agent: "claude"
shell_pid: "32276"
history:
- date: '2026-06-06'
  event: created
  note: Initial task generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/surface_resolver.py
- tests/specify_cli/coordination/test_surface_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Tracker: Assign Issue

Before reading anything else, assign GitHub issue #1726 to yourself:

```bash
unset GITHUB_TOKEN && gh issue edit 1726 --repo Priivacy-ai/spec-kitty --add-assignee @me
```

---

## Objective

Create `src/specify_cli/coordination/surface_resolver.py` containing a single public function `resolve_status_surface(repo_root: Path, mission_slug: str) -> Path` that returns the canonical path to `status.events.jsonl` for a given mission, correctly routing to the coordination worktree when `coordination_branch` is set in the mission's `meta.json`.

This is the **foundation WP** for the fix. WP02 cannot start until this module exists and its tests pass.

---

## Context

The merge done-marking loop has a structural write/read surface divergence:
- **Write**: `emit_status_transition_transactional` routes to the coordination branch worktree when `coordination_branch` is set in `meta.json`.
- **Read**: `get_wp_lane` always reads from `primary_checkout/kitty-specs/<slug>/status.events.jsonl` via plain `Path.read_text()`.

The fix requires both sides to resolve the same surface. This WP creates the resolver; WP02 wires it into the callers and audits the full merge path.

**Key reference files** (read before implementing):
- `src/specify_cli/coordination/status_transition.py` lines ~318/334 — how `coordination_branch` is currently extracted from `meta.json` and used for routing
- `src/specify_cli/coordination/transaction.py` lines ~598, ~754–765 — how `BookkeepingTransaction` derives the coordination worktree path and `txn.feature_dir`
- `src/specify_cli/missions/meta.py` (or equivalent) — the existing `meta.json` reader utility

---

## Subtask T005: Study Existing Topology Resolution

**Purpose**: Before implementing, understand exactly how `coordination_branch` is extracted and how the coordination worktree path is derived today, so the new resolver matches those conventions precisely.

**Steps**:
1. Read `src/specify_cli/coordination/status_transition.py`. Find the function or block that reads `coordination_branch` from `meta.json`. Note:
   - Which field names it reads (`coordination_branch`, `mid8`, `mission_id`)
   - Which meta-reader utility it calls (e.g., `_read_meta`, `load_meta`, `read_meta_json`)
2. Read `src/specify_cli/coordination/transaction.py`. Find `BookkeepingTransaction.acquire` (~line 598). Note:
   - The exact worktree path convention: `.worktrees/<slug>-<mid8>-coord/` or similar
   - The `txn.feature_dir` assignment (~line 765): what kitty-specs subdirectory name is used inside the worktree
3. Check `src/specify_cli/coordination/__init__.py` to understand what is exported.

**Output**: Notes on the exact meta-reader call, field names, and worktree path convention to use in T006.

---

## Subtask T006: Implement `resolve_status_surface`

**Purpose**: Write the canonical surface resolver function.

**File**: `src/specify_cli/coordination/surface_resolver.py` (new file)

**Requirements**:
- Fully typed (`repo_root: Path`, `mission_slug: str`, return `Path`)
- Reads `coordination_branch` from `meta.json` using the same utility as `status_transition.py`
- If `coordination_branch` is set: returns the `status.events.jsonl` path inside the coordination worktree, using the exact same path convention as `BookkeepingTransaction` (from T005 notes)
- If absent: returns `repo_root / KITTY_SPECS_DIR / mission_slug / "status.events.jsonl"` (primary checkout path)
- Raises the same exception type as other meta-read failures when `meta.json` is missing or unparseable
- No side effects (does not create worktrees, does not write files, does not call git)
- mypy --strict compatible (no `Any`, no `Optional` unless required)

**Constants** (define at module top):
```python
_KITTY_SPECS_DIR = "kitty-specs"
_STATUS_EVENTS_FILENAME = "status.events.jsonl"
```

**Implementation skeleton**:
```python
from pathlib import Path
# import the correct meta-reader (from T005 research)

def resolve_status_surface(repo_root: Path, mission_slug: str) -> Path:
    """Return the canonical status.events.jsonl path for the given mission."""
    meta = _load_meta(repo_root, mission_slug)  # use the utility found in T005
    coord_branch: str | None = meta.get("coordination_branch")
    if coord_branch:
        mid8: str = meta["mission_id"][:8]
        worktree_name = f"{mission_slug}-{mid8}-coord"  # verify against T005
        return (
            repo_root / ".worktrees" / worktree_name
            / _KITTY_SPECS_DIR / mission_slug
            / _STATUS_EVENTS_FILENAME
        )
    return repo_root / _KITTY_SPECS_DIR / mission_slug / _STATUS_EVENTS_FILENAME
```

**Important**: Verify the worktree subdirectory name and the kitty-specs subdirectory inside the worktree against `coordination/transaction.py` (T005). The exact naming convention must match or the path will be wrong.

Export the function from `src/specify_cli/coordination/__init__.py` if that module uses `__all__`.

**NFR-003 compliance note**: Add a short module docstring to `surface_resolver.py` noting that it is the sole canonical surface-resolution path. No secondary fallback or parallel path should be introduced — any future contributor who reaches for an alternative resolution mechanism should see this constraint stated explicitly at the module level.

---

## Subtask T007: Write Unit Tests

**Purpose**: Prove the resolver returns the correct path for both topologies and raises on missing meta.

**File**: `tests/specify_cli/coordination/test_surface_resolver.py` (new file)

**Test cases**:

1. **No coordination branch (legacy path)**:
   ```python
   def test_resolve_primary_checkout_when_no_coord_branch(tmp_path):
       # Write meta.json with no coordination_branch field
       # Call resolve_status_surface(tmp_path, "my-mission")
       # Assert returns tmp_path / "kitty-specs" / "my-mission" / "status.events.jsonl"
   ```

2. **With coordination branch (new topology)**:
   ```python
   def test_resolve_coordination_worktree_when_coord_branch_set(tmp_path):
       # Write meta.json with coordination_branch set and mission_id present
       # Call resolve_status_surface(tmp_path, "my-mission")
       # Assert returns tmp_path / ".worktrees" / "<slug>-<mid8>-coord"
       #                         / "kitty-specs" / "my-mission" / "status.events.jsonl"
       # (verify mid8 derivation from mission_id[:8])
   ```

3. **Missing meta.json**:
   ```python
   def test_raises_when_meta_missing(tmp_path):
       # Do not create meta.json
       # Assert resolve_status_surface raises the appropriate exception
   ```

4. **Explicit mid8 derivation check**:
   ```python
   def test_mid8_is_first_8_chars_of_mission_id(tmp_path):
       # meta.json with mission_id = "01KTDVHZKGCHCW6HQ4V577PNES", coordination_branch set
       # Assert path contains "my-mission-01KTDVHZ-coord"
   ```

---

## Subtask T008: Validate Quality Gates

**Purpose**: Ensure the new module meets all project quality requirements before WP02 depends on it.

**Steps**:

1. **mypy --strict**:
   ```bash
   .venv/bin/mypy --strict src/specify_cli/coordination/surface_resolver.py
   ```
   Fix any type errors. Common issues: `meta.get("coordination_branch")` returns `Any` if meta is `dict[str, Any]` — add explicit type annotation or cast.

2. **ruff check**:
   ```bash
   .venv/bin/ruff check src/specify_cli/coordination/surface_resolver.py
   ```

3. **Circular import check**:
   ```bash
   .venv/bin/python -c "from specify_cli.coordination.surface_resolver import resolve_status_surface; print('OK')"
   ```
   If ImportError, check whether `coordination/` imports from any module that imports back into `coordination/`.

4. **Run new tests**:
   ```bash
   .venv/bin/pytest tests/specify_cli/coordination/test_surface_resolver.py -v
   ```
   All four tests must pass.

5. **NFR-001 performance note**: `resolve_status_surface` performs a single `meta.json` read (O(1) filesystem stat). No benchmark is needed — confirm by inspection that no git I/O or network calls are made. This satisfies the sub-millisecond-per-WP threshold by design.

6. **Existing test suite** (sanity check — not full regression, that's WP02):
   ```bash
   .venv/bin/pytest tests/specify_cli/coordination/ -v
   ```

---

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per `lanes.json` when `spec-kitty implement WP01` is run

**To implement this WP**:
```bash
spec-kitty agent action implement WP01 --agent claude
```

---

## Definition of Done

- [ ] `src/specify_cli/coordination/surface_resolver.py` exists with `resolve_status_surface` function
- [ ] Function returns primary-checkout path when `coordination_branch` absent
- [ ] Function returns coordination-worktree path when `coordination_branch` present
- [ ] Function raises on missing `meta.json`
- [ ] `tests/specify_cli/coordination/test_surface_resolver.py` exists with 4+ tests, all passing
- [ ] `mypy --strict` passes on the new module
- [ ] `ruff check` passes
- [ ] No circular imports introduced
- [ ] Changes committed

---

## Risks

- **Worktree path convention mismatch**: The coordination worktree path must exactly match what `BookkeepingTransaction` creates. Read `transaction.py` carefully in T005 — do not guess the convention.
- **Meta reader API**: Different parts of the codebase use different meta-reading utilities. Use the same one as `status_transition.py` to ensure consistency.
- **`mission_slug` vs kitty-specs subdirectory name**: Verify whether the subdirectory inside the coordination worktree's `kitty-specs/` uses `mission_slug` or a different name (e.g., with `mid8` appended). This is critical for path correctness.

## Activity Log

- 2026-06-06T08:02:17Z – claude – shell_pid=3186 – Moved to for_review
- 2026-06-06T08:02:25Z – claude – shell_pid=32276 – Started review via action command
