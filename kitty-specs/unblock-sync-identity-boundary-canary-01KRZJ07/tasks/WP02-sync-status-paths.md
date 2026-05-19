---
work_package_id: WP02
title: '`sync status --check` path rendering (#1123)'
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: claude
history:
- at: '2026-05-19T08:46:23Z'
  actor: spec-kitty.tasks
  note: Generated initial WP prompt.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/sync.py
execution_mode: code_change
mission_slug: unblock-sync-identity-boundary-canary-01KRZJ07
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/cli/commands/sync.py
- tests/specify_cli/cli/commands/test_sync_status_check_paths.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

The profile defines your identity, governance scope, and boundaries for this work. Apply it for the entire duration of this work package.

## Objective

Render canonical file paths (queue DB path, executable path, source path, etc.) in `spec-kitty sync status --check` text output **verbatim, on a single line**, regardless of terminal width and regardless of whether stdout is a TTY. Path text must be byte-identical to the `--json` form. Move path rows out of the Rich `Table` and render them via plain `Console.print` so width-driven ellipsis (`…`) cannot truncate them again in the future.

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree is allocated per computed lane from `lanes.json` after `finalize-tasks` runs. Use `spec-kitty agent action implement WP02 --agent <name>` to enter the assigned workspace.

## Context

### What the bug is

`src/specify_cli/cli/commands/sync.py:1856-1863` builds a Rich `Table` (`expand=False`) for the "Identity Boundary" view. Rich's `Console()` defaults to 80 columns when stdout is not a TTY, and its default `overflow="ellipsis"` truncates long values with a U+2026 ellipsis. Machine consumers (the canary harness, but also pipes generally) see paths like `/private/var/folders/gj/bxx04…` that do not exist on disk. The `--json` form correctly emits the full path; the text form does not.

### Source contract

See [contracts/sync-status-check-rendering.md](../contracts/sync-status-check-rendering.md) — the split: tabular identity scalars stay in the Table, file paths render outside via plain `Console.print`.

### Why this approach (not `overflow="fold"`)

Decision `01KRZJ2HA6YH7HYB1XW1RRFTA4` (resolved: `print_paths_outside_table`) chose the structural fix. Rationale (from research R2): `fold` only wraps at column width; the next path field added to the boundary view re-introduces the same class of bug. Rendering paths outside the Table is the cleanest long-run answer and matches the `--json` contract.

## Subtasks

### T006 — Inventory path-bearing fields in boundary state

**Purpose**: Decide deterministically which rows become "path rows" outside the Table.

**Steps**:
1. Open `src/specify_cli/cli/commands/sync.py` and locate the function that builds `boundary_table` (≈line 1856). Trace what fields are added via `boundary_table.add_row(...)`.
2. Also inspect `src/specify_cli/sync/preflight.py` (`ForegroundIdentity`, `DaemonOwnerRecord`) and the JSON shape of `sync status --check --json` to identify every canonical file-path field. Expected set (verify against code):
   - active queue DB path
   - foreground executable path
   - foreground source path
   - daemon-owner executable path (when displayed)
   - daemon-owner source path (when displayed)
   - any other `Path` value displayed in the boundary view
3. Document the decision in a short module-level docstring (or an explanatory comment above the renderer) listing the path fields that render outside the Table. Keep it short — one or two lines.
4. Do **not** rename or relocate the source-of-truth fields on `ForegroundIdentity` / `DaemonOwnerRecord`. (Constraint C-004.)

**Files**: read-only walkthrough; doc comment in `sync.py` (~5 lines).

**Validation**:
- [ ] You can name each path field rendered today and its corresponding `--json` key.

### T007 — Refactor the renderer

**Purpose**: Split path rows out of the Rich `Table`. Path rows render via `Console.print(f"{label}: {path}")`; identity scalars stay in the Table.

**Steps**:
1. In the renderer, introduce a small helper or inline split:
   ```python
   path_rows: list[tuple[str, str]] = []
   scalar_rows: list[tuple[str, str]] = []
   for label, value in _iter_boundary_rows(state):
       if _is_path_field(label):  # or inspect by source field name
           path_rows.append((label, str(value)))
       else:
           scalar_rows.append((label, value))
   ```
   Prefer field-name-driven classification over heuristics (don't sniff for `/` in the string).
2. Render path rows first via `console.print(f"{label}: {path}")` — one path per line, no truncation, no overflow, no wrap. Verify they do **not** flow through any `Table` or width-bound renderer.
3. Render the remaining identity scalars through the existing Rich `Table` (keep `title="Identity Boundary"`, `box=None`, `expand=False`, etc.).
4. Preserve the existing color/style scheme for both paths and table rows; do not regress visual UX in wide TTYs.
5. Confirm the JSON form (`sync status --check --json`) is unchanged — this WP must not touch the JSON contract.

**Files**:
- `src/specify_cli/cli/commands/sync.py` (modify; ~30–50 changed lines around the renderer)

**Validation**:
- [ ] Running `spec-kitty sync status --check` in a wide TTY visually preserves the operator UX (Table for scalars, paths above/below as plain lines).
- [ ] Running `spec-kitty sync status --check | cat` shows every path on a single line, no `…`, no wrap.
- [ ] `sync status --check --json` output is byte-identical to pre-change.

### T008 — Regression tests

**Purpose**: Pin the four documented edge cases in CI.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_sync_status_check_paths.py`.
2. Implement the four tests from [contracts/sync-status-check-rendering.md](../contracts/sync-status-check-rendering.md) "Test surface":
   - **Non-TTY capture test**: invoke `sync status --check` under `typer.testing.CliRunner` (forces non-TTY). Parse stdout for `"Active queue DB:"` (or the chosen label). Assert the right-hand side equals the corresponding `--json` value.
   - **Long-path test**: monkeypatch the boundary state to seed a queue DB path >100 chars; assert no `…` (U+2026) appears in the rendered output and the path appears verbatim.
   - **Narrow-column test**: explicitly construct a `Console(width=40)` for the path renderer (or patch the console used by the command) and confirm paths still render on one line — i.e., they bypass the width-bound Table entirely.
   - **JSON parity test**: run both forms; compare every path field; assert byte equality.
3. Use existing fixture patterns in `tests/specify_cli/cli/commands/`.

**Files**:
- `tests/specify_cli/cli/commands/test_sync_status_check_paths.py` (new; ~120 lines)

**Validation**:
- [ ] All four tests pass after the refactor.
- [ ] On rc13 (pre-fix), at least the long-path and non-TTY tests FAIL.

### T009 — Smoke run

**Purpose**: Manual confirmation in a real shell that the canary's read path is fixed.

**Steps**:
1. Run:
   ```bash
   spec-kitty sync status --check | grep -F '…' && echo "FAIL" || echo "OK"
   ```
2. Run:
   ```bash
   spec-kitty sync status --check 2>/dev/null > /tmp/text.out
   spec-kitty sync status --check --json 2>/dev/null > /tmp/json.out
   # Pull the active_queue path from JSON and confirm it appears verbatim in the text
   python3 -c "import json,sys; print(json.load(open('/tmp/json.out'))['active_queue']['path'])" \
     | xargs -I{} grep -F "{}" /tmp/text.out
   ```
3. If grep returns the matching line, the contract holds.

**Files**: none.

**Validation**:
- [ ] No ellipsis (`…`) in the text output.
- [ ] The canonical `active_queue.path` from JSON appears verbatim in the text.

### T010 — Quality gate: mypy + ruff

**Purpose**: No type-check or lint regressions on the touched module.

**Steps**:
1. `mypy --strict src/specify_cli/cli/commands/sync.py`
2. `ruff check src/specify_cli/cli/commands/sync.py tests/specify_cli/cli/commands/test_sync_status_check_paths.py`
3. Address only failures attributable to your changes.

**Validation**:
- [ ] mypy clean.
- [ ] ruff clean.

## Definition of Done

- [ ] All five subtasks complete; each `[ ]` above checked.
- [ ] Spec-side requirements FR-004, FR-005, FR-006, FR-009 satisfied.
- [ ] No regression in existing `tests/specify_cli/cli/commands/test_sync*.py` (run them and confirm).
- [ ] JSON contract unchanged.

## Reviewer Guidance

- Read the renderer split first; confirm classification is driven by **field name / kind**, not by sniffing slashes in the string.
- Spot-check the long-path test: the seeded path must be the actual rendered value, no `…`, no wrap.
- Open a wide terminal and a piped capture side-by-side; both should preserve the canonical path verbatim.
- Confirm no source-of-truth field names (`package_version`, `queue_db_path`, etc.) were renamed (Constraint C-004).
