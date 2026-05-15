---
work_package_id: WP03
title: merge --dry-run review artifact gate parity
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-010
- C-002
- C-004
planning_base_branch: fix/workflow-parity-988-989-991
merge_target_branch: fix/workflow-parity-988-989-991
branch_strategy: Planning artifacts for this mission were generated on fix/workflow-parity-988-989-991. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/workflow-parity-988-989-991 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
agent: claude
history:
- at: '2026-05-14T18:15:00Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/merge.py
execution_mode: code_change
mission_slug: workflow-parity-988-989-991-01KRKTT5
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py
role: implementer
tags: []
---

# WP03 — `merge --dry-run` review-artifact gate parity (#991)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Wire the existing real-merge review-artifact consistency gate into the `spec-kitty merge --dry-run` path so that when real merge would emit `REJECTED_REVIEW_ARTIFACT_CONFLICT`, the dry-run does the same — in both human and JSON output. Do not introduce any new false-positive blockers on the success path.

## Context

- Bug report: https://github.com/Priivacy-ai/spec-kitty/issues/991
- Spec: [../spec.md](../spec.md) (see FR-007..FR-009, FR-010, C-002, C-004)
- Research: [../research.md](../research.md) (`#991` section)
- Contract: [../contracts/merge-dry-run-review-artifact.md](../contracts/merge-dry-run-review-artifact.md)

### Code map (read these first)

- Diagnostic constant: `src/specify_cli/post_merge/review_artifact_consistency.py:12` — `REJECTED_REVIEW_ARTIFACT_CONFLICT`
- Detection gate: `src/specify_cli/post_merge/review_artifact_consistency.py:53` — `find_rejected_review_artifact_conflicts()`
- Diagnostic emitter: `src/specify_cli/post_merge/review_artifact_consistency.py:101` — `review_artifact_conflict_diagnostic()`
- Merge CLI command: `src/specify_cli/cli/commands/merge.py` (look for the `--dry-run` flag handling and the existing real-merge gate invocation)

## Branch Strategy

- Planning/base branch: `fix/workflow-parity-988-989-991`
- Final merge target: `fix/workflow-parity-988-989-991` → ultimately `main`
- Shared feature branch (no per-lane worktree).

## Subtasks

### T007 — Extract `run_review_artifact_consistency_preflight()` helper

**Purpose**: Single implementation path shared by real merge and dry-run (FR-007).

**Steps**:
1. In `src/specify_cli/post_merge/review_artifact_consistency.py`, add a new function:
   ```python
   def run_review_artifact_consistency_preflight(
       feature_dir: Path,
       *,
       feature_slug: str,
   ) -> ReviewArtifactPreflightResult:
       """Run find_rejected_review_artifact_conflicts and wrap the result.

       Returns a structured result with .passed, .conflicts, and .diagnostics
       so both real merge and dry-run can render them identically.
       """
   ```
2. Define `ReviewArtifactPreflightResult` (frozen dataclass) with at least:
   - `passed: bool`
   - `conflicts: tuple[ReviewArtifactConflict, ...]` (reuse whatever type `find_rejected_review_artifact_conflicts` already returns)
   - `diagnostics: tuple[dict, ...]` — one per conflict, built via the existing `review_artifact_conflict_diagnostic()` emitter so the wire shape is identical to real merge.
3. Update the existing real-merge call site in `src/specify_cli/cli/commands/merge.py` to consume the helper instead of calling `find_rejected_review_artifact_conflicts` directly. Behavior must be byte-for-byte equivalent for real merge.

**Files**:
- `src/specify_cli/post_merge/review_artifact_consistency.py` (modify, ~50 lines added)
- `src/specify_cli/cli/commands/merge.py` (refactor real-merge gate call, ~10 lines)

**Validation**:
- [ ] `uv run pytest tests/post_merge/test_review_artifact_consistency.py tests/merge/test_merge_post_merge_invariant.py -q` is green (no regression in real-merge gate).
- [ ] `mypy --strict src/specify_cli/post_merge` passes.

### T008 — Invoke preflight in `merge --dry-run` path

**Purpose**: Fire the gate in dry-run so the diagnostic shows up in both human and JSON output.

**Steps**:
1. In `src/specify_cli/cli/commands/merge.py`, find the branch where `--dry-run` is true and the merge preview is computed.
2. **Before** computing the preview, call `run_review_artifact_consistency_preflight(feature_dir, feature_slug=...)`.
3. If `result.passed is False`:
   - For JSON output (`--json`): include `result.diagnostics` under the same top-level key the real merge uses (typically a `blockers` or `errors` array — match real merge exactly).
   - For human output: print a clearly-labeled `REJECTED_REVIEW_ARTIFACT_CONFLICT` block listing each offending WP and review-cycle file path. Reuse the same renderer real merge uses if one exists; otherwise call `review_artifact_conflict_diagnostic()` to build the strings.
   - Exit non-zero, matching the real-merge exit code for the same condition.
4. If `result.passed is True`: fall through to the existing dry-run preview logic with no behavior change (spec C-002).

**Files**:
- `src/specify_cli/cli/commands/merge.py` (modify, ~40 lines)

**Validation**:
- [ ] Smoke: build a temporary mission fixture (WP01 lane `approved`, latest review-cycle `verdict: rejected`); run `spec-kitty merge --mission <slug> --dry-run --json`; assert exit code non-zero and the JSON contains `REJECTED_REVIEW_ARTIFACT_CONFLICT`.
- [ ] Smoke: same fixture without `--json` produces the labeled human diagnostic on stderr/stdout.

### T009 — Regression test

**Purpose**: Lock the new dry-run behavior.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py`.
2. Use the existing scaffolding from `tests/post_merge/test_review_artifact_consistency.py` to build the mission fixture (it already knows how to set up a `tasks/WP01-*/review-cycle-N.md` with a `rejected` verdict).
3. Test cases:
   - `test_dry_run_json_emits_rejected_review_artifact_conflict`: Fixture with rejected latest cycle on approved WP. Run `merge --dry-run --json`. Assert exit code non-zero AND parsed JSON contains `REJECTED_REVIEW_ARTIFACT_CONFLICT` in the same top-level key real merge uses.
   - `test_dry_run_human_emits_rejected_review_artifact_conflict`: Same fixture, no `--json`. Assert exit code non-zero AND stdout/stderr contains `REJECTED_REVIEW_ARTIFACT_CONFLICT`.
   - `test_dry_run_success_path_unchanged`: Fixture with all `approved` cycles. Run `merge --dry-run --json`. Assert exit code zero AND payload contains the normal merge preview structure (and does NOT contain `REJECTED_REVIEW_ARTIFACT_CONFLICT`).

**Files**:
- `tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py` (new, ~160 lines)

**Validation**:
- [ ] All three tests fail before T008 lands (first two expect non-zero; today it's zero).
- [ ] All three tests pass after T008.
- [ ] `uv run pytest tests/specify_cli/cli/commands/test_merge.py tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py tests/post_merge/test_review_artifact_consistency.py tests/merge/test_merge_post_merge_invariant.py -q` is green.

## Definition of Done

- [ ] Three subtasks complete and committed.
- [ ] Contract [../contracts/merge-dry-run-review-artifact.md](../contracts/merge-dry-run-review-artifact.md) is satisfied.
- [ ] `uv run pytest tests/specify_cli/cli/commands/test_merge.py tests/post_merge/test_review_artifact_consistency.py tests/specify_cli/cli/commands/test_review.py tests/specify_cli/cli/commands/review/test_mode_resolution.py -q` is green (canonical four files).
- [ ] `uv run mypy --strict src/specify_cli/cli/commands/merge.py src/specify_cli/post_merge` is green.

## Risks & Mitigations

- **R-1**: Refactoring real-merge call site introduces a regression.
  - **Mitigation**: T007 keeps real-merge byte-for-byte equivalent; the existing `test_merge_post_merge_invariant.py` covers it; run that suite immediately after T007.
- **R-2**: Differing top-level key shapes between real merge JSON and dry-run JSON.
  - **Mitigation**: Reuse the same renderer / same diagnostic emitter for both paths so the JSON shape is by-construction identical.

## Reviewer guidance

- Verify a single function (the new preflight helper) is the only caller of `find_rejected_review_artifact_conflicts` (besides the existing tests).
- Diff the dry-run failure JSON against a real-merge failure JSON for the same mission state — they should match in shape.
- Confirm dry-run's success path is untouched by running it on a clean mission and comparing pre/post output.
