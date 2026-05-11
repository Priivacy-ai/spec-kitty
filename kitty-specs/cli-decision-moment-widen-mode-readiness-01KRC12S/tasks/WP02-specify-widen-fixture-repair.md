---
work_package_id: WP02
title: Specify-Widen Test Fixture Repair
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-005
- NFR-001
- NFR-002
- C-001
- C-002
- C-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
created_at: '2026-05-11T17:40:00+00:00'
subtasks:
- T004
- T005
shell_pid: '42715'
history:
- at: '2026-05-11T17:40:00Z'
  actor: claude
  action: created
authoritative_surface: tests/specify_cli/cli/commands/test_specify_widen.py
execution_mode: code_change
mission_id: 01KRC12SN9TNDD11SPPRRJRZ1C
mission_slug: cli-decision-moment-widen-mode-readiness-01KRC12S
owned_files:
- tests/specify_cli/cli/commands/test_specify_widen.py
priority: P0
status: planned
tags: []
---

# WP02 — Specify-Widen Test Fixture Repair

## Objective

Apply the same fixture hardening as WP01 to `tests/specify_cli/cli/commands/test_specify_widen.py` so its 4 pre-existing failures pass. This closes the **specify** surface of FR-003 ("charter, specify, and plan all create first-class Decision Moment artifacts and preserve local-only behavior without SaaS").

## Context

The mission reviewer noticed that the WP01 audit surfaced `test_specify_widen.py` as having the same root cause: `_setup_repo` does not bootstrap `.kittify/config.yaml` or `git init`, so `lifecycle.specify()` exits at `_enforce_initialized(require_specs=False)` before exercising the specify-widen path. Fix is mechanically identical to WP01.

## Subtasks

### T004 — Harden `_setup_repo` in test_specify_widen.py

Mirror the WP01 fix exactly:

1. Inside `_setup_repo(tmp_path)`, after `kittify.mkdir(...)`:
   - Run `subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)` so `resolve_canonical_root` succeeds.
   - Write `.kittify/config.yaml`:
     ```yaml
     version: 1
     project:
       uuid: 00000000-0000-0000-0000-000000000002
     ```
   - Use a UUID distinct from WP01 (last byte `...02`) to be obviously test-specific.
2. Make `kitty-specs/` parent creation explicit: `(tmp_path / "kitty-specs").mkdir(parents=True, exist_ok=True)`.
3. Do not modify any other helper, assertion, or test body. Do not modify production code.

### T005 — Verify

Run, from the lane worktree:

```bash
uv run pytest tests/specify_cli/cli/commands/test_specify_widen.py -q
```

Expected: all 4 previously-failing tests pass; total count = previously-passing count + 4.

Then run the broader CLI slice to confirm regressions are unchanged (should be 9 pre-existing remaining after WP01 fixed 4):

```bash
uv run pytest tests/specify_cli/cli/commands -q 2>&1 | tail -20
```

Expected: 9 pre-existing failures (down from 13 after WP01).

## Definition of Done

- [ ] T004 implemented exactly as specified.
- [ ] T005 verification confirms 4 newly-passing tests, no new regressions.
- [ ] No production code in `src/specify_cli/` is modified.
- [ ] Commit lands on the same lane branch as WP01.

## References

- WP01: `WP01-plan-widen-fixture-repair.md`
- Spec FR-003: `../spec.md`
- WP01 implementation commit: `2acf7eee` (reference pattern)
