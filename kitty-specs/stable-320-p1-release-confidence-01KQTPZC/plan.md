# Implementation Plan: Stable 3.2.0 P1 Release Confidence

**Branch**: `main` | **Date**: 2026-05-05 | **Spec**: [/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/spec.md](/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/spec.md)
**Input**: Mission specification from `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/spec.md`

## Summary

Close the post-PR #972 P1 release-readiness tranche for stable `3.2.0` with four focused workstreams: make task-board progress labels match their numerator and percentage semantics, verify or harden installed-vs-lock drift coverage for `spec-kitty-events`, run fresh local-only and SaaS-enabled lifecycle smokes, and compile release evidence with explicit #971 and P2/P3 deferrals.

Engineering alignment: keep the implementation local to status rendering, release drift verification, smoke documentation, and release evidence artifacts. Do not reopen PR #972 P0 blockers unless there is a fresh repro. Do not absorb #971 unless plan/task review explicitly creates a separate WP for strict mypy cleanup.

## Technical Context

**Language/Version**: Python 3.11+ for CLI/library code; CI and release jobs also exercise Python 3.12  
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy, packaging, uv, spec-kitty-events, spec-kitty-tracker  
**Storage**: Filesystem mission artifacts under `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC`; canonical WP status from `status.events.jsonl`; dependency resolution from `uv.lock` and installed package metadata  
**Testing**: Focused pytest coverage for status progress semantics, release drift guards, CLI JSON output, and workflow smoke commands; final evidence includes `uv run ruff check src tests`  
**Target Platform**: Spec Kitty CLI on macOS/Linux/Windows with Git; local smoke on this macOS workspace; SaaS-enabled smoke against the dev deployment only where hosted/sync paths are touched  
**Project Type**: Python CLI repository with mission planning artifacts and GitHub Actions release gates  
**Performance Goals**: Status rendering remains sub-2 seconds for typical missions and supports 100+ WPs without changing status computation complexity; drift guard adds only a small release/review preflight cost  
**Constraints**: Use `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on this computer for hosted auth, tracker, SaaS, or sync command paths; do not loosen dependency constraints as a substitute for detecting drift; do not alter closed P0 behavior without a fresh repro  
**Scale/Scope**: Two scoped issues (#966 and #848), two fresh smoke runs, one release evidence package, no broad release hygiene expansion

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter standard | Plan response | Status |
|---|---|---|
| Python 3.11+ and existing CLI stack | Work stays in existing Python CLI surfaces and existing dependencies. | PASS |
| pytest coverage for new behavior | WP01 requires approved/done/mixed/empty regression tests; WP02 requires guard or evidence tests if code changes. | PASS |
| mypy strict quality | #971 is explicitly deferred by default; if included, it becomes a separate WP with strict mypy evidence. | PASS WITH RECORDED DEFERRAL |
| CLI operations under typical 2 second target | Status output change is label/metadata work; drift guard should run only in review/release gates, not every status render. | PASS |
| External package boundaries | `spec-kitty-events` and `spec-kitty-tracker` remain external dependencies; no vendoring or path dependencies. | PASS |
| Branch strategy | Current branch `main`; planning/base branch `main`; completed changes merge into `main`; `branch_matches_target=true`. | PASS |
| User customization preservation | No command/skill installation or cleanup mutation is planned. | PASS |
| SaaS sync rule | Hosted/tracker/sync smoke commands must set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | PASS |
| Canonical Mission terminology | New planning artifacts use Mission as the canonical domain term except where quoting existing CLI flag names or source paths. | PASS |

## Project Structure

### Documentation For This Mission

```
/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- dependency-drift-guard.md
|   |-- smoke-workflow-contract.md
|   `-- task-progress-status.md
|-- checklists/
|   `-- requirements.md
`-- tasks/
    `-- README.md
```

### Source Code

```
/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/
|-- src/specify_cli/cli/commands/agent/tasks.py
|-- src/specify_cli/status/progress.py
|-- src/specify_cli/agent_utils/status.py
|-- scripts/release/check_shared_package_drift.py
|-- scripts/release/check_exact_install.py
|-- .github/workflows/check-spec-kitty-events-alignment.yml
|-- .github/workflows/release-readiness.yml
|-- .github/workflows/ci-quality.yml
|-- .github/workflows/release.yml
|-- tests/specify_cli/status/
|-- tests/specify_cli/cli/commands/agent/
|-- tests/status/
|-- tests/release/
`-- tests/contract/
```

**Structure Decision**: Use the existing CLI/status/release-test layout. Keep #966 inside status rendering and progress result semantics. Keep #848 inside existing release-script and release-test surfaces unless verification proves current CI already covers the installed environment.

## Phase 0 Research Findings

See [/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/research.md](/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/research.md).

Key decisions:

- Keep weighted readiness as a valid metric, but do not label it as done progress.
- Introduce or document separate done and ready/weighted fields for touched JSON output.
- Verify #848 before changing code because existing release workflows already compare lockfile versions, package constraints, and SaaS pins; the missing risk to prove or close is installed environment drift.
- Treat local-only and SaaS-enabled smokes as release evidence, not as broad new product work.

## Phase 1 Design

See:

- [/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/data-model.md](/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/data-model.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/task-progress-status.md](/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/task-progress-status.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/dependency-drift-guard.md](/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/dependency-drift-guard.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/smoke-workflow-contract.md](/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/smoke-workflow-contract.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/quickstart.md](/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/quickstart.md)

## Planned Work Packages

### WP01 Task Board Progress Semantics (#966)

Owner surface:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/src/specify_cli/cli/commands/agent/tasks.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/src/specify_cli/agent_utils/status.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/src/specify_cli/status/progress.py` only if the result object needs additional named semantics

Plan:

- Keep `done_count` as done-only.
- Keep weighted percentage as readiness/progress only when explicitly labeled as weighted/ready.
- For human output, replace contradictory `done_count/total (weighted%)` with one of:
  - `Done: X/Y (Z% done)` plus `Ready progress: A% weighted`, or
  - `Ready: R/Y ready (X done, A% weighted)` when approved/ready states are being emphasized.
- For JSON, preserve existing keys where possible and add explicit peer fields rather than silently changing meaning.
- Add tests for approved-only, done-only, mixed approved/done, no progress, and JSON output if touched.

### WP02 Dependency Drift Gate (#848)

Owner surface:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/scripts/release/check_shared_package_drift.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/scripts/release/check_exact_install.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/.github/workflows/check-spec-kitty-events-alignment.yml`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/.github/workflows/release-readiness.yml`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/.github/workflows/ci-quality.yml`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/tests/release/`

Plan:

- First verify whether `uv lock --check`, shared package drift checks, release install tests, and release-readiness jobs catch the installed environment mismatch described in #848.
- If yes, produce closure evidence for #848 and avoid code changes.
- If no, add a focused script/test path that compares installed `spec-kitty-events` metadata to the `uv.lock` resolved version before review/release evidence is trusted.
- Include `spec-kitty-tracker` only if the same drift path is clearly present and the code stays small.

### WP03 Fresh End-To-End Smoke

Owner surface:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/kitty-specs/stable-320-p1-release-confidence-01KQTPZC/quickstart.md`
- final release evidence artifact produced during implementation

Plan:

- Run a local-only full lifecycle smoke against the current prerelease line.
- Run a SaaS-enabled full lifecycle smoke, setting `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on hosted auth, tracker, SaaS, or sync paths.
- If a smoke fails, file/reference an issue, fix it if narrow, or record a stable-release blocker decision.

### WP04 Release Evidence And Deferrals

Owner surface:

- mission release evidence artifact created during implementation
- issue closure/defer notes for #966, #848, #971, and P2/P3 issues

Plan:

- Compile evidence for #966, #848, both smoke runs, and `uv run ruff check src tests`.
- Record #971 as deferred unless explicitly included.
- Record P2/P3 deferrals listed in the spec.

## Complexity Tracking

No charter violations require justification. The plan intentionally avoids new subsystems unless #848 verification proves an installed-vs-lock guard is missing.

## Post-Design Charter Re-check

| Charter standard | Result |
|---|---|
| Existing dependencies preferred | PASS |
| Local deterministic tests by default | PASS |
| SaaS sync flag on hosted/sync paths | PASS |
| External package boundary respected | PASS |
| Branch contract explicit | PASS |
| No task generation in plan phase | PASS |
