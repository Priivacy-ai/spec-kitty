---
work_package_id: WP04
title: Gate Function & CLI Wiring
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-002
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
agent: "claude:opus:implementer:implementer"
shell_pid: "68605"
history:
- date: '2026-04-13'
  author: claude
  action: created
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/bulk_edit/gate.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/workflow.py
- tests/specify_cli/bulk_edit/test_gate.py
- tests/specify_cli/cli/commands/test_implement_bulk_edit.py
- tests/specify_cli/cli/commands/test_review_bulk_edit.py
tags: []
---

# WP04 — Gate Function & CLI Wiring

## Objective

Create the `ensure_occurrence_classification_ready()` gate function and wire it into both the implement and review CLI paths. Also wire the inference warning into the implement path for non-bulk-edit missions. This is the core enforcement mechanism.

## Context

- **Spec**: FR-002 (workflow inserts required step), FR-006 (implementation blocked), FR-007/FR-008 (review validates), FR-009/FR-010 (inference warning)
- **Plan**: Integration Points 1, 2, 3 — Implement Guard, Review Guard, Inference Warning
- **Data model**: Gate decision flows in `data-model.md` — implement gate and review gate diagrams
- **Research**: RQ-1 (insert between planning validation and workspace allocation), RQ-4 (single function reused)
- **Key insight**: The gate goes in `implement.py` between `_ensure_planning_artifacts_committed_git()` (~line 464) and `resolve_workspace_for_wp()` (~line 465). In `workflow.py` review(), it goes after lane state validation (~line 1296).

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

---

### Subtask T008: Create gate.py — ensure_occurrence_classification_ready()

**Purpose**: Implement the reusable guard function that checks occurrence map readiness.

**Steps**:

1. Create `src/specify_cli/bulk_edit/gate.py`

2. Implement the main gate function:
   ```python
   from pathlib import Path
   from specify_cli.mission_metadata import load_meta
   from specify_cli.bulk_edit.occurrence_map import (
       load_occurrence_map,
       validate_occurrence_map,
       check_admissibility,
   )

   @dataclass(frozen=True)
   class GateResult:
       passed: bool
       change_mode: str | None
       errors: list[str]
       warnings: list[str]

   def ensure_occurrence_classification_ready(
       feature_dir: Path,
   ) -> GateResult:
       """Check if a bulk_edit mission has a valid occurrence map.

       Returns GateResult. For non-bulk-edit missions, always passes.
       """
   ```

3. Gate logic (follows data-model.md decision flow):
   - Load meta.json via `load_meta(feature_dir)`
   - If meta is None or `change_mode` not in meta or `change_mode != "bulk_edit"`: return `GateResult(passed=True, change_mode=None, ...)`
   - Load occurrence map via `load_occurrence_map(feature_dir)`
   - If None (file missing): return `GateResult(passed=False, errors=["Occurrence map required for bulk_edit missions. Create kitty-specs/<mission>/occurrence_map.yaml with target, categories, and actions."])`
   - Validate structure via `validate_occurrence_map(omap)`
   - If invalid: return `GateResult(passed=False, errors=validation.errors)`
   - Check admissibility via `check_admissibility(omap)`
   - If not admissible: return `GateResult(passed=False, errors=admissibility.errors)`
   - Otherwise: return `GateResult(passed=True, change_mode="bulk_edit", ...)`

4. Add a Rich-formatted error display helper:
   ```python
   def render_gate_failure(result: GateResult, console: Console) -> None:
       """Display gate failure with Rich formatting."""
       panel = Panel(
           "\n".join(f"  - {e}" for e in result.errors),
           title="[bold red]Bulk Edit Gate: BLOCKED[/]",
           subtitle="Create or fix occurrence_map.yaml before proceeding",
           border_style="red",
       )
       console.print(panel)
   ```

**Files**: `src/specify_cli/bulk_edit/gate.py`

**Validation**:
- [ ] Non-bulk-edit missions pass immediately
- [ ] Bulk-edit missions without occurrence_map.yaml are blocked
- [ ] Bulk-edit missions with invalid occurrence map are blocked with specific errors
- [ ] Bulk-edit missions with valid, admissible map pass

---

### Subtask T009: Wire Gate into implement.py

**Purpose**: Insert the occurrence classification gate into the implement action flow.

**Steps**:

1. Open `src/specify_cli/cli/commands/implement.py`

2. Add import at top:
   ```python
   from specify_cli.bulk_edit.gate import (
       ensure_occurrence_classification_ready,
       render_gate_failure,
   )
   ```

3. Insert the gate check in the `implement()` function, inside the `tracker.start("validate")` try-block, between `_ensure_planning_artifacts_committed_git()` and `resolve_workspace_for_wp()` (~line 464-465):
   ```python
   # Bulk edit occurrence classification gate (FR-006)
   gate_result = ensure_occurrence_classification_ready(feature_dir)
   if not gate_result.passed:
       render_gate_failure(gate_result, console)
       raise typer.Exit(1)
   ```

4. The gate must fire BEFORE workspace allocation — if it fails, no workspace is created, no lane is claimed, no status transition occurs.

**Files**: `src/specify_cli/cli/commands/implement.py`

**Validation**:
- [ ] Gate fires after planning artifacts committed, before workspace resolution
- [ ] Non-bulk-edit missions are unaffected (zero overhead beyond one load_meta call)
- [ ] Blocked missions exit cleanly with Rich error panel
- [ ] No workspace created or status changed when gate blocks

---

### Subtask T010: Wire Gate into workflow.py Review Function

**Purpose**: Insert the occurrence classification gate into the review action flow.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/workflow.py`

2. Add import:
   ```python
   from specify_cli.bulk_edit.gate import (
       ensure_occurrence_classification_ready,
       render_gate_failure,
   )
   ```

3. Insert the gate in the `review()` function, after lane state validation (the block that checks `for_review` / `in_progress` status), before the review claim transition:
   ```python
   # Bulk edit occurrence classification gate (FR-007, FR-008)
   gate_result = ensure_occurrence_classification_ready(feature_dir)
   if not gate_result.passed:
       render_gate_failure(gate_result, console)
       raise typer.Exit(1)
   ```

4. The review gate uses the exact same function — no review-specific logic in v1.

**Files**: `src/specify_cli/cli/commands/agent/workflow.py`

**Validation**:
- [ ] Review for non-bulk-edit missions is unaffected
- [ ] Review for bulk-edit missions with valid map proceeds normally
- [ ] Review for bulk-edit missions without map is rejected

---

### Subtask T011: Wire Inference Warning into Implement Path

**Purpose**: When a mission is NOT marked as bulk_edit, check if spec content suggests it should be.

**Steps**:

1. In `src/specify_cli/cli/commands/implement.py`, add import:
   ```python
   from specify_cli.bulk_edit.inference import scan_spec_file
   ```

2. After the gate check (which already returned early for non-bulk-edit missions with `passed=True`), add the inference check when `gate_result.change_mode is None`:
   ```python
   # Inference warning for potentially unmarked bulk edits (FR-009)
   if gate_result.change_mode is None:
       inference = scan_spec_file(feature_dir)
       if inference.triggered:
           matched = ", ".join(f"'{p}' ({w}pt)" for p, w in inference.matched_phrases)
           console.print(Panel(
               f"This mission's spec contains language suggesting a bulk edit "
               f"(score: {inference.score}/{inference.threshold}):\n"
               f"  Matched: {matched}\n\n"
               f"If this IS a bulk edit, set change_mode to 'bulk_edit' in meta.json.\n"
               f"If it is NOT, re-run with --acknowledge-not-bulk-edit to suppress.",
               title="[bold yellow]Bulk Edit Inference Warning[/]",
               border_style="yellow",
           ))
           if not acknowledge_not_bulk_edit:
               raise typer.Exit(1)
   ```

3. Add `--acknowledge-not-bulk-edit` option to the implement command signature:
   ```python
   acknowledge_not_bulk_edit: bool = typer.Option(
       False,
       "--acknowledge-not-bulk-edit",
       help="Suppress the bulk edit inference warning for this mission",
   )
   ```

4. Pass this flag through to the implement function.

**Files**: `src/specify_cli/cli/commands/implement.py`

**Validation**:
- [ ] No warning for missions without rename/migration language
- [ ] Warning displayed for spec content scoring >= 4
- [ ] `--acknowledge-not-bulk-edit` suppresses the warning
- [ ] Without flag, implement exits with code 1 when warning triggered

---

### Subtask T012: Integration Tests for Implement and Review Gates

**Purpose**: End-to-end tests that verify the gate blocks and passes correctly via the CLI.

**Steps**:

1. Create `tests/specify_cli/cli/commands/test_implement_bulk_edit.py`

2. Implement gate integration tests (use `tmp_path` for isolated project setup):

   Setup helper: Create a minimal mission directory with `meta.json`, `spec.md`, `tasks/WP01.md`, and `lanes.json`. Use existing test helpers where available.

   Test cases:
   - `test_implement_non_bulk_edit_passes_gate`: Mission without change_mode proceeds normally (may fail later in workspace allocation — that's OK, gate passed)
   - `test_implement_bulk_edit_no_map_blocks`: Mission with `change_mode: "bulk_edit"` but no `occurrence_map.yaml` exits with code 1 and error message
   - `test_implement_bulk_edit_invalid_map_blocks`: Mission with bulk_edit and incomplete occurrence map exits with code 1
   - `test_implement_bulk_edit_valid_map_passes`: Mission with bulk_edit and valid occurrence map proceeds past gate
   - `test_implement_inference_warning_blocks`: Mission without change_mode but rename language in spec exits with code 1
   - `test_implement_inference_warning_acknowledged`: Same spec but with `--acknowledge-not-bulk-edit` proceeds

3. Create `tests/specify_cli/cli/commands/test_review_bulk_edit.py`

   Test cases:
   - `test_review_non_bulk_edit_passes_gate`
   - `test_review_bulk_edit_no_map_blocks`
   - `test_review_bulk_edit_valid_map_passes`

4. Use `typer.testing.CliRunner` or subprocess-based approach matching existing CLI tests.

**Files**: `tests/specify_cli/cli/commands/test_implement_bulk_edit.py`, `tests/specify_cli/cli/commands/test_review_bulk_edit.py`

**Validation**:
- [ ] All integration tests pass
- [ ] Tests are isolated (tmp_path, no shared state)
- [ ] Tests cover both blocking and passing scenarios

## Definition of Done

- [ ] `gate.py` implements reusable `ensure_occurrence_classification_ready()`
- [ ] Gate wired into implement.py at correct location
- [ ] Gate wired into review in workflow.py at correct location
- [ ] Inference warning wired into implement path with `--acknowledge-not-bulk-edit` flag
- [ ] Rich error panels displayed for failures
- [ ] Integration tests cover all gate scenarios
- [ ] Non-bulk-edit missions experience zero workflow impact
- [ ] mypy --strict passes
- [ ] All tests pass

## Risks

- **Medium**: `implement.py` and `workflow.py` are large, frequently-modified files. Careful insertion point selection avoids merge conflicts. The changes are small (< 10 lines each) and well-localized.
- **Low**: The `--acknowledge-not-bulk-edit` flag adds a new CLI option. Verify it doesn't conflict with existing options.

## Reviewer Guidance

- **Critical**: Verify the gate insertion point in `implement.py` is between `_ensure_planning_artifacts_committed_git()` and `resolve_workspace_for_wp()` — wrong placement could allow workspace creation before the gate fires
- Verify the gate insertion in `workflow.py` is after lane validation, before review claim
- Check that non-bulk-edit missions are truly zero-cost (early return before any file I/O beyond load_meta)
- Confirm inference warning only fires when change_mode is NOT set (not for bulk_edit missions)
- Test error messages are actionable (tell the user exactly what to do)

## Activity Log

- 2026-04-13T19:12:32Z – claude:opus:implementer:implementer – shell_pid=68605 – Started implementation via action command
- 2026-04-13T19:18:30Z – claude:opus:implementer:implementer – shell_pid=68605 – Ready for review
- 2026-04-13T19:19:11Z – claude:opus:implementer:implementer – shell_pid=68605 – Review passed: gate correctly wired between planning validation and workspace allocation. --acknowledge-not-bulk-edit flag added. Review gate in workflow.py. 7 tests.
- 2026-04-13T19:32:10Z – claude:opus:implementer:implementer – shell_pid=68605 – Done override: Feature merged to main
