# Implementation Plan: Mutmut Mutation Testing CI Integration
*Path: [templates/plan-template.md](templates/plan-template.md)*

**Branch**: `architecture/restructure_and_proposals` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/047-mutmut-mutation-testing-ci/spec.md`

## Summary

Add `mutmut>=3.5.0` to the project's test dependency group, configure it via
`[tool.mutmut]` in `pyproject.toml` to target `src/specify_cli/` using the
existing pytest runner, and wire it into `.github/workflows/ci-quality.yml`
as a slow, push-only parallel job that runs after `unit-tests`. The job writes
HTML and JSON reports to `out/reports/mutation/`, uploads them as CI artifacts,
and enforces a configurable mutation-score floor (initially 0%). After the
toolchain is in place, a two-phase baseline squashing campaign kills surviving
mutants in the priority scope (`status/`, `glossary/`, `merge/`, `core/`) and
raises the floor to the achieved score.

**Execution model**: Work packages are executed **sequentially**. Each WP
progresses through its full lifecycle (planned → in_progress → for_review → done)
before the next WP begins. **No worktrees are created**; all work happens
directly in the planning repository on the `architecture/restructure_and_proposals`
branch.

## Technical Context

**Language/Version**: Python 3.12 (CI matrix), 3.11+ (supported range)
**Primary Dependencies**: mutmut>=3.5.0, pytest (existing), pytest-cov (existing)
**Storage**: Filesystem — `out/reports/mutation/` for HTML/JSON output; `mutmut.db` SQLite cache written to project root during runs (`.gitignore`-eligible)
**Testing**: pytest (existing suite, no second framework introduced)
**Target Platform**: Linux (CI: ubuntu-latest); developer workstations (Linux/macOS)
**Project Type**: Single Python project (`src/` layout)
**Performance Goals**: Mutation run must complete within 60 min (CI job timeout)
**Constraints**:
- mutmut>=3.5.0 only (3.x CLI; 2.x config format incompatible)
- No PRs triggered — job guarded with `if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'`
- Initial floor at 0% (non-blocking); must be raised after squashing campaign
- Report output path must follow `out/reports/<category>/` convention

## Constitution Check

No constitution file found at `.kittify/memory/constitution.md` — section
skipped. No constitution gates apply. Standard project conventions apply:
- Ruff lint must pass
- mypy type-check must pass
- Tests must not regress
- CI additions must follow existing job patterns

## Project Structure

### Documentation (this feature)

```
kitty-specs/047-mutmut-mutation-testing-ci/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── quickstart.md        # Phase 1 output (local workflow guide)
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
pyproject.toml                          # Add mutmut to [project.optional-dependencies].test
                                        # Add [tool.mutmut] config section

.github/workflows/ci-quality.yml        # Add mutation-testing job

scripts/check_mutation_floor.py         # Inline floor-check helper (new)
                                        # Reads out/reports/mutation/mutation-stats.json
                                        # Exits non-zero if score < configured floor

out/reports/mutation/                   # Runtime output (gitignored)
  ├── index.html                        # mutmut HTML report
  └── mutation-stats.json               # mutmut JSON stats (export-cicd-stats)

tests/                                  # Expanded during WP03-WP04 squashing
  ├── unit/
  │   ├── status/                       # New targeted tests (WP03)
  │   ├── glossary/                     # New targeted tests (WP03)
  │   ├── merge/                        # New targeted tests (WP04)
  │   └── core/                         # New targeted tests (WP04)
  └── ...                               # Existing test files untouched
```

**Structure Decision**: Single Python project. Changes are surgical: two config
files modified (`pyproject.toml`, `ci-quality.yml`), one new helper script
(`scripts/check_mutation_floor.py`), and targeted test additions under the
existing `tests/` hierarchy during the squashing WPs.

## Complexity Tracking

No constitution violations. The floor-check helper (`scripts/check_mutation_floor.py`)
is a ~30-line inline script justified by the absence of a built-in score-floor
mechanism in mutmut 3.x. A simpler one-liner `bash` floor check was rejected
because JSON parsing in bash is fragile and the logic is non-trivial (handle
zero-mutant edge case, produce a descriptive error message).

## Work Packages

WPs are executed **strictly in order**. Do not start WP(n+1) until WP(n) is done.

| WP | Title | Depends On | Scope |
|----|-------|------------|-------|
| WP01 | Toolchain Setup | — | `pyproject.toml` dependency + `[tool.mutmut]` config; verify `mutmut run` locally |
| WP02 | CI Integration | WP01 | Add `mutation-testing` job to `ci-quality.yml`; floor script; artifact upload |
| WP03 | Squash Survivors — Batch 1 | WP02 | Kill surviving mutants in `status/` and `glossary/` |
| WP04 | Squash Survivors — Batch 2 | WP03 | Kill surviving mutants in `merge/` and `core/` |
| WP05 | Enforce Floor | WP04 | Run full suite, compute achieved score, raise floor in config, verify CI |

### WP01 — Toolchain Setup

**Goal**: `mutmut run` works locally against `src/specify_cli/` with no
configuration errors and produces a results summary.

**Tasks**:
1. Add `mutmut>=3.5.0` to `[project.optional-dependencies].test` in `pyproject.toml`
2. Add `[tool.mutmut]` section to `pyproject.toml`:
   - `paths_to_mutate = ["src/specify_cli/"]`
   - Exclude test files, generated files, and `__pycache__`
   - Runner set to `python -m pytest` (reuse existing suite)
3. Add `mutmut.db` and `mutmut-cache/` to `.gitignore`
4. Run `mutmut run` locally against a single module to verify config loads
5. Run `mutmut results` and confirm output is parseable

**Acceptance**: `mutmut run` completes for at least one module without config
errors; `mutmut results` shows killed/surviving/timeout counts.

### WP02 — CI Integration

**Goal**: Push event triggers a `mutation-testing` job that runs to completion,
uploads HTML + JSON artifacts, and enforces the (initially 0%) floor.

**Tasks**:
1. Write `scripts/check_mutation_floor.py`:
   - Read `out/reports/mutation/mutation-stats.json`
   - Extract killed/total counts; compute score
   - Handle zero-mutant edge case (exit 0, emit warning)
   - Compare score to `MUTATION_FLOOR` env var (default 0)
   - Exit non-zero with descriptive message if score < floor
2. Add `mutation-testing` job to `.github/workflows/ci-quality.yml`:
   - `needs: unit-tests`
   - `if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'`
   - `timeout-minutes: 75`
   - Steps: checkout → Python setup → install `.[test]` → prepare `out/reports/mutation/` →
     run `mutmut run` → export stats → export HTML → run floor check → upload artifacts
3. Verify PR runs do **not** trigger the job (inspect `if:` condition)

**Acceptance**: Push triggers job; HTML + JSON appear as downloadable artifacts;
PR runs skip job entirely; floor=0 always passes.

### WP03 — Squash Survivors — Batch 1 (status/, glossary/)

**Goal**: All killable surviving mutants in `src/specify_cli/status/` and
`src/specify_cli/glossary/` are killed by targeted tests.

**Tasks**:
1. Run `mutmut run` scoped to `status/` and `glossary/`
2. Triage surviving mutants: classify as killable vs. equivalent
3. For each killable mutant: write a targeted test, verify `mutmut show <id>` matches
4. Re-run `mutmut run` and confirm mutant is now dead
5. Document any equivalent mutants with written rationale in a `mutmut-equivalents.md`
   file (if any exist)

**Acceptance**: No killable surviving mutants remain in `status/` and `glossary/`;
mutation score for these modules is measurably higher than pre-campaign baseline.

### WP04 — Squash Survivors — Batch 2 (merge/, core/)

**Goal**: All killable surviving mutants in `src/specify_cli/merge/` and
`src/specify_cli/core/` are killed by targeted tests.

**Tasks** (same pattern as WP03, different modules):
1. Run `mutmut run` scoped to `merge/` and `core/`
2. Triage, classify, kill surviving mutants
3. Re-run to confirm kills
4. Update `mutmut-equivalents.md` if applicable

**Acceptance**: No killable surviving mutants remain in `merge/` and `core/`;
score measurably higher than pre-campaign baseline.

### WP05 — Enforce Floor

**Goal**: CI enforces a meaningful mutation score floor that reflects the
achieved baseline after the squashing campaign.

**Tasks**:
1. Run the full mutation suite against all four modules in priority scope
2. Record the achieved score
3. Round down to the nearest 5%
4. Update `MUTATION_FLOOR` env var (or constant) in `ci-quality.yml` to the
   rounded value
5. Push and verify the `mutation-testing` CI job passes at the new floor
6. Update `spec.md` constraints (C-003) status from Open → Done

**Acceptance**: `MUTATION_FLOOR > 0`; CI passes at the new floor; SC-006 and
SC-007 are demonstrably met.
