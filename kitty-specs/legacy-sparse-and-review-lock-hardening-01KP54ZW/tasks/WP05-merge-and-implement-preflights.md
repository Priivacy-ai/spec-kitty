---
work_package_id: WP05
title: Merge and Implement Preflights with Post-Merge Refresh and Invariant
dependencies:
- WP01
- WP02
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T020
- T021
- T023
- T038
phase: Phase 1 — Hard-block preflights
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/merge.py
execution_mode: code_change
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/cli/commands/agent/workflow.py
- tests/integration/sparse_checkout/test_merge_preflight_blocks.py
- tests/integration/sparse_checkout/test_merge_with_allow_override.py
- tests/integration/sparse_checkout/test_merge_refresh_and_invariant.py
- tests/integration/sparse_checkout/test_implement_preflight_blocks.py
tags: []
wp_code: WP05
---

# Work Package Prompt: WP05 — Merge and Implement Preflights with Post-Merge Refresh and Invariant

## Implementation Command

```bash
spec-kitty agent action implement WP05 --agent <your-agent-name> --mission 01KP54ZW
```

Depends on WP01 (backstop) and WP02 (detection + preflight API). Rebase onto the lane where they land.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- Lane allocation by `finalize-tasks`; resolve from `lanes.json`.

---

## Objective

Install the hard-block preflight in the two highest-blast-radius CLI commands (mission merge, agent action implement), wire the `--allow-sparse-checkout` override flag, and complete the merge-path data-loss defence with a post-merge working-tree refresh and invariant assertion.

After this WP, the #588 cascade is prevented at four distinct layers: preflight blocks entry (this WP), working-tree refresh aligns state (this WP), invariant assertion catches residual drift (this WP), and the commit-layer backstop catches anything that still leaks through (WP01).

---

## Context

- `_run_lane_based_merge_locked` in `src/specify_cli/cli/commands/merge.py:616` is the canonical merge flow. Lines 693–756 cover the merge-base capture through the status-events `safe_commit`.
- The `implement` action lives at `src/specify_cli/cli/commands/agent/workflow.py:454`.
- Constraints: FR-006, FR-007, FR-008, FR-009, FR-013, FR-014, C-006, C-007.
- Quickstart Flow 2 is the acceptance spec for the merge preflight; Flow 4 is the commit-layer backstop (WP01) that integrates with this WP's refresh + invariant.

---

## Subtask Guidance

### T006 — Post-merge working-tree refresh in `_run_lane_based_merge_locked`

**Files**: `src/specify_cli/cli/commands/merge.py`

**What**: After the mission-to-target merge at line 714 completes (`merge_mission_to_target`), and BEFORE the `safe_commit` at line 748, insert an explicit refresh:

```python
# After merge_mission_to_target succeeds.
# Refresh the primary checkout's working tree to match HEAD. This is a no-op
# on a clean full checkout, but in any configuration where HEAD advanced ahead
# of the working tree (legacy sparse-checkout being the observed case), this
# closes the gap before the housekeeping commit runs. See FR-013 and
# Priivacy-ai/spec-kitty#588.
_ret_checkout, _out_checkout, _err_checkout = run_command(
    ["git", "checkout", "HEAD", "--", "."],
    capture=True,
    check_return=False,
    cwd=main_repo,
)
if _ret_checkout != 0:
    console.print(f"[yellow]Warning:[/yellow] post-merge working-tree refresh failed: {_err_checkout.strip()}")
```

Do not abort on refresh failure; log and continue. The commit-layer backstop (WP01) will catch any residual issue.

---

### T007 — Post-merge `git status` invariant assertion

**Files**: `src/specify_cli/cli/commands/merge.py`

**What**: Immediately after T006's refresh and still BEFORE the `safe_commit`, check that the working tree now matches HEAD:

```python
_ret_status, _out_status, _err_status = run_command(
    ["git", "status", "--porcelain"],
    capture=True,
    check_return=False,
    cwd=main_repo,
)
unexpected = (_out_status or "").strip()
# Allow only the status-file deltas that the about-to-run safe_commit expects.
# We approximate this by tolerating status.events.jsonl and status.json shown
# as modified; anything else is an invariant violation.
expected_paths = {
    f"kitty-specs/{mission_slug}/status.events.jsonl",
    f"kitty-specs/{mission_slug}/status.json",
}
offending_lines = [
    line for line in unexpected.splitlines()
    if line.strip() and line[3:].strip() not in expected_paths
]
if offending_lines:
    console.print(
        "[red]Error:[/red] Post-merge working-tree invariant violated. "
        "The following paths diverge from HEAD unexpectedly:"
    )
    for line in offending_lines:
        console.print(f"  {line}")
    console.print(
        "\nThis usually indicates sparse-checkout or a stale lock file. Run\n"
        "  spec-kitty doctor --fix sparse-checkout\n"
        "before retrying the merge."
    )
    raise typer.Exit(1)
```

The commit-layer backstop (WP01) would catch the cascade even without this check, but the explicit invariant surfaces the problem with a merge-specific error message instead of a generic `SafeCommitBackstopError`.

---

### T020 — Merge preflight wiring + `--allow-sparse-checkout` flag

**Files**: `src/specify_cli/cli/commands/merge.py`

**What**:

1. Add `--allow-sparse-checkout` as a new option on the `merge` Typer command. Default `False`. Help text: `"Proceed even if legacy sparse-checkout state is detected. Use of this override is logged. Does not bypass the commit-time data-loss backstop."`
2. At the top of `_run_lane_based_merge` (before any git work), call:
   ```python
   from specify_cli.git.sparse_checkout import require_no_sparse_checkout

   require_no_sparse_checkout(
       repo_root=main_repo,
       command="spec-kitty agent mission merge",
       override_flag=allow_sparse_checkout,
       actor=_resolve_actor(),  # existing helper, or pass None
       mission_slug=mission_slug,
       mission_id=canonical_id,
   )
   ```
3. Catch `SparseCheckoutPreflightError` at the top-level CLI handler and surface it as a user-facing error with non-zero exit code. Do NOT write any merge state.

---

### T021 — Implement preflight wiring + `--allow-sparse-checkout` flag

**Files**: `src/specify_cli/cli/commands/agent/workflow.py`

**What**:

1. Add `--allow-sparse-checkout` as a new option on the `implement` command. Default `False`.
2. At the top of `implement()` (at line 454), BEFORE any worktree creation or state changes, call the same `require_no_sparse_checkout` from WP02:
   ```python
   require_no_sparse_checkout(
       repo_root=main_repo_root,
       command="spec-kitty agent action implement",
       override_flag=allow_sparse_checkout,
       actor=agent,
       mission_slug=mission_slug,
       mission_id=mission_id,
   )
   ```
3. Same error handling as T020.

---

### T023 — Integration tests [P]

**Files**: `tests/integration/sparse_checkout/test_merge_preflight_blocks.py`, `test_merge_with_allow_override.py`, `test_merge_refresh_and_invariant.py`, `test_implement_preflight_blocks.py`.

Test cases (one per file as implied):

- **test_merge_preflight_blocks**: fixture with active sparse state + a finalized mission. `spec-kitty agent mission merge --mission X` exits non-zero. No commit appears on the target branch. No MergeState file written.
- **test_merge_with_allow_override**: same fixture + `--allow-sparse-checkout`. Merge proceeds. The override log record (stable marker `spec_kitty.override.sparse_checkout`) is captured in `caplog`.
- **test_merge_refresh_and_invariant**: clean (non-sparse) fixture. Merge completes. Post-merge `git status --porcelain` in the primary is empty (aside from the about-to-commit status files which are swept by the immediately-following `safe_commit`).
- **test_implement_preflight_blocks**: active sparse state, planned WP ready to implement. `spec-kitty agent action implement WP01 --mission X` exits non-zero. No worktree created in `.worktrees/`.

Also add an assertion in test_merge_preflight_blocks that when `--force` is passed WITHOUT `--allow-sparse-checkout`, the preflight still blocks (FR-009, T038).

---

### T038 — `--force` does not bypass preflight [P]

**Files**: covered inline in the T023 tests.

**What**: Add `@pytest.mark.parametrize("force_flag", [[], ["--force"]])` on the merge-block test so it runs once without `--force` and once with. Both runs must produce the same block outcome.

Similarly for implement.

---

## Definition of Done

- [ ] Merge command accepts `--allow-sparse-checkout`; default False.
- [ ] Implement command accepts `--allow-sparse-checkout`; default False.
- [ ] Both commands call `require_no_sparse_checkout()` at entry before any state change.
- [ ] Merge has the post-merge refresh (T006) and invariant assertion (T007) between merge completion and the status-event `safe_commit` call.
- [ ] 4 integration test files exist and pass.
- [ ] `pytest tests/integration/sparse_checkout/test_merge_*.py tests/integration/sparse_checkout/test_implement_*.py` passes.
- [ ] `--force` is verified to NOT bypass the preflight in tests.
- [ ] Existing merge tests still pass.
- [ ] `mypy --strict` passes on both modified files.

## Risks

- **Preflight position in merge flow**: putting it too late risks partial state. It must run BEFORE `load_state`, BEFORE any file write. Review `_run_lane_based_merge` wrapper carefully — the preflight belongs above the `acquire_merge_lock` call.
- **Override log suppression**: tests must use `caplog` to capture, not stdout. Log records are sometimes filtered in test setups.
- **Invariant assertion false positives**: the invariant tolerates the two status files as expected deltas; if other callers of `_run_lane_based_merge_locked` expect additional pending files, the tolerance list needs to expand. Keep the list synchronized with the `files_to_commit` passed to the subsequent `safe_commit`.

## Reviewer Guidance

- Grep for `--force` in merge.py and workflow.py to confirm it does not bypass sparse-preflight.
- Verify that `SparseCheckoutPreflightError` surfaces with exit code != 0 (check the error-mapping in the CLI handler).
- Verify that the post-merge refresh runs BEFORE the status-events `safe_commit` at line 748.
- Confirm no MergeState file is written when the preflight aborts.
