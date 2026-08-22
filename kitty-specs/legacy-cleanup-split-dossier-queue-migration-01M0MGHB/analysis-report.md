---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: legacy-cleanup-split-dossier-queue-migration-01M0MGHB
mission_id: 01M0MGHBVSHYM701TJHXEWG3PY
generated_at: '2026-08-22T13:29:56.564197+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/SK-missions/1058/kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/spec.md
    sha256: 166f8d77a4ff3efa602665f69d16477e96760d8285189d89a6ee580cf2dbcdab
  plan.md:
    path: /home/jeroennouws/dev/SK-missions/1058/kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/plan.md
    sha256: 9d8fa9db087117e7894c13d4c36b2a89abb11f3ec2dc4655076bbfa7b506be8d
  tasks.md:
    path: /home/jeroennouws/dev/SK-missions/1058/kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/tasks.md
    sha256: 8d174f5be6cdebaba6814e1867e5bc0857f61f0aef2e4b10fa69d4bf6eea9e95
  charter:
    path: /home/jeroennouws/dev/SK-missions/1058/.kittify/charter/charter.yaml
    sha256: a90fa5d9fb0187d036a248af499643921f46773f96ad8a37e660a801ee60b641
verdict: ready
issue_counts:
  critical: 0
  high: 0
  medium: 1
  low: 0
  info: 0
findings:
- id: E1
  severity: medium
  category: coverage
  summary: NFR-003's declared bounded test-scope (spec.md) and plan.md's mirrored Testing list omit tests/sync/test_events.py, though WP02/T012 owns it and adds new SC-005/FR-006/FR-007 regression content there; WP02's own Test Strategy pytest command also omits it.
---

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| E1 | Coverage | MEDIUM | spec.md:388 (NFR-003); plan.md:47-54 (Testing); tasks/WP02-validate-event-delegation-and-sentinel-coordination.md:451-453 (Test Strategy scope) | NFR-003 enumerates the mission's bounded per-WP test surface as `tests/dossier/`, `tests/sync/test_events_namespace.py`, `tests/sync/test_dossier_pipeline.py`, `tests/sync/test_diagnose.py`, and `tests/architectural/`. It omits `tests/sync/test_events.py` (verified live: a real, distinct file, `TestValidation` at line 642, `TestInternalValidation` at line 935 — not a typo for `test_events_namespace.py`, which is also a real, separate file). Yet tasks.md's own TASKS-DECOMP-001 remediation note, WP02's `owned_files` frontmatter, and WP02's T012 subtask all establish that WP02 adds new SC-005/FR-006 and FR-007 regression test content directly into `tests/sync/test_events.py`. WP02's "Test Strategy" section then literally reproduces NFR-003's incomplete list as its suggested `pytest` invocation (`tests/dossier/ tests/sync/test_events_namespace.py tests/sync/test_diagnose.py -q`), so an implementer following that command after each subtask would not re-run the very test file T012 is writing into. | Add `tests/sync/test_events.py` to NFR-003's enumerated scope in spec.md, mirror the addition in plan.md's "Testing" line, and add the path to WP02's "Test Strategy" pytest scope command. Small, mechanical, non-functional-artifact-only edit; does not require reopening plan/tasks review at large. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 (delete local Pydantic mirror) | Yes | T002 (WP01), T020 (WP04, identity proof) | |
| FR-002 (preserve legacy "other" remap) | Yes | T003 (WP01) | |
| FR-003 (delete `_consume_legacy_values` bridge) | Yes | T004, T005 (WP01) | |
| FR-004 (promote kwargs, preserve behaviour) | Yes | T004, T005, T006 (WP01) | Binding non-mock/autospec test bar carried into T006. |
| FR-005 (drop dead `last_known_*` params) | Yes | T005 (WP01) | |
| FR-006 (`validate_event()` delegation) | Yes | T007, T008, T009, T012, T013 (WP02) | |
| FR-007 (keep dossier keys in `VALID_EVENT_TYPES`) | Yes | T008, T012 (WP02) | |
| FR-008 (AST positional-call guard) | Yes | T014-T017 (WP03) | |
| FR-009 (re-point `test_events.py` mirror imports) | Yes | T018 (WP04) | |
| FR-010 (preserve #1056 regression test) | Yes | T019 (WP04) | |
| FR-011 (coordinate sentinel into `diagnose.py`) | Yes | T010 (fix), T011 (test) (WP02) | See dedicated FR-011 analysis below — chain verified end-to-end, real test commitment confirmed. |
| NFR-001 (no net-new dependency) | Yes | WP01, WP02 (by construction — no `pyproject.toml` edit in scope) | |
| NFR-002 (validation stays visible, split contract) | Yes | WP02 (T009 emitter warning path, T010 diagnose errors-accumulator path) | Verified non-contradictory — see below. |
| NFR-003 (test scope stays bounded) | Yes (with gap) | WP01 (T001), WP04 (T021) | See finding E1 — the declared scope list itself omits `tests/sync/test_events.py`. |
| C-001 (queue-drain out of scope) | Yes (negative) | N/A by design | Verified: zero WP touches `sync/queue.py`/`sync/migrate_journal.py`; WP01 prompt explicitly lists both as "out of scope, do not touch." |
| C-002 (no deprecated wrapper) | Yes | WP01 (deletion, not shim) | |
| C-003 (baseline before attributing red) | Yes | T001 (WP01) | |
| C-004 (terminology canon) | Yes | All WPs (prose discipline) | No `Feature`/`feature*` alias introduced by this mission's own diff; existing pre-mission symbol `sync_feature_dossier` is cited accurately in spec/plan prose as a real, untouched call site, not a new alias this mission introduces. |

**Charter Alignment Issues:** None found. plan.md's own Constitution Check table (Architectural alignment / Shared Package Boundaries, Single canonical authority, ATDD-first, Campsite cleaning, Mission tracer files, Architectural gate discipline, Red-main/release discipline, Terminology Canon, Git & workflow discipline) was independently spot-verified against the charter and against live code (line-number citations for `_PAYLOAD_RULES`, `VALID_EVENT_TYPES`, `EventEmitter`, `_validate_payload`, `diagnose.py::_validate_payload`, and `diagnose.py`'s current unguarded `rules.get(...)` shape all matched the artifacts exactly). No MUST-principle conflict identified.

**Unmapped Tasks:** None. All 21 subtasks (T001-T021) map to a named FR/NFR/C per tasks.md's own "Requirements Coverage Summary" and "Subtask Index" tables, cross-checked against the WP prompt files.

**Metrics:**

- Total Requirements: 18 (11 FR + 3 NFR + 4 C)
- Total Tasks: 21 subtasks across 4 WPs
- Coverage %: 100% (every FR/NFR/C maps to >=1 WP/subtask)
- Ambiguity Count: 0 (no vague adjectives, no unresolved placeholders found in spec.md/plan.md/tasks.md/WP files)
- Duplication Count: 0 (no near-duplicate requirements found)
- Critical Issues Count: 0

---

## FR-011 Well-Formedness and Coverage Chain (dedicated check)

**Falsifiable/testable**: Yes. FR-011 (spec.md:380) names the exact crash mechanism (`diagnose.py::_validate_payload`'s unguarded `rules.get("required", set())` / `rules.get("validators", {})` calls at `diagnose.py:301-306`, raising `AttributeError: 'object' object has no attribute 'get'`), the exact fix (recognize the FR-006 sentinel via the shared predicate before any dict-shaped access, delegate to `validate_event()`), and commits to a specific new regression test in `tests/sync/test_diagnose.py` asserting (a) no crash and (b) a real `ConformanceResult`-sourced violation appears in `DiagnoseResult.errors` for an invalid payload. This is not a vague aspiration — it names the failing line, the failure mode, and the acceptance shape.

Live-code verification confirms the premise is accurate as of this HEAD: `diagnose.py:51` imports `_PAYLOAD_RULES, VALID_AGGREGATE_TYPES` from `.emitter` exactly as cited; `diagnose.py:301-306`'s `_validate_payload` does `rules = _PAYLOAD_RULES.get(event_type); if rules is None: return` followed immediately by `rules.get("required", set())` with no further shape guard — precisely the crash FR-011 describes once FR-006 lands the `object()` sentinel. `tests/sync/test_diagnose.py` currently has zero `dossier` hits (grep-confirmed), matching spec.md's claim.

**Scope**: Correctly bounded. FR-011's text is explicitly "Coordinate FR-006's `_PAYLOAD_RULES` sentinel change with `diagnose.py::_validate_payload`" — it does not touch any other `diagnose.py` behavior (event-type recognition, `VALID_AGGREGATE_TYPES`, unrelated error categories). tasks.md's WP02/T010 mirrors this precisely: "Do not add a `_console.print`/`print` call here — that would be a new, inconsistent side channel this function's contract does not have anywhere else."

**NFR-002 consistency**: Confirmed non-contradictory. NFR-002 (spec.md:387) explicitly splits into two independently-scoped contracts: `emitter.py::_validate_payload` prints a `[yellow]Warning: ...` and drops the event (unchanged from today's behavior for every other `_PAYLOAD_RULES` entry); `diagnose.py::_validate_payload` (FR-011) "is a separate function with a different, equally binding visibility contract: it does not print a warning — it surfaces the violation by appending it to `DiagnoseResult.errors`." The spec text itself states "Neither contract weakens or contradicts the other; each governs its own function." WP02's T010 Notes reinforce this by explicitly forbidding introduction of a print statement in `diagnose.py`. No weakening found.

**Coverage chain, end-to-end**: spec.md FR-011 (line 380) -> plan.md: appears in the Red-First/ATDD Test Mapping table (FR-011 row, plan.md:990), the "`diagnose.py` coordinated fix" design section (plan.md:487-554), Phase 3 of Phasing (plan.md:919-946, same-commit requirement), and the Scale/Scope consumer inventory table -> tasks.md WP02 (Requirement Refs: FR-006, FR-007, FR-011; owned_files includes both `src/specify_cli/sync/diagnose.py` and `tests/sync/test_diagnose.py`) -> **T010** (the fix: adds the `is_dossier_delegate()`-guarded branch to `diagnose.py::_validate_payload`, folding violations into the `errors` accumulator) and **T011** (the test: "Add a new test (or a small set) to `tests/sync/test_diagnose.py`... Confirm this test goes red if T010's guarded branch is reverted (locally, temporarily)... Revert your temporary change before finishing").

T011's step 4 is a genuine, real, revert-proof commitment — it is not merely gestured at: it names the concrete file (`tests/sync/test_diagnose.py`, confirmed to be an existing file with zero current dossier coverage), the concrete entry point to drive through (`diagnose_events()`, "do not call `_validate_payload` directly here — exercise the real integration path"), the concrete dual assertion (no-crash AND a real violation string sourced from `ConformanceResult` in `DiagnoseResult.errors`), and an explicit red-first verification step against a temporary local revert of T010's own branch. WP02's Test Strategy section repeats this bar ("Confirm T011's and T012's tests both go red against a temporary local revert of their respective guarded branch... before finishing, per this mission's charter-bound ATDD discipline"), and the Risks & Mitigations section names this exact crash as "the single highest risk in this WP."

**Conclusion: no finding.** FR-011 is well-formed, falsifiable, correctly scoped, consistent with NFR-002, and its coverage chain is real and complete through to a concrete, revert-proof test commitment in `tests/sync/test_diagnose.py`.

---

## General Coverage Invariant (dedicated check)

All 11 FRs (FR-001 through FR-011) map to at least one WP/task — see the Coverage Summary Table above and tasks.md's own "Requirements Coverage Summary" table, cross-verified against each WP prompt's `Included Subtasks` section. No WP invents scope absent from spec.md: WP01's owned files/subtasks map to FR-001..FR-005; WP02's map to FR-006/FR-007/FR-011; WP03's map to FR-008; WP04's map to FR-009/FR-010 (plus a secondary FR-001 identity-proof subtask, T020, explicitly marked "WP01 remains the implementing WP" so this is not scope duplication, just an additional regression assertion added by a later WP against an already-implemented FR).

The queue-drain half of issue #1058 stays confirmed out of scope: grep-verified zero mentions of `sync/queue.py` or `sync/migrate_journal.py` as touched/owned files anywhere across `tasks.md` or any of the four WP files; WP01's prompt (lines 130-134) explicitly lists both paths under "Out of scope, do not touch," citing C-001 and the mission #3293 supersession recorded in spec.md's Clarifications. No WP or task reintroduces queue-drain/migration-transform scope.

**Conclusion: no finding.** The coverage invariant holds and the queue-drain exclusion is honored throughout tasks.md and all four WP files.

---

## Next Actions

No CRITICAL or HIGH findings — this mission's spec/plan/tasks artifacts may proceed to `/implement`. One MEDIUM finding (E1) is a small, mechanical documentation-scope gap (a missing test path in NFR-003's/plan.md's/WP02's declared test-scope enumeration); it does not block implementation but should be folded in before or during WP02 to avoid an implementer under-running their own new tests. Suggested command: manually edit spec.md's NFR-003 row, plan.md's "Testing" line, and WP02's "Test Strategy" scope command to add `tests/sync/test_events.py` to the enumerated list — a single-line addition in each of three files, no re-review of the broader plan/tasks required.
