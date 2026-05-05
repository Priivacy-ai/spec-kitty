# Tasks: 3.2.0 Release Blocker Cleanup

**Mission**: `stable-320-release-blocker-cleanup-01KQW4DF` (`01KQW4DF`)
**Branch**: `main` → merges to `main`
**Generated**: 2026-05-05

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-----------|----|----------|
| T001 | Create `src/specify_cli/sync/diagnostics.py` — `SyncDiagnosticCode` enum, `emit_sync_diagnostic()`, `classify_sync_error()` | WP01 | [P] |
| T002 | Refactor `sync/daemon.py`: replace lock-error console output with `emit_sync_diagnostic(LOCK_UNAVAILABLE, …)` | WP01 | |
| T003 | Refactor `sync/batch.py`: replace final-sync error output with `emit_sync_diagnostic(classified_code, …)` | WP01 | |
| T004 | Write `tests/sync/test_final_sync_diagnostics.py` — 6 regression test cases | WP01 | |
| T005 | Extend `tests/e2e/test_mission_create_clean_output.py` — assert JSON stdout valid + stderr ≤1 diagnostic | WP01 | |
| T006 | Add `TaskIdResolutionOutcome`, `TaskIdResolutionFormat`, `TaskIdResult` types to `tasks.py` | WP02 | [P] |
| T007 | Implement `_resolve_inline_subtasks()` — regex for `Subtasks: T001, T002` pattern | WP02 | |
| T008 | Implement `_resolve_wp_id()` — delegate to `emit_status_transition()` for bare WP IDs | WP02 | |
| T009 | Update `mark_status()` to use strategy stack and collect per-ID results | WP02 | |
| T010 | Update `--json` output to `results` + `summary` shape per `contracts/mark-status-result.schema.json` | WP02 | |
| T011 | Write regression tests: 8 cases covering inline, WP-ID, mixed, not-found, backwards-compat formats | WP02 | |
| T012 | Create `spec-kitty-end-to-end-testing/support/nested_env.py` with `NestedEnvResult` + `create_nested_env()` | WP03 | [P] |
| T013 | Write `spec-kitty-end-to-end-testing/tests/test_nested_env_helper.py` — 4 unit tests for helper | WP03 | |
| T014 | Update `spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py` to use `create_nested_env()` | WP03 | |
| T015 | Add `_check_mission_branch(mission_slug, repo_root)` function to `merge.py` | WP04 | [P] |
| T016 | Integrate `_check_mission_branch()` into `--dry-run` path (before JSON output) | WP04 | |
| T017 | Integrate `_check_mission_branch()` into real merge path (before irreversible git operations) | WP04 | |
| T018 | Write `tests/merge/test_merge_preflight_mission_branch.py` — 5 regression test cases | WP04 | |

**Total**: 18 subtasks across 4 work packages. All WPs are fully independent (no cross-WP dependencies).

---

## Work Package 01 — Sync Final-Sync Diagnostic Hygiene (#952)

**Priority**: High — release blocker
**Estimated prompt size**: ~280 lines
**Dependencies**: none
**Parallelizable with**: WP02, WP03, WP04 (all independent)
**Prompt file**: [tasks/WP01-sync-final-sync-diagnostic-hygiene.md](tasks/WP01-sync-final-sync-diagnostic-hygiene.md)

**Goal**: Eliminate leakage of final-sync error messages into successful command output.
Introduce `sync/diagnostics.py` as the sole stderr-routing authority for final-sync failures,
deduplicate messages per invocation, and classify into 5 named categories.

**Included subtasks**:
- [ ] T001 Create `src/specify_cli/sync/diagnostics.py` — `SyncDiagnosticCode` enum, `emit_sync_diagnostic()`, `classify_sync_error()` (WP01)
- [ ] T002 Refactor `sync/daemon.py`: replace lock-error output with `emit_sync_diagnostic(LOCK_UNAVAILABLE, …)` (WP01)
- [ ] T003 Refactor `sync/batch.py`: replace final-sync error output with `emit_sync_diagnostic(classified_code, …)` (WP01)
- [ ] T004 Write `tests/sync/test_final_sync_diagnostics.py` — 6 regression tests (WP01)
- [ ] T005 Extend `tests/e2e/test_mission_create_clean_output.py` — JSON stdout valid + stderr ≤1 diagnostic (WP01)

**Implementation sketch**: Create the new diagnostics module first (T001), then refactor daemon.py and batch.py call sites (T002-T003), then write tests (T004-T005). The deduplication state is module-level set; the emit function is the single write path.

**Success criteria**: A lifecycle command that completes successfully with SaaS sync unavailable exits 0, stdout is valid JSON (in --json mode), and stderr carries at most one `sync_diagnostic severity=warning` line.

**Risks**: Refactoring daemon.py and batch.py may expose other error paths that currently use the same console output — scope each change to final-sync paths only (DIRECTIVE_024: locality of change).

---

## Work Package 02 — mark-status Non-Checkbox ID Resolution (#783)

**Priority**: High — release blocker
**Estimated prompt size**: ~350 lines
**Dependencies**: none
**Parallelizable with**: WP01, WP03, WP04 (all independent)
**Prompt file**: [tasks/WP02-mark-status-non-checkbox-id-resolution.md](tasks/WP02-mark-status-non-checkbox-id-resolution.md)

**Goal**: Extend `mark_status()` with two new ID resolution strategies (inline `Subtasks:` references
and bare WP IDs via the status event log), a per-ID result structure, and a conformant `--json` output schema.

**Included subtasks**:
- [ ] T006 Add `TaskIdResolutionOutcome`, `TaskIdResolutionFormat`, `TaskIdResult` types to `tasks.py` (WP02)
- [ ] T007 Implement `_resolve_inline_subtasks()` — regex for `Subtasks: T001, T002` pattern (WP02)
- [ ] T008 Implement `_resolve_wp_id()` — delegate to `emit_status_transition()` for bare WP IDs (WP02)
- [ ] T009 Update `mark_status()` to use strategy stack and collect per-ID results (WP02)
- [ ] T010 Update `--json` output to `results` + `summary` per `contracts/mark-status-result.schema.json` (WP02)
- [ ] T011 Write 8 regression tests covering all formats + edge cases (WP02)

**Implementation sketch**: Add types first (T006), implement each resolver (T007, T008), wire into the strategy stack in `mark_status()` (T009), update the JSON output shape (T010), write tests last (T011). The strategy stack executes in order: checkbox → pipe-table → inline-subtasks → wp-id; first match wins.

**Success criteria**: `mark-status T001` on a tasks.md with `Subtasks: T001` succeeds and returns `outcome: updated`. `mark-status WP02 --status done` emits a status transition via the event log. Unknown IDs return `not_found`. Existing checkbox/pipe-table behavior is unchanged.

**Risks**: The WP-ID strategy calls `emit_status_transition()` which may raise if the transition is invalid (e.g., WP already in terminal state). Catch and translate to `not_found` or `already_satisfied` as appropriate, not an unhandled exception.

---

## Work Package 03 — Cross-Repo E2E uv-Managed Python (#975)

**Priority**: High — release blocker
**Estimated prompt size**: ~200 lines
**Dependencies**: none
**Parallelizable with**: WP01, WP02, WP04 (all independent)
**Prompt file**: [tasks/WP03-e2e-uv-managed-python.md](tasks/WP03-e2e-uv-managed-python.md)

**Goal**: Fix the `contract_drift_caught` E2E scenario failing before product behavior by
replacing `venv.create()` with a uv-aware helper that detects the runtime and
either uses `uv venv` or falls back gracefully.

**Note**: This WP operates in the `spec-kitty-end-to-end-testing` repository, not in `spec-kitty`.

**Included subtasks**:
- [ ] T012 Create `spec-kitty-end-to-end-testing/support/nested_env.py` with `NestedEnvResult` + `create_nested_env()` (WP03)
- [ ] T013 Write `spec-kitty-end-to-end-testing/tests/test_nested_env_helper.py` — 4 unit tests (WP03)
- [ ] T014 Update `spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py` to use `create_nested_env()` (WP03)

**Implementation sketch**: Write the helper module first (T012), test it (T013), then swap it into the scenario (T014). The helper must detect uv via `shutil.which("uv")` and use `uv venv` if available; skip/xfail if neither method works.

**Success criteria**: `scenarios/contract_drift_caught.py` runs to product assertions (not SKIPPED or ERROR) on a macOS machine with uv-managed Python. The drift detection assertion still fires correctly.

**Risks**: uv detection heuristic edge cases — uv on PATH but not the Python manager. The fallback to stdlib venv covers this; if stdlib venv also fails, the skip/xfail guard fires. This is safe behavior.

---

## Work Package 04 — merge --dry-run Mission Branch Preflight (#976)

**Priority**: High — release blocker
**Estimated prompt size**: ~250 lines
**Dependencies**: none
**Parallelizable with**: WP01, WP02, WP03 (all independent)
**Prompt file**: [tasks/WP04-merge-dry-run-mission-branch-preflight.md](tasks/WP04-merge-dry-run-mission-branch-preflight.md)

**Goal**: Add `_check_mission_branch()` to `merge.py` and call it from both the dry-run
and real merge paths so a missing `kitty/mission-<slug>` branch surfaces as a structured
`ready: false` blocker before any irreversible operation.

**Included subtasks**:
- [ ] T015 Add `_check_mission_branch(mission_slug, repo_root)` function to `merge.py` (WP04)
- [ ] T016 Integrate `_check_mission_branch()` into `--dry-run` path (before JSON output) (WP04)
- [ ] T017 Integrate `_check_mission_branch()` into real merge path (before irreversible operations) (WP04)
- [ ] T018 Write `tests/merge/test_merge_preflight_mission_branch.py` — 5 regression tests (WP04)

**Implementation sketch**: Implement the standalone helper function first (T015), reusing the existing `_has_branch_ref()` helper. Insert the check into dry-run path (T016), then real merge path (T017). The dry-run JSON output shape is defined in `contracts/merge-dry-run-blocker.schema.json`. Write tests last (T018).

**Success criteria**: `merge --dry-run --json` with a missing mission branch returns `{"ready": false, "blocker": "missing_mission_branch", ...}`. Same check fires in real merge. Happy path (branch exists) is unaffected.

**Risks**: Inserting the preflight check must not break the existing happy-path tests in `tests/merge/`. Confirm by running the full merge test suite after T016/T017. The `_has_branch_ref()` helper already exists and is tested — reuse it.

---

## Smoke Evidence

After all WPs are implemented, capture evidence in:
`kitty-specs/stable-320-release-blocker-cleanup-01KQW4DF/smoke-evidence.md`

Following the verification commands in `quickstart.md`.
