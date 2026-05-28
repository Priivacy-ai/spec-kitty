---
work_package_id: WP02
title: commit_helpers.py Status-Writing Reconciliation
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-05-28T07:11:05Z'
subtasks:
- T005
- T006
- T007
phase: Phase 1 - Foundation
agent: claude
history:
- at: '2026-05-28T07:11:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/git/
execution_mode: code_change
owned_files:
- src/specify_cli/git/commit_helpers.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 — commit_helpers.py Status-Writing Reconciliation

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else. This WP edits Python source — load the Python-implementer profile so type-strict + lint conventions apply.

---

## Objective

Reconcile two phrasings in `src/specify_cli/git/commit_helpers.py` that landed in a prior partial rename. Both currently say "status-writing"; both must change to the canonical "status commit". The line-159 string is the **most-visible artifact of this mission** — it is the user-facing error message contributors see when they try a status-changing operation on `main` or another protected branch.

## Context

- **Live state (confirmed at plan time)**: The file's docstrings at lines 70, 126, 134 already use "status commit" (canonical). Only lines 141 and 159 still say "status-writing" — these are the only edits this WP makes.
- **Spec anchor FR-003** asserts the exact post-rename error string. Match it character-for-character.
- **Spec anchor FR-002** requires reconciling all `status-writing` phrasings to `status commit`.
- **Spec anchor FR-004** requires consistent "status commit" usage in docstrings + comment.

## Subtask Detail

### T005 — Update line 141 comment

**File**: `src/specify_cli/git/commit_helpers.py`

**Current (line 141, inside the docstring for `assert_not_protected_branch()`)**:

```python
      exercise status-writing commands directly; forcing every fixture to fork a lane
```

**Replacement**:

```python
      exercise status commit operations directly; forcing every fixture to fork a lane
```

Surrounding context (do not modify):

```python
    """Fail loudly before a Spec Kitty status commit can pollute local main.

    The guard is bypassed when either of:
    - ``SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`` is set to a truthy value
      (``1``, ``true``, ``yes``) — opt-in for solo-fork operators who own ``main``.
    - ``SPEC_KITTY_TEST_MODE=1`` is set — the test-mode marker the conftest sets
      on its isolated environment. Test fixtures create projects on ``main`` and
      exercise status-writing commands directly; forcing every fixture to fork a lane    # <- this line
      branch would multiply boilerplate without testing anything the production
      guard cares about.
    """
```

### T006 — Update line 159 error string

**File**: `src/specify_cli/git/commit_helpers.py`

**Current (line 159)**:

```python
            "Run status-writing operations from the mission lane branch/worktree."
```

**Replacement** (must match spec FR-003 character-for-character):

```python
            "Run status commit operations from the mission lane branch/worktree."
```

Surrounding context:

```python
    if branch and branch in protected_branches(repo_path):
        raise ProtectedBranchCommitError(
            f"Refusing to {operation} on protected branch '{branch}' in {repo_path}. "
            "Run status commit operations from the mission lane branch/worktree."   # <- this line
        )
```

### T007 — Run targeted tests; update any test that asserted the old string

Run from lane workspace:

```bash
# Targeted test runs (PWHEADLESS=1 prevents browser spawn per CLAUDE.md)
PWHEADLESS=1 pytest tests/git_ops/test_safe_commit_helper_integration.py -v
PWHEADLESS=1 pytest tests/architectural/ -v
PWHEADLESS=1 pytest tests/specify_cli/git/ -v
```

If any test fails because it asserted on the old `"status-writing operations"` string, update the assertion to the new canonical `"status commit operations"`. List of likely places to grep for matching expectations before running tests:

```bash
grep -rn 'status-writing\|"Run status-writing' tests/ --include='*.py'
```

Update those tests in the same commit as the source edit (Activity-log them).

After all the above, run the wide architectural test to confirm no behavioral regression:

```bash
PWHEADLESS=1 pytest tests/architectural/ -v
```

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution workspace: allocated per lane in `lanes.json` after `finalize-tasks`. Do not branch manually.
- Resolve via `spec-kitty agent context resolve --action implement --wp WP02 --mission rename-ceremony-to-status-commit-01KSPN6C --json`.

## Test Strategy

- All targeted tests above must pass.
- `mypy --strict src/specify_cli/git/` passes (only string changes; no type drift).
- `ruff check src/specify_cli/git/` passes.
- WP06 (regression guard) will assert at CI time that no `status-writing` substring remains in `src/`.

## Definition of Done

- [ ] `src/specify_cli/git/commit_helpers.py` line 141 comment uses "status commit operations" (no "status-writing").
- [ ] `src/specify_cli/git/commit_helpers.py` line 159 error string exactly equals `"Run status commit operations from the mission lane branch/worktree."` (matches spec FR-003).
- [ ] `grep -n 'status-writing' src/specify_cli/git/commit_helpers.py` returns zero hits.
- [ ] `grep -n 'ceremony' src/specify_cli/git/commit_helpers.py` returns zero hits (verifying no regression introduced).
- [ ] Any test that asserted on the old string is updated to the new string in this commit.
- [ ] `PWHEADLESS=1 pytest tests/git_ops/test_safe_commit_helper_integration.py tests/architectural/` passes.
- [ ] `mypy --strict src/specify_cli/git/` passes.
- [ ] `ruff check src/specify_cli/git/` passes.

## Risks & Reviewer Guidance

- **Risk 1**: Test asserts on the old string and was not updated in the same commit. Mitigation: grep + update tests in same commit.
- **Risk 2**: Implementer introduces a third variant phrasing (e.g., "status commits" plural where the spec says singular "status commit operations"). Mitigation: copy the string from spec FR-003 verbatim.
- **Reviewer check 1**: Diff is strictly two lines in `commit_helpers.py` (+ optional test-expectation updates). No other source files changed.
- **Reviewer check 2**: Line 159 string matches FR-003 character-for-character.
- **Reviewer check 3**: Tests pass green.

## References

- Spec: [../spec.md](../spec.md) — FR-001, FR-002, FR-003, FR-004
- Plan: [../plan.md](../plan.md)
- Occurrence map: [../occurrence_map.yaml](../occurrence_map.yaml) — entries `ufs-001`, `ufs-002`
- Term-rename contract: [../contracts/term-rename-contract.md](../contracts/term-rename-contract.md) — Rule R1
