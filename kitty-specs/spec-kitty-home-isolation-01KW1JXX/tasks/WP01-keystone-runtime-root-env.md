---
work_package_id: WP01
title: Keystone — get_runtime_root honors SPEC_KITTY_HOME
dependencies: []
requirement_refs:
- FR-011
- FR-012
tracker_refs: []
planning_base_branch: fix/spec-kitty-home-isolation
merge_target_branch: fix/spec-kitty-home-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/spec-kitty-home-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spec-kitty-home-isolation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-spec-kitty-home-isolation-01KW1JXX
base_commit: 9e7a2f53d1985135b1b1be987431b7cfd58a7246
created_at: '2026-06-26T11:24:56.376268+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
assignee: ''
agent: claude
shell_pid: '31845'
history:
- at: '2026-06-26T11:06:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/paths/
create_intent:
- tests/paths/test_runtime_root_spec_kitty_home.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/paths/windows_paths.py
- src/specify_cli/paths/__init__.py
- tests/kernel/test_paths.py
- tests/kernel/test_paths_unified_windows_root.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Keystone — get_runtime_root honors SPEC_KITTY_HOME

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

This is the **keystone** of the mission (GitHub issue #2171). Every other WP depends on it.

Make `specify_cli.paths.get_runtime_root()` honor `SPEC_KITTY_HOME`:

- **DONE when**: with `SPEC_KITTY_HOME` set to a non-empty value, `get_runtime_root().base == Path($SPEC_KITTY_HOME)` on **all** platforms (`linux`, `darwin`, `win32`).
- Unset/empty `SPEC_KITTY_HOME` → preserves current defaults: POSIX `Path.home() / ".spec-kitty"`, Windows `platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)`.
- Resolution stays **pure** — no directories created, no file I/O (NFR-002).
- `RuntimeRoot` remains a frozen dataclass; its derived properties (`auth_dir`, `sync_dir`, `daemon_dir`, `tracker_dir`, `cache_dir`) are unchanged and now inherit the env-aware base.

Requirements: **FR-011, FR-012** (and enables FR-001..FR-010).

## Context & Constraints

- Spec: `kitty-specs/spec-kitty-home-isolation-01KW1JXX/spec.md`
- Plan / research / contracts: `kitty-specs/spec-kitty-home-isolation-01KW1JXX/{plan.md,research.md,contracts/runtime-state-root.md}`
- **Current code** (`src/specify_cli/paths/windows_paths.py`):
  - `RuntimeRoot` frozen dataclass at lines ~16–56 (`base` + derived dir properties).
  - `get_runtime_root()` at lines ~58–79: POSIX hardcodes `Path.home() / ".spec-kitty"`; Windows uses platformdirs; **no `SPEC_KITTY_HOME` check** — this is the bug.
- **Reference idiom** — `get_kittify_home()` already does this correctly in both `src/specify_cli/runtime/home.py:33` and `src/kernel/paths.py:46`:
  ```python
  if env_home := os.environ.get("SPEC_KITTY_HOME"):
      return Path(env_home)
  ```
  Use the **same walrus-falsy idiom** so an empty string falls through (matches asset-home and its existing test).
- **The venv is already warm** (`.venv` populated). Prefer `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy` directly.

## Branch Strategy

- **Strategy**: shared-feature-branch
- **Planning base branch**: fix/spec-kitty-home-isolation
- **Merge target branch**: fix/spec-kitty-home-isolation

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T001 – Add SPEC_KITTY_HOME read to get_runtime_root()

- **Purpose**: Make the env var the authoritative base selector on all platforms.
- **Steps**:
  1. In `get_runtime_root()`, **before** the `win32`/POSIX branches, add:
     ```python
     if env_home := os.environ.get("SPEC_KITTY_HOME"):
         base = Path(env_home)
     elif platform == "win32":
         base = Path(platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False))
     else:
         base = Path.home() / ".spec-kitty"
     ```
  2. Keep returning `RuntimeRoot(platform=platform, base=base)`.
  3. Ensure `import os` is present.
- **Files**: `src/specify_cli/paths/windows_paths.py`
- **Notes**: A non-empty env value becomes `base` directly (so `config.toml` lands at `$SPEC_KITTY_HOME/config.toml`). Do not append `.spec-kitty` to the env path.

### Subtask T002 – Preserve RuntimeRoot purity

- **Purpose**: Guarantee no behavioral side effects.
- **Steps**: Confirm `RuntimeRoot` stays `@dataclass(frozen=True)`; no `mkdir`, no `exists()`, no writes in `get_runtime_root()` or property getters. If `__init__.py` re-exports change, keep the public surface (`get_runtime_root`, `RuntimeRoot`, `render_runtime_path`) intact.
- **Files**: `src/specify_cli/paths/windows_paths.py`, `src/specify_cli/paths/__init__.py`

### Subtask T003 [P] – Env-precedence unit tests

- **Purpose**: Lock the contract (contracts/runtime-state-root.md T-RR-1..T-RR-4).
- **Steps**: Create `tests/paths/test_runtime_root_spec_kitty_home.py`:
  - For each platform in `{"linux","darwin","win32"}` (monkeypatch `_current_platform` or the `sys.platform` source used by `get_runtime_root`):
    - `SPEC_KITTY_HOME=/tmp/x` ⇒ `base == Path("/tmp/x")`.
    - `SPEC_KITTY_HOME=""` ⇒ falls through to platform default.
    - unset ⇒ POSIX `~/.spec-kitty`; win32 platformdirs base.
  - Use `monkeypatch.setenv`/`delenv` and `monkeypatch.setattr` for HOME/platform.
- **Files**: `tests/paths/test_runtime_root_spec_kitty_home.py`
- **Parallel?**: Yes (new file).

### Subtask T004 [P] – Extend kernel path tests

- **Purpose**: Keep the existing path test suite aligned with the new base behavior.
- **Steps**: Review `tests/kernel/test_paths.py` and `tests/kernel/test_paths_unified_windows_root.py`; add/adjust cases proving `SPEC_KITTY_HOME` precedence flows into `get_runtime_root().base` and derived dirs. Do not weaken existing assertions.
- **Files**: `tests/kernel/test_paths.py`, `tests/kernel/test_paths_unified_windows_root.py`
- **Parallel?**: Yes.

### Subtask T005 – No-directory-creation assertion

- **Purpose**: Prove NFR-002 (pure resolution).
- **Steps**: In the new test file, point HOME and `SPEC_KITTY_HOME` at fresh temp dirs, call `get_runtime_root()` and read `.base/.auth_dir/.sync_dir/...`, then assert none of those directories were created on disk.
- **Files**: `tests/paths/test_runtime_root_spec_kitty_home.py`

## Test Strategy

- Run: `.venv/bin/pytest tests/paths/test_runtime_root_spec_kitty_home.py tests/kernel/test_paths.py tests/kernel/test_paths_unified_windows_root.py -q`
- Lint/types: `.venv/bin/ruff check src/specify_cli/paths tests/paths` and `.venv/bin/mypy src/specify_cli/paths`

## Risks & Mitigations

- **Empty string**: ensure falsy fall-through (T003). 
- **Platform monkeypatching**: confirm how `get_runtime_root` detects platform (`_current_platform()`); patch the right symbol.
- **Public surface**: keep `paths/__init__.py` exports stable — many modules import from `specify_cli.paths`.

## Review Guidance

- Verify the env check precedes platform branches and uses the walrus-falsy idiom.
- Confirm zero directory creation and frozen dataclass intact.
- Confirm all three platforms covered in tests, including empty-string fall-through.

## Activity Log

- 2026-06-26T11:06:32Z – system – Prompt created.

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP01 --to <status>` to change WP status.
