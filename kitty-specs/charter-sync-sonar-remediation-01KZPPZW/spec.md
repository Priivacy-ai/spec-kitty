# Mission Specification: Charter & Sync Sonar Remediation

**Mission Branch**: `fix/charter-sync-sonar-remediation`
**Created**: 2026-08-10
**Status**: Draft
**Input**: Clear the SonarCloud maintainability backlog for the `charter` and `sync` modules (80 open findings) via behavior-preserving refactors with no new suppressions. Full findings inventory: scratchpad `charter-sync-sonar-findings.txt`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The charter and sync modules carry no avoidable Sonar maintainability debt (Priority: P2)

`src/charter/` (+ `src/specify_cli/charter_runtime/`) and `src/specify_cli/sync/` together carry **80**
open Sonar findings — duplicate literals, over-complex functions, malformed suppression comments, unused
parameters, too-many-parameter signatures, and one super-linear-backtracking (ReDoS-class) regex flagged
`BLOCKER`. This story clears them: hoist repeated literals to named constants; extract tested helpers to
bring over-complex functions to the ≤15 cognitive-complexity ceiling; fix or remove malformed suppression
comments; drop genuinely-unused parameters; simplify the ReDoS regex while preserving its match semantics —
all **behavior-preserving**, with **no new suppressions**, and each extracted helper covered by a focused test.

**Why this priority**: maintainability + one performance/robustness BLOCKER; no functional gap. Opportunistic
module sweep following the doctrine remediation (#3232). P2 (the BLOCKER regex is the highest-value item).

**Independent Test**: a fresh Sonar analysis of `src/charter/` and `src/specify_cli/sync/` reports 0 open
findings for the addressed rules (except any documented, meaningfully-reduced complexity residual); the full
`tests/charter/` and `tests/sync/` suites stay green (no behavior change).

**Acceptance Scenarios**:

1. **Given** a repeated literal flagged `S1192`, **When** the sweep runs, **Then** it becomes a single named
   module constant referenced at every site and the module's tests stay green.
2. **Given** an over-complex function flagged `S3776`, **When** it is refactored, **Then** deterministic
   sub-logic is extracted into tested helpers, its cognitive complexity is ≤15 (or a documented residual),
   and observable behavior is identical.
3. **Given** the `S8786` BLOCKER regex in `token_budget.py`, **When** it is simplified, **Then** it no longer
   backtracks super-linearly AND matches exactly the same inputs (proven by a characterization test).

### Edge Cases

- **A suppression genuinely needed** (`S7632`): fix the comment's syntax and keep it with a one-line
  rationale; only remove it when it suppresses nothing real. Never leave a malformed/no-op suppression.
- **A "concise regex" or ReDoS rewrite that changes match semantics** is a behavior bug — every regex change
  is proven byte-equivalent (or ReDoS-equivalent) against representative inputs before landing.
- **A complexity function that cannot reach ≤15 without harming clarity/behavior**: reduce as far as clean,
  leave a one-line inline rationale (an inline rationale is not a suppression). All charter/sync S3776 are
  16-33 (tractable); no deferral is expected.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Charter ReDoS BLOCKER regex | Simplify the super-linear-backtracking regex at `src/charter/context_renderers/token_budget.py:308` (`S8786`) so it is linear-time AND matches identically (characterization test). | High | Open |
| FR-002 | Charter complexity | Reduce the 20 `S3776` charter functions (complexity 16-29) toward ≤15 via tested helper extraction, behavior-preserving. | Medium | Open |
| FR-003 | Charter dup-literals | Hoist the 6 `S1192` charter repeated literals to named module constants. | Medium | Open |
| FR-004 | Charter suppression comments | Fix or remove the 13 `S7632` malformed suppression comments in charter (prefer removal when the suppression is unnecessary). | Medium | Open |
| FR-005 | Charter misc smells | Resolve the remaining charter smells: `S1172` unused params (3), `S3516` invariant-return (1), `S5890` (1). | Low | Open |
| FR-006 | Sync complexity | Reduce the 7 `S3776` sync functions (complexity 16-33) toward ≤15 via tested helper extraction, behavior-preserving. | Medium | Open |
| FR-007 | Sync dup-literals | Hoist the 9 `S1192` sync repeated literals to named module constants. | Medium | Open |
| FR-008 | Sync suppression comments | Fix or remove the 7 `S7632` malformed suppression comments in sync. | Medium | Open |
| FR-009 | Sync misc smells | Resolve the remaining sync smells: `S107` too-many-params (3), `S1172` unused params (2), `S6353` regex (1), `S7503` (1), `S5713` (2), `S5779` (1), `S8572` (2). | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior-preserving | No observable behavior change: the full `tests/charter/` and `tests/sync/` suites stay green; every extracted `S3776` helper carries a focused test exercising its branches; every regex change is proven match-equivalent. | Maintainability | High | Open |
| NFR-002 | No new suppressions | No `# noqa`, `# type: ignore`, or Sonar-suppression comment is ADDED to clear a finding; findings are cleared by real fixes. Pre-existing justified suppressions may be preserved (carried, not stripped). | Maintainability | High | Open |
| NFR-003 | ReDoS fix is real | The `S8786` regex no longer exhibits super-linear backtracking (verified), not merely reformatted. | Reliability | High | Open |

## Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Scoped to charter + sync | Touch only `src/charter/`, `src/specify_cli/charter_runtime/`, `src/specify_cli/sync/`, and their tests under `tests/charter/` / `tests/sync/`. No cross-module churn. | Technical | High | Open |
| C-002 | merge_driver S8786 out of scope | The second `S8786` finding (`src/specify_cli/cli/commands/merge_driver.py:519`) is outside charter/sync — noted for a future follow-up, not fixed here. | Technical | Medium | Open |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh Sonar analysis of `src/charter/` (+ `charter_runtime`) reports 0 open `S8786`/`S1192`/
  `S7632`/`S1172`/`S3516`/`S5890` and `S3776` at ≤15 (or documented residual).
- **SC-002**: A fresh Sonar analysis of `src/specify_cli/sync/` reports 0 open `S1192`/`S7632`/`S107`/`S1172`/
  `S6353`/`S7503`/`S5713`/`S5779`/`S8572` and `S3776` at ≤15 (or documented residual).
- **SC-003**: The `token_budget.py` regex is linear-time and match-equivalent (characterization test proves both).
- **SC-004**: `tests/charter/` and `tests/sync/` stay green; no new suppressions added anywhere.
