# Tasks: Legacy Sparse-Checkout Cleanup and Review-Lock Hardening

**Mission**: `legacy-sparse-and-review-lock-hardening-01KP54ZW`
**Mission ID**: `01KP54ZWEEPCC2VC3YKRX1HT8W`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Date**: 2026-04-14

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- Lane worktrees will be computed by `finalize-tasks` and materialized by `spec-kitty agent action implement` per work package.

## Work Package Overview

| WP | Title | Subtasks | Est. Lines | Depends On | Execution Mode |
|---|---|---|---|---|---|
| WP01 | Commit-layer data-loss backstop in `safe_commit` | 5 | ~400 | — | code_change |
| WP02 | Sparse-checkout detection primitive, session warning, and preflight API | 5 | ~420 | — | code_change |
| WP03 | Sparse-checkout remediation module (primary + lane worktrees) | 3 | ~300 | WP02 | code_change |
| WP04 | Doctor finding and `--fix sparse-checkout` action | 3 | ~280 | WP02, WP03 | code_change |
| WP05 | Merge + implement preflights with post-merge refresh and invariant | 5 | ~450 | WP01, WP02 | code_change |
| WP06 | Review-lock fixes, release lifecycle, and session-warning in task commands | 6 | ~480 | WP02 | code_change |
| WP07 | Per-worktree exclude writer, external session-warning sites, once-per-process test | 3 | ~300 | WP02, WP06 | code_change |
| WP08 | FR-020 approve-output source-lane anomaly investigation | 2 | ~220 | — | planning_artifact |
| WP09 | ADR, CHANGELOG, Kent diagnostic comment | 3 | ~260 | WP01, WP02, WP05, WP06, WP07 | code_change |

Total: 35 subtasks across 9 WPs.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add `UnexpectedStagedPath` and `SafeCommitBackstopError` types | WP01 |  | [D] |
| T002 | Implement `assert_staging_area_matches_expected()` helper | WP01 |  | [D] |
| T003 | Wire backstop inside `safe_commit` after stage, before commit | WP01 |  | [D] |
| T004 | Unit tests for backstop diff logic | WP01 | [D] |
| T005 | Regression test that reproduces the #588 cascade | WP01 | [D] |
| T006 | Post-merge working-tree refresh in `_run_lane_based_merge_locked` | WP05 |  | [D] |
| T007 | Post-merge `git status` invariant assertion | WP05 |  | [D] |
| T009 | `SparseCheckoutState` and `SparseCheckoutScanReport` types | WP02 |  | [D] |
| T010 | `scan_path()` and `scan_repo()` pure detection functions | WP02 |  | [D] |
| T011 | `warn_if_sparse_once()` session-warning emitter + module flag | WP02 |  | [D] |
| T012 | Unit tests for detection primitive covering R6 | WP02 | [D] |
| T013 | Remediation types: per-path result + aggregate report | WP03 |  | [D] |
| T014 | 5-step per-path remediation composed across primary + worktrees | WP03 |  | [D] |
| T015 | Unit tests for remediation outcomes | WP03 | [D] |
| T016 | Doctor finding surfacing sparse-checkout scan | WP04 |  | [D] |
| T017 | `doctor --fix sparse-checkout` action with CI/non-TTY handling | WP04 |  | [D] |
| T018 | Integration tests for doctor finding and remediation flow | WP04 | [D] |
| T019 | `SparseCheckoutPreflightError` + `require_no_sparse_checkout()` API | WP02 |  | [D] |
| T020 | Merge preflight wiring + `--allow-sparse-checkout` flag + log record | WP05 |  | [D] |
| T021 | Implement preflight wiring + `--allow-sparse-checkout` flag + log record | WP05 |  |
| T023 | Integration tests for merge + implement preflights, override, refresh, invariant | WP05 | [P] |
| T024 | Session-warning call sites inside `agent/tasks.py` commands | WP06 |  | [D] |
| T025 | Once-per-process integration test (NFR-005) | WP07 | [D] |
| T026 | Add `.spec-kitty/` + `.kittify/` deny-list filter to `_validate_ready_for_review` | WP06 |  | [D] |
| T027 | Parameterize retry guidance on actual `target_lane` | WP06 |  | [D] |
| T028 | Enhance `ReviewLock.release()` to remove empty `.spec-kitty/` directory | WP06 |  | [D] |
| T029 | Invoke `ReviewLock.release()` at approve and reject transition exits | WP06 |  | [D] |
| T030 | Write `.spec-kitty/` to per-worktree `info/exclude` at lane worktree creation | WP07 |  | [D] |
| T031 | Integration tests: approve/reject without `--force`, filter rules, release cleanup | WP06 | [P] |
| T032 | Investigate FR-020 approve-output source-lane anomaly | WP08 |  | [D] |
| T033 | Publish FR-020 investigation report; escalate fix if needed | WP08 |  | [D] |
| T034 | Draft ADR `2026-04-14-sparse-checkout-defense-in-depth.md` | WP09 |  | [D] |
| T035 | CHANGELOG entry + recovery recipe for affected users | WP09 | [D] |
| T036 | Post diagnostic comment on Priivacy-ai/spec-kitty#588 | WP09 | [D] |
| T037 | Session-warning call sites at charter sync and other external CLI surfaces | WP07 |  | [D] |
| T038 | Verify `--force` does not bypass the sparse-checkout preflight | WP05 | [P] |

## Work Packages

### WP01 — Commit-layer data-loss backstop in `safe_commit`

**Goal**: Guard every caller of `safe_commit` against silent inclusion of unexpected staged paths (the phantom-deletion cascade in Priivacy-ai/spec-kitty#588).

**Priority**: Highest — ships the data-loss defense that all other layers depend on.

**Independent test**: `tests/integration/git/test_safe_commit_backstop.py` reproduces the #588 cascade and asserts the backstop aborts the commit.

**Prompt file**: [tasks/WP01-commit-layer-backstop.md](tasks/WP01-commit-layer-backstop.md)

**Included subtasks**:
- [x] T001 Add `UnexpectedStagedPath` and `SafeCommitBackstopError` types (WP01)
- [x] T002 Implement `assert_staging_area_matches_expected()` helper (WP01)
- [x] T003 Wire backstop inside `safe_commit` after stage, before commit (WP01)
- [x] T004 Unit tests for backstop diff logic (WP01) [P]
- [x] T005 Regression test that reproduces the #588 cascade (WP01) [P]

**Dependencies**: none.
**Parallel opportunities**: T004 and T005 can run in parallel once T003 is complete.
**Risks**: False positives on callers that legitimately stage extra paths. Mitigated by tests covering every current `safe_commit` caller.

---

### WP02 — Sparse-checkout detection primitive, session warning, and preflight API

**Goal**: Create the single pure detection primitive (FR-001) and the preflight / session-warning entry points that every other sparse-checkout WP depends on.

**Priority**: Highest — shared dependency for WP03, WP04, WP05, WP06, WP07.

**Independent test**: `tests/unit/git/test_sparse_checkout_detection.py` covers the R6 rule (`core.sparseCheckout=true` ⇒ active regardless of pattern contents) and every edge case named in data-model.md.

**Prompt file**: [tasks/WP02-sparse-checkout-detection-and-api.md](tasks/WP02-sparse-checkout-detection-and-api.md)

**Included subtasks**:
- [x] T009 `SparseCheckoutState` and `SparseCheckoutScanReport` types (WP02)
- [x] T010 `scan_path()` and `scan_repo()` pure detection functions (WP02)
- [x] T011 `warn_if_sparse_once()` session-warning emitter + module flag (WP02)
- [x] T012 Unit tests for detection primitive covering R6 (WP02) [P]
- [x] T019 `SparseCheckoutPreflightError` + `require_no_sparse_checkout()` API (WP02)

**Dependencies**: none.
**Parallel opportunities**: T012 can run in parallel once T010 is complete.
**Risks**: Subtle git-config reading differences on worktrees (per-worktree configs layered over repo-local). Integration tests must assert behaviour on both.

---

### WP03 — Sparse-checkout remediation module

**Goal**: Implement the multi-step remediation that repairs the primary repo and every lane worktree, refusing on dirty trees (FR-003, FR-004, FR-005).

**Priority**: High — prerequisite for the doctor surface.

**Independent test**: `tests/unit/git/test_sparse_checkout_remediation.py` covers per-step outcomes and aggregation.

**Prompt file**: [tasks/WP03-sparse-checkout-remediation.md](tasks/WP03-sparse-checkout-remediation.md)

**Included subtasks**:
- [x] T013 Remediation types: per-path result + aggregate report (WP03)
- [x] T014 5-step per-path remediation composed across primary + worktrees (WP03)
- [x] T015 Unit tests for remediation outcomes (WP03) [P]

**Dependencies**: WP02.
**Parallel opportunities**: T015 after T014 complete.
**Risks**: `git checkout HEAD -- .` is destructive. The dirty-tree refusal must be enforced rigorously; tests must cover the refusal path on every target (primary + each worktree) before any remediation step runs.

---

### WP04 — Doctor finding and `--fix sparse-checkout` action

**Goal**: Surface the sparse-checkout condition through `spec-kitty doctor` and offer the remediation action behind a user-invoked fix flag, with correct CI / non-TTY behaviour (FR-002, FR-023).

**Priority**: High — the user-facing discovery surface.

**Independent test**: `tests/integration/sparse_checkout/test_doctor_finding.py` validates interactive prompt flow; `tests/integration/sparse_checkout/test_doctor_non_interactive.py` validates CI short-circuit.

**Prompt file**: [tasks/WP04-doctor-finding-and-fix-action.md](tasks/WP04-doctor-finding-and-fix-action.md)

**Included subtasks**:
- [x] T016 Doctor finding surfacing sparse-checkout scan (WP04)
- [x] T017 `doctor --fix sparse-checkout` action with CI/non-TTY handling (WP04)
- [x] T018 Integration tests for doctor finding and remediation flow (WP04) [P]

**Dependencies**: WP02, WP03.
**Parallel opportunities**: T018 after T017 complete.
**Risks**: Existing doctor output format — must match the current finding style, not introduce a new format.

---

### WP05 — Merge + implement preflights with post-merge refresh and invariant

**Goal**: Install the hard-block preflight on mission merge and agent action implement with `--allow-sparse-checkout` override (FR-006, FR-007, FR-008, FR-009), plus the post-merge working-tree refresh and invariant assertion (FR-013, FR-014).

**Priority**: High — the layer that prevents the #588 cascade from entering the merge path at all.

**Independent test**: `tests/integration/sparse_checkout/test_merge_preflight_blocks.py`, `test_merge_with_allow_override.py`, `test_merge_refresh_and_invariant.py`, `test_implement_preflight_blocks.py`.

**Prompt file**: [tasks/WP05-merge-and-implement-preflights.md](tasks/WP05-merge-and-implement-preflights.md)

**Included subtasks**:
- [x] T006 Post-merge working-tree refresh in `_run_lane_based_merge_locked` (WP05)
- [x] T007 Post-merge `git status` invariant assertion (WP05)
- [x] T020 Merge preflight wiring + `--allow-sparse-checkout` flag + log record (WP05)
- [ ] T021 Implement preflight wiring + `--allow-sparse-checkout` flag + log record (WP05)
- [ ] T023 Integration tests for merge + implement preflights, override, refresh, invariant (WP05) [P]
- [ ] T038 Verify `--force` does not bypass the sparse-checkout preflight (WP05) [P]

**Dependencies**: WP01 (backstop defensive layer must exist to prove multi-layer defense), WP02 (detection and preflight API).
**Parallel opportunities**: T023 and T038 after T020/T021 complete.
**Risks**: The override-log emission must land even when the preflight is skipped via the flag. Tests must capture log output to confirm.

---

### WP06 — Review-lock fixes, release lifecycle, and session-warning in task commands

**Goal**: Fix the #589 review-lock self-collision end-to-end: filter runtime-state directories from the dirty-tree guard (FR-015), correct the retry guidance (FR-017), release the lock and clean up its parent directory on approved/planned transitions (FR-018), ensure rejection does not trip the guard (FR-019), and install session-warning call sites inside the agent/tasks.py command set (FR-010 call sites).

**Priority**: High — closes all of #589 and installs half of the session-warning coverage.

**Independent test**: `tests/integration/review/test_approve_without_force.py`, `test_reject_without_force.py`.

**Prompt file**: [tasks/WP06-review-lock-and-task-session-warning.md](tasks/WP06-review-lock-and-task-session-warning.md)

**Included subtasks**:
- [x] T024 Session-warning call sites inside `agent/tasks.py` commands (WP06)
- [x] T026 Add `.spec-kitty/` + `.kittify/` deny-list filter to `_validate_ready_for_review` (WP06)
- [x] T027 Parameterize retry guidance on actual `target_lane` (WP06)
- [x] T028 Enhance `ReviewLock.release()` to remove empty `.spec-kitty/` directory (WP06)
- [x] T029 Invoke `ReviewLock.release()` at approve and reject transition exits (WP06)
- [ ] T031 Integration tests: approve/reject without `--force`, filter rules, release cleanup (WP06) [P]

**Dependencies**: WP02 (uses `warn_if_sparse_once()`).
**Parallel opportunities**: T031 after T029 complete.
**Risks**: The filter must remain narrow (named directories, not patterns, per C-003). Genuine uncommitted implementation work must still block (C-004). Both cases need explicit test coverage.

---

### WP07 — Per-worktree exclude writer, external session-warning sites, once-per-process test

**Goal**: Complete the review-lock fix by writing `.spec-kitty/` to every new lane worktree's `.git/worktrees/<lane>/info/exclude` (FR-016), install the remaining session-warning call sites at CLI surfaces outside agent/tasks.py (FR-010 completion), and ship the NFR-005 once-per-process test.

**Priority**: Medium — operational polish and defense-in-depth for #589.

**Independent test**: `tests/integration/sparse_checkout/test_session_warning_once.py` exercises three state-mutating commands in one process and asserts exactly one warning emission.

**Prompt file**: [tasks/WP07-worktree-exclude-and-external-warnings.md](tasks/WP07-worktree-exclude-and-external-warnings.md)

**Included subtasks**:
- [x] T025 Once-per-process integration test (NFR-005) (WP07) [P]
- [x] T030 Write `.spec-kitty/` to per-worktree `info/exclude` at lane worktree creation (WP07)
- [x] T037 Session-warning call sites at charter sync and other external CLI surfaces (WP07)

**Dependencies**: WP02 (uses detection + warn function), WP06 (session-warning call sites in tasks.py must already exist for the combined once-per-process test to assert correctly).
**Parallel opportunities**: T025 after T030 and T037 complete.
**Risks**: Identifying the right set of "external CLI surfaces" — the prompt must enumerate them explicitly so the implementer does not miss any.

---

### WP08 — FR-020 approve-output source-lane anomaly investigation

**Goal**: Determine whether the approve-output's reported "from in_progress" (instead of "from for_review") is a display bug, a deliberate consequence of how review-claim advances the lane, or a reducer anomaly — and then either fix it with a minimal change or publish an authoritative doc explaining why the observed output is correct (FR-020).

**Priority**: Medium — narrow investigation; blocks only FR-020 acceptance.

**Independent test**: the investigation itself — produces `research/fr020-investigation.md` with findings. If a code fix is warranted, a regression test accompanies it; otherwise a documentation entry goes to `docs/status-model.md`.

**Prompt file**: [tasks/WP08-fr020-anomaly-investigation.md](tasks/WP08-fr020-anomaly-investigation.md)

**Included subtasks**:
- [x] T032 Investigate FR-020 approve-output source-lane anomaly (WP08)
- [x] T033 Publish FR-020 investigation report; escalate fix if needed (WP08)

**Dependencies**: none.
**Parallel opportunities**: none within WP08 (T033 depends on T032).
**Risks**: Investigation may reveal a code fix that overlaps with other WPs' ownership. Mitigation: investigation produces documented findings; any code change is scoped as a follow-up issue rather than smuggled into another WP.

---

### WP09 — ADR, CHANGELOG, Kent diagnostic comment

**Goal**: Document the four-layer defense-in-depth architecture, ship the user-facing CHANGELOG entry with a recovery recipe for already-hit users, and post the diagnostic comment on Priivacy-ai/spec-kitty#588 (FR-021, FR-022, DIRECTIVE_003, adr-drafting-workflow).

**Priority**: Low (timing) — finishes the mission once all technical WPs produce material content.

**Independent test**: documentation review; no automated test.

**Prompt file**: [tasks/WP09-adr-changelog-and-diagnostic-comment.md](tasks/WP09-adr-changelog-and-diagnostic-comment.md)

**Included subtasks**:
- [x] T034 Draft ADR `2026-04-14-sparse-checkout-defense-in-depth.md` (WP09)
- [x] T035 CHANGELOG entry + recovery recipe for affected users (WP09) [P]
- [x] T036 Post diagnostic comment on Priivacy-ai/spec-kitty#588 (WP09) [P]

**Dependencies**: WP01, WP02, WP05, WP06, WP07 (must exist for authoritative ADR content).
**Parallel opportunities**: T035 and T036 after T034 complete.
**Risks**: T036 (posting the GH comment) is a human-action subtask. Treat as non-blocking for the mission's technical acceptance.

---

## MVP Scope

The mission's MVP (smallest shippable set that closes the data-loss regression) is **WP01 + WP02 + WP03 + WP04 + WP05**. Shipping only this set would close Priivacy-ai/spec-kitty#588 but leave #589 open. Shipping the full mission closes both.

## Parallelization Plan

- **Starting simultaneously (no deps)**: WP01, WP02, WP08.
- **Once WP02 lands**: WP03, WP06 can start.
- **Once WP03 lands**: WP04 can start.
- **Once WP01 + WP02 land**: WP05 can start.
- **Once WP02 + WP06 land**: WP07 can start.
- **Once all technical WPs land**: WP09 can start.

Lane assignment is authoritative once `finalize-tasks` produces `lanes.json`.
