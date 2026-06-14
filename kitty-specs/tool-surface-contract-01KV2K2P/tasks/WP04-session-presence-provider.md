---
work_package_id: WP04
title: Session-Presence Provider
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-003
- FR-006
- FR-010
- FR-018
- NFR-001
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
agent: claude
shell_pid: '29358'
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/providers/
create_intent:
- src/specify_cli/tool_surface/providers/session_presence.py
- src/specify_cli/tool_surface/providers/native_config.py
- tests/specify_cli/tool_surface/providers/test_session_presence.py
- tests/specify_cli/tool_surface/providers/test_native_config.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/providers/session_presence.py
- src/specify_cli/tool_surface/providers/native_config.py
- tests/specify_cli/tool_surface/providers/test_session_presence.py
- tests/specify_cli/tool_surface/providers/test_native_config.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Add a `SurfaceProvider` for session presence and context/hook surfaces, making session presence surfaces distinct in `doctor tool-surfaces` output -- explicitly separate from command skills and doctrine skills.

**Important**: `session_presence` is a provider name, not a SurfaceKind. The provider expands into instances of distinct SurfaceKind values:
- `context_file` — CLAUDE.md, AGENTS.md, orientation files (always-on context)
- `hook` — `.claude/settings.json` hook entries (tool lifecycle event handlers)
- `rule` — markdown rules, steering files, cursor rules (path-pattern-activated)

These distinct kinds matter for `--kind` filtering (e.g., `--kind context_file` vs `--kind hook`), for docs validation, and for plugin bundle mapping. The `session_presence` provider MUST expand into `context_file`, `hook`, and/or `rule` instances — never into a fictional `session_presence` kind instance.

For `NullWriter` harnesses: yield a `research-gap-surface` finding (not silent OK).

**Out-of-map edits required**: This WP extends `status.py`, `findings.py`, and `repair.py` (owned by WP03). Record the rationale: "WP04 sequential; no parallel conflict; extends status/findings for context_file/hook/rule SurfaceKinds."

**Child issue**: #1938
**Parent epic**: #1945

## Context

Session presence surfaces are always-on context or orientation files loaded at tool session start. Examples:
- Claude Code: `.claude/CLAUDE.md`, `.claude/settings.json`
- Codex/OpenCode/Antigravity: `AGENTS.md`
- Windsurf/Devin: rules files
- Kiro: steering files

These are categorically different from command skills (slash-command invocations) and must be reported as `context_file`, `hook`, or `rule` kinds in doctor output — NOT as a fictional `session_presence` kind. See the Objective section for the correct SurfaceKind mapping.

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Command: `spec-kitty agent action implement WP04 --agent claude`

## Subtask Details

### T019 -- Implement `providers/session_presence.py`

**Purpose**: Wrap `specify_cli.session_presence.writers.registry` as a `SurfaceProvider`.

**Key design points**:
- The session presence writer registry knows which paths each tool's writer produces
- `expand()` asks the registry what paths a given tool's writer produces
- `probe()` checks whether those paths exist
- `repair()` calls the writer to regenerate the session presence files
- Session presence paths are per-tool and differ significantly between harnesses

```python
_SESSION_PRESENCE_KINDS = frozenset({
    SurfaceKind.CONTEXT_FILE,
    SurfaceKind.HOOK,
    SurfaceKind.RULE,
})

class SessionPresenceProvider:
    provider_key = "session_presence"

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        # session_presence is a PROVIDER NAME, not a SurfaceKind.
        # This provider handles context_file, hook, and rule kinds.
        return definition.kind in _SESSION_PRESENCE_KINDS

    def expand(self, definition: SurfaceDefinition, tool_key: str, project_root: Path) -> list[SurfaceInstance]:
        # Get the writer for this tool key
        # Ask it for the list of paths it manages, tagged with the correct SurfaceKind
        # (CONTEXT_FILE for CLAUDE.md/AGENTS.md, HOOK for settings entries, RULE for rules/steering)
        # Return SurfaceInstance for each — kind from the writer's metadata, not hardcoded
        ...
```

The session presence writer for each tool produces a specific set of files. Consult `src/specify_cli/session_presence/writers/` for the per-tool implementations to understand what paths each writer manages.

**Files**: `src/specify_cli/tool_surface/providers/session_presence.py` (new, ~80 lines)

**Validation**:
- [ ] `isinstance(SessionPresenceProvider(...), AbstractSurfaceProvider)` is True
- [ ] `mypy --strict` passes
- [ ] Does not assume a fixed path -- queries the writer for actual paths

---

### T020 -- Implement `providers/native_config.py`

**Purpose**: Handle tool-specific native config glue: hooks, MCP config, vibe path config. These are `native_config` kind surfaces.

**Scope**:
- Windsurf/Vibe: `.vibe/config.toml` skills path entry
- Claude Code hooks: registered hook entries in `.claude/settings.json`
- Other tool-specific config files that do not fit session presence, command skills, or doctrine skills

This provider is narrower than session presence -- it handles config entries that set up the tool to find its skills, not the orientation/context files themselves.

**Files**: `src/specify_cli/tool_surface/providers/native_config.py` (new, ~60 lines)

**Validation**:
- [ ] `mypy --strict` passes
- [ ] Does not duplicate logic from `session_presence.py`

---

### T021 -- Extend `status.py` and `findings.py` for session-presence provider outputs

**Purpose**: Add session-presence provider output handling to the status service.

**Out-of-map edit to `status.py`** (owned by WP03):
- Extend the `SurfaceStatusService.collect()` status/finding mapping to handle `SurfaceKind.CONTEXT_FILE`, `SurfaceKind.HOOK`, and `SurfaceKind.RULE`
- Use finding codes `context-file-missing`, `session-presence-incomplete` from the stable code table

**Out-of-map edit to `findings.py`** (owned by WP03):
- Confirm `context-file-missing` and `session-presence-incomplete` constants are present; document that this WP activates them
- Do NOT use SCREAMING_SNAKE codes (`TOOL_SURFACE_SESSION_PRESENCE_MISSING`) — use the kebab-case codes from the stable table in data-model.md

**Rationale for out-of-map**: WP04 is sequential after WP03; no parallel conflict. Session-presence kinds must be handled alongside command-skill kind in the same status collection dispatch.

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind context_file --json` returns context-file findings (not `--kind session-presence` — no such kind)
- [ ] Migration compat tests still pass

---

### T022 -- Extend repair service for session-presence findings

**Purpose**: Add session-presence repair dispatch to `repair.py`.

**Out-of-map edit to `repair.py`** (owned by WP03):
- Add cases for `SurfaceKind.CONTEXT_FILE`, `SurfaceKind.HOOK`, and `SurfaceKind.RULE` that delegate to `SessionPresenceProvider.repair()`

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind context_file --fix` repairs missing context files
- [ ] `spec-kitty doctor tool-surfaces --kind hook --fix` repairs missing hook entries
- [ ] Does not affect command-skill repair behavior

---

### T023 -- Write tests for session-presence provider

**Purpose**: Cover `SessionPresenceProvider` and `NativeConfigProvider` with unit tests and integration.

**Tests**:
```python
# test_session_presence.py
def test_session_presence_provider_can_handle_context_file():
    definition = SurfaceDefinition(kind=SurfaceKind.CONTEXT_FILE, ...)
    assert provider.can_handle(definition) is True

def test_session_presence_provider_can_handle_hook():
    definition = SurfaceDefinition(kind=SurfaceKind.HOOK, ...)
    assert provider.can_handle(definition) is True

def test_session_presence_provider_can_handle_rule():
    definition = SurfaceDefinition(kind=SurfaceKind.RULE, ...)
    assert provider.can_handle(definition) is True

def test_session_presence_provider_cannot_handle_command_skill():
    definition = SurfaceDefinition(kind=SurfaceKind.COMMAND_SKILL, ...)
    assert provider.can_handle(definition) is False

def test_session_presence_expand_returns_per_tool_paths():
    """Each tool should have distinct session presence paths."""
    ...

def test_session_presence_probe_detects_missing_file():
    ...
```

**Files**:
- `tests/specify_cli/tool_surface/providers/test_session_presence.py` (new, ~80 lines)
- `tests/specify_cli/tool_surface/providers/test_native_config.py` (new, ~50 lines)

**Validation**:
- [ ] All tests pass
- [ ] WP02 migration compat tests still pass

## Definition of Done

- [ ] `spec-kitty doctor tool-surfaces --kind context_file --json` returns valid output
- [ ] `spec-kitty doctor tool-surfaces --kind hook --json` returns valid output
- [ ] `spec-kitty doctor tool-surfaces --kind rule --json` returns valid output
- [ ] Session presence surfaces appear as distinct `surface_kind` values (`"context_file"`, `"hook"`, `"rule"`) — NOT as `"session_presence"` (there is no such SurfaceKind)
- [ ] `spec-kitty doctor tool-surfaces --kind context_file --fix` repairs missing context files
- [ ] `pytest tests/specify_cli/tool_surface/providers/test_session_presence.py` passes
- [ ] WP02 migration compat tests pass
- [ ] `mypy --strict src/specify_cli/tool_surface/` passes

## Risks

- **Per-tool path variability**: Session presence paths vary significantly per harness. Provider must not assume fixed paths -- must query the writer.
- **Null writers**: Some harnesses have null writers (no session presence). These should produce a `RESEARCH_GAP` finding, not a hard failure.

## Reviewer Guidance (Codex)

- Verify session presence surfaces appear as `context_file`, `hook`, or `rule` kinds — NOT `session_presence` (no such SurfaceKind exists)
- Verify null writers produce `RESEARCH_GAP` (not `error`)
- Verify provider delegates to writer registry, not hardcoded paths
