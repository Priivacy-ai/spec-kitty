# Mission Specification: Sonar BUG and BLOCKER Remediation

**Mission Branch**: `fix/sonar-bug-blocker-remediation`
**Created**: 2026-08-10
**Status**: Draft
**Input**: Remediate all OPEN/CONFIRMED SonarCloud BUG (34) and BLOCKER (7) issues on `Priivacy-ai_spec-kitty`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Eliminate real logic and security defects (Priority: P1)

A maintainer relies on SonarCloud's BLOCKER and BUG signals to catch defects that would otherwise ship: filesystem paths built from user-controlled data (path-traversal exposure), methods whose control flow can only ever return one value (a sign of a broken branch), and conditions that can never be false (dead or inverted logic). Today seven BLOCKERs and two always-true BUG conditions sit OPEN, so the quality gate cannot distinguish "no real defects" from "known defects ignored". This story closes them at the root.

**Why this priority**: These are correctness and security defects — the highest-stakes items. A path-injection hotspot or an always-true guard can cause real incorrect behavior, not just noise.

**Independent Test**: Fix the 3 path-injection (S2083), 4 always-same-return (S3516), and 2 always-true (S2583) issues; verify each with a focused test that exercises the corrected branch/validation, and confirm SonarCloud no longer reports them. Delivers a clean BLOCKER surface independent of the test-integrity work.

**Acceptance Scenarios**:

1. **Given** a path constructed from an externally-influenced value (S2083), **When** the fix lands, **Then** the path component is validated/sanitized (or proven trusted-local with recorded rationale) and a test exercises the rejection/containment path.
2. **Given** a method Sonar flags as always returning the same value (S3516), **When** the fix lands, **Then** the control flow is corrected (real bug) or the vacuous return is removed/redesigned (intentional), with a test asserting the observable behavior.
3. **Given** a condition Sonar flags as always true (S2583), **When** the fix lands, **Then** the condition is corrected or the dead branch removed, with a test proving the intended behavior.

---

### User Story 2 - Restore test-suite integrity (Priority: P2)

A developer trusts a green test suite to mean the assertions actually check something. Today 32 tests/assertions are defective in ways that make them silently vacuous: 16 compare a value to itself (`assert x == x`), 14 place an `assert` inside a `try/except` that catches `AssertionError` (so the failure is swallowed), and 2 `parametrize` sets are empty (so the test never runs). Each is a false sense of safety. This story restores real coverage.

**Why this priority**: Defective tests mask regressions but are not themselves a live production defect, so they rank below US1. They are still real bugs — a vacuous test is worse than no test because it looks like protection.

**Independent Test**: Fix the S5863 (16), S5779 (14), and S8998 (2) issues; for each, demonstrate the corrected assertion/parametrize now fails against the defect it is meant to catch (red-first) or, where intent is unrecoverable, remove it with rationale. Confirm SonarCloud clears them.

**Acceptance Scenarios**:

1. **Given** an assertion with identical actual and expected expressions (S5863), **When** fixed, **Then** it asserts the intended relationship (recovered from test intent) and would fail if that relationship were violated — or it is removed with a recorded rationale.
2. **Given** an `assert` inside `try/except AssertionError` (S5779), **When** fixed, **Then** the assertion is moved outside the swallowing handler (or the handler narrowed) so a failed assertion propagates.
3. **Given** an empty `parametrize` (S8998), **When** fixed, **Then** the test runs against at least one real case, or the parametrize is removed so the test executes.

### Edge Cases

- **Unrecoverable test intent**: an S5863 assertion whose intended comparison cannot be reconstructed from context is removed (not left tautological), with a one-line rationale, rather than guessing a wrong assertion.
- **Intentional constant return**: an S3516 method that legitimately always returns the same value (e.g. a protocol-conforming stub) is refactored to remove the smell (drop the vacuous `return`, adjust the signature, or make the invariant explicit) rather than inventing branching.
- **Trusted-local path (not external input)**: an S2083 path built from repo/mission-internal data rather than external user input is confirmed safe and kept with a recorded rationale, per the charter's loopback/local-only Sonar guidance — not sanitized artificially.
- **New Sonar issues introduced by a fix**: a fix that adds a branch/helper without a test would create a new-code-coverage finding; every new branch gets a test in the same change.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Path-injection hotspots resolved (S2083 ×3) | As a maintainer, I want paths built from user-controlled data validated/contained so that path traversal is impossible. | High | Open |
| FR-002 | Always-same-return methods corrected (S3516 ×4) | As a maintainer, I want methods that can only return one value fixed or redesigned so that the control flow reflects real intent. | High | Open |
| FR-003 | Always-true conditions corrected (S2583 ×2) | As a maintainer, I want conditions that can never be false fixed so that no branch is dead or inverted. | High | Open |
| FR-004 | Tautological assertions corrected (S5863 ×16) | As a developer, I want self-comparing assertions to assert the intended relationship so that the test actually checks something. | Medium | Open |
| FR-005 | Swallowed assertions restructured (S5779 ×14) | As a developer, I want assertions not caught by their own except-AssertionError so that failures propagate. | Medium | Open |
| FR-006 | Empty parametrize sets executed (S8998 ×2) | As a developer, I want parametrized tests to run against real cases so that they are not silently skipped. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No suppression | Zero new suppression comments (`# noqa`, `# type: ignore`, Sonar suppress/`NOSONAR`) are introduced to resolve any issue; measured as 0 added-suppression lines in the mission diff. | Maintainability | High | Open |
| NFR-002 | Green and lint-clean | All touched test files pass, and `ruff` + `mypy` report zero new issues on changed files. | Reliability | High | Open |
| NFR-003 | Red-first for recoverable assertions | For every recoverable-intent test-assertion fix, the corrected assertion demonstrably fails against the defect it replaces before the fix (red-first evidence captured); deletions carry a recorded rationale. | Reliability | High | Open |
| NFR-004 | Sonar surface cleared | A post-merge SonarCloud re-scan reports 0 OPEN/CONFIRMED BUG and 0 OPEN/CONFIRMED BLOCKER for the project (or every residual item carries a written, reviewed false-positive rationale). | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Trusted-local path exemption | For S2083, a path built from trusted repo/mission-internal data (not external user input) is kept with a recorded safety rationale rather than artificially sanitized, per the charter loopback/local-only Sonar guidance. | Technical | High | Open |
| C-002 | New branch requires a test | Every new branch/helper introduced by a fix gets a focused test in the same change (Sonar new-code coverage). | Technical | High | Open |
| C-003 | Scope boundary | Scope is exactly the 34 BUG + 7 BLOCKER OPEN/CONFIRMED at mission start; HIGH-severity maintainability issues (complexity/dup-literals) are explicitly out of scope (handled by separate per-module missions). | Technical | High | Open |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 OPEN/CONFIRMED SonarCloud BUG issues project-wide after merge (from 34).
- **SC-002**: 0 OPEN/CONFIRMED SonarCloud BLOCKER issues project-wide after merge (from 7).
- **SC-003**: 0 suppression comments added to achieve the above — every fix is a real change (residual false positives, if any, carry a written rationale, not a suppression).
- **SC-004**: The full affected test scope runs green with no new `ruff`/`mypy` findings on changed files.
