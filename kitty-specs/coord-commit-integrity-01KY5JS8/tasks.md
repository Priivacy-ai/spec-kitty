# Tasks: Trusted mission-artifact commit path

**Mission**: `coord-commit-integrity-01KY5JS8` | **Branch**: `remediation/coord-trust-2841` (coord topology)
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md) | **Design**: [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

6 work packages. **Lane ownership (post-plan + post-tasks squads, corrected):** per `lanes.json` WP01=lane-a,
WP02=lane-b (`depends_on_lanes:["lane-a"]`), WP03=lane-c, WP04=lane-d, WP05=lane-e, WP06=lane-f. WP01 and WP02
share `agent/workflow_executor.py` but are in SEPARATE worktrees — WP02's out-of-map actor-seam edit is safe
via the **#1684 dependency-tip merge** (`lanes/worktree_allocator.py:99-159` merges WP01's approved tip into
WP02's base before WP02 edits), NOT "same worktree". IC-01 (WP01) and IC-03 (WP04) both call the ONE existing
`CoordinationWorkspace.resolve` authority (`workspace.py:232`) — **call-only, no new shared code**; if it's
insufficient for either, that becomes a blocking coordination point, not a parallel silent edit.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | NFR-002 live #2861 causation repro FIRST (records: FR-002 misroute vs FR-006 actor warning) | WP01 | |
| T002 | Campsite: extract `_handle_commit_failure`; delete dead `workflow.py:672 _resolve_git_common_dir` triplicate | WP01 | |
| T003 | FR-002(a) misroute-to-legacy fail-loud guard (`workflow_executor.py:~217`) | WP01 | |
| T004 | FR-002(b) legacy porcelain pre-check against the resolved worktree root (`workflow.py:~599`) | WP01 | |
| T005 | NFR-001 real-repo e2e (real `git worktree add`; `git show <ref>:<path>`; negative → `SafeCommitHeadMismatch`) | WP01 | |
| T006 | FR-005 widen `build_resolved_actor` (`emit.py:1077`) with self-asserted profile/model (no synthetic defaults, no fake binding) | WP02 | |
| T007 | FR-005 parse `--agent` at the 3 claim seams → bare tool (out-of-map `workflow_executor.py` actor seams, rationale-recorded) | WP02 | |
| T008 | FR-006 widen `WPStatusChanged`(`emitter.py:434`)+`WPCreated`(`:452`) validators to `Union[str,Dict]`; campsite `_is_actor_field` | WP02 | |
| T009 | FR-001 review-cycle write-in-home — enumerate ALL write sites; extract `_review_cycle_wp_dir` | WP03 | |
| T010 | FR-003 analysis-report re-home = ONE frozenset move; KEEP `_COORD_RESIDUE_FILENAMES` entry; drop coord copy + `copy2:700-705` | WP03 | |
| T011 | Mandatory co-changes: `PARTITION_RATIONALE` arch-gate (#2198); INVERT ~8 coord-pinning tests; rewrite stale comment | WP03 | |
| T012 | FR-004 topology-conditional status write-authority (`status_transition.py:~924` + batch `:~1028`); preserve coord-less fallback | WP04 | [P] |
| T013 | FR-007 runtime-state gate exemption (own-`feature_dir` named allowlist) threaded into the classifier | WP05 | [P] |
| T014 | FR-008/009 coord staleness detector + `doctor coordination --check-staleness` + safe `--fix` FF | WP06 | [P] |

## WP01 — Coord-commit correctness + #2861 causation (IC-01, URGENT-FIRST)

**Goal**: Close the real manual-review blocker: prove (live) the block is the misroute-to-legacy, then make it
unrepresentable. **Priority**: P1 (MVP — the blocker; unblocks `docs-structural-sanity-01KY53KJ`).
**Independent test**: real-repo e2e — a coord mission commits status/review to the right partitions; a
mis-placed write → `SafeCommitHeadMismatch`; the live #2861 repro classifies the block.
**Dependencies**: none. **Lane**: a. **Requirement refs**: FR-002, NFR-001, NFR-002.
**Prompt**: [tasks/WP01-coord-commit-misroute.md](tasks/WP01-coord-commit-misroute.md)

- [ ] T001 NFR-002 live #2861 causation repro FIRST — red-first through real `agent action review --agent tool:model:profile:role` (no `--invocation-id`); RECORD the failure mode (WP01)
- [ ] T002 Campsite: extract `_handle_commit_failure` from the two rollback+`_record_receipt("refused")` arms; delete dead triplicate `workflow.py:672 _resolve_git_common_dir` + stale test (WP01)
- [ ] T003 FR-002(a) misroute-to-legacy fail-loud guard (`workflow_executor.py:~217`) — coord-routed topology + incomplete identity triple must fail loud, never commit coord paths from repo_root (WP01)
- [ ] T004 FR-002(b) legacy-leaf porcelain pre-check (`workflow.py:~599`, #2684) run against the resolved worktree root via `CoordinationWorkspace.resolve` (WP01)
- [ ] T005 NFR-001 real-repo e2e (reuse `test_issue_2508.py`/`coord_topology_fixture.py`; assert via `git show <ref>:<path>`; negative = swapped `worktree_root`/`destination_ref`) + confirm the modern path unchanged (regression only) (WP01)

## WP02 — Actor identity on the emit seam (IC-04)

**Goal**: A manual claim records a valid parsed actor; SaaS fanout stops rejecting dict actors.
**Priority**: P2. **Independent test**: a compact `--agent` claim yields a `{role,tool,profile,model}` actor
(bare tool, no synthetic defaults); dict actors pass the validators.
**Dependencies**: WP01 (same lane-a, sequential; and WP01's NFR-002 verdict decides whether this satisfies US2 AC-3 — do NOT claim it unblocks manual review unless the repro says so).
**Lane**: a. **Requirement refs**: FR-005, FR-006.
**Prompt**: [tasks/WP02-actor-emit-seam.md](tasks/WP02-actor-emit-seam.md)

- [ ] T006 FR-005 widen `build_resolved_actor` (`emit.py:1077`) with self-asserted `profile`/`model` kwargs — NO synthetic `unknown-model`/`{tool}-default`, NO synthesized `ResolvedBinding` (C-002/C-007) (WP02)
- [ ] T007 FR-005 parse `--agent` at the boundary → bare tool at the 3 seams (`workflow_executor.py:648/:1465` as rationale-recorded out-of-map edits since same-lane-sequential; `tasks_move_task.py`) (WP02)
- [ ] T008 FR-006 widen `WPStatusChanged`(`emitter.py:434`)+`WPCreated`(`:452`) to `Union[str,Dict]` (WPAssigned has no actor field — out); campsite: collapse to one `_is_actor_field` + fold `_is_proof_actor`↔`_is_actor_payload` (WP02)

## WP03 — Write-in-home placement + analysis-report re-home (IC-02)

**Goal**: Retire wrong-partition authorship + the second-copy residue; re-home `ANALYSIS_REPORT`→PRIMARY.
**Priority**: P2. **Independent test**: review-cycle lands PRIMARY from every write site; analysis-report
lands PRIMARY with no coord copy; `assert_partition_invariant` green; the inverted tests + arch-gate pass.
**Dependencies**: none. **Lane**: b. **Requirement refs**: FR-001, FR-003. References #2646/#2697/#2275/#2198.
**Prompt**: [tasks/WP03-placement-and-rehome.md](tasks/WP03-placement-and-rehome.md)

- [ ] T009 FR-001 enumerate ALL review-cycle write sites (`review/cycle.py:~272` + move-task `--review-feedback-file` #2697 + verify `post_merge/review_artifact_consistency.py` reader resolves PRIMARY #2275/#2646); extract one `_review_cycle_wp_dir` (read+write converge) (WP03)
- [ ] T010 FR-003 analysis-report re-home = the ONE `_PLACEMENT→_PRIMARY` frozenset move in `artifacts.py` ONLY — KEEP `_COORD_RESIDUE_FILENAMES["analysis-report.md"]`; drop the coord copy (`mission_record_analysis.py` suppress-block) + the `copy2` at `commit_router.py:700-705` ONLY (keep bypass `:691-699` + status-skip `:688`); acceptance/issue-matrix STAY COORD; regression enumerating coord-kind callers before removal (WP03)
- [ ] T011 Mandatory co-changes: update `test_write_surface_placement_guard.py PARTITION_RATIONALE[ANALYSIS_REPORT]` (#2198); INVERT (assert the PRIMARY truth, NOT run-to-green) ~8 coord-pinning tests (`test_commit_router.py:502` #2463 flip-test landmine; swap coord-exemplars to `ACCEPTANCE_MATRIX`/`ISSUE_MATRIX`); rewrite stale `mission_record_analysis.py:~336` comment; verify 3 direct-path readers get PRIMARY; campsite: dedup 5 error branches + narrow 2 `suppress(Exception)` (WP03)

## WP04 — Single status write-authority (topology-conditional) (IC-03)

**Goal**: Coord topology commits status to the coord worktree; coord-less topologies keep the correct primary write.
**Priority**: P2. **Independent test**: a coord mission's status commits to coord; a `SINGLE_BRANCH`/`LANES`/flat
mission still commits primary — regression BOTH.
**Dependencies**: none (parallel). **Lane**: c. **Requirement refs**: FR-004.
**Prompt**: [tasks/WP04-status-write-authority.md](tasks/WP04-status-write-authority.md)

- [ ] T012 FR-004 conditionalize the `_transaction_topology_available` False arm in BOTH `status_transition.py:~924` and the batch `:~1028` — coord topology → materialize/target the coord worktree via `CoordinationWorkspace.resolve`; PRESERVE the primary-uncommitted fallback for coord-less topologies; campsite: extract one `_emit_via_non_transactional_fallback` (conditionalize once; batch fn is C25 — don't branch-in-place) (WP04)
- [ ] T015 FR-004 eliminate the empty-second-commit (the live #2861 blocker): make the coordination transaction's follow-up commit idempotent (`commit_idempotent` no-ops when the transactional emit already committed the transition) so the manual coord review claim SUCCEEDS; FLIP `tests/regression/test_2861_causation_repro.py` `exit_code == 1` → `exit_code == 0` (WP04)

## WP05 — Runtime-state gate exemption (IC-05)

**Goal**: The diff-compliance gate never blocks the mission's own runtime state; no `occurrence_map` exception.
**Priority**: P2. **Independent test**: a diff touching the mission's own `status.events.jsonl` is exempt; a
non-runtime file (and another mission's runtime file) under the same feature_dir still classifies.
**Dependencies**: none (parallel). **Lane**: d. **Requirement refs**: FR-007.
**Prompt**: [tasks/WP05-gate-exemption.md](tasks/WP05-gate-exemption.md)

- [ ] T013 FR-007 named allowlist (status.events.jsonl/status.json/review-cycle-N.md/matrices/notes) anchored to the RUNNING mission's OWN `feature_dir`, threaded from `bulk_edit/gate.py:199 check_review_diff_compliance` into `bulk_edit/diff_check.py`; exemption branch BEFORE the classifier; regression (non-runtime + other-mission still classify); campsite: `_glob_match` + `_is_bulk_edit_mission` + pure `_filter_allowlisted` (WP05)

## WP06 — Coord staleness signal + safe resync (IC-06)

**Goal**: Surface coord-vs-target staleness non-blockingly; fast-forward only when unambiguously safe.
**Priority**: P2. **Independent test**: strict-ancestor → stale + FF under `--fix`; diverged/dirty → fail loud with diff, no mutation.
**Dependencies**: none (parallel). **Lane**: e. **Requirement refs**: FR-008, FR-009.
**Prompt**: [tasks/WP06-coord-staleness.md](tasks/WP06-coord-staleness.md)

- [ ] T014 FR-008 coord-vs-target staleness detector + `spec-kitty doctor coordination --check-staleness` + non-blocking WARN at `finalize-tasks`; FR-009 safe `--fix` FF only when strict-ancestor AND clean, else fail loud with diff; keep `--fix` MINIMIZED (C-003); file `cli/commands/_coordination_doctor.py`; campsite: extract `_fast_forward_finding`/`_is_ff_candidate` from `_coord_worktree_stale_finding:~312`, hoist 7× subprocess import, extract `_resolve_coord_short` (WP06)

## Dependencies & parallelization

```
lane-a:  WP01 ──(dep)──> lane-b: WP02   (#1684 merges WP01's approved tip into WP02's base)
lane-c:  WP03            (parallel)
lane-d:  WP04            (parallel)
lane-e:  WP05            (parallel)
lane-f:  WP06            (parallel)
```

MVP = WP01 (the blocker). WP01 runs first; WP03/04/05/06 can run in parallel with the lane-a chain.

## Cross-cutting (all WPs)

- NFR-004: `ruff` + `mypy --strict` clean; complexity ≤15 (do NOT inflate `emit.py:495`/`:789`, `commit_router.py:210`, `workflow_executor.py:845` — extract helpers, don't branch-in-place); focused tests per new branch/helper; no new suppressions.
- NFR-003: preserve the fail-loud nets + the `review_artifact_consistency` check (now in `merge/`); the FR-004 coord-less fallback is load-bearing — do NOT delete.
- Issue-matrix: #2841/#2861 owned (close on merge; #2861 contingent on the NFR-002 verdict); #2646/#2697/#2275/#2198 referenced-contingent-close; #2868/#2612/#2684 context.
