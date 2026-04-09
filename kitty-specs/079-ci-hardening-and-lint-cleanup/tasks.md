# Tasks: CI Hardening and Lint Cleanup (Mission 079)

**Branch**: `feat/079-ci-hardening-and-lint-cleanup` → merges into `main`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

---

## Subtask Index

| ID | Description | WP | [P] |
|----|-------------|-----|-----|
| T001 | Fix ARG001: unused `doctrine_root` arg in `charter/catalog.py:245` | WP01 | P | [D] |
| T002 | Fix SIM108: if/else → ternary in `charter/resolver.py:120` | WP01 | P | [D] |
| T003 | Fix B009: `getattr` with constant → direct attr in `glossary_hook.py:134` | WP01 | P | [D] |
| T004 | Fix SIM105: try/except/pass → `contextlib.suppress` in `_safe_re.py:185` | WP01 | P | [D] |
| T005 | Verify WP01 files pass ruff check and tests | WP01 | | [D] |
| T006 | Move logger init below imports in `acceptance.py` (E402 root cause) | WP02 | |
| T007 | Remove unused imports (MutableMapping, extract_scalar, find_repo_root) | WP02 | |
| T008 | Replace deprecated `typing.*` with builtins/`collections.abc` (UP035) | WP02 | |
| T009 | Verify `acceptance.py` passes ruff + mypy, run affected tests | WP02 | |
| T010 | Inspect current `MissionDossier` and `ArtifactRef` constructor signatures | WP03 | | [D] |
| T011 | Fix `MissionDossier(...)` call sites in `test_snapshot.py` (3 sites) | WP03 | | [D] |
| T012 | Fix `ArtifactRef(...)` call sites in `test_snapshot.py` (6 sites) | WP03 | | [D] |
| T013 | Verify mypy passes for `test_snapshot.py`; all dossier tests pass | WP03 | | [D] |
| T014 | Remove 4 stale ignores from `post_merge/stale_assertions.py` (lines 317,319,322,324) | WP04 | P |
| T015 | Remove stale ignore from `merge/config.py:57` | WP04 | P |
| T016 | Remove stale ignore from `migration/rebuild_state.py:38` | WP04 | P |
| T017 | Fix `migration/backfill_identity.py:36`: fix no-any-return + remove stale ignore | WP04 | P |
| T018 | Fix `policy/audit.py:27`: fix no-any-return + remove stale ignore | WP04 | P |
| T019 | Verify mypy passes for all 5 WP04 files; no regressions | WP04 | |
| T020 | Fix bare `dict`/`list` generics in state_contract.py, acceptance_matrix.py, doctrine/missions/repository.py, migration/backfill_ownership.py | WP05 | P |
| T021 | Fix `no-any-return` in version_utils.py, upgrade/feature_meta.py, doctrine/missions/repository.py, migration/backfill_identity.py | WP05 | P |
| T022 | Fix missing return type annotations in `sync/config.py:15,39` | WP05 | P |
| T023 | Fix type incompatibilities in `merge/conflict_resolver.py:172` and `cli/commands/materialize.py:123` | WP05 | P |
| T024 | Fix `tracker/credentials.py`: remove stale ignore (line 15) + fix None→Module assignment (line 17) | WP05 | P |
| T025 | Add `types-requests` to dev dependencies in `pyproject.toml` | WP05 | P |
| T026 | Verify `mypy --strict src/` exits 0 for all FR-002 files; run full test suite | WP05 | |
| T027 | Measure aggregate coverage for Tier A modules (status, lanes, kernel, sync) | WP06 | P |
| T028 | Measure aggregate coverage for Tier B modules (next, review, merge, cli, missions, upgrade) | WP06 | P |
| T029 | Measure aggregate coverage for Tier C modules (dashboard, release, orchestrator_api, post_merge, core-misc) | WP06 | P |
| T030 | Apply floor formula and write `coverage-baseline.md` | WP06 | |
| T031 | Verify zero test failures in baseline run; flag any failures before proceeding | WP06 | |
| T032 | Classify and add markers to all 12 `tests/lanes/` test files | WP07 | P |
| T033 | Classify and add markers to all 6 `tests/review/` test files | WP07 | P |
| T034 | Classify and add markers to all 7 `tests/merge/` test files | WP07 | P |
| T035 | Classify and add markers to all 3 `tests/cli/` test files | WP07 | P |
| T036 | Verify all newly-marked tests pass; confirm `pytest -m fast` runs cleanly for these modules | WP07 | |
| T037 | Inspect `tests/next/` git_repo tests; identify shift-left candidates | WP08 | |
| T038 | Convert eligible `tests/next/` git_repo tests to fast; document non-eligible ones | WP08 | |
| T039 | Inspect `tests/missions/` git_repo tests; identify shift-left candidates | WP08 | |
| T040 | Convert eligible `tests/missions/` git_repo tests to fast; document non-eligible ones | WP08 | |
| T041 | Verify full test suite passes; confirm coverage does not decrease post-shift | WP08 | |
| T042 | Add workflow-level `paths:` trigger to `ci-quality.yml` for docs-only skip | WP09 | |
| T043 | Add `changes` detection job using `dorny/paths-filter` with module-level filters | WP09 | |
| T044 | Define Tier 0 per-module `fast-tests` jobs (sync, merge, missions, post_merge, release) with `if:` path conditions | WP09 | |
| T045 | Define Tier 1 `fast-tests-status` job with `needs: [changes, fast-tests-sync]` and path condition | WP09 | |
| T046 | Define Tier 2 `fast-tests` jobs (review, next, lanes, dashboard, upgrade) with DAG `needs:` and path conditions | WP09 | |
| T047 | Define Tier 3 `fast-tests` jobs (cli, orchestrator_api, core-misc) with full DAG `needs:` | WP09 | |
| T048 | Add `integration-tests-<module>` job pairs for modules with git_repo/integration tests; apply coverage floors from `coverage-baseline.md` | WP09 | |
| T049 | Remove `fast-tests-core` and `integration-tests-core`; update `report` and `quality-gate` jobs | WP09 | |
| T050 | Add skip-pass shim jobs for all jobs that are required branch-protection checks | WP09 | |
| T051 | Confirm current required-checks list with repo owner (pre-merge gate for WP10) | WP10 | |
| T052 | Add path filter to `orchestrator-boundary.yml` (FR-014) | WP10 | |
| T053 | Add path filter to `check-spec-kitty-events-alignment.yml` (FR-015) | WP10 | |
| T054 | Validate docs-only PR behavior: open a draft PR with only `*.md` changes; confirm no Python jobs run | WP10 | |
| T055 | Confirm `quality-gate` passes on `main` with full migration applied | WP10 | |

---

## Work Packages

### Batch 1 — Lint and Type Fixes (WP01–WP05, parallel)

All five WPs are independent and can run simultaneously in separate lanes. None touches the same source file. Merge to feature branch as each completes.

---

#### WP01 — Auto-Fix Ruff Violations

**Priority:** High | **Effort:** Small | **Estimated prompt:** ~260 lines
**Goal:** Fix 4 isolated ruff violations in 4 different files using auto-fix tooling.
**Success:** `ruff check src/charter/catalog.py src/charter/resolver.py src/doctrine/missions/glossary_hook.py src/kernel/_safe_re.py` exits 0.

**Includes:**
- [x] T001 Fix ARG001: unused `doctrine_root` arg in `charter/catalog.py:245` (WP01)
- [x] T002 Fix SIM108: if/else → ternary in `charter/resolver.py:120` (WP01)
- [x] T003 Fix B009: `getattr` with constant → direct attr in `glossary_hook.py:134` (WP01)
- [x] T004 Fix SIM105: try/except/pass → `contextlib.suppress` in `_safe_re.py:185` (WP01)
- [x] T005 Verify WP01 files pass ruff check and tests (WP01)

**Parallel opportunities:** T001–T004 each touch a different file; safe to apply all at once.
**Dependencies:** None
**Prompt:** [WP01-auto-fix-ruff-violations.md](tasks/WP01-auto-fix-ruff-violations.md)

---

#### WP02 — Fix acceptance.py Import Ordering

**Priority:** High | **Effort:** Small | **Estimated prompt:** ~220 lines
**Goal:** Resolve the E402 cascade in `acceptance.py` (logger before imports) and clean up the UP035/F401 violations on the same line.
**Success:** `ruff check src/specify_cli/acceptance.py` and `mypy src/specify_cli/acceptance.py` both exit 0.

**Includes:**
- [ ] T006 Move logger init below imports in `acceptance.py` (E402 root cause) (WP02)
- [ ] T007 Remove unused imports (MutableMapping, extract_scalar, find_repo_root) (WP02)
- [ ] T008 Replace deprecated `typing.*` with builtins/`collections.abc` (UP035) (WP02)
- [ ] T009 Verify `acceptance.py` passes ruff + mypy, run affected tests (WP02)

**Dependencies:** None
**Prompt:** [WP02-fix-acceptance-import-ordering.md](tasks/WP02-fix-acceptance-import-ordering.md)

---

#### WP03 — Fix Dossier Test Schema Drift

**Priority:** High | **Effort:** Small–Medium | **Estimated prompt:** ~280 lines
**Goal:** Fix the 25+ mypy call-arg errors in `test_snapshot.py` caused by `MissionDossier` and `ArtifactRef` schema drift.
**Success:** `mypy src/specify_cli/dossier/tests/test_snapshot.py` exits 0; all dossier tests pass.

**Includes:**
- [x] T010 Inspect current `MissionDossier` and `ArtifactRef` constructor signatures (WP03)
- [x] T011 Fix `MissionDossier(...)` call sites in `test_snapshot.py` (3 sites) (WP03)
- [x] T012 Fix `ArtifactRef(...)` call sites in `test_snapshot.py` (6 sites) (WP03)
- [x] T013 Verify mypy passes for `test_snapshot.py`; all dossier tests pass (WP03)

**Risk:** If tests are testing deprecated behavior (not just wrong signatures), escalate — do not silently fix.
**Dependencies:** None
**Prompt:** [WP03-fix-dossier-schema-drift.md](tasks/WP03-fix-dossier-schema-drift.md)

---

#### WP04 — Remove Stale type: ignore Comments

**Priority:** Medium | **Effort:** Small | **Estimated prompt:** ~300 lines
**Goal:** Remove 6 stale `# type: ignore` suppressions; for two files, also fix the underlying violation that the ignore was (incorrectly) trying to suppress.
**Success:** Zero `unused-ignore` mypy errors across all 5 files.

**Includes:**
- [ ] T014 Remove 4 stale ignores from `post_merge/stale_assertions.py` (lines 317,319,322,324) (WP04)
- [ ] T015 Remove stale ignore from `merge/config.py:57` (WP04)
- [ ] T016 Remove stale ignore from `migration/rebuild_state.py:38` (WP04)
- [ ] T017 Fix `migration/backfill_identity.py:36`: fix no-any-return + remove stale ignore (WP04)
- [ ] T018 Fix `policy/audit.py:27`: fix no-any-return + remove stale ignore (WP04)
- [ ] T019 Verify mypy passes for all 5 WP04 files; no regressions (WP04)

**Parallel opportunities:** T014–T018 each touch a different file.
**Dependencies:** None
**Prompt:** [WP04-remove-stale-type-ignores.md](tasks/WP04-remove-stale-type-ignores.md)

---

#### WP05 — Fix Remaining Mypy Violations

**Priority:** High | **Effort:** Medium | **Estimated prompt:** ~380 lines
**Goal:** Fix bare generic types, no-any-return violations, missing return annotations, type incompatibilities, and add `types-requests` stub.
**Success:** `mypy --strict src/` reports zero errors for all files in FR-002.

**Includes:**
- [ ] T020 Fix bare `dict`/`list` generics (4 files) (WP05)
- [ ] T021 Fix `no-any-return` violations (4 files) (WP05)
- [ ] T022 Fix missing return type annotations in `sync/config.py` (WP05)
- [ ] T023 Fix type incompatibilities in `conflict_resolver.py` and `materialize.py` (WP05)
- [ ] T024 Fix `tracker/credentials.py`: stale ignore + None→Module assignment (WP05)
- [ ] T025 Add `types-requests` to dev dependencies in `pyproject.toml` (WP05)
- [ ] T026 Verify `mypy --strict src/` exits 0 for all FR-002 files; full test suite passes (WP05)

**Dependencies:** None (T017/T018 in WP04 are coordinated by file ownership, no overlap)
**Prompt:** [WP05-fix-remaining-mypy-violations.md](tasks/WP05-fix-remaining-mypy-violations.md)

---

### Batch 2 — Coverage Baseline and Test Quality (WP06–WP08, sequential)

WP06 must complete first (produces `coverage-baseline.md`). WP07 follows (marker cataloguing changes which tests are in scope for marker-filtered runs). WP08 follows WP07 (some tests being shifted may receive or change markers during cataloguing).

---

#### WP06 — Measure Per-Module Coverage Baseline

**Priority:** High | **Effort:** Small | **Estimated prompt:** ~260 lines
**Goal:** Run the full test suite (all markers) per module cluster and produce `coverage-baseline.md` with measured percentages and calibrated floors.
**Success:** `coverage-baseline.md` committed; no test failures during baseline run.

**Includes:**
- [ ] T027 Measure aggregate coverage for Tier A modules (status, lanes, kernel, sync) (WP06)
- [ ] T028 Measure aggregate coverage for Tier B modules (next, review, merge, cli, missions, upgrade) (WP06)
- [ ] T029 Measure aggregate coverage for Tier C modules (dashboard, release, orchestrator_api, post_merge, core-misc) (WP06)
- [ ] T030 Apply floor formula and write `coverage-baseline.md` (WP06)
- [ ] T031 Verify zero test failures in baseline run (WP06)

**Dependencies:** WP01, WP02, WP03, WP04, WP05 (clean baseline requires passing tests)
**Prompt:** [WP06-coverage-baseline-measurement.md](tasks/WP06-coverage-baseline-measurement.md)

---

#### WP07 — Test Marker Cataloguing

**Priority:** High | **Effort:** Medium | **Estimated prompt:** ~310 lines
**Goal:** Add pytest markers to all test functions in `tests/lanes/`, `tests/review/`, `tests/merge/`, and `tests/cli/` that currently have zero markers.
**Success:** Zero unmarked test functions in the four targeted module directories.

**Includes:**
- [ ] T032 Classify and add markers to all 12 `tests/lanes/` test files (WP07)
- [ ] T033 Classify and add markers to all 6 `tests/review/` test files (WP07)
- [ ] T034 Classify and add markers to all 7 `tests/merge/` test files (WP07)
- [ ] T035 Classify and add markers to all 3 `tests/cli/` test files (WP07)
- [ ] T036 Verify all newly-marked tests pass; confirm `pytest -m fast` runs cleanly (WP07)

**Dependencies:** Depends on WP06 (coverage-baseline.md must exist before marking changes coverage accounting)
**Prompt:** [WP07-test-marker-cataloguing.md](tasks/WP07-test-marker-cataloguing.md)

---

#### WP08 — Shift-Left Test Migration

**Priority:** Medium | **Effort:** Medium | **Estimated prompt:** ~320 lines
**Goal:** Identify and convert git_repo-marked tests in `tests/next/` and `tests/missions/` that do not require real git operations to fast-marked tests.
**Success:** At least 3 tests shifted to fast tier; no coverage decrease; all tests pass.

**Includes:**
- [ ] T037 Inspect `tests/next/` git_repo tests; identify shift-left candidates (WP08)
- [ ] T038 Convert eligible `tests/next/` tests from git_repo to fast (WP08)
- [ ] T039 Inspect `tests/missions/` git_repo tests; identify shift-left candidates (WP08)
- [ ] T040 Convert eligible `tests/missions/` tests from git_repo to fast (WP08)
- [ ] T041 Verify full test suite passes; confirm coverage does not decrease (WP08)

**Dependencies:** Depends on WP07 (marker cataloguing must complete so overall marker state is stable)
**Prompt:** [WP08-shift-left-test-migration.md](tasks/WP08-shift-left-test-migration.md)

---

### Batch 3 — CI Structure (WP09–WP10, sequential)

WP09 must complete and merge before WP10 begins. WP10 depends on per-module job names that WP09 creates.

---

#### WP09 — Per-Module CI Job Split and Path Filter

**Priority:** High | **Effort:** Large | **Estimated prompt:** ~560 lines
**Goal:** Replace monolithic `fast-tests-core`/`integration-tests-core` with per-module job pairs organised in the verified DAG, with path-based triggering and coverage floor gates from `coverage-baseline.md`.
**Success:** All new per-module jobs pass on `main`; `quality-gate` passes; no test runs twice.

**Includes:**
- [ ] T042 Add workflow-level `paths:` trigger for docs-only skip (WP09)
- [ ] T043 Add `changes` detection job using `dorny/paths-filter` (WP09)
- [ ] T044 Define Tier 0 `fast-tests` jobs with path conditions (WP09)
- [ ] T045 Define Tier 1 `fast-tests-status` job with DAG `needs:` (WP09)
- [ ] T046 Define Tier 2 `fast-tests` jobs with DAG `needs:` and path conditions (WP09)
- [ ] T047 Define Tier 3 `fast-tests` jobs (cli, orchestrator_api, core-misc) (WP09)
- [ ] T048 Add `integration-tests-<module>` job pairs with coverage floors (WP09)
- [ ] T049 Remove old monolithic jobs; update `report` and `quality-gate` (WP09)
- [ ] T050 Add skip-pass shim jobs for required-check jobs (WP09)

**Dependencies:** Depends on WP06 (coverage floors), WP07 (all tests marked), WP08 (shift-left done)
**Prompt:** [WP09-per-module-ci-job-split.md](tasks/WP09-per-module-ci-job-split.md)

---

#### WP10 — External Workflow Filters and Validation

**Priority:** High | **Effort:** Small | **Estimated prompt:** ~260 lines
**Goal:** Add path filters to `orchestrator-boundary.yml` and `check-spec-kitty-events-alignment.yml`; coordinate branch protection required-checks update; validate the full migration end-to-end.
**Success:** All FR-010–FR-015 acceptance criteria satisfied; `quality-gate` passes on `main`.

**Includes:**
- [ ] T051 Confirm current required-checks list with repo owner (WP10)
- [ ] T052 Add path filter to `orchestrator-boundary.yml` (FR-014) (WP10)
- [ ] T053 Add path filter to `check-spec-kitty-events-alignment.yml` (FR-015) (WP10)
- [ ] T054 Validate docs-only PR behavior via draft PR (WP10)
- [ ] T055 Confirm `quality-gate` passes on `main` (WP10)

**Dependencies:** Depends on WP09
**Prompt:** [WP10-external-workflow-filters-and-validation.md](tasks/WP10-external-workflow-filters-and-validation.md)
