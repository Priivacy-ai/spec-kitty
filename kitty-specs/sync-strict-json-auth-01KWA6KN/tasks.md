# Tasks: Fix sync strict-JSON ingress-skip auth

**Mission**: sync-strict-json-auth-01KWA6KN | **Tracker**: [#2254](https://github.com/Priivacy-ai/spec-kitty/issues/2254)
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## Overview

Single-surface test fix. Root cause (FR-001, see research.md) is confirmed test-seeding drift:
the test seeds its encrypted shared-only `StoredSession` at the legacy `~/.spec-kitty/auth`
path while production now reads `$SPEC_KITTY_HOME/auth` (commit `a75174917` / #2182). Fix the
**test**, not production. One work package.

- **FR-001** (root-cause determination): already delivered in `research.md` — no code work.
- **FR-007** (CI-trigger blind-spot): deferred decision `01KWA6Q7…`; resolved at mission-review (research recommends folding into #2034). Not a code WP here.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Re-pin session seeding to the production resolver path | WP01 | |
| T002 | Correct the stale seeding docstrings | WP01 | |
| T003 | Add the non-vacuous negative auth pin assertion | WP01 | |
| T004 | Live-verify the genuine ingress-skip path fires (logging-reachability residual) | WP01 | |
| T005 | Regression + quality gates (full tests/sync, ruff, mypy) | WP01 | |

## Work Packages

### WP01 — Re-pin sync strict-JSON test seeding + non-vacuous regression lock

- **Goal**: Make `test_mission_create_json_strict_when_sync_skips_ingress` pass via the genuine
  direct-ingress-skip path by seeding the session where production reads it, lock the drift class
  by anchoring to the production resolver, and add a negative auth pin — without touching
  production or weakening the diagnostic guard.
- **Priority**: P0 (this is the whole mission).
- **Independent test**: `PWHEADLESS=1 uv run pytest tests/sync/test_strict_json_stdout.py::test_mission_create_json_strict_when_sync_skips_ingress -n0` passes, with `direct ingress skipped`/`direct_ingress_missing_private_team` on stderr and NO `no valid access token` on stderr.
- **Prompt**: [tasks/WP01-repin-sync-strict-json-seeding.md](./tasks/WP01-repin-sync-strict-json-seeding.md)
- **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, NFR-001, NFR-002, NFR-003, NFR-004, C-002, C-003.
- **Dependencies**: none.
- **Estimated prompt size**: ~280 lines.

Included subtasks:

- [ ] T001 Re-pin session seeding to the production resolver path (WP01)
- [ ] T002 Correct the stale seeding docstrings (WP01)
- [ ] T003 Add the non-vacuous negative auth pin assertion (WP01)
- [ ] T004 Live-verify the genuine ingress-skip path fires (WP01)
- [ ] T005 Regression + quality gates (full tests/sync, ruff, mypy) (WP01)

## MVP

WP01 is the entire mission.
