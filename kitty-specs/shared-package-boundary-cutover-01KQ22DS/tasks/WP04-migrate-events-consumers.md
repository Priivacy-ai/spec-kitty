---
work_package_id: WP04
title: Migrate Events Consumers to the Public PyPI Package
dependencies: []
requirement_refs:
- FR-004
- FR-018
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
agent: "claude:opus-4.7:python-reviewer:reviewer"
shell_pid: "47022"
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/decisions/
execution_mode: code_change
owned_files:
- src/specify_cli/decisions/emit.py
- src/specify_cli/glossary/events.py
- src/specify_cli/sync/diagnose.py
- tests/specify_cli/cli/commands/test_charter_decision_integration.py
- tests/specify_cli/decisions/test_emit.py
- tests/contract/test_handoff_fixtures.py
tags: []
---

# WP04 — Migrate Events Consumers to the Public PyPI Package

## Objective

Every CLI consumer of events imports from `spec_kitty_events.*` (the public PyPI
package) rather than `specify_cli.spec_kitty_events.*` (the vendored copy).
After this WP, the vendored tree at `src/specify_cli/spec_kitty_events/` is
*unreferenced* by production code (its actual deletion is WP05's job).

## Context

This is lane B's foundation. It runs in parallel with lane A's WP01..WP03.
Pre-cutover production consumers of the vendored events tree (verified via
grep):

| File | Lines | Imports |
|------|-------|---------|
| `src/specify_cli/decisions/emit.py` | 34, 40 | `specify_cli.spec_kitty_events.decisionpoint`, `specify_cli.spec_kitty_events.decision_moment` |
| `src/specify_cli/glossary/events.py` | (audit on rebase) | `specify_cli.spec_kitty_events.*` |
| `src/specify_cli/sync/diagnose.py` | 20 | `specify_cli.spec_kitty_events.models.Event` |

Pre-cutover test consumers:

| File | Lines | Imports |
|------|-------|---------|
| `tests/specify_cli/cli/commands/test_charter_decision_integration.py` | (audit on rebase) | `specify_cli.spec_kitty_events.*` |
| `tests/specify_cli/decisions/test_emit.py` | (audit on rebase) | `specify_cli.spec_kitty_events.*` |
| `tests/contract/test_handoff_fixtures.py` | (audit on rebase) | `specify_cli.spec_kitty_events.*` |

The public-surface contract for what CLI is allowed to import from
`spec_kitty_events` is in
[`../contracts/events_consumer_surface.md`](../contracts/events_consumer_surface.md).

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: lane B (no dependencies; parallel with WP01).

## Implementation

### Subtask T017 — Migrate `decisions/emit.py` [P]

**Purpose**: This file imports `decisionpoint` and `decision_moment`
sub-modules from the vendored events tree. Switch to the public package.

**Steps**:

1. Replace at line 34:
   ```python
   # Before:
   from specify_cli.spec_kitty_events.decisionpoint import (
       <whatever symbols are imported>
   )
   # After:
   from spec_kitty_events.decisionpoint import (
       <same symbols>
   )
   ```

2. Replace at line 40:
   ```python
   # Before:
   from specify_cli.spec_kitty_events.decision_moment import (
       <whatever symbols are imported>
   )
   # After:
   from spec_kitty_events.decision_moment import (
       <same symbols>
   )
   ```

3. Update the module docstring (lines 1..28). The docstring currently says
   "vendored `specify_cli.spec_kitty_events.decisionpoint` payload models".
   Change to: "public `spec_kitty_events.decisionpoint` payload models (4.0.0
   contract)."

4. If a symbol that exists in the vendored tree does NOT exist in the public
   package at the same path, that is a contract gap. File a delta in the
   events repo's `events-pypi-contract-hardening-01KQ1ZK7` mission and adjust
   the import to use the public surface that does exist (consult
   `contracts/events_consumer_surface.md` for the authoritative list).

**Files**: `src/specify_cli/decisions/emit.py`.

**Validation**:
- `grep -n "specify_cli.spec_kitty_events" src/specify_cli/decisions/emit.py`
  returns zero matches.
- `mypy --strict` passes.
- `python -c "from specify_cli.decisions.emit import emit_decision_opened, emit_decision_resolved"` succeeds.

### Subtask T018 — Migrate `glossary/events.py` [P]

**Purpose**: Same migration pattern, applied to the glossary events emitter.

**Steps**:

1. Audit imports: `grep -n "specify_cli.spec_kitty_events" src/specify_cli/glossary/events.py`.
2. Replace each `specify_cli.spec_kitty_events.<sub>` → `spec_kitty_events.<sub>`.
3. If any imported symbol is not on the public surface (per
   `contracts/events_consumer_surface.md`), file a delta in the events mission
   and adjust to a public-surface equivalent.

**Files**: `src/specify_cli/glossary/events.py`.

**Validation**:
- `grep -n "specify_cli.spec_kitty_events" src/specify_cli/glossary/events.py`
  returns zero matches.
- `mypy --strict` passes.

### Subtask T019 — Migrate `sync/diagnose.py` and any other production consumer [P]

**Purpose**: Catch any consumer not enumerated in the plan's grep audit.

**Steps**:

1. Replace at line 20 of `sync/diagnose.py`:
   ```python
   # Before:
   from specify_cli.spec_kitty_events.models import Event
   # After:
   from spec_kitty_events import Event
   ```

2. Re-run the audit:
   ```bash
   grep -rn "specify_cli.spec_kitty_events" src/ --include="*.py"
   ```

   The only remaining matches MUST be inside
   `src/specify_cli/spec_kitty_events/` itself (the vendored tree, deleted in
   WP05). If the grep finds any other production file, extend this subtask to
   cover it.

**Files**: `src/specify_cli/sync/diagnose.py` and any other production
consumer surfaced by audit.

**Validation**:
- `grep -rn "specify_cli.spec_kitty_events" src/` yields matches only inside
  `src/specify_cli/spec_kitty_events/`.
- `mypy --strict` passes.

### Subtask T020 — Rewrite test consumers

**Purpose**: Tests import the vendored copy too. Migrate them in the same step.

**Steps**:

1. `tests/specify_cli/cli/commands/test_charter_decision_integration.py`: replace
   `from specify_cli.spec_kitty_events.<sub> import X` →
   `from spec_kitty_events.<sub> import X`.

2. `tests/specify_cli/decisions/test_emit.py`: same.

3. `tests/contract/test_handoff_fixtures.py`: same.

4. Audit the broader test tree:
   ```bash
   grep -rln "specify_cli.spec_kitty_events" tests/
   ```

   Migrate every match.

**Files**: 3 test files in this WP's owned_files; any additional test files
surfaced by audit are added to the WP's owned_files in this PR (not in a
follow-up).

**Validation**:
- `grep -rn "specify_cli.spec_kitty_events" tests/` yields zero matches.
- `pytest tests/specify_cli/decisions/ tests/specify_cli/cli/commands/test_charter_decision_integration.py tests/contract/test_handoff_fixtures.py -v` passes.

### Subtask T021 — Run full event-related suite; fix any contract delta

**Purpose**: The vendored events tree and the public PyPI package may differ
in private internals. Catch any behavior delta now, before WP05 deletes the
vendored tree.

**Steps**:

1. Run all event-related tests:
   ```bash
   pytest tests/specify_cli/decisions/ tests/specify_cli/glossary/ tests/specify_cli/sync/ tests/contract/test_handoff_fixtures.py -v
   ```

2. If a test fails because a symbol's behavior differs between the vendored
   copy and the public package: this is a contract gap. File a delta in the
   events mission's tracker and resolve in this WP by switching to the
   public-surface equivalent (don't paper over the gap by re-introducing the
   vendored import).

3. Run `mypy --strict` on all modified files.

**Files**: None modified directly in this subtask.

**Validation**: All event-related test suites green.

## Definition of Done

- [ ] All 5 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] No production module imports `specify_cli.spec_kitty_events.*` (verified
  by grep, scoped to outside `src/specify_cli/spec_kitty_events/` itself,
  which still exists until WP05).
- [ ] No test module imports `specify_cli.spec_kitty_events.*`.
- [ ] Event-related test suite green.
- [ ] `mypy --strict` green on all changed files.

## Risks

- **A symbol the vendored tree exposes is not on the public-surface contract.**
  Mitigation: file a delta in the events mission; do not work around by
  re-introducing the vendored import. The whole point of FR-004 is that CLI
  consumes only the public surface.
- **Behavior differs between vendored and public versions of the same symbol.**
  Mitigation: the events mission `events-pypi-contract-hardening-01KQ1ZK7` is
  merged at sha `81d5ccd4`; that is the contract. Any delta is a contract bug
  on the events side, fixed there, not papered over here.

## Reviewer guidance

- Verify the production grep set is empty (modulo
  `src/specify_cli/spec_kitty_events/` itself).
- Verify the test grep set is empty.
- Verify all event-related tests are green.
- Verify no `# TODO: switch back to vendored` or similar comments.

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```

## Activity Log

- 2026-04-25T11:25:08Z – claude:opus-4.7:python-implementer:implementer – shell_pid=43440 – Started implementation via action command
- 2026-04-25T11:34:15Z – claude:opus-4.7:python-implementer:implementer – shell_pid=43440 – Ready for review: events consumers migrated to public spec_kitty_events PyPI package; no specify_cli.spec_kitty_events imports outside the vendored tree itself; architectural R2 rule converted to AST scan and now passing.
- 2026-04-25T11:34:29Z – claude:opus-4.7:python-reviewer:reviewer – shell_pid=47022 – Started review via action command
- 2026-04-25T11:36:38Z – claude:opus-4.7:python-reviewer:reviewer – shell_pid=47022 – Implementation committed; subtasks complete
