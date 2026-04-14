---
work_package_id: WP04
title: Registry Wiring and Runtime Routing
dependencies:
- WP03
base_branch: main
base_commit: f77b338496a13dd0685eedcba899765e965e0d90
created_at: '2026-04-14T10:16:24.526697+00:00'
subtasks:
- T018
- T019
- T020
- T021
- T022
lane: "doing"
shell_pid: "13190"
history:
- at: '2026-04-14T00:00:00+00:00'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/
branch_strategy: lane-worktree
execution_mode: code_change
merge_target_branch: main
owned_files:
- src/specify_cli/core/config.py
- src/specify_cli/agent_utils/directories.py
- src/specify_cli/runtime/agent_commands.py
- src/specify_cli/cli/commands/agent/config.py
- tests/specify_cli/core/test_config_registry.py
- tests/specify_cli/runtime/test_agent_commands_routing.py
planning_base_branch: main
requirement_refs:
- FR-001
- FR-002
- FR-011
- FR-013
---

# WP04 — Registry Wiring and Runtime Routing

## Objective

Thread `vibe` into every registry the CLI consults to recognize an agent, and route both `codex` and `vibe` through the new `command_installer` instead of the legacy command-file rendering path. Remove `codex` from the command-file registries because its command layer is retired.

## Context

The installer and renderer from WP01-03 are in place but nothing calls them yet. This WP connects the plumbing.

Files being edited (each owned by this WP):

- `src/specify_cli/core/config.py` — canonical registries (`AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, `AGENT_COMMAND_CONFIG`, `AGENT_SKILL_CONFIG`).
- `src/specify_cli/agent_utils/directories.py` — `AGENT_DIRS`, `AGENT_DIR_TO_KEY`, and migration-related mappings referenced in `CLAUDE.md`.
- `src/specify_cli/runtime/agent_commands.py` — the code path that currently renders command files; now branches on agent key.
- `src/specify_cli/cli/commands/agent/config.py` — `agent config remove` dispatch.

Do not touch `init.py`, `verify.py`, or `gitignore_manager.py` in this WP — those belong to WP05 and overlap would violate ownership.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per lane from `lanes.json` after `finalize-tasks`. This WP depends on WP03, so it lands after WP03.

## Implementation

### Subtask T018 — Edit `core/config.py`

- `AI_CHOICES`: add `"vibe": "Mistral Vibe"`. Keep keys sorted alphabetically if the file already sorts them; otherwise append.
- `AGENT_TOOL_REQUIREMENTS`: add `"vibe": ("vibe", "https://github.com/mistralai/mistral-vibe")`.
- `AGENT_COMMAND_CONFIG`: **remove** the `"codex"` entry entirely. Do NOT add `"vibe"` — Vibe never had a command-file layer.
- `AGENT_SKILL_CONFIG`: add `"vibe": {"class": SKILL_CLASS_SHARED, "skill_roots": [".agents/skills/"]}`. The existing `"codex"` entry already has class `SKILL_CLASS_SHARED` and `skill_roots=[".agents/skills/"]` — leave it as is.
- `IDE_AGENTS`: do not add `vibe` (it is a CLI agent, not IDE-integrated).
- Update `__all__` only if you add new exports — no new exports are expected in this WP.

Verify by running `grep -n '"codex"' src/specify_cli/core/config.py` — the only remaining references should be in `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, and `AGENT_SKILL_CONFIG`.

### Subtask T019 — Edit `agent_utils/directories.py` [P]

- Remove the `(".codex", "prompts")` tuple from `AGENT_DIRS`.
- Add `(".agents", "skills")` entry for vibe if and only if `AGENT_DIRS` is used for shared-root agents elsewhere. Inspect callers first with `grep -rn 'AGENT_DIRS' src/specify_cli/ tests/specify_cli/`. If `AGENT_DIRS` is only used for command-file agents, do not add a vibe entry — the shared `.agents/skills/` is already represented by `AGENT_SKILL_CONFIG`.
- Update `AGENT_DIR_TO_KEY`: remove the `.codex` → `codex` mapping (if it exists in this file).
- Update any hardcoded agent list in this module (e.g., the comment on line 68 showing a sample iteration set) to reflect the new registry state.

If migrations reference these constants via `get_agent_dirs_for_project()`, confirm the migration infrastructure still returns sensible data — WP06's migration will lean on this.

### Subtask T020 — Edit `runtime/agent_commands.py`

Find the function (or functions) that today writes command files for each configured agent. The relevant pointer from `grep` was `runtime/agent_commands.py:145` where `arg_format` is consulted. Trace upward from there to the enclosing function.

Add a branch at the top of that function:

```python
if agent_key in ("codex", "vibe"):
    from specify_cli.skills import command_installer
    return command_installer.install(repo_root, agent_key)
```

Keep the existing path for every other agent byte-identical. Do not restructure the existing loop — the goal is minimum diff on the twelve non-migrated agents so WP07's regression snapshot passes.

If the existing function returns a specific type that differs from `InstallReport`, wrap the installer call to produce the caller's expected shape. Add a test (T022) that exercises both branches.

### Subtask T021 — Edit `cli/commands/agent/config.py`

Find the `remove` command implementation. Today it deletes the agent's command directory (e.g., `.codex/prompts/`). For codex and vibe, this must instead call `command_installer.remove(repo_root, agent_key)`.

Add a branch:

```python
if agent_key in ("codex", "vibe"):
    from specify_cli.skills import command_installer
    report = command_installer.remove(repo_root, agent_key)
    _print_remove_report(console, report)
    # Also update config.yaml to drop the agent key (this is the existing behavior,
    # preserve it unchanged).
    ...
else:
    # existing removal logic for command-layer agents
    ...
```

Do not duplicate the `config.yaml` update — reuse the existing helper.

For `add`, the existing flow calls the runtime; that flow will end up calling the installer via WP04's T020 changes. No edit needed here for `add`.

### Subtask T022 — Unit tests

Create two test files:

**`tests/specify_cli/core/test_config_registry.py`**:

- `test_vibe_in_ai_choices`: `"vibe" in AI_CHOICES` and `AI_CHOICES["vibe"] == "Mistral Vibe"`.
- `test_vibe_tool_requirement`: `AGENT_TOOL_REQUIREMENTS["vibe"][0] == "vibe"`.
- `test_codex_not_in_command_config`: `"codex" not in AGENT_COMMAND_CONFIG`.
- `test_vibe_not_in_command_config`: `"vibe" not in AGENT_COMMAND_CONFIG`.
- `test_codex_and_vibe_are_shared_skill_roots`: both have class `SKILL_CLASS_SHARED` with `.agents/skills/` as the primary root.
- `test_twelve_agents_still_in_command_config`: assert the other twelve agent keys are present (claude, copilot, gemini, cursor, qwen, opencode, windsurf, kilocode, auggie, roo, q, antigravity). This is a smoke test for NFR-005.

**`tests/specify_cli/runtime/test_agent_commands_routing.py`**:

- `test_codex_routes_to_installer`: mock `specify_cli.skills.command_installer.install` and assert it is called with `agent_key="codex"` when the runtime is asked to write for codex.
- `test_vibe_routes_to_installer`: same but for `vibe`.
- `test_claude_still_routes_to_command_files`: mock the installer and assert it is NOT called when the agent is `claude`; the legacy command-file path runs.

Where the runtime needs a `repo_root`, feed it a tmpdir fixture. Where it needs a `config`, build a minimal one.

## Definition of Done

- [ ] `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, `AGENT_SKILL_CONFIG` include `vibe`.
- [ ] `AGENT_COMMAND_CONFIG` no longer contains `codex`.
- [ ] `runtime/agent_commands.py` routes `codex` and `vibe` through `command_installer.install`.
- [ ] `cli/commands/agent/config.py` routes `remove` for `codex`/`vibe` through `command_installer.remove`.
- [ ] `tests/specify_cli/core/test_config_registry.py` and `tests/specify_cli/runtime/test_agent_commands_routing.py` pass.
- [ ] `ruff check src/specify_cli/` passes.
- [ ] `grep -n '\.codex/prompts' src/specify_cli/` returns only references in migration code (WP06) or in generated-asset templates that are explicitly out of scope here.
- [ ] No changes outside `owned_files`.

## Risks

- **`AGENT_DIRS` contract leak**. If `AGENT_DIRS` is consulted by `gitignore_manager.py` or other callers, removing the codex tuple could break them. Grep before editing and adjust tests accordingly.
- **Import cycles**. `runtime/agent_commands.py` importing `specify_cli.skills.command_installer` must not create a cycle. Use the `from specify_cli.skills import command_installer` form inside the function body to defer the import.
- **Coexistence with existing skills installation**. Spec Kitty already installs *skills* (like `spec-kitty-runtime-next`) into `.agents/skills/` for codex via `AGENT_SKILL_CONFIG`. The installer for *commands* must not trample those skill directories — they are named differently (not `spec-kitty.<command>`), so they sort to different keys in the manifest, but add a coexistence test in WP03 or here if any doubt.

## Reviewer Guidance

- Diff `src/specify_cli/core/config.py` at the registry-by-registry level. Confirm each registry edit is minimal and leaves every non-codex / non-vibe agent untouched.
- Read the single new branch added to `runtime/agent_commands.py` and confirm the existing loop body for the twelve other agents is byte-identical.
- Confirm no new `print()` or `console.print()` statements were added that would change CLI output visible to users of the twelve non-migrated agents.

## Command to run implementation

```bash
spec-kitty agent action implement WP04 --agent <name>
```
