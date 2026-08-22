---
description: "Work package task list for M5 — Canonical mission-type reader"
---

# Work Packages: M5 — Canonical mission-type reader

**Inputs**: Design documents from `/kitty-specs/rc3-canonical-mission-type-reader-01M0GGWM/`
**Prerequisites**: plan.md (required), spec.md, research.md (re-grounded census)

**Tests**: Red-first. The FR-010 structural invariant test is the gate; per-reader regression pins precede each converter.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). File ownership is disjoint across WPs; cross-mission same-file coordination (M6, M8) is honored per-symbol.

## Path Conventions

- **Single project**: `src/`, `tests/`

---

## Work Package WP01: Shared canonical reader seam + M3↔M5 reconciliation + red gate (Priority: P0)

**Goal**: Introduce the one `read_mission_type(meta) -> str | None` authority; make the CLI and charter readers delegate to it; author the FR-010 structural gate red.
**Independent Test**: `read_mission_type` unit table passes; `_canonical_meta_mission_type` and the charter path return identical results to it; `test_layer_rules.py` still green; FR-010 structural test exists and is red against the not-yet-converged readers.
**Prompt**: `/tasks/WP01-shared-reader-seam.md`
**Requirement Refs**: FR-001, FR-004, FR-010 (skeleton)

### Included Subtasks

T001 Add `read_mission_type(meta: dict) -> str | None` beside `canonical_mission_type_key` in `src/charter/mission_type_key.py` (reads `mission_type` → `canonical_mission_type_key` → `None`; no legacy `mission`; no default); export in `__all__`
T002 Unit table for `read_mission_type` in `tests/charter/` (canonical, blank, absent, non-string, legacy-only-does-not-resolve)
T003 Collapse `_canonical_meta_mission_type` (`src/specify_cli/mission.py:542`) to a thin delegate; **drop the legacy `mission` read**
T004 Route charter `_read_meta_mission_type`/`_resolve_type_key` (`src/charter/mission_type_profiles.py`) so field-extract+canon delegates to `read_mission_type(dict)` (M3↔M5 shared authority; behavior-parity, no change)
T005 [P] Author FR-010 structural invariant test in `tests/architectural/` (`pytestmark`; table of in-scope readers asserting parity + source-scan for `software-dev` fallback / legacy `mission` read, encoded allow-list) — RED first
T006 [P] Confirm `tests/architectural/test_layer_rules.py::test_charter_does_not_import_specify_cli` stays green (AC-4)

### Dependencies

- None (foundation).

### Risks & Mitigations

- Charter path is already canonical-only (M3) → this is a parity refactor; pin byte-parity, not a behavior change.
- Dead-symbol / golden-count gates → keep `__all__` correct; no bare `len(x)==N` in new tests.

---

## Work Package WP02: Runtime READ converters — legacy + default drop (Priority: P0)

**Goal**: Route every in-scope runtime **read** through the seam, dropping legacy `mission` and silent `software-dev`, one reader per test-pinned step. Includes the FR-005 dashboard visible change.
**Independent Test**: Each converted reader returns `read_mission_type(meta)` for the same dict; dashboard shows `research` for `{"mission_type":"research"}` and typeless for `{"mission":"software-dev"}`-only; FR-010 rows for these readers go green.
**Prompt**: `/tasks/WP02-runtime-read-converters.md`
**Requirement Refs**: FR-002, FR-003, FR-005, FR-006

### Included Subtasks

T007 Convert `dashboard/handlers/features.py:68` to the helper (FR-005) + regression pin (visible change: `research` shown; legacy-only → typeless)
T008 [P] Convert `mission_metadata.py:255` read path (drop legacy + default); classify `:216` build path as create-time write-boundary (documented, retained)
T009 [P] Convert `retrospective/generator.py:1319` (drop default) — own only `:1319` (M8 owns `:271`)
T010 [P] Convert `context/resolver.py:94` (drop legacy read)
T011 [P] Convert `verify_enhanced.py:28/31` (drop legacy read)
T012 [P] Convert `dashboard/diagnostics.py:31/34` (drop legacy read)
T013 [P] Route `retrospective/reader.py:312` & `writer.py:408` for parity (already canonical-only)
T014 Per-reader regression pins for T007–T013

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- Caller boundaries expecting a concrete default must tolerate typeless (`get_mission_type` precedent) — inspect each caller's degrade path.
- Dashboard/retrospective are user-visible → changelog lines in WP05; regression pins here.

---

## Work Package WP03: Write/echo/audit boundaries + FR-009 exemption allow-list (Priority: P1)

**Goal**: Classify the non-read sites — converge the field set where they echo legacy, exempt-with-rationale the create/inference writers, interview payload, and the field-aware audit tool; encode the FR-009 inline-migration exemptions.
**Independent Test**: `mission_create.py` echo drops legacy `mission`; the audit tool stays field-aware (its legacy-only bucket test passes); `inline_meta_read_allowlist.yaml` exists and the FR-010 source-scan consumes it; frozen-migration fixtures replay byte-exact.
**Prompt**: `/tasks/WP03-write-boundaries-and-allowlist.md`
**Requirement Refs**: FR-002, FR-006, FR-009

### Included Subtasks

T015 Converge the field set of `cli/commands/agent/mission_create.py:374` echo to canonical-only (drop legacy `mission` echo) + pin
T016 [P] Classify `upgrade/feature_meta.py` `infer_mission` (inference-on-upgrade write); document default disposition + pin
T017 [P] Confirm `charter/interview.py:225` reads the interview payload (`self.mission`), not `meta.json`; encode as exempt-with-rationale
T018 [P] Keep `cli/commands/_mission_type_audit.py` field-aware (census/audit tool); encode allow-list entry with rationale
T019 Create `inline_meta_read_allowlist.yaml` with FR-009 exemptions: `m_0_13_0_research_csv_schema_check.py` (historical legacy read, #2477), `m_0_13_5` (`mission_name`, different field), `migration/mission_state.py:1617` (frozen backfill write) — each with cited rationale
T020 Replay-equivalence check (or exemption) for the frozen-migration sites; no silent path-exclude

### Dependencies

- Depends on WP01 (allow-list consumed by the FR-010 gate from WP01/T005).

### Risks & Mitigations

- Over-converging a write/inference path could drop a legitimately-needed create-time default → keep writers as writers.
- Frozen-migration replay drift → default to encoded exemption where equivalence can't be guaranteed.

---

## Work Package WP04: Fold #2901 — WP-frontmatter tolerant reader (residual) (Priority: P2)

**Goal**: Route the residual divergent WP-frontmatter site(s) through the landed `status/wp_metadata.py` tolerant reader; pin the already-routed consumers.
**Independent Test**: `audit/classifiers/wp_files.py` classification comes from the tolerant reader; parity assertion pins `bootstrap.py`/`indexer.py`/`scan.py`; the #2884 B3 "incomplete import reported as success" case stays closed.
**Prompt**: `/tasks/WP04-wp-frontmatter-fold.md`
**Requirement Refs**: FR-008

### Included Subtasks

T021 Route `audit/classifiers/wp_files.py:58` through the `status/wp_metadata.py` tolerant reader (own only the WP-frontmatter reader; M6 owns `_TERMINAL_LANES:16`)
T022 [P] Evaluate `mission_v1/guards.py` `_read_lane_from_frontmatter` — route if it duplicates the tolerant classification, else document why exempt
T023 [P] Parity/regression pin asserting `bootstrap.py`, `dossier/indexer.py`, `sync/history_import/scan.py` share the tolerant reader's classification (the landed consumers)

### Dependencies

- None (independent; WP-frontmatter domain, not the mission-type seam).

### Risks & Mitigations

- Scope creep into `review/prompt_metadata.py` (review prompts, not WP frontmatter) — explicitly out of scope.
- Verify-first: three consumers already landed; do not rebuild.

---

## Work Package WP05: FR-007 verify-and-sequence + ADR + changelog + gate closeout (Priority: P1)

**Goal**: Verify M0's backfill covers legacy→`mission_type` (AC-5); author the legacy-retirement ADR and the per-surface `[Unreleased]` changelog; tighten the FR-010 gate to fully green.
**Independent Test**: AC-5 backfill test passes (or reuses M0's); ADR present and names the M3 compounding + M0-first sequencing; changelog has a line per visible surface; FR-010 structural gate fully green; `tests/architectural/test_no_legacy_terminology.py` green.
**Prompt**: `/tasks/WP05-backfill-adr-changelog.md`
**Requirement Refs**: FR-007, FR-010 (final)

### Included Subtasks

T024 Verify `backfill-mission-type` maps legacy `mission`→`mission_type` and `needs_manual_resolution` never manufactures an M3-breaker (AC-5); document the `backfill-identity` gap. **No new backfill.**
T025 Author `docs/adr/3.x/…-canonical-mission-type-reader-legacy-retirement.md` (blast radius; M3↔M5 compounding: silently-resolving → typeless (M5) → hard-fail (M3); M0-backfill-first sequencing)
T026 [P] `CHANGELOG.md` `[Unreleased]` entries per user-visible surface (dashboard, retrospective, interview) — true type / typeless now shown
T027 Tighten FR-010 structural gate to fully green; run `tests/architectural/` + terminology guard

### Dependencies

- Depends on WP02, WP03, WP04.

### Risks & Mitigations

- Rebuilding the M0 backfill — explicitly avoid; this is verification.
- ADR must name the compounding so neither M3 nor M5 ships the compound break unguarded.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → {WP02, WP03, WP04 (parallel)} → WP05.
- **Parallelization**: WP02/WP03/WP04 touch disjoint files and may proceed concurrently after WP01.
- **MVP Scope**: WP01 + WP02 (the shared seam + the runtime read convergence, incl. the dashboard visible fix) is the minimal correctness release; WP03–WP05 complete the folds, exemptions, and behavior-change governance.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01, WP02, WP03 |
| FR-003 | WP02 |
| FR-004 | WP01 |
| FR-005 | WP02 |
| FR-006 | WP02, WP03 |
| FR-007 | WP05 |
| FR-008 | WP04 |
| FR-009 | WP03 |
| FR-010 | WP01 (red), WP05 (green) |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add `read_mission_type` seam | WP01 | P0 | No |
| T002 | Seam unit table | WP01 | P0 | No |
| T003 | `_canonical_meta_mission_type` delegate | WP01 | P0 | No |
| T004 | Charter path delegates to seam | WP01 | P0 | No |
| T005 | FR-010 structural test (red) | WP01 | P0 | Yes |
| T006 | Layer-rules stays green | WP01 | P0 | Yes |
| T007 | Dashboard features → helper (FR-005) | WP02 | P0 | No |
| T008 | mission_metadata read/build | WP02 | P0 | Yes |
| T009 | retrospective/generator :1319 | WP02 | P1 | Yes |
| T010 | context/resolver :94 | WP02 | P1 | Yes |
| T011 | verify_enhanced | WP02 | P1 | Yes |
| T012 | dashboard/diagnostics | WP02 | P1 | Yes |
| T013 | retrospective reader/writer parity | WP02 | P1 | Yes |
| T014 | Per-reader pins | WP02 | P0 | No |
| T015 | mission_create echo field set | WP03 | P1 | No |
| T016 | feature_meta infer_mission | WP03 | P1 | Yes |
| T017 | interview payload exemption | WP03 | P1 | Yes |
| T018 | audit tool stays field-aware | WP03 | P1 | Yes |
| T019 | inline_meta_read_allowlist.yaml | WP03 | P1 | No |
| T020 | Frozen-migration replay/exempt | WP03 | P1 | No |
| T021 | audit/classifiers/wp_files route | WP04 | P2 | No |
| T022 | mission_v1/guards evaluate | WP04 | P2 | Yes |
| T023 | landed-consumer parity pin | WP04 | P2 | Yes |
| T024 | FR-007 backfill verify (AC-5) | WP05 | P1 | No |
| T025 | Legacy-retirement ADR | WP05 | P1 | No |
| T026 | Per-surface changelog | WP05 | P1 | Yes |
| T027 | FR-010 gate green + arch suite | WP05 | P1 | No |
