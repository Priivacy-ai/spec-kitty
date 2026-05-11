---
work_package_id: WP01
title: Plan-Widen Test Fixture Repair
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
created_at: '2026-05-11T17:30:00+00:00'
subtasks:
- T001
- T002
- T003
history:
- at: '2026-05-11T17:30:00Z'
  actor: claude
  action: created
authoritative_surface: tests/specify_cli/cli/commands/test_plan_widen.py
execution_mode: code_change
mission_id: 01KRC12SN9TNDD11SPPRRJRZ1C
mission_slug: cli-decision-moment-widen-mode-readiness-01KRC12S
owned_files:
- tests/specify_cli/cli/commands/test_plan_widen.py
priority: P0
status: planned
tags: []
---

# WP01 — Plan-Widen Test Fixture Repair

## Objective

Fix the 4 failing tests in `tests/specify_cli/cli/commands/test_plan_widen.py` by updating their shared `_setup_repo` helper to produce a repository tree that satisfies `assert_initialized(require_specs=True)`. Closes Priivacy-ai/spec-kitty#757 and (validation-only) Priivacy-ai/spec-kitty#758.

## Context

The `plan()` Typer command (`src/specify_cli/cli/commands/lifecycle.py:109`) calls `_enforce_initialized()` which delegates to `assert_initialized(require_specs=True)`. That guard verifies two paths exist at the resolved repo root:

1. `<root>/.kittify/config.yaml`
2. `<root>/kitty-specs/`

The current `_setup_repo` (lines 49–59 of `test_plan_widen.py`) creates `.kittify/` and `kitty-specs/<MISSION_SLUG>/` but **never writes `.kittify/config.yaml`**, so all 4 plan-widen integration tests exit with `SPEC_KITTY_REPO_NOT_INITIALIZED` before exercising the widen path under test.

The equivalent charter-widen tests pass because the `charter` CLI path in those tests exercises a different surface that does not go through `_enforce_initialized()` at the same gate. We therefore fix the test fixture rather than relax the production guard — the guard is the right invariant (FR-032 / WP07-T039) and must not be weakened (C-001).

## Subtasks

### T001 — Harden `_setup_repo`

In `tests/specify_cli/cli/commands/test_plan_widen.py`:

1. Inside `_setup_repo(tmp_path)`, after `kittify.mkdir(...)`:
   - Write `.kittify/config.yaml` with content:
     ```yaml
     version: 1
     project:
       uuid: 00000000-0000-0000-0000-000000000001
     ```
   - Use `(kittify / "config.yaml").write_text(...)`.
2. Make `kitty-specs/` parent creation explicit and idempotent: `(tmp_path / "kitty-specs").mkdir(parents=True, exist_ok=True)` before the per-mission `mission_dir.mkdir(...)` call.
3. Do not change any other helper, assertion, or test body.

### T002 — Verify acceptance test set

Run, from repo root:

```bash
uv run pytest tests/specify_cli/cli/commands/test_charter_widen.py \
  tests/specify_cli/cli/commands/test_plan_widen.py \
  tests/specify_cli/cli/commands/test_decision_widen_subcommand.py \
  tests/specify_cli/cli/commands/test_charter_prereq_suppression.py \
  tests/status/test_read_events_tolerates_decision_events.py -q
```

Confirm: 55 passed, 0 failed (up from 51 passed / 4 failed baseline).

Then run the broader CLI slice to confirm no regressions (SC-003):

```bash
uv run pytest tests/specify_cli/cli/commands -q
```

### T003 — Audit sibling test fixtures

Run `grep -l "_setup_repo\|kittify\.mkdir" tests/specify_cli/` and inspect each match. Confirm one of:

- Helper already writes `config.yaml`; OR
- Helper exercises a CLI path that does not invoke `_enforce_initialized()`; OR
- Test is already passing under the new gate (and therefore not affected).

Record findings inline in the PR description. Do not modify other helpers in this WP — that scope expansion is out of bounds. If a sibling helper is in the affected category and not yet failing, file a follow-up issue rather than fixing it here.

## Definition of Done

- [ ] T001 implemented exactly as specified.
- [ ] T002 acceptance command exits with code 0 and prints `55 passed`.
- [ ] T003 audit findings recorded in PR description.
- [ ] No production code in `src/specify_cli/` is modified.
- [ ] PR opened against `main` with title `[Mission 1] CLI Decision Moment Widen Mode Readiness`.

## Out of Scope

- Production-side changes to widen flow, plan interview, or charter interview.
- Other mission scope items (Slack closure, E2E acceptance, invite onboarding).
- Sibling fixture fixes that may surface during T003 — log and defer.

## References

- Spec: [../spec.md](../spec.md)
- Plan: [../plan.md](../plan.md)
- Production guard: `src/specify_cli/workspace/assert_initialized.py`
- Plan command: `src/specify_cli/cli/commands/lifecycle.py:103-153`
- Reference fixture (passing): `tests/specify_cli/cli/commands/test_charter_widen.py:42-59`
