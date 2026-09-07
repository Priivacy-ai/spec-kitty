---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: fsm-write-path-integrity-01M1TZV6
mission_id: 01M1TZV64BPYQBCST251ECBZ4Z
generated_at: '2026-09-06T14:08:57.737112+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: kitty-specs/fsm-write-path-integrity-01M1TZV6/spec.md
    sha256: 82f022d446ef3083dac27610899f12f54a27454510d1318a26c3b4d3cc99e42b
  plan.md:
    path: kitty-specs/fsm-write-path-integrity-01M1TZV6/plan.md
    sha256: 138dbfcdab26ec6a5150f9cdd6df67d2913c13c42b567fa9790b389aa5246fb2
  tasks.md:
    path: kitty-specs/fsm-write-path-integrity-01M1TZV6/tasks.md
    sha256: 5036585d2d44b52a58de3ffef60831bcc86c61f26e1497133ef6dd13fb61d428
  charter:
    path: .kittify/charter/charter.yaml
    sha256: cded0cf700d030b6f13d6c6f58d237e371ec41e0b874ca2630dcf234dd695fdf
verdict: ready
issue_counts:
  critical: 0
  high: 0
  medium: 5
  low: 5
  info: 0
findings:
- id: I1
  severity: medium
  category: inconsistency
  summary: "WP03's _unsafe allowlist gate has a bypass: coordination/transaction.py (boundary-test exempt) imports status.store.append_event_stream_log directly and would never appear as an _unsafe importer; that primitive is also missing from the six-name list."
- id: I2
  severity: medium
  category: inconsistency
  summary: WP04's fail-open polarity is argued sound 'because after WP03 no durable write bypasses the shells', but WP04 depends only on WP06, not WP03; the soundness precondition is not encoded as a dependency.
- id: I3
  severity: medium
  category: inconsistency
  summary: WP01 T006 requires one-line edits in status/emit.py and coordination/transaction.py (owned by WP02/WP06) while WP01 and WP02 run in parallel in wave 0; a merge conflict on emit.py is likely unless WP01 merges first.
- id: I4
  severity: medium
  category: inconsistency
  summary: "spec.md still carries ten '[NEEDS DECISION: Q1..Q10]' markers and FR-018/FR-007 'placement per Q1'/'default per Q5' language although all ten are resolved or deferred in decisions/ and plan.md."
- id: I5
  severity: medium
  category: inconsistency
  summary: spec.md C-008 and US2-3 name four 'plain-door callers' that research.md D-1 shows are docstring mentions only (zero production plain-door callers outside the fallback arms); the spec rationale is stale though the pin remains valid.
- id: U1
  severity: low
  category: underspecification
  summary: NFR-003 requires 'a finite timeout' without a bound or source; tasks T007 pins it to the existing _in_queue_status_lock_timeout pattern, but the spec does not.
- id: U2
  severity: low
  category: underspecification
  summary: data-model.md §5 states 'exactly two shell kinds exist' while its table lists three rows (the coord fallback arm is a mode of the flat shell, not a third shell); wording invites a third-shell reading.
- id: C1
  severity: low
  category: coverage
  summary: NFR-005 (test discipline) is mapped only to WP06 and C-010 only to WP01, although both bind every WP; coverage is real (every prompt has a Test Strategy) but the mapping under-reports it.
- id: A1
  severity: low
  category: ambiguity
  summary: "spec.md header still reads 'Status: Draft (proto-mission — no plan.md or tasks yet)' after plan and tasks exist."
- id: A2
  severity: low
  category: ambiguity
  summary: quickstart.md WP01 blast radius cites tests/status/test_locking*.py, which matches no file until T006 creates test_locking_key.py.
---

## Specification Analysis Report

Mission `fsm-write-path-integrity-01M1TZV6` · re-recorded after remediation at commit `7327a9acc` (I1, I2, I3 applied: WP03 gate scope widened to boundary-exempt store importers; WP04 now depends on WP03; tasks.md states WP01-before-WP02 merge order) · original analysis at `e5c36116c` · Re-recorded (3) at `40814f570` after `plan.md` changed only by the Q6/Q9 `[NEEDS CLARIFICATION]` marker removals made by WP02/WP05 (decisions resolved via the CLI); no finding changed · Re-recorded (4) after WP07 (writer-census addendum for the two writers WP03's gates found: `decisions/emit.py:100-112`, `migration/rebuild_state.py:758-766`) was minted into tasks.md; coverage of FR-001/FR-002/NFR-001 now WP01+WP07; 42 subtasks in 7 WPs (spec `27a40ee90`, plan `31151eea8`/`065c25211`, tasks `e5c36116c`) · charter `.kittify/charter/charter.md` loaded.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Inconsistency | MEDIUM | tasks/WP03 T015–T017; contracts/write-gates.md §1; `src/specify_cli/coordination/transaction.py:36` | The allowlist gate scans for importers of `status._unsafe`. `transaction.py` is exempt from `test_status_module_boundary.py` and imports `status.store.append_event_stream_log` directly — it never becomes an `_unsafe` importer, so the gate cannot see it; the primitive is also absent from the six-name list. Any other boundary-exempt module could do the same. | In WP03 T017, extend the scan to treat direct `specify_cli.status.store` imports of any `append_*` primitive from outside `status/` as `_unsafe` importers (or repoint `transaction.py` to `_unsafe` and add `append_event_stream_log` to the re-export list). State this in the WP03 prompt. |
| I2 | Inconsistency | MEDIUM | tasks.md WP04 Dependencies; tasks/WP04 frontmatter `dependencies: ["WP06"]`; spec C-004 | Fail-open on `None` is sound only once WP03's gates guarantee no durable write bypasses the shells. WP04 can merge before WP03 under the current graph. | Add `WP03` to WP04's dependencies (`["WP03","WP06"]`) and re-run `finalize-tasks`; or record explicitly that soundness is a mission-completion condition, not a WP04 exit criterion. |
| I3 | Inconsistency | MEDIUM | tasks/WP01 T006 step 2; tasks/WP02 Context ("WP01 touches emit.py:634"); plan.md Parallel Work Analysis ("disjoint owned files — verified") | FR-004 forces the lock-key argument change at `emit.py:634` and `transaction.py:290`, both outside WP01's owned files, while WP01 ∥ WP02 in wave 0. The plan's "disjoint" claim is false for that one line. | Keep the out-of-map leeway but make the merge order explicit in tasks.md (WP01 merges before WP02 rebases), or move the two one-line lock-argument hunks into WP02 (which then keys on `feature_dir.name` itself, as its prompt already allows). |
| I4 | Inconsistency | MEDIUM | spec.md "Open Decisions" §, FR-007, FR-018, US5 "open decision Q10" | All ten Q markers are resolved/deferred in `decisions/` and `plan.md`, but the spec still presents them as open. Implementers reading the spec first will re-open settled questions. | On the next spec touch, replace each marker with a one-line "Resolved: … (decision `<id>`)" and drop the "placement per Q1"/"default per Q5" hedges. Not blocking: plan.md is the binding record. |
| I5 | Inconsistency | MEDIUM | spec.md C-008, US2-3, WP02 slicing row; research.md §3 D-1 | Verified at HEAD: `contracts/anchoring.py`, `dossier/rebaseline.py`, `runtime_bridge_composition.py` mention the plain door only in docstrings; `verdict_provenance_backfill.py` calls the raw store primitive (census family ⑥). Production plain-door callers outside the coordination fallback arms: zero. The C-008 pin (SC-007) stays valid via `_fallback_emit_single._primary`. | On next spec touch, rewrite C-008's rationale to cite the fallback arm. WP06 T033 already encodes the corrected rationale. |
| U1 | Underspecification | LOW | spec.md NFR-003, FR-003(b) | "finite timeout" has no bound or source in the spec. | Accept T007's pin to `_in_queue_status_lock_timeout` (or the lifted `bounded_status_lock_timeout`); record the chosen value in WP01's design note. |
| U2 | Underspecification | LOW | data-model.md §5 | Three table rows under "exactly two shell kinds". | Reword the third row as "coord fallback arm (a mode of the flat shell with fan-out suppressed)". |
| C1 | Coverage | LOW | tasks.md Requirements Coverage Summary | NFR-005 → WP06 only; C-010 → WP01 only. | Optional: map both to all six WPs via `map-requirements` so the coverage table reflects the real binding. |
| A1 | Ambiguity | LOW | spec.md:L5 | Stale status line. | Update on next spec touch. |
| A2 | Ambiguity | LOW | quickstart.md per-WP table | Glob matches nothing pre-T006. | Cosmetic; resolves itself when WP01 lands. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 writer-census-governed | Yes | T008 | comment re-label + design note |
| FR-002 lock-and-atomic-append-unlocked-writers | Yes | T002, T003, T004, T005 | |
| FR-003 three-lock-rules-encoded | Yes | T007, T008 | rules (a)(b)(c) |
| FR-004 uniform-lock-key | Yes | T006 | |
| FR-005 layered-pipeline-extraction | Yes | T009, T010, T011, T014 | |
| FR-006 converge-three-orchestrations | Yes | T034, T035, T037, T039 | |
| FR-007 batch-effective-root-parity | Yes | T032, T035 | |
| FR-008 fan-out-unification | Yes | T031, T036 | |
| FR-009 minimal-doc-correction | Yes | T038 | |
| FR-010 facade-strip-unsafe | Yes | T015, T016 | see I1 |
| FR-011 ast-writes-gate | Yes | T018 | |
| FR-012 readiness-tri-state-guard | Yes | T020, T021 | |
| FR-013 in-lock-resolution | Yes | T022, T023 | |
| FR-014 reuse-and-demote | Yes | T025 | |
| FR-015 atomic-run-cursor | Yes | T029 | |
| FR-016 mission-id-keyed-index | Yes | T026, T027, T028 | |
| FR-017 pure-progress-read | Yes | T030 | |
| FR-018 batch-door-lock | Yes | T012 | |
| NFR-001 no-lock-across-git | Yes | T002–T005 (design constraint), T008 note | |
| NFR-002 replay-purity | Yes | T024 | |
| NFR-003 bounded-lock-waits | Yes | T007 | see U1 |
| NFR-004 emit-cost-preserved | Yes | T013 | |
| NFR-005 test-discipline | Yes | every WP Test Strategy; T039 | see C1 |
| C-001..C-010 | Yes | per tasks.md coverage table | C-008 rationale: see I5 |
| Edge cases (8) | Yes | T031/T036, T024, T006, T024, T007, T033, T017/T018, T002 | all eight mapped |

**Charter Alignment Issues:** none. Single canonical authority (Q4 decision), architectural alignment (pipeline in `status/`, no new `status→coordination` reach), ATDD-first (RED-first per WP), decision documentation (10 records + ADR amendment task T038), close-defect-class-by-construction (gates + non-vacuity), terminology canon (Mission/WP/lane; tool-generated commit messages say "feature" — tool wording, not artifact wording, ledgered separately).

**Unmapped Tasks:** none (39 subtasks, each under exactly one WP with requirement refs).

**Metrics:**

- Total Requirements: 18 FR + 5 NFR + 10 C = 33 (+ 8 edge cases)
- Total Tasks: 42 subtasks in 7 WPs (WP sizes 5/8/6/5/6/9/3; prompts 119–232 lines)
- Coverage %: 100 % (every FR/NFR/C has ≥1 task)
- Ambiguity Count: 2 (A1, A2) + 2 underspecification (U1, U2)
- Duplication Count: 0
- Critical Issues Count: 0

## Next Actions

No CRITICAL or HIGH findings: implementation may proceed. The three recommended pre-dispatch remediations below were APPLIED in commit `7327a9acc` (findings kept in the table for traceability):

1. **I2** — add `WP03` to WP04's `dependencies` and re-run `spec-kitty agent mission finalize-tasks --mission fsm-write-path-integrity-01M1TZV6 --json`.
2. **I1** — add the boundary-exempt-importer rule to WP03 T017 and `append_event_stream_log` to T015's re-export list.
3. **I3** — add "merge order: WP01 before WP02 rebases" to tasks.md's Dependency & Execution Summary.

I4, I5, A1 are spec-text staleness; fold them at the next spec touch (spec is committed; the plan and decision records are binding). U1/U2/C1/A2 are cosmetic.
