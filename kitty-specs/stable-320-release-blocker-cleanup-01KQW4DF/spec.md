# 3.2.0 Release Blocker Cleanup

**Mission ID**: 01KQW4DFAWRMK2PM22CHZYBJ26
**Mission Slug**: stable-320-release-blocker-cleanup-01KQW4DF
**Mission Type**: software-dev
**Target Branch**: main
**Created**: 2026-05-05

---

## Purpose

**TL;DR**: Fix four CLI release blockers for the Spec Kitty 3.2.0 stable release.

**Context**: The Stable 3.2.0 P1 Release Confidence mission (`stable-320-p1-release-confidence-01KQTPZC`) completed lifecycle smoke runs and identified four open issues that prevent the 3.2.0 stable release from shipping with confidence. Each blocker was observed during real smoke execution and is documented with reproducible evidence. This mission fixes all four blockers, adds focused regression tests, and produces clean smoke evidence suitable for closing the associated GitHub issues.

---

## Scope

### In Scope

- Fix SaaS final-sync error output that leaks into successful local command results (GitHub issue #952).
- Fix `spec-kitty agent tasks mark-status` failing to accept task IDs that appear outside checkbox rows (GitHub issue #783).
- Fix the cross-repo E2E `contract_drift_caught` scenario failing before product behavior on macOS with uv-managed Python (GitHub issue #975).
- Fix `spec-kitty merge --dry-run` not catching a missing mission branch prerequisite (GitHub issue #976).
- Add focused regression tests for all four fixes.
- Produce smoke evidence demonstrating issue closure.

### Out of Scope

- GitHub issue #971 (tracker rollout machinery) — explicitly deferred; this mission must not expand to address it.
- Any rollout gating changes inside the `spec-kitty-tracker` package.
- Reopening issues #966 or #848 unless this mission's changes introduce a demonstrable fresh regression in those areas.

---

## User Scenarios & Testing

### Scenario A — Successful agent state transition with SaaS sync unavailable

**Actor**: A release engineer or AI agent running a lifecycle smoke run.
**Trigger**: The operator transitions a work package to a new lane using a hosted-capable CLI command while the SaaS sync daemon has a held lock, auth-refresh contention, or WebSocket connection failure.
**Happy path**: The local state transition completes successfully. The command exits 0. The JSON output (when `--json` is used) contains only valid JSON. The sync failure is reported as a single non-fatal structured diagnostic on stderr only, deduped to one occurrence, categorized by failure type, and worded so that it is clear the local operation succeeded.
**Exception path**: If sync cannot complete after bounded retries, the operator sees exactly one stderr diagnostic naming the failure type (e.g., lock unavailable, auth refresh in progress) and a bounded queue depth. They do not see red failure prefixes, `Connection failed` text, or repeated error lines.
**Acceptance**: Smoke run logs show no red failure output for successful local mutations; JSON stdout parses cleanly; stderr carries at most one non-fatal diagnostic per invocation.

### Scenario B — Marking status for task IDs that appear outside checkbox rows

**Actor**: An AI agent or operator running `spec-kitty agent tasks mark-status` after planning.
**Trigger**: The operator requests status update for a task ID (`T001`) or WP ID (`WP02`) that is referenced in a tasks artifact but not backed by a `- [ ] T001` checkbox row — for example, appearing in an inline `Subtasks: T001, T002, T003` line or in a WP-level bookkeeping reference.
**Happy path**: The command locates the ID via supported reference formats, updates or records status appropriately, and returns a per-ID result summary (found / updated / already-satisfied). The output (both text and `--json`) reports what happened for each requested ID.
**Exception path**: An ID that genuinely does not appear in any known format returns a specific `not-found` result for that ID only; other IDs in the same invocation are still processed.
**Acceptance**: The command does not fail with "No task IDs found" when the ID exists in a supported non-checkbox format. Existing checkbox and pipe-table update behavior remains unaffected.

### Scenario C — Cross-repo E2E contract drift check on uv-managed Python runner

**Actor**: A CI runner or local developer executing `contract_drift_caught` on macOS with a uv-managed Python installation.
**Trigger**: The scenario needs to create a nested Python environment to install a downstream consumer and test for contract drift.
**Happy path**: The scenario detects the uv-managed runner context, uses `uv venv` to create the nested environment, installs the downstream package, and proceeds to assert that real contract drift is caught.
**Exception path**: If neither `uv venv` nor stdlib `venv` can safely create the environment, the scenario emits a precise human-readable skip or xfail reason before any product assertion runs, so the failure is classified as an environment limitation rather than a product regression.
**Acceptance**: The scenario does not fail with a missing `libpython` error before reaching product behavior; product drift assertions still run and pass when environment creation succeeds.

### Scenario D — Merge dry-run catches missing mission branch

**Actor**: An AI agent or operator about to merge a completed mission.
**Trigger**: The operator runs `spec-kitty merge --mission <slug> --dry-run --json` in a fresh workspace where the expected `kitty/mission-<slug>` branch does not exist yet.
**Happy path**: Dry-run detects the missing branch, reports `"ready": false` with a structured `blocker` field identifying the missing branch and including a `remediation` command. The human-readable output names the missing branch and the fix. No merge is attempted.
**Exception path**: If auto-creating the branch is the correct product behavior for a valid fresh single-branch smoke, dry-run reports that planned action deterministically instead of reporting a blocker.
**Acceptance**: Dry-run and real merge agree on readiness; the operator is not surprised by a merge failure that dry-run declared ready. Existing preflight checks (dirty worktrees, diverged target branch, conflict forecasting) are unaffected.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | When a local lifecycle command completes successfully, its exit code, stdout text, and JSON output must remain success-oriented regardless of whether SaaS final sync can complete. | Proposed |
| FR-002 | In `--json` mode, the command's standard output must contain only valid JSON. All final-sync failure information must be written exclusively to standard error. | Proposed |
| FR-003 | Within a single command invocation, final-sync failure diagnostics must be deduplicated: at most one diagnostic message is emitted per invocation regardless of how many retry attempts or failure signals occur. | Proposed |
| FR-004 | Each final-sync failure diagnostic must classify the failure into one of at least five named categories: lock unavailable, auth refresh already in progress, WebSocket offline or unavailable, interpreter shutdown or event loop unavailable, hosted server or authentication failure. | Proposed |
| FR-005 | Before emitting a non-fatal final-sync diagnostic, the runtime must attempt final sync with bounded retries sufficient that a normally reachable server completes sync during a standard smoke run. | Proposed |
| FR-006 | No successful local mutation may print a red failure prefix, the string "Connection failed", or any wording that a reader could reasonably interpret as the local command having failed. | Proposed |
| FR-007 | `spec-kitty agent tasks mark-status` must resolve task IDs that appear in inline reference lines of the form `Subtasks: T001, T002, T003` within task artifacts, in addition to the existing checkbox-row format. | Proposed |
| FR-008 | `spec-kitty agent tasks mark-status` must resolve bare work-package IDs (e.g., `WP02`) as valid targets for WP-level status bookkeeping, producing a result rather than "No task IDs found". | Proposed |
| FR-009 | `mark-status` must return a per-ID result entry for every requested ID, indicating one of: updated, already-satisfied, or not-found. A request covering multiple IDs must return all individual results without hiding successful ones behind a failing one. | Proposed |
| FR-010 | When a requested task ID is genuinely absent from all supported reference formats, the result for that specific ID must be `not-found` with a concise human-readable explanation; other IDs in the same invocation are processed normally. | Proposed |
| FR-011 | Existing `mark-status` behavior for checkbox-row task IDs and pipe-table task IDs must continue to function identically after the changes introduced by FR-007 and FR-008. | Proposed |
| FR-012 | The `contract_drift_caught` E2E scenario must detect when the outer Python runner is uv-managed and `uv` is available on PATH, and in that case use `uv venv` to create any nested Python environment required by the scenario. | Proposed |
| FR-013 | When the scenario cannot safely create a nested Python environment by any available method, it must skip or xfail before executing any product assertions, emitting a precise, structured reason that identifies this as an environment limitation rather than a product failure. | Proposed |
| FR-014 | The nested environment creation logic must be implemented as a reusable helper module accessible to other cross-repo E2E scenarios, not inlined into `contract_drift_caught` alone. | Proposed |
| FR-015 | When the nested environment creation succeeds, the `contract_drift_caught` scenario must still reach and execute its product-level contract drift assertions, confirming that real drift is detected. | Proposed |
| FR-016 | `spec-kitty merge --dry-run` must verify that the expected mission branch (e.g., `kitty/mission-<slug>`) exists, and must report `ready: false` with a structured blocker when the branch is absent. | Proposed |
| FR-017 | When `merge --dry-run --json` reports a missing mission branch blocker, the JSON output must include stable fields: `ready` (boolean), `blocker` (string identifier), `expected_branch` (full branch name), and `remediation` (command string). | Proposed |
| FR-018 | The mission branch existence check introduced for dry-run must also be applied to real merge execution; a condition that causes `merge --dry-run` to report `ready: false` must also block the real merge before any irreversible git operation. | Proposed |
| FR-019 | If the correct product behavior for a valid fresh single-branch smoke is to auto-create the mission branch, `merge --dry-run` must report that planned creation deterministically rather than a blocker, so the operator can anticipate the action before running the real merge. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All four blocker fixes must be accompanied by focused regression tests that pass reliably in CI with no flakes. | 100% pass rate across all regression test cases; zero flakes over 3 consecutive CI runs. | Proposed |
| NFR-002 | The changes introduced by this mission must not cause any currently passing tests covering the behavior of closed issues #966 and #848 to fail. | Zero new failures in test files related to those issue areas. | Proposed |
| NFR-003 | The deduplication logic for final-sync diagnostics must not add observable latency to the fast path where sync completes immediately. | Less than 5 ms of added overhead on the fast-path sync completion scenario. | Proposed |
| NFR-004 | The `mark-status --json` output for all ID resolution outcomes (updated, already-satisfied, not-found) must conform to a documented, stable JSON schema. | Schema correctness validated by at least one test per outcome type; no breaking schema changes without a version bump. | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | GitHub issue #971 (tracker rollout machinery) is explicitly out of scope. This mission must not implement, stub, or design any rollout gating infrastructure inside `spec-kitty-tracker`. | Firm |
| C-002 | All hosted and sync-capable lifecycle commands run as part of smoke verification for this mission must be executed with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Firm |
| C-003 | No rollout gating machinery may be added inside the `spec-kitty-tracker` package as part of this mission. | Firm |
| C-004 | GitHub issues #966 and #848 are closed. This mission must not reopen them. If changes introduced here create a demonstrable fresh regression in those areas, they must be treated as a new defect and tracked separately. | Firm |

---

## Success Criteria

1. A lifecycle smoke run in which the SaaS sync daemon cannot complete final sync produces no red failure output and no ambiguous failure wording for the successfully-mutated local state — confirmed by log review of the smoke evidence file.
2. `spec-kitty agent tasks mark-status` returns a non-error result for task IDs referenced in at least the three formats: checkbox rows, inline `Subtasks:` lines, and bare WP IDs — confirmed by passing regression tests covering each format.
3. The `contract_drift_caught` E2E scenario completes without failing before reaching product assertions on a macOS workstation with a uv-managed Python installation — confirmed by a passing scenario run in the configured E2E environment.
4. `spec-kitty merge --dry-run --json` returns `"ready": false` with a `blocker` field identifying the missing mission branch in a fresh workspace where the branch does not exist — confirmed by a passing regression test and by a captured dry-run output in smoke evidence.
5. All four regression test suites covering the fixed behaviors pass in a single local test run against the relevant test paths.
6. No currently-passing test in the areas of #966 or #848 fails after the changes land.

---

## Tracked Issues

| Issue | Title (abbreviated) | Role in this mission |
|-------|---------------------|----------------------|
| #952 | SaaS final-sync errors leak into success output | Fixed by FR-001 – FR-006 |
| #783 | `mark-status` fails on non-checkbox task IDs | Fixed by FR-007 – FR-011 |
| #975 | Cross-repo E2E fails before product behavior on uv Python | Fixed by FR-012 – FR-015 |
| #976 | `merge --dry-run` misses missing mission branch | Fixed by FR-016 – FR-019 |
| #971 | Tracker rollout machinery | **Explicitly out of scope** |
| #966 | (closed) | Must not regress |
| #848 | (closed) | Must not regress |

---

## Assumptions

- The SaaS server at `https://spec-kitty-dev.fly.dev` is reachable from the development machine during hosted smoke verification; unreachability is treated as a non-fatal environmental condition, not a product failure.
- The macOS workstation used for E2E testing has `uv` installed and available on PATH; if it does not, FR-013 (skip/xfail path) applies.
- The regression test suite can be run locally using `uv run pytest` from the relevant repository root without additional infrastructure.
- The bounded-retry threshold for FR-005 is sufficient for normal development network conditions; exact retry counts are implementation details determined during planning.
- Auto-creation of the mission branch (FR-019) is acceptable only if it is idempotent and does not overwrite an existing branch; the implementation team will confirm during planning whether auto-creation or a blocker report is the correct behavior for the fresh-smoke case.
