# Mission Specification: Post-Merge Reliability And Release Hardening

**Mission**: 068-post-merge-reliability-and-release-hardening
**Type**: software-dev
**Priority**: P1 stabilization
**Status**: draft
**Target branch**: main
**Created**: 2026-04-07
**Validated against**: Fresh clone `/tmp/spec-kitty-20260407-090957` at commit `7307389a1f529dae9e90279ea972609bb0b420aa`

---

## Mission Intent

This is the **final** workflow-stabilization mission for the spec-kitty core repository. Its purpose is to drive the open workflow-stabilization backlog to zero by:

1. Finishing the four issues that are still clearly current on main, and
2. Explicitly verifying-and-closing the two older recovery issues that already have substantial implementation and test coverage on main.

A successful mission ends the current workflow-stabilization track cleanly. After this mission lands, the repository should not need another broad "workflow stabilization" mission.

---

## Tracked GitHub Issues

### Primary scope (must implement)

| Issue | Title | Owning WP |
|---|---|---|
| Priivacy-ai/spec-kitty#454 | Post-merge stale test assertion detection/reporting | WP01 |
| Priivacy-ai/spec-kitty#456 | Protected-branch linear-history support in `spec-kitty merge` | WP02 |
| Priivacy-ai/spec-kitty#455 | Diff-coverage CI policy cleanup/closure for large PRs | WP03 |
| Priivacy-ai/spec-kitty#457 | Automatic release prep after merge | WP04 |

### Verification-and-close scope (prove fixed or finish residual gaps)

| Issue | Title | Owning WP |
|---|---|---|
| Priivacy-ai/spec-kitty#415 | Implementation crash recovery | WP05 |
| Priivacy-ai/spec-kitty#416 | Merge interruption/recovery idempotence | WP02 (fix) + WP05 (verification) |

> **Footnote on #416**: The status-events commit fix (FR-019/FR-020) lands in WP02 because it edits `_run_lane_based_merge` in the same file and function as WP02's strategy wiring. WP05 owns the verification report and the final close-with-evidence comment for #416.

### Explicitly out of scope

The following issues are **not** part of this mission. Either they are already materially implemented on current main and need no fresh feature work, or they belong to a different track:

- Priivacy-ai/spec-kitty#412 — already implemented on main, no fresh work needed
- Priivacy-ai/spec-kitty#414 — already implemented on main, no fresh work needed
- Priivacy-ai/spec-kitty#442 — already implemented on main, no fresh work needed
- Priivacy-ai/spec-kitty#393 — already implemented on main, no fresh work needed
- Priivacy-ai/spec-kitty#447 — already implemented on main, no fresh work needed
- Priivacy-ai/spec-kitty#443 — already implemented on main, no fresh work needed
- Priivacy-ai/spec-kitty#419 — cross-repo contract/cutover work, separate track
- Doctrine/agent-profile architecture work — separate track
- Typed dashboard contract migration — separate track
- Any new feature work unrelated to merge/release/recovery stabilization

---

## Current-Main Observations

These observations were validated against the fresh clone above. Subsequent work packages should re-verify before changing behavior.

- **#455 is partially addressed already.** `.github/workflows/ci-quality.yml` now enforces critical-path diff coverage and emits a separate advisory full-diff report. WP03 must verify whether the remaining hard-fail behavior still mismatches the intended policy before changing anything. If current main already resolves the issue, WP03 closes it with evidence rather than changing code.
- **#456 is still clearly current.** `spec-kitty merge` accepts a `--strategy` flag but currently discards it. The lower-level lane merge code hardcodes merge commits. Both behaviors conflict with protected-branch environments that require linear history.
- **#415 and #416 have substantial code and tests on main already.** Implementation recovery exists, merge resume/abort exists, and recovery tests exist. WP05 must treat these as "prove fixed or finish residual gaps," not greenfield work.

---

## Mission 067 Failure-Mode Evidence (A): #416 status-events loss

While preparing this mission, the maintainer reproduced and root-caused a concrete failure mode that satisfies the "#416 Option C" framing — uncommitted status events can be silently destroyed when a merge is externally rebuilt. **WP02 owns the fix** (it edits the same function as WP02's strategy wiring) and **WP05 owns the verification** (the report and close-with-evidence comment). It is recorded here so the implementer begins with a known target rather than discovering it.

### What happened on 067

1. `spec-kitty merge` ran locally on 3.1.0a6. Lane→mission→target merges produced commits `ed4ad118`, `598f2241`, `dfacf707`, `b36383c2`, `bc47f57d` via `git update-ref` from temp worktrees.
2. The mark-done loop in `_run_lane_based_merge` (`src/specify_cli/cli/commands/merge.py:277-464`) wrote 6 `done` events to the working tree's `status.events.jsonl` via `_mark_wp_merged_done` → `emit_status_transition` → `_store.append_event` (`src/specify_cli/status/store.py:28-38`). **These events were never `git add`/`git commit`-ed.** There is no `safe_commit` call anywhere in the merge command after the mark-done loop, and `_store.append_event` is a pure file-write with no git interaction.
3. `git push origin main` was rejected by linear-history protection (#456).
4. To work around protection, the maintainer reset and rebuilt the change as a squash PR. **This discarded the local merge commits AND wiped the uncommitted done events.**
5. PR #452 squash-merged as `ba356d15`. The squash brought in only the committed lane content. Done events were lost.

### Verification

`status.events.jsonl` was read at `bc47f57d` (the local mission→main merge commit, still reachable via reflog). 43 lines, identical to the current file, ending at WP02 approved at 19:20:52. Zero `to_lane: done` entries, zero `actor: merge` entries. The event log was never written to by the local merge — confirming the events existed only in the post-merge working tree, never in any committed state.

### Why WP01 of 067 did not catch it

WP01 of 067's scope was `MergeState` lifecycle, dedup guards, retry tolerance, and `--resume`/`--abort`. The "Option C" call from #416 ("commit status files BEFORE the crash-prone step") was not in the WP01 task list. The fact that uncommitted state survives only by happenstance was not flagged by the WP01 review either.

### Independence from #456

Even if linear-history support had been in place and `--strategy squash` had been the default, the squash commit is built from the committed working tree. The uncommitted done events would still have been left out of the squash. **This bug manifests any time the user rebuilds the merge externally — protection or not.** #456 only made it more likely to occur by forcing the user to reset.

### Scope (preempting "what about MergeState?")

The same write-without-commit pattern applies to `MergeState` persistence under `.kittify/runtime/merge/<mission_id>/state.json` (`src/specify_cli/merge/state.py:138-150`), and to the per-WP `save_state` writes inside the merge loop (`merge.py:392-399`) and the `cleanup_merge_workspace`/`clear_state` calls at the end (`merge.py:463-464`). However, `.kittify/runtime/` is the canonical **runtime** state location and is intentionally ephemeral — those paths are not the cause of the 067 done-events loss. The 067 loss is specific to the feature-directory event log under `kitty-specs/<mission>/`, which IS tracked in git and IS the canonical authority for WP lane state. WP05's fix surface is therefore limited to `status.events.jsonl` and `status.json` for the mission's feature directory; runtime state under `.kittify/runtime/` is out of scope for this fix.

### Concrete fix surface

Between the mark-done loop and the worktree-removal step in `_run_lane_based_merge` (`merge.py` ~line 400 ↔ ~line 408), call:

```python
safe_commit(
    repo_path=main_repo,
    files_to_commit=[feature_dir / "status.events.jsonl", feature_dir / "status.json"],
    commit_message=f"chore({mission_slug}): record done transitions for merged WPs",
    allow_empty=False,
)
```

The `safe_commit` pattern is already used by `cli/commands/implement.py:460`. This call satisfies #416 Option C and makes the mark-done step crash-safe and reset-safe.

---

## Mission 067 Failure-Mode Evidence (B): #415 post-merge recovery deadlock

A second concrete gap was surfaced by current-main analysis. This one belongs to #415 ("Implementation crash recovery") and must be addressed by WP05 — either by landing the fix or by filing an explicit follow-up that narrows #415's scope.

### What is broken

`scan_recovery_state` (`src/specify_cli/lanes/recovery.py:174-267`) only iterates branches matching `kitty/mission-{slug}*` returned by `_list_mission_branches`. **If a mission's lane branches were already merged and deleted (the post-merge case), there is nothing left to scan.** The user's "WP07 deadlock after deps merged" scenario from #415 therefore still has no resolution on current main: the recovery scanner finds no branches and no claim files, declares the workspace clean, and leaves the user stuck.

The `spec-kitty implement` command also still does not accept `--base main`. A user trying to start a fresh downstream WP after upstream lanes have already been merged-and-deleted has no supported path to do so without manually editing `.kittify/` state.

### Why this matters

Both shapes are common after a successful merge run: lane branches get deleted by post-merge cleanup, then the user wants to either (a) recover from a crash that happened earlier in the same session, or (b) start a downstream WP that depends on the now-merged work. Today both paths silently fail.

### Required disposition

WP05 SHALL EITHER:

1. **Land the fix**: extend `scan_recovery_state` to consult mission status events alongside live branch state, so a WP whose dependency branches have been merged-and-deleted is recognized as "ready to start" rather than "no recovery needed"; AND add `--base main` to the `implement` command so users can explicitly start a downstream WP from the post-merge target branch.
2. **Or narrow #415**: file a new follow-up issue capturing the exact unfixed scenario, link it from #415, and record the close-or-narrow decision in the Mission Close Ledger.

WP05 SHALL NOT silently leave #415 open.

---

## Primary Users

- **Spec Kitty maintainers** running release prep, merging completed missions, and triaging the workflow-stabilization backlog.
- **Spec Kitty contributors** running missions on protected-branch repositories where merge commits are forbidden.
- **Spec Kitty users** who benefit from cleaner failure modes when implementation crashes mid-WP or when a multi-WP merge is interrupted.
- **Spec Kitty CI** authors who need diff-coverage signals that hard-fail only on intended risk surfaces.

---

## User Scenarios & Testing

### Primary Scenarios

#### Scenario 1: Maintainer detects stale test assertions after a multi-lane merge

1. Maintainer runs `spec-kitty merge` for a feature with multiple lanes whose changes touch related production code paths.
2. After the merge completes, the post-merge analyzer inspects the merged diff and the test files near the changed code.
3. The analyzer surfaces a report listing test assertions that are likely stale (literal values, regex patterns, or fixture comparisons that reference now-changed strings, file paths, line numbers, or schema fields).
4. Each finding includes file path, line number, the changed source location it references, and a confidence indicator.
5. The maintainer can review the report, fix the assertions before re-running the suite, and avoid the surprise CI failures that motivated the issue.

**Acceptance**: Given a merged change that renames a function, when the post-merge analyzer runs, then any test asserting on the old name is reported with file:line and a "likely stale" confidence indicator.

#### Scenario 2: Contributor merges into a protected-branch repository

1. A repository maintainer has configured branch protection on `main` requiring linear history (no merge commits).
2. A contributor runs `spec-kitty merge` after completing a mission's WPs.
3. The merge succeeds locally and the resulting history is push-acceptable on the protected branch — no merge commits are created on the mission→target step.
4. If the contributor explicitly requests `--strategy merge`, the override is honored and the contributor is warned that their target branch may reject the push.
5. If a push is rejected because of linear-history protection, the failure message includes a remediation pointer to `--strategy squash` and to the project-level config key.

**Acceptance (default path)**: Given a target branch protected against merge commits, when `spec-kitty merge` runs without arguments, then the resulting commit on the target branch is a single squashed commit and a subsequent push succeeds without rejection.

**Acceptance (override path)**: Given a target branch protected against merge commits AND `--strategy merge` explicitly passed, when the push is attempted and rejected, then the rejection message presented to the user contains the substring `--strategy squash` and a reference to the `merge.strategy` config key.

#### Scenario 3: Maintainer runs release prep after a mission lands

1. A mission's final WP merges into the target branch.
2. The maintainer runs the release-prep flow (a CLI command or workflow step).
3. The flow generates a draft changelog entry from mission and WP artifacts (titles, descriptions, accepted-on dates, contributing actors).
4. The flow proposes a version bump for the requested release channel (alpha, beta, or stable).
5. The flow assembles the inputs needed for the release PR/tag step (version string, changelog text, mission slug list, branch name).
6. The maintainer reviews the proposed inputs, makes any edits, and triggers the release through the existing GitHub release workflow.

**Acceptance**: Given a completed mission with at least one merged WP, when the release-prep flow runs, then it produces a version bump proposal, a draft changelog block, and the inputs required for the release tag/PR step without the maintainer manually reading mission artifacts.

#### Scenario 4: CI surfaces diff-coverage signals correctly on a large PR

1. A contributor opens a large PR touching many files.
2. CI runs the diff-coverage policy.
3. Critical-path diff coverage is enforced as a hard failure if it falls below the configured threshold.
4. Full-diff coverage runs as an advisory report with no hard-fail.
5. The CI output explicitly identifies which surface produced any failure and which surface is advisory only.
6. The contributor is not blocked by misleading hard failures on surfaces that the policy never intended to gate.

**Acceptance**: Given a large PR that meets critical-path diff coverage but misses full-diff coverage, when CI runs, then the build passes and the contributor sees the advisory full-diff report alongside the passing critical-path enforcement.

#### Scenario 5: Implementation recovers cleanly from a mid-WP crash

1. A coding agent is implementing a WP and the process crashes (the host kernel kills it, a runaway tool hangs and is interrupted, or the user aborts).
2. The maintainer runs the implement-recovery path.
3. Recovery detects partial state, restores the WP to a coherent lane, releases stale claims, and presents the maintainer with a clear next action.
4. Re-running `spec-kitty implement WP##` resumes from a deterministic point without requiring manual cleanup of `.kittify/` state.

**Acceptance**: Given a WP whose implementation was interrupted by a process crash, when recovery runs, then the WP is returned to a coherent lane (`planned`, `claimed`, or `in_progress`), no orphan claim files remain, and a subsequent `implement` call succeeds without manual state edits.

#### Scenario 6: Merge resumes cleanly after interruption

1. A maintainer runs `spec-kitty merge` for a feature with several WPs.
2. The merge is interrupted partway through (Ctrl+C, terminal disconnect, conflict on a later WP).
3. The maintainer runs `spec-kitty merge --resume`.
4. Resume reads the persisted merge state, skips already-merged WPs, and continues from the exact next WP in the order.
5. If aborted, `spec-kitty merge --abort` rolls the workspace back to a clean state with no partial commits or dangling worktrees.

**Acceptance**: Given an interrupted merge with two WPs already completed and one pending, when `spec-kitty merge --resume` runs, then the pending WP is merged, the previously-completed WPs are not re-merged, and the merge state file is cleared on success.

#### Scenario 7: Maintainer starts a downstream WP after upstream lanes have merged

1. A mission has WPs WP01–WP06 in a dependency chain. WP01–WP05 have been implemented, reviewed, and merged into the target branch. Their lane branches were deleted by post-merge cleanup.
2. The maintainer wants to start WP06.
3. `spec-kitty implement WP06` recognizes that WP06's dependencies are already integrated into the target branch (not present as live lane branches), creates WP06's lane workspace based on the current target branch tip, and proceeds normally.

**Acceptance**: Given a WP whose dependency lane branches have all been merged-and-deleted, when `spec-kitty implement WP##` runs, then a new lane workspace is created from the target branch tip without requiring manual `--base` overrides or `.kittify/` state edits.

### Edge Cases

- **Stale-detector false positives.** The detector must err on the side of cheap guidance, not perfect proof. False-positive findings must be explicitly labeled "likely stale," never "stale."
- **Merge strategy mismatches the project config.** If a contributor passes `--strategy merge` to a repo configured for `squash`, the override is honored but a warning is emitted.
- **Release prep on a mission with no merged WPs.** The flow refuses to run and explains why.
- **Recovery against an already-clean state.** Recovery reports "no recovery needed" without modifying state.
- **Resume against a missing merge-state file.** Resume reports "no merge in progress" with guidance to run `spec-kitty merge` from scratch.
- **Protected-branch detection fallback.** Squash is the default for the mission→target step regardless of any external detection. Lane→mission merges (which never hit protected branches) keep their existing merge-commit behavior.

---

## Functional Requirements

| ID | Requirement | Owning WP | Status |
|---|---|---|---|
| FR-001 | The post-merge stale-assertion analyzer SHALL accept a merge result and emit a structured report listing test assertions likely invalidated by merged source changes. | WP01 | proposed |
| FR-002 | The analyzer SHALL identify test references to changed source identifiers (function names, class names, file paths, error message strings, schema fields) by parsing **both source files and test files** with Python's stdlib `ast` module. The analyzer SHALL NOT use regex/text scanning over raw test file content for identifier matching, because regex bleeds false positives from comments and inert string content (which would make NFR-002's FP ceiling impractical). The analyzer SHALL NOT load, import, or execute the project's test suite — it operates purely on the merged diff and the AST of test files reachable from `git ls-files`. **Worked example**: a test that asserts `error_message == "foo"` SHALL be flagged only if the merge changes the literal `"foo"` in source AND the test file's AST contains a `Constant("foo")` node in an assertion-bearing position. A test whose comments or unrelated string literals merely mention `"foo"` SHALL NOT be flagged. | WP01 | proposed |
| FR-003 | The analyzer SHALL classify each finding with a confidence indicator (`high`, `medium`, `low`) and SHALL never mark a finding as "definitely stale." | WP01 | proposed |
| FR-004 | The analyzer SHALL be invokable as a CLI subcommand at the locked path `spec-kitty agent tests stale-check --base <ref> --head <ref>` (a new `agent tests` group at `src/specify_cli/cli/commands/agent/tests.py`). The analyzer SHALL also be invokable as a library function `run_check(...)` exported from `src/specify_cli/post_merge/stale_assertions.py`. The post-merge workflow inside `spec-kitty merge` SHALL invoke the analyzer via **direct library import** (`from specify_cli.post_merge.stale_assertions import run_check`), NOT by spawning the CLI subcommand as a subprocess. The CLI entry and the merge runner are two thin shims around the same library function. The merge summary SHALL include the analyzer's findings inline. | WP01 | proposed |
| FR-005 | `spec-kitty merge` SHALL honor the `--strategy` flag end-to-end. The flag value SHALL flow from the CLI surface into the lane-merge implementation and SHALL determine the git command sequence used for the mission→target step. | WP02 | proposed |
| FR-006 | The mission→target merge step SHALL default to `squash` when no `--strategy` flag and no project-level config override are present. | WP02 | proposed |
| FR-007 | Lane→mission merges SHALL retain merge-commit behavior because lane→mission merges are local and never interact with protected branches. | WP02 | proposed |
| FR-008 | The project-level configuration file (`.kittify/config.yaml`) SHALL accept a `merge.strategy` key with allowed values `merge`, `squash`, and `rebase`. The lane-merge implementation SHALL read and honor this key. | WP02 | proposed |
| FR-009 | When a push to the target branch fails because of linear-history protection, `spec-kitty merge` SHALL parse the captured git stderr and emit a remediation hint pointing the user at `--strategy squash` and the `merge.strategy` config key. The parser SHALL match any of the following case-insensitive substrings: `merge commits`, `linear history`, `fast-forward only`, `GH006`, `non-fast-forward`. On unknown rejection messages the parser SHALL fail open (no remediation hint) rather than emit a misleading hint. **Note**: with squash as the default (FR-006), this requirement is a backstop for users who explicitly opt into `--strategy merge`; it is not expected to fire on the default path. | WP02 | proposed |
| FR-010 | WP03 SHALL begin with a written validation of current `ci-quality.yml` behavior on a representative large PR diff before any policy code is changed. | WP03 | proposed |
| FR-011 | If WP03's validation shows that current main already satisfies the issue intent, WP03 SHALL close issue #455 with an evidence comment and tighten the documentation/CI messages so future contributors understand which surface is enforced and which is advisory. | WP03 | proposed |
| FR-012 | If WP03's validation shows residual policy mismatch, WP03 SHALL adjust the workflow so that only the intended critical-path surface produces hard failures and full-diff coverage runs as advisory. | WP03 | proposed |
| FR-013 | A release-prep CLI command SHALL exist that accepts a target release channel (`alpha`, `beta`, `stable`) and produces (a) a draft changelog block, (b) a proposed version bump, and (c) the inputs required for the release tag/PR workflow. | WP04 | proposed |
| FR-014 | The release-prep command SHALL build the changelog block from mission and WP artifacts on disk (titles, descriptions, accepted-on dates, contributors). It SHALL NOT require a network call to GitHub. | WP04 | proposed |
| FR-015 | The release-prep command SHALL emit its outputs both as printable text for the maintainer and as a structured JSON document so future automation can consume it. | WP04 | proposed |
| FR-023 | WP04 SHALL document in the issue #457 close comment exactly which steps from the original issue are now automated (changelog draft, version bump, structured release-prep payload) and which remain manual (PR creation, tag push, workflow monitoring). If the #457 reporter requests automation of the still-manual steps, those SHALL be filed as a follow-up issue rather than expanded into this mission. | WP04 | proposed |
| FR-016 | WP05 SHALL produce a written verification report covering each documented failure shape from issues #415 and #416. The report SHALL explicitly account for the two pre-identified gaps from the Mission 067 Failure-Mode Evidence sections: (1) `_run_lane_based_merge` does not commit status events before workspace cleanup (#416, addressed by **WP02 via FR-019/FR-020**); (2) `scan_recovery_state` ignores merged-and-deleted dependency lane branches and `implement` does not accept `--base main` (#415, addressed by **WP05 via FR-021**). For each additional shape encountered, the report SHALL state "fixed by current main, evidence: …" or "residual gap: …". | WP05 | proposed |
| FR-017 | For any residual gap surfaced by WP05, a fix SHALL be landed in this mission and a regression test SHALL be added. | WP05 | proposed |
| FR-018 | At mission close, every issue in the tracked-issues table SHALL be either closed (with a comment linking the merge commit and the verification evidence) or have a clearly narrowed scope captured in a follow-up issue. | WP05 | proposed |
| FR-019 | WP02 SHALL fix the uncommitted-status-events bug documented in the Mission 067 Failure-Mode Evidence (A) section by inserting a `safe_commit` call after the per-WP `_mark_wp_merged_done` loop and before the worktree-removal step in `_run_lane_based_merge` (`src/specify_cli/cli/commands/merge.py`). The committed payload SHALL be `status.events.jsonl` and `status.json` for the mission's feature directory, using the `safe_commit` helper imported from `specify_cli.git` (the same helper called from `cli/commands/implement.py:460`). | WP02 | proposed |
| FR-020 | A regression test SHALL exercise the lane-based merge path end-to-end and SHALL assert that, after `_run_lane_based_merge` returns successfully, `git show HEAD:kitty-specs/<mission>/status.events.jsonl` contains a `to_lane: done` entry for every WP in the merged feature. The test SHALL run without network access and SHALL be added to the pytest suite. This proves FR-019's contract directly: events are durably committed at the time the merge command returns, not left in the working tree. | WP02 | proposed |
| FR-021 | WP05 SHALL address the #415 known residual gap (documented in the Mission 067 Failure-Mode Evidence (#415) section) by EITHER (a) extending `scan_recovery_state` (`src/specify_cli/lanes/recovery.py:174-267`) to consult mission status events alongside live branch state so a WP whose dependency lane branches were merged-and-deleted is recognized correctly, AND adding `--base main` support to the `spec-kitty implement` command, OR (b) filing a new follow-up issue that explicitly narrows #415's scope to just the unfixed scenario and recording the close-or-narrow decision in the Mission Close Ledger. WP05 SHALL NOT silently leave #415 open. | WP05 | proposed |
| FR-022 | If WP01 implementation determines that the FR-002 heuristic exceeds NFR-002's false-positive threshold on the curated benchmark, WP01 SHALL narrow scope (e.g. literal-string changes only, or function-rename detection only), SHALL document the narrowed scope as a new constraint row in this spec before requesting review, and SHALL update FR-001/FR-002 to reflect the narrowed surface. WP01 SHALL NOT ship an analyzer that exceeds NFR-002 by default. | WP01 | proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The post-merge stale-assertion analyzer SHALL run within 30 seconds on a repository the size of spec-kitty core (≈ 9000+ tests in the pytest suite per the 067 PR description, with comparable source LOC including templates and skills) on a developer laptop. | ≤ 30 seconds wall clock on spec-kitty core | proposed |
| NFR-002 | The stale-assertion analyzer SHALL produce no more than 5 false-positive findings per 100 LOC of merged change on a representative sample, measured against a curated benchmark in `tests/`. | ≤ 5 false positives per 100 merged LOC | proposed |
| NFR-003 | The mission→target merge step SHALL succeed against a target branch protected with `require_linear_history = true` in 100% of merge attempts that use the default strategy on a clean lane workspace. | 100% success on the integration test matrix | proposed |
| NFR-004 | The release-prep command SHALL complete within 5 seconds on a mission with up to 16 WPs. | ≤ 5 seconds wall clock | proposed |
| NFR-005 | All new tests added by this mission SHALL run in the existing pytest suite without requiring network access. | 0 network calls in the new test paths | proposed |
| NFR-006 | New code added by this mission SHALL maintain `mypy --strict` cleanliness and SHALL meet the critical-path diff coverage threshold **as it exists at mission start (commit `7307389a`)**. WP03 may legitimately change that threshold or its include-list as part of #455's policy cleanup; if WP03 does so, NFR-006 SHALL be re-evaluated against the post-WP03 threshold rather than blocking the WP03 change. | mypy strict pass + critical-path coverage ≥ threshold pinned at commit `7307389a`, re-evaluated only after WP03 lands | proposed |

## Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | The mission→target merge default SHALL be `squash`. Lane→mission merges retain `merge` semantics. | Lane→mission is local and never hits branch protection; mission→target lands on shared branches that may enforce linear history. Squash is the only default that is safe in both regimes without external detection. | accepted |
| C-002 | This mission SHALL NOT introduce GitHub API calls to detect branch protection state. Detection SHALL be reactive (parse git push errors) and configurable via `.kittify/config.yaml`. | Auth, rate limits, GHE/GitLab/Bitbucket coverage gaps, and offline dev all degrade an API-based detector to its config fallback. The reactive path is 100% accurate and free. | accepted |
| C-003 | This mission SHALL NOT re-implement the existing implement-recovery or merge-resume subsystems from scratch. WP05 is verification-driven; only residual gaps are coded. | Both subsystems already have substantial code and tests on main. Re-implementation would create regression risk for no benefit. | accepted |
| C-004 | This mission SHALL NOT touch any of the explicitly out-of-scope issues listed above, even if related code is encountered. | Scope discipline is the difference between "ending the workflow-stabilization track" and "carrying it forward indefinitely." | accepted |
| C-005 | Every closed issue from this mission SHALL have an explicit closing comment that links to the merge commit and the verification evidence. Issues SHALL NOT be silently closed by automation. The Mission Close Ledger SHALL live at `kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md` and SHALL be committed as part of the mission close. | Closing-with-evidence is what makes "definition of done" auditable in six months. | accepted |
| C-006 | New work in this mission SHALL respect the project's standard test, type, and lint checks: pytest passes, `mypy --strict` passes, ruff is clean. | Charter policy. | accepted |

---

## Success Criteria

The mission is successful when **all** of the following are true:

1. **Stale-assertion detector ships and is exercised in tests.** Maintainers running `spec-kitty merge` see stale-assertion findings inline with the merge summary on at least one synthetic test repository in CI.
2. **Merge strategy is honored.** The `--strategy` flag is no longer silently discarded. The lane-merge implementation respects both the flag and the `merge.strategy` config key. Default behavior on the mission→target step is squash.
3. **Protected linear-history workflow has a coherent supported path.** A target branch protected with `require_linear_history = true` accepts the default `spec-kitty merge` output without rejection.
4. **Diff-coverage policy is explicit and validated.** Either issue #455 is closed with documented evidence that current main already satisfies the policy intent, or the workflow is corrected so only critical-path coverage hard-fails. CI output identifies enforced vs advisory surfaces explicitly.
5. **Release prep flow is real.** A maintainer can run a single command to produce a draft changelog, proposed version bump, and release-PR/tag inputs, instead of reconstructing them by hand.
6. **#415 and #416 are closed-with-evidence or narrowed-with-fixes.** The verification report exists in the mission artifacts and each documented failure shape is accounted for.
7. **Every tracked issue has a final disposition recorded.** After this mission lands, every issue listed in the Tracked GitHub Issues table SHALL have a final disposition recorded in the Mission Close Ledger (`closed_with_evidence` or `narrowed_to_followup` with a follow-up issue link). No issue from the table SHALL remain open without an explicit ledger entry.

---

## Key Entities

- **Stale-assertion finding** — `{ test_file, test_line, source_file, source_line, changed_symbol, confidence, hint }`. Emitted by the post-merge analyzer.
- **Merge strategy** — One of `merge`, `squash`, `rebase`. Resolved from CLI flag, then config key, then squash default. Applies to the mission→target step.
- **Project merge config** — A `merge.strategy` key in `.kittify/config.yaml`.
- **Release-prep payload** — `{ channel, current_version, proposed_version, changelog_block, mission_slug_list, target_branch, structured_inputs }`. Emitted by the release-prep command.
- **Recovery verification entry** — `{ failure_shape, status: fixed_by_current_main | residual_gap, evidence_path, regression_test? }`. Recorded by WP05.
- **Mission close ledger** — A markdown file at `kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md` containing a list of `{ issue_id, decision: closed_with_evidence | narrowed_to_followup, reference (PR/commit/follow-up issue link), notes }` rows captured at mission close. Committed as part of the final mission artifacts.

---

## Assumptions

- The stale-assertion detector targets Python tests in this mission. JavaScript/TypeScript test detection is out of scope and can be added in a follow-up if needed.
- The release-prep command builds on existing version-bump and changelog infrastructure. It does not need to fully automate PyPI propagation checks; that would bloat scope.
- WP03 is verification-first. If validation shows current main already satisfies the policy intent, WP03 closes the issue with evidence and may need only documentation/message tightening.
- WP05 begins with a written verification report. **Two residual gaps are pre-identified by current-main analysis** and SHALL be addressed in this mission: (a) `scan_recovery_state` does not handle the case where dependency lane branches were merged-and-deleted before the user attempts to implement a downstream WP — this blocks the post-crash unblocking workflow described in #415 (addressed by **WP05** via FR-021); (b) `_run_lane_based_merge` does not commit status events before workspace cleanup, causing done events to be lost when the user subsequently rebuilds the merge externally (addressed by **WP02** via FR-019/FR-020 because the fix lives in the same function as WP02's strategy wiring; WP05 verifies and closes #416). Any additional gaps surfaced by the verification report SHALL be either fixed in this mission or recorded as follow-ups in the Mission Close Ledger.
- The FSEvents debounce question raised by #416 ("is `_worktree_removal_delay()`'s 5-second wait enough?") is **explicitly carved out** of WP05's scope. It is filed as a follow-up rather than expanded into this mission, because empirical sweeping of the macOS CI runner is a separate workstream from the deterministic event-commit fix. WP05 records this carve-out in the Mission Close Ledger.
- The tracked-issues table is the authoritative scope marker for "the workflow-stabilization track" within this mission. No external label or umbrella issue is consulted.
- All work happens against `main` as the planning, implementation, and merge target.

---

## Dependencies

- Existing `spec-kitty merge` and `spec-kitty implement` subsystems on current main (WP02, WP05).
- Existing `.github/workflows/ci-quality.yml` and the critical-path diff-coverage instrumentation (WP03).
- Existing release tag/PR workflow that the release-prep payload feeds into (WP04).
- Existing implement-recovery and merge-resume code paths and their tests (WP05).
- pytest, mypy, ruff, ruamel.yaml, typer, rich (charter-aligned tool stack).

---

## Out of Scope (Reiterated for Reviewers)

- Issues #412, #414, #442, #393, #447, #443 — already implemented on main.
- Issue #419 — cross-repo contract/cutover work.
- Issue #410 (umbrella for workflow-resilience tracking) is reviewed but **not closed** by this mission. After #416 closes, the umbrella should be re-evaluated separately. It remains open as the long-term workflow-resilience tracking issue.
- Doctrine and agent-profile architecture work.
- Typed dashboard contract migration.
- Any new feature work unrelated to merge/release/recovery stabilization.
- GitHub-API-based branch-protection detection.
- JavaScript/TypeScript test surface for the stale-assertion analyzer.
- Full PyPI propagation verification in release prep.
- FSEvents debounce / `_worktree_removal_delay()` empirical timing for #416 — filed as a follow-up rather than expanded into this mission.
- The dirty-classifier `git check-ignore` consultation gap (`src/specify_cli/cli/commands/agent/tasks.py` flags `.gitignore`-d snapshot files as blocking owned-files) — workaround exists (`--force` or restoring the gitignored snapshot file). Filed as a follow-up rather than expanded into 068's scope.
- `MergeState` runtime persistence under `.kittify/runtime/merge/<mission_id>/state.json` — out of scope for FR-019. That path is intentionally ephemeral runtime state, not the cause of the 067 done-events loss.

---

## Definition of Done

The mission is done when **all** of the following hold:

1. The four primary-scope issues (#454, #455, #456, #457) are either closed with merge-commit evidence or, in the case of #455, closed with a documented validation showing current main already satisfies the intent.
2. The two verification-scope issues (#415, #416) are either closed with verification evidence or have any residual gap fixed in this mission and a regression test added.
3. No tracked issue is carried forward without an explicit, reasoned close-or-narrow decision recorded in the mission close ledger.
4. Every issue in the Tracked GitHub Issues table has a final disposition recorded in `kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md` (`closed_with_evidence` or `narrowed_to_followup` with a follow-up issue link). This is mechanically checkable: the ledger SHALL contain a row for every issue listed in the tracked-issues table.
5. All charter-required gates pass: pytest, `mypy --strict`, ruff, and the critical-path diff coverage threshold.
6. Mission artifacts (spec, plan, tasks, WP files) are merged into `main` and the mission is accepted.
