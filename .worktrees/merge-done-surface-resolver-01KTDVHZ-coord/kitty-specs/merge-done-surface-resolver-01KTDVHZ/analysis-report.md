# Specification Analysis Report

**Mission**: merge-done-surface-resolver-01KTDVHZ  
**Analyzed**: 2026-06-06  
**Artifacts**: spec.md (v1), plan.md (v1), tasks.md (4 WPs, 21 subtasks)  
**Charter**: .kittify/charter/charter.md v1.1.5

---

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Charter | CRITICAL | tasks.md WP02, WP03; charter C-011 | **ATDD-First violation**: WP02 implements the fix; WP03 adds regression tests. Charter C-011 (binding) requires a failing test committed *before* any implementation commit. Current ordering is implementation-then-tests. | Add a "write failing test first" subtask at the start of WP02 (before T009–T013), or split: WP02 writes the failing coord-branch test, WP03 implements the fix, WP04 verifies green. |
| I2 | Inconsistency | HIGH | plan.md:118–128 | plan.md WP decomposition table lists 5 WPs (WP01=Audit, WP02=Resolver, WP03=Wire, WP04=Tests, WP05=Changelog). tasks.md was restructured to 4 WPs during finalization (WP01=Resolver, WP02=Audit+Wire, WP03=Tests, WP04=Changelog). Any agent cross-referencing plan.md will find the wrong WP identities. | Update plan.md §"Work Package Decomposition" table to reflect the 4-WP structure actually in tasks.md. |
| I3 | Inconsistency | MEDIUM | spec.md C-006; tasks.md WP02/T004 | C-006 requires "committed as a **discoverable artifact** before the mission is closed." plan.md project structure shows `audit/merge-path-status-sites.md` as the artifact. WP02/T004 now produces an inline code comment in `merge.py` instead. A comment is committed but is less discoverable than a named file. | Either (a) update C-006 to read "committed inline as a code comment in `merge.py`" to match the implementation, or (b) have T004 also write a minimal `audit/` stub that echoes the comment. Option (a) is the least-effort path. |
| I4 | Inconsistency | MEDIUM | plan.md:50–55 (project structure section) | plan.md project structure diagram lists `audit/merge-path-status-sites.md` as a planned output file. This file will not be created — the audit was folded into WP02 as a code comment. | Update plan.md project structure to remove the `audit/` directory line and note that the audit finding lives as a comment in `merge.py`. |
| I5 | Coverage Gap | MEDIUM | spec.md FR-010; tasks.md | FR-010 requires "the dashboard shows `Completed: 1 (100%)`." No task tests the dashboard display. Tests verify done events are readable on the correct surface; they do not assert the dashboard aggregation or display computation. | Add a note in WP03 (or WP04) to verify progress via `spec-kitty agent tasks status` after the fix, confirming 100% display. Alternatively, document that the display is a pure derivation of the event log, making explicit dashboard testing unnecessary. |
| I6 | Coverage Gap | MEDIUM | spec.md FR-004; tasks.md WP02 | FR-004 says the fix makes the assertion independent of worktree-teardown ordering. No task explicitly tests this invariant (e.g., a test that tears down the worktree before calling `_assert_merged_wps_reached_done` and verifies it still succeeds). | Add a specific test scenario in WP03 that calls `_assert_merged_wps_reached_done` after the coordination worktree directory is removed (or simulated removed), confirming the event file was flushed before the assertion ran. |
| I7 | Charter | MEDIUM | tasks.md WP01; charter (Tracker Ticket Assignment Rule) | Charter requires: "When an agent starts implementing work from a tracker-backed issue, the agent must assign that ticket to the Human-in-Charge (HiC) before or as part of beginning the implementation." No WP instructs agents to assign GitHub issue #1726. | Add a step to WP01 (first WP to run): `unset GITHUB_TOKEN && gh issue edit 1726 --repo Priivacy-ai/spec-kitty --add-assignee @me` or equivalent HiC assignment command. |
| I8 | Ambiguity | LOW | spec.md NFR-001 | NFR-001 specifies "sub-millisecond per WP" surface resolution. No task benchmarks or measures this. The single `meta.json` read makes this almost certain by design, but it remains unvalidated. | Accept by design. Add a one-line note in WP01/T008 confirming performance acceptability (e.g., "meta.json read is O(1), satisfies NFR-001 by design — no benchmark needed"). |
| I9 | Underspecification | LOW | tasks.md WP04/T021; WP02/T004 | T021 greps for `"Merge-path status surface audit"` (case-sensitive). T004 prescribes `# Merge-path status surface audit` (same case). If the WP02 agent capitalizes differently, T021's verification grep fails silently. | In WP04/T021, use case-insensitive grep: `grep -in "merge-path status surface audit" src/specify_cli/cli/commands/merge.py` to tolerate minor capitalization variations. |
| I10 | Coverage Gap | LOW | spec.md NFR-003 | NFR-003 requires "zero additional surface-resolution paths." No test would fail if a second path-resolution approach were introduced alongside the resolver. | Accept as unverified (the spec_kitty team's own code review gate enforces this). Optionally: add a comment in the surface_resolver.py module header stating it is the sole canonical path. |

---

## Coverage Summary

| Requirement | Has Task? | Task IDs | Notes |
|-------------|-----------|----------|-------|
| FR-001 | ✅ | T005–T008 (WP01) | — |
| FR-002 | ✅ | T010 (WP02) | — |
| FR-003 | ✅ | T011 (WP02) | — |
| FR-004 | ⚠️ | T011 (WP02) implicit | No explicit ordering-independence test (I6) |
| FR-005 | ✅ | T001–T004 (WP02) | Audit is inline comment, not standalone file (I3) |
| FR-006 | ✅ | T012 (WP02) | — |
| FR-007 | ✅ | T015 (WP03) | — |
| FR-008 | ✅ | T016 (WP03) | — |
| FR-009 | ✅ | T013 (WP02) + T018 (WP03) | — |
| FR-010 | ⚠️ | T013 (WP02), T018 (WP03) | Dashboard display unverified (I5) |
| NFR-001 | ⚠️ | none explicit | Accepted by design (I8) |
| NFR-002 | ✅ | T018 (WP03) | — |
| NFR-003 | ⚠️ | T007 (WP01) implicit | No negative test (I10) |
| C-001 | ✅ | T020 (WP04) implicit | No wire-format change → full suite gate suffices |
| C-002 | ✅ | T013 (WP02) | Existing tests without coordination_branch run unchanged |
| C-003 | ✅ | T008 (WP01) | Circular import check in T008 |
| C-004 | ✅ | WP03 (stated constraint) | Enforced by WP03 implementer instructions |
| C-005 | ✅ | T001–T003 (WP02) | Scope boundary in audit steps |
| C-006 | ⚠️ | T004 (WP02) + T021 (WP04) | "Discoverable artifact" is a code comment (I3) |

---

## Charter Alignment Issues

| Issue | Charter Principle | Severity |
|-------|------------------|----------|
| ATDD-First: WP02 implements before tests exist (I1) | C-011 (ATDD-First Discipline, binding) | CRITICAL |
| Tracker ticket #1726 not assigned to HiC before WP01 starts (I7) | Tracker Ticket Assignment Rule | MEDIUM |

---

## Unmapped Tasks

All 21 tasks map to at least one requirement. No orphaned tasks found.

---

## Metrics

| Metric | Value |
|--------|-------|
| Total Functional Requirements | 10 |
| Total Non-Functional Requirements | 3 |
| Total Constraints | 6 |
| Total Tasks | 21 (4 WPs) |
| Coverage: FRs with ≥1 task | 10/10 (100%) |
| Coverage: NFRs with ≥1 task | 2/3 (67% — NFR-001 by design) |
| Coverage: Constraints with ≥1 task | 5/6 (83% — C-006 has caveat) |
| Ambiguity Count | 3 |
| Inconsistency Count | 4 |
| Critical Issues | 1 (I1: ATDD-First) |
| High Issues | 1 (I2: plan.md WP structure stale) |
| Medium Issues | 5 (I3–I7) |
| Low Issues | 3 (I8–I10) |

---

## Next Actions

### Before `/implement`

**CRITICAL — must resolve I1 (ATDD-First)**:

Charter C-011 is binding. Recommended minimal fix: add a new first subtask to WP02 that commits a failing test for the coordination-branch merge scenario before any code changes:

```
T000 (add to WP02 before T001): Write a failing pytest fixture and test that calls
_assert_merged_wps_reached_done on a coord-branch mission and asserts it passes.
Commit it as a failing (RED) test. This commit becomes the ATDD anchor.
The remaining WP02 subtasks then make it GREEN.
```

Alternatively: reorder so WP03 (currently regression tests) precedes WP02 (wire resolver), writing failing tests first.

**HIGH — should resolve I2 (plan.md stale)**:

Update `plan.md` §"Work Package Decomposition" to reflect the 4-WP final structure. This prevents implementers from being confused by the wrong WP mapping when cross-referencing.

### May proceed after I1/I2 resolution

Findings I3–I10 are refinements that improve rigor but do not block implementation. Recommended to address I3 (C-006 artifact form), I4 (plan.md project structure), I5 (FR-010 dashboard verification), and I7 (tracker ticket assignment) as quick edits — each is a sentence-level clarification.

---

## Suggested Commands

```bash
# After resolving ATDD-First in WP02:
spec-kitty agent action implement WP01 --agent claude

# Verify after WP01:
spec-kitty agent tasks status --mission merge-done-surface-resolver-01KTDVHZ
```
