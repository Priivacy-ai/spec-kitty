# Work Packages: Synthesized DRG Stale-Refresh Fix

**Inputs**: Design documents from `/kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/`
**Prerequisites**: plan.md (required), spec.md (user scenarios), research.md, data-model.md, contracts/synthesized-drg-freshness-rule.md, quickstart.md, the three tracer files

**Tests**: Required by the charter's C-011 (ATDD / red-first, binding),
scoped to the WPs that deliver **user-observable behavior**. WP02 (writer) and
WP03 (reader) are self-contained planning-base-red-first: their red-first
tests are RED on that WP's base (the prior WP's final state) and GREEN on that
WP's own final commit. **WP01 (infra) and WP04 (docs/verification) deliver NO
user-observable runtime behavior → C-011 planning-base-red-first is N/A**:
WP01 follows red-green-refactor INTERNALLY (TDD for the shim + helper) and its
gate is green-preserving regression + new-symbol unit coverage + the intra-WP
verify-shim TDD cycle; WP04's gate is the full regression suite + the NFR
guards. This is correct scoping of C-011 to behavior WPs — NOT the
mission-level dilution the `/analyze` gate rejects.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages
(`WPxx`). Strictly sequential WP01→WP02→WP03→WP04 (single-branch topology,
shared surfaces → strict ordering).

**Prompt Files**: Each WP references a matching prompt file in `/tasks/`. Deep
implementation detail (file:line citations, code snippets, red/green
sequencing) lives in the prompt files.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different
  files/components) — WITHIN a work package only; work packages are strictly
  sequential.
- Include precise file paths or modules.

## Path Conventions

- **Single project**: `src/`, `tests/` (single Python CLI package,
  `spec-kitty-cli`).

---

## Work Package WP01: Manifest schema + hash infra (infra WP — C-011 planning-base-red-first N/A) (Priority: P0)

**Goal**: Deliver a manifest that can carry `bundle_content_hash` and stay
self-consistent, plus the pure content-hash helper — with the two
backward-compat breaks the field addition would cause (`verify_manifest_hash`
for existing v2 manifests; the fresh-seed raw-`hashlib` writer) fixed in the
SAME WP. This is INTERNAL infrastructure with **no user-observable freshness
behavior** (reader + the three constructor writers untouched).
**Independent Test** (C-011 planning-base-red-first N/A — infra WP): WP01's
gate is (i) green-preserving regression (existing v2 manifests still
`verify_manifest_hash` after the field add + shim), (ii) new-symbol unit
coverage (helper incl. fail-safe `None` cases + finalizer parity), and (iii)
the intra-WP verify-shim red→green (the field add reddens v2 verify, the
per-field shim greens it — a TDD cycle WITHIN WP01, not a planning-base-red
operator test). The T006(b) tamper fixture is the DISCRIMINATING shape (field
present on disk, stored hash EXCLUDING it, then tampered) that proves the shim
is per-field, not a pop-list.
**Prompt**: `/tasks/WP01-manifest-schema-hash-infra.md`
**Requirement Refs**: NFR-001, NFR-004, NFR-005, C-001, C-005, C-006

### Included Subtasks

- [x] T001 [P] Add `bundle_content_hash` field + widen `schema_version: Literal["2","3"]` (keep default `"2"`) in `src/charter/synthesizer/manifest.py`
- [x] T002 [P] Pure UNWIRED `compute_bundle_content_hash` + `BUNDLE_CONTENT_HASH_FILES` (C1: catch `OSError` AND `UnicodeDecodeError` → `None`) in `src/charter/bundle.py`
- [x] T003 Extract `finalize_manifest()` in `src/charter/synthesizer/manifest.py`
- [x] T004 Generalize `verify_manifest_hash` fallback (per-field `_raw_field_names` subset) in `src/charter/synthesizer/manifest.py`
- [x] T005 Route `_fresh_seed_manifest_text` through `finalize_manifest` in `src/specify_cli/cli/commands/charter/_fresh_doctrine.py`
- [x] T006 Intra-WP shim/parity tests (incl. the DISCRIMINATING per-field tamper fixture) + production fresh-seed pin in `tests/charter/synthesizer/test_manifest.py`, `tests/integration/test_charter_synthesize_fresh.py`
- [x] T007 [P] Helper unit tests (missing-file→None, **non-UTF-8→None**, happy path) in NEW `tests/charter/test_bundle_content_hash.py`

### Implementation Notes

- T001/T002 are parallel (different files). T003/T004/T006 depend on T001;
  T005 depends on T003; T007 depends on T002.
- The `schema_version` default bump to `"3"` is NOT in this WP (WP02) —
  landing it here would desync the two writers' hardcoded `"2"` hashed-dict
  literal against the `"3"` default (fact #17).
- **C-011 N/A (infra WP)**: WP01 delivers no user-observable freshness
  behavior, so there is no planning-base-red operator test (the new symbols
  don't exist on the base → unrunnable, not a clean RED; v2 verify is GREEN
  on the base). Follow red-green-refactor INTERNALLY: the field add reddens
  v2 verify momentarily, the per-field shim (T004) greens it; write the
  helper unit tests (T007) against the new symbol test-then-implement. The
  gate is green-preserving regression + new-symbol unit coverage + the
  intra-WP shim TDD cycle.

### Parallel Opportunities

- T001 ∥ T002; T007 ∥ T006 (once T002 lands).

### Dependencies

- None (first work package).

### Risks & Mitigations

- `verify_manifest_hash` shim regressing to a fixed pop-list → weakens tamper
  detection. Mitigated by T006 tamper pin.
- C1: catching only `OSError` → a non-UTF-8 bundle file crashes `charter
  status`/preflight. Mitigated by T007's non-UTF-8 test.

---

## Work Package WP02: Writer wiring (self-contained red→green, reader-independent) (Priority: P0)

**Goal**: Make every persist site write a correct non-`None`
`bundle_content_hash` via the one finalizer. Bump the model `schema_version`
default `"2"`→`"3"` ATOMICALLY with converting `promote`/`_rewrite_manifest`
to instances-through-`finalize_manifest`; fix `apply_post_condition`
(BLOCKER-1) via `model_copy` + `finalize_manifest`; thread `repo_root` into
`_rewrite_manifest`. Reader untouched.
**Independent Test** (per-WP red→green, reader-independent): after `synthesize`
AND `resynthesize`, `manifest.bundle_content_hash is not None and ==
compute_bundle_content_hash(repo_root)` (T011); the BLOCKER-1 field survives
the `apply_post_condition` flip + `verify_manifest_hash` passes (T012); a
content edit + re-`synthesize` recomputes the field (T013). All RED on WP02's
base (writers emit `None`), GREEN on WP02's final commit.
**Prompt**: `/tasks/WP02-writer-wiring.md`
**Requirement Refs**: FR-001, FR-003, FR-005, NFR-001, NFR-004, NFR-005, C-001, C-004, C-005, C-006

### Included Subtasks

- [x] T008 Bump `schema_version` default `"2"`→`"3"` (out-of-map `manifest.py` one-liner) + convert `write_pipeline.promote` to instance+`finalize_manifest` (ATOMIC, one commit)
- [x] T009 [P] Convert `resynthesize_pipeline._rewrite_manifest` to instance+`finalize_manifest`; thread `repo_root`
- [x] T010 [P] Fix `project_drg.apply_post_condition` (BLOCKER-1) via `model_copy` + `finalize_manifest`
- [x] T011 Red-first writer-side field==helper assertion (synthesize AND resynthesize) in `tests/charter/synthesizer/test_orchestrator_resynthesize.py`, `tests/charter/synthesizer/test_write_pipeline.py`
- [x] T012 [P] Red-first BLOCKER-1 non-vacuous pin (drives the mutation branch; field survives + `verify_manifest_hash` passes) in `tests/integration/test_charter_synthesize_built_in_only.py`
- [x] T013 Red-first writer-recompute on genuine content drift (SC-003 writer half, reader-independent) in `tests/charter/synthesizer/test_orchestrator_resynthesize.py`
- [x] T014 WP02 regression validation (no-op-stable green, `_VOLATILE_MANIFEST_FIELDS` unchanged)

### Implementation Notes

- **Out-of-map edit**: T008 makes a ONE-LINE `manifest.py` default bump
  (WP01-owned file) — NOT listed in WP02 `owned_files`; document it with
  rationale in the Activity Log. It MUST land in the SAME commit as the
  `promote` conversion (fact #17).
- BLOCKER-1 needs its OWN non-vacuous test (T012): `apply_post_condition`
  fast-path early-returns on a normal non-built-in synthesize
  (`project_drg.py:305-310`), so synthesize flows never reach the mutation
  branch; the existing built_in_only tests seed `bundle_content_hash=None`
  (`None→None`, invisible).
- WP02's red tests assert on the manifest FIELD (reader-independent), so they
  go green at WP02 without the reader swap.

### Parallel Opportunities

- T009 ∥ T010 (once T008 sets the pattern); T012 ∥ T011.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- T008 default bump + `promote` conversion in separate commits → accidental
  `verify_manifest_hash` RED (fact #17). Mitigated: T008 is one atomic unit.
- `_VOLATILE_MANIFEST_FIELDS` gaining the field → breaks AS-4 self-heal.
  Mitigated by the DoD diff check.
- A red-first pin that was never red (vacuous). Mitigated by the confirm-red
  step in T011/T012/T013.

---

## Work Package WP03: Reader swap (self-contained red→green) (Priority: P0)

**Goal**: Rewrite `_compute_synthesized_drg`'s comparison
(`computer.py:411-441`) to stored-vs-current `bundle_content_hash` (None
either side → stale); remove dead `manifest_exists`/`bundle_ts`; preserve
built_in_only/missing/legacy-seed/synced_bundle-precedence + parse-failure
early-return; correct the module docstring (FR-007 internal).
**Independent Test** (per-WP red→green): AS-1 (fresh survives mtime
perturbation) and AS-5 (#2681 full repro) are RED on WP03's base (the
still-mtime reader gives the WRONG verdict) and GREEN on WP03's final commit
(content-hash reader). Plus the genuine-content-change remediation e2e
(SC-003/AS-3 full proof) green, the flaky assertion tightened, and the
preserved-branch pins green.
**Prompt**: `/tasks/WP03-reader-swap.md`
**Requirement Refs**: FR-001, FR-002, FR-004, FR-005, FR-006, FR-007, NFR-004, NFR-005, NFR-006, C-002

### Included Subtasks

- [x] T015 Rewrite the `_compute_synthesized_drg` comparison block to content-hash (lazy import) in `src/specify_cli/charter_runtime/freshness/computer.py`
- [x] T016 Remove dead `manifest_exists` (`:352`) + `bundle_ts` (`:412`) in `computer.py`
- [x] T017 [P] Correct the module docstring "Detection rules" (FR-007 internal) in `computer.py`
- [x] T018 [P] Red-first AS-1 + AS-2 reader unit tests in `tests/specify_cli/charter_freshness/test_computer.py`
- [x] T019 [P] Red-first AS-5 #2681 full repro (synthesize+resynthesize) + genuine-content-change remediation e2e in `tests/specify_cli/charter_freshness/test_computer.py`, `tests/integration/test_charter_status_freshness.py`
- [x] T020 [P] Tighten the flaky `test_freshness_state_fresh_when_all_artifacts_aligned` (`in {"fresh","stale"}` → `== "fresh"`) + preserved-branch pins in `tests/integration/test_charter_status_freshness.py`, `tests/specify_cli/charter_freshness/test_computer.py`
- [x] T021 WP03 regression validation

### Implementation Notes

- The `compute_bundle_content_hash` import in `computer.py` MUST be LAZY
  (inside the function) — LD-3 / NFR-002/003.
- AS-1 + AS-5 are the UNAMBIGUOUS per-WP red pins; AS-2 and some
  remediation-e2e assertions may coincidentally pass on the mtime base but
  pin the requirement precisely — label each test's role.
- WP03 does NOT edit `test_orchestrator_resynthesize.py` (WP02-owned) — the
  reader-side remediation e2e lives in WP03's owned test files.

### Parallel Opportunities

- T017 (docstring) ∥ T015/T016; T018 ∥ T019 ∥ T020.

### Dependencies

- Depends on WP02 (writers must persist real values for the reader to compare).

### Risks & Mitigations

- Touching a PRESERVED branch → regression. Mitigated by T020's pins.
- Eager `charter.bundle` import → NFR-002/003 regression. Mitigated by the
  lazy-import discipline.

---

## Work Package WP04: Contract doc + full regression + NFR verification (closeout) (Priority: P0)

**Goal**: Correct the published `charter-status-json.md` contract doc (FR-007
external half); verify NFR-002 (<2s) via a permanent perf guard and NFR-003
(no new manual step/dep); run the full regression suite + quality gates;
issue-matrix close-out + DIR-003 caveat + tracer assessment. **Delivers no new
runtime behavior → C-011 red-first N/A**; its gate is the regression suite +
NFR guards.
**Independent Test**: the full command list in the prompt passes;
NFR-002/NFR-003 have recorded evidence; terminology guard passes; tracer
close-out appended.
**Prompt**: `/tasks/WP04-contract-doc-regression-nfr.md`
**Requirement Refs**: FR-007, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, C-001, C-003

### Included Subtasks

- [x] T022 [P] Correct the external contract doc (FR-007, reviewer-attested) in `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/charter-status-json.md`
- [x] T023 [P] NFR-002 perf guard (<2s freshness compute) in `tests/charter/synthesizer/test_performance_envelopes.py`
- [x] T024 [P] NFR-003 audit (0 new manual steps/dependencies, recorded evidence)
- [x] T025 Full regression run (mypy --strict, ruff, coverage ≥90%, no-op-stable + terminology guards)
- [x] T026 issue-matrix close-out (pre-settled verdicts) + DIR-003 caveat + tracer assessment

### Implementation Notes

- **Ownership note**: WP04's `owned_files` is
  `tests/charter/synthesizer/test_performance_envelopes.py` (T023's guard),
  NOT the `kitty-specs/` contract doc T022 edits — the `finalize-tasks`
  ownership gate hard-rejects `kitty-specs/` paths, and empty `owned_files`
  is rejected by lane computation. T022's edit is reviewer-attested. See the
  prompt's dedicated ownership note.
- WP04 adds no new runtime code path — it is categorically a closeout; the
  NFR-002 test is a performance ratchet, not a behavior red→green.

### Parallel Opportunities

- T022, T023, T024 are independent.

### Dependencies

- Depends on WP01, WP02, WP03 (verifies the whole mission).

### Risks & Mitigations

- Contract-doc wording drifting from WP03's internal docstring. Mitigated:
  both trace to `synthesized-drg-freshness-rule.md`.
- NFR-002/003 rubber-stamps. Mitigated: T023 is a permanent test; T024
  requires recorded grep/diff evidence.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → WP04 — strictly sequential, single-branch
  topology, no parallel work-package execution. Each WP's `dependencies`
  frontmatter names exactly the one WP before it.
- **Parallelization**: only WITHIN a work package (see each WP's "Parallel
  Opportunities").
- **MVP Scope**: all four work packages are required to close #2681.
- **C-011 scoping (no dilution)**: C-011 planning-base-red-first is scoped to
  the WPs that deliver **user-observable behavior** — WP02 (writer) and WP03
  (reader) are self-contained planning-base-red→green (their red-first tests
  are RED on the WP's base and GREEN on the WP's final commit). WP01 (infra:
  new optional field + pure helper + finalize refactor + verify-shim) and WP04
  (docs/verification) deliver **no user-observable behavior → planning-base-
  red-first N/A**: WP01 uses INTERNAL red-green-refactor (green-preserving
  regression + new-symbol unit coverage + the intra-WP shim TDD cycle); WP04's
  gate is the full regression suite + NFR guards. This is correct scoping of
  C-011 to behavior WPs, NOT the mission-level dilution the `/analyze` gate
  rejects.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02 (write), WP03 (read) |
| FR-002 | WP03 (test + read) |
| FR-003 | WP02 (writer recompute, reader-independent), WP03 (remediation e2e) |
| FR-004 | WP03 (preserve + pin) |
| FR-005 | WP02 (write), WP03 (read + repro) |
| FR-006 | WP03 (preserve + pin) |
| FR-007 | WP03 (internal docstring), WP04 (external contract) |
| NFR-001 | WP01 (non-volatile field), WP02 (writer no-op-stability), WP04 (final) |
| NFR-002 | WP04 |
| NFR-003 | WP04 |
| NFR-004 | WP01, WP02, WP03, WP04 |
| NFR-005 | WP01, WP02, WP03, WP04 |
| NFR-006 | WP03 |
| C-001 | WP01 (widen-not-break), WP02 (writer wiring), WP04 (final) |
| C-002 | WP03 (preserve + pin) |
| C-003 | WP04 |
| C-004 | WP02 (writer), WP03 (both remediation paths corrected) |
| C-005 | WP01 (finalizer + helper), WP02 (single writer), WP03 (single reader) |
| C-006 | WP01 (finalizer), WP02 (single writer wiring) |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|---------------|----------|-----------|
| T001 | Add `bundle_content_hash` field + widen `schema_version` Literal (keep default `"2"`) | WP01 | P0 | Yes |
| T002 | Pure `compute_bundle_content_hash` + `BUNDLE_CONTENT_HASH_FILES` (C1: OSError+UnicodeDecodeError→None) | WP01 | P0 | Yes |
| T003 | Extract `finalize_manifest()` | WP01 | P0 | No |
| T004 | Generalize `verify_manifest_hash` per-field subset fallback | WP01 | P0 | No |
| T005 | Route fresh-seed writer through `finalize_manifest` | WP01 | P0 | No |
| T006 | Intra-WP shim/parity tests (discriminating per-field tamper fixture) + fresh-seed pin | WP01 | P0 | No |
| T007 | Helper unit tests (missing→None, non-UTF-8→None, happy path) | WP01 | P0 | Yes |
| T008 | Bump default `"3"` (out-of-map) + convert `promote` (atomic) | WP02 | P0 | No |
| T009 | Convert `_rewrite_manifest` + thread `repo_root` | WP02 | P0 | Yes |
| T010 | Fix `apply_post_condition` (BLOCKER-1) via `model_copy`+finalize | WP02 | P0 | Yes |
| T011 | Red-first writer-side field==helper (synth+resynth) | WP02 | P0 | No |
| T012 | Red-first BLOCKER-1 non-vacuous pin | WP02 | P0 | Yes |
| T013 | Red-first writer-recompute on content drift (SC-003 writer half) | WP02 | P0 | No |
| T014 | WP02 regression validation | WP02 | P0 | No |
| T015 | Rewrite comparison block to content-hash (lazy import) | WP03 | P0 | No |
| T016 | Remove dead `manifest_exists`/`bundle_ts` | WP03 | P0 | No |
| T017 | Correct module docstring (FR-007 internal) | WP03 | P0 | Yes |
| T018 | Red-first AS-1 + AS-2 reader unit tests | WP03 | P0 | Yes |
| T019 | Red-first AS-5 full repro + genuine-content-change remediation e2e | WP03 | P0 | Yes |
| T020 | Tighten flaky assertion + preserved-branch pins | WP03 | P0 | Yes |
| T021 | WP03 regression validation | WP03 | P0 | No |
| T022 | Correct external contract doc (FR-007, reviewer-attested) | WP04 | P0 | Yes |
| T023 | NFR-002 perf guard (<2s) | WP04 | P0 | Yes |
| T024 | NFR-003 audit (0 new manual steps/deps) | WP04 | P0 | Yes |
| T025 | Full regression run | WP04 | P0 | No |
| T026 | issue-matrix close-out + DIR-003 caveat + tracer assessment | WP04 | P0 | No |
