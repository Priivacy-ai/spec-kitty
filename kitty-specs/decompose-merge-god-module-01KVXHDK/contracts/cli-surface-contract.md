# Frozen CLI Surface Contract — `spec-kitty merge`

This is the **byte-identity contract** the refactor must preserve (FR-001, C-001,
INV-1). The golden CLI characterization test (WP01) captures this against the
pre-refactor module and re-asserts it after every seam move.

## Registration

- `merge` is a **single top-level Typer command** (not a sub-app), registered once at
  `cli/commands/__init__.py:216` via `app.command()(merge_module.merge)`.
- Decorated with `@require_main_repo`.
- One-line help (docstring): `Merge a lane-based feature into its target branch.`

## Flags (name / type / default / notes — all byte-identical post-refactor)

| Flag(s) | Type / default | Notes |
|---|---|---|
| `--strategy` | `MergeStrategy \| None`, default `None` → SQUASH | merge \| squash \| rebase |
| `--delete-branch / --keep-branch` | bool, default `True` | |
| `--remove-worktree / --keep-worktree` | bool, default `True` | |
| `--push` | bool, default `False` | |
| `--target` | str, default `None` | auto-detected |
| `--dry-run` | bool, default `False` | |
| `--json` | bool, default `False` | **dry-run-only** (enforced) |
| `--mission` | str, default `None` | mission slug |
| `--feature` | str, default `None`, **hidden** | legacy alias for `--mission` |
| `--resume` | bool, default `False` | |
| `--abort` | bool, default `False` | |
| `--context` | str, default `None` | **unused** compat flag (parsed then `del`'d) |
| `--keep-workspace` | bool, default `False` | **unused** compat flag (parsed then `del`'d) |
| `--allow-sparse-checkout` | bool, default `False` | logged override |
| `--yes / -y` | bool, default `False` | proceed past warnings |

## Behavioral contract points (must be pinned beyond flag parse)

1. **`--json` without `--dry-run`** → prints
   `{"spec_kitty_version", "error": "--json is currently supported with --dry-run only."}`
   and exits **1**.
2. **`--dry-run --json` payload** carries exactly these keys:
   `spec_kitty_version, mission_slug, target_branch, strategy, delete_branch,
   remove_worktree, push, mission_branch, lanes, would_assign_mission_number`.
3. **`--abort`** cleanup sequence (order preserved): state clear → global lock file
   unlink → legacy `merge-state.json` unlink → git-merge abort → coordination teardown.
4. **`--resume`** with no interrupted merge → `No interrupted merge to resume.` exit **1**.
5. **Unresolved mission slug** → `Mission slug could not be resolved. Use --mission <slug>.` exit **1**.
6. **Dry-run review-artifact gate** emits `REJECTED_REVIEW_ARTIFACT_CONFLICT` in both
   human and JSON output.

## Importable-symbol contract (FR-006 / INV-4)

The shim must keep these importable (via re-export) so the 3 src consumers + ~41 test
files need zero edits, and `__all__` ordering stays byte-stable:

- Src consumers: `merge` (command), `path_is_under_worktrees`, `_mark_wp_merged_done`.
- Test-imported internals: `_run_lane_based_merge`, `_run_lane_based_merge_locked`,
  `_assert_merged_wps_reached_done`, `_assert_merged_wps_done_on_target`,
  `_bake_mission_number_into_mission_branch`, `_check_mission_branch`,
  `_effective_push_requested`, `_enforce_canonical_status_history`,
  `_enforce_review_artifact_consistency`, `_has_transition_to`,
  `_reconcile_completed_wps_for_resume`, `_resolve_mission_slug`, `_resolve_target_branch`.

## Invariants referenced

- INV-1 CLI byte-identity · INV-4 `__all__` stability + re-export · INV-5 #1827
  baseline ordering · INV-8 `LINEAR_HISTORY_REJECTION_TOKENS` locked.
