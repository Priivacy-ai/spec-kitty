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

Add a `SurfaceProvider` for session presence and context/hook surfaces, making session presence a distinct surface kind in `doctor tool-surfaces` output -- explicitly separate from command skills and doctrine skills.

**Out-of-map edits required**: This WP extends `status.py`, `findings.py`, and `repair.py` (owned by WP03). Record the rationale: "WP04 sequential; no parallel conflict; extends status/findings for session-presence SurfaceKind."

**Child issue**: #1938
**Parent epic**: #1945

## Context

Session presence surfaces are always-on context or orientation files loaded at tool session start. Examples:
- Claude Code: `.claude/CLAUDE.md`, `.claude/settings.json`
- Codex/OpenCode/Antigravity: `AGENTS.md`
- Windsurf/Devin: rules files
- Kiro: steering files

These are categorically different from command skills (slash-command invocations) and must be reported as `session_presence` kind in doctor output.

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
class SessionPresenceProvider:
    provider_key = "session_presence"

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == SurfaceKind.SESSION_PRESENCE

    def expand(self, definition: SurfaceDefinition, tool_key: str, project_root: Path) -> list[SurfaceInstance]:
        # Get the writer for this tool key
        # Ask it for the list of paths it manages
        # Return SurfaceInstance for each
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

### T021 -- Extend `status.py` and `findings.py` for session-presence kind

**Purpose**: Add session-presence finding generation to the status service.

**Out-of-map edit to `status.py`** (owned by WP03):
- Extend `compute_findings` to handle `SurfaceKind.SESSION_PRESENCE`
- Use `TOOL_SURFACE_SESSION_PRESENCE_MISSING` finding code

**Out-of-map edit to `findings.py`** (owned by WP03):
- `TOOL_SURFACE_SESSION_PRESENCE_MISSING` is already defined as placeholder -- verify it is there, document that this WP activates it

**Rationale for out-of-map**: WP04 is sequential after WP03; no parallel conflict. Session-presence kind must be handled alongside command-skill kind in the same `compute_findings` dispatch.

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind session-presence --json` returns session-presence findings
- [ ] Migration compat tests still pass

---

### T022 -- Extend repair service for session-presence findings

**Purpose**: Add session-presence repair dispatch to `repair.py`.

**Out-of-map edit to `repair.py`** (owned by WP03):
- Add a case for `SurfaceKind.SESSION_PRESENCE` that delegates to `SessionPresenceProvider.repair()`

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind session-presence --fix` repairs missing session presence files
- [ ] Does not affect command-skill repair behavior

---

### T023 -- Write tests for session-presence provider

**Purpose**: Cover `SessionPresenceProvider` and `NativeConfigProvider` with unit tests and integration.

**Tests**:
```python
# test_session_presence.py
def test_session_presence_provider_can_handle_correct_kind():
    definition = SurfaceDefinition(kind=SurfaceKind.SESSION_PRESENCE, ...)
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

- [ ] `spec-kitty doctor tool-surfaces --kind session-presence --json` returns valid output
- [ ] Session presence surfaces appear as `surface_kind: "session_presence"` (not `"command_skill"`)
- [ ] `spec-kitty doctor tool-surfaces --kind session-presence --fix` repairs missing files
- [ ] `pytest tests/specify_cli/tool_surface/providers/test_session_presence.py` passes
- [ ] WP02 migration compat tests pass
- [ ] `mypy --strict src/specify_cli/tool_surface/` passes

## Risks

- **Per-tool path variability**: Session presence paths vary significantly per harness. Provider must not assume fixed paths -- must query the writer.
- **Null writers**: Some harnesses have null writers (no session presence). These should produce a `RESEARCH_GAP` finding, not a hard failure.

## Reviewer Guidance (Codex)

- Verify session presence is distinct from command skills in output (`surface_kind: "session_presence"`)
- Verify null writers produce `RESEARCH_GAP` (not `error`)
- Verify provider delegates to writer registry, not hardcoded paths
