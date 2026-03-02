# Feature Specification: Mutmut Mutation Testing CI Integration

**Feature Branch**: `047-mutmut-mutation-testing-ci`
**Created**: 2026-03-01
**Status**: Draft
**Mission**: software-dev

## Overview

Introduce mutation testing to the Spec Kitty project using `mutmut`. Mutation
testing goes beyond line-coverage by verifying that the test suite actually
detects bugs — if mutating a line of production code does not cause at least
one test to fail, the test suite has a coverage gap for that line.

The feature adds mutmut to the project's test toolchain and wires it into CI as
a slow, parallel job so it does not slow down PR feedback loops.

## User Scenarios & Testing

### User Story 1 — Developer runs mutation testing locally (Priority: P1)

A developer wants to run mutation testing against a specific module to check
whether their new tests actually detect all the bugs they are fixing.

**Why this priority**: The primary value is the local developer workflow.
CI integration is secondary but exposes team-level trends.

**Independent Test**: Run `mutmut run` locally against a single module; verify
that the output shows surviving and killed mutants without any external
dependencies.

**Acceptance Scenarios**:

1. **Given** the dev dependency is installed, **When** the developer runs
   `mutmut run`, **Then** mutmut analyses `src/specify_cli/` and prints a
   summary of killed, surviving, and timeout mutants.
2. **Given** a mutant survives, **When** the developer runs `mutmut results`,
   **Then** the output identifies the exact file and line of the surviving
   mutant.

---

### User Story 2 — CI reports mutation score on every push (Priority: P2)

When a maintainer pushes to the repository (or triggers a manual dispatch), the
CI pipeline runs mutation testing in a dedicated job, produces reports, and
makes the mutation score visible without blocking the build.

**Why this priority**: Provides team-level visibility into mutation score trends
without blocking development workflow.

**Independent Test**: Push a commit; verify the `mutation-testing` CI job
appears, runs to completion, and uploads artifacts containing a mutation report.

**Acceptance Scenarios**:

1. **Given** a push event, **When** the CI pipeline runs, **Then** a
   `mutation-testing` job executes after `unit-tests` completes.
2. **Given** the `mutation-testing` job completes, **When** a maintainer views
   CI artifacts, **Then** HTML and JSON mutation reports are available under
   `out/reports/mutation/`.
3. **Given** a PR (not a push), **When** the CI pipeline runs, **Then** the
   `mutation-testing` job is skipped.

---

### User Story 3 — CI enforces a configurable mutation score floor (Priority: P3)

Once the team has established a baseline mutation score, they can raise the
floor to prevent regressions.

**Why this priority**: Foundational quality gate; initially set to 0% so it
never blocks, but the mechanism must exist for future enforcement.

**Independent Test**: Set the floor to a value above the current score; verify
the CI job exits non-zero and the error message cites the floor.

**Acceptance Scenarios**:

1. **Given** a floor of 0%, **When** any mutation score is reported, **Then**
   the job always passes.
2. **Given** a floor of 50%, **When** the mutation score is 40%, **Then** the
   job exits with a non-zero status and a descriptive error message.
3. **Given** a floor of 50%, **When** the mutation score is 55%, **Then** the
   job exits with status 0.

---

### User Story 4 — Developer inspects a surviving mutant and improves tests (Priority: P2)

After a mutation run, a developer discovers that some mutants survived (their
tests did not kill them). They inspect the surviving mutant, understand what
production code variant was not caught, write a new or improved test that kills
the mutant, re-run mutation testing, and confirm the mutant is now killed.

**Why this priority**: The toolchain only delivers value if developers can act
on the results. This story ensures the full fix-iteration loop is usable, not
just the reporting step.

**Independent Test**: Introduce a deliberate mutant-equivalent gap in a small
module, run mutmut, confirm a surviving mutant is reported, write a test that
kills it, re-run, and confirm the mutant is now dead.

**Acceptance Scenarios**:

1. **Given** a surviving mutant is reported, **When** the developer runs
   `mutmut show <id>`, **Then** the tool displays the exact source diff that
   represents the surviving mutant.
2. **Given** the developer adds a test that exercises the mutated code path,
   **When** they re-run `mutmut run`, **Then** the previously surviving mutant
   is now listed as killed and the mutation score improves.
3. **Given** the mutation score improves above the configured floor, **When**
   the developer pushes the changes, **Then** the CI mutation-testing job exits
   successfully.

---

### User Story 5 — Maintainer runs a baseline squashing campaign on existing code (Priority: P1)

Before the feature is considered done, a maintainer runs mutation testing
against the existing codebase, identifies surviving mutants in the
highest-value modules, writes targeted tests to kill those mutants, and then
sets the mutation score floor to the achieved baseline. This transforms the
initial 0% placeholder floor into a meaningful, enforced lower bound that
protects the project going forward.

**Why this priority**: Without this step the toolchain exists but provides no
protection. A floor of 0% never fails, so it conveys no quality signal. Doing
the squashing campaign as part of the feature delivery ensures the tool
produces real value from day one, not just a green CI badge.

**Independent Test**: After the squashing campaign, run the full mutation suite
and verify the score meets or exceeds the agreed floor; verify the CI floor
config reflects the agreed value.

**Scoping rule**: The campaign focuses on modules with clear correctness
invariants (state machines, transition guards, validation logic, event
serialisation). Modules that are primarily CLI glue, thin wrappers, or
already covered at integration level may be deferred to a later campaign.

**Acceptance Scenarios**:

1. **Given** the toolchain is configured, **When** the maintainer runs a full
   mutation pass on the priority scope, **Then** a list of surviving mutants
   and their locations is produced.
2. **Given** the surviving mutant list, **When** the maintainer triages them
   into "killable" and "equivalent" categories, **Then** all killable surviving
   mutants in the priority scope are addressed by new or improved tests.
3. **Given** all killable mutants in scope are killed, **When** the mutation
   suite runs again, **Then** the mutation score for the priority scope is
   measurably higher than the pre-campaign baseline.
4. **Given** the final score after squashing, **When** the maintainer updates
   the floor configuration, **Then** the floor is set to the achieved score
   (rounded down to the nearest 5%) and CI enforces it going forward.

---

### Edge Cases

- What happens when mutmut times out on a slow test? The job should continue
  and count timed-out mutants separately, not fail the run.
- What happens when zero mutants are generated (empty source scope)? The job
  should exit 0 and emit a warning rather than divide-by-zero.
- What happens when the floor check script cannot parse the mutmut report? The
  job should fail with a clear error, not silently pass.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Add mutmut dependency | As a developer, I want mutmut available as a test dependency so that I can run mutation testing locally. | High | Open |
| FR-002 | Configure mutmut scope | As a developer, I want mutmut configured to target `src/specify_cli/` with the existing pytest runner so that results are relevant and reproducible. | High | Open |
| FR-003 | Add mutation-testing CI job | As a maintainer, I want a dedicated mutation-testing CI job so that mutation scores are tracked over time. | High | Open |
| FR-004 | Trigger only on push/dispatch | As a developer, I want mutation testing to be skipped on PRs so that PR feedback loops remain fast. | High | Open |
| FR-005 | Output reports to standard location | As a maintainer, I want mutation reports written to `out/reports/mutation/` so that they are co-located with other CI quality reports. | Medium | Open |
| FR-006 | Upload reports as CI artifacts | As a maintainer, I want mutation reports uploaded as CI artifacts so that they are accessible after the job completes. | Medium | Open |
| FR-007 | Enforce configurable score floor | As a maintainer, I want a configurable mutation score floor so that the team can gradually raise the quality bar. | Medium | Open |
| FR-008 | Run after unit-tests, before SonarCloud | As a maintainer, I want mutation testing to run after unit tests succeed and feed results to SonarCloud so that the pipeline stays logically ordered. | Medium | Open |
| FR-009 | Inspect individual surviving mutants | As a developer, I want to be able to view the exact source diff for a surviving mutant so that I understand what code change the test suite missed. | High | Open |
| FR-010 | Re-run mutation testing after test improvements | As a developer, I want to re-run mutation testing locally after adding or improving tests so that I can verify the mutant is now killed before pushing. | High | Open |
| FR-011 | Define priority scope for initial squashing | As a maintainer, I want a documented list of priority modules for the baseline squashing campaign so that effort is focused where correctness matters most. | High | Open |
| FR-012 | Execute baseline squashing campaign | As a maintainer, I want surviving mutants in the priority scope killed by targeted tests so that the mutation score floor reflects real test quality, not just a 0% placeholder. | High | Open |
| FR-013 | Set floor to achieved baseline after squashing | As a maintainer, I want the mutation score floor updated to the score achieved after the squashing campaign so that future regressions are automatically caught by CI. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No PR slowdown | Mutation testing must not add any time to PR CI runs (skipped entirely on pull_request events). | Performance | High | Open |
| NFR-002 | Reproducible local runs | Running mutmut locally produces the same configuration as CI (same source paths, same test runner). | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | mutmut version | Must use `mutmut>=3.5.0` (3.x CLI, not 2.x). | Technical | High | Open |
| C-002 | No new test runner | Must use the existing pytest suite; no second test framework introduced. | Technical | High | Open |
| C-003 | Initial floor at 0%, raised after squashing | The floor starts at 0% so no builds are blocked during setup. After the baseline squashing campaign completes it must be raised to the achieved score (rounded down to nearest 5%). The feature is not done while the floor remains at 0%. | Business | High | Done — floor raised to 70% (baseline 70.5%, 2026-03-02) |
| C-004 | Report path convention | Report output paths must follow the `out/reports/<category>/` convention already established in CI. | Technical | Medium | Open |

## Success Criteria

### Measurable Outcomes

- **SC-001**: Running `mutmut run` locally completes without configuration errors and produces output for `src/specify_cli/`.
- **SC-002**: A push to the repository triggers the `mutation-testing` CI job within the existing `ci-quality.yml` workflow.
- **SC-003**: HTML and JSON mutation reports appear as downloadable CI artifacts after every push run.
- **SC-004**: Setting the mutation score floor above the actual score causes the CI job to exit non-zero with a descriptive message.
- **SC-005**: PRs never trigger the mutation-testing job (verified by `if:` condition on the job).
- **SC-006**: After the baseline squashing campaign, the mutation score for the priority scope is measurably higher than the pre-campaign baseline, and CI enforces a floor greater than 0%.
- **SC-007**: All surviving mutants in the priority scope are either killed by targeted tests or explicitly classified as equivalent mutants with a written rationale.

## Assumptions

1. mutmut 3.x produces parseable output for score extraction; implementation adapts to the 3.x API if it differs from 2.x.
2. The existing pytest suite runs without external service dependencies in mutation CI runs.
3. Mutation runs may take up to 60 minutes per push; CI timeout for this job is set accordingly.
4. Excluding `tests/`, `.venv/`, and generated files from the mutation scope is a reasonable default configured in `pyproject.toml`.

## Out of Scope

- Incremental mutation testing (only mutating changed lines) — future enhancement.
- Per-file or per-module score floors — a single project-level floor is sufficient.
- Automatic floor ratcheting — the floor is manually adjusted by maintainers.
