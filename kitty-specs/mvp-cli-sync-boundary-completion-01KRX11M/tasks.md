# Tasks: MVP CLI Sync Boundary Completion

**Mission**: `mvp-cli-sync-boundary-completion-01KRX11M`
**Mission ID**: `01KRX11MCY70M5NFBBHT4DQHJ2`
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Target branch**: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` (PR #1107)

## Branch contract

- Current branch: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`
- Planning/base branch: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`
- Final merge target: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`
- `branch_matches_target`: true

All WP execution worktrees are allocated under `.worktrees/<human-slug>-<mid8>-lane-<id>` by `finalize-tasks` once lanes are computed.

## Work-package overview

| WP | Title | Subtasks | Depends on | Authoritative surface | Execution mode |
|---|---|---|---|---|---|
| WP01 | Sync boundary preflight module | T001–T005 (5) | — | `src/specify_cli/sync/preflight.py` | code_change |
| WP02 | Row-level queue migration: body uploads + idempotence | T006–T009 (4) | — | `src/specify_cli/sync/queue.py` | code_change |
| WP03 | sync.py: status/check expansion, sync-now wiring, gate delegation | T010–T016 (7) | WP01, WP02 | `src/specify_cli/cli/commands/sync.py` | code_change |
| WP04 | setup-plan preflight integration | T017–T020 (4) | WP01 | `src/specify_cli/cli/commands/agent/mission.py` | code_change |
| WP05 | Mission closure: evidence + PR body update draft | T021–T024 (4) | WP02, WP03, WP04 | `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/` | planning_artifact |

**Total subtasks**: 24. **Total WPs**: 5. **Parallelization**: WP01 ∥ WP02 (lane A and lane B). WP03 ∥ WP04 (after WP01 lands). WP05 last.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `preflight.py` with dataclasses (`ForegroundIdentity`, `OwnerMismatch`, `PreflightResult`, `MismatchField` literal) | WP01 |  |
| T002 | Implement `collect_foreground_identity(repo_root)` | WP01 |  |
| T003 | Implement `run_preflight(...)` composing existing helpers | WP01 |  |
| T004 | Implement `PreflightResult.render(console)` and `.to_dict()` | WP01 |  |
| T005 | Add `tests/sync/test_sync_boundary_preflight.py` (unit + integration) | WP01 |  |
| T006 | Extend `_migrate_legacy_queue_to_scope` to walk both `sync_events` and `body_upload_queue` | WP02 | [P] vs WP01 |
| T007 | Switch all migration inserts to `INSERT OR IGNORE` keyed on primary keys | WP02 |  |
| T008 | Extend `detect_legacy_rows_for_scope` to return event/body-upload subtotals | WP02 |  |
| T009 | Extend `tests/sync/test_queue_row_level_migration.py` with body-upload + non-empty scoped + idempotence cases | WP02 |  |
| T010 | Refactor `_build_boundary_check_failures` into a reusable single source of truth | WP03 |  |
| T011 | Rewrite `_require_daemon_owner_coherence` as a thin wrapper over `run_preflight` | WP03 |  |
| T012 | Wire `run_preflight` into `sync now` (around `sync.py:1196`) before any enqueue or flush | WP03 |  |
| T013 | Extend `sync status` printed fields per `contracts/sync-status-output.md` | WP03 |  |
| T014 | Add `--check --json` mode emitting `PreflightResult.to_dict` plus extras | WP03 |  |
| T015 | Update orphan-daemon section (`sync.py:2007`) to share preflight categories | WP03 |  |
| T016 | Extend `tests/sync/test_sync_status_boundary_check.py` and `tests/sync/test_daemon_owner_record.py` | WP03 |  |
| T017 | Wire `run_preflight` into `setup_plan` after hosted-auth preflight and before any enqueue or body upload | WP04 | [P] vs WP03 |
| T018 | Verify all SaaS-producing mission lifecycle paths route through the same gate; document path inventory | WP04 |  |
| T019 | Extend `tests/runtime/test_setup_plan_sync_evidence.py` with preflight integration | WP04 |  |
| T020 | Add regression assertion that `setup-plan` never writes to legacy queue when authenticated | WP04 |  |
| T021 | Run full verification suite and capture transcripts into `evidence/test-transcripts/` | WP05 |  |
| T022 | Draft sub-issue evidence comments (`evidence/close-1090.md`, `close-1088.md`, `close-1087.md`, `close-1089.md`) | WP05 |  |
| T023 | Draft replacement PR #1107 body in `evidence/pr-1107-body-update.md` (for operator to apply via `gh pr edit`) | WP05 |  |
| T024 | Update mission status events and decision verify; mark Definition of Done satisfied | WP05 |  |

## WP01 — Sync boundary preflight module

**Goal**: Land the reusable preflight helper that subsequent WPs wire into entry points.
**Priority**: P0 (blocking gate for WP03 and WP04).
**Independent test**: `uv run pytest tests/sync/test_sync_boundary_preflight.py -q` exits 0 with all named scenarios passing.
**Risks**: Wrong API shape causes WP03/WP04 churn — fix the contract now (see `contracts/sync-boundary-preflight.md`).

**Included subtasks**:

- [x] T001 Create `preflight.py` with dataclasses (WP01)
- [x] T002 Implement `collect_foreground_identity` (WP01)
- [x] T003 Implement `run_preflight` composition (WP01)
- [x] T004 Implement `PreflightResult.render` and `.to_dict` (WP01)
- [x] T005 Add `tests/sync/test_sync_boundary_preflight.py` (WP01)

**Implementation sketch**: Mirror `src/specify_cli/merge/preflight.py` shape. Compose existing `owner.check_daemon_owner_match()`, `owner.is_orphan()`, `owner.list_orphan_records()`, and `queue.detect_legacy_rows_for_scope()`. Default refusal output is Rich-rendered, ≤25 lines, with canonical field names from `spec.md` Domain Language.

**Parallelization**: Runs concurrently with WP02 (lane A and lane B).
**Dependencies**: none.

**Prompt**: [tasks/WP01-preflight-module.md](./tasks/WP01-preflight-module.md) (~380 lines)

## WP02 — Row-level queue migration: body uploads + idempotence

**Goal**: Extend the legacy → scoped row-level migration to cover `body_upload_queue` rows and make retries idempotent via `INSERT OR IGNORE`.
**Priority**: P0 (blocking sub-issue #1090).
**Independent test**: `uv run pytest tests/sync/test_queue_row_level_migration.py -q` exits 0 including new body-upload and idempotence cases.
**Risks**: Duplicate-row bug on retry (R2 in `research.md`) — guarded by `INSERT OR IGNORE` plus a dedicated retry test.

**Included subtasks**:

- [x] T006 Extend `_migrate_legacy_queue_to_scope` to walk both row classes (WP02)
- [x] T007 Switch inserts to `INSERT OR IGNORE` keyed on primary keys (WP02)
- [x] T008 Extend `detect_legacy_rows_for_scope` to return event/body-upload subtotals (WP02)
- [x] T009 Extend tests (WP02)

**Implementation sketch**: Keep the existing scope-filtering logic; the change is the inner loop and the subtotal-bearing return type. No SQLite schema change.

**Parallelization**: Runs concurrently with WP01.
**Dependencies**: none.

**Prompt**: [tasks/WP02-row-level-migration.md](./tasks/WP02-row-level-migration.md) (~330 lines)

## WP03 — sync.py: status/check expansion, sync-now wiring, gate delegation

**Goal**: Make `sync status --check` and `sync now` both consume the single shared boundary-check builder; expand printed fields to match `contracts/sync-status-output.md`; expose `--check --json`.
**Priority**: P0 (blocking sub-issues #1087 and #1088 evidence).
**Independent test**: `uv run pytest tests/sync/test_sync_status_boundary_check.py tests/sync/test_daemon_owner_record.py -q` exits 0; live `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check` matches contract.
**Risks**: Drift between gate and status output — eliminated by routing both through `_build_boundary_check_failures` and `run_preflight`. Touching one large file (`sync.py`) — owned exclusively by this WP to avoid merge conflicts.

**Included subtasks**:

- [x] T010 Refactor `_build_boundary_check_failures` into single source of truth (WP03)
- [x] T011 Rewrite `_require_daemon_owner_coherence` as preflight wrapper (WP03)
- [x] T012 Wire `run_preflight` into `sync now` (WP03)
- [x] T013 Extend `sync status` printed fields (WP03)
- [x] T014 Add `--check --json` mode (WP03)
- [x] T015 Update orphan-daemon section (WP03)
- [x] T016 Extend `test_sync_status_boundary_check.py` and `test_daemon_owner_record.py` (WP03)

**Parallelization**: Runs concurrently with WP04 (different files) once WP01 and WP02 land.
**Dependencies**: WP01, WP02.

**Prompt**: [tasks/WP03-sync-py-expansion.md](./tasks/WP03-sync-py-expansion.md) (~480 lines)

## WP04 — setup-plan preflight integration

**Goal**: Wire `run_preflight` into `setup_plan` after the existing hosted-auth preflight and before any enqueue, body upload, or WPCreated SaaS emission.
**Priority**: P0 (blocking sub-issue #1089 evidence).
**Independent test**: `uv run pytest tests/runtime/test_setup_plan_sync_evidence.py -q` exits 0 including new preflight integration cases.
**Risks**: Missing a SaaS-producing path — T018 produces an inventory in the mission directory.

**Included subtasks**:

- [x] T017 Wire `run_preflight` into `setup_plan` (WP04)
- [x] T018 Document inventory of all SaaS-producing mission lifecycle paths (WP04)
- [x] T019 Extend tests with preflight integration (WP04)
- [x] T020 Add regression: no legacy-queue writes from `setup-plan` when authenticated (WP04)

**Parallelization**: Runs concurrently with WP03.
**Dependencies**: WP01.

**Prompt**: [tasks/WP04-setup-plan-preflight.md](./tasks/WP04-setup-plan-preflight.md) (~280 lines)

## WP05 — Mission closure: evidence + PR body update draft

**Goal**: Capture verification evidence, draft sub-issue close comments, and prepare the PR #1107 body replacement for operator application.
**Priority**: P1 (last WP; non-code planning artifact).
**Independent test**: All evidence files exist under `evidence/` and the verification transcripts demonstrate green test suites + clean `sync status --check`.

**Included subtasks**:

- [x] T021 Run full verification suite and capture transcripts (WP05)
- [x] T022 Draft sub-issue evidence comments for #1090/#1088/#1087/#1089 (WP05)
- [x] T023 Draft replacement PR #1107 body (WP05)
- [x] T024 Update mission status events and decision verify (WP05)

**Parallelization**: None; runs after all code WPs land.
**Dependencies**: WP02, WP03, WP04.

**Prompt**: [tasks/WP05-mission-closure.md](./tasks/WP05-mission-closure.md) (~240 lines)

## Polish / cross-cutting

- `mypy --strict src/specify_cli/sync/` is verified at the end of WP01, WP02, and WP03 — each WP includes a "Definition of Done" check for it.
- 90 %+ coverage on changed surfaces is verified via per-WP `pytest --cov` runs (subset).
- `spec-kitty agent decision verify --mission mvp-cli-sync-boundary-completion-01KRX11M` is rerun at end of WP05 (T024) and must be clean.
