# Mission Specification: Gate-Artifact Merge Driver Unit Gate

**Mission Branch**: `fix/gate-artifact-merge-driver-unit-gate`
**Created**: 2026-08-10
**Status**: Draft
**Input**: Restore the driver-level unit gate deleted by `b04da00e1` (#3232), rewritten against the #3076 row-union authority model, pinning the #2804 no-reset-to-scaffold + evidence-survival invariant at the reconciler-unit level.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reconciler regression that clobbers a filled gate artifact is caught fast, at unit level (Priority: P1)

When two branches' gate artifacts (`acceptance-matrix.json`, `issue-matrix.json`) are merged, the shipped **row-union reconciler** must never reset a filled/accepted criterion back to a scaffold placeholder (`SCAFFOLD_TODO_MARKER`), and the accepted evidence handle must survive — including when a genuine same-key divergence is emitted as a structured conflict marker. Today the only coverage of this #2804 invariant is (a) a slow (~160 s) integration marker that shells out to `spec-kitty merge-driver-*` as a subprocess (invisible until `pip install -e .`), and (b) a general row-union sibling test that exercises the reconcilers but never in the #2804-specific scaffold-vs-filled + evidence-handle framing. The **driver-level unit gate that held this invariant was deleted in `b04da00e1`** and never restored — nobody owns its absence. This story restores that gate as fast, in-memory unit tests calling the pure reconcilers directly.

**Why this priority**: A silent reconciler regression that resets filled gate artifacts to placeholder would let missions merge with their acceptance evidence discarded — the exact #2804 defect. The integration marker catches it slowly and only through a subprocess; a unit gate catches it in-process, in milliseconds, at the seam where the logic actually lives. P1 (tech-debt / regression-coverage restoration).

**Independent Test**: Call `reconcile_acceptance_matrix_documents(base, ours, theirs)` with base=scaffold criterion, ours=filled criterion (accepted evidence handle), theirs=base-unchanged; assert the merged criterion is the filled one, the evidence handle is present, `SCAFFOLD_TODO_MARKER` is absent from that criterion, and `overall_verdict == "pass"`. Break the reconciler to take-theirs and the test reds.

**Acceptance Scenarios**:

1. **Given** a base scaffold criterion and a filled+accepted `ours` (theirs unchanged from base), **When** the acceptance-matrix reconciler runs, **Then** the merged criterion is the filled one, the evidence handle survives, and `SCAFFOLD_TODO_MARKER` is not in that criterion.
2. **Given** the fill authored on the lane side (`theirs`), base scaffold, `ours` unchanged, **When** the reconciler runs, **Then** the fill and evidence handle survive and the verdict is admissible.
3. **Given** an add/add divergence with no base (ours=filled, theirs=scaffold, same `criterion_id`), **When** the reconciler runs, **Then** it does not raise, the evidence handle appears in the merged document (even embedded in a conflict marker), and the merged `overall_verdict` is admissible (never `fail`).
4. **Given** an issue-matrix row that is `unknown` in base and terminal (verified, with an evidence ref) on one side, **When** the issue-matrix reconciler runs, **Then** the merged row keeps the terminal verdict and the evidence ref survives.

### Edge Cases

- **Structured conflict, not silent pick**: when both sides diverge from base to different non-base values, the reconciler embeds both in a conflict marker — the evidence handle must still appear; the test asserts survival, not absence-of-marker (the marker legitimately contains the scaffold text).
- **Anti-vacuity**: every survival assertion is paired with a negative control (all-scaffold input → handle absent, verdict `pending`/`unknown`) and a two-way fixture self-control (the handle IS in the filled fixture, is NOT in the placeholder fixture), so no assertion can pass silently unsatisfiable or silently vacuous.
- **`pending` is admissible on purpose**: a merged document that admits a scaffold row yields `overall_verdict == "pending"` (the #3231 product behavior). The gate MUST admit `pending`; it must not try to force `pass` (that would amend the #3076 row-union authority model and is a separate, filed concern).

### User Story 2 - Doctrine module Sonar-HIGH maintainability debt is remediated (Priority: P2)

The `src/doctrine/` package carries 45 open Sonar HIGH maintainability findings — 37 `S1192`
(the same non-trivial string/path literal repeated ≥3× in a module, mostly in
`drg/migration/hand_authored_overlay.py`) and 8 `S3776` (functions over the cognitive-complexity
ceiling of 15). This story clears the mechanical dup-literal debt (hoist repeated literals to named
module constants) and reduces the tractable over-complex functions via clean, behavior-preserving,
tested helper extraction — without changing doctrine behavior and without suppressions. One outlier
(`drg/migration/extractor.py:545`, complexity 183) is explicitly **deferred** to a dedicated mission:
a 183→15 restructure is disproportionate and high-risk to fold here.

**Why this priority**: maintainability debt, not a correctness hole — lower stakes than the #2804 gate,
folded opportunistically because this mission is otherwise a single small WP. P2.

**Independent Test**: after the change, a fresh Sonar analysis of `src/doctrine/` reports **0** open
`S1192` HIGH findings and the 7 addressed `S3776` functions at ≤15 (or a documented, meaningfully-reduced
residual); the full `tests/doctrine/` suite stays green (no behavior change).

**Acceptance Scenarios**:

1. **Given** a repeated literal flagged by `S1192` in a doctrine module, **When** the sweep runs, **Then**
   it becomes a single named module constant referenced at every site, and the module's tests stay green.
2. **Given** an over-complex doctrine function flagged by `S3776` (excluding `extractor.py:545`), **When**
   it is refactored, **Then** deterministic sub-logic is extracted into helpers with focused tests and the
   function's cognitive complexity is reduced toward ≤15, with identical observable behavior.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Restore the driver-unit gate file | Restore `tests/merge/test_gate_artifact_merge_drivers_2804.py` (reclaiming the name `b04da00e1` deleted) with unit tests that call the pure reconcilers `reconcile_acceptance_matrix_documents` / `reconcile_issue_matrix_documents` directly, in memory. | High | Open |
| FR-002 | Pin no-reset-to-scaffold + evidence survival | Assert that a filled/accepted acceptance criterion is never reset to `SCAFFOLD_TODO_MARKER` and its accepted evidence handle survives the merge, for both fill-on-ours and fill-on-theirs orderings. | High | Open |
| FR-003 | Pin evidence survival inside a structured conflict | Assert that in an add/add same-key divergence the reconciler does not raise and the accepted evidence handle appears in the merged document even when emitted inside a conflict marker. | High | Open |
| FR-004 | Pin the admissible merged-verdict domain | Assert the merged `overall_verdict` is always in `{pass, pending, pass_pending_consolidation}` (never `fail`) when a scaffold row is admitted alongside a filled row. | High | Open |
| FR-005 | Issue-matrix terminal-verdict survival | Assert `reconcile_issue_matrix_documents` keeps a terminal issue-row verdict and its evidence ref when the other side is base/scaffold. | Medium | Open |
| FR-006 | Clear doctrine S1192 dup-literals | Hoist every `S1192`-flagged repeated literal in `src/doctrine/` (37 findings, chiefly `drg/migration/hand_authored_overlay.py`) to a single named module constant referenced at all sites. | Medium | Open |
| FR-007 | Reduce tractable doctrine S3776 complexity | For the 7 tractable `S3776` functions in `src/doctrine/` (`drg/merge.py:941`, `drg/validator.py:35`, `agent_profiles/repository.py:365`, `drg/org_pack_loader.py:746`, `base.py:227`, `versioning.py:316`, `drg/migration/extractor.py:933`), extract deterministic helpers with focused tests to bring cognitive complexity toward ≤15, behavior-preserving. `extractor.py:545` (complexity 183) is DEFERRED. | Medium | Open |
| FR-008 | Resolve remaining doctrine minor smells | Fix the 3 remaining doctrine code-smell minors: `S6353` concise-regex (`drg/org_pack_config.py:71` — `[A-Za-z0-9_]`→`\w`), `S7632` malformed suppression comment (`artifact_kinds.py:118`), `S117` local-variable naming (`missions/glossary_hook.py:134`). | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Unit-level, no I/O | The gate runs purely in memory: no git repository, no subprocess, no `pip install -e .`. Marker is `pytest.mark.unit` only (never `git_repo`/`non_sandbox`/`integration`). | Maintainability | High | Open |
| NFR-002 | Non-vacuous assertions | Every invariant assertion is paired with a negative control that fails when the invariant is absent (take-theirs / all-scaffold), plus a two-way fixture self-control on the evidence handle. | Reliability | High | Open |
| NFR-003 | Fast | The whole gate file completes in under 5 seconds locally (contrast: the integration marker is ~160 s), so it can run in the fast unit lane. | Efficiency | Medium | Open |
| NFR-004 | Behavior-preserving Sonar sweep | The doctrine Sonar remediation changes no observable doctrine behavior: the full `tests/doctrine/` suite stays green, and every extracted `S3776` helper carries focused tests exercising its branches (per the Sonar coverage expectation). | Maintainability | Medium | Open |
| NFR-005 | No suppressions | No `# noqa`, `# type: ignore`, or Sonar suppression comment is added to clear a finding; findings are cleared by real fixes only. | Maintainability | High | Open |

## Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Do not touch the integration marker | `tests/merge/test_issue_2804_merge_resets_gate_artifacts.py` (the subprocess marker) is out of scope — do not re-pin, relocate, or edit it. | Technical | High | Open |
| C-002 | Admit `pending` — do not fix #3231 | The gate MUST keep `pending` in the admissible verdict domain. Forcing `pass` on an admitted scaffold row would amend the #3076 row-union authority model and is the separately-filed #3231 product defect — explicitly out of scope. | Technical | High | Open |
| C-003 | Overlay, not duplicate | Keep the gate a narrow #2804-specific overlay (~6 tests) and cross-reference the row-aware sibling (`tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`) in the module docstring so a future reader does not cull it as a duplicate of the general row-union coverage. | Technical | Medium | Open |
| C-004 | Sonar sweep scoped to doctrine | The Sonar remediation touches only `src/doctrine/` and its tests under `tests/doctrine/`; no cross-module churn. `extractor.py:545` (S3776, complexity 183) is out of scope (deferred to a dedicated mission). | Technical | Medium | Open |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `tests/merge/test_gate_artifact_merge_drivers_2804.py` exists with ~6 unit tests, all green, `pytest.mark.unit` only, no git/subprocess.
- **SC-002**: Each survival/domain invariant has a negative control that reds when the invariant is removed (mutating the reconciler to take-theirs, or the fixture to all-scaffold, fails the gate).
- **SC-003**: The gate closes the #2804 driver-level ownership gap: a reconciler regression that resets a filled criterion to `SCAFFOLD_TODO_MARKER` or drops the accepted evidence handle reds this gate (in-process, fast), independent of the slow integration marker.
- **SC-004**: `pending` remains admissible (a merged doc with an admitted scaffold row passes the domain assertion), confirming #3231 was not silently "fixed" here.
- **SC-005**: A fresh Sonar analysis of `src/doctrine/` reports **0** open `S1192` HIGH findings (from 37).
- **SC-006**: The 7 addressed `S3776` doctrine functions are at cognitive complexity ≤15 (or carry a documented, meaningfully-reduced residual); `tests/doctrine/` stays green and each extracted helper has focused tests.
- **SC-007**: The 3 remaining doctrine minor smells (`S6353`, `S7632`, `S117`) are resolved — a fresh Sonar analysis of `src/doctrine/` reports **0** open findings for those rules.
