# Quickstart: Mid-Stream Change Command

**Feature**: `029-mid-stream-change-command`  
**Date**: 2026-02-09

## Purpose

Use this guide to validate `/spec-kitty.change` end-to-end with deterministic scoring, branch-aware stash routing, and stack-first implement behavior.

## Preconditions

- Planning repository initialized with `kitty-specs/`.
- Open feature WPs exist in `kitty-specs/<feature>/tasks/` for feature-branch scenarios.
- Embedded main stash path exists or can be created at `kitty-specs/change-stack/main/`.

## Scenario 1: Ambiguous request fails fast

Example request:

`/spec-kitty.change "change this block"`

Expected outcome:
1. Preview marks request as ambiguous.
2. No new WP file is created.
3. User receives clarification prompt.

Verify:
- No new files under `kitty-specs/change-stack/main/` or `kitty-specs/<feature>/tasks/`.
- Response indicates `requiresClarification=true`.

## Scenario 2: Simple feature-branch request

Example request:

`/spec-kitty.change "use this lib instead"`

Expected outcome:
1. Stash resolves to current feature path (`kitty-specs/<feature>/tasks/`).
2. Complexity class is `simple`.
3. One change WP is created with multiple tasks.
4. Last task in the new change WP is a testing task.

Verify:
- New WP frontmatter contains `change_stack: true`.
- `kitty-specs/<feature>/tasks.md` references the new WP.
- Dependency validation passes.

## Scenario 3: Main branch request routes to embedded stash

Example request on `main`:

`/spec-kitty.change "revert that block"`

Expected outcome:
1. Stash resolves to `kitty-specs/change-stack/main/`.
2. New change WP file is created in embedded main stash.
3. Feature-local task files are untouched.

Verify:
- New files appear under `kitty-specs/change-stack/main/`.
- No unrelated feature `tasks/` directories are modified.

## Scenario 4: High complexity warning with explicit continue

Example request:

`/spec-kitty.change "rework multiple active WPs and reconcile integration conflicts"`

Expected outcome:
1. Score class is `high`.
2. Command recommends `/spec-kitty.specify`.
3. User can choose continue or stop.
4. If continue, generated WPs are marked for elevated review attention.

Verify:
- Warning shown before apply.
- Apply requires explicit decision.

## Scenario 5: Closed WP reference handling

Example request references closed WP `WP04`.

Expected outcome:
1. New change WP is created.
2. Closed WP is linked as historical context.
3. Closed WP lane/state is unchanged.

Verify:
- Change WP contains closed-reference metadata.
- `WP04` remains in `done` lane.

## Scenario 6: Stack-first implement behavior

With pending change WPs:

1. Any ready change WP is selected before normal planned WPs.
2. If change WPs exist but none are ready, blockers are reported and normal progression stops.
3. Normal planned WPs are selected only when the change stack is empty.

Verify command:

```bash
spec-kitty agent workflow implement --agent codex
```

## Recommended Verification Commands

```bash
pytest tests/unit/test_change_classifier.py
pytest tests/unit/test_change_stack.py
pytest tests/unit/agent/test_change_command.py
pytest tests/integration/test_change_main_stash_flow.py
pytest tests/integration/test_change_stack_priority.py
mypy --strict src/specify_cli
```

---

**END OF QUICKSTART**
