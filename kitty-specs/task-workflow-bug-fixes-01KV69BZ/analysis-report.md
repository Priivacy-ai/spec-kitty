---
schema: analysis-findings/v1
findings:
  - id: A1
    severity: critical
    category: charter
    summary: "Task ordering in WP01 and WP02 violates C-011 ATDD-First Discipline — implementation subtasks precede test subtasks in both WPs."
  - id: C1
    severity: high
    category: coverage
    summary: "T005 test assertion ('create_intent' in error_text) passes against the pre-fix message; it does not fail before WP02's fix is applied, making it a non-red-first regression guard."
  - id: C2
    severity: medium
    category: coverage
    summary: "C-003 (both fixes independently revertable) has no commit-structure task or note in either WP prompt."
  - id: I1
    severity: low
    category: inconsistency
    summary: "plan.md Project Structure names test files differently than WP prompts (test_map_requirements.py vs test_map_requirements_spec_path.py; test_ownership_validation.py vs test_validation.py)."
  - id: I2
    severity: low
    category: inconsistency
    summary: "FR-004 and FR-005 embed regression-test obligations as functional requirements rather than deriving tests from FRs."
counts: {critical: 1, high: 1, medium: 1, low: 2, info: 0}
verdict_hint: blocked
---

## Specification Analysis Report

Mission: `task-workflow-bug-fixes-01KV69BZ`
Branch: `fix/task-workflow-bug-fixes`
Analyzed: 2026-06-15

> **Note**: `spec-kitty agent mission record-analysis` failed with "Required artifact missing: ...coord/.../spec.md" — the same coord-worktree topology bug this mission exists to fix (bug #1981). Report committed directly via `safe-commit` as a workaround.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Charter | CRITICAL | WP01 (T001→T002→T003), WP02 (T004→T005) | Charter C-011 (binding) requires a failing ATDD test committed before any implementation commit. Both WPs list implementation subtasks before tests — T003 follows T001/T002 in WP01; T005 follows T004 in WP02. Reviewer cannot verify red→green as required. | Reorder subtasks: T003 first in WP01 (write failing test for primary-path contract before modifying tasks.py), T005 first in WP02. Add "commit this test first, before any implementation" note to each test subtask. |
| C1 | Coverage | HIGH | WP02 T005, `tests/specify_cli/ownership/test_validation.py` | The current (pre-fix) error message already contains the substring `'create_intent'` via "add it to 'create_intent' in the WP frontmatter." T005's assertion `"create_intent" in error_text` would therefore PASS before T004's fix is applied — it is not a failing-first ATDD guard. The test would pass the entire test run even if T004 is skipped. | Change T005 assertion to check for YAML-syntax presence (e.g., `"create_intent:\n    -" in error_text`). This string is absent in the pre-fix message and present after the fix. |
| C2 | Coverage | MEDIUM | WP01 Definition of Done, WP02 Definition of Done, C-003 | C-003 requires both fixes to be independently revertable. Neither WP prompt includes a task or note instructing the implementer to commit each fix in a separate commit. A single commit landing both changes makes revert non-atomic. | Add a "Commit Discipline" note to each WP's Definition of Done: "Commit this WP's changes as a standalone commit (separate from WP02/WP01 changes) to satisfy C-003 independent-revert requirement." |
| I1 | Inconsistency | LOW | plan.md Project Structure section | plan.md shows `test_map_requirements.py` and `test_ownership_validation.py`; WP01 frontmatter and body correctly say `test_map_requirements_spec_path.py`; WP02 correctly says `test_validation.py`. Drift between the sketch in plan.md and the authoritative WP prompts. | Update plan.md Project Structure to match WP filenames. No implementation impact since WPs are authoritative. |
| I2 | Inconsistency | LOW | spec.md FR-004, FR-005 | FR-004 and FR-005 are regression-test obligations listed as functional requirements. Conventionally, tests are derived from FRs, not stated as FRs. No execution impact but creates ambiguity when tracing test coverage back to requirements. | Optional: re-classify FR-004 and FR-005 as NFRs (test obligations) or notes under FR-003/FR-001 respectively. No blocking action needed. |

---

## Coverage Summary Table

| Requirement | Has Task? | Task IDs | Notes |
|-------------|-----------|----------|-------|
| FR-001 (map-requirements reads spec.md from primary checkout) | ✓ | T001, T002 | IC-01 — covered |
| FR-002 (WP file reads remain topology-aware) | ✓ | T002 | Implicit: feature_dir unchanged downstream |
| FR-003 (YAML fragment in zero-match error) | ✓ | T004 | IC-02 — covered |
| FR-004 (regression test: error contains path + create_intent key) | ✓ | T005 | Covered structurally; assertion too weak (see C1) |
| FR-005 (regression test: map-requirements succeeds with coord worktree) | ✓ | T003 | Covered structurally; T003 tests the resolver function, not map_requirements — passes pre-fix |
| NFR-001 (no existing tests regress) | ✓ | T001–T005 | Definition of Done in both WPs |
| NFR-002 (no subprocess calls in spec.md fix) | ✓ | T001, T002 | Pure-path operations; verified in plan/research |
| NFR-003 (error message ≤300 chars) | ✓ | T004 | Length verified in T004 instructions (~180 chars typical) |
| C-001 (sanctioned resolver only) | ✓ | T001 | primary_feature_dir_for_mission from feature_dir_resolver.py; architectural test gate enforces |
| C-002 (exact field name create_intent) | ✓ | T004 | Pattern variable used verbatim in YAML fragment |
| C-003 (independently revertable) | Partial | — | WPs in separate lanes (good) but no commit-structure guidance |

---

## Charter Alignment Issues

| Principle | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ | ✓ PASS | All changed modules already Python 3.11+ |
| mypy --strict | ✓ PASS | Swapping one Path-returning function for another with identical signature |
| pytest 90%+ new-code coverage | ✓ PASS | Two new test functions, each directly exercising the new behavior |
| Run targeted test surface | ✓ PASS | WP validation sections scope to specific test files/dirs |
| No direct push to origin/main | ✓ PASS | Branch strategy correct: fix/task-workflow-bug-fixes → PR |
| Terminology Canon (Mission not Feature) | ✓ PASS | No user-facing strings introduce new "feature" terminology |
| **ATDD-First Discipline (C-011, binding)** | ✗ **FAIL** | Both WPs order implementation before tests — see A1 CRITICAL |
| Complexity ceiling ≤15 | ✓ PASS | One-line changes; complexity unchanged |
| No noqa / type: ignore suppression | ✓ PASS | Not introduced |

---

## Unmapped Tasks

None — all subtasks (T001–T005) map to at least one FR/NFR/Constraint.

---

## Metrics

- **Total Functional Requirements**: 5 (FR-001 through FR-005)
- **Total Non-Functional Requirements**: 3 (NFR-001 through NFR-003)
- **Total Constraints**: 3 (C-001 through C-003)
- **Total Tasks**: 5 (T001–T005 across 2 WPs)
- **Coverage %**: 100% (all FRs have ≥1 associated task)
- **Ambiguity Count**: 0
- **Duplication Count**: 0
- **Critical Issues Count**: 1 (A1 — ATDD ordering)
- **High Issues Count**: 1 (C1 — weak test assertion)

---

## Next Actions

**BLOCKED** — two issues must be resolved before `/spec-kitty.implement`:

1. **A1 (CRITICAL)** — Reorder subtasks in WP01 and WP02 so that the test task comes first. Add an explicit "commit test before implementation" instruction to each test subtask's body. This brings the WPs into compliance with C-011.

2. **C1 (HIGH)** — Strengthen T005's assertion in WP02. Change `"create_intent" in error_text` to `"create_intent:\n" in error_text` (or the exact YAML list syntax form). The current assertion passes without the fix being applied.

**Advisory (do not block):**

3. **C2 (MEDIUM)** — Add commit-discipline notes to both WP Definitions of Done to satisfy C-003.

4. **I1 (LOW)** — Update plan.md Project Structure test file names to match WP prompts.

5. **I2 (LOW)** — Optionally reclassify FR-004/FR-005 as NFRs.
