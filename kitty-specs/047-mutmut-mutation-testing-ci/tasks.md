---
description: "Work package task list template for feature implementation"
---

# Work Packages: Mutmut Mutation Testing CI Integration

**Inputs**: Design documents from `/kitty-specs/047-mutmut-mutation-testing-ci/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, quickstart.md

**Execution model**: **Sequential only**. Each WP must reach `done` before the next begins.
**No worktrees**: All work is performed directly on the `architecture/restructure_and_proposals` branch.

---

## Work Package WP01: Toolchain Setup (Priority: P0)

**Goal**: Add `mutmut>=3.5.0` to the project and configure it so that `mutmut run`
works locally against `src/specify_cli/` without errors.
**Independent Test**: `mutmut run` completes for at least one module and `mutmut results`
shows killed/surviving/timeout counts without configuration errors.
**Prompt**: `tasks/WP01-toolchain-setup.md`
**Requirement Refs**: FR-001, FR-002, NFR-002, C-001, C-002, SC-001

### Included Subtasks

- [ ] T001 Add `mutmut>=3.5.0` to `[project.optional-dependencies].test` in `pyproject.toml`
- [ ] T002 Add `[tool.mutmut]` configuration section to `pyproject.toml` (paths, runner, excludes)
- [ ] T003 Add `mutmut.db`, `mutmut-cache/`, and `.mutmut-cache` to `.gitignore`
- [ ] T004 Install dependencies locally (`pip install -e ".[test]"`) and run `mutmut run --paths-to-mutate src/specify_cli/status/` to verify config loads
- [ ] T005 Run `mutmut results` and confirm output shows killed/surviving/timeout counts

### Implementation Notes

- The `[tool.mutmut]` section goes in `pyproject.toml` (PEP 517 standard, consistent with ruff/mypy/pytest in this project).
- Runner must use `python -m pytest -x --timeout=30 -q` to avoid spawning a new interpreter per mutant.
- Exclude `src/specify_cli/upgrade/migrations/` (idempotent, hard to mutate meaningfully) and `__pycache__`.
- T004 is a local verification step — the implementer runs mutmut and captures the output to confirm no config errors.

### Parallel Opportunities

- None. Steps are sequential within this WP.

### Dependencies

- None (first WP).

### Risks & Mitigations

- mutmut 3.x `[tool.mutmut]` schema may differ from researched format → check `mutmut --help` and `mutmut run --help` for actual CLI flags if the toml config doesn't load correctly.
- Long run time for full codebase → scope T004 to a single small module (`status/`) to keep verification fast.

---

## Work Package WP02: CI Integration (Priority: P0)

**Goal**: A `mutation-testing` job exists in `ci-quality.yml`, runs on push/dispatch,
uploads HTML + JSON artifacts, and enforces a 0% floor (always passes initially).
**Independent Test**: Push a commit; verify the `mutation-testing` job appears and completes
with artifacts downloadable from the CI run. Verify PR runs skip the job.
**Prompt**: `tasks/WP02-ci-integration.md`
**Requirement Refs**: FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-001, C-003, C-004, SC-002, SC-003, SC-004, SC-005

### Included Subtasks

- [ ] T006 Write `scripts/check_mutation_floor.py` — reads `out/reports/mutation/mutation-stats.json`, computes score, enforces `MUTATION_FLOOR` env var (default 0)
- [ ] T007 Add `mutation-testing` job to `.github/workflows/ci-quality.yml` with `needs: unit-tests`, correct `if:` guard, `timeout-minutes: 75`
- [ ] T008 Add job steps: checkout → Python setup → install `.[test]` → prepare output dir → `mutmut run` → `export-cicd-stats` → `mutmut html` → floor check → upload artifacts
- [ ] T009 Set initial `MUTATION_FLOOR: 0` as a job-level env var in `ci-quality.yml`
- [ ] T010 Verify the `if:` condition skips the job on `pull_request` events (read the condition, confirm logic is correct)

### Implementation Notes

- Mirror the `integration-smoke` job pattern: `if: always() && (github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.run_extended))`.
- `mutmut export-cicd-stats` must run before the floor-check script (ordered steps).
- Artifact name: `mutation-reports`; upload path: `out/reports/mutation/`.
- `check_mutation_floor.py` must handle: zero mutants (warn + exit 0), missing JSON (exit 1 with clear error), score below floor (exit 1 with descriptive message).
- The floor env var lives in the job definition (`env:` block) so it can be edited in one place when raised later.

### Parallel Opportunities

- T006 (script authoring) can be done independently of T007 (CI YAML editing).

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- `mutmut run` may exceed 60-minute budget on full codebase → set `timeout-minutes: 75` to give buffer; mutmut will mark timed-out mutants separately, not fail.
- `export-cicd-stats` output schema differs from researched format → adjust `check_mutation_floor.py` to log the raw JSON if key not found, to aid debugging.

---

## Work Package WP03: Squash Survivors — Batch 1 (status/, glossary/) (Priority: P1)

**Goal**: All killable surviving mutants in `src/specify_cli/status/` and
`src/specify_cli/glossary/` are killed by targeted tests; mutation score for
these modules is measurably higher than the pre-campaign baseline.
**Independent Test**: Run `mutmut run --paths-to-mutate src/specify_cli/status/ src/specify_cli/glossary/`
after adding the new tests; confirm surviving mutant count is lower than before and
all remaining survivors are documented as equivalent.
**Prompt**: `tasks/WP03-squash-batch1-status-glossary.md`
**Requirement Refs**: FR-009, FR-010, FR-011, FR-012, SC-006, SC-007

### Included Subtasks

- [x] T011 Run `mutmut run --paths-to-mutate src/specify_cli/status/` and record surviving mutant IDs and locations
- [x] T012 Triage status/ survivors: classify each as killable or equivalent; for each killable, inspect diff with `mutmut show <id>`
- [x] T013 Write targeted tests in `tests/unit/status/` (or extend existing ones) to kill each killable status/ mutant; re-run to verify kills
- [x] T014 Run `mutmut run --paths-to-mutate src/specify_cli/glossary/` and record surviving mutant IDs and locations
- [x] T015 Triage glossary/ survivors: classify each as killable or equivalent
- [x] T016 Write targeted tests in `tests/unit/glossary/` (or extend existing ones) to kill each killable glossary/ mutant; re-run to verify kills
- [x] T017 Create `kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md` documenting any equivalent mutants with rationale

### Implementation Notes

- A killable mutant is one where a reasonable test can distinguish the original from the mutated behaviour.
- An equivalent mutant is one where the mutation produces semantically identical behaviour (e.g., `x + 0` → `x - 0`); these are documented, not killed.
- Re-run mutmut after each batch of new tests to confirm kills before moving to the next group.
- Focus on correctness-critical code paths: state machine transitions (`status/transitions.py`), JSONL append/read (`status/store.py`), term parsing (`glossary/`).

### Parallel Opportunities

- None (sequential within WP; run status/ first, then glossary/).

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- Many surviving mutants → prioritise by module criticality; kill state machine guards first, then parsers.
- Slow mutmut run per re-check → scope the re-run to a single file once you know which mutants you targeted.

---

## Work Package WP04: Squash Survivors — Batch 2 (merge/, core/) (Priority: P1)

**Goal**: All killable surviving mutants in `src/specify_cli/merge/` and
`src/specify_cli/core/` are killed by targeted tests.
**Independent Test**: Run `mutmut run --paths-to-mutate src/specify_cli/merge/ src/specify_cli/core/`
after test additions; confirm surviving count lower than baseline and all remaining
survivors are documented as equivalent.
**Prompt**: `tasks/WP04-squash-batch2-merge-core.md`
**Requirement Refs**: FR-009, FR-010, FR-012, SC-006, SC-007

### Included Subtasks

- [x] T018 Run `mutmut run --paths-to-mutate src/specify_cli/merge/` and record surviving mutant IDs
- [x] T019 Triage merge/ survivors and write targeted tests in `tests/unit/merge/`; re-run to verify kills
- [x] T020 Run `mutmut run --paths-to-mutate src/specify_cli/core/` and record surviving mutant IDs
- [x] T021 Triage core/ survivors and write targeted tests in `tests/unit/core/`; re-run to verify kills
- [x] T022 Update `kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md` with any equivalent mutants from merge/ and core/

### Implementation Notes

- Focus for merge/: MergeState persistence (`merge/state.py`), preflight validation (`merge/preflight.py`), conflict forecasting (`merge/forecast.py`).
- Focus for core/: Dependency graph utilities, any shared ABCs or protocol definitions.
- Keep the same triage → test → re-run loop as WP03.
- All new tests go under the existing `tests/` hierarchy (e.g., `tests/unit/merge/`, `tests/unit/core/`); create subdirectories if they don't exist.

### Parallel Opportunities

- None (sequential within WP; run merge/ first, then core/).

### Dependencies

- Depends on WP03.

### Risks & Mitigations

- merge/ has integration-level tests (preflight requires git repo) → use `tmp_path` fixtures with a real git init, or mock git calls at the boundary.
- core/ may have few units to mutate → if module is thin, move on quickly.

---

## Work Package WP05: Enforce Floor (Priority: P1)

**Goal**: After the squashing campaign, the mutation score floor is raised to the
achieved score (rounded down to nearest 5%), CI enforces it, and the feature is
complete per spec constraint C-003.
**Independent Test**: `MUTATION_FLOOR=<new-value>` in `ci-quality.yml`; push a commit;
CI mutation-testing job passes. Manually set floor 5% above actual score and confirm
job fails with a descriptive message.
**Prompt**: `tasks/WP05-enforce-floor.md`
**Requirement Refs**: FR-013, C-003, SC-004, SC-006

### Included Subtasks

- [x] T023 Run full mutation suite against all four priority modules (`status/`, `glossary/`, `merge/`, `core/`) and capture the final achieved score from `mutation-stats.json`
- [x] T024 Compute floor value: `floor(score_percent / 5) * 5` (round down to nearest 5%)
- [x] T025 Update `MUTATION_FLOOR` env var in `ci-quality.yml` job to the computed value
- [x] T026 Push and verify the `mutation-testing` CI job passes at the new floor; spot-check by temporarily setting floor 5% above actual to confirm failure path works
- [x] T027 Update `spec.md` constraint C-003 status from `Open` to `Done` with a note of the achieved floor value

### Implementation Notes

- The floor must be > 0 for C-003 to be satisfied. If the squashing campaign produced no kills, escalate before closing this WP.
- The floor value is stored as a plain integer (0–100) in the `MUTATION_FLOOR` env var.
- The failure-path spot-check (T026) is important: it validates the enforcement mechanism is actually wired up and not silently ignored.
- After updating spec.md, the feature can be considered done.

### Parallel Opportunities

- T025 and T027 can be done in parallel (different files).

### Dependencies

- Depends on WP04.

### Risks & Mitigations

- Achieved score is very low (e.g., 5–10%) → still update the floor; the mechanism exists and future campaigns will raise it further.
- CI timeout hit during full-scope run → if the four-module run exceeds the 75-minute timeout, split into two CI runs (status+glossary on one push, merge+core on another) and take the lower score.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → WP04 → WP05 (strictly sequential).
- **Parallelization**: None — this feature uses sequential execution by design to keep the history traceable and avoid merge conflicts in test files.
- **MVP Scope**: WP01 + WP02 constitute the minimum release (toolchain + CI). WP03–WP05 deliver the baseline squashing campaign required by C-003.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP02 |
| FR-004 | WP02 |
| FR-005 | WP02 |
| FR-006 | WP02 |
| FR-007 | WP02 |
| FR-008 | WP02 |
| FR-009 | WP03, WP04 |
| FR-010 | WP03, WP04 |
| FR-011 | WP03 (plan.md defines scope) |
| FR-012 | WP03, WP04 |
| FR-013 | WP05 |
| NFR-001 | WP02 |
| NFR-002 | WP01 |
| C-001 | WP01 |
| C-002 | WP01 |
| C-003 | WP02 (initial 0%), WP05 (raise after squashing) |
| C-004 | WP02 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add mutmut to pyproject.toml test deps | WP01 | P0 | No |
| T002 | Add [tool.mutmut] config section | WP01 | P0 | No |
| T003 | Update .gitignore for mutmut artifacts | WP01 | P0 | No |
| T004 | Local verification run | WP01 | P0 | No |
| T005 | Confirm mutmut results output | WP01 | P0 | No |
| T006 | Write check_mutation_floor.py | WP02 | P0 | Yes |
| T007 | Add mutation-testing CI job | WP02 | P0 | Yes |
| T008 | Add CI job steps | WP02 | P0 | No |
| T009 | Set MUTATION_FLOOR=0 in CI | WP02 | P0 | No |
| T010 | Verify PR skip logic | WP02 | P0 | No |
| T011 | Run mutmut on status/ | WP03 | P1 | No |
| T012 | Triage status/ survivors | WP03 | P1 | No |
| T013 | Write tests to kill status/ mutants | WP03 | P1 | No |
| T014 | Run mutmut on glossary/ | WP03 | P1 | No |
| T015 | Triage glossary/ survivors | WP03 | P1 | No |
| T016 | Write tests to kill glossary/ mutants | WP03 | P1 | No |
| T017 | Create mutmut-equivalents.md (batch 1) | WP03 | P1 | No |
| T018 | Run mutmut on merge/ | WP04 | P1 | No |
| T019 | Triage and kill merge/ survivors | WP04 | P1 | No |
| T020 | Run mutmut on core/ | WP04 | P1 | No |
| T021 | Triage and kill core/ survivors | WP04 | P1 | No |
| T022 | Update mutmut-equivalents.md (batch 2) | WP04 | P1 | No |
| T023 | Run full priority-scope mutation suite | WP05 | P1 | No |
| T024 | Compute floor value | WP05 | P1 | No |
| T025 | Update MUTATION_FLOOR in ci-quality.yml | WP05 | P1 | Yes |
| T026 | Push and verify CI at new floor | WP05 | P1 | No |
| T027 | Update spec.md C-003 status | WP05 | P1 | Yes |

---

> Sequential execution model: start WP01, complete it fully, then move to WP02, and so on.
> No worktrees are used for this feature — all work happens on the target branch directly.

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: done
- WP03: done
- WP04: done
- WP05: done
<!-- status-model:end -->
