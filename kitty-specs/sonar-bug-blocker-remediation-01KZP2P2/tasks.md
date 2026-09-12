# Tasks: Sonar BUG and BLOCKER Remediation

**Mission**: `sonar-bug-blocker-remediation-01KZP2P2`
**Branch**: `fix/sonar-bug-blocker-remediation`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Inventory**: [research/sonar-inventory.txt](./research/sonar-inventory.txt)

Four independent, parallelizable work packages. WP01/WP02 are the **mechanical** stream
(test-integrity + assertion restructure); WP03/WP04 are the **investigate** stream
(security + control-flow judgment). No inter-WP dependencies — file ownership is disjoint.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Fix S5863 tautological asserts — sync cluster (4 sites) | WP01 | [P] |
| T002 | Fix S5863 tautological asserts — specify_cli cluster (5 sites) | WP01 | [P] |
| T003 | Fix S5863 tautological asserts — remaining cluster (7 sites) | WP01 | [P] |
| T004 | Restructure S5779 swallowed asserts in src (4 sites) | WP02 | [P] |
| T005 | Restructure S5779 swallowed asserts in tests (10 sites) | WP02 | [P] |
| T006 | Fix S8998 empty parametrize (2 sites) | WP02 | [P] |
| T007 | Classify + fix S2083 path-injection in bookkeeping_projection (2 sites) | WP03 | [P] |
| T008 | Classify + fix S2083 path-injection in skills/verifier (1 site) | WP03 | [P] |
| T009 | Classify + fix S3516 always-same-return methods (4 sites) | WP04 | [P] |
| T010 | Fix S2583 always-true conditions (2 sites) | WP04 | [P] |

## Work Packages

### WP01 — Tautological test assertions (S5863 ×16) — mechanical

- **Goal**: Replace 16 assertions whose actual and expected expressions are identical with the
  intended comparison (recovered from test context), so each test actually checks something. Where
  intent is unrecoverable, remove the assertion with a one-line rationale (never leave it tautological).
- **Priority**: P2 (US2 — test integrity). **Requirements**: FR-004; NFR-001/002/003.
- **Independent test**: for each corrected assertion, show red-first evidence (it fails against the
  pre-fix behavior) then passes; scoped pytest over the touched files is green.
- **Subtasks**: T001, T002, T003.
- **Prompt**: [tasks/WP01-tautological-assertions.md](./tasks/WP01-tautological-assertions.md) (~200 lines)

### WP02 — Swallowed assertions + empty parametrize (S5779 ×14 + S8998 ×2) — mechanical

- **Goal**: Move each `assert` out of a `try/except AssertionError` that swallows it (4 src + 10 test
  sites) so failures propagate; the src sites must preserve the intended error translation/recovery.
  Make the 2 empty `parametrize` tests execute (real cases, or remove the vestigial parametrize).
- **Priority**: P2 (US2). **Requirements**: FR-005, FR-006; NFR-001/002.
- **Independent test**: scoped pytest green; a deliberately-failing assert now propagates (spot-check);
  the previously-empty parametrized tests now run ≥1 case.
- **Subtasks**: T004, T005, T006.
- **Prompt**: [tasks/WP02-swallowed-asserts-parametrize.md](./tasks/WP02-swallowed-asserts-parametrize.md) (~230 lines)

### WP03 — Path-injection security (S2083 ×3) — investigate

- **Goal**: For each of the 3 BLOCKER path-injection sites, trace the tainted path component to its
  source. If reachable from external/user input, validate/contain it (reject traversal, anchor under an
  allowed root) with a test exercising the rejection. If from trusted repo/mission-internal data, keep
  the semantics and record a safety rationale (C-001) — no sanitization theatre.
- **Priority**: P1 (US1 — security). **Requirements**: FR-001; C-001; NFR-001/002.
- **Independent test**: for a contained site, a traversal input is rejected/anchored (test); for a
  trusted-local site, the rationale is recorded and behavior unchanged.
- **Subtasks**: T007, T008.
- **Prompt**: [tasks/WP03-path-injection.md](./tasks/WP03-path-injection.md) (~200 lines)

### WP04 — Degenerate control flow (S3516 ×4 + S2583 ×2) — investigate

- **Goal**: For each site, decide real-bug vs intentional. Always-same-return (S3516 ×4): fix the logic
  (real bug) or remove the smell (drop vacuous return / adjust signature / make invariant explicit).
  Always-true condition (S2583 ×2): correct the condition or remove the dead branch. Every fix carries
  a behavioral test (C-002); never a suppression.
- **Priority**: P1 (US1 — correctness). **Requirements**: FR-002, FR-003; C-002; NFR-001/002.
- **Independent test**: a behavioral test asserts the corrected control flow / condition; scoped pytest green.
- **Subtasks**: T009, T010.
- **Prompt**: [tasks/WP04-degenerate-control-flow.md](./tasks/WP04-degenerate-control-flow.md) (~200 lines)

## Dependencies

None. WP01–WP04 own disjoint files and may run fully in parallel.

## MVP / sequencing note

WP03 (security BLOCKERs) and WP04 (logic BLOCKERs/BUGs) are the highest-value (US1, P1). WP01/WP02 are
P2 test-integrity. All four are independent; recommended review depth is higher for WP03/WP04.
