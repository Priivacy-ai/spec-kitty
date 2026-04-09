---
work_package_id: WP01
title: Track 1 — Init Coherence
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-04-09T07:30:50Z'
  event: created
authoritative_surface: src/specify_cli/cli/commands/init.py
execution_mode: code_change
mission_slug: 079-post-555-release-hardening
owned_files:
- src/specify_cli/cli/commands/init.py
- src/specify_cli/core/git_ops.py
- tests/init/**
tags: []
---

# WP01 — Track 1: Init Coherence

**Spec FRs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-001
**Priority**: P1 — first in rollout sequence; fresh `init` must work cleanly before anything else is verified.
**Estimated size**: ~380 lines

## Objective

Rewrite `spec-kitty init` so it is **file-creation-only**. Remove every path by which it initializes a git repository, creates a commit, or seeds `.agents/skills/` content. Remove the `--no-git` flag entirely (it has no meaning under the new model). Rewrite the next-steps output to name `spec-kitty next` and `spec-kitty agent action implement/review` as the canonical user workflow.

This is a deliberate CLI surface change. Users passing `--no-git` after this lands will get a typer "no such option" error. That is the intended behavior and must not be softened into a backward-compat no-op.

## Context

**Current state** (from Phase 0 research):
- `init.py:547-560` calls `init_git_repo(project_path, quiet=True)` when `--no-git` is not set.
- `git_ops.py:104-128` `init_git_repo()` runs `git init`, `git add .`, `git commit -m "Initial commit from Specify template"`.
- `init.py:515-540` calls `install_skills_for_agent()` which seeds `.agents/skills/` or per-agent skill roots.
- `init.py:641-650` lists next-steps including `/spec-kitty.implement` as a canonical step.
- The `--no-git` flag already exists at `init.py:267`.
- Existing init tests (`tests/init/test_init_*.py`) do **not** lock the literal commit message or assert `git init` is called — safe to change behavior without breaking existing tests.

**Target state** (spec D-1, FR-001..FR-008):
- `init` is file-creation-only. No git operations under any flag combination.
- `--no-git` flag does not exist (removed).
- `.agents/skills/` is not created. Per-agent directories (`.codex/prompts/`, `.claude/skills/`, etc.) may still be populated.
- Next-steps panel names `spec-kitty next` (loop entry) and `spec-kitty agent action implement/review` (per-decision verbs).
- Re-run in an already-initialized directory is idempotent or fails fast.
- Run inside an existing git repo: no git state changes.

## Branch Strategy

Plan in `main`, implement in the lane worktree allocated by `finalize-tasks`. Merge back to `main` on completion.

## Subtask Guidance

### T001 — Remove git initialization from `init.py`

**File**: `src/specify_cli/cli/commands/init.py`, `src/specify_cli/core/git_ops.py`

**Steps**:

1. In `init.py`, locate `init_git_repo(project_path, quiet=True)` call at lines ~547-560. Remove the entire `if not no_git:` block. Remove the conditional that checks `--no-git`.

2. Remove the `--no-git` typer option parameter from the `init()` function signature (at `init.py:267`). Remove all references to `no_git` local variable in the function body.

3. In `git_ops.py`, the `init_git_repo()` function itself (lines 104-128) may remain if it has other callers outside `init.py`. Add a grep for all other call sites: if it has no callers, delete it; if it has callers, leave it but add a docstring note saying it must not be called from `init`.

4. Delete the literal string `"Initial commit from Specify template"` from the codebase. After your change, verify with: `grep -r "Initial commit from Specify template" src/` — must return no matches.

5. Update the CLI entry point registration if `--no-git` was listed in the help epilog or other registration files. Search `grep -r "no-git" src/`.

**Validation**:
- `grep -r "Initial commit from Specify template" src/` → empty
- `grep -r "no-git\|no_git" src/specify_cli/cli/commands/init.py` → empty
- Running `spec-kitty init --help` does NOT show `--no-git` option

**Risk**: If `init_git_repo()` is called from test setup fixtures, those fixtures will break. Search `tests/` for calls to `init_git_repo` and update test setup accordingly (they should call `git init` directly via subprocess, not through the spec-kitty function).

---

### T002 — Remove `.agents/skills/` seeding

**File**: `src/specify_cli/cli/commands/init.py`

**Steps**:

1. Find the `install_skills_for_agent()` call block at `init.py:515-540`. Read the surrounding logic: it calls `skill_registry_per_agent.discover_skills()` and then iterates agents, installing skills. Identify whether this installs into `.agents/skills/` (shared) or into per-agent directories (`.codex/prompts/`, `.claude/skills/`, etc.).

2. Per spec D-1 / FR-003: `.agents/skills/` seeding must be removed. Per-agent directory installs (`.codex/prompts/`, etc.) MAY remain if they are part of the new init model (the spec permits skills under the agent's own directory).

3. Remove only the code path that targets the shared `.agents/skills/` root. If `install_skills_for_agent()` installs ONLY to per-agent directories, the entire call may be preserved. If it also seeds `.agents/skills/`, add a parameter or conditional to skip the shared root.

4. After the change: `spec-kitty init demo --ai codex --non-interactive` against a temp dir → `.agents/skills/` does NOT exist.

**Validation**:
- Test T1.3: `(tmp_path / "demo" / ".agents" / "skills").exists() == False`
- Per-agent directory (`.codex/prompts/`) still contains the slash-command files

---

### T003 — Rewrite `init` next-steps output

**File**: `src/specify_cli/cli/commands/init.py:641-650`

**Steps**:

1. Find the "Next Steps" panel construction at lines 641-650. It currently appends slash-command lines including `/spec-kitty.implement`.

2. Replace the entire panel content with a new block that:
   - Names the canonical loop entry: `spec-kitty next --agent <agent> --mission <slug>` (or the slash-command equivalent `/spec-kitty.next`)
   - Names the per-decision verbs: `spec-kitty agent action implement <WP> --agent <name>` and `spec-kitty agent action review <WP> --agent <name>`
   - Does NOT name top-level `spec-kitty implement` as a command users should run
   - Preserves the other slash commands if they still apply (`/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`, etc.)

3. The output should read roughly:
   ```
   Next steps:
     /spec-kitty.specify    — create mission specification
     /spec-kitty.plan       — create implementation plan
     /spec-kitty.tasks      — generate work packages
   
   Run your agent loop:
     spec-kitty next --agent <agent> --mission <slug>
   
   Your agent will call:
     spec-kitty agent action implement <WP> --agent <name>  [implement a WP]
     spec-kitty agent action review    <WP> --agent <name>  [review a WP]
   ```
   Adjust to match the existing Rich panel styling of the output.

**Validation**:
- Test T1.4: captured stdout contains `spec-kitty next` and `spec-kitty agent action implement`
- Test T1.4: captured stdout does NOT contain `spec-kitty implement WP` (bare top-level CLI invocation)

---

### T004 — Add idempotency check on re-run

**File**: `src/specify_cli/cli/commands/init.py`

**Steps**:

1. At the start of the `init()` function, after computing the target directory, add a check: if `.kittify/config.yaml` already exists in the target directory, either:
   - Exit 0 with message "Already initialized. Run `spec-kitty upgrade` to migrate." (idempotent path), OR
   - Exit non-zero with a clear message naming the conflict (fail-fast path)

2. Choose the idempotent path (exit 0, no changes) OR fail-fast — be consistent. Whichever you choose, document it in a code comment and in the test.

3. Suggested approach: exit 0 (idempotent) with a Rich `[yellow]Already initialized[/]` message so non-interactive scripts don't break when running `init` twice.

4. Under `--non-interactive`, the same behavior applies (no interactive prompt).

**Validation**:
- Test T1.5: run `init` twice in the same directory → second run exits 0 (idempotent) OR exits non-zero with named conflict. No silent merge.

---

### T005 — Update `init --help` text

**File**: `src/specify_cli/cli/commands/init.py`

**Steps**:

1. Find the typer docstring for the `init` command. Update it to describe the new model:
   - "Creates project files only. Does not initialize a git repository."
   - "Does not create any commits."
   - "The `--no-git` flag from previous versions has been removed."
   - Next steps: `spec-kitty next` loop + `spec-kitty agent action implement/review`

2. Verify the `--help` output does not list `--no-git` as an option.

**Validation**:
- `spec-kitty init --help` output:
  - Contains "Does not initialize a git repository" (or equivalent)
  - Does NOT contain `--no-git`
  - Contains `spec-kitty next` in the description
  - Contains `spec-kitty agent action implement` in the description

---

### T006 — Regression tests for Track 1

**File**: `tests/init/` (extend existing + add new files)

**Test files to create/extend**:

1. **Extend `tests/init/test_init_minimal_integration.py`** (T1.1, T1.2, T1.3):
   ```python
   def test_init_does_not_create_git_dir(tmp_path):
       # Run init in tmp_path/demo
       # Assert: no .git/ directory
   
   def test_init_does_not_create_commit(tmp_path):
       # Run init in tmp_path/demo
       # Assert: "Initial commit from Specify template" not in any file under tmp_path
       # Or: git log fails (no git repo)
   
   def test_init_does_not_create_agents_skills(tmp_path):
       # Run init in tmp_path/demo
       # Assert: no .agents/skills/ directory
   ```

2. **Create `tests/init/test_init_next_steps.py`** (T1.4):
   ```python
   def test_init_next_steps_names_spec_kitty_next(tmp_path, capsys):
       # Run init, capture stdout
       # Assert stdout contains "spec-kitty next"
       # Assert stdout contains "spec-kitty agent action implement"
       # Assert stdout does NOT contain "spec-kitty implement WP"

   def test_init_commit_string_absent_from_source():
       # Assert grep -r "Initial commit from Specify template" src/ is empty
   ```

3. **Create `tests/init/test_init_idempotent.py`** (T1.5):
   ```python
   def test_init_is_idempotent_on_rerun(tmp_path):
       # Run init once
       # Run init again
       # Assert: exits 0 (idempotent) OR exits non-zero with clear message
       # Assert: no silent merge/overwrite
   ```

4. **Create `tests/init/test_init_in_existing_repo.py`** (T1.6):
   ```python
   def test_init_does_not_touch_git_state_in_existing_repo(tmp_path):
       # Setup: create a git repo with one user commit
       # Record: HEAD hash before
       # Run init inside the existing repo
       # Assert: HEAD hash unchanged
       # Assert: git log still shows only the original commit
       # Assert: git status --porcelain shows only the new init files (no modified existing files)
   ```

5. **Extend or create `tests/init/test_init_help.py`** (T1.7):
   ```python
   def test_init_help_does_not_show_no_git_flag(runner):
       result = runner.invoke(app, ["init", "--help"])
       assert "--no-git" not in result.output
       assert "spec-kitty next" in result.output

   def test_passing_no_git_flag_gives_error(runner, tmp_path):
       result = runner.invoke(app, ["init", "--no-git", str(tmp_path)])
       assert result.exit_code != 0
       # typer "no such option" error
   ```

**Coverage target**: ≥90% line coverage on all new/modified init.py code paths.

## Definition of Done

- [ ] `spec-kitty init demo --ai codex --non-interactive` in a fresh `/tmp/` directory produces no `.git/`, no `.agents/skills/`, no commit.
- [ ] The literal string `"Initial commit from Specify template"` is absent from `src/` (confirmed by test).
- [ ] `spec-kitty init --help` does not show `--no-git` option.
- [ ] Passing `--no-git` to init produces a typer "no such option" error.
- [ ] Next-steps output names `spec-kitty next` and `spec-kitty agent action implement/review`.
- [ ] Re-run in an already-initialized directory is idempotent (exit 0) or fail-fast (no silent merge).
- [ ] Running inside an existing git repo leaves git HEAD unchanged.
- [ ] All 6 subtask test files pass under `PWHEADLESS=1 pytest tests/init/ -q`.
- [ ] `mypy --strict src/specify_cli/cli/commands/init.py` is clean.

## Risks

| Risk | Mitigation |
|------|-----------|
| `init_git_repo()` called from test fixtures | Search `tests/` for callers; update them to call `git init` directly. |
| Per-agent skill install accidentally removed | Confirm `.codex/prompts/spec-kitty.*.md` still exists after init by checking T1.1 fixture. |
| `--no-git` removal breaks existing scripts/docs | This is an intentional breaking change. Document in CHANGELOG (the human release engineer handles that). |

## Reviewer Guidance

Verify:
1. No execution path through `init.py` reaches `git init`, `git add`, or `git commit` — even with creative flag combinations.
2. The string `"Initial commit from Specify template"` is truly gone from `src/`.
3. The next-steps output is accurate: names `spec-kitty next` and `agent action implement`, does NOT name bare `spec-kitty implement`.
4. All 6 subtask tests pass without modification to the test assertions.
