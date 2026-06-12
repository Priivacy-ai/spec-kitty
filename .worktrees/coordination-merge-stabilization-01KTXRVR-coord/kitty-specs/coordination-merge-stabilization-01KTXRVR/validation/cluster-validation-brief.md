# Handoff Brief: Coordination & Merge Stabilization for 3.2.0
**For:** `/spec-kitty.specify` discovery interview
**Date:** 2026-06-12 | **Repo HEAD:** 956ab0e3e | **Sources:** debbie-analysis.md, paula-analysis.md, recon digest (13 issues)

---

## 1. Mission Intent

Stabilize the validated coordination/merge bug cluster for the 3.2.0 release by closing the three live root-cause classes (coord-worktree ref-resync, fake-read-only checkout mutation, workspace fall-through trust) plus narrow residuals of two drained classes — **stability only, no architecture rework**. The cluster's structural spine (coord-vs-primary execution-context split-brain) was already drained at HEAD by PR #1850 / commit 8544012fa, rc42 (9c8bff06f), and rc41 (c5a10ce56); this mission ships the remaining small, well-localized fixes and regression ratchets so the class cannot silently return, and explicitly defers the resolver/allocator unification strangler work to a follow-up umbrella under epic #1666.

---

## 2. Confirmed In-Scope Issues

| # | Verbatim title | Root-cause class | Fix shape (smallest safe action) |
|---|---|---|---|
| **#1826** | spec-kitty merge: coordination worktree falls behind its own branch mid-merge, tripping the safe_commit backstop ("working tree is behind HEAD") | **Class B** — ref-advance without checked-out-worktree resync (only fully-VALID issue; release **BLOCKER**) | After each `update-ref` advancing the coord/mission branch (`lanes/merge.py:440,474`; `cli/commands/merge.py:993-998`), resync any worktree with that branch checked out (`git -C <coord> reset --hard <branch>` under the feature-status lock), or self-heal index-behind-HEAD in `BookkeepingTransaction._acquire_locked`. ~20 lines, localized. |
| **#1861** (Part 1 only) | finalize-tasks --validate-only switches the git checkout (not non-mutating); safe-commit --to-branch bounces the checkout back | **Class C** — nominally read-only command mutating checkout state (release **BLOCKER**, trivial) | Gate `mission.py:2462` `_ensure_branch_checked_out` behind `not validate_only`. One-line guard; post-WP07 reads already anchor on the primary feature dir. Part 2 is already retired (SafeCommitHeadMismatch, 8e79b3f6d) — issue update only. |
| **#1833** (residuals only) | agent action review claim mints mid8-slug HUSK directories in .worktrees/; move-task resolves them over the real worktrees | **Class D** — workspace-resolution fall-through treated as success (strongly recommended) | Three coordinated guards, one invariant ("fall-through is failure"): (a) `ResolvedWorkspace.exists` requires `.git` marker (`workspace/context.py:148-150`); (b) move `ReviewLock.acquire` after the workspace existence/creation block and promote `git worktree add` failure from warning to error (`workflow.py:2237/2243/2265`); (c) move-task asserts `git -C <path> rev-parse --show-toplevel == <path>` before any git call (`agent/tasks.py:1346`) → structured resolution-failure error. Naming trigger already fixed in #1850. |
| **#1814** (residual only) | record-analysis refuses on coord-residue: primary-checkout dirty-tree check deadlocks coord-topology missions | **Class A residual (A-r1)** — finalize staging leaves untracked residue on primary checkout (strongly recommended) | Have `_stage_finalize_artifacts_in_coord_worktree` (`mission.py:99-131`) clean up (or never create) its primary-side copies of `lanes.json`/`tasks/*`/matrices — cleanup at source, NOT widening the `COORD_OWNED_STATUS_FILES` exclusion list. Named status-file deadlock already fixed (#1850 WP06). |
| **#1736** (residuals only) | Three merge bugs exposed by coordination-branch topology: PATH, mixed JSONL timestamps, StrEnum sentinel | **Class F** — merge-driver env/schema hardening debt (strongly recommended, hours not days) | One small PR: extract `_make_merge_env()` in `lanes/merge.py` + ratchet test that every subprocess call uses it; narrow `status_transition.py:399-400` `except Exception` to `(ValueError, FileNotFoundError)` with documented GENESIS fallback; add mixed `at`/`timestamp`/neither sort ratchet test. Bugs A/B/C already fixed. |
| **#1735** (residuals, fold into Fix 4) | retrospect create: completion gate reads primary checkout event log instead of coord worktree surface | **Class A residual (A-r2)** — coord-unaware direct event reads | Route `retrospective/gate.py:597` and `agent_retrospect.py:432` through `resolve_status_surface`; add AC7 "identity-only" docstring to `ResolvedMission.feature_dir`; AC10 architectural ratchet (extend `test_execution_context_parity.py`). Core fix landed (#1850 WP08). |
| **#1827** (test gap + edge only) | spec-kitty merge: post-merge baseline validation runs before the tool writes baseline_merge_commit — circular failure | **Class A residual (A-r3)** — missing regression coverage | Add coord-topology baseline-recording regression test (unmock helpers in `test_merge_coord_topology_1772.py:224-225` or sibling); note the crash-between-record-and-commit re-run edge. Defect itself fixed in rc42 (9c8bff06f). |
| **#1784** (P3 crumbs, optional) | 3.2.0rc40: finalize-tasks branch-model catch-22 + rough edges | **Class C-adjacent polish** | Suppress "Upgrade complete!" on `--dry-run` (`upgrade.py:987`); make safe_commit backstop message (`commit_helpers.py:321-339`) name the actual divergence cause (dovetails with #1826 fix). Catch-22 core fixed in #1850 (dup of #1777). |

### Exclusions (recon found FIXED at HEAD — issue hygiene only, no code)

| # | Reason for exclusion |
|---|---|
| **#1770** (merge baking gitignored path) | FIXED — PR #1793 (c5a10ce56, FR-035/FR-037 tempdir bake) + PR #1850 acceptance anchor; CHANGELOG lists it drained. Close-as-fixed. |
| **#1789** (sync daemons/dashboard re-materialize status.json + daemon leak) | FIXED — PR #1850 WP11/WP12 (git-op guard, write-free snapshot, scoped reaper) with regression tests. Close-as-fixed. |
| **#1816** (implement-claim planning-artifact split) | FIXED — PR #1850 WP06 unified CommitTarget/FLATTENED classification with regression tests. Close-as-fixed. |
| **#1771** (retrospect writes to gitignored .kittify/missions/) | FIXED — PR #1850 WP08, FR-006 canonical tracked path + `test_record_committable_1771.py`. Close-as-fixed. ADJACENT mechanism anyway (write-target path, not git-op breakage). |
| **#1571** (merge blocked by local/origin divergence → reset --hard data loss) | FIXED — PR #1719 (2026-06-05), push-gated sync preflight + non-destructive remediation; superseded by #1706. ADJACENT (publish-layer policy, not cluster mechanism). Close-as-fixed. |
| **#1784 core** | FIXED — dup of #1777, landed via #1850 `resolve_placement_only` ("the literal #1784 fix"). Only the P3 crumbs above remain in scope. |
| **#1827 core** / **#1735 core** | FIXED (rc42 / #1850 WP08 respectively) — only the residuals listed in-scope above carry into this mission. |

**Issue hygiene task (in scope, no code):** close/update the seven stale-open fixed issues citing real landed commits — the tracker currently describes retired behavior and is the cluster's biggest triage-noise source (Debbie Fix 6).

---

## 3. Root-Cause Classes → Structural Fixes (Debbie), constrained to smallest-safe-release-action (Paula)

| Class | Structural defect | 3.2.0 ship-now shape |
|---|---|---|
| **B — ref-advance without worktree resync** (#1826) | Plumbing-level `git update-ref` from detached temp worktrees with no invariant that worktrees checking out that ref are resynced; only the primary checkout gets repaired (`merge.py:698-718`). The backstop is the detector working as designed. | Resync coord worktree after each of the 3 update-ref sites (or self-heal in `BookkeepingTransaction._acquire_locked`). Debbie's full `advance_branch_ref()` shared helper is acceptable if kept to merge-pipeline blast radius; assert the coord worktree carries no unique uncommitted state, fail loudly if dirty. |
| **C — fake-read-only commands** (#1861 P1) | Branch positioning treated as eager precondition, a "compatibility shim" from the pre-WP07 read model; fires before the first `validate_only` guard. | One-line `not validate_only` gate. Shim deletion deferred. |
| **D — fall-through treated as success** (#1833) | No layer enforces "resolved workspace must be an actual git worktree"; husk dirs pass `Path.exists()`, git calls fall through to the primary repo, `git worktree add` failure is a warning. | The three guards above (exists→.git marker, lock-after-create, rev-parse toplevel assertion). Ship with a doctor check listing/removing `.worktrees/*` entries lacking `.git` (pre-existing husks will now error explicitly — desired). |
| **A — split-brain residuals** (#1814/#1735/#1827) | Placement authority exists (`resolve_placement_only`/`resolve_status_surface`) but a few call sites are not behind it, and finalize staging generates residue. | Clean residue at source; route the two remaining direct reads through the surface resolver; add the AC10 ratchet and the baseline regression test. No resolver API changes. |
| **F — merge-driver hardening** (#1736) | Inline env construction, broad exception mask, missing mixed-schema ratchet. | Helper extraction + narrowed except + ratchet test, one small PR. |
| **E (background writers) and G (publish-layer)** | — | CLOSED at HEAD; verify existing ratchets stay green only. |

---

## 4. Explicit Non-Goals (Paula's follow-up split — file as ONE umbrella under epic #1666, do NOT do in 3.2.0)

- **No coordination-topology changes** and no changes to safe_commit semantics.
- **No resolver API redesign**: completing the strangler — all artifact reads/writes behind `resolve_placement_only`/`resolve_status_surface`, killing the implement.py legacy C-004 fallback — is follow-up.
- **No single ref-advance helper rollout beyond the merge pipeline** (the "retire all direct update-ref calls" invariant is follow-up; 3.2.0 only fixes the three known sites).
- **No worktree-naming allocator unification** (context.py:707 fallback vs core/worktree.py:252 / lanes/worktree_allocator.py:77) and no workspace-lifecycle or ReviewLock redesign.
- **No status-model changes, no daemon work** (Class E is closed; foreground `materialize()` writing tracked status.json is an accepted residual).
- **No deletion of the `_ensure_branch_checked_out` shim** (follow-up once the commit phase reads via plumbing).
- No `doctor.py` god-module split (#1623) or other deferred-debt items.

---

## 5. Known Risks / Dependencies (ordering constraints)

1. **Recommended order (Debbie):** issue hygiene (Fix 6, unblocks triage) → #1861 guard (one-liner) → #1826 (only live hard blocker) → #1833 guards → Class A residuals → Class F hardening. Fixes 1-5 are otherwise **mutually independent** and all 3.2.0-sized.
2. **#1826 ↔ #1784 backstop wording:** the improved safe_commit backstop message ("name which divergence") dovetails with the #1826 fix — land in the same WP or sequence backstop wording after the resync fix to avoid message churn.
3. **#1826 resync safety precondition:** resync (`reset --hard`) is safe only because the coord worktree carries no unique uncommitted state by design — the fix MUST verify and assert that precondition and fail loudly if the worktree is dirty (do not silently discard).
4. **#1833 husk-error blast radius:** pre-existing husk dirs on operator machines will start producing explicit errors; ship the doctor check in the same release so recovery is self-serve.
5. **#1814 cleanup vs exclusion-list:** choosing the writer-cleanup option means the `COORD_OWNED_STATUS_FILES` list stays narrow; do not also widen the list (double mechanism).
6. **#1736 except-narrowing:** narrowing `status_transition.py:399` may surface previously-swallowed errors in coord status reads; land after (or with) the #1826 resync so stale-worktree reads don't newly throw.
7. **Class B mask 11:** any new `update-ref` call site added during this mission inherits #1826 unless it goes through the helper — the ratchet test (no raw update-ref outside the helper) guards this.
8. **CI note:** terminology guard and `tests/architectural/` must stay green; new code must pass ruff+mypy with zero suppressions per project policy.

---

## 6. Acceptance Criteria Sketch (testable, per root-cause class)

**Class B (#1826):**
- AC-B1: Coord-topology mission with ≥2 lane merges + mission-number baking completes `spec-kitty merge` unattended — `_record_merged_wps_done_for_merge` commits without `SafeCommitBackstopError`. Test: `tests/specify_cli/cli/commands/test_merge_coord_worktree_resync_1826.py` (pattern: test_merge_coord_topology_1772.py).
- AC-B2: After each Stage-1 update-ref, coord worktree index == HEAD (assert directly).
- AC-B3: Ratchet — no raw `git update-ref` subprocess call exists outside the shared helper (if helper shape chosen).
- AC-B4: Resync refuses (loud error) if the coord worktree has uncommitted unique state.

**Class C (#1861 P1):**
- AC-C1: `finalize-tasks --validate-only` on a repo where mission target ≠ current branch leaves `git symbolic-ref HEAD` unchanged before/after and stages no files. Test: `test_finalize_tasks_validate_only_readonly.py`.
- AC-C2: Commit-phase finalize behavior unchanged (existing tests green).
- AC-C3: Issue #1861 updated: Part 2 recorded as resolved by `SafeCommitHeadMismatch` (8e79b3f6d).

**Class D (#1833):**
- AC-D1: Planted husk dir `.worktrees/<slug>-lane-a` (no `.git`): move-task approval fails with a structured resolution error — NOT "No implementation commits on lane branch!" and NOT a primary-repo dirty verdict. Test: `test_workspace_husk_resolution_1833.py`.
- AC-D2: `ResolvedWorkspace.exists` is False for the husk; review claim does not mkdir before worktree creation; failed `git worktree add` is a hard error, not a warning.
- AC-D3: Doctor check reports/removes `.worktrees/*` entries lacking `.git`.

**Class A residuals (#1814/#1735/#1827):**
- AC-A1: Untracked `lanes.json`/`tasks/WP01.md` residue on the primary checkout does not block record-analysis under coordination placement — and after finalize, no such residue exists on the primary checkout at all. Extend `test_wp06_sc2_paused_mission_blockers.py`.
- AC-A2: `retrospective/gate.py` and `agent_retrospect.py` status reads route through `resolve_status_surface`; AC10 architectural ratchet forbids `resolved.feature_dir` → `read_events()`/direct `status.events.jsonl` reads outside the surface resolver (extend `test_execution_context_parity.py`).
- AC-A3: Real (unmocked) `_record_baseline_merge_commit` + assert under coord topology: `git show <target>:kitty-specs/<slug>/meta.json` contains `baseline_merge_commit`.

**Class F (#1736):**
- AC-F1: Ratchet — every subprocess call in `_merge_branch_into` uses `_make_merge_env()`.
- AC-F2: `merge_event_payloads` sorts a mixed `at`/`timestamp`/neither log deterministically (`test_merge_event_payloads_mixed_at_timestamp_neither` in tests/status/test_event_log_merge.py).
- AC-F3: `status_transition.py` lane read catches only `(ValueError, FileNotFoundError)`; other exceptions propagate.

**Classes E/G (closed):**
- AC-EG1: Existing ratchets stay green: `tests/status/test_views_gitop_guard.py`, `tests/sync/test_daemon_singleton_reaper_consolidation.py`, `tests/retrospective/test_record_committable_1771.py`, `tests/architectural/test_execution_context_parity.py`.

**Hygiene:**
- AC-H1: #1770, #1789, #1816, #1771, #1571, #1827-core, #1784-core (dup #1777), #1735-core closed citing real landed commits (8544012fa, 9c8bff06f, c5a10ce56, 9f57ce4e); #1814/#1736/#1833/#1861 re-scoped to residuals.

---

## 7. Discovery-Interview Answers

- **Target version:** 3.2.0 (final; current rc line rc39-rc42).
- **Mission type:** bug-fix / stabilization (software-dev mission; no architecture/research mission needed).
- **Affected surfaces:**
  - `src/specify_cli/lanes/merge.py`, `src/specify_cli/cli/commands/merge.py` (Class B + F)
  - `src/specify_cli/coordination/workspace.py`, `coordination/transaction.py`, `coordination/status_transition.py` (B, F)
  - `src/specify_cli/git/commit_helpers.py` (backstop message only, polish)
  - `src/specify_cli/cli/commands/agent/mission.py` (C: validate-only guard; A: finalize residue cleanup)
  - `src/specify_cli/cli/commands/agent/workflow.py`, `review/lock.py`, `workspace/context.py`, `cli/commands/agent/tasks.py` (D)
  - `src/specify_cli/retrospective/gate.py`, `cli/commands/agent_retrospect.py`, `context/mission_resolver.py` (A residuals)
  - `src/specify_cli/cli/commands/upgrade.py` (P3 dry-run message)
  - Tests: `tests/specify_cli/cli/commands/`, `tests/status/`, `tests/architectural/`
- **Test strategy:** regression-test-first per class (the 8 tests in §6 / Paula §5); integration coverage for coord-topology merge end-to-end; architectural ratchet tests so each class cannot silently return (no-raw-update-ref, env-helper usage, AC10 read-surface ban); keep existing #1850/#1719 ratchets green; `pytest tests/`, `ruff check .`, mypy clean, plus `pytest tests/architectural/test_no_legacy_terminology.py` before push.
- **Observability requirement (cross-cutting, cheap):** failing layers must name the resolution they used (which worktree, which ref, which placement kind) rather than surfacing raw git errors — apply within the fixes for Classes B/D/F (Debbie §6).
- **WP shaping hint:** ~6 WPs — (1) issue hygiene, (2) #1861 guard, (3) #1826 resync + backstop message, (4) #1833 workspace invariant + doctor check, (5) Class A residuals + tests, (6) Class F hardening. Independent; only soft ordering per §5.
