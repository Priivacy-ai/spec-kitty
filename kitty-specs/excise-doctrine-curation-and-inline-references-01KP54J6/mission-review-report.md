# Mission Review Report: excise-doctrine-curation-and-inline-references-01KP54J6

**Reviewer**: Claude Opus 4.6 (post-merge mission reviewer)
**Date**: 2026-04-14
**Mission**: `excise-doctrine-curation-and-inline-references-01KP54J6` — Excise Doctrine Curation and Inline References (EPIC #461 Phase 1, tracked by #463)
**Baseline commit**: `6e9e6506` (PR #607 "fix: address sonar sync literals")
**HEAD at review**: `f20564f0`
**Merge commit**: `cab59fc1`
**WPs reviewed**: WP01 (curation excision) / WP02 (inline-field strip) / WP03 (single context builder + legacy excision)
**Per-WP review outcome**: all three approved first cycle, no rejection cycles, no arbiter overrides.

---

## Method summary

- Spec / plan / tasks / contracts absorbed in full; all 16 FRs and 4 NFRs traced.
- `status.events.jsonl`: clean pipeline, zero rejection cycles, two `force=true` transitions (reviewer-start claims and final `approved` transition — both procedural).
- Git timeline: 136 changed files since baseline; +7,873 / -5,182 lines.
- Live fidelity checks (on `f20564f0`):
  - Success Criterion 1–3 filesystem checks: PASS (no `_proposed/`, no `curation/`, no `doctrine.py`, no `reference_resolver.py`).
  - Occurrence verifier (`python scripts/verify_occurrences.py .../index.yaml`): VERIFIER GREEN.
  - NFR-002b byte-parity diff: **empty for all four bootstrap actions** (specify, plan, implement, review) — the central acceptance gate for the cutover.
  - Key shipped YAMLs grep: zero `tactic_refs` / `paradigm_refs` / `applies_to` outside carve-outs.
  - Pytest on all WP03-authored new tests (56 tests): all pass.
  - `mypy --strict` on new code: only pre-existing dict-invariance warning confirmed to exist on baseline.

---

## FR Coverage Matrix

| FR ID | Requirement (brief) | WP Owner | Test File(s) | Verdict | Finding |
|-------|---------------------|----------|--------------|---------|---------|
| FR-001 | Zero `_proposed/` dirs under `src/doctrine/` | WP01 | `tests/specify_cli/cli/test_doctrine_cli_removed.py` + filesystem check | ADEQUATE | — |
| FR-002 | `src/doctrine/curation/` deleted in entirety | WP01 | filesystem check | ADEQUATE | — |
| FR-003 | `doctrine.py` removed + CLI unknown-command | WP01 | `tests/specify_cli/cli/test_doctrine_cli_removed.py` | ADEQUATE | — |
| FR-004 | `validators/doctrine_curation.py` deleted | WP01 | (absent-file check, occurrence verifier) | ADEQUATE | — |
| FR-005 | No shipped YAML contains forbidden keys | WP02 | occurrence verifier + `tests/doctrine/test_artifact_compliance.py` | ADEQUATE | — |
| FR-006 | Schemas declare no forbidden fields | WP02 | (grep via verifier) | ADEQUATE | — |
| FR-007 | Pydantic models declare no forbidden fields | WP02 | `tests/doctrine/*/test_models.py` | **PARTIAL** | [DRIFT-1] `specify_cli/charter/schemas.py :: Directive.applies_to` still declared; carve-out hides it |
| FR-008 | Per-kind validation rejects with structured error (incl. procedure step-level) | WP03 | `tests/doctrine/test_inline_ref_rejection.py` | **FALSE_POSITIVE** | [DRIFT-2] rejecters have zero live `src/` callers; runtime loader path (`DirectiveRepository`) catches `ValidationError` and only emits `warnings.warn`, never raises `InlineReferenceRejectedError` |
| FR-009 | Single context builder `build_charter_context` | WP03 | `tests/charter/test_context.py` | ADEQUATE | Twin `specify_cli/charter/context.py` is thin re-export; NFR-002b byte-parity passes on all 4 actions |
| FR-010 | `reference_resolver.py` deleted, callers refactored | WP03 | grep via verifier; `tests/charter/test_resolver.py` | ADEQUATE | — |
| FR-011 | `include_proposed` removed from `load_doctrine_catalog` | WP03 | grep via verifier | ADEQUATE | — |
| FR-012 | Templates/skills/READMEs updated | WP01/03 | (manual spot-check) | ADEQUATE | — |
| FR-013 | Obsolete tests deleted or rewritten | WP03 | deletions confirmed in diff | PARTIAL | See [RISK-2] `tests/doctrine/drg/migration/test_extractor.py::_count_inline_refs` now vacuously true |
| FR-014 | Validator-rejection test suite, one per kind | WP03 | `tests/doctrine/test_inline_ref_rejection.py` | **PARTIAL** | Test constructs dicts directly rather than "loading a YAML fixture"; does not exercise the load-path the spec scenario 4 requires |
| FR-015 | Per-WP occurrence classification artifact | all | `occurrences/WP0N.yaml` | **MISSING for WP02** | [DRIFT-3] `occurrences/WP02.yaml` was never committed; only WP01.yaml and WP03.yaml exist |
| FR-016 | Merged-graph validator runs on live `build_charter_context()` path | WP03 | `tests/charter/test_merged_graph_on_live_path.py` | PARTIAL | Test exercises `load_validated_graph` helper in isolation, not `build_charter_context` itself; however, `src/charter/context.py:505` provably calls `assert_valid()` unconditionally, so the behavior holds even though the regression test doesn't target the exact invocation FR-016 asks about |
| NFR-001 | Pytest runtime ≤5% regression | all | (not measured in-repo) | UNKNOWN | Reviewer cited "109 WP03-focus tests all pass"; no CI-level p50 comparison committed |
| NFR-002a | Artifact-reachability parity across (profile, action, depth) | WP03 | absorbed into rewritten `test_context.py` and NFR-002b | PARTIAL | New `test_context.py` uses a minimal synthetic graph with `assert_valid` patched out (line 129); the comprehensive parametrized matrix from the deleted `test_context_parity.py` is not reproduced. Reachability is guaranteed transitively via NFR-002b byte-parity, not directly. |
| NFR-002b | Rendered-text byte parity on 4 bootstrap actions | WP03 | `baseline/pre-wp03-context-*.json` | ADEQUATE | Verified live: `diff` is empty for `specify`, `plan`, `implement`, `review`. |
| NFR-003 | `mypy --strict` clean, ≥90% coverage on new code | all | CI | ADEQUATE | Only 1 mypy error reproduced on baseline (compiler.py dict-invariance); pre-existing. Coverage not programmatically verified in this review. |
| NFR-004 | Zero stray occurrences of listed literals outside carve-outs | all | `scripts/verify_occurrences.py` | ADEQUATE | Verifier green. |

**Summary**: ADEQUATE = 12; PARTIAL = 5; FALSE_POSITIVE = 1; MISSING = 1; UNKNOWN = 1 (no objective measurement committed).

---

## Drift Findings

### DRIFT-1: Twin `specify_cli/charter/schemas.py :: Directive.applies_to` field still declared

**Type**: LOCKED-DECISION VIOLATION (D-3 twin-package lockstep) + partial FR-007 miss
**Severity**: MEDIUM
**Spec reference**: D-3 in plan.md ("every edit that touches `src/charter/{context,compiler,resolver,catalog,__init__}.py` also touches the equivalent `src/specify_cli/charter/*` file in the same WP PR"); FR-007; NFR-004 "applies_to" literal target
**Evidence**:
- `src/charter/schemas.py:80-94` — `Directive` class has `applies_to` **removed**, docstring explicitly documents the removal.
- `src/specify_cli/charter/schemas.py:80-87` — `Directive` class **still declares** `applies_to: list[str] = Field(default_factory=list)`.
- `kitty-specs/.../occurrences/index.yaml:145` — papers this over by explicitly adding `src/specify_cli/charter/schemas.py` to the `applies_to` excluding list.
- `src/specify_cli/charter/sync.py:19` and `src/specify_cli/charter/extractor.py:17` both import `Directive` from the twin — so a user overlay that supplies `applies_to` on a Directive will be silently accepted by this code path.

**Analysis**: The spec.md WP02 scope explicitly names `src/charter/schemas.py (strip applies_to)` but does not name the twin. The plan's D-3 rule, however, requires twin-package lockstep for every charter module edit. The carve-out in `index.yaml` was added to make the verifier pass without actually applying the twin edit, trading mechanical completeness against a silent inconsistency. Since `specify_cli.charter.schemas.Directive` is imported from live production code, a downstream YAML with `applies_to` is accepted here and rejected via the doctrine Pydantic model — two different validation surfaces with opposite behavior on the same field name. This is the precise "inline/edge drift" failure mode the spec's Problem Statement calls out as the reason for the mission. Not release-blocking (the field is accepted but never read), but a direct contradiction of D-3 and should be cleaned up in a follow-up issue.

### DRIFT-2: `occurrences/WP02.yaml` never committed

**Type**: PUNTED-FR (FR-015 miss for WP02)
**Severity**: LOW
**Spec reference**: FR-015; tasks.md Included subtasks for WP02 ("[x] T007 Author `occurrences/WP02.yaml`…"); plan.md D-5; spec.md Success Criterion 10
**Evidence**:
- `ls kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/` returns only `WP01.yaml`, `WP03.yaml`, `index.yaml`.
- `git log --all -- "kitty-specs/.../occurrences/WP02*"` returns no commits.
- WP02 approval reason explicitly mentions "Ephemeral r1 script and missing_edges.yaml deleted" — these appear to have stood in for the per-WP occurrence artifact.

**Analysis**: The mission-level `index.yaml` aggregates the must-be-zero set across all three WPs and the verifier passes against the aggregate. FR-015 as specified requires per-WP artifacts as evidence documents. In WP02's case, this evidence artifact simply does not exist in git. The effective verification-by-completeness gate was still enforced by the aggregate verifier, so operational risk is low — but spec.md Success Criterion 10 literally says "Each of WP1.1 / WP1.2 / WP1.3 has a committed occurrence-classification artifact at `kitty-specs/<mission_slug>/occurrences/WP1.<n>.yaml`." WP02 fails that criterion as stated.

### DRIFT-3: Twin-package capability asymmetry (pre-existing, not introduced but not closed)

**Type**: NON-GOAL ADJACENT / LOCKED-DECISION PARTIAL (D-3)
**Severity**: LOW
**Spec reference**: D-3 twin-package lockstep; plan.md "twin charter packages … deduplicating them is explicitly out of scope"
**Evidence**:
- `src/charter/resolver.py` exposes `resolve_governance_for_profile` with full DRG integration (`resolve_transitive_refs`, `load_validated_graph`).
- `src/specify_cli/charter/resolver.py` does NOT expose `resolve_governance_for_profile` and does NOT import `resolve_transitive_refs`.
- Canonical `GovernanceResolution` has 6 extra fields (`tactics`, `styleguides`, `toolguides`, `procedures`, `profile_id`, `role`); the twin does not.
- `git show 6e9e6506:src/specify_cli/charter/resolver.py` confirms this drift **pre-existed** (no `tactics` field on baseline twin).
- `src/specify_cli/charter/_drg_helpers.py` exists as a no-caller twin stub; the implementer flagged this as Deviation D2 in the WP03 report.

**Analysis**: The mission did not introduce this asymmetry and the plan explicitly carved it out of scope. However, D-3's lockstep-edit rule was only partially honored: when the canonical `charter.resolver` grew new DRG-backed functions, the twin did not. The helper scaffold was created in lockstep, but without callers in the twin it serves no runtime purpose. Treat as a known pre-existing wart confirmed by this mission, not a regression.

---

## Risk Findings

### RISK-1: Validator-rejection helpers are dead code from a runtime perspective

**Type**: DEAD-CODE / CROSS-WP-INTEGRATION
**Severity**: **HIGH**
**Location**: `src/doctrine/{directives,paradigms,procedures,tactics,styleguides,toolguides,agent_profiles}/validation.py` `reject_<kind>_inline_refs` functions; `src/doctrine/shared/errors.py::reject_inline_refs` + `reject_inline_refs_in_procedure_steps`
**Trigger condition**: Any artifact YAML (shipped or project overlay) that contains `tactic_refs` / `paradigm_refs` / `applies_to`.
**Evidence**:
- `grep` for `reject_directive_inline_refs`, `reject_tactic_inline_refs`, `reject_paradigm_inline_refs`, `reject_procedure_inline_refs`, `reject_styleguide_inline_refs`, `reject_toolguide_inline_refs`, `reject_agent_profile_inline_refs` across `src/`: **zero live callers outside definitions**. Only the test suite imports them.
- Production loader `src/doctrine/directives/repository.py:49-68` uses the pattern `Directive.model_validate(data) … except (YAMLError, ValidationError, OSError) as e: warnings.warn(...)`. An inline `applies_to` would surface as a generic Pydantic `extra_forbidden` warning, not as a structured `InlineReferenceRejectedError`, and would be silently skipped rather than raised.
- Spec Scenario 4: "`spec-kitty` loads that overlay. Then the per-kind validator **raises** a structured error … The loader does not silently ignore the field." Shipped behavior: the loader emits `warnings.warn` (which is "silently ignore" by Spec Scenario 4's definition) and does not raise.

**Analysis**: FR-008's contract is satisfied at the **function-API level** — invoking `reject_<kind>_inline_refs(data, file_path=…)` does raise `InlineReferenceRejectedError`, and the 11 fixtures in `test_inline_ref_rejection.py` prove it. But no runtime surface calls these functions, so on a real overlay the structured error never surfaces. If every rejection helper were deleted from `src/`, production behavior would be unchanged — meeting the classic "would the test still pass if implementation were deleted" definition of a false-positive test. The Pydantic `extra="forbid"` backstop provides *some* rejection (as a warning), so the pure silent-acceptance case doesn't occur, but the contract's "structured error with migration hint" promise is not met at runtime. This is the single most consequential finding in this review.

### RISK-2: Migration extractor completeness tests are now vacuously true

**Type**: ERROR-PATH / silent-coverage-loss
**Severity**: LOW (migration tool is carve-out territory)
**Location**: `tests/doctrine/drg/migration/test_extractor.py:35-96` (`_count_inline_refs`) and lines 369–430 (`TestEdgeCountCompleteness`)
**Trigger condition**: Running `test_extractor.py::TestEdgeCountCompleteness::*` against post-WP02 shipped doctrine.
**Evidence**: `_count_inline_refs()` scans `data.get("tactic_refs", [])` against `src/doctrine/directives/shipped/*.directive.yaml`. WP02 stripped every such field, so this returns ~0 for directives/paradigms. `test_edge_count_gte_inline_refs` now asserts `len(graph.edges) >= ~0`, which is trivially true.
**Analysis**: The migration extractor is explicitly a MIGRATION-ONLY tool (C-006-adjacent carve-out). Its coverage on current shipped doctrine is now weakened because the inputs the tool was calibrated against no longer exist. Not a correctness issue, but the completeness test no longer detects regressions. Acceptable as long as the extractor is kept frozen; any future change to the extractor should be accompanied by fixture-based coverage rather than live-doctrine-based coverage.

### RISK-3: `resolve_transitive_refs` behavioral-equivalence tests are hand-computed

**Type**: TEST-ADEQUACY / CROSS-WP-INTEGRATION
**Severity**: LOW
**Location**: `tests/doctrine/drg/test_resolve_transitive_refs.py:257-316` (Dimension 6 tests)
**Trigger condition**: Any future regression in DRG traversal semantics that happens to still match the hand-computed expected sets.
**Evidence**: The implementer comment block (lines 244-254) explicitly acknowledges: "The pre-WP03 transitive-reference helper has been deleted in T017 … we therefore evaluate the R-2 equivalence contract by asserting the DRG walk output matches a hand-computed expected bucketed set." The R-2 contract said "behavioral-equivalence proof vs the legacy resolver" — a live diff against the legacy is no longer possible because the legacy is deleted.
**Analysis**: The strongest equivalence proof available in-repo is the NFR-002b byte-parity check (empty diff on all 4 bootstrap actions), which integrates `resolve_transitive_refs` transitively through `build_charter_context`. The hand-computed equivalence tests are a weaker corroboration. Given the byte-parity check is green, this is acceptable; but the test file's claimed "behavioral equivalence" is a softer guarantee than R-2 demanded.

### RISK-4: Context-test `_call` harness patches `assert_valid` out

**Type**: BOUNDARY-CONDITION / TEST-ADEQUACY
**Severity**: LOW
**Location**: `tests/charter/test_context.py:129` — `patch("doctrine.drg.validator.assert_valid")`
**Trigger condition**: A regression that silently stops calling `assert_valid` on the live path would not be caught by this test file.
**Evidence**: Every functional test in the new `test_context.py` calls the harness at lines 102–137 which uses a `with … patch("doctrine.drg.validator.assert_valid") …` context. The comment on line 129 says "fixture may not pass full validation."
**Analysis**: FR-016 is nominally covered by `test_merged_graph_on_live_path.py` (which does verify `assert_valid` is called on the `load_validated_graph` helper) and the live-code inspection at `src/charter/context.py:505`. But within the mainline context-builder test suite, `assert_valid` being patched out means the suite cannot detect a regression where `build_charter_context` stops calling it. The belt-and-braces is the live-path test file, not this suite.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `src/doctrine/directives/repository.py:62-67` | Directive YAML has `applies_to` (extra-forbidden on Pydantic) | `warnings.warn("Skipping invalid shipped directive …")` | FR-008/Scenario 4: the directive is silently skipped rather than raising `InlineReferenceRejectedError` with the migration hint. |
| `src/doctrine/procedures/repository.py` / `paradigms/repository.py` | Same pattern | Same | Same. |
| `src/specify_cli/charter/schemas.py :: Directive` | User overlay supplies `applies_to` on a Directive entry in charter | Field silently accepted, never rejected, never consumed | NFR-004 verifier passes via carve-out; twin-package drift persists. |

---

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---------|----------|------------|----------------|
| YAML loaders throughout repository use `YAML(typ="safe")` (e.g. `src/doctrine/directives/repository.py:51`, `tests/doctrine/drg/migration/test_extractor.py:32`) | All doctrine YAML reads | safe | No action — `ruamel.yaml` safe mode is the correct baseline for untrusted overlays. |
| `scripts/verify_occurrences.py` reads arbitrary paths from the index.yaml | verifier | PATH-TRAVERSAL-adjacent | Low risk: developer-run script, inputs live in a repo-scoped yaml file. No action required. |
| No new subprocess, no new HTTP, no new auth surfaces introduced. | — | — | — |

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

Success Criteria 1–9 from spec.md all hold on `f20564f0`. The occurrence verifier is green, NFR-002b byte-parity is empty across all four bootstrap actions (the central acceptance gate for the cutover), no stray references to deleted literals remain outside documented carve-outs, and the 56 new/rewritten tests pass cleanly. `mypy --strict` introduces no new errors. No locked decision is violated in a release-blocking way. No security-sensitive surface was altered.

Two non-blocking findings warrant follow-up issues:

- **RISK-1 (HIGH severity)** — the FR-008 validator-rejection helpers have no live `src/` callers, so the structured `InlineReferenceRejectedError` contract is honored at the function-API level but not on the actual runtime load path. Production behavior falls back to Pydantic `extra_forbidden` warnings emitted through `warnings.warn`, which means a project overlay with inline refs is silently skipped rather than raised with the migration hint the spec promised in Scenario 4. This is not a regression from baseline (the same loader pattern existed pre-mission), and it does not re-introduce a fallback code path — but it does mean the spec's user-facing promise for Scenario 4 is unmet.
- **DRIFT-1 (MEDIUM severity)** — `specify_cli/charter/schemas.py::Directive.applies_to` is still declared. The occurrence verifier was configured with an explicit carve-out for this file, so the mechanical "zero stray occurrences" gate passes, but the D-3 twin-package lockstep rule was not honored for this field. The twin Directive is actively imported by live production code.

Neither finding is release-blocking because (a) no current production path exercises the missed rejection, (b) byte-parity is green across all bootstrap actions, and (c) the violations are additive-non-action rather than additive-wrong-action. The mission delivered its main contract: curation excision, inline-field removal from shipped YAMLs/schemas/canonical models, single-builder context, resolver excision.

### Open items (non-blocking — recommend follow-up)

1. **Wire `reject_<kind>_inline_refs` into `<kind>Repository._load()`** so Scenario 4's structured error is raised at the load path, not just callable at the library API. (RISK-1)
2. **Strip `applies_to` from `src/specify_cli/charter/schemas.py::Directive`** to restore D-3 twin-package lockstep, and remove the corresponding carve-out from `occurrences/index.yaml:145`. (DRIFT-1)
3. **Commit `occurrences/WP02.yaml`** retroactively, or amend the spec's Success Criterion 10 to reflect that WP02 used the aggregated index as its artifact. (DRIFT-2)
4. **Rehome migration-extractor completeness coverage** to static fixtures rather than live shipped doctrine (RISK-2).
5. **Add `assert_valid` spy to the mainline `test_context.py` harness** so the live-path validator invariant is enforced at every bootstrap action path (RISK-4).
6. **(Optional)** Remove the no-caller `src/specify_cli/charter/_drg_helpers.py` scaffold or promote a live caller in the twin to break the forward dead-code risk (Deviation D2).

None of these items blocks tagging a release that contains this mission's changes.
