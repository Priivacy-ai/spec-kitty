# Research: Mission Coordination Branch with Atomic Event Log

This document captures the architectural decisions made during specify + plan interrogation, along with rationale and alternatives considered. Format follows the ADR-lite pattern from the charter's `adr-drafting-workflow` tactic.

---

## R-001 — Merge strategy for `status.events.jsonl`

**Decision**: Linearize via lock-only writes. `status.events.jsonl` is **exclusively coordination-branch-authored** by `BookkeepingTransaction`. Lane branches MUST NOT contain commits that modify it. Lane integration merges (lane → coordination) bring code only. (Spec: FR-028, C-014.)

**Rationale**: The 3.0 status model declares the event log as the sole authority for WP lane state. Any architecture where lane branches author their own event-log changes — even append-only — violates this in subtle ways:
- Two lanes can write events about the same WP without conflict markers (line-concat merge "succeeds" but the resulting log has impossible chronology).
- A query from a non-merged branch returns a different lane state than a query from a different branch.
- "Sole authority" becomes "sole authority *after* merge," which is operationally insufficient for long-running parallel missions.

Centralizing writes through `BookkeepingTransaction` on the coordination branch (under the feature status lock) yields exactly one `status.events.jsonl` per mission. Queries from any worktree return the same answer (via CLI mediation, R-004). No merge driver, no rebase complexity.

**Alternatives considered**:

1. **Stock `git rebase` + JSONL append-only invariant.** Rejected: stock rebase sees byte-level conflicts when two lanes append at line N, even if event_ids differ. The "re-emit on top of B's" framing hides a structured replay that the CLI would have to perform — at which point you've reinvented option 2 with more steps.
2. **Custom git merge driver.** Rejected: the distribution problem. Merge drivers are pinned per-repo in `.git/config`, not in the tree. Every clone, every CI runner, every fork must register the driver. First-time contributors hit "merge succeeded but data is wrong because the driver wasn't registered" — same class of bug spec-kitty already fights elsewhere.
3. **Lock-only linearization** (chosen). Real cost is making the emit pipeline cross-tree-aware via `BookkeepingTransaction`. Bounded; has the useful side effect of eliminating the working-tree-vs-HEAD race because the working tree being modified is always the coordination tree, which the lock guarantees no one else is touching.

**Consequences**:
- Lane worktrees must exclude `status.events.jsonl` and `status.json` from their working tree (R-003).
- Lane-side reads must go through CLI mediation (R-004).
- The earlier draft's "Scenario C: concurrent emit during rollback" is impossible under the lock and was removed from the spec.

---

## R-002 — Where `destination_ref` enters

**Decision**: `safe_commit()` gains a **required keyword-only `destination_ref` parameter** and an internal `HEAD == destination_ref` assertion. `BookkeepingTransaction` is a higher-level wrapper that ensures the coordination worktree is on `destination_ref` before delegating, but the helper-level assertion is the **ultimate gate** against silent commit-target drift. (Spec: FR-031, C-015.)

**Rationale**: A `destination_ref` parameter that is only used as a policy label is decorative. Git commits go to whatever ref the working tree's HEAD currently points at. If `WorkflowMutationPolicy.assert_allowed(destination_ref="kitty/mission-foo")` passes, but the subsequent `safe_commit()` runs in a worktree checked out to `main` or to a different lane, the actual commit lands on the wrong branch. Policy passes; reality diverges. **That is the same failure mode as #1348**, just with the staging point shifted by one layer.

`destination_ref` must therefore be a **commit-target contract**, not a policy label. The HEAD assertion makes the parameter load-bearing: the helper refuses to operate when the worktree HEAD doesn't match the declared target.

Once Layer 1 is in place, future callers cannot silently land commits on the wrong branch — even ones that bypass `BookkeepingTransaction`. mypy catches missing-arg regressions structurally; the assertion catches mismatched-HEAD at runtime, surfaced loudly by tests.

**Alternatives considered**:

1. **Separate `WorkflowMutationPolicy.assert_allowed()` called before `safe_commit()`, with `safe_commit()` unchanged.** Rejected: makes `destination_ref` a policy label rather than a commit-target contract. Any future workflow mutation that bypasses the transaction layer and calls `safe_commit()` directly — code-review oversight, a quick-fix that didn't get a transaction wrapper, a migration that forgot — silently lands commits on the wrong branch. The structural property doesn't hold.
2. **Add optional `destination_ref` to `safe_commit()`, default to current branch.** Rejected: provides escape hatches that recreate the current asymmetric-bypass class of bugs. Defaults that infer from HEAD are exactly what C-012 prohibits.
3. **Helper-level required parameter + HEAD assertion** (chosen). Largest mechanical diff (every caller must be updated) but the property is structurally enforced for all current and future callers. PR ordering (R-005) splits the work so PR 1 lands the helper invariant first; PR 2 builds the transaction layer on a foundation that already enforces commit-target correctness.

**Consequences**:
- Every existing `safe_commit()` call site in the codebase must be audited and migrated. Most are mechanical (`destination_ref = current_branch`).
- The public `spec-kitty safe-commit` CLI gains required `--to-branch` or resolves via the existing branch-context resolver and passes explicitly.
- A structured error is added: `SAFE_COMMIT_HEAD_MISMATCH` with destination_ref, observed_head, and worktree_path fields.

---

## R-003 — Lane worktree composition

**Decision**: Lane worktrees use **sparse-checkout** to exclude `kitty-specs/<mission>/status.events.jsonl` and `kitty-specs/<mission>/status.json` from their working tree. The lane allocator registers the sparse-checkout pattern at worktree creation time. (Spec: FR-029.)

**Rationale**: Two options offered the same end-state (lane worktrees cannot accidentally edit status files):

- **Sparse-checkout**: preserves the file paths under `kitty-specs/<mission>/`. The primary checkout (and the coordination worktree) see the files normally. The lane worktree sees nothing at those paths. Backward-compatible with all existing tooling that reads from `kitty-specs/<mission>/status.json` because that tooling runs from the primary checkout / coordination worktree, never the lane. Stock git feature since 2.25.

- **Filesystem boundary move**: relocate status files to `.kittify/missions/<mission>/`. Cleaner architectural separation (data lives outside `kitty-specs/`, which is reserved for spec/plan/tasks artifacts). Cost: 3.0→3.x data migration, every existing reader must be updated, breaks scripts that point at `kitty-specs/<mission>/status.json`.

The sparse-checkout option ships in one PR and requires zero existing-tooling updates. The filesystem move is *cleaner long-term* but a much larger scope shift that is orthogonal to issue #1348's fix. We can revisit the filesystem move in a future mission once this one has stabilized.

**Alternatives considered**:

1. **Filesystem boundary move** (rejected for this mission). Better long-term hygiene but pulls in a data migration that is not part of #1348's scope.
2. **`.gitattributes` merge=ours**: would let lane branches keep their own copies but always defer to coordination on merge. Rejected: the lane's local copy can drift from truth between commits, lane agents can still mutate it accidentally, and "merge=ours" silently discards differences. Sparse-checkout makes the file *not exist* in the lane, which is unambiguous.
3. **Sparse-checkout** (chosen). Backward-compatible, in-tree config, doctor-checkable.

**Consequences**:
- Minimum git version becomes 2.25 (the version where `git sparse-checkout` became stable). Documented in CHANGELOG and CI matrix.
- `spec-kitty doctor` gains a sparse-checkout drift check (RR-04).
- Lane-side reads of status must go through CLI mediation (R-004).

---

## R-004 — Lane-side reads of mission status

**Decision**: Lane-side reads MUST go through **CLI mediation**. `spec-kitty agent tasks status --mission <handle>` and `spec-kitty agent context resolve --mission <handle>` resolve the coordination worktree path and read from there, regardless of the operator's CWD. No on-disk snapshot mirror in scope. (Spec: FR-030.)

**Rationale**: Lane worktrees do not contain `status.events.jsonl` or `status.json` (R-003). Any read needs to reach the coordination worktree. Two paths:

- **CLI mediation**: every read-side query becomes a CLI invocation; the CLI knows where the truth lives (coordination worktree resolved by mission handle). Simple, matches the existing `--mission <handle>` plumbing, no per-lane state to maintain.

- **Read-only mirror in the lane**: `spec-kitty agent context resolve` materializes a stale snapshot of status into a known path in the lane (e.g. `.spec-kitty/mission-status-snapshot.json`), refreshable on demand. Faster for repeated reads inside a single agent session, but introduces a freshness/refresh contract that adds complexity.

CLI mediation is the default. The snapshot mirror is an optimization for a future ticket if profiling shows repeated CLI calls are a bottleneck (unlikely — each call is sub-100ms on a typical event log).

**Alternatives considered**:

1. **Read-only mirror** (rejected for this mission). Optimization without a measured need.
2. **Read directly from the lane's view of `kitty-specs/<mission>/`** (rejected — see R-003: the file doesn't exist in the lane).
3. **CLI mediation** (chosen).

**Consequences**:
- Any agent doing more than ~100 status reads per minute may see a small overhead; profiling target: < 100ms per read.
- The CLI's `--mission` handle resolver is reused; no new code path for handle resolution.

---

## R-005 — PR ordering

**Decision**: Three-PR sequence:
1. **PR 1**: Helper-level invariant. `safe_commit(destination_ref=...)` + HEAD assertion + audit + migrate every caller. CHANGELOG entry. Tests.
2. **PR 2**: Coordination branch topology + `BookkeepingTransaction` + sparse-checkout + workflow call-site migration + two-stage merge + legacy fallback.
3. **PR 3 (optional)**: Architectural test forbidding direct `safe_commit` imports from transactional modules; optional rename to `_safe_commit_unchecked`.

**Rationale**: The cross-review explicitly preferred this ordering. After PR 1 lands, the structural property (no commit can silently land on the wrong branch) holds for every current and future caller. PR 2 then builds the transaction layer on a foundation that already enforces commit-target correctness — making PR 2 simpler because the failure mode the spec was guarding against can't occur anymore in PR 2 code paths.

PR 3 is hardening that prevents future regressions but is not required to fix issue #1348. It can ship in a follow-up release.

**Alternatives considered**:

1. **Single mega-PR** (rejected). High blast radius, hard to review, all-or-nothing rollout.
2. **PR 1 = transaction layer; PR 2 = helper invariant** (rejected). PR 1 would ship without the structural property in place, leaving the bug class C-012 exists to prevent. Even with all current callers audited, future callers could drift.
3. **Helper first, then transaction, then hardening** (chosen).

**Consequences**:
- Each PR is independently shippable in the sense that PR 1 makes the codebase safer in isolation (fixes silent commit-target drift) and PR 2 makes it correct (closes #1348's specific reproduction).
- Coordination tests that exercise the full multi-lane workflow live in PR 2.

---

## R-006 — Legacy mission migration strategy

**Decision**: Legacy missions (no coordination branch present) continue to run under the same pre-flight gate, lock, transaction, and rollback machinery — only the `destination_ref` resolves differently (to the lane branch instead of a coordination branch). No automatic migration of in-flight legacy missions. The new topology applies to missions created after PR 2 lands. (Spec: FR-017, FR-027.)

**Rationale**: The issue #1348 reproduction can occur on any mission that uses `safe_commit()` via the old code paths. The minimum fix is: pre-flight gate + atomic lock + rollback apply universally. Whether the destination ref is a coordination branch or a lane branch is orthogonal to whether the bug class is closed.

Forcing existing in-flight missions to migrate would require a non-trivial git surgery (rebase lane branches onto a freshly minted coordination branch, transplant the event log). Operators may have weeks of context in their lane worktrees; an automatic migration is a footgun.

**Alternatives considered**:

1. **Automatic migration on first invocation post-upgrade** (rejected). Footgun for operators with in-flight work.
2. **Hard cutover: refuse legacy missions until manually migrated** (rejected). Worst possible UX.
3. **Legacy fallback with same invariants** (chosen). Closes #1348 for both old and new missions; operators can opt in to the new topology by starting a new mission or by running a documented manual migration in a future ticket.

**Consequences**:
- The doctor command surfaces "this mission is on the legacy topology; migrate via X" guidance (out of scope for this mission, but documented).
- Tests cover both topologies (SC-08 for new, SC-11 for legacy).

---

## R-007 — Test surface for atomicity

**Decision**: Atomicity is verified by:
1. SHA-256 equality of `status.events.jsonl` pre/post a forced commit failure (NFR-001, SC-05).
2. Mock SaaS sink count = 0 for the rolled-back transition (NFR-009, SC-09).
3. Multi-process stress test with 20 concurrent `implement` calls; verify no interleaved partial writes (SC-12).
4. Specific reproduction of issue #1348's sequence (event on main, commit blocked, on-disk state divergent); verify the reproduction fails (SC-06).

**Rationale**: Three independent failure modes need verification:
- Local atomicity (file system): rollback restores byte-identical pre-state.
- Outbound atomicity (external state): SaaS sink never sees rolled-back events.
- Concurrent atomicity: lock-based linearization prevents interleaved writes under realistic concurrency.

The #1348-specific regression test guards against re-introduction.

**Consequences**:
- Test infrastructure gains a mock SaaS sink fixture (decorator-based; per-test reset).
- Multi-process tests run in CI but may be slow (target: stress test < 60s on a typical runner).
