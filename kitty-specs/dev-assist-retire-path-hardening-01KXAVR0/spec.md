# Mission Specification: Dev-Assist Retirement + Path-Validation Hardening

**Mission Branch**: `feat/dev-assist-retire-path-hardening`
**Created**: 2026-07-12
**Status**: Draft
**Input**: 2nd-wave test-suite friction audit under epic #2071 ("Tests as scaffold, not friction"). Addresses #2073 (path-validation security), #2557 (runtime-bridge dev-assist), #2076 (sibling-mission dev-assist), #2565 (compat-battery consolidation).

## Summary

After the god-module decompositions (runtime-bridge, tasks, doctor, merge, mission), the test suite accumulated **development-assist scaffolding** — tests written to drive a specific decomposition slice that, once the slice landed, became inert (self-compares, one-shot recorders), duplicative of a broader standing guard (per-seam `__module__`/re-export shape checks), or shape-pinning in a way that fights the next refactor. Separately, the deliverables-path security validator (`validate_deliverables_path`) has its failures **masked behind `xfail`**, so a green suite conceals live path-traversal / symlink / absolute / null-byte acceptance.

This mission (a) surfaces and **fixes** the path-validation security gap in-mission (red→green), and (b) retires, narrows, or consolidates the spent development-assist scaffolding **with coverage provably preserved by a standing guard before any removal** — restoring a suite that fails exactly when a real contract breaks. Retirement follows the canonical `development-assist-test-cleanup` procedure and DIRECTIVE_041.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deliverables-path validator rejects malicious paths (Priority: P1)

An operator (or mission tooling on their behalf) supplies a deliverables path. A path that escapes the project root — via `../` traversal, a case-variant bypass, an unresolved symlink, a home-directory (`~`) or absolute path, an empty/whitespace or dot-only path, or an embedded null byte — is **rejected**. Today `validate_deliverables_path()` accepts several of these, and the tests that would catch it call `pytest.xfail()` when the malicious path is accepted, so the suite stays green and the hole stays open.

**Why this priority**: it is a live security defect masked as a test-hygiene item; a security check that fails open is the highest-risk finding in the audit.

**Independent Test**: remove each `if is_valid: pytest.xfail(...)` guard so the existing `assert not is_valid` runs strict; confirm each vector goes red against today's validator (proving the vuln is live), then fix the validator until all vectors go green.

**Acceptance Scenarios**:

1. **Given** a deliverables path containing `../` that escapes the project root, **When** `validate_deliverables_path` is called, **Then** it reports the path invalid.
2. **Given** an unresolved-symlink / home / absolute / null-byte / empty / dot-only / case-variant path, **When** validated, **Then** each is reported invalid.
3. **Given** the corrected validator, **When** the path-validation suite runs, **Then** it contains zero `xfail` masks and every vector assertion passes strict.

---

### User Story 2 - Runtime-bridge dev-assist tests stop taxing refactors (Priority: P2)

A maintainer relocates a private symbol within the `runtime_bridge_*` family. The standing family compat-surface guard (`test_bridge_compat_surface.py::test_guard_b_identity_reexport_for_relocated_symbols`) still catches a genuinely broken re-export, but the per-file duplicate shape checks and the inert timing seed no longer false-red or sit vacuous.

**Why this priority**: highest-confidence, already-grounded retirements (coverage membership verified against the family guard's `ALL_COMPAT_SYMBOLS`); low risk, immediate friction relief.

**Independent Test**: the proven-duplicate tests are removed, the narrowed test still covers its unique public symbols, the kept unique test remains; the family guard still passes and a planted silent-re-export regression still trips it.

**Acceptance Scenarios**:

1. **Given** the runtime-bridge suite after retirement, **When** it runs, **Then** it is green with no coverage of any relocated-symbol invariant lost.
2. **Given** a deliberately reintroduced copy-instead-of-delegate re-export, **When** the suite runs, **Then** the standing family guard fails.

---

### User Story 3 - Sibling-mission dev-assist tests retired/narrowed with coverage preserved (Priority: P2)

The doctor / mission / merge / commit-router decomposition tests carry the same anti-patterns (golden-count duplicates strictly subsumed by a set-equality golden; one-shot "gap closed" pins; presence-overlap with a consolidated shim guard). Each is retired or narrowed only where a named standing guard is proven to cover the same invariant.

**Why this priority**: same class as Story 2, broader surface, needs per-candidate coverage verification.

**Independent Test**: each retired/narrowed test's invariant is shown covered by a named guard; the doctor/mission/merge suites stay green.

**Acceptance Scenarios**:

1. **Given** a retired golden-count assertion, **When** the canonical golden set-equality runs, **Then** it already fails on the same drift the retired count would have caught.

---

### User Story 4 - Fragmented per-seam compat batteries consolidated (Priority: P3)

The per-seam re-export identity + `__module__`-ownership battery is copy-pasted across the merge (×8), tasks (×6), and doctor families. Each is real, unique coverage of private relocated symbols (not covered by CLI goldens), so it is not deleted — it is **consolidated** into one per-family compat-surface guard (the runtime-bridge/mission shape), and the tautological byte-identical-literal pins and internal-call-graph interception proofs are retired.

**Why this priority**: the biggest structural lever, but larger and lower-urgency than the security and dev-assist retirements; depends on the consolidation pattern proven in Stories 2–3.

**Independent Test**: one consolidated guard per family whose symbol set ≥ the union of the retired batteries; a planted broken re-export in any family trips the consolidated guard.

**Acceptance Scenarios**:

1. **Given** a family's fragmented identity batteries replaced by one consolidated guard, **When** any relocated private symbol becomes a copy instead of a delegate, **Then** the consolidated guard fails.

### Edge Cases

- A path-validation `xfail` that is actually **stale** (the vector is already rejected): the assertion simply goes green when de-xfailed — no product fix needed for that vector; record it as verified-already-fixed.
- A per-file shape test whose symbol set is **not** fully covered by the standing guard (e.g. public relocated names, unpatched helpers): it is **narrowed or kept**, never deleted (coverage-before-deletion).
- Consolidating a family guard must not drop a symbol that only a fragmented battery covered — the consolidated symbol set must be a strict superset.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Validator rejects malicious deliverables paths | As an operator, I want `validate_deliverables_path` to reject traversal / case-variant / empty / dot / unresolved-symlink / home / absolute (POSIX **and** Windows) / control-char (null + RTL) paths so that no deliverable escapes the project root. (Hardens the validator **function**; wiring it into the runtime path is deferred — see Out of Scope.) | High | Open |
| FR-002 | Unmask path-validation tests to strict red-first | As a maintainer, I want the 8 `xfail` masks and 5 assertion-free tests in `test_path_validation.py` replaced by strict acceptance assertions so that a green suite guarantees the holes are closed. | High | Open |
| FR-003 | Retire/narrow runtime-bridge dev-assist tests | As a maintainer, I want the family-guard-duplicate shape tests + inert timing seed retired, the partially-duplicate `io` test narrowed to its uncovered public symbols, and the unique untracked-reexport test kept, so relocations stop false-redding. | High | Open |
| FR-004 | Retire/narrow sibling-mission dev-assist tests | As a maintainer, I want the doctor/mission/merge/commit-router golden-count duplicates, one-shot "gap closed" pins, and presence-overlaps retired or narrowed where a named standing guard covers the invariant. | Medium | Open |
| FR-005 | Consolidate per-seam compat batteries | As a maintainer, I want each family's fragmented per-seam re-export identity batteries consolidated into one per-family compat-surface guard, with tautological literal pins and call-graph interception proofs retired. | Medium | Open |
| FR-006 | Re-point stale docstrings | As a maintainer, I want every source/test docstring that names a moved or deleted test re-pointed so references stay accurate. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Security anti-vacuity | After FR-001/002: 8/8 malicious vectors rejected and 0 `xfail` remain in `test_path_validation.py`; a reintroduced accepted-malicious-path makes the suite fail (proven red-first before the fix). | Security | High | Open |
| NFR-002 | Coverage-preservation on retirement | Every retired test's invariant is demonstrably covered by a NAMED standing guard; the full pre-existing runtime + architectural + doctor + merge suites stay green (0 regressions); a planted silent-re-export regression still trips the relevant standing guard. | Reliability | High | Open |
| NFR-003 | No new masking introduced | The change adds 0 new `xfail`/`skip` masks, 0 `file.py:NNN`-pinned ratchet entries, and 0 wiring-only (`assert_called`-only) assertions (DIRECTIVE_041). | Maintainability | High | Open |
| NFR-004 | Net scaffolding reduction | Net test LOC decreases (scaffolding removed, not merely moved); no retained test pins transient code-shape that fails on a behavior-preserving relocation. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Security lands in-mission | FR-001/FR-002 land verified live (red→green) within this mission; the security fix is not deferred to a follow-up. | Technical | High | Open |
| C-002 | Coverage before deletion | No test is deleted until its invariant is proven covered by a standing guard (procedure anti-pattern "retire coverage disguised as a duplicate"). | Technical | High | Open |
| C-003 | Canonical procedure governs retirement | Retirements follow `development-assist-test-cleanup` + DIRECTIVE_041 (keep functional/arch; retire inert/duplicate/shape-pin; narrow partials); "delete the test" as a blanket verb is prohibited. | Process | High | Open |
| C-004 | Scope boundary | Out of scope: the #2077 ban-gate hole (#2564), fixture/ULID realism (#2074), wiring-only triage (#2075) — sibling missions. Pre-decomposition scaffolding (e.g. mission-068's `git show` self-compare) is DIRECTIVE_025, not this mission. | Process | Medium | Open |

### Key Entities

- **Development-assist test**: a test written to drive a specific decomposition slice; after the slice lands it may be inert, duplicative of a standing guard, or shape-pinning.
- **Family / compat-surface guard**: the single standing test that asserts a whole symbol family's re-export/native-delegate invariant (e.g. `test_bridge_compat_surface.py`); the authority coverage is measured against.
- **Deliverables-path validator**: `validate_deliverables_path()` (`src/specify_cli/mission.py`) — the security surface under FR-001.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `test_path_validation.py` contains 0 `xfail` masks and 0 assertion-free tests; all 8 malicious-path vectors are rejected by the validator (verified red→green).
- **SC-002**: 0 test regressions across the runtime, architectural, doctor, and merge suites after retirement/consolidation; every retirement cites the standing guard that preserves its coverage.
- **SC-003**: net development-assist test LOC is reduced; each consolidated family exposes ≤1 compat-surface guard whose symbol set is a strict superset of the batteries it replaces.
- **SC-004**: planted regressions — an accepted malicious path, and a silent copy-instead-of-delegate re-export in each touched family — are each caught by a retained standing guard.

## Assumptions

- The path-validation vulnerabilities are live; this is verified red-first per vector. A stale `xfail` (vector already rejected) is de-xfailed and recorded as verified-already-fixed rather than driving a product change.
- The family/golden guards' symbol coverage is as analyzed in the 2nd-wave audit (verified per-candidate before deletion, not assumed).

## Out of Scope

- Sibling missions under #2071: gate-hardening (#2564), test fixture/data realism (#2074), wiring-only assertion triage (#2075).
- Any test that predates the in-scope decomposition missions (governed by DIRECTIVE_025, not this mission's procedure).
- Broad refactors of the production modules beyond the `validate_deliverables_path` security fix required by FR-001.
- **Runtime wiring of the validator** — `validate_deliverables_path` currently has no production callers (the runtime path `get_deliverables_path` → `workflow_executor.py` never invokes it). This mission hardens the function (verified latent hardening); wiring it into the runtime so a malicious `deliverables_path` is rejected in production is a path-containment/trust concern that overlaps the ship-code-as-assets doctrine design (**epic #2539**, trust-surface **#2536**) and is deferred there. NFR-001 is scoped to the function's behavior, and the un-wired state is stated in the PR.
