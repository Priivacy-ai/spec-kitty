# Specification Analysis Report
## Mission: merge-preflight-remote-state-boundary-separation-01KTBE5M
**Generated**: 2026-06-05 | **Scope**: spec.md + plan.md + tasks.md + charter

---

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| D1 | Charter Alignment | CRITICAL | tasks.md WP01–WP04; charter C-011 | Charter C-011 (ATDD-First, binding) requires every WP to have a failing test committed BEFORE any implementation commit. No WP prompt mentions this rule. WP03 (tests) is sequenced AFTER WP02 (implementation), which is the inverse of ATDD-first. | Add an "ATDD Stub" phase before WP02: a minimal failing test that pins FR-002 (local-ahead proceeds) and FR-010 (#1706 regression) must be committed to the lane branch before WP02's first implementation commit. Revise WP01/WP02 prompts to reference the ATDD-first requirement. |
| D2 | Inconsistency | HIGH | tasks/WP01-publish-layer-module.md T003; tasks/WP02-domain-cleanup-and-call-site.md T006; owned_files | WP01's `owned_files` no longer includes `preflight.py` (removed to resolve finalize-tasks overlap error), but T003 in the WP01 prompt explicitly instructs the agent to remove functions from `preflight.py`. WP02 T006 also says to strip the same code. Both WPs instruct agents to modify a file only WP02 owns, creating confusion and potential double-removal or conflict between lane implementations. | Option A: Add `preflight.py` back to WP01's `owned_files` and remove T006 from WP02 (consolidate all `preflight.py` work in WP01). Option B: Update T003 in WP01 to clarify it should only ADD to `push_preflight.py` and leave removal of source functions to WP02 T006 exclusively. Option B is lower-risk. |
| D3 | Inconsistency | HIGH | data-model.md "behind" row; research.md push-safety matrix; tasks/WP03-test-coverage.md T010 matrix | The `"behind"` origin state is described inconsistently. `data-model.md` and `research.md` both specify a warning should be emitted when push is requested and local is behind origin. `WP03`'s test matrix only says "proceeds (git handles rejection)" with no mention of testing a warning. No WP is tasked with implementing the `behind`-state warning. | Either: (a) accept that `"behind"` emits no warning (update data-model.md to remove "warn only" language, confirm in spec Assumption 2 that warning is not required), or (b) add a subtask to WP02 to emit a non-blocking warning when push=True and state="behind", and add a corresponding test assertion to WP03 T010. Decision needed before implementation starts. |
| C1 | Coverage Gap | MEDIUM | NFR-001; all WPs | NFR-001 requires push-gated fetch latency ≤ 3 seconds on a standard connection. No WP contains a task, test, or validation to measure or assert this threshold. The NFR is fully unmapped. | If latency is a real concern (push runs in CI or slow networks), add a micro-benchmark or document that it is validated manually/observationally. If it's not testable, downgrade NFR-001 to an assumption in spec.md and remove it from the NFR table. At minimum, add a note to WP03's Definition of Done acknowledging NFR-001 as out-of-test-suite scope. |
| C2 | Coverage Gap | MEDIUM | FR-004; tasks/WP03-test-coverage.md | FR-004 requires "local integration results shall be preserved" when push is blocked by diverged state. WP03 T010 tests that `push=True + diverged` is blocked (Exit 1), but no assertion verifies that local lane merges completed successfully before the block. A regression could block push AND discard local merge results; the tests would still pass. | Add an explicit assertion in the T010 diverged-block test case: check that local branch `main` has the expected commits (the merged WP lanes) before the push block fires. One additional `assert_branch_contains(merged_commit)` call is sufficient. |
| C3 | Underspecification | MEDIUM | tasks/WP01-WP04 — "Branch Strategy" / "To start" blocks | Every WP prompt's "To start" command is `spec-kitty agent action implement WP0X --agent claude` with no `--mission` flag. In a multi-mission repository (this one has multiple missions), this will fail or resolve to the wrong mission per the resolver's documented behavior. | Update all four WP prompts to include `--mission merge-preflight-remote-state-boundary-separation-01KTBE5M` in the "To start" command. Example: `spec-kitty agent action implement WP01 --agent claude --mission merge-preflight-remote-state-boundary-separation-01KTBE5M`. |
| I1 | Inconsistency | MEDIUM | tasks.md WP03 "Success criteria"; tasks/WP03-test-coverage.md T010 matrix | tasks.md WP03 success criteria says "New parametrized tests cover all **six** origin states × push/no-push combinations." The T010 test matrix in WP03-test-coverage.md shows **five** states (`in_sync`, `ahead`, `behind`, `diverged`, `no_tracking_branch`). The sixth state (`missing_local_branch`) from the `TargetBranchSyncState` literal is present in data-model.md but absent from the test plan. | Decide whether `missing_local_branch` is testable and meaningful for the push-safety matrix. If yes, add it to the T010 matrix. If no, correct the success criteria count to "five" and add a note that `missing_local_branch` is a degenerate internal state not reached via the normal merge flow. |
| A1 | Ambiguity | MEDIUM | NFR-001 | "≤ 3 seconds on a standard network connection" is unmeasurable without defining "standard network connection" (bandwidth, latency, geographic region). This is a textbook unmeasurable NFR. | Add a footnote: "Standard network connection = LAN or broadband with round-trip latency ≤ 100ms to the Git remote." Or convert to: "Fetch-and-inspect round trip must add no more than one network RTT of latency, as measured by comparing wall-clock time of `git fetch` + `rev-list` vs. equivalent no-fetch local-merge." |
| A2 | Ambiguity | LOW | spec.md FR-003 | "fires only after all local lane integrations complete successfully, **immediately before** the push attempt" — "immediately before" is slightly ambiguous about whether the check could be placed inside the push helper or outside it in the orchestrator. Acceptable given research.md specifies `merge.py:1508`. | Non-actionable for implementation. No change needed given research.md resolves this. Mark informational. |
| I2 | Inconsistency | LOW | spec.md Domain Language; data-model.md module name | The canonical domain language section (spec.md) names the concept "push-safety check" but the module implementing it is named `push_preflight.py`. No canonical entry for "push_preflight" or "push-preflight" exists in the domain language table. | Add an entry to the Domain Language table: `push_preflight module | The publish-layer Python module implementing push-safety checks (push_preflight.py). | "push safety module", "push check module"`. |
| I3 | Inconsistency | LOW | tasks/WP03-test-coverage.md T010; tasks.md WP03 success criteria | WP03 success criteria in tasks.md says "`pytest tests/merge/test_target_branch_preflight.py -v` exits 0" but WP03 also creates a new file `tests/merge/test_push_preflight.py`. The success criteria should include running the new file too. | Update WP03 success criteria and Definition of Done to include `pytest tests/merge/ -v` (not just the single original file), covering both the updated and new test files. |
| A3 | Underspecification | LOW | spec.md Assumption 3; tasks/WP03-test-coverage.md Risks | Assumption 3 states test fixtures for a realistic #1706 scenario are assumed available. WP03 Risks mentions this and provides a mock fallback. However, no WP is assigned to discover/create the fixture setup if it doesn't exist, leaving this as silent risk. | Add to WP03 Definition of Done: "If no git-worktree-based fixture exists in the test suite, document the mock-boundary choice in a test comment and open a follow-up issue for fixture creation." |

---

## Coverage Summary Table

| Requirement | Has Task? | Task IDs | Notes |
|-------------|-----------|----------|-------|
| FR-001 | ✅ | T002, T003, T004, T007 | |
| FR-002 | ✅ | T003, T004, T007, T009 | |
| FR-003 | ✅ | T004, T007 | |
| FR-004 | ⚠️ | T007, T010 | No explicit "local results preserved" assertion — see C2 |
| FR-005 | ✅ | T002, T005 | |
| FR-006 | ✅ | T001, T002, T003 | |
| FR-007 | ✅ | T008 | |
| FR-008 | ✅ | T008 | |
| FR-009 | ✅ | T009 | |
| FR-010 | ✅ | T011 | |
| FR-011 | ✅ | T012 | |
| NFR-001 | ❌ | — | Zero task coverage — see C1 |
| NFR-002 | ✅ | T002, T005, T006, T007, T008 | mypy --strict in WP01/WP02 definitions of done |
| NFR-003 | ✅ | T009, T010, T011 | WP03 target ≥90% |
| NFR-004 | ✅ | T008 | |
| NFR-005 | ✅ | T008 | |

---

## Charter Alignment Issues

### CRITICAL: C-011 ATDD-First Discipline violated

The charter (C-011, binding) requires: *"The WP cannot start coding until at least one failing-first ATDD test exists that pins the user-observable behaviour the WP delivers. The ATDD test is committed as a separate commit (often the first commit of the lane) BEFORE any implementation commits."*

**Current task structure**: WP01 (create module) → WP02 (wire call site + state) → WP03 (write tests)

**Required structure under C-011**: failing ATDD tests committed first → WP01/WP02 implementation turns them green.

**Affected WPs**: WP01, WP02 (both are implementation WPs that must be preceded by a failing ATDD test). WP03 is the formal test WP, but key behavioral assertions (FR-002, FR-010) should also exist as stub ATDD tests before WP01/WP02 begin.

**Minimum remediation**: Add a T000 (ATDD stub) subtask, either in WP01's frontmatter or as a new WP00, that commits at least one failing test (`test_local_merge_proceeds_when_ahead` and `test_issue_1706_regression`) before any implementation work begins.

---

## Unmapped Tasks

All tasks (T001–T013) are mapped to at least one functional or non-functional requirement.

No orphaned tasks found.

---

## Metrics

| Metric | Value |
|--------|-------|
| Total Functional Requirements | 11 |
| Total Non-Functional Requirements | 5 |
| Total Constraints | 5 |
| Total Tasks | 13 |
| Total Work Packages | 4 |
| FR Coverage (≥1 task) | 11/11 (100%) |
| NFR Coverage (≥1 task) | 4/5 (80%) — NFR-001 uncovered |
| Ambiguity Count | 3 |
| Inconsistency Count | 4 |
| Coverage Gap Count | 3 |
| Charter Violation Count | 1 (CRITICAL) |
| CRITICAL Issues | 1 (D1 — ATDD-First) |
| HIGH Issues | 2 (D2, D3) |
| MEDIUM Issues | 5 (C1, C2, C3, I1, A1) |
| LOW Issues | 3 (A2, I2, I3) |

---

## Next Actions

### Before `/implement`

1. **[CRITICAL] Resolve D1 — ATDD-First**: Add ATDD stub tasks or a WP00 that commits at least two failing tests (`test_local_merge_proceeds_when_ahead_no_push` and `test_issue_1706_regression`) before WP01/WP02 begin implementing. The charter is explicit: the test must be RED on `planning_base_branch` and GREEN on the WP's final commit. This requires editing `tasks.md` and adding a T000 entry, plus updating WP01 or creating WP00.

2. **[HIGH] Resolve D2 — WP01/WP02 preflight.py ownership conflict**: Decide who owns `preflight.py` for the removal step in T003. The safest fix is to update T003's instruction text in `WP01-publish-layer-module.md` to clarify it only ADDS to `push_preflight.py` and does NOT delete from `preflight.py` — leaving that entirely to WP02 T006.

3. **[HIGH] Resolve D3 — `"behind"` warning behavior**: Make an explicit decision: does the push-requested + behind-state path emit a warning? If yes, add a task. If no, align data-model.md to say "no warning emitted; git rejection is sufficient feedback."

### Safe to Proceed With

Issues C1, C2, C3, I1, A1 are LOW-MEDIUM and can be addressed during implementation without blocking:

- **C3**: Fix `--mission` flag in WP prompts — quick edit, do before handing off to implementing agents.
- **I1**: Clarify "five vs. six" state count in WP03 — update WP03 success criteria to be accurate.
- **I3**: Add `tests/merge/` to WP03's pytest command in Definition of Done.
- **C2**: Add "local results preserved" assertion to T010 — note in WP03 implementer review.

### Suggested Commands

```bash
# Edit WP01 prompt to clarify T003 scope (D2):
# Update T003's "After moving" step to say: "Do NOT delete from preflight.py;
# leave deletion to WP02 T006."

# Edit WP01–WP04 prompts to add --mission to "To start" commands (C3):
# s/--agent claude/--agent claude --mission merge-preflight-remote-state-boundary-separation-01KTBE5M/

# Add ATDD-first note to WP01 and WP02 prompts (D1):
# Add section: "## ATDD Prerequisite" instructing agent to first run the ATDD
# failing tests from the planning_base_branch before writing implementation code.
```
