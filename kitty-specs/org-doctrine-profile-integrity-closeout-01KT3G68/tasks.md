# Tasks — Org Doctrine Profile Integrity Close-Out

Hardening close-out remediating findings I-1..I-12 (parent debrief). 6 work packages, all on `mission/org-doctrine-profile-integrity-activation-closure`. Designs settled in `research.md` (R1 load-layer skip; R3 delete both cascade-warning branches) and `contracts/`. ATDD-first for behavioral FRs.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Load-layer skip: `repository._load_layer` catches `InlineReferenceRejectedError` → `_record_skip` (populate profile_id) | WP01 | |
| T002 | Reconcile `diagnostics.py` docstring + `repository.py` comment to "surfaced skip" (I-9) | WP01 | |
| T003 | Integration test: `doctor doctrine` vs `tactic_refs` org profile → healthy:false + invalid surfaced + valid siblings visible (RED→GREEN) | WP01 | |
| T004 | Regression-verify general callers (`resolve_profile`/`get_ancestors`, `test_inline_ref_rejection.py`) | WP01 | |
| T005 | Add `pytestmark` (unit/contract) to the 4 pure test files | WP02 | [P] |
| T006 | Add `pytestmark = [..., integration]` to the I/O-heavy `test_operational_context_wiring.py` | WP02 | [P] |
| T007 | Verify `test_pytest_marker_convention` + `test_pytest_marker_correctness` pass | WP02 | |
| T008 | Create `src/charter/template_catalog.py` re-export facade (`__all__`) | WP03 | |
| T009 | Repoint module-level doctrine imports in `activate.py`/`list_cmd.py` to `charter.*` facades | WP03 | |
| T010 | Remove both `_BASELINE_ALLOWLIST` entries; set `_baselines.yaml` boundary baseline to 0 | WP03 | |
| T011 | Verify boundary + ratchet gates green | WP03 | |
| T012 | `merge.py`: make `_tag_source[T: BaseModel](obj: T) -> T`; `mypy --strict` clean | WP04 | |
| T013 | `merge.py`: type the `provenance` sidecar (FR-013) OR file tracker | WP04 | |
| T014 | `events.py`: drop 2 payloads from `__all__` (KEEP imports); remove the 2 allowlist entries | WP04 | |
| T015 | Verify `test_no_dead_symbols` + `mypy` | WP04 | |
| T016 | Delete both stale cascade-warning branches in `pack_manager` (activate + deactivate) | WP05 | |
| T017 | Test: "not yet implemented"/"deferred" absent from activate AND deactivate `--cascade` output | WP05 | |
| T018 | Update existing `test_activate_cascade_calls_with_true` + `test_activate_cascade_flag_accepted` (DD-4) | WP05 | |
| T019 | Populate parent `acceptance-matrix.json` with real per-FR criteria + test IDs; set `overall_verdict` | WP06 | [P] |
| T020 | Add `CLAUDE.md` section (charter activation/cascade, kind vocabulary, `specializes_from`) | WP06 | [P] |
| T021 | File tracker(s) for pre-existing failures (`ceremony`, `git_repo` markers) + doctor.py modularity (FR-012 deferred) | WP06 | |

## Work Packages

### WP01 — Doctor false-healthy: load-layer skip (I-1, I-9) — HIGH, merge blocker
**Goal:** `doctor doctrine` reports `healthy:false` and surfaces an inline-ref-invalid profile while valid siblings remain visible. **Independent test:** `tests/specify_cli/test_doctor_doctrine.py` new integration case (RED before, GREEN after).
- [ ] T001 Load-layer skip in `repository._load_layer` (WP01)
- [ ] T002 Reconcile docstring/comment (I-9) (WP01)
- [ ] T003 Integration test driving the raising load (WP01)
- [ ] T004 Regression-verify general callers (WP01)
**Dependencies:** none. **Risks:** blast radius to general callers — covered by T004. **Prompt:** `tasks/WP01-doctor-false-healthy-load-layer.md`

### WP02 — CI marker visibility (I-2) — HIGH, merge blocker
**Goal:** every parent-mission test file declares a correct `pytestmark`; convention + correctness gates pass. **Independent test:** `test_pytest_marker_convention`/`test_pytest_marker_correctness`.
- [ ] T005 Markers on the 4 pure files (WP02)
- [ ] T006 Integration marker on the I/O-heavy wiring test (WP02)
- [ ] T007 Verify both marker gates (WP02)
**Dependencies:** none. **Prompt:** `tasks/WP02-ci-marker-visibility.md`

### WP03 — Charter boundary facade + allowlist→0 (I-4) — MEDIUM
**Goal:** CLI reaches doctrine only via charter facades; boundary allowlist back to 0. **Independent test:** `test_runtime_charter_doctrine_boundary` + `test_ratchet_baselines`.
- [ ] T008 `charter.template_catalog` facade (WP03)
- [ ] T009 Repoint module-level imports (WP03)
- [ ] T010 Allowlist→0 + `_baselines.yaml` (WP03)
- [ ] T011 Verify gates (WP03)
**Dependencies:** none. **Note:** only module-level imports are gated; lazy `mission_type_repository`/`MissionTemplateRepository` imports are boundary-invisible — do not facade them. **Prompt:** `tasks/WP03-charter-boundary-facade.md`

### WP04 — Type + dead-symbol gate hygiene (I-3, I-6, I-11) — HIGH/MEDIUM
**Goal:** `mypy --strict` clean on `merge.py`; FR-036 dead-symbol claim accurate. **Independent test:** `mypy --strict src/doctrine/drg/merge.py`; `test_no_dead_symbols`.
- [ ] T012 `_tag_source` generic (WP04)
- [ ] T013 Provenance typing OR tracker (WP04)
- [ ] T014 Drop 2 `events.py` `__all__` entries (keep imports) + allowlist (WP04)
- [ ] T015 Verify gates (WP04)
**Dependencies:** none. **Prompt:** `tasks/WP04-type-deadsymbol-hygiene.md`

### WP05 — Cascade output hygiene (I-5) — MEDIUM
**Goal:** no stale "deferred"/"not yet implemented" cascade warnings; cascade still works. **Independent test:** cascade-output absence test (activate + deactivate).
- [ ] T016 Delete both stale warning branches (WP05)
- [ ] T017 Absence test (WP05)
- [ ] T018 Update existing cascade tests (DD-4) (WP05)
**Dependencies:** none. **Prompt:** `tasks/WP05-cascade-output-hygiene.md`

### WP06 — Completion-proof + docs + trackers (I-7, I-8, I-10, I-12) — MEDIUM/LOW
**Goal:** accurate acceptance matrix, synced CLAUDE.md, trackers for deferred/pre-existing items. **Independent test:** matrix has no pending/null; CLAUDE.md section present; trackers filed.
- [ ] T019 Populate parent `acceptance-matrix.json` (WP06)
- [ ] T020 CLAUDE.md section (WP06)
- [ ] T021 Trackers (pre-existing failures + doctor modularity) (WP06)
**Dependencies:** none (best landed last — T019 references the proving test IDs the other WPs add). **Prompt:** `tasks/WP06-completion-proof-docs.md`

## Parallelization
All six WPs touch disjoint files and are independently implementable in parallel. Suggested priority: WP01 + WP02 (merge blockers) first; WP06 best last (its matrix references the other WPs' test IDs).

## MVP
WP01 (the core #1584 regression fix) is the highest-value package.
