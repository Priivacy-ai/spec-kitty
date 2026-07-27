---
work_package_id: WP01
title: 'Test Hygiene: xfail Removal & Branch Naming Gap'
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: fix/cli-bug-sweep-tool-surface-self-registration
merge_target_branch: fix/cli-bug-sweep-tool-surface-self-registration
branch_strategy: Planning artifacts for this mission were generated on fix/cli-bug-sweep-tool-surface-self-registration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cli-bug-sweep-tool-surface-self-registration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-bug-sweep-tool-surface-self-registration-01KV5AWE
base_commit: 093cb7fce499da0e5b6b50b94ca1be6c73930dae
created_at: '2026-06-15T11:21:40.873530+00:00'
subtasks:
- T001
- T002
- T003
agent: claude
shell_pid: '14961'
history:
- date: '2026-06-15'
  event: created
agent_profile: python-pedro
authoritative_surface: tests/
create_intent: []
execution_mode: code_change
owned_files:
- tests/adversarial/test_distribution.py
- src/specify_cli/lanes/branch_naming.py
- tests/core/test_branch_naming_human_slug.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

This loads the Python implementation profile with TDD discipline, mypy-strict constraints, and idiomatic Python 3.11+ style rules.

---

## Objective

Remove a stale `xfail` marker that masks regression detection for the init-with-`--ai` code path, and close the test coverage gap for the branch naming pathological case where a slug's embedded `mid8` differs from the `mission_id` argument.

## Branch Strategy

- **Implementation branch**: allocated by `spec-kitty agent action implement WP01 --agent claude`
- **Planning/base branch**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Final merge target**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Worktree**: allocated per lane from `lanes.json`; do not create worktrees manually

## Context

### Why the xfail exists (IC-01)

`TestUpgradeWithAllMissions::test_upgrade_updates_templates` in `tests/adversarial/test_distribution.py` was marked `@pytest.mark.xfail(strict=False)` because `spec-kitty init` was observed to prompt for agent strategy even when `--ai` was passed. That bug has since been fixed (`if ai_assistant:` guard at `src/specify_cli/cli/commands/init.py:617`). The `--script` and `--mission` flags referenced in the xfail reason do not exist in the CLI. The marker now masks all XPASS outcomes, providing zero regression protection.

**The `strict=False` with an incorrect reason is a dormant mask: a future regression in the init-with-`--ai` path would silently become an XFAIL, not a test failure.**

The marker is at `tests/adversarial/test_distribution.py` lines 193–206 (a comment block + the decorator). Removing them is the entire fix.

**Residual risk**: `ensure_runtime()` inside `init` may be flaky in some CI environments (absent global runtime state). If the test fails after the marker is removed with a failure unrelated to the agent-strategy prompt, that is a pre-existing latent issue. File a new GitHub issue with the failure; do NOT restore the xfail.

**Note on T002 scope**: T002 (docstring addition to `_human_slug_for_mid8_branch`) is plan-level refinement complementing the test required by FR-002. FR-002 specifies the test; T002 documents the invariant the test covers so future maintainers understand the guard before touching it. Both are part of this WP.

### Why the branch naming test gap exists (IC-02)

`_human_slug_for_mid8_branch()` in `src/specify_cli/lanes/branch_naming.py` strips the embedded `mid8` from a slug before re-appending it — but only when the slug's embedded `mid8` matches the `mission_id` argument's `mid8`. When they differ (the pathological case), the guard does not fire and the `mid8` is appended twice, producing a doubled branch name like `kitty/mission-my-feature-AAAA1111-01KV3NGS`.

Production risk is low because a slug's embedded `mid8` is always derived from its own `mission_id` at creation time. But the behavior is untested, so any future change to the guard would be invisible to the suite.

The existing tests at `tests/core/test_branch_naming_human_slug.py` cover the matching case (slug mid8 equals argument mid8). The new test must cover the non-matching case and document the current output explicitly.

---

## Subtask T001 — Remove xfail Decorator

**Purpose**: Delete the `@pytest.mark.xfail(strict=False, reason=…)` decorator and its accompanying comment block from `test_distribution.py` so `test_upgrade_updates_templates` runs undecorated.

**Steps**:

1. Read `tests/adversarial/test_distribution.py` — locate the `xfail` decorator on `TestUpgradeWithAllMissions::test_upgrade_updates_templates`. It is approximately at lines 193–206.

2. Delete the entire block: the comment line (`# spec-kitty init still prompts…`) and the `@pytest.mark.xfail(...)` decorator. The `def test_upgrade_updates_templates(self` line that follows becomes the direct class member, undecorated.

3. Do **not** change any other part of the test body, fixture, or class.

**Validation**:
- `pytest tests/adversarial/test_distribution.py::TestUpgradeWithAllMissions::test_upgrade_updates_templates -v` produces `PASSED` or `FAILED` — never `XFAIL` or `XPASS`.
- No other tests in the file are affected.

---

## Subtask T002 — Add Docstring to `_human_slug_for_mid8_branch`

**Purpose**: Document the invariant that the guard only strips the embedded `mid8` when it matches `mission_id`'s `mid8`, so future maintainers understand the pathological case before touching the logic.

**Steps**:

1. Read `src/specify_cli/lanes/branch_naming.py` — locate `_human_slug_for_mid8_branch` at line ~134.

2. Add a one-sentence docstring immediately after the `def` line:
   ```python
   def _human_slug_for_mid8_branch(mission_slug: str, mission_id: str) -> str:
       """Strip the embedded mid8 only when it matches mission_id's mid8; mismatched mid8 is not stripped."""
       ...
   ```

3. Do not change the function body.

**Validation**:
- `mypy src/specify_cli/lanes/branch_naming.py --strict` passes with zero errors.
- `ruff check src/specify_cli/lanes/branch_naming.py` passes.

---

## Subtask T003 — Add Pathological Case Test

**Purpose**: Assert the current behavior when a slug's embedded `mid8` differs from the `mission_id` argument's `mid8`. This documents the double-append as explicit named behavior, not a silent outcome.

**Steps**:

1. Read `tests/core/test_branch_naming_human_slug.py` to understand the existing test structure and parametrize pattern.

2. Add a new parametrized test case (or a separate test function) covering the pathological scenario:
   - Slug: `"my-feature-AAAA1111"` (embedded mid8 is `AAAA1111`)
   - `mission_id`: a ULID whose mid8 is `"01KV3NGS"` (e.g. `"01KV3NGSDCJ272573TF6T6NWDW"`)
   - Expected output: `"kitty/mission-my-feature-AAAA1111-01KV3NGS"` (the slug's mid8 is NOT stripped; the mission_id's mid8 is appended; result contains both)

3. Add a comment on the assertion explaining this is documented behavior, not a bug: the guard keys on `mission_id`'s mid8, so a mismatched embedded mid8 is treated as part of the human slug.

4. Also cover `lane_branch_name` with the same pathological slug if the existing test suite covers it — confirm both functions have coverage.

**Example test structure**:
```python
def test_mission_branch_name_pathological_mid8_mismatch():
    # When slug's embedded mid8 differs from mission_id's mid8,
    # the guard does NOT strip the slug's mid8 — documented behavior.
    slug = "my-feature-AAAA1111"
    mission_id = "01KV3NGSDCJ272573TF6T6NWDW"  # mid8 = "01KV3NGS"
    result = mission_branch_name(slug, mission_id=mission_id)
    # The slug's "AAAA1111" is treated as part of the human name;
    # "01KV3NGS" is appended by the composer.
    assert result == "kitty/mission-my-feature-AAAA1111-01KV3NGS"
```

**Validation**:
- `pytest tests/core/test_branch_naming_human_slug.py -v` → all pass, including the new case.
- `mypy tests/core/test_branch_naming_human_slug.py --strict` passes.

---

## Definition of Done

- [ ] `test_upgrade_updates_templates` runs with no `xfail`/`xpass` markers and produces a clean PASSED or FAILED result.
- [ ] `_human_slug_for_mid8_branch` has a docstring stating the invariant.
- [ ] `test_branch_naming_human_slug.py` has a test explicitly asserting the pathological-case output.
- [ ] `ruff check .` passes with zero issues.
- [ ] `mypy src/ tests/ --strict` passes with zero errors.
- [ ] No other tests broken.

## Risks for Reviewer

- If `test_upgrade_updates_templates` fails after the xfail removal with a message about `ensure_runtime()`, that is pre-existing latent behavior — confirm by checking if the same failure occurs on `main` before this WP. File a new issue; do not re-add the xfail.
- The pathological-case test must assert the **current** double-append output. If the assertion uses an idealized (non-doubling) output, it is incorrect.
