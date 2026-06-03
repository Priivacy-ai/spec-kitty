---
work_package_id: WP02
title: Command Renderer Snapshot Refresh
dependencies: []
requirement_refs:
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
agent: claude
history:
- date: '2026-06-03'
  status: planned
agent_profile: implementer-ivan
authoritative_surface: tests/specify_cli/skills/
execution_mode: code_change
owned_files:
- tests/specify_cli/skills/test_command_renderer.py
- tests/specify_cli/skills/__snapshots__/codex/**
- tests/specify_cli/skills/__snapshots__/vibe/**
- src/doctrine/missions/mission-steps/**/implement/prompt.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

Apply the Lynn Cole engineering culture (DIRECTIVE_039) throughout: observe the failure first, fix only what is broken, verify with the full suite before marking done.

---

## Objective

Fix pre-existing snapshot drift in `tests/specify_cli/skills/test_command_renderer.py` for the `codex-implement` and `vibe-implement` test cases. Align the WP lifecycle dependency-gate wording in source templates to the canonical phrase `approved or done`. Regenerate the affected snapshots. The full 102-test suite must pass with zero failures.

## Branch Strategy

- **Planning base**: `main`
- **Merge target**: `main`
- **Your workspace**: allocated by `spec-kitty agent action implement WP02 --agent claude`; use the resolved worktree path from `lanes.json`.

## Context

During the 2026-06-03 harness audit, this command failed with pre-existing snapshot drift:

```bash
uv run pytest tests/specify_cli/skills/test_command_renderer.py
```

Observed failures:
- `test_snapshot[codex-implement]`
- `test_snapshot[vibe-implement]`

The drift is around WP lifecycle dependency-gate wording: `approved or done` vs `done`. The status model (`src/specify_cli/status/transitions.py`) is definitive: the dependency gate is satisfied when a WP is in `approved` **or** `done`. Using `done`-only would deadlock same-mission dependency chains. The canonical phrase is `approved or done`.

**Snapshot mechanism** (from `test_command_renderer.py`):
- Snapshots live at `tests/specify_cli/skills/__snapshots__/<agent>/<command>.SKILL.md`
- Source templates are at `src/doctrine/missions/mission-steps/<mission_type>/<step_id>/prompt.md`
- Update snapshots: `PYTEST_UPDATE_SNAPSHOTS=1 uv run pytest tests/specify_cli/skills/test_command_renderer.py`

---

## Subtask T007 — Run Snapshot Suite and Capture Failure Output

**Purpose**: Establish the actual failure before touching any file. Do not guess — observe.

**Steps**:
1. From the worktree root, run:
   ```bash
   uv run pytest tests/specify_cli/skills/test_command_renderer.py -x --tb=short 2>&1 | head -60
   ```
2. Record the exact diff shown (expected vs actual) for `codex-implement` and `vibe-implement`.
3. Note any other failing tests — if failures beyond these two exist, do not proceed until you understand whether they are pre-existing or new.

**Validation**:
- [ ] Failure output captured; you know exactly which lines differ and what the stale wording is

---

## Subtask T008 — Locate Snapshot Files and Source Implement Template

**Purpose**: Find all files that need to change before changing any of them.

**Steps**:
1. Find the snapshot files:
   ```bash
   ls tests/specify_cli/skills/__snapshots__/codex/implement.SKILL.md
   ls tests/specify_cli/skills/__snapshots__/vibe/implement.SKILL.md
   ```
2. Find the source template:
   ```bash
   find src/doctrine/missions/mission-steps -path "*/implement/prompt.md"
   ```
3. Read the relevant section of the source template — find the dependency gate wording.
4. Grep for `approved or done` and bare `done` in the template:
   ```bash
   grep -n "approved or done\|approved.*done\| done " <template_path>
   ```
5. Confirm whether the source template has the stale wording or whether it is already correct (in which case, only the snapshots need regenerating).

**Validation**:
- [ ] You know the exact file(s) that contain stale `done`-only wording
- [ ] You know whether the fix is in the source template, in the snapshots directly, or both

---

## Subtask T009 — Fix Source Template Wording

**Purpose**: If the source template contains stale `done`-only wording for the dependency gate, fix it to `approved or done`. This is the single source of truth; fixing it here means all agents' snapshots will regenerate correctly.

**Steps**:
1. If the source template (found in T008) says something like "all dependencies are in `done`" or "dependency must be `done`":
   - Change to "all dependencies are in `approved` or `done`" (or equivalent phrasing that preserves the sentence structure)
2. If the source template already says `approved or done`: skip this subtask and note it — only the snapshot regeneration in T010 is needed.
3. Do not change any other wording. This is a one-phrase fix.

**Validation**:
- [ ] `grep -n "approved or done" <template_path>` now matches the dependency-gate clause
- [ ] No other lines in the template changed

---

## Subtask T010 — Regenerate Snapshots

**Purpose**: Update the committed snapshot files to match the current (corrected) rendered output.

**Steps**:
1. Run with the update flag:
   ```bash
   PYTEST_UPDATE_SNAPSHOTS=1 uv run pytest tests/specify_cli/skills/test_command_renderer.py -k "codex-implement or vibe-implement" -v
   ```
2. Confirm the snapshot files were written:
   ```bash
   git diff --stat tests/specify_cli/skills/__snapshots__/
   ```
3. Inspect the diff: verify the only change is the dependency-gate wording (`done` → `approved or done` or equivalent). If the diff shows unrelated changes, investigate before proceeding.

**Validation**:
- [ ] `tests/specify_cli/skills/__snapshots__/codex/implement.SKILL.md` updated
- [ ] `tests/specify_cli/skills/__snapshots__/vibe/implement.SKILL.md` updated
- [ ] `git diff` of snapshot files shows only the expected wording change

---

## Subtask T011 — Verify Full Suite Passes

**Purpose**: Confirm the fix resolves the target failures and introduces no regressions. All 102 tests must pass.

**Steps**:
1. Run the full suite without the update flag:
   ```bash
   uv run pytest tests/specify_cli/skills/test_command_renderer.py -v 2>&1 | tail -20
   ```
2. Confirm: `102 passed, 0 failed`.
3. If any failures remain: investigate before marking done. Do not move on with a failing suite.

**Validation**:
- [ ] `pytest` output shows `102 passed`
- [ ] `test_snapshot[codex-implement]` passes
- [ ] `test_snapshot[vibe-implement]` passes
- [ ] No new failures introduced

---

## Definition of Done

- [ ] `uv run pytest tests/specify_cli/skills/test_command_renderer.py` exits 0 with 102 passed
- [ ] Snapshot files updated with canonical `approved or done` wording
- [ ] Source template (if stale) corrected — no other template lines changed
- [ ] `git diff` shows only targeted wording changes in template and/or snapshots
- [ ] No files outside `owned_files` modified

## Reviewer Guidance

Run `uv run pytest tests/specify_cli/skills/test_command_renderer.py` — must show 102 passed. Inspect `git diff tests/specify_cli/skills/__snapshots__/` — the only change should be `done` → `approved or done` (or equivalent) in the dependency-gate clause. Flag any other snapshot changes as out-of-scope and requiring explanation.
