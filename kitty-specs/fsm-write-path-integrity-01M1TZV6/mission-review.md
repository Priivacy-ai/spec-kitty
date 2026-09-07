# Mission Review Report: fsm-write-path-integrity-01M1TZV6

**Reviewer**: claude-fable-5-1 (mission-review subagent)
**Date**: 2026-09-06
**Mission**: `fsm-write-path-integrity-01M1TZV6` — FSM Write-Path Integrity (`mission_id` `01M1TZV64BPYQBCST251ECBZ4Z`, type `software-dev`, topology `single_branch`, target `missions/coreloop-proto-missions`)
**Baseline commit**: `meta.json` records `baseline_merge_commit = b10c2349f` (the acceptance commit; diffing against it shows only the squash). The pre-mission base used for every diff below is **`135f1430b`** (branch after the `origin/main` merge, before any lane landed).
**HEAD at review**: source diffs, WP artifacts and code reads were taken at `8e449088b` ("post-merge gate repairs"); a second repair commit **`1ceba9f22`** ("post-merge architectural gate repairs (2)") landed on the branch mid-review and the Gate 2 re-verification was run at that HEAD. `git diff 135f1430b..8e449088b -- src tests docs`: 80 files, +8234/−1350.
**WPs reviewed**: WP01 (serialize out-of-pipeline writers), WP02 (pipeline + flat shell), WP03 (facade strip + gates), WP04 (dependency guard), WP05 (run-state hardening), WP06 (transactional convergence), WP07 (writer-census addendum, minted mid-implementation). All 7 `done` (`spec-kitty agent tasks status`: 7/7, 100 %).

---

## Step 1 — Orientation and event-log signals

- `status.events.jsonl`: 0 `ReviewerSelfApproval` events (grep `-ci selfapproval` → 0). Every `approved` event carries a full reviewer verdict text (reviewer-renata subagent), and every WP was implemented by a different subagent profile (`python-pedro`); both were driven by the same orchestrator identity (`claude-fable-5-1`), which is the normal orchestration shape here, not a self-approval.
- Rejection cycles: WP02 ×1 (cycle 1 `changes requested`; cycle 2 approved), WP04 ×1 (cycle "2" file is the real round-1 REJECT; cycle "3" file is the approval — the `review-cycle-1.md` for WP04 is a non-review note about the blocked→planned unblock). All other WPs approved on cycle 1.
- `--force` transitions (7): WP02 ×1 (`in_review→planned` backward rewind for the rejection — the tool's rewind mechanism), WP04 ×4 (`in_progress→for_review` ×2, `in_review→planned` rewind, `in_review→approved` — the approval reason states "--force used only because the ledger-behind check (120 status commits on the target branch) fired"), WP05 ×2 (`in_progress→for_review`, `in_review→approved`). Judgement: each force is a lane-gate / ledger-behind workaround on a single-branch topology with an unusually long status ledger, not a review bypass — every forced `approved` event carries the reviewer's verified checklist. The retrospective flags them (n-003/n-004/n-005); the underlying ledger-behind friction is a tooling item, not a code-integrity item.
- WP04 also sat in `blocked` (`worktree_alloc_failed`: the auto-merge of lane-f into lane-d conflicted on the benign `emit.py` lock-key hunk WP01 and WP02 both carried — analysis finding I3 materialised exactly as predicted) and was unblocked by a manual merge (`a1a60f096`) plus the batch-door xfail flip (`596396b7d`).

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -n 3` (run by the orchestrator on `8e449088b`)
- Exit code: 0 — 245 passed, 10 skipped
- Result: **PASS**

### Gate 2 — Architectural tests
- Command: `.venv/bin/pytest tests/architectural/ -n 3` on `8e449088b` (orchestrator) → **12 failed, 1813 passed, 2 skipped, 2 xfailed**; the same suite on the pre-mission base `135f1430b` → 9 failed (`scratchpad/arch-fail-base.txt`).
- Attribution (12 rows):

| # | Failing node (at `8e449088b`) | On base `135f1430b`? | Classification | Evidence |
|---|---|---|---|---|
| 1 | `test_execution_context_parity.py::test_cwd_parity` | fails | baseline-red (env-sensitive) | listed in both files |
| 2 | `…::test_cwd_parity_write` | fails | baseline-red (env-sensitive) | both files |
| 3 | `…::test_full_sequence_direct_to_target` | fails | baseline-red (env-sensitive) | both files |
| 4 | `…::test_full_sequence_main_checkout_parity` | fails | baseline-red (env-sensitive) | both files |
| 5 | `…::test_full_sequence_ratchet_catches_divergence` | fails | baseline-red (env-sensitive) | both files |
| 6 | `…::test_full_sequence_worktree_parity` | fails | baseline-red (env-sensitive) | both files |
| 7 | `test_golden_count_ban.py::test_convert_sites_do_not_exceed_frozen_baseline` | fails | PARTLY branch-caused (corrected 2026-09-07 by the adversarial squad, architect lens): `tests/specify_cli` 238→242 and `tests/status` 31→34 were exactly at ceiling on `origin/main` and crossed it because of this mission's own tests (11 sites, all cardinality-only, now annotated `# golden-count: cardinality-is-contract`); `tests/architectural` is 15 vs ceiling 14 on `origin/main` too — that single site is the genuine baseline red that remains | mixed |
| 8 | `test_mission_runtime_surface.py::TestMissionRuntimeSurface::test_package_root_cold_imports` | fails | baseline-red | both files |
| 9 | `test_spec_kitty_home_pin_census.py::test_t022_both_artefacts_are_reproduced_byte_identically_by_the_documented_command` | fails | baseline-red (env-sensitive) | both files |
| 10 | `test_arch_shard_marker_completeness.py::test_every_group_root_node_has_exactly_one_shard_marker[next]` | passes (file absent) | **mission-caused (WP05)** | assertion names all 15 nodes of `tests/runtime/test_run_state_hardening.py` with `[]` markers — the new file was not registered in `tests/_next_shard_map.py` |
| 11 | `test_cold_import_status_boundary.py::test_cold_import_keeps_status_orchestration_out[specify_cli.cli.commands.charter]` | passes | **mission-caused (WP07)** | `specify_cli.cli.commands.charter/__init__.py:22` module-imports `decisions.service`, which module-imports `decisions.emit`; WP07 added module-level `from specify_cli.status import feature_status_lock` / `status._unsafe` / `workspace.root_resolver` there (diff `decisions/emit.py` +432..434) → 43 forbidden `specify_cli.status.*` modules on the charter cold path (#1461 boundary) |
| 12 | `test_no_absolute_event_timestamp_mixture.py::test_derived_mixture_matches_recorded_baseline` | passes | **mission-caused (WP04)** | assertion: new mixture `('tests/status/test_work_package_lifecycle.py', 'test_start_implementation_resume_is_not_regated_when_dependency_regresses')` not recorded — the new resume pin mixed hard-coded `at=` seed events with a live-clock production call |

- Repair: all three mission-caused nodes were fixed post-merge in `1ceba9f22` (function-local imports in `decisions/emit.py:132-134` with `# noqa: PLC0415`; `tests/_next_shard_map.py` +1 row; the resume test's seed events now use `at=now_utc_iso()`, mixture ledger stays at 13 rows). Re-verified at `1ceba9f22`: the three gates + `tests/specify_cli/decisions/test_emit_locking.py` + `tests/status/test_writer_serialization.py` → **23 passed** (`.venv/bin/pytest … -p no:cacheprovider -q`, 75 s); `test_cold_import_status_boundary.py` re-run twice → 3 passed each.
- Result: **FAIL at `8e449088b` (3 mission-caused) → PASS-after-repair at `1ceba9f22`** (the 9 baseline-red nodes remain red on both trees and are not this mission's). Recorded as DRIFT-1 (MEDIUM) below.

### Gate 3 — Cross-repo E2E
- Command: not run — the `spec-kitty-end-to-end-testing` repo is not checked out on this machine.
- Result: **NOT RUN (environmental)**. No `kitty-specs/fsm-write-path-integrity-01M1TZV6/mission-exception.md` exists. The mission claims **no cross-repo behaviour**: every change is local write-path hardening (lock/append/pipeline/guard/run-state); the SaaS/zeitgeist fan-out payloads are unchanged (data-model §9: "only timing changes") and the adapters registry is untouched (`status/adapters.py` not in the diff). No new e2e scenario is therefore required by C-010. An operator should still run the four floor scenarios before tagging.

### Gate 4 — Issue Matrix
- File: `kitty-specs/fsm-write-path-integrity-01M1TZV6/issue-matrix.json` (schema 1)
- Rows: 13 — `verified-already-fixed` ×6 (#1667, #1775, #1848, #3460, #3773, #3888), `deferred-with-followup` ×7 (#1666, #1868, #2173, #3885, #3893, #3895, #3904)
- Empty / `unknown` / `in-mission` verdicts: 0
- `deferred-with-followup` rows missing a follow-up handle: 0 — each `evidence_ref` names the follow-up (operator posts on #3893/#2173/#3895/#1868; PR #3904 supersession; design-note record for #1666/#3885). Nit: #1666's ref reads "Follow-up: none required" — the verdict would be better as `verified-already-fixed`; and nine rows still carry the `title: "<fill at WP-implementation time>"` placeholder (cosmetic).
- Result: **PASS**

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|--------------|---------------|---------|
| FR-001 | Writer census governed (9 families after WP07) | WP01, WP07 | `tests/status/test_writer_serialization.py` (9-family parametrized lock-held pin via `_HeldLocksAtWrite` on `store._fsync_directory` + `os.replace`); census in `design-notes/WP01-lock-rules.md` §1/§8; stale "2 of 6" comment relabelled (`orchestrator_api/commands.py:3573`) | ADEQUATE | comment now says "seven" families (nine after WP07) — LOW doc drift (DRIFT-6) |
| FR-002 | Lock + atomic-append the unlocked writers | WP01, WP07 | `test_writer_serialization.py::test_retro_append_waits_for_rollback_and_lands_after_truncate` (SC-001: forced `safe_commit` failure, racing thread, asserts the retro row survives the truncate); `tests/specify_cli/retrospective/test_{events,lifecycle_events}_locking.py`; `tests/specify_cli/migration/test_backfill_writer_locking.py`; `tests/specify_cli/decisions/test_emit_locking.py`; `tests/specify_cli/migration/test_rebuild_state_locking.py` | ADEQUATE — deleting the lock at any site re-opens the window and the race pins fail (RED proofs recorded in design notes §8.7) | — |
| FR-003 | Three lock rules (a)(b)(c) | WP01 | (a) `tests/status/test_locking_key.py::test_bound_is_aligned_with_the_verdict_save_queue_bound` + pre-existing `tests/review/test_verdict_status_lock_bound.py`; (b) `tests/specify_cli/retrospective/test_merge_path_lock_timeout.py` (real contended lock, terminus returns < 5 s, warning names lock file + holder); (c) lock-key tests | ADEQUATE | — |
| FR-004 | Lock key = `feature_dir.name` | WP01 | `test_locking_key.py::test_colliding_slugs_resolve_distinct_lock_files`, `::test_legacy_bare_slug_dir_writers_share_one_lock_file`, `::test_emit_lock_key_is_the_directory_name_not_the_slug`, `::test_transaction_lock_key_equals_its_mission_dir_name`; all 18 `feature_status_lock(` sites audited (`WP01-lock-rules.md` §4) | ADEQUATE | — |
| FR-005 | Pure pipeline extraction | WP02 | `tests/status/test_transition_pipeline.py` (alias/gates/evidence/validate-once/purity; AST pins with non-vacuity mutation; `test_pipeline_never_imports_coordination`) | ADEQUATE | — |
| FR-006 | Converge 3 orchestrations + aggregate de-dup | WP06 | `tests/specify_cli/coordination/test_status_transition.py::test_three_doors_build_the_same_event_and_validate_once_each` (asserts `not hasattr(st, "_prepare_event")`, `validate_transition` count 1/2/3 across plain/single/batch); `tests/status/test_agent_status_emit_aggregate_wiring.py::test_validate_transition_runs_exactly_once_through_the_aggregate` (count == 1 + AST: aggregate source has no `validate_transition` call) | ADEQUATE | — |
| FR-007 | Batch `effective_root` parity | WP06 | `test_status_transition.py::test_batch_door_refuses_owned_mission_without_transaction_like_single`, `::test_batch_door_acquires_transaction_with_the_single_door_shape` | ADEQUATE | — |
| FR-008 | Fan-out deferred behind commit | WP06 | `tests/specify_cli/coordination/test_phantom_fanout.py::test_coord_fallback_commit_failure_announces_nothing[single|batch]` (forces `_commit_status_artifacts_to_coord` to raise; asserts truncation AND `order == ["commit"]`), `::test_coord_fallback_fans_out_only_after_commit`, `::test_transactional_door_fans_out_only_after_commit`, collapse-arm pin | ADEQUATE — deleting the `fan_out=False` seam re-orders to `["fan_out","commit"]` (the recorded RED) | RISK-1 (fallback-arm truncate is lockless) |
| FR-009 | Minimal doc correction | WP06 | `AGENTS.md` (CLAUDE.md symlink) one table row; `docs/architecture/status-model.md:211` one sentence; terminology guard | ADEQUATE (doc) | the spec's `:393` anchor was stale; corrected in design note |
| FR-010 | Facade strip → `status/_unsafe.py` | WP03 | `tests/architectural/test_status_unsafe_allowlist.py` (`ALLOWED_CALLERS ⊆ BASELINE`, four door shapes incl. direct `status.store` and the `status_service` wrappers — closes analysis I1; liveness; `test_facade_no_longer_exports_raw_appends`; 10 synthetic floors) | ADEQUATE | — |
| FR-011 | AST writes-gate + non-vacuity | WP03, WP07 | `tests/architectural/test_status_events_writes_gate.py` (positive store census `{Path.open a, os.replace}`; per-key counted ledger of 4 out-of-store sites; unresolved event-named pins; R14 lock-composition census of 15 modules; 15 synthetic writer floors) | ADEQUATE | — |
| FR-012 | Tri-state guard field, fail-open on `None` | WP04 | `tests/status/test_dependency_guard.py::TestGuardPolarity`, `::TestProbeSitesFailOpen`, `::TestChainMatrix`; `tests/specify_cli/status/test_wp_state.py::TestDependencyReadinessGuard::test_none_is_not_treated_like_subtasks_complete`; `wp_state.py:317,344` refuse only on `is False` | ADEQUATE | — |
| FR-013 | In-lock resolution on the write surface | WP04 | `test_dependency_guard.py::test_verdict_reflects_state_written_by_a_writer_that_held_the_lock_first` (real second thread holds L1 and regresses the dep), `::TestCoordSurfaceResolution` (primary/coord disagree both ways; order pin acquire→reduce→readiness→release with reduced dir == `txn.feature_dir`) | ADEQUATE | reviewer probe: the guard also fires on the **coord fallback arm** (scratch probe, `GUARD FIRED`) |
| FR-014 | Reuse `dependency_readiness_for_wp`; demote 6 sites | WP04 | `::TestVerdictHelpers::test_declared_dependencies_agree_with_the_pre_flight_parser` (shell == `parse_wp_dependencies` for `"[]"`, `"WP01, WP02"`, bare `WP01`); `tests/specify_cli/status/test_wp_metadata.py::TestCoerceLegacyDependencies`; six sites are comments-only diffs; `tests/status/test_work_package_lifecycle.py::test_start_implementation_resume_is_not_regated_when_dependency_regresses` | ADEQUATE (US4-6 pinned at the lifecycle layer only — the `implement` CLI pre-flight still re-gates a resume; recorded honestly in `WP04-guard.md` A4) | RISK-4 |
| FR-015 | Atomic run-cursor writes | WP05 | `tests/runtime/test_run_state_hardening.py::test_write_snapshot_crash_window_keeps_previous_cursor` (patches `os.replace` to raise; previous bytes intact; tmp left; later write publishes), `::test_write_snapshot_stages_tmp_in_the_run_directory`, `::test_append_event_journal_lines_are_whole_even_when_fsync_fails` | ADEQUATE | no directory fsync after `os.replace` (same as the `reducer.materialize` precedent) — LOW |
| FR-016 | `mission_id`-keyed index; loud missing state | WP05 | `::test_slug_collision_resolves_distinct_runs` (RED on base at `runtime_bridge_io.py:618`), `::test_missing_state_with_live_entry_raises_and_starts_nothing` (`RunStateMissing`, `error_code RUN_STATE_MISSING`, no engine start, index bytes unchanged), rekey idempotency/losslessness, read-only resolvers never persist | ADEQUATE | — |
| FR-017 | Pure progress read | WP05 | `::test_progress_query_leaves_tracked_status_json_byte_identical`, `::test_progress_query_logs_when_weighted_progress_is_unavailable` (the `except: pass` became a logged warning) | ADEQUATE | — |
| FR-018 | Batch door takes L1 | WP02 | `tests/status/test_emit.py::TestBatchShellLock::test_batch_holds_feature_lock_across_derive_prepare_and_append`; `test_writer_serialization.py::test_batch_door_writes_only_while_holding_its_mission_lock` (WP01's strict xfail, flipped at `596396b7d`) | ADEQUATE | — |
| NFR-001 | No lock across git in new code | WP01, WP07 | spawn-recorder pins for families 8/9 (`test_emit_locking.py::test_no_git_subprocess_while_holding_the_mission_lock`, `test_rebuild_state_locking.py::…`); families 4–7 verified by inspection (critical sections = reads + one append; `git_common_dir` probe is `lru_cache`d and runs before `acquire`) | PARTIAL — no spawn-recorder pin for families 4–7; `verdict_provenance_backfill.py` now holds L1 across review-artifact reads (no git) | LOW note |
| NFR-002 | Replay purity | WP04 | `test_dependency_guard.py::TestReplayPurity` (AST scan of `reducer.py` with non-vacuity mutation; now-dep-illegal history replays/audits clean); `grep` confirms zero `validate_transition`/`GuardContext` refs in `reducer.py`/`validate.py` bodies | ADEQUATE | — |
| NFR-003 | Bounded outage-shaped waits | WP01 | `test_locking_key.py::test_contended_bounded_take_raises_structured_error_naming_holder`, `test_merge_path_lock_timeout.py`; `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS = 10.0` pinned equal to the verdict-queue bound | ADEQUATE | — |
| NFR-004 | Emit cost preserved | WP02, WP04 | `test_transition_pipeline.py::test_emit_reads_log_once`, `::test_batch_emit_reads_log_once_for_the_whole_batch` (`_derive_from_lane == 1`, `read_events` before append == 1); `_reduce_write_surface` feeds both from-lane and verdict | ADEQUATE for log reads | new per-emit WP-file frontmatter read on every edge (RISK-5, LOW) |
| NFR-005 | Test discipline | all | reviewer-recorded counts in every cycle file (e.g. WP04: 2199 passed blast radius; WP06: 1948+2246) | ADEQUATE (process) | but the full `tests/architectural/` suite was never run on a merged tree before accept (DRIFT-1) |
| C-001 | Coord/primary partition preserved | WP06 | `test_phantom_fanout.py` (truncate-restore symmetry), `tests/coordination/test_status_write_authority.py` pins, `test_plain_door_semantics.py` | ADEQUATE | — |
| C-002 | NFR-006 standing violation not fixed | WP01 | `transaction.py` diff is the one-line lock-key hunk only | ADEQUATE | — |
| C-003 | 083 identity | WP01, WP05 | lock key + run-index key tests | ADEQUATE | — |
| C-004 | Fail-open on `None` | WP04 | `TestProbeSitesFailOpen`, `test_none_is_not_treated_like_subtasks_complete`; both probe sites (`lanes/recovery.py`, `agent/tasks_transition_core.py`) untouched | ADEQUATE | — |
| C-005 | Replay never validates | WP04 | as NFR-002 | ADEQUATE | — |
| C-006 | status never imports coordination | WP02/WP06 | `test_pipeline_never_imports_coordination`; `tests/architectural/test_status_module_boundary.py` (+`_unsafe` carve-out pin); `aggregate.py:636-644` lazy import kept with the C-006 comment; no second reach added | ADEQUATE | — |
| C-007 | Three failure policies | WP06 | `test_transactional_emit_fails_closed_when_coordination_branch_missing` (#1848), `test_transactional_batch_fails_closed_when_coordination_branch_missing` (new), `test_inner_state_annotation_degrades_when_coordination_branch_missing` (#3460), `test_tasks_move_task_degod.py::test_runtime_state_persistence_error_propagates`, collapse-arm pins | ADEQUATE | — |
| C-008 | Plain-door semantics | WP06 | `tests/specify_cli/coordination/test_plain_door_semantics.py` (HEAD count unchanged, no `.worktrees/`, no mutating git verb; plain door spawns exactly `[rev-parse --git-common-dir]`) | ADEQUATE | spec's "four plain-door callers" are docstring mentions (research D-1); pin rationale correctly cites `_fallback_emit_single._primary` |
| C-009 | Red-first repros transitional | WP01, WP02 | no `xfail`/`regression` markers remain (`grep` over the 15 mission test files: only WP01's batch xfail existed and was flipped) | ADEQUATE | — |
| C-010 | Test policy | all | cycle files | ADEQUATE | — |

**Legend**: ADEQUATE = test constrains the required behaviour; PARTIAL = test exists but does not fully pin the requirement; MISSING = no test; FALSE_POSITIVE = passes with the implementation deleted. No MISSING or FALSE_POSITIVE rows: every FR-numbered pin either exercises the production door (flat/transactional shells, real `BookkeepingTransaction`, real git repos) or is an AST/structural pin with a non-vacuity floor.

---

## Drift Findings

### DRIFT-1: Three architectural-gate regressions shipped through seven per-lane reviews

**Type**: NFR-MISS (process) / CROSS-WP
**Severity**: MEDIUM
**Spec reference**: NFR-005, C-010 ("never the full arch suite locally"); plan.md §Structure Decision ("`tests/architectural/` full run is NOT triggered by the cross-cutting rule")
**Evidence**:
- Gate 2 table rows 10–12: `tests/runtime/test_run_state_hardening.py` (WP05) unregistered in `tests/_next_shard_map.py`; `src/specify_cli/decisions/emit.py` (WP07) module-level `specify_cli.status` imports on the `charter` cold path (`cli/commands/charter/__init__.py:22 → decisions.service:28 → decisions.emit`); `tests/status/test_work_package_lifecycle.py` (WP04) absolute-timestamp mixture not recorded.
- Each per-WP review ran only the named targeted gates (WP04: "five architectural gates → 65 passed"; WP07: "90 gate tests"); none ran `tests/architectural/` on the lane, and the plan explicitly told them not to.
- Repaired post-merge in `1ceba9f22` (verified: 23 passed at that HEAD).

**Analysis**: the repo carries registry/ratchet gates (shard map, cold-import boundary, timestamp mixture, dead-symbol, ruff-format) whose trigger condition is "a new test file / a new module-level import / a new fixture shape", which is exactly what most WPs do. Scoping the local run to "the two new gates + boundary + terminology" (plan.md:195) made these invisible until the merged tree was tested. The code defects themselves were small and are now fixed; the process gap is the finding: per-lane review does not run the full architectural suite, and neither `accept` nor `merge` did either — the mission was accepted (`3cc712066`) and squash-merged (`d0d28589c`) with Gate 2 red. Recommend the implement-review skill / charter gate discipline require one `tests/architectural/` run on the merged lane (or the accept step) before `accept`.

### DRIFT-2: Non-transactional coord fallback arm keeps a lockless rollback truncate (SC-001 defect class, sibling site)

**Type**: PUNTED-FR (partial closure of the US1 invariant)
**Severity**: MEDIUM
**Spec reference**: US1 scenario 1 / SC-001; data-model I-3 ("a rollback truncate can only run while the same lock is held"); `contracts/write-gates.md` §2
**Evidence**:
- `src/specify_cli/coordination/status_transition.py::_restore_coord_status_artifacts` (`:364-390`) — `events_path.open("ab")` + `fh.truncate(pre_emit_event_size)` with **no** `feature_status_lock`; called from `_emit_on_coord_then_commit` (`:118-162`) after the flat shell has *released* L1 and `safe_commit` ran unlocked.
- The writes-gate ledger entry itself says so: `("specify_cli.coordination.status_transition", "Path.open", "events_path"): 1` — "coord fallback-arm rollback truncate (WP06 may retire → ledger shrinks)" (`design-notes/WP03-gates.md` §4). WP06 did not retire it; the WP06 reviewer recorded the "pre-existing lockless commit window" as a non-blocking minor.

**Analysis**: SC-001 was scoped to `BookkeepingTransaction._rollback` (`transaction.py:944`) and that window is closed (the transaction holds L1 for its lifetime and every writer now waits on it). The fallback coord arm reproduces the same shape one level up: a concurrent *locked* writer (retrospective, decision row, another shell) can legitimately append between the flat shell's release and the failed commit's truncate, and the truncate destroys it. Reachable only when a stored-coord mission takes the `_transaction_topology_available() is False` arm (legacy-shaped coord missions without transaction metadata), so blast radius is narrow, but it is the one remaining rollback-truncate window in the tree and it is not documented as an accepted risk in the spec's risk register (R9 covers the L1-across-git case, not this one). Candidate follow-up: hold L1 across emit→commit→truncate is forbidden by NFR-001 (commit spawns git), so the fix is either a locked, size-verified truncate (re-check the tail equals the emitted rows before truncating) or retiring the arm in the caller-migration mission.

### DRIFT-3: Plain batch door lost the deliberate #946 fail-closed skip (D-2)

**Type**: LOCKED-DECISION VIOLATION (of an older decision, adjudicated in-mission)
**Severity**: LOW
**Spec reference**: FR-006/FR-007 parity; `design-notes/WP02-pipeline.md` §6 D-2; `WP06-convergence.md` §5
**Evidence**: `git diff 135f1430b..HEAD -- src/specify_cli/status/emit.py` removed `if workspace_context is None and not (from_lane == Lane.CLAIMED and resolved_lane == Lane.IN_PROGRESS)` (old `:820`); the pipeline now always synthesises `"<execution_mode>:<root>"`. Pinned by `test_batch_claimed_to_in_progress_defaults_workspace_context_like_every_other_door`.
**Analysis**: a direct plain-batch caller that omits `workspace_context` on `claimed→in_progress` used to be refused ("requires workspace context"); it now passes with a synthetic root. Production callers always pass it, the parity is spec-mandated and the change is recorded with the #946 provenance, so this is an adjudicated divergence, not silent drift — but it weakens a fail-closed guard for future direct callers and the #946 owner was not consulted. Flag for operator confirmation.

### DRIFT-4: Spec text still carries the ten "[NEEDS DECISION]" markers and the stale four-caller C-008 rationale

**Type**: documentation drift (analysis I4/I5/A1, acknowledged, not fixed)
**Severity**: LOW
**Evidence**: `spec.md:5` ("Status: Draft … no plan.md or tasks yet"), `spec.md:188-201` (Q1–Q10 all resolved in `decisions/`), `spec.md:159` C-008 names four modules that research §3 D-1 shows are docstring mentions only.
**Analysis**: plan.md and the decision records are binding; a reader starting from the spec re-opens settled questions. Fold at the next spec touch.

### DRIFT-5: Contract deviations recorded but not reconciled

**Type**: documentation drift
**Severity**: LOW
**Evidence**: `contracts/dependency-guard.md` §2 promises a refusal message ending in `<ids>`; implemented message names no ids (`wp_state.py:31`); `contracts/emit-pipeline.md` §1 types `annotation: StatusEvent | None` (implemented `InnerStateChanged | None`) and lists `coordination/status_transition.py` in the `_unsafe` allowlist (it is not an importer). All three are recorded in the design notes; the contracts were not updated.

### DRIFT-6: Two comments went stale inside the mission

**Type**: documentation drift
**Severity**: LOW
**Evidence**: `src/specify_cli/retrospective/lifecycle_events.py:102` says the non-git degrade is `<root>/.git/spec-kitty-locks` — WP01 §6 changed it to `<root>/.kittify/spec-kitty-locks` (`status/locking.py:167-171`); `src/specify_cli/orchestrator_api/commands.py:3575` says WP01 "serialized all seven writer families" — nine after WP07. Both were reviewer minors left open.

---

## Risk Findings

### RISK-1: Post-commit tail fan-out can announce a row the arm did not write

**Type**: CROSS-WP-INTEGRATION / BOUNDARY-CONDITION
**Severity**: LOW
**Location**: `src/specify_cli/coordination/status_transition.py::_fan_out_committed_coord_tail` (`:75-112`)
**Trigger condition**: on the coord fallback arm, another locked writer appends a *transition* row to the same coord log between the flat shell's L1 release and `_commit_status_artifacts_to_coord`; the commit then includes it and the tail parse (`read_event_stream_from_text` from `pre_emit_event_size`) fans it out a second time (the other shell already fanned it out itself).
**Analysis**: the tail approach is what makes SC-002 byte-safe (annotations are recovered, never re-minted), and foreign rows (retrospective/decision dicts) are skipped by the partitioner (`store.py:653`), so this is a duplicate SaaS announcement, not a lost one. The WP06 reviewer suggested a deferred-callable seam as the follow-up; agree.

### RISK-2: Non-git / transient-probe degrade now lands a worktree-local lock

**Type**: BOUNDARY-CONDITION
**Severity**: LOW
**Location**: `src/specify_cli/status/locking.py::_git_common_dir` (`:157-171`)
**Trigger condition**: `git_common_dir()` raises (git missing or transient failure) inside a linked worktree whose `.git` is a *file*; `dot_git.is_dir()` is False → lock root becomes `<worktree>/.kittify/spec-kitty-locks/` instead of the shared common dir.
**Analysis**: before WP01 the same failure produced a `mkdir` under a `.git` *file* (loud). Now two worktrees of one checkout could silently serialise on different files. Mitigated by `git_common_dir` being `lru_cache`d and re-run after a raise (`kernel/git_topology.py:44-47`), and by the bare-tree case being the intended target (fixes the "minted `.git/` fake repo root" trap, pinned by `test_lock_on_non_git_tree_never_mints_a_dot_git_directory`). The WP01 reviewer flagged it as a minor; record on the risk register.

### RISK-3: `_declared_dependencies` treats a missing WP prompt file as "no dependencies"

**Type**: ERROR-PATH (silent fail-open)
**Severity**: LOW
**Location**: `src/specify_cli/status/emit.py::_declared_dependencies` (`:134-163`) — `if wp_file is None: return ()`
**Trigger condition**: the planning dir handed to the shell has no `tasks/<WP>*.md` (legacy mission with no `tasks/`, a renamed WP file, or — on the coord fallback arm — the flat shell reading the WP file from the **coord worktree copy** rather than primary).
**Analysis**: by design (reviewer-probed "legacy mission with no tasks/ dir still emits"), and the scratch probe confirms the guard does fire on the coord fallback arm when the coord branch carries the WP files (it does today: `GUARD FIRED`). The residual risk is a coord branch that lags primary (a dependency added on primary after the coord branch was cut is not seen by the fallback arm). Corrupt files are fail-closed with a `force` escape (shape (b)); a *missing* file is fail-open with no log line. Suggest a `logger.debug` at minimum.

### RISK-4: `implement` pre-flight still re-gates a resume (US4-6 only pinned at the lifecycle layer)

**Type**: CROSS-WP-INTEGRATION
**Severity**: LOW
**Location**: `src/specify_cli/cli/commands/implement.py:1869` (`_ensure_wp_claim_preconditions` unconditional)
**Analysis**: pre-existing (WP04's diff there is comments-only, FR-014 says the sites stay), recorded honestly in `WP04-guard.md` A4; the guard itself cannot re-gate a resume (`test_start_implementation_resume_is_not_regated_when_dependency_regresses`). Carry to the caller-migration mission.

### RISK-5: New per-emit planning-file read on every edge

**Type**: BOUNDARY-CONDITION (cost)
**Severity**: LOW
**Location**: `src/specify_cli/status/emit.py::_resolve_dependency_readiness` — called unconditionally in all four doors (`emit.py:535,874`; `status_transition.py:606,796`)
**Analysis**: NFR-004 pins log reads and those are unchanged (one reduce per emit), but every emit — including `→for_review`, `→done`, `→canceled` where the guard has no opinion — now globs `tasks/*.md` and parses one frontmatter under L1. Cheap, but the reviewer's shape (a) (resolve only when the target resolves to `claimed`/`in_progress`) would remove it and also shrink RISK-3's surface. Follow-up.

### RISK-6: `_write_snapshot` does not fsync the run directory after `os.replace`

**Type**: ERROR-PATH
**Severity**: LOW
**Location**: `src/runtime/next/_internal_runtime/engine.py::_write_snapshot` (`:137-149`)
**Analysis**: matches the `reducer.materialize` precedent (`reducer.py:278`, also no directory fsync), so it is not a regression; a power loss right after the rename can still lose the new name on some filesystems. The crash-window test covers the process-kill case only.

### Dead-code check
Every new public symbol has a live `src/` caller: `prepare_transition`/`PreparedTransition` (both shells + aggregate path), `bounded_lock_timeout` (`post_merge/retrospective_terminus.py`), `retro_status_lock` (families 4/5), `run_index_key`/`RunStateMissing`/`_require_run_state`/`_canonicalize_run_index` (`runtime_bridge_io.py`), `coerce_legacy_dependencies` (`wp_metadata.py` + `emit.py`), `readiness_from_snapshot`/`unresolvable_readiness` (`emit.py`), `_fan_out_committed_coord_tail`/`_emit_on_coord_then_commit` (both fallback arms), `fan_out=` (fallback arms), `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS` (terminus). `wp_lanes_from_snapshot` and `UNRESOLVABLE_MARKER` are module-level test-pinned helpers deliberately dropped from `__all__` in `8e449088b` (dead-symbol gate). `_unsafe.append_event` and `ALLOWED_CALLERS` are allow-listed in `test_no_dead_symbols.py` with rationale. No dead module.

### Cross-WP integration
- `status/emit.py` was touched by WP01 (lock-key args), WP02 (owner), WP04 (verdict helpers) and the merge resolved the identical lock-arg hunk on both sides; `status/__init__.py` by WP01 (+2 exports) and WP03 (strip); `test_no_dead_symbols.py` by WP03 and WP07 (hash re-mint); `test_status_events_writes_gate.py` by WP03 and WP07. All resolutions verified consistent at HEAD (allowlist 9 == BASELINE 9; lock-composition census 15 == tree; `__all__` trims in `dependency_verdict.py`/`transition_pipeline.py` keep the symbols module-level).
- WP01's batch-door strict `xfail` was flipped at the WP04 unblock (`596396b7d`), not by WP02 — the reviewer's F3 warning was acted on by the orchestrator, correctly.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `status/emit.py:156-158` `_declared_dependencies` | WP prompt file not found under `tasks/` | returns `()` → verdict *satisfied*; no log line | FR-012/013: guard fails open on a missing planning artifact (RISK-3) |
| `coordination/status_transition.py:95-101` `_fan_out_committed_coord_tail` | events file missing / empty tail | returns silently | by design (collapse arm announces nothing); a non-collapse arm hitting this would be an unannounced committed event — unreachable today |
| `status/locking.py:172-193` `_record_holder` / `_clear_holder` / `_read_holder` | sidecar I/O error | `logger.debug`, holder reported as "unknown" | NFR-003 message loses the holder name only; acceptable best-effort |
| `coordination/status_transition.py:380-389` `_restore_coord_status_artifacts` | `OSError` during truncate/restore | `logger.exception`, continues | pre-existing; a failed restore leaves an uncommitted row on the coord worktree |
| `runtime/next/decision.py:398-401` `_compute_wp_progress` | weighted-progress error | `logger.warning`, counts returned without `weighted_percentage` | FR-017 closed the former `except: pass` |
| `status/emit.py:327-333` `_persist_prepared` | `materialize` fails after the append | `logger.warning` | pre-existing policy (event persisted, snapshot stale, recoverable) |

No `except …: pass` / `return ""` was introduced by the mission; the one pre-existing swallow in scope (`decision.py`) was converted to a logged warning.

---

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---------|----------|------------|----------------|
| Lock scope covers read-modify-write everywhere it was extended: retrospective Lamport read + append (`_locked_append`), backfill idempotency read + append (`_backfill_runtime_state_locked`, `_collect_backfill_events`), decision row + Lamport readback, rebuild read→rewrite — all under one acquisition | `retrospective/lifecycle_events.py:990-1006`; `migration/*`; `decisions/emit.py:130-136`; `migration/rebuild_state.py:581` | LOCK-TOCTOU (closed) | none |
| No new lock-across-git: every new L1 take's critical section is file I/O only; the git probe (`git_common_dir`) is `lru_cache`d and runs before `acquire`; the coord fallback commit runs after the flat shell releases | `status/locking.py`, `status_transition.py:138-154` | LOCK-TOCTOU | keep the spawn-recorder pins; add them for families 4–7 |
| Lockless rollback truncate remains on the coord fallback arm | `status_transition.py:364-390` | LOCK-TOCTOU | DRIFT-2 follow-up (locked, size-verified truncate or retire the arm) |
| Holder sidecar `<lock>.holder` written next to the lock file (under `.git/spec-kitty-locks` or `.kittify/spec-kitty-locks`); JSON with pid/thread/timestamp only; parsed defensively (`isinstance(parsed, dict)`) | `status/locking.py:172-193` | — | none (no secrets, best-effort, unlinked on release) |
| `bounded_lock_timeout` is a `ContextVar` scope — follows the calling context, does not leak across threads; explicit keyword wins | `retrospective/lifecycle_events.py:892-914` | — | none; the merge-path call chain is synchronous (reviewer-verified) |
| Non-git fallback path is deterministic and never mints `.git/` | `status/locking.py:157-171` | PATH-TRAVERSAL (none) | RISK-2 note only |
| AST scanners read only `src/**/*.py` from the repo root; no user-controlled paths; synthetic floors parse literal strings | `tests/architectural/test_status_*` | — | none |
| `os.replace` targets are same-directory tmp files (`state.json.tmp`, store write-ahead tmp) — same filesystem, atomic on POSIX/NTFS; fixed tmp name relies on the run journal being single-writer (documented) | `engine.py:137-149` | — | RISK-6 (directory fsync) is optional hardening |
| No `shell=True`, no new HTTP calls, no credential handling in the diff | — | — | — |

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

All 18 FRs, the five NFRs and the ten constraints trace to production-path tests that would fail if the implementation were removed (the SC-001/SC-002/SC-005/SC-006 RED proofs are recorded per WP and were independently reproduced by the per-WP reviewers; this review re-ran the family-8/9 race pins and the writer-serialization suite green at `1ceba9f22`). No Non-Goal was invaded: no ports, no runtime facade work, no compaction (`_reduce_write_surface` still reduces the full log), no `transaction.py` redesign (one-line lock-key hunk), `adapters.py`/`reducer.py`/`validate.py` untouched, `wp_state.py` gained exactly the guard field and two clauses, and no event schema changed. Every locked decision holds: C-004 fail-open on `None` (`is False` only), C-005 replay purity (AST-pinned), C-006 (pipeline imports nothing from `coordination`; the `aggregate.py` lazy reach is unchanged and commented as the one exception), C-007 (three policies + collapse arm each pinned by name), C-008 (plain door spawns only the lock-path probe, no commits). Gate 1 and Gate 4 pass; Gate 3 is environmental (no cross-repo behaviour claimed). Gate 2 was **red at the accepted/merged tree** (`8e449088b`) with three mission-caused regressions and is green after the second post-merge repair (`1ceba9f22`) — that is the substantive note: the mission was accepted and squash-merged with architectural gates failing because the plan scoped every WP's local run away from the full suite (DRIFT-1, MEDIUM). The remaining open items are the lockless truncate on the legacy coord fallback arm (DRIFT-2, MEDIUM, narrow reach, ledgered) and LOW documentation/cost items. No CRITICAL or HIGH finding is open at `1ceba9f22`, so the mission is releasable from this branch with the follow-ups below tracked.

### Open items (non-blocking)

1. DRIFT-1 — make one full `tests/architectural/` run on the merged lane a precondition of `accept` (process; charter/implement-review skill).
2. DRIFT-2 — lockless rollback truncate on the coord fallback arm (`_restore_coord_status_artifacts`); decide: locked size-verified truncate vs retire the arm in the caller-migration mission; add to the risk register alongside R9.
3. RISK-1 — deferred-callable seam so the post-commit fan-out announces exactly the arm's own rows.
4. RISK-3/RISK-5 — resolve readiness only on the two guarded entry edges; log the missing-WP-file fail-open.
5. RISK-4 — `implement` pre-flight should skip the gate for an `in_progress` resume (caller-migration mission), then add the CLI-level US4-6 pin.
6. NFR-001 — spawn-recorder pins for writer families 4–7.
7. DRIFT-3 — operator confirmation that removing the #946 plain-batch skip is intended.
8. DRIFT-4/5/6 — fold the spec markers, contract deviations and two stale comments at the next touch.
9. Deferred handles owed by the operator (issue matrix): #3895 census-gate-rule note, #2173 StatusReader de-serialization note, #3893 compaction + finite-default-L1-timeout follow-ups, #1868 (Mission B), milestone reconciliation (#3893 4.0.0 vs 3.2.7).
10. Tooling: the shared `.venv` still carries an editable `.pth` pointing at the removed `.worktrees/fsm-write-path-integrity-01M1TZV6-lane-e/src`, so `.venv/bin/spec-kitty` fails with `ModuleNotFoundError: specify_cli`; `PYTHONPATH=src .venv/bin/python -m specify_cli …` works. Re-run `uv sync --frozen --all-extras` from the main checkout (not this review's job).

## Retrospective Reminder

The retrospective record **does exist** and was captured at the runtime terminus: `kitty-specs/fsm-write-path-integrity-01M1TZV6/retrospective.yaml` (`created_at 2026-09-06T17:05:39Z`, `provenance.kind: runtime_post_completion`, `findings_status: has_findings`, 5 `helped` / 7 `not_helpful`, 0 gaps, 0 proposals; the matching `RetrospectiveCaptured` event is the last row of `status.events.jsonl`). Note it lives in the mission's `kitty-specs/` directory (the durable primary home per #2119), not under `.kittify/missions/<mission_id>/`.

Canonical post-merge sequence from here: **mission review (this report) → verify the retrospective (present; no `retrospect create` needed) → surface findings**:

- `spec-kitty retrospect summary` — cross-mission aggregation (read-only)
- `spec-kitty agent retrospect synthesize --mission fsm-write-path-integrity-01M1TZV6` — inspect proposals (dry-run by default); `--apply` to apply

The captured `not_helpful` rows (WP02/WP04 rejection cycles; 7 `--force` overrides on WP02/WP04/WP05; "WP02 needed 2 implementation cycles") match this review's Step-1 reading: the forces were ledger-behind/lane-gate workarounds, and the two rejections were substantive (WP02: ruff-format gate + non-monotonic ULID assertion; WP04: legacy `dependencies` string forms locked the whole write path). Feed DRIFT-1 into the synthesis as the process learning the generator could not see.
