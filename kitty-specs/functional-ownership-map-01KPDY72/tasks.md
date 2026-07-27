# Work Packages: Functional Ownership Map

**Mission**: `functional-ownership-map-01KPDY72`
**Mission ID**: `01KPDY72HV348TA2ERN9S1WM91`
**Planning base → merge target**: `feature/module_ownership` → `feature/module_ownership`
**Generated**: 2026-04-18
**Total subtasks**: 16 across 3 work packages

---

## Subtask Index

| ID   | Description                                                                   | WP    | Parallel |
|------|-------------------------------------------------------------------------------|-------|----------|
| T001 | Pre-flight grep audit: charter shim file list, CI refs, C-005 fixture locs    | WP01  |          | [D] |
| T002 | Create `05_ownership_map.md` — front matter, legend, "How to use" section     | WP01  |          | [D] |
| T003 | Write cli_shell + charter_governance (exemplar callout) + doctrine entries    | WP01  |          | [D] |
| T004 | Write runtime_mission_execution slice entry (with `dependency_rules`)          | WP01  |          | [D] |
| T005 | Write glossary + lifecycle_status + orchestrator + migration slice entries    | WP01  |          | [D] |
| T006 | Write map closing sections: safeguards, downstream missions, change control   | WP01  |          | [D] |
| T007 | Author `05_ownership_manifest.yaml` — all 8 slice keys                        | WP01  |          | [D] |
| T008 | Grep: confirm zero non-test callers of `specify_cli.charter` pre-deletion     | WP02  |          | [D] |
| T009 | Delete `src/specify_cli/charter/` — all 4 files                               | WP02  |          | [D] |
| T010 | Delete 3 C-005 test-fixture exceptions (`test_defaults_unit.py` + 2 edits)    | WP02  | [D] |
| T011 | Add CHANGELOG Unreleased/"Removed" entry for shim deletion                    | WP02  | [D] |
| T012 | Run existing test suite; confirm zero regressions (NFR-003)                   | WP02  |          | [D] |
| T013 | Write `tests/architecture/test_ownership_manifest_schema.py` (9 assertions)   | WP03  |          | [D] |
| T014 | Edit `04_implementation_mapping/README.md` — add cross-link to map (FR-007)   | WP03  | [D] |
| T015 | Run schema test; confirm all 9 assertions pass in ≤1 s (NFR-002)              | WP03  |          | [D] |
| T016 | Verify `import specify_cli.charter` raises `ModuleNotFoundError` (NFR-004)    | WP03  |          | [D] |

---

## WP01 — Core Ownership Artefacts (map + manifest)

**Goal**: Author the two normative artefacts that define the canonical functional ownership of all eight `src/specify_cli/*` slices: `architecture/2.x/05_ownership_map.md` (human-readable Markdown with all seven structural sections) and `architecture/2.x/05_ownership_manifest.yaml` (machine-readable YAML with all 8 slice keys). These are the source of truth that WP02 (deletion) and WP03 (schema test) both depend on.

**Priority**: Critical — blocks WP02 and WP03.

**Independent success test**: Both files exist; `python -c "import yaml; m=yaml.safe_load(open('architecture/2.x/05_ownership_manifest.yaml')); assert set(m)=={'cli_shell','charter_governance','doctrine','runtime_mission_execution','glossary','lifecycle_status','orchestrator_sync_tracker_saas','migration_versioning'}; print('OK')"` exits 0.

**Included subtasks**:
- [x] T001 Pre-flight grep audit: confirm charter shim file list, CI/script refs, C-005 fixture locations (WP01)
- [x] T002 Create `architecture/2.x/05_ownership_map.md` — front matter, legend, "How to use" section (WP01)
- [x] T003 Write cli_shell + charter_governance (exemplar callout) + doctrine slice entries (WP01)
- [x] T004 Write runtime_mission_execution slice entry with `dependency_rules` (WP01)
- [x] T005 Write glossary + lifecycle_status + orchestrator_sync_tracker_saas + migration_versioning slice entries (WP01)
- [x] T006 Write map closing sections: safeguards/direction, downstream missions table, change control (WP01)
- [x] T007 Author `architecture/2.x/05_ownership_manifest.yaml` — all 8 slice keys (WP01)

**Implementation sequence**:
1. T001 — pre-flight audit first (builds final picture of current state, confirms C-005 fixture paths).
2. T002 — create the map file structure and top sections.
3. T003 → T004 → T005 → T006 — fill in the 8 slice entries in order, then the closing sections.
4. T007 — author the manifest last, deriving each slice key directly from the completed map.

**Parallel opportunities**: None — each step within this package informs the next. Later packages have [P] opportunities at T010+T011 and T013+T014.

**Dependencies**: None. This is the first package and starts immediately.

**Risks**:
- The `orchestrator_sync_tracker_saas` slice is fragmented across 7 subdirectories; resist the temptation to tidy it in the map. Document the fragmentation factually (R-005).
- `dependency_rules` for runtime requires enumerating callers/callees correctly. Mitigated by data-model §1.3 and research R-003.
- Map section count and size: target ≤600 lines for the map document itself (8 slices × ~50 lines each + headers = ~500 lines).

**Prompt file**: `tasks/WP01-core-ownership-artefacts.md`
**Estimated prompt size**: ~430 lines

---

## WP02 — Charter Shim Deletion + CHANGELOG

**Goal**: Permanently delete `src/specify_cli/charter/` (all 4 files) and the 3 C-005 test-fixture exceptions that existed solely to keep legacy-import tests passing while the shim was alive. Add the CHANGELOG removal notice. Confirm zero regressions in the existing test suite. This is the code-deletion half of the mission and must happen after WP01 so the map reads as "fully consolidated" from the moment it lands.

**Priority**: High — blocks WP03.

**Independent success test**: `python -m pytest tests/ --ignore=tests/architecture -x -q` exits green with zero failures and zero new `filterwarnings` ignore entries in `pyproject.toml`.

**Included subtasks**:
- [x] T008 Grep confirm zero non-test callers of `specify_cli.charter` across repo (WP02)
- [x] T009 Delete `src/specify_cli/charter/` — `__init__.py`, `compiler.py`, `interview.py`, `resolver.py` (WP02)
- [x] T010 Delete `tests/specify_cli/charter/test_defaults_unit.py`; remove legacy-path lines from `tests/charter/test_sync_paths.py` and `tests/charter/test_chokepoint_coverage.py` (WP02) [P]
- [x] T011 Add CHANGELOG Unreleased/"Removed" entry (WP02) [P]
- [x] T012 Run full test suite (`pytest tests/ --ignore=tests/architecture`) to confirm zero regressions (WP02)

**Implementation sequence**:
1. T008 — grep gate: if unexpected callers are found, **stop and report** before deleting anything.
2. T009 — delete the four shim files.
3. T010 + T011 — clean fixtures and add CHANGELOG in parallel.
4. T012 — full test run as the final gate.

**Parallel opportunities**: T010 and T011 can be done concurrently (different files, unrelated changes).

**Dependencies**: WP01 (map/manifest must exist before deletion).

**Risks**:
- An unexpected non-test caller of `specify_cli.charter` is discovered at T008. Mitigation: halt and open a follow-up; do not delete the shim until cleared.
- Deleting too much from `tests/charter/test_sync_paths.py` or `test_chokepoint_coverage.py`. Mitigation: only remove lines that import `specify_cli.charter` or markers explicitly scoped to the C-005 exception; all `from charter import …` lines are canonical and must stay.

**Prompt file**: `tasks/WP02-charter-shim-deletion.md`
**Estimated prompt size**: ~310 lines

---

## WP03 — Schema Validation Test + Cross-reference

**Goal**: Write the pytest module `tests/architecture/test_ownership_manifest_schema.py` that validates the YAML manifest against all 9 data-model assertions; add a prominent cross-link in `architecture/2.x/04_implementation_mapping/README.md` pointing readers to the ownership map. This WP closes all remaining FR/NFR gaps (FR-007, FR-011, NFR-002, NFR-004).

**Priority**: Normal.

**Independent success test**: `pytest tests/architecture/test_ownership_manifest_schema.py -v` exits 0 with 9 passing tests; elapsed time ≤1 s on a warm interpreter.

**Included subtasks**:
- [x] T013 Write `tests/architecture/test_ownership_manifest_schema.py` with all 9 assertions from data-model §4 (WP03)
- [x] T014 Edit `architecture/2.x/04_implementation_mapping/README.md` — add prominent cross-link paragraph to `05_ownership_map.md` (WP03) [P]
- [x] T015 Run schema test; confirm all 9 assertions pass in ≤1 s (WP03)
- [x] T016 Verify `python -c "import specify_cli.charter"` raises `ModuleNotFoundError` (WP03)

**Implementation sequence**:
1. T013 + T014 — write test and README edit in parallel.
2. T015 — run schema test to confirm green.
3. T016 — final acceptance check for NFR-004.

**Parallel opportunities**: T013 and T014 are fully independent.

**Dependencies**: WP02 (schema test asserts `charter_governance.shims == []` and verifies that no shim paths listed in the manifest still exist on disk; WP02's deletion must be complete first).

**Risks**:
- `ruamel.yaml` vs PyYAML divergence: use `import yaml; yaml.safe_load()` in the test (PyYAML is already a project dependency; ruamel is only needed for manifest *authoring* in WP01).
- pytest-timeout absent: implement a soft timing assertion (measure time with `time.time()`, emit a warning if >1 s, but don't fail the test hard — NFR-002 is "≤1 s on a baseline dev machine").
- `tests/architecture/` directory may not exist yet: create it with an `__init__.py` if absent.

**Prompt file**: `tasks/WP03-schema-test-and-cross-reference.md`
**Estimated prompt size**: ~270 lines
