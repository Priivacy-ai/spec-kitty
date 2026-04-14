---
work_package_id: WP07
title: Per-Worktree Exclude Writer, External Session-Warning Sites, and Once-Per-Process Test
dependencies:
- WP02
- WP06
requirement_refs:
- FR-010
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T030
- T037
phase: Phase 2 — Polish
agent: "claude:opus-4.6:implementer:implementer"
shell_pid: "61123"
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/core/worktree.py
execution_mode: code_change
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- src/specify_cli/core/worktree.py
- src/specify_cli/cli/commands/glossary.py
- tests/integration/sparse_checkout/test_session_warning_once.py
- tests/integration/core/test_worktree_exclude_spec_kitty.py
tags: []
wp_code: WP07
---

# Work Package Prompt: WP07 — Per-Worktree Exclude, External Session-Warning Sites, Once-Per-Process Test

## Implementation Command

```bash
spec-kitty agent action implement WP07 --agent <your-agent-name> --mission 01KP54ZW
```

Depends on WP02 (warn function) and WP06 (in-tasks.py session-warning call sites — required for the combined NFR-005 test to be meaningful). Rebase onto the combined lane where WP06 lands.

**Ownership note**: `merge.py` is owned by WP05. WP07 does NOT edit `merge.py`. The merge path's session-warning surface is WP05's preflight: the preflight already emits a WARNING (either the block message or the override log record) whenever sparse-checkout state is detected, so a separate `warn_if_sparse_once()` call on merge would be redundant.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- Lane allocation by `finalize-tasks`; resolve from `lanes.json`.

---

## Objective

Three small but distinct pieces of polish:
1. Write `.spec-kitty/` to every new lane worktree's per-worktree exclude file at creation (FR-016).
2. Install session-warning call sites at the remaining external CLI surfaces outside `agent/tasks.py` (FR-010 completion).
3. Ship the NFR-005 once-per-process integration test.

---

## Context

- FR-016: belt-and-braces defense for FR-015 — even without the deny-list filter, git would not surface `.spec-kitty/` as untracked if the per-worktree exclude is in place. Eliminates another class of false positives.
- The per-worktree exclude file lives at `<git-common-dir>/worktrees/<name>/info/exclude`. It is NOT committed; it is per-worktree local.
- External CLI surfaces needing the session warning (excluding merge and agent/tasks.py, which are covered by WP05 and WP06 respectively):
  - `spec-kitty charter sync` (in `src/specify_cli/cli/commands/glossary.py` — verify; it may live elsewhere)
  - Any other state-mutating top-level command that does NOT route through `agent/tasks.py` and is not the merge command

---

## Subtask Guidance

### T030 — Per-worktree exclude writer at lane worktree creation

**Files**: `src/specify_cli/core/worktree.py`

**What**: Find the lane-worktree creation path (search for `git worktree add`). Immediately after the worktree is successfully created, resolve the per-worktree exclude path and append `.spec-kitty/` if it is not already present.

Helper:

```python
def _ensure_spec_kitty_exclude(worktree_path: Path) -> None:
    """Ensure '.spec-kitty/' is listed in the worktree's info/exclude file.

    FR-016: prevent spec-kitty's own runtime state directory from appearing as
    untracked content in the review lane's git status.
    """
    # Resolve git common dir for the worktree.
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        logger.warning("Could not resolve git-dir for %s; skipping exclude setup", worktree_path)
        return
    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = worktree_path / git_dir
    info_dir = git_dir / "info"
    info_dir.mkdir(parents=True, exist_ok=True)
    exclude_path = info_dir / "exclude"
    existing_lines: list[str] = []
    if exclude_path.exists():
        existing_lines = exclude_path.read_text(encoding="utf-8").splitlines()
    if any(line.strip() == ".spec-kitty/" for line in existing_lines):
        return
    existing_lines.append(".spec-kitty/")
    exclude_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")
```

Invoke `_ensure_spec_kitty_exclude(new_worktree_path)` right after the `git worktree add` subprocess in the creation path.

---

### T037 — External session-warning call sites

**Files**: `src/specify_cli/cli/commands/glossary.py` (and any other state-mutating surface identified during implementation that is NOT `merge.py` or `agent/tasks.py`).

**What**: At the entry of each external state-mutating Typer handler, call:

```python
from specify_cli.git.sparse_checkout import warn_if_sparse_once
warn_if_sparse_once(repo_root, command="spec-kitty agent mission merge")
```

with the appropriate `command` string. The call is non-blocking and swallows errors; it is safe to place above any other code.

For `merge.py`: no action — covered by WP05's preflight, which already emits WARNING records on active sparse-checkout state.

For charter sync: locate the handler (likely `src/specify_cli/cli/commands/glossary.py` or `charter.py`) and add the call at its top.

Enumerate other state-mutating surfaces:
- `spec-kitty agent config add/remove/sync` — if state-mutating
- Any `init` command
- `spec-kitty sync` commands

Use judgment; err on the side of including more rather than fewer, because `warn_if_sparse_once` is a no-op on its second call.

---

### T025 — Once-per-process integration test [P]

**Files**: `tests/integration/sparse_checkout/test_session_warning_once.py` (new)

**What**: A single integration test that invokes 3 state-mutating commands in one process and asserts exactly one warning emission.

Pytest approach:

```python
import logging
from typer.testing import CliRunner
from specify_cli.git.sparse_checkout import _reset_session_warning_state

def test_session_warning_emitted_exactly_once(sparse_configured_repo, caplog):
    _reset_session_warning_state()
    caplog.set_level(logging.WARNING)
    runner = CliRunner()
    # Invoke three state-mutating commands back-to-back in the same process.
    # Each one hits a different surface with a session-warning call.
    runner.invoke(app, ["agent", "tasks", "status", "--mission", "test", "--json"])
    runner.invoke(app, ["agent", "tasks", "move-task", "WP01", "--to", "claimed", "--mission", "test"])
    runner.invoke(app, ["agent", "mission", "merge", "--mission", "test", "--dry-run"])
    warning_records = [r for r in caplog.records if "sparse_checkout.detected" in r.getMessage()]
    assert len(warning_records) == 1
```

Adjust commands to match actual CLI surfaces available in the test harness.

**Validation**:
- Reset the session-warning flag before test.
- Use `caplog` — do NOT capture stdout.
- Assert exactly 1 matching log record, not >= 1.

---

## Definition of Done

- [ ] `_ensure_spec_kitty_exclude()` helper in `core/worktree.py` writes to per-worktree `info/exclude` idempotently.
- [ ] Helper invoked after every new lane worktree creation.
- [ ] Session-warning calls present at every identified external state-mutating surface.
- [ ] `test_session_warning_once.py` exists and passes.
- [ ] `test_worktree_exclude_spec_kitty.py` (new) verifies the exclude entry is written once and not duplicated on re-invocation of worktree creation.
- [ ] `mypy --strict` passes on touched files.
- [ ] Existing worktree-creation tests still pass.

## Risks

- **Git common-dir resolution**: `git rev-parse --git-dir` returns a relative path by default inside a worktree. Must normalize to absolute.
- **Duplicate lines in exclude**: re-running worktree creation must not duplicate the entry. Helper checks existing lines before appending.
- **Missed external surfaces**: if a future state-mutating command is added without the warning hook, coverage will drop. Consider whether a module-level docstring in `sparse_checkout.py` (WP02) should list the known call sites — but that is optional; the once-per-process test is the contract.

## Reviewer Guidance

- Verify the per-worktree exclude file is `<git-common-dir>/worktrees/<name>/info/exclude`, NOT `<worktree>/.git/info/exclude` (common misunderstanding; the latter would not exist for a worktree because worktree's `.git` is a file, not a directory).
- Verify the once-per-process test is genuinely single-process. `CliRunner` invokes the Typer app in the same process.
- Verify no session-warning call was accidentally placed in a read-only command handler.

## Activity Log

- 2026-04-14T07:40:59Z – claude:opus-4.6:implementer:implementer – shell_pid=61123 – Started implementation via action command
