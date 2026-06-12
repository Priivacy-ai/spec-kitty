# Tasks: Doctrine, Glossary & Architecture Consolidation

**Mission**: doctrine-glossary-architecture-consolidation-01KTNWFC | **Branch**: feat/doctrine-glossary-consolidation-01KTNWFC
**Plan**: [plan.md](./plan.md) | **Decisions**: [research.md](./research.md) | **change_mode**: standard (O1-reverted; occurrence_map is a reference-rewrite advisory checklist, not an enforcement gate)

11 work packages from the 9 ICs. Phase 1 (moves, bulk_edit) → Phase 2 (authoring) ; code lanes parallel ; #391 dogfood last.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Inventory glossary locations + reference sites; finalize occurrence_map glossary section | WP01 | |
| T002 | Move glossary content → top-level `glossary/` (+ `contexts/`) | WP01 | |
| T003 | Update `GlossaryScope` loader + seed paths in `src/glossary` | WP01 | |
| T004 | Rewrite glossary refs in `.kittify/glossaries` + doctrine/doc cross-links | WP01 | |
| T005 | Validate: `glossary validate` + loader tests + terminology guard | WP01 | |
| T006 | Create top-level `vision/`, `diagrams/`, retain `audience/`; updated `README.md` boundary rule | WP02 | |
| T007 | Carry C4 forward into `diagrams/` (numbered levels); freeze 2.x snapshot | WP02 | |
| T008 | Versioned history dirs `{1.x,2.x,3.x}/{adr,vision,research}`; demote obsolete; de-dup `docs/explanation` link-up | WP02 | |
| T009 | Rewrite architecture-path refs incl. charter authority paths; finalize occurrence_map architecture section | WP02 | |
| T010 | Verify reference integrity (grep, no dangling); occurrence_map verification block | WP02 | |
| T011 | Refresh C4 context level to 3.x domain model (Mermaid) | WP03 | [P] |
| T012 | Refresh C4 container level (Governance/Mission-Mgmt/Execution-Runtime + Op/lifecycle tier) | WP03 | [P] |
| T013 | Refresh C4 component level for the changed domains | WP03 | [P] |
| T014 | Author planning/tracking **procedure** (tracker-organisation workflow) | WP04 | |
| T015 | Author **tactic**: iterative-deepening review | WP04 | |
| T016 | Author **tactic**: MoSCoW prioritisation approach | WP04 | |
| T017 | Author planning/tracking **styleguide** (functional-vs-meta, community-precedence, label/type/priority, naming) | WP05 | |
| T018 | Author planning/tracking **toolguide** (gh/GraphQL mechanics + gotchas) | WP05 | |
| T019 | Author the **Ops ADR** (shared Op/lifecycle abstraction; #1804+#1802) | WP06 | |
| T020 | Cross-link Ops ADR from #1804/#1802/#1810; record in correlation matrix | WP06 | |
| T021 | Refresh glossary **content** for new epics + architectural direction | WP01 | |
| T022 | Reconcile planning-and-tracking subset terms; record FR-011 runtime-scope **defer** | WP01 | |
| T023 | Implement `org-charter.yaml` `extends:` additive merge + base precedence | WP08 | |
| T024 | Cycle detection + integrate with `charter.activation_engine`/cascade (no parallel resolver) | WP08 | |
| T025 | Tests for extends (additive, precedence, cycle-reject, non-destructive) | WP08 | |
| T026 | DRG **regeneration command** (deterministic output) | WP09 | |
| T027 | **Symmetric** profile-edge detection + freshness gate | WP09 | |
| T028 | Tests: regenerate-twice identical; freshness green | WP09 | |
| T029 | Re-curate built-in DRG: add new doctrine artefacts as nodes/edges | WP10 | |
| T030 | Prune stale/duplicate edges + dead profiles (no valid edge dropped) | WP10 | |
| T031 | `doctor doctrine --json` healthy; regenerate graph.yaml | WP10 | |
| T032 | Apply procedure/styleguide to #391: classify children, propose reparenting | WP11 | |
| T033 | Execute reparenting + close #391 as superseded (community-precedence) | WP11 | |
| T034 | Record usage-test outcome in `work/`; validate SC-1/SC-6 | WP11 | |

---

## Phase 1 — Restructure & moves (bulk_edit)

### WP01 — Glossary: reconcile top-level surface + content refresh
- **Goal**: RECONCILE the already-canonical top-level `glossary/` + DELETE residual `architecture/glossary/` pointer content (C-005, R-01); update loader/path refs; refresh content for the new epics (FR-010) and record the runtime-scope defer (FR-011). *(Merged former WP07 to keep `glossary/**` ownership in one WP.)*
- **Priority**: P1 (gates Phase 2 authoring) | **Independent test**: `glossary validate` + loader tests pass against top-level `glossary/`; no dangling glossary refs; `architecture/glossary/` absent.
- **Subtasks**: - [x] T001 (WP01) · - [x] T002 (WP01) · - [x] T003 (WP01) · - [x] T004 (WP01) · - [x] T005 (WP01) · - [x] T021 (WP01) · - [x] T022 (WP01)
- **change_mode**: standard (O1 revert: occurrence_map is a reference-rewrite advisory checklist, not a gate) | **Depends on**: none | **Est**: ~420 lines
- **Risks**: missed reference breaks glossary loading / charter authority path; terminology guard on refreshed content.

### WP02 — Living-architecture layout + reconcile (closes #1805)
- **Goal**: Top-level living `architecture/` (vision/, audience/, diagrams/, README boundary rule) + versioned history; RECONCILE + delete residual parallel content; carry C4 forward; rewrite architecture refs incl. charter authority paths. Closes #1805.
- **Priority**: P1 | **Independent test**: reference-integrity grep clean; README states boundary rule + decay path; no residual parallel narrative surfaces.
- **Subtasks**: - [x] T006 (WP02) · - [x] T007 (WP02) · - [x] T008 (WP02) · - [x] T009 (WP02) · - [x] T010 (WP02)
- **change_mode**: standard (O1-reverted; occurrence_map is a reference-rewrite advisory checklist, not a gate) | **Depends on**: WP01 (shares the charter authority-path file; needs final glossary path) | **Est**: ~360 lines
- **Risks**: broken internal doc links; decay rule must be documented to prevent re-drift; tier-field layout must remain open for #1843.

## Phase 2 — Authoring (into the settled layout)

### WP03 — Refresh the 3.x C4 model
- **Goal**: Update living C4 (Markdown+Mermaid, numbered levels) to the 3.x domain model.
- **Subtasks**: - [x] T011 (WP03) · - [x] T012 (WP03) · - [x] T013 (WP03) | **Depends on**: WP02 | **Est**: ~240 lines
- **Risks**: Mermaid drift (generated-C4 swap deferred to #1812).

### WP04 — Author planning/tracking procedure + tactics
- **Goal**: Procedure (tracker-organisation workflow) + tactics (iterative-deepening, MoSCoW) from `work/` traces.
- **Subtasks**: - [ ] T014 (WP04) · - [ ] T015 (WP04) · - [ ] T016 (WP04) | **Depends on**: WP01, WP02 | **Est**: ~300 lines
- **Risks**: terminology guard; conform to doctrine schemas + DRG (WP10 re-curates after).

### WP05 — Author planning/tracking styleguide + toolguide
- **Goal**: Styleguide (functional-vs-meta, community-precedence, conventions, naming) + toolguide (gh/GraphQL mechanics).
- **Subtasks**: - [x] T017 (WP05) · - [x] T018 (WP05) | **Depends on**: WP01, WP02 | **Est**: ~280 lines
- **Risks**: "Feature"/"features" prose vs terminology guard; architect sign-off (encodes architecture conventions).

### WP06 — Author the Ops ADR
- **Goal**: Ratify "Op as first-class execution artifact" covering pre/post-mission lifecycle (shared abstraction; #1804+#1802).
- **Subtasks**: - [x] T019 (WP06) · - [x] T020 (WP06) | **Depends on**: WP02 | **Est**: ~240 lines
- **Risks**: must define ONE shared abstraction (C-005), not two parallel ones.

## Code lanes (parallel from start)

### WP08 — Charter `extends:` (additive multi-org config)
- **Goal**: `org-charter.yaml` `extends:` additive merge, base precedence, cycle detection, via activation_engine/cascade (no parallel resolver).
- **Subtasks**: - [x] T023 (WP08) · - [x] T024 (WP08) · - [x] T025 (WP08) | **Depends on**: none | **Est**: ~340 lines
- **Risks**: cycle detection; reuse activation/cascade (C-005); preserve charter content (C-004); ruff/mypy clean.

### WP09 — DRG generator/freshness gaps
- **Goal**: Regeneration command (deterministic) + symmetric profile-edge detection + freshness gate (code only).
- **Subtasks**: - [x] T026 (WP09) · - [x] T027 (WP09) · - [x] T028 (WP09) | **Depends on**: none | **Est**: ~300 lines
- **Risks**: determinism; ruff/mypy clean.

### WP10 — Built-in DRG + profile re-curation
- **Goal**: Add new doctrine artefacts as DRG nodes/edges; prune stale/duplicate edges + dead profiles (data re-curation).
- **Subtasks**: - [ ] T029 (WP10) · - [ ] T030 (WP10) · - [ ] T031 (WP10) | **Depends on**: WP04, WP05, WP09 | **Est**: ~260 lines
- **Risks**: don't drop valid edges; doctor doctrine healthy.

## Validation / dogfood

### WP11 — #391 doctrine usage-test
- **Goal**: Apply the new doctrine to reorganize #391 (split/reparent/close superseded) — dogfood proving SC-1/SC-6.
- **Subtasks**: - [x] T032 (WP11) · - [x] T033 (WP11) · - [x] T034 (WP11) | **Depends on**: WP04, WP05 | **Est**: ~240 lines
- **Risks**: community-precedence on dedup; follow toolguide rate-limit/mechanics findings.

---

## Dependencies summary
- 10 WPs (WP07 merged into WP01; IDs WP01–06, WP08–11).
- WP01 → WP02 → WP03 ; {WP04, WP05, WP06} depend on Phase 1 ; WP08, WP09 parallel (no deps) ; WP10 depends WP04/WP05/WP09 ; WP11 depends WP04/WP05.

## MVP / sequencing
- **Critical path**: WP01 → WP02 → (WP04/WP05) → WP10/WP11.
- **Start-immediately (parallel)**: WP08, WP09 (code lanes, no doc-path deps).
