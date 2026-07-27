---
schema: analysis-findings/v1
findings:
  - id: A1
    severity: medium
    category: coverage
    summary: "NFR-003 (≥90% branch coverage on new code) has no enforcement task — no WP includes a coverage measurement step."
  - id: A2
    severity: medium
    category: underspecification
    summary: "Success Criterion 3 (zero coordinator-file conflicts in parallel lanes) is untestable by any single WP; T019 Directive-030 test is a structural proxy only."
  - id: A3
    severity: low
    category: inconsistency
    summary: "T002 (docstring addition to _human_slug_for_mid8_branch) has no spec-level FR anchor; FR-002 specifies only a test."
  - id: A4
    severity: low
    category: inconsistency
    summary: "Plan.md IC-05 Part A fix sketch ('fallback to coord worktree') and WP05 T020 guidance ('investigate resolve_feature_dir_for_slug first') propose slightly different approaches; WP file is authoritative but minor drift."
  - id: A5
    severity: low
    category: inconsistency
    summary: "Plan.md charter check table uses mixed directive notation (DIRECTIVE_003 vs DIR-005 vs DIR-010/011); should be consistent."
  - id: A6
    severity: low
    category: inconsistency
    summary: "Coord worktree plan.md predates IC-05 expansion; WP05 implementers navigating via the CLI-resolved coord path see stale 'Four targeted fixes' context. WP05 prompt is self-contained but drift is present."
counts: {critical: 0, high: 0, medium: 2, low: 4, info: 0}
verdict_hint: ready
---

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Coverage | MEDIUM | spec.md NFR-003; WP03–WP04 DoDs | NFR-003 requires ≥ 90% branch coverage on new code but no WP includes a `pytest --cov` measurement step. Implementers may ship covered-by-tests code that falls below the threshold without noticing. | Add a coverage measurement command to the integration check in WP03 and WP04: `pytest tests/specify_cli/tool_surface/ --cov=src/specify_cli/tool_surface/providers --cov-report=term-missing --cov-fail-under=90`. Update each WP DoD with "coverage report shows ≥ 90% on new files." |
| A2 | Underspecification | MEDIUM | spec.md Success Criteria #3; tasks.md WP04/T019 | "Two contributors merge in parallel with zero coordinator-file conflicts" is not mechanically testable by any task. T019 asserts the Directive-030 structural invariant (no central literal lists in service.py) but does not simulate or prove the merge-conflict outcome. | Add a note to T019 clarifying that the test is a structural proxy for the zero-conflict claim. Remove "zero conflicts" from success criteria or rephrase as "the coordinator file has no provider-specific literals that would produce merge conflicts." A structural test plus the self-registration design is the actual guarantee. |
| A3 | Inconsistency | LOW | tasks.md T002; spec.md FR-002 | T002 ("Add docstring invariant to _human_slug_for_mid8_branch()") has no spec-level FR anchor. FR-002 specifies only "a test must be added." The docstring is plan-derived scope not declared in the spec. | Either add a note to FR-002 mentioning the docstring intent, or acknowledge T002 as plan-level refinement in the WP01 context section. No structural change required — the scope is small and beneficial. |
| A4 | Inconsistency | LOW | plan.md IC-05 Part A; WP05 T020 | Plan.md IC-05 Part A describes the fix as "look for the mission's coord worktree and resolve feature_dir from it." WP05 T020 requires investigation-first and proposes `resolve_feature_dir_for_slug` (coord-aware already) as the likely cleaner fix. Both are valid approaches; the WP file is authoritative for implementation. | Accept the WP05 guidance as authoritative. The plan.md sketch is exploratory; implementers should follow WP05's investigation-first instruction. No file change needed, but plan.md could add a note: "see WP05 T020 for confirmed fix path." |
| A5 | Inconsistency | LOW | plan.md Charter Check table | Mixed directive notation: `DIRECTIVE_003`, `DIR-005`, `DIR-006`, `DIR-010/011`. Makes it harder to look up the actual directives. | Standardize to one notation (e.g., `DIRECTIVE_NNN`) or add a parenthetical name to each entry so readers can identify the directive without knowing the numbering convention. |
| A6 | Inconsistency | LOW | coord worktree plan.md | The coord worktree's `plan.md` (the file returned by `check-prerequisites` as the canonical plan path) predates the mission expansion that added IC-05. It shows "Four targeted fixes across three subsystems" and has no IC-05 section. WP05 implementers who navigate to plan.md via the coord worktree will see incomplete planning context. | The WP05 prompt file is self-contained and does not depend on plan.md, so this is mitigated. To fully close the gap, cherry-pick or merge the IC-05 planning commits from the planning branch into the coord worktree's lane branch, or note in WP05 that plan.md in the coord worktree is stale and the primary checkout's plan.md is authoritative. |

---

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001: Remove xfail | ✓ | T001 | WP01 |
| FR-002: Pathological mid8 test | ✓ | T003 (+ T002 extra scope) | WP01; T002 is undeclared but beneficial |
| FR-003: Singular kind subdir | ✓ | T005, T006 | WP02 |
| FR-004: Remove stale sidecars | ✓ | T004 | WP02 |
| FR-005: built_in_only early-exit | ✓ | T007, T008 | WP02 |
| FR-006: One-module provider add | ✓ | T009–T011, T012–T018 | WP03+WP04 |
| FR-007: Provider self-declares registration | ✓ | T012–T018 | WP04 |
| FR-008: Registry supports multi-def, synthetic-key, multi-token | ✓ | T009, T016, T017 | WP03+WP04 |
| FR-009: Coordinator derives all config from registry + conformance test | ✓ | T011, T019 | WP03+WP04 |
| FR-010: Deterministic ordering | ✓ | T009 (order field) | WP03 |
| FR-011: map-requirements resolves spec.md from main checkout | ✓ | T020 | WP05 |
| FR-012: finalize-tasks error includes create_intent hint | ✓ | T021 | WP05 |
| NFR-001: mypy --strict | ✓ (DoDs) | All WPs | Referenced in each WP DoD |
| NFR-002: ruff zero issues | ✓ (DoDs) | All WPs | Referenced in each WP DoD |
| NFR-003: ≥90% branch coverage | ⚠ partial | T003, T008, T019, T020 | No coverage measurement step (A1) |
| NFR-004: No behavioral regressions | ✓ | T011, T012–T018 | Existing test suite regression check in each WP |
| NFR-005: Existing charter validate unchanged | ✓ | T008 (negative test) | WP02 integration check runs full charter suite |
| C-001: Explicit enumeration, not pkgutil | ✓ | T010 | _discovery.py explicit tuple |
| C-002: Full provider contract supported | ✓ | T009, T016, T017 | Frozen dataclass, synthetic_key, 3-def tuple |
| C-003: Gitignore whitelist unchanged | ✓ | T005, T006 | Singular dirs; no gitignore edit |
| C-004: No new CLI surfaces | ✓ | N/A | Satisfied by omission |

---

**Charter Alignment Issues:**

No charter MUST violations found. Minor notation inconsistency in charter check table (A5).

The charter requires "90%+ test coverage for new code" — this is NFR-003. The mission correctly specifies NFR-003 but lacks an enforcement task (A1).

---

**Unmapped Tasks:**

T002 has no direct FR anchor (FR-002 specifies a test; T002 adds a docstring). This is LOW-severity extra scope with clear implementation rationale. All other tasks map to at least one FR.

---

**Metrics:**

- Total Functional Requirements: 12
- Total Non-Functional Requirements: 5
- Total Constraints: 4
- Total Tasks: 21 (T001–T021)
- Total Work Packages: 5 (WP01–WP05)
- Coverage % (FRs with ≥1 task): 100% (12/12)
- NFR Coverage % (with ≥1 task or DoD reference): 100% (5/5); NFR-003 has partial coverage (A1)
- Ambiguity Count: 0 (no vague adjectives without thresholds; NFR-003 has measurable threshold)
- Duplication Count: 0
- Critical Issues Count: 0
- High Issues Count: 0
- Medium Issues Count: 2 (A1, A2)
- Low Issues Count: 4 (A3–A6)

---

**Next Actions:**

The mission is **READY for implementation**. No HIGH or CRITICAL findings block implementation.

Recommended (but optional) pre-implementation improvements:

1. **A1** — Add coverage measurement step to WP03 and WP04 integration checks. One-line addition to each integration check block.
2. **A2** — Rephrase Success Criterion 3 to match what T019 actually proves (structural invariant, not multi-lane simulation).
3. **A6** — No immediate action needed; WP05 prompt is self-contained. Optionally note in WP05's context that the coord worktree's plan.md is stale.

A4 and A5 can be deferred to post-implementation polish.
