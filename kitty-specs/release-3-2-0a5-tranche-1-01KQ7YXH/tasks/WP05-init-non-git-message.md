---
work_package_id: WP05
title: FR-005 init non-git message (+ FR-003 init.py boundary line)
dependencies: []
requirement_refs:
- FR-003
- FR-005
planning_base_branch: release/3.2.0a5-tranche-1
merge_target_branch: release/3.2.0a5-tranche-1
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a5-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a5-tranche-1 unless the human explicitly redirects the landing branch.
created_at: '2026-04-27T18:00:45+00:00'
subtasks:
- T022
- T023
- T024
- T025
agent: "reviewer-renata"
shell_pid: "80527"
history:
- at: '2026-04-27T18:00:45Z'
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/init.py
execution_mode: code_change
mission_id: 01KQ7YXHA5AMZHJT3HQ8XPTZ6B
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
owned_files:
- src/specify_cli/cli/commands/init.py
- tests/specify_cli/cli/commands/test_init_non_git_message.py
role: implementer
tags:
- ux
- init
---

# WP05 — FR-005 `init` non-git message (+ FR-003 init.py boundary line)

## ⚡ Do This First: Load Agent Profile

Before reading further or making any edits, invoke the `/ad-hoc-profile-load` skill with these arguments:

- **Profile**: `implementer-ivan`
- **Role**: `implementer`

This loads your identity, governance scope, and self-review checklist. The bug-fixing-checklist tactic guides you to write the failing test (T025) before changing `init.py`.

## Objective

When `spec-kitty init` runs in a directory that is **not** inside a git work tree, surface a single actionable line guiding the user to run `git init` before downstream `agent` commands will work, then **complete the scaffold and exit 0** as today. Do NOT auto-init the repo (existing T001 design decision in `init.py` says init is file-creation-only). Do NOT bail out before writing files.

**Canonical invariant** (Decision Moment `01KQ84P1AJ8H3FPJN9J5C12CBY` resolved by user): non-git init is allowed; silent non-git init is not. Fail-fast semantics were considered and rejected.

This WP also owns one cross-FR cleanup line: remove the deprecated `/spec-kitty.checklist` reference from `init.py:723`. That line falls under FR-003's bulk-edit scope but is housed here so `init.py` ownership stays single-WP (avoids a false DIRECTIVE_035 collision with WP04).

## Context

- Today (`src/specify_cli/cli/commands/init.py`):
  - Line ~222–230: `is_git_available()` checks for the `git` binary and raises `VCSNotFoundError("git is not available. Please install git.")` if missing.
  - Line ~360: `_console.print("[yellow]ℹ git not detected[/yellow] - install git for version control")` runs in the binary-missing path.
  - Line ~595–597: A T001 comment notes "No git initialization. init is file-creation-only."
  - Line ~723: A `_console.print("○ [cyan]/spec-kitty.checklist[/] ...")` line that promotes the deprecated checklist command in the post-init quick-start.
- The hole #636 names: a non-git target gets a fully-populated `.kittify/` with no hint that `git init` is required.
- See [research.md R4](../research.md#r4--spec-kitty-init-non-git-target-fr-005--636) and [contracts/init_non_git_message.contract.md](../contracts/init_non_git_message.contract.md).

## Branch Strategy

- **Planning base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target**: `release/3.2.0a5-tranche-1`
- This WP has no dependencies; its lane is rebased directly onto `release/3.2.0a5-tranche-1`.
- Execution worktrees are allocated per computed lane from `lanes.json` (created by `finalize-tasks`).

## Subtasks

### T022 — Add non-git-target detection in `init.py`

**Purpose**: Detect when the target directory is not inside a git work tree and print one actionable info line.

**Files**:
- `src/specify_cli/cli/commands/init.py`

**Steps**:

1. Locate the existing `git not detected` branch (~line 360). Identify the function that resolves VCS state.
2. Add a sibling check: when `is_git_available()` returns True (binary is installed) BUT the target directory is not inside a git work tree, print one yellow info line that contains BOTH the substring "not a git repository" AND the substring "git init".
3. Implementation sketch (adapt to the surrounding style):

   ```python
   def _is_inside_git_work_tree(target: Path) -> bool:
       """Return True when `target` is inside a git work tree.

       Caller should already have verified `is_git_available()` is True.
       """
       result = subprocess.run(
           ["git", "rev-parse", "--is-inside-work-tree"],
           cwd=str(target),
           check=False,
           capture_output=True,
           text=True,
       )
       return result.returncode == 0 and result.stdout.strip() == "true"
   ```

4. Call `_is_inside_git_work_tree(target)` after the binary-availability check. If False, print:

   ```python
   _console.print(
       "[yellow]ℹ Target is not a git repository[/yellow] — "
       "run `git init` here before using `spec-kitty agent ...` commands."
   )
   ```

5. Do NOT raise. Continue with file creation as today.

**Validation**:
- [ ] `init.py` imports `subprocess` (or already does).
- [ ] The new helper has a docstring noting WHY the caller must verify `is_git_available()` first.
- [ ] No call to `git init` is added.

**Edge Cases / Risks**:
- If `git` binary is missing entirely, `is_git_available()` already short-circuits this branch. Don't double-print.
- If the target directory does not yet exist, `subprocess.run(cwd=...)` will fail. Make sure this branch runs AFTER the directory has been created (or wrap the subprocess call in a `try` that returns `False` on `FileNotFoundError`).

### T023 — Append "next: run `git init`" to the post-init quick-start summary

**Purpose**: Reinforce the message at the end of the init flow, where the user reads the next-steps list.

**Files**:
- `src/specify_cli/cli/commands/init.py`

**Steps**:

1. Locate the post-init quick-start summary block (search for "Next steps" or the `_console.print` calls that produce the bulleted list near the end of the init function).
2. When `_is_inside_git_work_tree(target)` is False at that point, prepend a single bullet to the suggested next-steps list:

   ```python
   _console.print("○ [yellow]Run [cyan]git init[/cyan][/yellow] - this directory is not yet a git repository")
   ```

3. Place it ABOVE all other next-step bullets so it's the first thing the user sees.

**Validation**:
- [ ] Bullet appears exactly once.
- [ ] Bullet does NOT appear when target IS a git repo.

### T024 — Remove the `/spec-kitty.checklist` quick-start line at `init.py:723`

**Purpose**: Cross-FR cleanup. WP04 owns the bulk `/spec-kitty.checklist` removal; this single line lives in a file owned by WP05, so it lands here.

**Files**:
- `src/specify_cli/cli/commands/init.py`

**Steps**:

1. Locate line ~723:

   ```python
   "○ [cyan]/spec-kitty.checklist[/] [bright_black](optional)[/bright_black] - Cross-artifact consistency & alignment report (after [cyan]/spec-kitty.tasks[/])",  # noqa: E501
   ```

2. Delete the entire string element (it's an item in a list passed to `_console.print` or similar).
3. Verify no other code path constructs this list — only the literal at ~line 723.

**Validation**:
- [ ] `grep -n "spec-kitty\.checklist" src/specify_cli/cli/commands/init.py` prints zero matches.
- [ ] The post-init quick-start summary still renders cleanly (run `spec-kitty init` against a tmp dir and visually confirm).

**Note**: This is a single-line tracking item against `occurrence_map.yaml::cli_commands::remove`.

### T025 — Add `tests/specify_cli/cli/commands/test_init_non_git_message.py`

**Purpose**: Unit and CliRunner smoke for the new behavior.

**Files**:
- `tests/specify_cli/cli/commands/test_init_non_git_message.py` (new)

**Steps**:

1. Create the new test file:

   ```python
   from __future__ import annotations

   import re
   from pathlib import Path

   import pytest
   from click.testing import CliRunner

   from specify_cli.cli import cli  # adjust import to actual entrypoint


   NOT_A_GIT_REPO = re.compile(r"not\s+a\s+git\s+repository", re.IGNORECASE)
   GIT_INIT_HINT = re.compile(r"\bgit\s+init\b", re.IGNORECASE)


   def test_init_in_non_git_dir_emits_actionable_message(tmp_path: Path) -> None:
       runner = CliRunner()
       result = runner.invoke(
           cli,
           ["init", str(tmp_path / "demo"), "--no-confirm"],
           catch_exceptions=False,
       )
       assert result.exit_code == 0, result.output

       # Strip rich markup before regex match
       output = result.output

       assert NOT_A_GIT_REPO.search(output), (
           f"Expected 'not a git repository' in output, got:\n{output}"
       )
       assert GIT_INIT_HINT.search(output), (
           f"Expected 'git init' guidance in output, got:\n{output}"
       )

       # Init did NOT auto-init git
       assert not (tmp_path / "demo" / ".git").exists()


   def test_init_in_existing_git_repo_does_not_emit_non_git_message(
       tmp_path: Path,
   ) -> None:
       # Arrange: make tmp_path a git repo
       import subprocess
       subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

       # Act
       runner = CliRunner()
       result = runner.invoke(
           cli, ["init", str(tmp_path / "demo"), "--no-confirm"],
           catch_exceptions=False,
       )
       assert result.exit_code == 0

       # Assert: NO "not a git repository" message
       assert not NOT_A_GIT_REPO.search(result.output)
   ```

2. Adapt the CLI import to the actual entrypoint module. (Look at sibling tests in `tests/specify_cli/cli/commands/` for the conventional import.)
3. If the project uses a custom CliRunner fixture, reuse it.

**Validation**:
- [ ] `pytest tests/specify_cli/cli/commands/test_init_non_git_message.py -q` exits 0 (after T022, T023).
- [ ] Both test functions pass; the second confirms no false positive in git repos.

**Edge Cases / Risks**:
- The `--no-confirm` flag may not exist. If `init` is interactive, drive it via `runner.invoke(input="y\n")` or whichever pattern the existing init tests use.
- Rich markup may need to be stripped before regex matching; if so, use `rich.markup.strip(...)` or similar.

## Test Strategy

- Unit + CliRunner-driven smoke in T025 covers the entire FR-005 contract.
- T024's removal is verified by `grep` (no functional behavior changes — just one fewer line in the console output).

## Definition of Done

- [ ] T022–T025 complete.
- [ ] `pytest tests/specify_cli/cli/commands/test_init_non_git_message.py -q` exits 0.
- [ ] `grep -c "spec-kitty\.checklist" src/specify_cli/cli/commands/init.py` prints `0`.
- [ ] Manual smoke: `mkdir -p /tmp/sk-test && spec-kitty init /tmp/sk-test/demo` shows the new info line and the new "next: git init" bullet.
- [ ] PR description includes:
  - One-line CHANGELOG entry for **WP02** to consolidate. Suggested: `\`spec-kitty init\` in a non-git directory now prints an actionable "run \`git init\`" message (#636).`
  - Note the FR-003 boundary line removal (one of the 27 REMOVE occurrences from `occurrence_map.yaml`).

## Risks

- **R1**: The non-git check may add a small subprocess invocation overhead per `init` call. Acceptable — `init` is a one-time setup command, not a hot path.
- **R2**: A reviewer might think T024 belongs to WP04. Defensive note in the PR description: WP04's owned_files explicitly excludes `init.py` to avoid DIRECTIVE_035 collision; T024 is housed here to keep `init.py` single-owner.

## Reviewer Guidance

- Verify the new info line contains BOTH "not a git repository" AND "git init" substrings (case-insensitive).
- Verify the message is at info-level styling (yellow), not error-level (red).
- Verify NO `git init` subprocess is added — only the detection check.
- Verify T024 deletes the exact line at ~723 and nothing else in that region.
- Confirm CHANGELOG candidate text in the PR description for WP02 to pick up.

## Implementation command

```bash
spec-kitty agent action implement WP05 --agent claude
```

## Activity Log

- 2026-04-27T20:17:25Z – claude:sonnet:implementer-ivan:implementer – shell_pid=79003 – Started implementation via action command
- 2026-04-27T20:23:27Z – claude:sonnet:implementer-ivan:implementer – shell_pid=79003 – Ready for review: non-git detection + 2 unit tests; init.py:723 deprecated line removed; canonical invariant 'non-git init is allowed; silent non-git init is not' verified
- 2026-04-27T20:24:03Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=80527 – Started review via action command
- 2026-04-27T20:25:45Z – reviewer-renata – shell_pid=80527 – Review passed: canonical invariant verified — non-git init allowed but loud (yellow info line + top quick-start bullet, both contain 'not a git repository' + 'git init'); no auto git init, exit 0, scaffold completes. T022 _is_inside_git_work_tree helper has docstring noting is_git_available() precondition and returns False on FileNotFoundError/OSError. T023 'Run git init' bullet prepended to steps_lines. T024 init.py:723 /spec-kitty.checklist line removed (grep returns 0). T025: 2/2 tests pass; fixture pattern matches sibling test_init_integration.py. Pre-existing ARG001 on activate_mission confirmed against base branch — not introduced. Scope clean (init.py + new test only).
