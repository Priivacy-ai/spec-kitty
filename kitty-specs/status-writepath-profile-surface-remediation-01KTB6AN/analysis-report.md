# Specification Analysis Report

Cross-artifact consistency analysis (`/spec-kitty.analyze`) over `spec.md`, `plan.md`, `tasks.md` (+ `data-model.md`, `research.md`) for mission `status-writepath-profile-surface-remediation-01KTB6AN`. Read-only; date 2026-06-05.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| I1 | Inconsistency / Charter (DIR-032) | HIGH | spec.md FR-019; tasks WP04↔WP06 | FR-019 requires the *abstract base profile* vocabulary to land **before** the `profile show` warning string ships, but WP06 (glossary, FR-019) **depends on** WP04 (warning string, FR-015) — so the user-facing term is introduced in code before the glossary defines it. Vocab-before-code is inverted at WP granularity. | Move the glossary subtask (T029) ahead of WP04: into the dependency-free WP03, or a new glossary-first WP that WP04 depends on. Requires re-`finalize-tasks` (lane recompute) → **needs approval**. |
| C1 | Coverage gap | MEDIUM | spec.md NFR-003; tasks (none) | NFR-003 ("no `runtime/next` activation regression") has no task or review checkpoint. WP03/WP04 change the activation path `runtime/next` already consumes. | Add an NFR-003 review checkpoint to WP03/WP04 ("existing `runtime/next` profile-resolution tests stay green"). Body-only edit (no re-finalize). |
| N1 | Inconsistency (dangling ref) | MEDIUM | spec.md:27 | "one **design note** records the profile-activation gating decision (see **Contracts §B**)" — but the Contracts appendix (incl. §B) was replaced by a pointer to plan/data-model; §B no longer exists. | Repoint to `data-model.md` / `plan.md` D-2. |
| S1 | Inconsistency (staleness) | LOW | spec.md Source Issues (#1667 row) | "closes the **untested**/unwired write path (RISK-001)" — the *untested* half shipped in PR #1682; only *unwired* remains. | Drop "untested"; note coverage shipped in #1682. |
| S2 | Inconsistency (staleness) | LOW | spec.md Scenario A/B | Scenarios describe the aggregate write methods *having unit coverage* — already true (#1682). The mission's Lane-A work is the **wiring** (FR-004), not the coverage. | Reframe A/B around the wired surface, or annotate as already-satisfied acceptance behavior. |
| A1 | Ambiguity | LOW | tasks WP01 T002; spec FR-004 | FR-004's `.save()` usage is conditional ("where the command relies on the transactional commit"); T002 leaves "does the command need `ms.save()`?" as an in-task investigation. | Acceptable (the task flags it) — implementer resolves by inspecting the current commit path; no change required. |

No CRITICAL findings. No duplications. No unmapped tasks. No charter MUST violations beyond the I1 ordering smell.

## Coverage Summary

| Requirement | Has Task? | Task IDs / WP | Notes |
|-------------|-----------|---------------|-------|
| FR-004 (wire write surface) | ✅ | WP01 / T001-T002, T005-T006 | |
| FR-007 (slug guard) | ✅ | WP01 / T003-T004 | DIR-010/011 accented case covered |
| FR-008 (ratchet write path) | ✅ | WP02 / T007-T010 | dep WP01 |
| FR-010 (factory) | ✅ | WP03 / T011-T012 | |
| FR-011 (list filter) | ✅ | WP04 / T015, T020 | NFR-001 byte-identity tested |
| FR-012 (--all/--show-available) | ✅ | WP04 / T016 | |
| FR-013 (show render) | ✅ | WP04 / T017 | |
| FR-014 (show gate) | ✅ | WP04 / T018, T021 | |
| FR-015 (lineage Option A) | ✅ | WP04 / T019, T021-T022 | |
| FR-016 (include gate) | ✅ | WP05 / T023-T026 | |
| FR-017 (skill reconcile) | ✅ | WP06 / T027, T030-T031 | |
| FR-018 (parity guard) | ✅ | WP06 / T028 | dep WP04 |
| FR-019 (glossary) | ✅ | WP06 / T029 | **ordering issue I1** |
| NFR-001 (list byte-identity) | ✅ | WP04 / T020 | |
| NFR-002 (no transaction.py change) | ✅ | WP01 constraint / review guidance | negative constraint |
| NFR-003 (no runtime/next regression) | ❌ | — | **gap C1** |
| NFR-004 (show --json stable) | ✅ | WP04 / T017 | |

## Charter Alignment

- DIR-010/011 (ASCII identifier safety): ✅ FR-007 + T004.
- DIR-032 (conceptual alignment / vocab-before-code): ⚠️ I1 — glossary ordered after the code that uses the term.
- No conflict with the governing 3.x ADRs (Status owned by Mission Management; the FR-004 wiring *reinforces* it).

## Unmapped Tasks

None — every subtask rolls up to a WP with mapped FRs.

## Metrics

- Functional requirements: **13** · Non-functional: **4**
- Work packages: **6** · Subtasks: **31**
- FR coverage: **100%** (13/13) · NFR coverage: **75%** (3/4 — NFR-003 gap)
- Duplication: 0 · Ambiguity: 1 (low) · Critical: 0 · High: 1

## Next Actions

- **Before `/implement`**: resolve **I1** (HIGH) — reorder the glossary so vocabulary precedes the warning-string code (re-finalize required) — and close **C1** (NFR-003 checkpoint).
- Safe doc fixes (N1, S1) applied in the accompanying commit (no structural change).
- Then proceed to `/spec-kitty-implement-review`.
