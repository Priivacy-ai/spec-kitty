---
work_package_id: WP02
title: Author the read-only SonarCloud review tool + smoke test
dependencies: []
requirement_refs:
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: feat/sonar-qa-config-remediation
merge_target_branch: feat/sonar-qa-config-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/sonar-qa-config-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sonar-qa-config-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T003
- T004
agent: "reviewer-renata"
shell_pid: "3165955"
history:
- Created for mission sonar-qa-config-remediation-01KWYCX7
agent_profile: python-pedro
authoritative_surface: scripts/ci/
create_intent:
- scripts/ci/sonarcloud_branch_review.sh
- tests/ci/test_sonarcloud_branch_review.py
execution_mode: code_change
owned_files:
- scripts/ci/sonarcloud_branch_review.sh
- tests/ci/test_sonarcloud_branch_review.py
- tests/ci/fixtures/sonarcloud/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile (`python-pedro`) via `/ad-hoc-profile-load` before reading anything else.

## Objective
Author a tracked, **read-only** SonarCloud review tool at `scripts/ci/sonarcloud_branch_review.sh` + a token-free smoke test — the canonical tool the coverage investigation (WP03) and the SC-001b projectVersion check route through. **FR-005, FR-006, NFR-001, SC-003.**

## Context (grounded)
- **No predecessor exists in git** — a `sonarcloud_branch_review.sh` lives only as an untracked, `work/`-gitignored file on the maintainer's machine (not fetchable on any ref, incl. `stijn/design/…`). **Author fresh** to the behavioral contract below. (If Stijn hands over his copy, adopt it as a starting point — do not block on it.)
- SonarCloud's public read API needs **no `SONAR_TOKEN`** for this public project (`Priivacy-ai_spec-kitty`). Sibling: `scripts/ci/quality_gate_decision.py`.

## Guidance
**T003 — the script (FR-005)**: read-only subcommands over the public REST API, each printing parseable output:
- `quality-gate` → `GET /api/qualitygates/project_status`
- `coverage` → `GET /api/measures/component` / `component_tree` (`coverage`, `new_coverage`)
- `uncovered <file>` → per-file uncovered lines
- `issues` → issues by rule/file (`GET /api/issues/search`)
- `version` / `analyses` → `GET /api/project_analyses/search` + `/api/components/show` (backs SC-001b — reports the analysed `projectVersion` + the new-code baseline period)
Arg-parsing (subcommand + flags), explicit error handling (non-200, missing arg), **no state mutation** (only `GET`s). `shellcheck`-clean.
**T004 — smoke test (FR-006, NFR-001, SC-003)**: `tests/ci/test_sonarcloud_branch_review.py` drives the script against **recorded JSON fixtures** in `tests/ci/fixtures/sonarcloud/` (so CI needs no network + no token) — assert arg-parsing, subcommand dispatch, and output shape for each subcommand; assert the script issues only `GET`s (read-only). Optionally one live-read smoke behind a skip-if-offline guard.

## Definition of Done
- Script is tracked, read-only, 5 subcommands, shellcheck-clean.
- `pytest tests/ci/test_sonarcloud_branch_review.py` green with **no `SONAR_TOKEN` and no network** (fixture-backed).
- `ruff` + `mypy` clean on the test; commitlint-clean.
- No mutation path; no token requirement (NFR-001); no suppression (NFR-002).

## Reviewer guidance
Confirm every subcommand is a `GET` (grep for any POST/PUT/DELETE → fail), the smoke test truly needs no token/network (run it offline), and the `version`/`analyses` subcommand can back SC-001b.

## Activity Log

- 2026-07-07T14:35:59Z – python-pedro – shell_pid=3142769 – Assigned agent via action command
- 2026-07-07T14:49:48Z – python-pedro – shell_pid=3142769 – Ready for review: read-only SonarCloud tool (5 subcommands, GET-only, shellcheck-clean) + token-free fixture-backed smoke test (20 passing, ruff+mypy strict clean)
- 2026-07-07T14:51:26Z – reviewer-renata – shell_pid=3165955 – Started review via action command
- 2026-07-07T14:59:33Z – user – shell_pid=3165955 – Review passed: read-only proven (static+runtime), 20 tests offline/token-free, gates clean
