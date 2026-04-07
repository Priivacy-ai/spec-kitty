---
work_package_id: WP05
title: Recovery Extension And Mission Close
dependencies: []
requirement_refs:
- C-005
- FR-016
- FR-017
- FR-018
- FR-021
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning/base branch is main. Final merge target is main. Execution worktree is allocated by spec-kitty implement WP05 and resolved from lanes.json. WP05 also produces the Mission Close Ledger that satisfies DoD-4.
subtasks:
- T024
- T025
- T026
- T027
- T028
history:
- at: '2026-04-07T08:46:34Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/lanes/recovery.py
execution_mode: code_change
mission_number: '068'
mission_slug: 068-post-merge-reliability-and-release-hardening
owned_files:
- src/specify_cli/lanes/recovery.py
- src/specify_cli/cli/commands/implement.py
- kitty-specs/068-post-merge-reliability-and-release-hardening/wp05-verification-report.md
- kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md
- tests/lanes/test_recovery_post_merge.py
- tests/cli/commands/test_implement_base_flag.py
priority: P1
status: planned
---

# WP05 — Recovery Extension And Mission Close

## Objective

Fix the #415 known residual gap (post-merge recovery deadlock) by extending `scan_recovery_state` to consult mission status events and adding `--base <ref>` to `spec-kitty implement`. Author the WP05 verification report covering both pre-identified gaps from the Mission 067 Failure-Mode Evidence sections. Author the Mission Close Ledger that satisfies DoD-4 — every issue in the Tracked GitHub Issues table gets exactly one ledger row.

This is the WP that **closes the workflow-stabilization track**.

## Context

Issue [Priivacy-ai/spec-kitty#415](https://github.com/Priivacy-ai/spec-kitty/issues/415) (implementation crash recovery) and [Priivacy-ai/spec-kitty#416](https://github.com/Priivacy-ai/spec-kitty/issues/416) (merge interruption recovery) both have substantial code on main already. WP05 is verification-driven, but two residual gaps are pre-identified and must be addressed:

1. **#415 known gap (FR-021)**: `scan_recovery_state` (`src/specify_cli/lanes/recovery.py:174-267`) only iterates branches matching `kitty/mission-{slug}*`. When dependency lane branches have been merged-and-deleted, no live branches exist to scan, leaving the user with an unblockable post-merge unblocking workflow. Plus `spec-kitty implement` has no `--base` flag for explicit base ref selection.
2. **#416 known gap**: addressed by WP02 via FR-019/FR-020. WP05 verifies and closes #416.

WP05 is also the home of the Mission Close Ledger (`mission-close-ledger.md`), which is the mechanically-checkable artifact for DoD-4.

**Key spec references**:
- FR-016: written verification report covering both pre-identified gaps and any additional shapes
- FR-017: any residual gap surfaced gets fixed in this mission with a regression test
- FR-018: mission close ledger with one row per tracked issue
- FR-021: `scan_recovery_state` extension + `implement --base` flag (or file follow-up narrowing #415)
- C-005: Mission Close Ledger lives at `kitty-specs/068-.../mission-close-ledger.md` and is committed as part of mission close

**Key planning references**:
- `contracts/recovery_extension.md` for `scan_recovery_state` new parameter, `--base` flag spec, ledger schema
- `data-model.md` for `RecoveryVerificationEntry`, `MissionCloseLedgerRow`, and `RecoveryState.ready_to_start_from_target` field
- `research.md` "Failure-Mode Reproduction: FR-021" for the post-merge recovery deadlock walk-through
- `spec.md` "Mission 067 Failure-Mode Evidence (B): #415 post-merge recovery deadlock" for the full failure shape

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP05` and resolved from `lanes.json`.

To start work:
```bash
spec-kitty implement WP05
```

## Subtasks

### T024 — Extend `scan_recovery_state` to consult mission status events

**Purpose**: Make the recovery scanner aware that done-and-deleted lane branches are NOT missing — they're successfully merged. When a downstream WP's dependencies are all done, the scanner should report it as "ready to start from target branch tip."

**Files**:
- Modified: `src/specify_cli/lanes/recovery.py`

**Steps**:
1. Read the current `scan_recovery_state` function (lines 174-267 per spec analysis — verify against current main)
2. Add a new keyword parameter:
   ```python
   def scan_recovery_state(
       repo_root: Path,
       mission_slug: str,
       *,
       consult_status_events: bool = True,  # NEW, defaults True
   ) -> RecoveryState:
   ```
3. Add a new field to `RecoveryState`:
   ```python
   ready_to_start_from_target: list[str] = field(default_factory=list)
   ```
4. When `consult_status_events=True`:
   - Read `kitty-specs/<mission_slug>/status.events.jsonl`
   - Use `specify_cli.status.reducer.materialize` to compute the lane snapshot for every WP
   - For each WP whose lane is `done` and whose `kitty/mission-<slug>-<wp_id>` branch is absent, mark it as `merged_and_deleted` (not as "missing")
   - For each WP whose dependencies (read from the WP file frontmatter `dependencies:` list) are ALL `done`, append the WP id to `ready_to_start_from_target`
5. When `consult_status_events=False`, behave exactly as the current implementation (legacy live-branch-only path). This preserves backwards compatibility for any existing caller.

**Files**: `src/specify_cli/lanes/recovery.py`

**Validation**: a synthetic mission with WP01-WP05 marked done-and-deleted and WP06 dependent on WP05 returns `ready_to_start_from_target = ["WP06"]`.

### T025 — Add `--base <ref>` CLI flag to `spec-kitty implement`

**Purpose**: Give users a supported path to start a downstream WP from an explicit branch ref (typically `main`) after upstream lanes have been merged.

**Files**:
- Modified: `src/specify_cli/cli/commands/implement.py`

**Steps**:
1. Read the current `implement` command signature
2. Add a new optional parameter:
   ```python
   base: Optional[str] = typer.Option(
       None,
       "--base",
       help="Explicit base ref for the lane workspace (default: auto-detect)",
   ),
   ```
3. Inside the command:
   - If `base is None`, run the existing auto-detect logic (unchanged)
   - If `base is not None`:
     - Validate the ref resolves locally via `subprocess.run(["git", "rev-parse", "--verify", base], ...)`
     - If resolution fails, raise a clear error: `f"Base ref '{base}' does not resolve. Try 'git fetch' or 'git branch -a' to see available refs."`
     - Create the lane workspace from the explicit base via the existing worktree-allocator helper, passing the validated ref
4. Preserve all existing behavior when `--base` is omitted

**Files**: `src/specify_cli/cli/commands/implement.py`

**Validation**: `spec-kitty implement WP06 --base main` creates a worktree at the main branch tip. `spec-kitty implement WP06 --base bogus-ref` fails with the clear remediation error.

### T026 — Test suite for FR-021 + Scenario 7 + recovery scanner with merged-deleted deps

**Purpose**: Lock the FR-021 contract end-to-end. Reproduce Scenario 7 mechanically.

**Files**:
- New: `tests/lanes/test_recovery_post_merge.py`
- New: `tests/cli/commands/test_implement_base_flag.py`

**Tests** (per `contracts/recovery_extension.md` test surface table):
- `test_scan_recovery_state_finds_merged_deleted_deps` — synthetic mission with WP01-WP05 done-and-deleted, WP06 dependent on WP05, returns `ready_to_start_from_target == ["WP06"]`
- `test_scan_recovery_state_legacy_live_branch_path_unchanged` — `consult_status_events=False` returns the same shape as before FR-021
- `test_implement_base_flag_creates_workspace_from_ref` — `spec-kitty implement WP06 --base main` creates a worktree at main's tip
- `test_implement_base_flag_invalid_ref_fails_clearly` — `--base bogus-ref` fails with the documented error message
- `test_post_merge_unblocking_scenario_end_to_end` — **Scenario 7 reproduction**:
  1. Set up a synthetic mission with WP01-WP06 in a dependency chain
  2. Implement and merge WP01-WP05 (use a synthetic merge that mimics the post-merge state with branches deleted)
  3. Run `scan_recovery_state` and assert WP06 is in `ready_to_start_from_target`
  4. Run `spec-kitty implement WP06 --base main` and assert a fresh lane workspace is created
  5. No manual `.kittify/` state edits required

**Validation**: `pytest tests/lanes/test_recovery_post_merge.py tests/cli/commands/test_implement_base_flag.py -v` exits zero. No network calls.

### T027 — Author `wp05-verification-report.md`

**Purpose**: Account for every documented failure shape from #415 and #416 with a written verification report. Both pre-identified gaps must appear with evidence.

**Files**:
- New: `kitty-specs/068-post-merge-reliability-and-release-hardening/wp05-verification-report.md`

**Steps**:
1. Use the structure from `contracts/recovery_extension.md` "Verification report" section
2. Authored at: today's date
3. Validated against: current HEAD commit SHA
4. Coverage statement: "This report accounts for every documented failure shape from issues #415 and #416, including the two pre-identified gaps from the Mission 067 Failure-Mode Evidence sections."
5. **Pre-identified gap 1 (#416 status-events loss)**:
   - Failure shape: `_run_lane_based_merge` writes `done` events to disk but never commits them
   - Status: `fixed_by_this_mission`
   - Evidence: WP02 FR-019 (`safe_commit` insertion) + FR-020 (`tests/cli/commands/test_merge_status_commit.py::test_done_events_committed_to_git`)
   - Verified: read `git show HEAD:kitty-specs/<mission>/status.events.jsonl` after a synthetic merge
6. **Pre-identified gap 2 (#415 post-merge recovery deadlock)**:
   - Failure shape: `scan_recovery_state` ignores merged-and-deleted dependency branches; `implement` does not accept `--base main`
   - Status: `fixed_by_this_mission`
   - Evidence: this WP's T024 + T025 + T026 tests
   - Verified: Scenario 7 reproduced in `test_post_merge_unblocking_scenario_end_to_end`
7. **Other failure shapes from #415/#416**: walk both issues' descriptions and comments. For each documented shape that's not the pre-identified gaps:
   - If current main + this mission's fixes already cover it: status = `fixed_by_current_main` or `fixed_by_this_mission`, evidence = pointer to the relevant test or code
   - If there's a residual gap: status = `residual_gap`, file a follow-up issue and link it
8. Commit the file as `kitty-specs/068-post-merge-reliability-and-release-hardening/wp05-verification-report.md`

**Validation**: the file exists, has all required sections, and every shape has either a `fixed_*` or `residual_gap` status with an evidence pointer.

### T028 — Author `mission-close-ledger.md` with one row per tracked issue

**Purpose**: Satisfy DoD-4 — the mechanically-checkable artifact that proves every tracked issue has a final disposition.

**Files**:
- New: `kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md`

**Steps**:
1. Use the structure from `contracts/recovery_extension.md` "Mission close ledger" section
2. Authored at: today's date
3. Validated DoD: "every issue from the Tracked GitHub Issues table appears below"
4. **Primary scope rows** (must implement issues):
   - #454: WP01 stale-assertion analyzer shipped
   - #456: WP02 strategy wiring + squash default + push-error parser shipped
   - #455: WP03 validation report + close-with-evidence OR tighten-workflow decision
   - #457: WP04 release-prep CLI shipped + FR-023 scope-cut documented
5. **Verification-and-close scope rows**:
   - #415: WP05 FR-021 fix landed (scan_recovery_state + --base)
   - #416: WP02 FR-019/FR-020 fix landed; WP05 verified
6. **Carve-out rows** (filed as follow-ups):
   - FSEvents debounce / `_worktree_removal_delay()` empirical timing — link to the new follow-up issue
   - Dirty classifier `git check-ignore` consultation — link to the new follow-up issue
7. Each row contains: `issue_id`, `decision` (`closed_with_evidence` | `narrowed_to_followup`), `reference` (PR URL, commit SHA, or follow-up issue link), `notes`
8. Render as a markdown table

**Files**: `kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md`

**Validation**: every issue from `spec.md` Tracked GitHub Issues table appears in the ledger with exactly one row. The DoD-4 test (run by hand or automated): `grep -c "^|" mission-close-ledger.md` matches the expected row count.

## Test Strategy

Tests are required by FR-021. The verification report (T027) and ledger (T028) are markdown artifacts that lock the mission close contract. Use synthetic git/mission fixtures for the recovery and `--base` tests.

## Definition of Done

- [ ] `scan_recovery_state` extended to consult status events; new `consult_status_events` keyword parameter; `RecoveryState.ready_to_start_from_target` field added
- [ ] `spec-kitty implement` accepts `--base <ref>` flag with validation and clear error
- [ ] All FR-021 tests pass including Scenario 7 end-to-end
- [ ] `wp05-verification-report.md` exists with both pre-identified gaps accounted for and any additional shapes documented
- [ ] `mission-close-ledger.md` exists with one row for every issue in the Tracked GitHub Issues table
- [ ] Carve-out follow-up issues filed and linked from the ledger
- [ ] DoD-4 mechanically verified: ledger row count matches tracked issue count
- [ ] `mypy --strict` passes on `recovery.py` and `implement.py`
- [ ] `ruff` clean

## Risks

- **Backwards compatibility for `scan_recovery_state`**: existing callers must continue to work. The new `consult_status_events` parameter defaults to True (the new behavior), but the legacy live-branch-only path must still be reachable via `consult_status_events=False`. Add a regression test.
- **Cyclic dependency detection in WP frontmatter**: T024 reads WP file frontmatter `dependencies:` lists. Don't introduce a `from specify_cli.lanes.recovery import ...` chain that imports the WP loader and creates a cycle.
- **Ledger drift**: if any WP closes its issue with a different decision than what's recorded in the ledger, the mission close fails DoD-4. Update the ledger as the last step at mission close, not before.

## Reviewer Guidance

- Verify both `scan_recovery_state` paths (consult_status_events True and False) have explicit tests
- Verify `--base` flag produces a clear error on invalid ref
- Walk Scenario 7 by hand: check out a synthetic mission state where WP01-WP05 are done-and-deleted, run `spec-kitty implement WP06 --base main`, confirm it succeeds without manual `.kittify/` edits
- Open `wp05-verification-report.md` and check that every shape from #415 and #416 is accounted for
- Open `mission-close-ledger.md` and grep-count the rows: there must be one for each issue in the Tracked GitHub Issues table
- Verify every closed issue has its reference filled in (PR URL or commit SHA), not a placeholder

## Next steps after merge

WP05 lands the mission close artifact. Once the ledger is committed and the issues closed, mission 068 is done and the workflow-stabilization track is empty.
