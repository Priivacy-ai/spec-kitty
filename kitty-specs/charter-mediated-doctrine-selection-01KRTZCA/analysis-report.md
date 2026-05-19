# Specification Analysis Report — Charter-Mediated Doctrine Selection (Mission B)

> Mission: `charter-mediated-doctrine-selection-01KRTZCA`
> Mission ID: `01KRTZCA58EM8RFPVDHYBZQSF8`
> Run date: 2026-05-17
> Branch: `feat/org-doctrine-layer`
> Analyser protocol: `/spec-kitty.analyze` (6-step)

This report is the cross-artifact consistency check across `spec.md`, `plan.md`, `tasks.md`, and the 4 contract files, with the project charter (`.kittify/charter/charter.md`) treated as non-negotiable per the analyzer's charter authority rule.

---

## 1. Inputs Loaded

| Source | Sections consulted |
|--------|-------------------|
| `spec.md` | Overview, 5 User Journeys, Domain Language (10 terms), 18 FRs, 6 NFRs, 7 Constraints, Goals, Non-Goals, 8 Acceptance Criteria |
| `plan.md` | Architectural design, Component changes, Sequencing & risks, Test strategy, Plan-time decisions |
| `data-model.md` | All 10 sections covering schema extensions, activation registry, mission-type profile, trigger registry, facade modules |
| `contracts/*.md` | 4 contract files |
| `tasks.md` + 9 WP files | 51 subtasks, dependency graph, ATDD mappings per WP |
| `.kittify/charter/charter.md` | Technical standards, architecture, testing requirements |
| 7 ATDD test files at `bd95f1f5` | The canonical executable spec |

---

## 2. Findings

### 2.1 Detection Pass Summary

| Pass | Findings |
|------|----------|
| Duplication | 1 (LOW) |
| Ambiguity | 2 (MEDIUM, LOW) |
| Underspecification | 1 (LOW) |
| Charter Alignment | 0 |
| Coverage Gaps | 0 |
| Inconsistency | 2 (MEDIUM x 2) |

### 2.2 Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Inconsistency | MEDIUM | plan.md sec 2.10; data-model.md sec 5, sec 7; contracts/activation-registry.md note | The relationship between `ALLOWED_ACTIONS` (10 entries, vocabulary for `activation_context.action`) and `_REGISTERED_TRIGGERS` (15 entries, vocabulary for artifact `triggers:` blocks) is documented in three places with slightly different framings. Risk of drift if one is updated without the others. | Add a single canonical paragraph in data-model.md sec 7 cross-linking the two sets and the `_REGISTERED_TRIGGERS = ALLOWED_ACTIONS UNION {4 fine-grained tokens}` formula. Other locations reference this section. (Documentation-only.) |
| I2 | Inconsistency | MEDIUM | plan.md sec 2.9 says WP07 owns "13 runtime files"; tasks.md WP07 covers 14 paths (13 files + new `src/kernel/schema_utils.py`); spec.md FR-013 says "13 runtime files"; the `_BASELINE_ALLOWLIST` carries exactly 13 entries | The "13 files" count is consistent (matches the allowlist), but readers may briefly confuse the 14 paths in WP07's owned_files (13 migrate + 1 new kernel module) with the file-count. | Minor clarification in WP07 description: "13 baseline files migrate + 1 new `kernel/schema_utils.py` lands as part of the SchemaUtilities promotion (T040)." |
| D1 | Duplication | LOW | tasks.md "Definition of Done" mapping vs. WP file "Definition of Done" sections | ATDD mapping appears in both tasks.md (summary) and the WP file (detail). Intentionally redundant for traceability but easy to drift. | Acceptable. tasks.md summary could reference WP file as source of truth. Cosmetic - leave for follow-up. |
| A1 | Ambiguity | MEDIUM | plan.md sec 2.10 decides initial trigger registry of 15 tokens. `_REGISTERED_TRIGGERS` lives in `tests/architectural/test_trigger_registry_coverage.py` per its own docstring. WP05 T024 says "Re-export from charter.activations for runtime consumers if needed". | The single source of truth for the trigger registry is left as "test file with optional runtime re-export". An implementer might create two divergent copies. | Pin the SSOT explicitly in data-model.md sec 7: the test file `_REGISTERED_TRIGGERS` is canonical; `charter.activations.REGISTERED_TRIGGERS` (if added) MUST stay in lockstep via cross-check architectural test. |
| A2 | Ambiguity | LOW | contracts/mission-type-profile.md "Hard-fail on unknown mission type" - exception class stated as "implementation detail (`ValueError` subclass acceptable)" | Implementation team must pick; ATDD only asserts message contains unknown value. | Acceptable - the ATDD is permissive and the recommendation in plan.md sec 2.7 is `UnknownMissionTypeError` (ValueError subclass). |
| U1 | Underspecification | LOW | tasks.md WP09 T050 - "Extend `spec-kitty doctor doctrine` with Selections section" - exact data source left vague | A reviewer cannot mechanically verify without running the command. | Add to WP09: doctor command MUST snapshot-test the Selections section format against a known fixture. Already in WP09 owned_files. |

---

## 3. Coverage Summary

All 18 FRs + 6 NFRs + 7 Cs = 31 requirements have at least one WP. 0 unmapped tasks. Highlights:

- FR-001 -> WP01 (T001), gate: `test_artifact_selection_completeness.py`
- FR-002 -> WP06 (T002), gate: same arch test
- FR-003 -> WP06 (T026), gate: `test_case_2_required_styleguides_in_org_charter_pre_fills`
- FR-004 -> WP02 (T006), gate: `test_case_1_selected_styleguides_field_round_trips`
- FR-005 -> WP04 (T017-T021), gate: `test_case_1_project_styleguide_appears_in_implement_prompt`
- FR-006 -> WP01 (T003) + WP02 (T007), gate: `test_activation_registry_schema.py` (4 tests)
- FR-007 -> WP04 (T023 wires) + WP05 (T022 renderer), gate: `test_case_1_styleguide_render_includes_trigger_stanza`
- FR-008 -> WP06 (T028)
- FR-009 -> WP05 (T024), gate: `test_trigger_registry_coverage.py`
- FR-010 -> WP08 (T042-T045), gate: `test_mission_type_ships_governance_profile_yaml` x4
- FR-011 -> WP08 (T046, T047), gate: `test_resolve_governance_*` x2
- FR-012 -> WP03 (T010-T016), gate: new `test_charter_facades_reexport_doctrine.py`
- FR-013 -> WP07 (T032-T040), gate: `test_runtime_charter_doctrine_boundary.py` (allowlist shrinks)
- FR-014 -> WP06 (T029), gate: `test_case_2_org_styleguide_collision_with_builtin_warns`
- FR-015 -> WP06 (T030), gate: `test_case_2_consumer_without_fetched_pack_fails_loudly`
- FR-016, FR-017, FR-018 -> WP09 (T048-T050)
- NFR-001 to NFR-006 -> distributed gates (latency, layer, ATDD, glossary)
- C-001 to C-007 -> distributed; C-005 resolved in plan sec 2.10; C-006 in WP06/WP09; C-007 in WP09

Coverage: 100% (31/31).

---

## 4. Charter Alignment

Reviewed `.kittify/charter/charter.md` against mission deliverables.

| Charter principle | Mission alignment |
|-------------------|-------------------|
| Python 3.11+ | Pydantic v2, typer, ruamel.yaml - all current stack |
| pytest 90%+ coverage | Each WP includes unit tests; ATDD is integration coverage |
| mypy --strict | Pydantic models typed; facades pure re-exports |
| CLI < 2 seconds | NFR-002 sets 1.5x baseline |
| Cross-platform | All new code is pathlib + ruamel.yaml |
| Shared package boundary | Mission does NOT touch spec_kitty_events / spec_kitty_tracker |
| C-001 layer rule | Mission tightens this rule. Honoured throughout WP03/WP07. |

No charter violations. All MUST-level principles upheld.

---

## 5. Unmapped Tasks

None. Every subtask T001-T051 maps to a WP and a requirement.

---

## 6. Metrics

| Metric | Value |
|--------|-------|
| Total FRs | 18 |
| Total NFRs | 6 |
| Total Constraints | 7 |
| Total WPs | 9 |
| Total subtasks | 51 |
| Coverage % | 100% |
| Ambiguity Count | 2 (1 MEDIUM, 1 LOW) |
| Duplication Count | 1 (LOW) |
| Inconsistency Count | 2 (MEDIUM) |
| Underspecification Count | 1 (LOW) |
| Critical Issues | 0 |
| Charter Violations | 0 |
| Lane Count (from finalize) | 2 |
| ATDD Test Files Pinned | 7 |
| ATDD Assertions to Turn Green | 29 |
| Boundary Allowlist Final Cap | <= 2 (per C-004) |

---

## 7. Next Actions

No CRITICAL or HIGH findings. Mission is READY FOR IMPLEMENTATION.

Optional pre-implementation touch-ups (LOW/MEDIUM):

1. ~~I1 / A1 - Tighten trigger-registry SSOT story in data-model.md sec 7.~~ **Resolved in `be6b1c53` (2026-05-17)** — see §9.
2. ~~I2 - Clarify the WP07 file count in tasks.md ("13 migrate + 1 new = 14 paths").~~ **Resolved in `be6b1c53` (2026-05-17)** — see §9.
3. ~~U1 - Pin the doctor doctrine Selections format with a snapshot test (already in WP09 owned_files).~~ **Resolved in `be6b1c53` (2026-05-17)** — see §9.
4. D1 - Cosmetic; defer to follow-up. *(Only remaining touch-up.)*

Suggested next command:

```
spec-kitty agent action implement WP01 --agent claude
```

---

## 8. Verdict

READY FOR IMPLEMENTATION. Mission is internally consistent, charter-aligned, and fully covered by 9 WPs / 51 subtasks. The 7-file ATDD suite at bd95f1f5 is the executable acceptance gate, and every assertion is mapped to a specific WP. Lane decomposition produced a clean 2-lane dependency graph (lanes.json).

The 4 findings above are quality-of-life touch-ups, not blockers. Three (I1+A1, I2, U1) were applied pre-implementation; see §9 for the resolution log. D1 remains as a cosmetic follow-up.

---

## 9. Drift-Risk Resolution Log

**Date:** 2026-05-17
**Resolution commit:** `be6b1c53169536659d8c62a215f8312fb87ddbbb` (`be6b1c53`)
**Branch:** `feat/org-doctrine-layer`

### I1 + A1 — Trigger registry SSOT consolidation

**Changes:**
- `data-model.md` §7 rewritten as the **canonical definition** for both `_ALLOWED_ACTIONS` (10 tokens) and `_REGISTERED_TRIGGERS` (15 tokens). Includes the union formula `_REGISTERED_TRIGGERS = _ALLOWED_ACTIONS ∪ {write_comment, write_docstring, rename_identifier, add_dependency}` exactly once.
- `data-model.md` §5 collapsed to a one-line pointer to §7.
- `plan.md` §2.10 collapsed to a one-line pointer to §7.
- `contracts/activation-registry.md` "Note on Trigger Registry" section collapsed to a one-line pointer to §7.
- `src/charter/activations.py` runtime re-export upgraded from **optional** to **MANDATORY** (per data-model.md §7 contract).
- New architectural cross-check test `test_trigger_registry_runtime_export_in_sync` (lives in `tests/architectural/test_trigger_registry_coverage.py`) added to WP05's deliverables — asserts byte-identical equality between the canonical frozensets and the runtime re-exports.
- WP05 subtasks updated: T024 rewritten to mark re-export MANDATORY; new T024a explicitly scopes the cross-check test as a deliverable.
- WP05 frontmatter `owned_files` extended with `src/charter/activations.py`; `subtasks` extended with T024a.
- WP05 Definition of Done cites the new cross-check test.

**Verification:** `rg "= _ALLOWED_ACTIONS \\| frozenset\\(\\{"` returns exactly two hits — `data-model.md` §7 (canonical) and `WP05` (implementation reference that points back to §7). All other locations reference §7 via a hyperlink pointer.

### I2 — WP07 file count clarity

**Changes:**
- `tasks/WP07-...md` Context section gains an explicit "Scope clarification" paragraph: 13 migrating runtime files + 1 new `src/kernel/schema_utils.py` = 14 paths touched, allowlist counts 13.
- `tasks.md` WP07 summary cell appends "13 migrate + 1 new = 14 paths" parenthetical.
- `plan.md` §2.9 appends a parenthetical noting the new kernel module and that the allowlist still counts 13.

### U1 — `doctor doctrine` Selections snapshot test

**Changes:**
- `tasks/WP09-...md` T050 gains an explicit Definition-of-Done clause requiring a snapshot test at `tests/cli/test_doctor_doctrine_selections_snapshot.py` with snapshot file `tests/cli/__snapshots__/doctor_doctrine_selections.txt`. Snapshot scope (multi-source kind, empty kind, exact provenance suffix) pinned in the task body.
- WP09 frontmatter `owned_files` extended with both the test file and the snapshot file.
- WP09 Definition of Done cites the new snapshot test.

### D1 — Cosmetic ATDD-mapping duplication (intentionally deferred)

No action. Per analyzer recommendation: acceptable redundancy for traceability; defer to a follow-up cosmetic pass.
