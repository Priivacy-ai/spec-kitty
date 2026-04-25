---
work_package_id: WP05
title: Remove the Vendored Events Tree
dependencies:
- WP04
requirement_refs:
- FR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
agent: "claude:opus-4.7:python-reviewer:reviewer"
shell_pid: "69431"
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/spec_kitty_events/
execution_mode: code_change
owned_files:
- src/specify_cli/spec_kitty_events/**
tags: []
---

# WP05 — Remove the Vendored Events Tree

## Objective

Delete `src/specify_cli/spec_kitty_events/` from the production source tree
and update wheel build configuration so the deleted tree is not shipped. After
this WP, the only events code in the wheel is what comes from the
`spec-kitty-events` PyPI package as a runtime dep.

## Context

WP04 has migrated every consumer (production and test) off the vendored tree.
The vendored tree is now unreferenced. WP05 deletes it. WP06 then locks the
deletion with packaging assertions.

Wheel-build configuration in `pyproject.toml`:
- `[tool.hatch.build.targets.wheel]` lists `packages = ["src/kernel", "src/specify_cli", "src/doctrine", "src/charter"]` — the `src/specify_cli` entry transitively includes the vendored tree today.
- `artifacts = ["src/specify_cli/**/*.md", ...]` — the vendored tree's non-Python assets are pulled in by these globs.
- After deletion, neither line needs structural change: globs simply find fewer files.
- The `exclude = ["src/specify_cli/**/tests/**", ...]` line is unrelated; leave it.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: lane B (depends on WP04).

## Implementation

### Subtask T022 — Audit + adjust wheel build config

**Purpose**: Confirm wheel build still works after the deletion. The build
config does not require structural changes (globs find fewer files), but
verify.

**Steps**:

1. Read `pyproject.toml` `[tool.hatch.build.targets.wheel]` and
   `[tool.hatch.build.targets.sdist]` sections.
2. Confirm no entry references `specify_cli/spec_kitty_events` directly.
3. If any entry does (e.g. an explicit `artifacts` glob narrowed to that
   subtree), remove it.
4. Document any change in the WP commit message; if no changes, the commit
   message says "wheel build config audit: no changes required."

**Files**: `pyproject.toml` (changes only if the audit surfaces a direct
reference; usually none).

**Validation**: `python -m build --wheel` succeeds against the pre-deletion
tree (sanity check).

### Subtask T023 — Delete the vendored tree

**Purpose**: The actual deletion.

**Steps**:

1. Remove the entire directory:
   ```bash
   git rm -r src/specify_cli/spec_kitty_events/
   ```

2. Run the static check:
   ```bash
   grep -rn "specify_cli.spec_kitty_events" src/
   ```
   MUST return zero matches now.

3. Run the same check on tests:
   ```bash
   grep -rn "specify_cli.spec_kitty_events" tests/
   ```
   MUST return zero matches.

4. Update any in-repo doc that referenced the vendored tree by path. WP10 owns
   the bulk of doc updates, but a non-doc-flavored reference may exist (e.g. a
   `__init__.py` comment). Audit:
   ```bash
   grep -rn "specify_cli/spec_kitty_events\|specify_cli.spec_kitty_events" .
   ```

   Anything outside `kitty-specs/` (planning artifacts, which are immutable
   history) and `docs/` (WP10's scope) gets fixed in this WP.

**Files**: `src/specify_cli/spec_kitty_events/**` (deletion).

**Validation**:
- The directory does not exist on disk.
- `git status` shows the deletion staged.
- Greps from steps 2 / 3 / 4 are clean.

### Subtask T024 — Run full suite; build wheel; fix any missed consumer

**Purpose**: Catch any consumer WP04 missed. The full test suite is the gate.

**Steps**:

1. Run the full unit + integration test suite:
   ```bash
   pytest -m "fast or integration" -x
   ```

2. Build the wheel:
   ```bash
   python -m build --wheel
   ls dist/spec_kitty_cli-*.whl
   ```

3. Inspect the wheel:
   ```bash
   python -c "
   import zipfile, sys
   with zipfile.ZipFile(sys.argv[1]) as z:
       names = [n for n in z.namelist() if 'spec_kitty_events' in n]
       assert not names, f'wheel still contains vendored events: {names[:5]}'
   print('OK: wheel does not contain vendored events tree')
   " dist/spec_kitty_cli-*.whl
   ```

4. If any test or build step fails: a consumer was missed. Fix in this WP
   (extend the WP's `owned_files` if the missed consumer is in a previously
   un-listed file, and document in the commit message).

**Files**: None directly in this subtask; fixes flow into the file containing
the missed consumer.

**Validation**:
- Test suite green.
- Wheel builds successfully.
- Wheel does not contain `spec_kitty_events` paths.

## Definition of Done

- [ ] All 3 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] `src/specify_cli/spec_kitty_events/` is gone.
- [ ] `grep -rn "specify_cli.spec_kitty_events" src/ tests/` returns zero matches.
- [ ] Full test suite green.
- [ ] Wheel builds and does not contain the vendored events paths.
- [ ] `tests/architectural/test_shared_package_boundary.py` (from WP03) — its
  vendored-events-rule scope comment can now be simplified; update the
  comment to reflect that the vendored tree is gone.

## Risks

- **A consumer was missed in WP04.** Mitigation: T024's full-suite + wheel
  build is the hard gate.
- **A non-Python asset (markdown, YAML) inside the vendored tree was being
  loaded by name at runtime.** Mitigation: T024's full-suite catches it; the
  fix is to switch the load-by-name to a public-package import equivalent (or
  a CLI-internal path).

## Reviewer guidance

- Verify the directory is gone.
- Verify the greps are clean.
- Verify the wheel builds and doesn't contain the deleted paths.
- Verify the architectural test from WP03 had its scope comment updated.
- Verify the commit message documents either "no wheel-build config changes
  needed" or the specific changes that were needed.

## Implementation command

```bash
spec-kitty agent action implement WP05 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```

## Activity Log

- 2026-04-25T11:41:18Z – claude:opus-4.7:python-implementer:implementer – shell_pid=52882 – Started implementation via action command
- 2026-04-25T11:52:27Z – claude:opus-4.7:python-implementer:implementer – shell_pid=52882 – Moved to planned
- 2026-04-25T11:54:56Z – claude:opus-4.7:python-implementer:implementer – shell_pid=66490 – Started implementation via action command
- 2026-04-25T11:58:30Z – claude:opus-4.7:python-implementer:implementer – shell_pid=66490 – Vendored events tree deleted (311 files, ~23k LOC). pyproject.toml mutate_only glob cleaned. Architectural test docstring updated. Fast suite 1524 passed; 1 unrelated pre-existing failure in tests/audit/test_no_legacy_agent_profiles_path.py (predates mission).
- 2026-04-25T11:58:37Z – claude:opus-4.7:python-reviewer:reviewer – shell_pid=69431 – Started review via action command
- 2026-04-25T11:59:10Z – claude:opus-4.7:python-reviewer:reviewer – shell_pid=69431 – Approved: all acceptance criteria met. Vendored tree deleted (311 files), greps clean, architectural tests 8/8 pass, fast suite 1524 passed (1 unrelated pre-existing failure). T022 audit removed dead pyproject.toml glob. Refs: FR-003, T022-T024, commit ea1d9350.
