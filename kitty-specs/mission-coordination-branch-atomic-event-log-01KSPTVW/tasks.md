# Work Packages: Mission Coordination Branch with Atomic Event Log

**Mission**: `mission-coordination-branch-atomic-event-log-01KSPTVW`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Source Issue**: [Priivacy-ai/spec-kitty#1348](https://github.com/Priivacy-ai/spec-kitty/issues/1348)
**Status**: Draft
**Date**: 2026-05-28
**Branch**: `main` (planning_base_branch == merge_target_branch)

---

## Subtask Index (reference table; not a tracking surface)

| ID    | Description                                                                                   | WP   | Parallel |
| ----- | --------------------------------------------------------------------------------------------- | ---- | -------- |
| T001  | Update `safe_commit()` signature → keyword-only `destination_ref` required                    | WP01 |          |
| T002  | Implement `HEAD == destination_ref` assertion + structured error types                        | WP01 |          |
| T003  | Remove silent `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` spec-kitty-internal bypass entries        | WP01 | [P]      |
| T004  | Unit tests: happy path, HEAD mismatch, protected branch, missing-arg, empty paths             | WP01 | [P]      |
| T005  | CHANGELOG entry for PR 1                                                                      | WP01 | [P]      |
| T006  | Audit every `safe_commit()` call site in the codebase; produce migration manifest             | WP02 |          |
| T007  | Update `spec-kitty safe-commit` CLI: add required `--to-branch`; deprecation env var          | WP02 |          |
| T008  | Migrate non-workflow callers (charter, upgrade migrations, mission close) to pass `destination_ref` | WP02 | [P]   |
| T009  | Integration tests for `safe-commit` CLI; deprecation-warning path                              | WP02 | [P]      |
| T010  | Update tests for migrated callers; verify no `safe_commit()` call site lacks `destination_ref` | WP02 | [P]      |
| T011  | Add coordination branch creation logic to `agent mission create`                              | WP03 |          |
| T012  | Implement idempotent branch creation; preserve existing coordination ref                      | WP03 |          |
| T013  | Persist coordination branch ref in `meta.json`; expose in `mission create --json` output     | WP03 |          |
| T014  | Unit tests for branch creation, idempotency, name derivation (mid8 disambiguation)            | WP03 | [P]      |
| T015  | `CoordinationWorkspace` service: resolve/create/teardown coordination worktree                | WP04 |          |
| T016  | Sparse-checkout policy registration at lane worktree creation (`LANE_SPARSE_CHECKOUT_EXCLUSIONS`) | WP04 |        |
| T017  | Lane allocator updates: parent lane branches on coordination branch                            | WP04 |          |
| T018  | Unit tests: coordination worktree lifecycle; sparse-checkout drift detection                  | WP04 | [P]      |
| T019  | Doctor command: sparse-checkout drift + coordination worktree health checks                   | WP04 | [P]      |
| T020  | `GitChangeSet` value object + `PolicyVerdict` sum type                                         | WP05 |          |
| T021  | `WorkflowMutationPolicy.assert_allowed()` — single chokepoint with stable error codes         | WP05 |          |
| T022  | `BookkeepingTransaction` context manager: acquire/append_event/commit/rollback/release         | WP05 |          |
| T023  | Surgical truncate rollback path with `pre_emit_size` capture                                   | WP05 |          |
| T024  | Outbound-deferral mechanism (`defer_outbound`) inside transaction                              | WP05 |          |
| T025  | Unit tests: full transaction lifecycle, refusal, rollback, nested-lock blocking               | WP05 | [P]      |
| T026  | Migrate planning-artifact commit site (`implement.py:236`) → `BookkeepingTransaction`         | WP06 |          |
| T027  | Migrate lifecycle status writes (`workflow.py:689`, `:1463`) → `BookkeepingTransaction`       | WP06 |          |
| T028  | Migrate event emit pipeline (`emit.py:468`) → `BookkeepingTransaction`                        | WP06 |          |
| T029  | Implement/review terminal output: commit-summary section (FR-014)                              | WP06 |          |
| T030  | Integration tests: 2-lane mission happy path; forced commit failure → rollback                | WP06 | [P]      |
| T031  | Fix `_resolve_planning_branch()` in `mission.py:321` → returns canonical merge target          | WP07 |          |
| T032  | Two-stage merge: lane → coordination → target; lane integration events                        | WP07 |          |
| T033  | Mission close teardown: delete coordination worktree + coordination branch + lanes (FR-016)   | WP07 |          |
| T034  | Integration tests: finalize-tasks from prep branch; full multi-lane merge → target            | WP07 | [P]      |
| T035  | Legacy mission detection: missing coordination branch → lane-branch destination_ref           | WP08 |          |
| T036  | Apply pre-flight + transaction + rollback uniformly to legacy missions (FR-017, FR-027)       | WP08 |          |
| T037  | CLI status mediation: `agent tasks status` / `agent context resolve` read coordination worktree | WP08 |        |
| T038  | Integration tests: legacy mission regression + CLI mediation from lane CWD                    | WP08 | [P]      |
| T039  | Architectural test: forbid direct `safe_commit` imports from transactional workflow modules   | WP09 | [P]      |
| T040  | Stress test: 20 concurrent `implement` calls; verify no interleaved writes (SC-12)            | WP09 | [P]      |
| T041  | SaaS-sink fanout deferral instrumentation + mock-sink test fixture (NFR-009)                  | WP09 |          |
| T042  | Issue #1348 regression test: exact reproduction sequence; verify fix holds                    | WP09 | [P]      |

Total subtasks: **42**. Total WPs: **9**.

---

## MVP Scope

**Minimum viable shipment that actually closes #1348**: **WP01 → WP06**.

The earlier draft incorrectly claimed WP01+WP02 alone closed #1348. That's wrong: WP01+WP02 close the *structural class* of bug (silent commit-target drift), but the specific symptom in #1348 — `status.events.jsonl` ahead of HEAD because the event-log append happens before the protected-branch refusal — only stops when bookkeeping writes route through `BookkeepingTransaction` (WP05) and the four workflow call sites are migrated (WP06). Until WP06 lands, the reproduction sequence still triggers.

What each PR delivers:
- **PR 1 (WP01+WP02)**: Helper-level invariant. After this, no `safe_commit()` caller can silently land on the wrong branch via type/HEAD drift. **Does NOT yet close #1348's reproduction**, because the bookkeeping writes still happen before the commit attempt.
- **PR 2 (WP03..WP08)**: Coordination branch + `BookkeepingTransaction` + workflow call-site migration + legacy fallback. **This is the PR that actually closes the #1348 reproduction.**
- **PR 3 (WP09)**: Hardening that prevents future regression. Optional for closing #1348; required for long-term resilience.

**Full mission close**: WP01–WP08. WP09 is hardening that can ship in a follow-up release.

---

## Dependency Graph

```
WP01 (helper signature + assertion)
  └── WP02 (caller migration; depends on WP01 for new signature)
        └── WP03 (mission create mints coord branch; depends on WP02 for safe-commit availability)
              ├── WP04 (CoordinationWorkspace + lane sparse-checkout; depends on WP03 for coord branch)
              │     └── WP05 (BookkeepingTransaction + Policy; depends on WP04 for coord worktree)
              │           └── WP06 (workflow call-site migration; depends on WP05 for transaction service)
              │                 └── WP07 (two-stage merge + finalize-tasks fix; depends on WP06 for transaction-routed writes)
              │                       └── WP08 (legacy fallback + CLI status mediation; depends on WP07)
              │                             └── WP09 (hardening + regression tests; depends on WP08)
```

Lane assignment (the lane allocator will determine final lane IDs):
- **Lane A**: WP01 → WP02 (PR 1 sequence)
- **Lane B**: WP03 → WP04 → WP05 (PR 2 foundation)
- **Lane C**: WP06 → WP07 → WP08 (PR 2 workflow migration; depends on Lane B)
- **Lane D**: WP09 (PR 3, parallelizable with later WP08 stages)

No cycles. WP01 is the only WP with no dependencies.

---

## Work Package WP01: `safe_commit()` helper signature change with HEAD assertion

**Goal**: Make `destination_ref` a required keyword-only parameter on `safe_commit()`; add an internal `HEAD == destination_ref` assertion. This is the **structural invariant** that prevents silent commit-target drift. (Spec: FR-031, FR-013, C-015, NFR-007.)

**Priority**: P0 — blocker for every subsequent WP.

**Independent test**: A unit test calls `safe_commit()` against a worktree whose HEAD does not match `destination_ref`; the call MUST raise `SAFE_COMMIT_HEAD_MISMATCH` with the structured error fields. A second test confirms `mypy --strict` rejects any call site that omits `destination_ref`.

**Estimated prompt size**: ~350 lines.

**Included subtasks**:
- [ ] T001 Update `safe_commit()` signature → keyword-only `destination_ref` required (WP01)
- [ ] T002 Implement `HEAD == destination_ref` assertion + structured error types (WP01)
- [ ] T003 Remove silent `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` spec-kitty-internal bypass entries (WP01)
- [ ] T004 Unit tests: happy path, HEAD mismatch, protected branch, missing-arg, empty paths (WP01)
- [ ] T005 CHANGELOG entry for PR 1 (WP01)

**Implementation sketch**: Edit `src/specify_cli/git/commit_helpers.py`. Add `CommitDestinationMismatch` exception. Refactor `safe_commit` to receive `destination_ref` via keyword-only param. Run `git -C <worktree> symbolic-ref HEAD` and compare. Update existing protected-branch exception logic to remove planning-artifact bypass. Write the test file. Add CHANGELOG entry.

**Risks**:
- Existing callers will break compilation. Mitigated by WP02 immediately following.
- mypy errors will surface across the tree. This is the intended structural enforcement; do not soften the type signature.

**Dependencies**: None.

**Prompt**: [tasks/WP01-safe-commit-helper-invariant.md](tasks/WP01-safe-commit-helper-invariant.md)

---

## Work Package WP02: Migrate existing `safe_commit()` callers

**Goal**: Audit and migrate every existing call site of `safe_commit()` to pass `destination_ref` explicitly. Update the public `spec-kitty safe-commit` CLI to require `--to-branch`. Add a deprecation env var to ease external-script rollout. (Spec: FR-031 caller migration, FR-013 follow-through.)

**Priority**: P0 — unblocks the rest of the codebase after WP01's signature change.

**Independent test**: After WP02 lands, `mypy --strict` passes on the entire codebase, and a test enumerates every `safe_commit()` call site and asserts each one passes `destination_ref` explicitly.

**Estimated prompt size**: ~400 lines.

**Included subtasks**:
- [ ] T006 Audit every `safe_commit()` call site in the codebase; produce migration manifest (WP02)
- [ ] T007 Update `spec-kitty safe-commit` CLI: add required `--to-branch`; deprecation env var (WP02)
- [ ] T008 Migrate non-workflow callers (charter, upgrade migrations, mission close) to pass `destination_ref` (WP02)
- [ ] T009 Integration tests for `safe-commit` CLI; deprecation-warning path (WP02)
- [ ] T010 Update tests for migrated callers; verify no `safe_commit()` call site lacks `destination_ref` (WP02)

**Implementation sketch**: `grep -rn 'safe_commit(' src/` to find call sites. Categorize: workflow (deferred to WP06) vs non-workflow (this WP). For non-workflow, add `destination_ref=<resolved>` parameter — typically `destination_ref=current_branch` from the branch-context resolver. Update CLI command. Add deprecation env var path: if `SPEC_KITTY_INFER_DESTINATION_REF=1` is set AND `--to-branch` is missing, resolve via branch-context resolver with a one-line stderr deprecation notice.

**Risks**:
- Some callers may be exotic (e.g. inside migrations) and require careful destination_ref resolution.
- The deprecation env var must be documented and have a removal date.

**Dependencies**: WP01.

**Prompt**: [tasks/WP02-migrate-safe-commit-callers.md](tasks/WP02-migrate-safe-commit-callers.md)

---

## Work Package WP03: Mission create mints coordination branch

**Goal**: `spec-kitty agent mission create` mints the coordination branch `kitty/mission-<slug>-<mid8>` parented off the canonical target branch. Idempotent on re-run. Branch ref persisted in `meta.json`. (Spec: FR-003, FR-015, FR-018, C-001, C-005, C-006.)

**Priority**: P1 — foundational for the coordination-branch topology.

**Independent test**: An integration test runs `mission create` twice for the same mission slug; the second call reuses the existing coordination branch and is a no-op. The branch name follows the `kitty/mission-<slug>-<mid8>` pattern.

**Estimated prompt size**: ~280 lines.

**Included subtasks**:
- [ ] T011 Add coordination branch creation logic to `agent mission create` (WP03)
- [ ] T012 Implement idempotent branch creation; preserve existing coordination ref (WP03)
- [ ] T013 Persist coordination branch ref in `meta.json`; expose in `mission create --json` output (WP03)
- [ ] T014 Unit tests for branch creation, idempotency, name derivation (mid8 disambiguation) (WP03)

**Implementation sketch**: In `agent/mission.py` (`mission create` subcommand), after `mission_id` / `mid8` / `mission_slug` are minted, compute the coordination branch name and call `git branch <name> <target_branch>` (or reuse if it exists). Update `meta.json` to include `coordination_branch` field. Update the JSON output schema.

**Risks**:
- The coordination branch must be created BEFORE finalize-tasks runs, since lane branches will parent off it.
- If the branch exists at a non-ancestor commit of target, the runtime must refuse with a clear error (no auto-recovery).

**Dependencies**: WP02.

**Prompt**: [tasks/WP03-mission-create-coordination-branch.md](tasks/WP03-mission-create-coordination-branch.md)

---

## Work Package WP04: CoordinationWorkspace service + lane sparse-checkout policy

**Goal**: New `src/specify_cli/coordination/workspace.py` module hosting the `CoordinationWorkspace` service. Lane worktree creation registers the sparse-checkout pattern that excludes `status.events.jsonl` and `status.json` from lane working trees. Doctor command gains coordination-worktree and sparse-checkout drift checks. (Spec: FR-024, FR-025, FR-029, C-011, RR-01.)

**Priority**: P1 — required before BookkeepingTransaction (WP05) has somewhere to write.

**Independent test**: An integration test creates a lane worktree and asserts `.git/info/sparse-checkout` contains the expected exclusions and the worktree's working tree does NOT contain the status files.

**Estimated prompt size**: ~400 lines.

**Included subtasks**:
- [ ] T015 `CoordinationWorkspace` service: resolve/create/teardown coordination worktree (WP04)
- [ ] T016 Sparse-checkout policy registration at lane worktree creation (`LANE_SPARSE_CHECKOUT_EXCLUSIONS`) (WP04)
- [ ] T017 Lane allocator updates: parent lane branches on coordination branch (WP04)
- [ ] T018 Unit tests: coordination worktree lifecycle; sparse-checkout drift detection (WP04)
- [ ] T019 Doctor command: sparse-checkout drift + coordination worktree health checks (WP04)

**Implementation sketch**: Create `src/specify_cli/coordination/__init__.py` and `workspace.py`. `CoordinationWorkspace.resolve(repo_root, mission_slug, mid8)` runs `git worktree list --porcelain` to find the worktree; creates via `git worktree add` if missing. The lane allocator (existing module — likely `src/specify_cli/lanes/`) gains a step that runs `git sparse-checkout init --no-cone` and writes the exclusion patterns. Doctor command gains `_check_coordination_worktree_health()` and `_check_sparse_checkout_drift()`.

**Risks**:
- Sparse-checkout requires `git >= 2.25`. Check the version and emit a clear error on older git.
- Operators may manually edit `.git/info/sparse-checkout`. Doctor must detect drift.

**Dependencies**: WP03.

**Prompt**: [tasks/WP04-coordination-workspace-sparse-checkout.md](tasks/WP04-coordination-workspace-sparse-checkout.md)

---

## Work Package WP05: BookkeepingTransaction + WorkflowMutationPolicy modules

**Goal**: New module `src/specify_cli/coordination/transaction.py` hosting `BookkeepingTransaction` (context manager that owns coordination-tree writes). New `policy.py` hosting `WorkflowMutationPolicy.assert_allowed()`. Both built on the existing feature status lock (`locking.py`). Surgical truncate rollback path. Deferred outbound side effects. (Spec: FR-019, FR-020, FR-021, FR-023, FR-026, NFR-001, NFR-008, NFR-010, C-013, I-1, I-7.)

**Priority**: P1 — core of the atomicity contract; the most architecturally important WP.

**Independent test**: A unit test acquires a transaction, appends an event, forces the inner `safe_commit()` to fail (mock or pre-commit hook), and asserts the SHA-256 of `status.events.jsonl` is identical pre/post (NFR-001).

**Estimated prompt size**: ~500 lines (the biggest core module).

**Included subtasks**:
- [ ] T020 `GitChangeSet` value object + `PolicyVerdict` sum type (WP05)
- [ ] T021 `WorkflowMutationPolicy.assert_allowed()` — single chokepoint with stable error codes (WP05)
- [ ] T022 `BookkeepingTransaction` context manager: acquire/append_event/commit/rollback/release (WP05)
- [ ] T023 Surgical truncate rollback path with `pre_emit_size` capture (WP05)
- [ ] T024 Outbound-deferral mechanism (`defer_outbound`) inside transaction (WP05)
- [ ] T025 Unit tests: full transaction lifecycle, refusal, rollback, nested-lock blocking (WP05)

**Implementation sketch**: Create `GitChangeSet` dataclass (frozen, kw-only). Create `Allowed` / `Refused` dataclasses. `WorkflowMutationPolicy.assert_allowed(change_set)` checks `destination_ref` for protected-branch / not-found / remote-only / invalid-shape. `BookkeepingTransaction.acquire(...)` resolves coordination worktree (delegates to WP04), acquires lock (`locking.py`), captures `pre_emit_size = os.path.getsize(events_path)`, runs policy gate. `__exit__` on exception truncates and re-materializes. Outbound callbacks are queued and run after commit success.

**Risks**:
- The lock-acquisition timeout must be tunable; default 30s.
- The rollback path itself must be idempotent (if rollback fails, the original error is preserved and the rollback error is chained).

**Dependencies**: WP04.

**Prompt**: [tasks/WP05-bookkeeping-transaction-policy.md](tasks/WP05-bookkeeping-transaction-policy.md)

---

## Work Package WP06: Migrate workflow call sites to BookkeepingTransaction

**Goal**: Update the four critical workflow call sites identified in the cross-review — `implement.py:236` (planning artifacts), `workflow.py:689` and `:1463` (lifecycle status writes), and `emit.py:468` (event emit pipeline) — to route through `BookkeepingTransaction`. Add the implement/review commit-summary terminal output (FR-014). (Spec: FR-005, FR-009, FR-010, FR-011, FR-014, FR-019, FR-020, FR-022, SC-03, SC-05/06.)

**Priority**: P1 — the call sites whose bugs are issue #1348.

**Independent test**: An integration test runs the 2-lane quickstart scenario (`quickstart.md` § "Implement first WP, first lane") and asserts the tracking commit landed on the coordination branch, the event is in `status.events.jsonl`, and `git log main` is unchanged. Forced pre-commit hook reject runs the rollback; SHA-256 of event log is byte-identical pre/post.

**Estimated prompt size**: ~480 lines.

**Included subtasks**:
- [ ] T026 Migrate planning-artifact commit site (`implement.py:236`) → `BookkeepingTransaction` (WP06)
- [ ] T027 Migrate lifecycle status writes (`workflow.py:689`, `:1463`) → `BookkeepingTransaction` (WP06)
- [ ] T028 Migrate event emit pipeline (`emit.py:468`) → `BookkeepingTransaction` (WP06)
- [ ] T029 Implement/review terminal output: commit-summary section (FR-014) (WP06)
- [ ] T030 Integration tests: 2-lane mission happy path; forced commit failure → rollback (WP06)

**Implementation sketch**: For each of the four call sites, replace the existing `safe_commit()` call with a `with BookkeepingTransaction.acquire(...) as txn:` block. Inside the block, call `txn.append_event(event)` (for emit), `txn.write_artifact(path, content)` for planning artifacts, or `txn.stage_path(path)` for already-modified files. The commit happens implicitly on `__exit__`. Add the commit-summary printout: collect `EventReceipt`s from each transaction; print a table of (commit_message, destination_ref, outcome).

**Risks**:
- The four call sites have subtly different semantics (event emit vs planning-artifact write vs lifecycle write). Each migration must preserve the existing behavior beyond the routing change.
- The commit-summary section must be both human-readable (Rich console) and JSON-parseable (for scripted use).

**Dependencies**: WP05.

**Prompt**: [tasks/WP06-migrate-workflow-call-sites.md](tasks/WP06-migrate-workflow-call-sites.md)

---

## Work Package WP07: Two-stage merge + finalize-tasks fix

**Goal**: `spec-kitty merge` implements the two-stage merge (lane → coordination, then coordination → target). Fix `_resolve_planning_branch()` in `mission.py:321` to return the canonical merge target rather than the current checkout branch. Mission close teardown removes coordination worktree, coordination branch, and lane branches. (Spec: FR-008, FR-012, FR-016, SC-04, SC-10.)

**Priority**: P1 — required for missions to actually complete and ship.

**Independent test**: An end-to-end test runs a 2-lane mission to completion and asserts: lane code is on `main` (via coordination branch); coordination branch is deleted; lane branches are deleted; `.worktrees/<slug>-<mid8>-*` are all removed. A second test runs `finalize-tasks` from a `prep/` branch and asserts `merge_target_branch: main` in WP frontmatter.

**Estimated prompt size**: ~420 lines.

**Included subtasks**:
- [ ] T031 Fix `_resolve_planning_branch()` in `mission.py:321` → returns canonical merge target (WP07)
- [ ] T032 Two-stage merge: lane → coordination → target; lane integration events (WP07)
- [ ] T033 Mission close teardown: delete coordination worktree + coordination branch + lanes (FR-016) (WP07)
- [ ] T034 Integration tests: finalize-tasks from prep branch; full multi-lane merge → target (WP07)

**Implementation sketch**: Edit `mission.py` to compute target branch from `meta.json` (which already holds the canonical value from `mission create`). Update `spec-kitty merge` (likely in `src/specify_cli/cli/commands/merge.py`) to: (1) for each WP in dependency order, merge lane → coordination, record a `lane_integrated` tracking event via BookkeepingTransaction; (2) merge coordination → target; (3) teardown via `CoordinationWorkspace.teardown(...)` and `git branch -d` for each lane and the coordination branch.

**Risks**:
- Lane integration may surface real code conflicts. Handle via the existing interactive merge UX.
- Teardown must be idempotent: if the operator already deleted a worktree, the teardown step is a no-op.

**Dependencies**: WP06.

**Prompt**: [tasks/WP07-two-stage-merge-finalize-tasks.md](tasks/WP07-two-stage-merge-finalize-tasks.md)

---

## Work Package WP08: Legacy mission fallback + CLI status mediation

**Goal**: Missions created before this change (no coordination branch) continue to function — same pre-flight gate, lock, transaction, rollback, only the `destination_ref` differs (resolves to lane branch instead). `spec-kitty agent tasks status` and `agent context resolve` read from the coordination worktree regardless of operator CWD. (Spec: FR-017, FR-027, FR-030, SC-11.)

**Priority**: P1 — closes #1348 for in-flight missions, not just new ones.

**Independent test**: An integration test creates a fixture mission with the legacy topology (lanes parented on `main`, no coordination branch). Runs `implement` and forces a commit failure on the lane branch; asserts no dangling event-log append, no commit on the lane branch attempted before pre-flight refusal of a protected destination. A second test runs `spec-kitty agent tasks status --mission <handle>` from inside a lane worktree and asserts the output matches a query from the primary checkout.

**Estimated prompt size**: ~360 lines.

**Included subtasks**:
- [ ] T035 Legacy mission detection: missing coordination branch → lane-branch destination_ref (WP08)
- [ ] T036 Apply pre-flight + transaction + rollback uniformly to legacy missions (FR-017, FR-027) (WP08)
- [ ] T037 CLI status mediation: `agent tasks status` / `agent context resolve` read coordination worktree (WP08)
- [ ] T038 Integration tests: legacy mission regression + CLI mediation from lane CWD (WP08)

**Implementation sketch**: In `BookkeepingTransaction.acquire(...)`, check whether `CoordinationWorkspace.is_present(...)` returns True. If not (legacy mission), resolve the worktree to the operator's lane worktree, set `destination_ref` to the lane branch, emit a one-time warning. The rest of the transaction flow is unchanged. For CLI mediation, every read-side command (`tasks status`, `context resolve`, `decision verify`, `doctor`) calls a single helper `resolve_mission_read_path(mission_handle)` that returns the coordination worktree (new topology) or the primary checkout (legacy).

**Risks**:
- The "one-time warning" must not spam operators. Use a per-mission marker file (`.kittify/legacy-warning-shown-<mission_id>`) to suppress after first emit.
- CLI mediation can subtly change behavior for some scripts that hard-coded paths. Document in CHANGELOG.

**Dependencies**: WP07.

**Prompt**: [tasks/WP08-legacy-fallback-cli-mediation.md](tasks/WP08-legacy-fallback-cli-mediation.md)

---

## Work Package WP09: Hardening — architectural test + stress + regression coverage

**Goal**: Architectural test that prevents future regressions by forbidding direct `safe_commit` imports from transactional workflow modules. Stress test for SC-12 (concurrent emit ordering). Issue #1348 regression test. SaaS-sink fanout deferral instrumentation. (Spec: FR-022, NFR-009, SC-06, SC-09, SC-12.)

**Priority**: P2 — optional; can ship in a follow-up release.

**Independent test**: The architectural test refuses to pass if any new module under `src/specify_cli/cli/commands/agent/` directly imports `safe_commit`. The stress test runs 20 concurrent `implement` calls in subprocess and asserts no interleaved partial writes in `status.events.jsonl`. The #1348 regression test reproduces the exact sequence from the issue and asserts it does not reproduce.

**Estimated prompt size**: ~320 lines.

**Included subtasks**:
- [ ] T039 Architectural test: forbid direct `safe_commit` imports from transactional workflow modules (WP09)
- [ ] T040 Stress test: 20 concurrent `implement` calls; verify no interleaved writes (SC-12) (WP09)
- [ ] T041 SaaS-sink fanout deferral instrumentation + mock-sink test fixture (NFR-009) (WP09)
- [ ] T042 Issue #1348 regression test: exact reproduction sequence; verify fix holds (WP09)

**Implementation sketch**: The architectural test uses `ast.parse` to scan target modules and detect `from specify_cli.git.commit_helpers import safe_commit` or equivalent. The stress test uses `multiprocessing` to spawn N subprocess workers, each running an `implement` against the same mission with a different WP. The mock SaaS sink fixture records every call and exposes a `clear()`/`get_calls()` API. The #1348 regression test asserts the bug-reproducing sequence (event on main, commit blocked, on-disk advance) does not happen on either topology.

**Risks**:
- Stress test may be slow in CI; target < 60s budget. May need to be in a `@pytest.mark.slow` or `@pytest.mark.stress` group.
- The architectural test must not be too restrictive (it should still allow `safe_commit` in test files and in helpers under `src/specify_cli/coordination/`).

**Dependencies**: WP08.

**Prompt**: [tasks/WP09-hardening-tests-regression.md](tasks/WP09-hardening-tests-regression.md)

---

## Parallelization Opportunities

After the linear dependency through WP01 → WP02 → WP03, the following parallelism is available:

- **Lane B** (foundation): WP03 → WP04 → WP05 (must be sequential within the lane; the coordination branch must exist before the worktree, the worktree before the transaction).
- **Lane C** (workflow migration): WP06 → WP07 → WP08 (sequential within the lane).
- **Lane D** (hardening): WP09 can start as soon as WP05 is reviewed (the architectural test and stress test only need the transaction service to exist). It runs in parallel with WP06–WP08.

Realistic parallelism: 2 lanes after WP02 lands; 3 lanes after WP05 lands.

---

## Risk-to-WP map

| Risk (from plan.md) | Owning WP   |
| ------------------- | ----------- |
| RR-01 (git ≥ 2.25)  | WP04 (sparse-checkout requires it; doctor check) |
| RR-02 (lane code conflicts) | WP07 (two-stage merge) |
| RR-03 (external script breakage) | WP02 (deprecation env var) |
| RR-04 (sparse-checkout drift) | WP04 (doctor check) |
| RR-05 (legacy destination_ref skew) | WP08 (HEAD assertion in legacy mode) |
| RR-06 (coord worktree deleted out-of-band) | WP04 (idempotent re-creation) |
| RR-07 (pre-commit hook mutates files) | WP06 (commit-summary surfaces this) |

---

## Definition of Done — Mission

The mission is `accepted` and ready to merge when:
- All 9 WPs reach `approved`.
- `pytest` passes with ≥ 90% line coverage on new modules.
- `mypy --strict` passes with zero errors.
- The 12 Success Criteria (SC-01..SC-12) all have at least one passing test.
- The `quickstart.md` walkthrough runs end-to-end without manual intervention.
- CHANGELOG entries for PR 1 (WP01+WP02) and PR 2 (WP03..WP08) are written.
- `spec-kitty doctor` reports zero issues on a fresh mission created on the new topology.
- The issue #1348 reproduction sequence (T042) is verified to fail on `main`.

---

## Next step

After WPs are finalized (`spec-kitty agent mission finalize-tasks`), the lane allocator will assign concrete lanes. Then run `spec-kitty next --agent <agent> --mission mission-coordination-branch-atomic-event-log-01KSPTVW` to begin implementation.
