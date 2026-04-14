---
work_package_id: WP03
title: Sparse-Checkout Remediation Module
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
phase: Phase 1 — Remediation
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/git/sparse_checkout_remediation.py
execution_mode: code_change
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- src/specify_cli/git/sparse_checkout_remediation.py
- tests/unit/git/test_sparse_checkout_remediation.py
tags: []
wp_code: WP03
---

# Work Package Prompt: WP03 — Sparse-Checkout Remediation Module

## Implementation Command

```bash
spec-kitty agent action implement WP03 --agent <your-agent-name> --mission 01KP54ZW
```

Depends on WP02. Rebase onto the lane where WP02 lands before starting.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- Lane allocation by `finalize-tasks`; resolve from `lanes.json`.

---

## Objective

Implement the doctor-offered remediation that disables sparse-checkout state across the primary repo and every lane worktree, refuses on a dirty tree, and produces a structured per-path report. The remediation is called only from WP04's doctor surface; it must have no other entry points.

---

## Context

- Research R8 enumerates the five per-path steps: `git sparse-checkout disable`, unset `core.sparseCheckout`, remove pattern file if present, `git checkout HEAD -- .`, verify `git status --porcelain` is clean.
- C-002 requires remediation to be user-consented and doctor-offered. This module provides the mechanism; WP04 provides the CLI surface and consent prompt.
- FR-005: remediation refuses on a dirty working tree at any target.
- NFR-003: 100% of successful remediations leave `git status` clean in every touched path.

---

## Subtask Guidance

### T013 — Remediation types

**Files**: `src/specify_cli/git/sparse_checkout_remediation.py` (new)

Define:

```python
@dataclass(frozen=True)
class SparseCheckoutRemediationResult:
    path: Path
    success: bool
    steps_completed: tuple[str, ...]
    error_step: str | None
    error_detail: str | None
    dirty_before_remediation: bool


@dataclass(frozen=True)
class SparseCheckoutRemediationReport:
    primary_result: SparseCheckoutRemediationResult
    worktree_results: tuple[SparseCheckoutRemediationResult, ...]

    @property
    def overall_success(self) -> bool:
        return self.primary_result.success and all(w.success for w in self.worktree_results)
```

Step name constants:
```python
STEP_SPARSE_DISABLE = "sparse_disable"
STEP_UNSET_CONFIG = "unset_config"
STEP_REMOVE_PATTERN_FILE = "remove_pattern_file"
STEP_REFRESH_WORKING_TREE = "refresh_working_tree"
STEP_VERIFY_CLEAN = "verify_clean"
```

---

### T014 — 5-step per-path remediation

**Files**: `src/specify_cli/git/sparse_checkout_remediation.py`

Implement the orchestrating function:

```python
def remediate(
    report: SparseCheckoutScanReport,
    *,
    interactive: bool,
    confirm: Callable[[str], bool] | None = None,
) -> SparseCheckoutRemediationReport:
    """Disable sparse-checkout state across primary + lane worktrees.

    Refuses if ANY target has a dirty tree. When interactive is True and
    confirm is provided, prompts once per affected path; a False return aborts
    remediation for that path. In non-interactive mode, proceeds without
    prompting (caller is responsible for having gotten consent).
    """
    # 1. Dirty-tree pre-check across ALL targets. If any dirty, build per-path
    #    results where dirty_before_remediation=True, success=False, and return.
    # 2. For each active target (primary first, then worktrees), run the 5 steps
    #    inside a single try block. Record the steps_completed progression.
    # 3. Aggregate into a SparseCheckoutRemediationReport.
```

Per-path 5-step sequence:
1. Run `git sparse-checkout disable` in the target path.
2. Run `git config --unset core.sparseCheckout` in the target path (tolerate "not set").
3. Remove the resolved pattern file (primary: `.git/info/sparse-checkout`; worktree: `<git-common-dir>/worktrees/<name>/info/sparse-checkout`). Use `Path.unlink(missing_ok=True)`.
4. Run `git checkout HEAD -- .` in the target path.
5. Run `git status --porcelain` in the target path; assert empty output.

If any step raises `subprocess.CalledProcessError` or non-zero returncode, capture the step name in `error_step`, the stderr in `error_detail`, and stop further steps for that path. `success=False` on that path. Continue with subsequent paths.

Dirty-tree pre-check: run `git status --porcelain` on each target; if any produces non-empty output, none of the paths are remediated and every result carries `dirty_before_remediation=True, success=False`.

Interactive confirm: if `interactive=True and confirm is not None`, before step 1 for each target call `confirm(target_path_str)`. If it returns False, skip that target with `success=False, error_step="user_declined"`.

**Validation**:
- Paths iterate primary FIRST, then worktrees in sorted order.
- Dirty-tree refusal is all-or-nothing across the scan report; no partial remediation when any target is dirty.
- The function is synchronous and pure enough to test with fixture repos.

---

### T015 — Unit tests [P]

**Files**: `tests/unit/git/test_sparse_checkout_remediation.py` (new)

Test cases:
- **Clean primary only, no worktrees**: all 5 steps run, result success, steps_completed has all 5.
- **Clean primary + 2 clean worktrees**: 3 results, all success.
- **Primary dirty**: NO remediation runs; all results have `dirty_before_remediation=True, success=False`.
- **One worktree dirty**: NO remediation runs anywhere; all-or-nothing rule.
- **Interactive confirm returns False for one worktree**: other paths remediate; the declined worktree has `error_step="user_declined", success=False`.
- **`git sparse-checkout disable` fails in one worktree**: that path's result has `error_step="sparse_disable"`, other paths complete.
- **Pattern file absent**: `remove_pattern_file` step still counts as completed (the absence is the desired state).
- **Verify-clean fails after refresh**: `error_step="verify_clean"`, `error_detail` carries the porcelain output.

Every test uses `tmp_path` fixtures that build sparse-configured repos with realistic `.git/info/sparse-checkout` content.

---

## Definition of Done

- [ ] New module `src/specify_cli/git/sparse_checkout_remediation.py` with the types and `remediate()` function.
- [ ] `remediate()` imports detection types from `specify_cli.git.sparse_checkout` (WP02).
- [ ] Dirty-tree refusal is all-or-nothing.
- [ ] Interactive mode respects the `confirm` callback on a per-path basis.
- [ ] Unit tests cover every listed case with ≥90% coverage.
- [ ] `mypy --strict` passes on the new module.
- [ ] `ruff check` passes.

## Risks

- **`git sparse-checkout disable` behaviour**: git documents this as both unsetting the config and refreshing the working tree. However, relying on it alone would couple us to a specific git version. The five explicit steps are deliberately redundant so each git version behaves correctly; the redundancy is documented in the ADR (WP09).
- **Pattern-file removal races**: if the user concurrently modifies the pattern file during remediation, the `unlink(missing_ok=True)` is tolerant. Remediation is not expected to defend against concurrent writers.

## Reviewer Guidance

- Verify that the function never writes outside the target paths. Grep for `Path("/")` or `/tmp/` in the implementation — should be absent.
- Verify `dirty_before_remediation` is set on EVERY result when the refusal fires, not only on the dirty path.
- Verify the step names in results exactly match the `STEP_*` constants; future code will look for these strings.
