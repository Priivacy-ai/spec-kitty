---
work_package_id: WP01
title: Wire sonar.projectVersion from pyproject.toml
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: feat/sonar-qa-config-remediation
merge_target_branch: feat/sonar-qa-config-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/sonar-qa-config-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sonar-qa-config-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
agent: "reviewer-renata"
shell_pid: "3164460"
history:
- Created for mission sonar-qa-config-remediation-01KWYCX7
agent_profile: python-pedro
authoritative_surface: .github/workflows/
create_intent:
- tests/ci/test_sonar_projectversion_wired.py
- scripts/ci/sonar_project_version.py
- tests/ci/test_sonar_project_version.py
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- tests/ci/test_sonar_projectversion_wired.py
- scripts/ci/sonar_project_version.py
- tests/ci/test_sonar_project_version.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile (`python-pedro`) via `/ad-hoc-profile-load` before reading anything else.

## Objective
Make every SonarCloud analysis carry a real `projectVersion` read from `pyproject.toml`, so the new-code baseline resets per dev cycle instead of freezing at 2026-03-21 (#2421). **FR-001, FR-002, SC-001a.**

## Context (grounded)
- The `sonarcloud` job in `.github/workflows/ci-quality.yml` ("Materialize effective Sonar config" step + the scanner-action `args`) never sets `sonar.projectVersion`; `sonar-project.properties` has no version key.
- **The job is gated `if: … github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'`** — it runs on NEITHER `pull_request` NOR `push`. So this change is **not** observable in a PR or on merge; it takes effect on the next nightly cron (`17 2 * * *`) or a manual dispatch. Verify statically (see T002), never by waiting for a PR run.

## Guidance
**T001 — testable version extraction + wire it (FR-001, FR-002)**
- **Extract the derivation into a small, unit-testable module** `scripts/ci/sonar_project_version.py` (reads `pyproject.toml` via `tomllib`, returns the version string; raises loudly — never emits empty — on a missing/unreadable version). This is the post-tasks-squad fold: the runtime extraction must be **executable + tested in-mission**, not hidden in an inline shell step that only a nightly run would exercise.
- In `.github/workflows/ci-quality.yml`, the `sonarcloud` job calls that script and injects `-Dsonar.projectVersion=<version>` into the scanner args (or appends `sonar.projectVersion=<version>` in the "Materialize effective Sonar config" step). Single-sourced from `pyproject.toml`; survives a version bump with zero further edits (FR-002).
**T002 — assertions (SC-001a) — two layers, both red-first**
- **Extraction unit test** `tests/ci/test_sonar_project_version.py`: assert `sonar_project_version.py` returns exactly `pyproject.toml`'s version, and raises (not empty) when the key is absent. This closes the green-but-broken gap the static check alone can't (wrong key / empty emit).
- **Static wiring assertion** `tests/ci/test_sonar_projectversion_wired.py`: parse `ci-quality.yml` (YAML) and assert the `sonarcloud` job wires `sonar.projectVersion` via the extraction script — no network, no live analysis. Both tests must fail against the current (unwired) tree and pass after T001.

## Definition of Done
- projectVersion wired from `pyproject.toml`; no hardcoded/duplicated version.
- `tests/ci/test_sonar_projectversion_wired.py` green (and demonstrably red before T001).
- `ruff` + `mypy` clean on the new test; YAML valid; commitlint-clean commits.
- No `SONAR_TOKEN` introduced (NFR-001); no suppression (NFR-002).

## Reviewer guidance
Confirm the version is single-sourced from `pyproject.toml`, the assertion is a genuine static parse (not a tautology), and it goes red against the pre-fix workflow.

## Activity Log

- 2026-07-07T14:35:05Z – python-pedro – shell_pid=3139686 – Assigned agent via action command
- 2026-07-07T14:35:52Z – python-pedro – shell_pid=3141717 – Assigned agent via action command
- 2026-07-07T14:50:13Z – python-pedro – shell_pid=3141717 – projectVersion wired from pyproject.toml via scripts/ci/sonar_project_version.py (raises-not-empty); extraction unit test + static YAML wiring assertion both red-first->green; ruff + mypy --strict clean; no SONAR_TOKEN, no suppression.
- 2026-07-07T14:51:14Z – reviewer-renata – shell_pid=3164460 – Started review via action command
- 2026-07-07T14:59:41Z – user – shell_pid=3164460 – Moved to planned
- 2026-07-07T15:00:49Z – user – shell_pid=3164460 – Moved to in_progress
- 2026-07-07T15:00:51Z – reviewer-renata – shell_pid=3164460 – Moved to for_review
- 2026-07-07T15:00:55Z – user – shell_pid=3164460 – Approved: code proven adversarially (14 red→green, raises-not-empty mutant reds 7, static assertion genuine); matrix filled
