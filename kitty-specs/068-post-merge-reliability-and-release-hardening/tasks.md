# Tasks: Post-Merge Reliability And Release Hardening

**Mission**: 068-post-merge-reliability-and-release-hardening
**Branch**: `main` (planning, base, and merge target — all `main`)
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Generated**: 2026-04-07

---

## Branch Strategy

- **Current branch at workflow start**: `main`
- **Planning/base branch for this mission**: `main`
- **Final merge target for completed changes**: `main`
- **Branch matches target**: ✅ true

Per `spec-kitty agent context resolve`: *"Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main."*

Execution worktrees are allocated per computed lane from `lanes.json` after `finalize-tasks` runs. Agents working a WP MUST enter the workspace path printed by `spec-kitty implement WP##`, not reconstruct paths manually.

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `src/specify_cli/post_merge/` package with `__init__.py` and `stale_assertions.py` skeleton (dataclasses + module docstring) | WP01 | |
| T002 | Implement source-side AST extraction: parse changed Python files from `git diff base..head`, walk ASTs, collect changed function/class names and changed string-literal `Constant` values | WP01 | |
| T003 | Implement test-side AST scan: walk every test file from `git ls-files 'tests/**/*.py'`, parse with `ast`, find references to changed identifiers in assertion-bearing positions (`Assert`, `Compare`, `Call(func=Attribute(attr='assert*'))`) | WP01 | |
| T004 | Implement `run_check(base_ref, head_ref, repo_root) -> StaleAssertionReport` orchestration: call source extractor, call test scanner, assign confidence (`high`/`medium`/`low`), populate `elapsed_seconds`/`files_scanned`/`findings_per_100_loc` | WP01 | |
| T005 | Create `src/specify_cli/cli/commands/agent/tests.py` typer subapp with `stale-check --base --head [--json]` command; register the new subapp in `agent/__init__.py` | WP01 | |
| T006 | Author test suite at `tests/post_merge/test_stale_assertions.py` and `tests/cli/commands/agent/test_tests_stale_check.py` covering FR-001/002/003/004 worked examples, NFR-001 wall-clock benchmark, NFR-002 FP-ceiling benchmark, FR-022 fallback path | WP01 | |
| T007 | Add `--json` output mode to the CLI subcommand using `dataclasses.asdict` so downstream automation can consume the report; verify NFR-005 (no network) by mocking `subprocess` calls | WP01 | |
| T008 | Add `MergeStrategy` enum and `MergeConfig` dataclass + `load_merge_config(repo_root) -> MergeConfig` accessor in new file `src/specify_cli/merge/config.py`; extend `.kittify/config.yaml` with the `merge.strategy` schema; raise startup error on invalid value | WP02 | |
| T009 | Wire `--strategy` CLI flag through `cli/commands/merge.py merge()` into `_run_lane_based_merge`: resolve from CLI flag → config key → squash default; pass resolved strategy down into `lanes/merge.py` | WP02 | |
| T010 | Modify `src/specify_cli/lanes/merge.py` to honor the strategy parameter for the **mission→target** step (squash/rebase/merge); preserve existing merge-commit semantics for the **lane→mission** step | WP02 | |
| T011 | Add `LINEAR_HISTORY_REJECTION_TOKENS` tuple, `_is_linear_history_rejection(stderr)` parser, and `_emit_remediation_hint(console)` helper to `cli/commands/merge.py`; wire the parser into the push failure path so rejected pushes trigger the hint (fail-open on unknown messages) | WP02 | |
| T012 | Insert `safe_commit` call in `_run_lane_based_merge` immediately after the `_mark_wp_merged_done` loop and before any worktree-removal step (FR-019); commit `status.events.jsonl` and `status.json` for the mission feature directory using the existing `safe_commit` helper from `specify_cli.git` | WP02 | |
| T013 | Add `from specify_cli.post_merge.stale_assertions import run_check` to `cli/commands/merge.py` and call `run_check(merge_base_sha, "HEAD", repo_root)` after the safe_commit step; render the resulting findings as part of the merge summary block printed to console (depends on WP01) | WP02 | |
| T014 | Author test suite at `tests/cli/commands/test_merge_strategy.py` and `tests/cli/commands/test_merge_status_commit.py` covering FR-005/006/007/008/009 (strategy wiring + token list + fail-open) AND FR-019/020 (`git show HEAD:kitty-specs/<mission>/status.events.jsonl` returns `to_lane: done` for every WP after `_run_lane_based_merge` returns); add NFR-003 integration test against a `require_linear_history = true` synthetic remote | WP02 | |
| T015 | Author the WP03 validation report at `kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md`: walk current `.github/workflows/ci-quality.yml` against the policy intent of #455, populate `DiffCoverageValidationReport` fields, write the rationale (≥ 50 chars), record decision as `close_with_evidence` OR `tighten_workflow` | WP03 | | [D] |
| T016 | Execute the FR-011 path **only if** the report's decision is `close_with_evidence`: close issue #455 with a comment linking to the validation report and the line ranges that implement the enforce/advisory split; tighten CI step names in `ci-quality.yml` so they self-document (e.g., "diff-coverage (critical-path, enforced)" vs "diff-coverage (full-diff, advisory)") | WP03 | | [D] |
| T017 | Execute the FR-012 path **only if** the report's decision is `tighten_workflow`: modify `.github/workflows/ci-quality.yml` so only the intended critical-path surface produces hard failures and full-diff coverage runs as advisory; add an integration/synthetic test demonstrating that a large PR meeting critical-path coverage but missing full-diff passes; close issue #455 with a comment linking to the workflow diff and the new test | WP03 | | [D] |
| T018 | Author test suite at `tests/release/test_diff_coverage_policy.py` covering: validation report exists with all sections, exactly one decision recorded, **content gate** (`test_validation_report_close_path_populated`: rationale ≥ 50 chars + findings have "satisfied by" rationale), no workflow modification on close path, FR-012 large-PR sample on tighten path | WP03 | | [D] |
| T019 | Create `src/specify_cli/release/` package with `version.py` (`propose_version(current, channel) -> str` per the locked alpha/beta/stable + stable→stable patch rule from contracts/release_prep.md) | WP04 | |
| T020 | Implement `src/specify_cli/release/changelog.py` (`build_changelog_block(repo_root, since_tag) -> tuple[str, list[str]]`) reading from `kitty-specs/` and `git tag --list` only — no network calls per FR-014 | WP04 | |
| T021 | Implement `src/specify_cli/release/payload.py` (`build_release_prep_payload(channel, repo_root) -> ReleasePrepPayload` orchestration + `ReleasePrepPayload` dataclass per data-model.md) | WP04 | |
| T022 | Populate `src/specify_cli/cli/commands/agent/release.py` stub: replace the placeholder typer.Typer with a real `prep` subcommand accepting `--channel {alpha,beta,stable} [--json]`; render text mode via rich, JSON mode via `dataclasses.asdict`; update the stale "Deep implementation in WP05" comment | WP04 | |
| T023 | Author test suite at `tests/release/test_release_prep.py` covering FR-013/014/015 (text + JSON modes), FR-023 #457 close-comment scope-cut helper, FR-014 zero-network-calls assertion (mock `requests`/`urlopen`), `propose_version` per channel including stable→stable patch rule, NFR-004 5-second benchmark on 16-WP synthetic mission | WP04 | |
| T024 | Extend `scan_recovery_state` in `src/specify_cli/lanes/recovery.py` to consult mission status events: read `kitty-specs/<mission>/status.events.jsonl`, materialize lane snapshots, mark merged-and-deleted WPs correctly; add `RecoveryState.ready_to_start_from_target: list[str]` field; add `consult_status_events: bool = True` keyword parameter (FR-021) | WP05 | |
| T025 | Add `--base <ref>` CLI flag to `src/specify_cli/cli/commands/implement.py`: validate ref resolves locally, create lane workspace from explicit base via `git worktree add --branch <new> <path> <base>`; preserve existing auto-detect path when flag omitted (FR-021) | WP05 | |
| T026 | Author test suite at `tests/lanes/test_recovery_post_merge.py` and `tests/cli/commands/test_implement_base_flag.py` covering Scenario 7 end-to-end (synthetic test mission with placeholder upstream work packages done-and-deleted and a downstream work package starting via `--base main`), `scan_recovery_state` finds merged-deleted deps, `--base bogus-ref` fails with clear error, post-merge unblocking integration | WP05 | |
| T027 | Author the WP05 verification report at `kitty-specs/068-post-merge-reliability-and-release-hardening/wp05-verification-report.md` accounting for both pre-identified gaps (#416 status-events, #415 recovery deadlock) AND any additional shapes discovered during verification; status: `fixed_by_this_mission` or `residual_gap` per row (FR-016, FR-017) | WP05 | |
| T028 | Author the Mission Close Ledger at `kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md` with one row per issue in the Tracked GitHub Issues table (#454, #455, #456, #457, #415, #416) plus carve-out rows for the FSEvents debounce follow-up and the dirty-classifier follow-up; mechanically checkable per DoD-4 (FR-018, C-005) | WP05 | |

**Total**: 28 subtasks across 5 work packages.

---

## Phase 1 — Setup

*(No setup WPs required. The mission extends existing modules and the dev environment is already configured.)*

---

## Phase 2 — Foundational

*(No foundational WPs required. Each story WP is independently implementable except for WP02's library-import dependency on WP01.)*

---

## Phase 3 — Story WPs

### WP01 — Stale-Assertion Analyzer

**Goal**: Build the post-merge stale-assertion analyzer (#454) — a stdlib `ast`-based tool that flags test assertions likely invalidated by merged source changes. Library + CLI subcommand. Wired into the merge runner via direct library import.
**Priority**: P1 (primary scope)
**Estimated prompt size**: ~480 lines (7 subtasks × ~65 lines each)
**Independent test**: `pytest tests/post_merge tests/cli/commands/agent/test_tests_stale_check.py` exits zero with NFR-001 wall-clock and NFR-002 FP-ceiling benchmarks both green.
**Dependencies**: none

**Included subtasks**:
- [ ] T001 Create `src/specify_cli/post_merge/` package skeleton (WP01)
- [ ] T002 Implement source-side AST identifier/literal extraction (WP01)
- [ ] T003 Implement test-side AST scan in assertion-bearing positions (WP01)
- [ ] T004 Implement `run_check()` orchestration + confidence assignment (WP01)
- [ ] T005 New `agent tests` subapp + `stale-check` command + register in `agent/__init__.py` (WP01)
- [ ] T006 Test suite for FR-001/002/003/004 + NFR-001/002 + FR-022 fallback (WP01)
- [ ] T007 `--json` output mode + NFR-005 zero-network assertion (WP01)

**Implementation sketch**: Create the new `post_merge/` package, write `stale_assertions.py` top-down (dataclasses → source extractor → test scanner → orchestrator), then add the CLI shim, then the test suite, then the JSON output. Avoid all subprocess use except for `git diff` and `git ls-files` invocations needed to enumerate the diff and the test file list.

**Parallel opportunities**: The internal subtasks are mostly sequential within the WP because each layer builds on the previous. T006 (tests) can be drafted in parallel with T002/T003 if you write the test scaffolding first.

**Risks**: NFR-002's FP ceiling (≤ 5 per 100 LOC of merged change) is tight. If the AST-based heuristic exceeds it, FR-022 mandates narrowing scope (e.g., literal-string changes only). Document the narrowed scope as a new constraint row in `spec.md` before requesting review.

**Prompt file**: [tasks/WP01-stale-assertion-analyzer.md](tasks/WP01-stale-assertion-analyzer.md)

---

### WP02 — Merge Strategy + Status-Events Safe Commit

**Goal**: Wire `--strategy` end-to-end through the merge command (#456), default to squash for the mission→target step, add the push-error remediation parser, and fix the FR-019 status-events loss bug by inserting `safe_commit` after the mark-done loop (#416 known residual gap). Also wires the WP01 stale-assertion analyzer call into the merge runner.
**Priority**: P1 (primary scope, largest sequential chain)
**Estimated prompt size**: ~520 lines (7 subtasks × ~75 lines each — slightly over target because the FRs all touch the same function and need cohesive guidance)
**Independent test**: `pytest tests/cli/commands/test_merge_strategy.py tests/cli/commands/test_merge_status_commit.py` exits zero. The FR-020 regression test asserts `git show HEAD:kitty-specs/<mission>/status.events.jsonl` contains a `to_lane: done` entry for every merged WP after `_run_lane_based_merge` returns.
**Dependencies**: WP01 (T013 imports `run_check` from `specify_cli.post_merge.stale_assertions`)

**Included subtasks**:
- [ ] T008 `MergeStrategy` enum + `MergeConfig` + `load_merge_config` in `merge/config.py` + `.kittify/config.yaml` schema (WP02)
- [ ] T009 Wire `--strategy` CLI flag through to `_run_lane_based_merge` (WP02)
- [ ] T010 Honor strategy parameter in `lanes/merge.py` mission→target step; preserve lane→mission merge commits (WP02)
- [ ] T011 Push-error parser tokens + remediation hint helper + wire to push failure path (WP02)
- [ ] T012 Insert `safe_commit` between mark-done loop and worktree-removal (FR-019) (WP02)
- [ ] T013 Import + call `run_check` from WP01 in the merge runner; render findings in merge summary (WP02)
- [ ] T014 Test suite covering FR-005..FR-009, FR-019, FR-020, NFR-003 (WP02)

**Implementation sketch**: Land in dependency order. (1) `merge/config.py` first — pure dataclass file with no side effects. (2) Wire the CLI parameter and the resolution order in `cli/commands/merge.py`. (3) Push the resolved strategy down into `lanes/merge.py` and switch on it for the mission→target step. (4) Add the push-error parser helpers as private functions in `cli/commands/merge.py`. (5) Insert the `safe_commit` call at the documented insertion point. (6) Add the `run_check` import and call. (7) Tests last so they exercise the full plumbing.

**Parallel opportunities**: T008 is fully independent and can land first. T011 is independent of T009/T010 but lives in the same file so should be sequenced. T013 depends on WP01 landing, but can be drafted as a stub that imports cleanly.

**Risks**: The FR-019 fix is the most important single change in the mission. The regression test (T014) MUST use `git show HEAD:` directly — do NOT use `git reset --hard HEAD` (proves nothing per the contracts/merge_strategy.md note). Lane→mission merges MUST keep merge-commit semantics — do not collapse them under the strategy switch.

**Prompt file**: [tasks/WP02-merge-strategy-and-safe-commit.md](tasks/WP02-merge-strategy-and-safe-commit.md)

---

### WP03 — Diff-Coverage Policy Validation And Closure

**Goal**: Validate current `ci-quality.yml` against the policy intent of #455. If validation shows current main already satisfies the intent, close #455 with evidence and tighten doc/CI messages (FR-011). Otherwise, modify the workflow so only critical-path coverage hard-fails and full-diff coverage stays advisory (FR-012). Verification-first: no workflow edits before the validation report exists.
**Priority**: P1 (primary scope)
**Estimated prompt size**: ~280 lines (4 subtasks × ~70 lines each)
**Independent test**: `pytest tests/release/test_diff_coverage_policy.py` exits zero AND the validation report file exists with all required sections, exactly one decision recorded, and a non-empty rationale.
**Dependencies**: none

**Included subtasks**:
- [x] T015 Author the WP03 validation report walking current `ci-quality.yml` (WP03)
- [x] T016 FR-011 path: close #455 with evidence + tighten CI step names (only if `decision == close_with_evidence`) (WP03)
- [x] T017 FR-012 path: modify `ci-quality.yml` + add large-PR test (only if `decision == tighten_workflow`) (WP03)
- [x] T018 Test suite covering report content gate, decision recording, and conditional FR-011/FR-012 paths (WP03)

**Implementation sketch**: Read `ci-quality.yml` end-to-end first. Identify which step enforces critical-path and which emits the advisory full-diff report. Run a representative large PR (or a synthetic equivalent) through it locally. Record findings in the validation report. Decide. Execute either the FR-011 path (no workflow change, comment + step rename) OR the FR-012 path (workflow change + test + comment). Then write the test suite that validates whichever path you took.

**Parallel opportunities**: T015 must come first. T016 and T017 are mutually exclusive. T018 can be drafted in parallel with T015 (test scaffolding) but must finalize after the decision.

**Risks**: Skipping straight to "make it advisory" without the validation step is forbidden (FR-010). The content gate test (`test_validation_report_close_path_populated`) prevents shipping a vacuous report — the rationale must be ≥ 50 characters and findings must carry "satisfied by" justifications.

**Prompt file**: [tasks/WP03-diff-coverage-policy-validation.md](tasks/WP03-diff-coverage-policy-validation.md)

---

### WP04 — Release-Prep CLI

**Goal**: Populate the existing `agent/release.py` stub with a real `prep` subcommand (#457). Build the changelog draft from local `kitty-specs/` artifacts (no network), propose a version bump per channel (alpha/beta/stable with stable→stable patch rule), and emit both rich text and JSON. Document the scope-cut in the #457 close comment (automated steps vs still-manual steps).
**Priority**: P1 (primary scope)
**Estimated prompt size**: ~350 lines (5 subtasks × ~70 lines each)
**Independent test**: `pytest tests/release/test_release_prep.py` exits zero with the NFR-004 5-second benchmark green AND `spec-kitty agent release prep --channel alpha --json | jq .proposed_version` returns the expected next-version string.
**Dependencies**: none

**Included subtasks**:
- [ ] T019 Create `src/specify_cli/release/version.py` with `propose_version` per locked rules (WP04)
- [ ] T020 Implement `release/changelog.py` `build_changelog_block` reading kitty-specs/ + git tags only (WP04)
- [ ] T021 Implement `release/payload.py` `build_release_prep_payload` orchestration + `ReleasePrepPayload` dataclass (WP04)
- [ ] T022 Populate `agent/release.py` stub with `prep` subcommand (text + JSON modes); update stale comment (WP04)
- [ ] T023 Test suite covering FR-013/014/015/015a + NFR-004 benchmark + zero-network assertion (WP04)

**Implementation sketch**: Build the package bottom-up. (1) `version.py` is pure functions over version strings — start here, fully tested. (2) `changelog.py` reads filesystem + invokes `git tag --list` — testable with synthetic kitty-specs/ fixture. (3) `payload.py` orchestrates the above. (4) `agent/release.py` becomes a thin typer shim. (5) Tests lock the contract. Network mocking is essential — FR-014 forbids any GitHub API call.

**Parallel opportunities**: T019/T020/T021 are independent files and can be drafted in parallel. T022 depends on all three. T023 lands last.

**Risks**: The `agent/release.py` stub is currently a registered live subapp at `agent/__init__.py:20` — DO NOT delete the registration or move the file. Just populate the existing stub. The locked decision is to use the `release/` package split (NOT inline into `agent/release.py`) — no second-guessing at code time.

**Prompt file**: [tasks/WP04-release-prep-cli.md](tasks/WP04-release-prep-cli.md)

---

### WP05 — Recovery Extension + Verification + Mission Close Ledger

**Goal**: Fix the #415 known residual gap by extending `scan_recovery_state` to consult mission status events and adding `--base <ref>` to `spec-kitty implement` (FR-021). Author the WP05 verification report covering the two pre-identified gaps and any additional shapes (FR-016/017). Author the Mission Close Ledger with one row per tracked issue (FR-018, C-005). This is the WP that closes the workflow-stabilization track.
**Priority**: P1 (primary scope, also delivers DoD-4)
**Estimated prompt size**: ~390 lines (5 subtasks × ~78 lines each)
**Independent test**: `pytest tests/lanes/test_recovery_post_merge.py tests/cli/commands/test_implement_base_flag.py` exits zero AND `mission-close-ledger.md` contains one row for every issue in the Tracked GitHub Issues table.
**Dependencies**: none (verification can be authored against any branch state; FR-021 fix is independent of all other WPs)

**Included subtasks**:
- [ ] T024 Extend `scan_recovery_state` to consult status events; add `ready_to_start_from_target` field (WP05)
- [ ] T025 Add `--base <ref>` CLI flag to `spec-kitty implement` (WP05)
- [ ] T026 Test suite for Scenario 7 end-to-end + recovery scanner with merged-deleted deps (WP05)
- [ ] T027 Author `wp05-verification-report.md` accounting for both pre-identified gaps + any additional shapes (WP05)
- [ ] T028 Author `mission-close-ledger.md` with one row per tracked issue + carve-out rows (WP05)

**Implementation sketch**: T024 + T025 are the code changes; do them first, then T026 tests them. T027 verification report can be drafted in parallel with the code changes since the failure shapes are already documented in `spec.md` Mission 067 Failure-Mode Evidence sections. T028 ledger is filled in last because some rows need merge commit / PR links from the other WPs.

**Parallel opportunities**: T024 and T025 are independent files (`recovery.py` vs `implement.py`) and can be parallelized within the WP. T027 and T028 are markdown authoring and don't block the code changes.

**Risks**: WP05 owns the mechanically-checkable DoD-4. If any tracked issue is missing from the ledger, the mission cannot close. Use the spec's Tracked GitHub Issues table as the authoritative checklist.

**Prompt file**: [tasks/WP05-recovery-and-mission-close.md](tasks/WP05-recovery-and-mission-close.md)

---

## Phase 4 — Polish

*(No polish WPs required. Verification, documentation tightening, and ledger authorship are folded into WP03 and WP05.)*

---

## Dependency Graph

```
WP01 (no deps) ────► WP02 (uses WP01's run_check library)
WP03 (no deps)  ──► (independent)
WP04 (no deps)  ──► (independent)
WP05 (no deps)  ──► (independent)
```

The lane planner SHOULD give WP01 → WP02 the longest sequential lane (Lane A). WP03, WP04, WP05 are independent and can run in parallel lanes.

Recommended lane allocation (lane planner will compute the canonical version from `lanes.json`):
- **Lane A**: WP01 → WP02 (sequential because of run_check import dependency)
- **Lane B**: WP03 (verification-first, low-risk)
- **Lane C**: WP04 (release-prep, isolated)
- **Lane D**: WP05 (recovery + ledger, isolated)

4 parallel lanes maximum, with WP01→WP02 as the longest serial chain.

---

## MVP Scope Recommendation

**MVP = WP02 alone** (the FR-019 status-events safe_commit fix). It's the most urgent residual gap from mission 067 and stands on its own — every subsequent merge of multi-WP missions on this repo or any other consuming spec-kitty will hit the loss-of-events failure mode again until WP02 lands. Everything else in 068 can ship later if needed.

If you want a more complete MVP, **MVP = WP01 + WP02** (the analyzer + the merge fix) gives you the two highest-impact code changes in one ship.

---

## Coverage Summary (FR → WP)

| FR | Owning WP | Subtask(s) |
|---|---|---|
| FR-001 | WP01 | T001, T002, T003, T004, T006 |
| FR-002 | WP01 | T002, T003, T006 |
| FR-003 | WP01 | T004, T006 |
| FR-004 | WP01 | T005, T006, T007 |
| FR-005 | WP02 | T009 |
| FR-006 | WP02 | T009 |
| FR-007 | WP02 | T010 |
| FR-008 | WP02 | T008 |
| FR-009 | WP02 | T011 |
| FR-010 | WP03 | T015 |
| FR-011 | WP03 | T015, T016 |
| FR-012 | WP03 | T015, T017 |
| FR-013 | WP04 | T019, T021, T022 |
| FR-014 | WP04 | T020, T021, T023 |
| FR-015 | WP04 | T022, T023 |
| FR-023 | WP04 | T023 |
| FR-016 | WP05 | T027 |
| FR-017 | WP05 | T024, T025, T027 |
| FR-018 | WP05 | T028 |
| FR-019 | WP02 | T012 |
| FR-020 | WP02 | T014 |
| FR-021 | WP05 | T024, T025, T026 |
| FR-022 | WP01 | T006 |
| NFR-001 | WP01 | T006 |
| NFR-002 | WP01 | T006 |
| NFR-003 | WP02 | T014 |
| NFR-004 | WP04 | T023 |
| NFR-005 | WP01, WP02, WP04 | T007, T014, T023 |
| NFR-006 | all | (charter gate) |
