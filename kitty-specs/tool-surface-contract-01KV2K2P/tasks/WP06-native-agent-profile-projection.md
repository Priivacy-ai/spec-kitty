---
work_package_id: WP06
title: Native Agent Profile Projection
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-012
- FR-013
- FR-014
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
- T033
agent: claude
shell_pid: '30035'
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/tool_surface/profiles/
create_intent:
- src/specify_cli/tool_surface/profiles/__init__.py
- src/specify_cli/tool_surface/profiles/projection.py
- src/specify_cli/tool_surface/profiles/renderers.py
- src/specify_cli/tool_surface/profiles/manifest.py
- src/specify_cli/tool_surface/providers/agent_profiles.py
- tests/specify_cli/tool_surface/profiles/__init__.py
- tests/specify_cli/tool_surface/profiles/test_projection.py
- tests/specify_cli/tool_surface/profiles/test_renderers.py
- tests/specify_cli/tool_surface/profiles/test_manifest.py
- tests/specify_cli/tool_surface/providers/test_agent_profiles.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/profiles/__init__.py
- src/specify_cli/tool_surface/profiles/projection.py
- src/specify_cli/tool_surface/profiles/renderers.py
- src/specify_cli/tool_surface/profiles/manifest.py
- src/specify_cli/tool_surface/providers/agent_profiles.py
- tests/specify_cli/tool_surface/profiles/__init__.py
- tests/specify_cli/tool_surface/profiles/test_projection.py
- tests/specify_cli/tool_surface/profiles/test_renderers.py
- tests/specify_cli/tool_surface/profiles/test_manifest.py
- tests/specify_cli/tool_surface/providers/test_agent_profiles.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load architect-alphonso
```

## Objective

Project built-in Spec Kitty agent profiles and org/project overlay profiles into host-native agent/subagent formats. Track projected files in a manifest. Add `agent_profile` kind to `doctor tool-surfaces` output.

**Profile manifest file**: `.kittify/agent-profiles-manifest.json` (NOT `tool-surface-profile-manifest.json`)

**Out-of-map edits required**: Extends `status.py`, `findings.py` (owned by WP03) for `SurfaceKind.AGENT_PROFILE`. Rationale: "WP06 sequential; no parallel conflict."

**Key constraint (FR-014)**: Tools that do not support named agents natively must receive a finding with code `"research-gap-surface"` (or `"profile-projection-unsupported"` when the tool is known but unverified), severity `"info"`, and the top-level `ok` field must remain `true`. These are NOT error or warning findings. Never use a fictional `"research_gap"` severity value — the schema only allows `error`, `warning`, `info`.

**Child issue**: #1940
**Parent epic**: #1945

## Context

Spec Kitty has an `AgentProfileRepository` in `src/doctrine/agent_profiles/` that resolves built-in profiles (e.g., `architect-alphonso`, `researcher-robbie`, `implementer-ivan`) and org/project overlay profiles via DRG traversal. Currently these profiles are only accessible through the CLI's profile loading mechanism -- not as native agents in tool UIs.

This WP adds the "render + manifest + doctor" layer that projects profiles into host-native files so users can select them directly in their tool's agent picker.

**Important**: Do NOT modify `AgentProfileRepository` or the profile loading/scoring model. Only add the projection layer on top.

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Command: `spec-kitty agent action implement WP06 --agent claude`

## Subtask Details

### T028 -- Implement `profiles/projection.py`

**Purpose**: Load profiles from `AgentProfileRepository` and project them into the appropriate format for each configured tool.

```python
class ProfileProjector:
    """Projects Spec Kitty agent profiles into host-native agent/subagent formats."""

    def __init__(self, profile_repo: AgentProfileRepository) -> None:
        self._repo = profile_repo

    def project(
        self,
        tool_key: str,
        project_root: Path,
        source_layers: list[str] | None = None,  # None = all: builtin + org + project
    ) -> list[NativeAgentProfile]:
        """Project all available profiles into native format for the given tool.

        Returns empty list for tools that don't support named agents.
        """
        renderer = get_renderer(tool_key)
        if renderer is None:
            return []  # Tool has no native agent support

        profiles = self._repo.all_profiles(source_layers=source_layers)
        result = []
        for profile in profiles:
            output_path = renderer.output_path(tool_key, profile, project_root)
            content = renderer.render(profile)
            result.append(NativeAgentProfile(
                profile_urn=profile.urn,
                source_layer=profile.source_layer,
                tool_key=tool_key,
                output_path=output_path,
                format=renderer.format_key,
                file_hash=None,  # computed after write
            ))
        return result
```

**Files**: `src/specify_cli/tool_surface/profiles/projection.py` (new, ~80 lines)

**Validation**:
- [ ] `project("claude", ...)` returns at least the built-in profiles
- [ ] `project("unknown_tool_key", ...)` returns empty list (no error)
- [ ] Does not modify `AgentProfileRepository`

---

### T029 -- Implement `profiles/renderers.py`

**Purpose**: Per-harness render functions that convert a Spec Kitty profile into the tool's native agent file format.

**Renderers to implement** (confirmed active targets; Codex is the only research gap):

**Claude Code project/user**: `.claude/agents/<profile-id>.md` (`claude-agent` format — Markdown frontmatter + body)
**Claude plugin bundle**: `agents/<profile-id>.md` (`claude-plugin-agent` format)
**Copilot CLI / VS Code**: `.github/agents/<profile-id>.agent.md` (`copilot-agent` / `vscode-agent` format — `.agent.md` frontmatter + instructions)
**Codex**: No verified native profile primitive → `research-gap-surface` finding. Do NOT model Codex AGENTS.md hints as native profiles — AGENTS.md is a `context_file` surface (session presence), not a profile projection.

```python
class ProfileRenderer(Protocol):
    format_key: str

    def can_render(self, tool_key: str) -> bool: ...
    def output_path(self, tool_key: str, profile: AgentProfile, project_root: Path) -> Path: ...
    def render(self, profile: AgentProfile) -> str: ...

class ClaudeCodeProfileRenderer:
    format_key = "claude-agent"

    def can_render(self, tool_key: str) -> bool:
        return tool_key == "claude"

    def output_path(self, tool_key: str, profile: AgentProfile, project_root: Path) -> Path:
        return project_root / ".claude" / "agents" / f"{profile.slug}.md"

    def render(self, profile: AgentProfile) -> str:
        # Generate the YAML frontmatter + content format
        ...

class CopilotProfileRenderer:
    format_key = "copilot-agent"

    def can_render(self, tool_key: str) -> bool:
        return tool_key in ("copilot", "vscode")

    def output_path(self, tool_key: str, profile: AgentProfile, project_root: Path) -> Path:
        return project_root / ".github" / "agents" / f"{profile.slug}.agent.md"

    def render(self, profile: AgentProfile) -> str:
        # Generate the .agent.md frontmatter + instructions format
        ...

def get_renderer(tool_key: str) -> ProfileRenderer | None:
    """Return the renderer for a tool key, or None if unsupported (yields research-gap-surface)."""
    ...
```

**Files**: `src/specify_cli/tool_surface/profiles/renderers.py` (new, ~140 lines)

**Validation**:
- [ ] `ClaudeCodeProfileRenderer` produces valid `.md` with YAML frontmatter (`claude-agent` format)
- [ ] `CopilotProfileRenderer` produces valid `.agent.md` files (`copilot-agent` format)
- [ ] `get_renderer("codex")` returns `None` (yields research-gap-surface)
- [ ] `get_renderer("unknown")` returns `None` (no error)
- [ ] `mypy --strict` passes

---

### T030 -- Implement `profiles/manifest.py`

**Purpose**: Track projected native agent profile files with hashes and owners (same pattern as command-skills manifest).

```python
class ProfileManifest:
    """Tracks installed native agent profile files.

    Stored at: .kittify/agent-profiles-manifest.json
    """
    manifest_path: Path

    def record(self, profile: NativeAgentProfile) -> None: ...
    def get_hash(self, output_path: Path) -> str | None: ...
    def all_entries(self) -> list[NativeAgentProfile]: ...
    def remove(self, output_path: Path) -> None: ...
```

**Files**: `src/specify_cli/tool_surface/profiles/manifest.py` (new, ~70 lines)

**Validation**:
- [ ] Manifest is stored at `.kittify/agent-profiles-manifest.json` (NOT `tool-surface-profile-manifest.json`)
- [ ] Hash is SHA-256 of file content
- [ ] Manifest survives round-trip (write → read → same data)

---

### T031 -- Implement `providers/agent_profiles.py`

**Purpose**: Wire the projection + manifest into a `SurfaceProvider`.

```python
class AgentProfilesProvider:
    provider_key = "agent_profiles"

    def __init__(self, projector: ProfileProjector, manifest: ProfileManifest) -> None: ...

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == SurfaceKind.AGENT_PROFILE

    def expand(self, definition: SurfaceDefinition, tool_key: str, project_root: Path) -> list[SurfaceInstance]:
        projected = self._projector.project(tool_key, project_root)
        # Convert NativeAgentProfile -> SurfaceInstance
        ...

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        # Check if the native file exists and hash matches manifest; return SurfaceStatus
        ...

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        # Re-project and write files for the supplied statuses; update manifest
        ...
```

**Files**: `src/specify_cli/tool_surface/providers/agent_profiles.py` (new, ~90 lines)

**Validation**:
- [ ] `isinstance(AgentProfilesProvider(...), AbstractSurfaceProvider)` is True
- [ ] `mypy --strict` passes

---

### T032 -- Extend `status.py` and `findings.py` for agent-profile kind

**Out-of-map edit to `status.py`** (owned by WP03):
- Handle `SurfaceKind.AGENT_PROFILE`: if file missing → code `"native-agent-profile-missing"`, severity `"error"`
- If `required_policy == RESEARCH_GAP` (tool has no native agent support) → code `"research-gap-surface"` or `"profile-projection-unsupported"`, severity `"info"` (NOT `"error"`, NOT `"research_gap"`)
- `ok` is `true` when the only findings have severity `"info"`; `ok` is `false` only when any finding has severity `"error"`

**Out-of-map edit to `findings.py`** (owned by WP03):
- Activate constants: `NATIVE_AGENT_PROFILE_MISSING = "native-agent-profile-missing"`, `RESEARCH_GAP_SURFACE = "research-gap-surface"`, `PROFILE_PROJECTION_UNSUPPORTED = "profile-projection-unsupported"`
- These are kebab-case string values; the Python constant names are SCREAMING_SNAKE for readability only

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind agent-profile --json` works
- [ ] Tools without native agent support: finding code is `"research-gap-surface"`, severity is `"info"`, `ok` is `true`
- [ ] `ok: true` when the only findings are `severity: "info"` (research-gap) findings
- [ ] `ok: false` only when at least one `severity: "error"` finding is present

---

### T033 -- Write tests for profile projection and provider

**Tests**:
```python
# test_projection.py
def test_project_claude_returns_builtin_profiles():
    ...

def test_project_unsupported_tool_returns_empty():
    ...

# test_renderers.py
def test_claude_code_renderer_output_path():
    profile = make_test_profile(slug="architect-alphonso")
    renderer = ClaudeCodeProfileRenderer()
    path = renderer.output_path("claude", profile, Path("/project"))
    assert path == Path("/project/.claude/agents/architect-alphonso.md")

def test_claude_code_renderer_produces_yaml_frontmatter():
    ...

def test_copilot_renderer_output_path():
    profile = make_test_profile(slug="researcher-robbie")
    renderer = CopilotProfileRenderer()
    path = renderer.output_path("copilot", profile, Path("/project"))
    assert path == Path("/project/.github/agents/researcher-robbie.agent.md")

def test_copilot_renderer_produces_agent_md_frontmatter():
    ...

def test_get_renderer_returns_none_for_codex():
    assert get_renderer("codex") is None  # Codex yields research-gap-surface

def test_get_renderer_returns_none_for_unknown_tool():
    assert get_renderer("unknown_tool") is None

# test_manifest.py
def test_manifest_roundtrip():
    ...

# test_agent_profiles.py
def test_agent_profiles_provider_research_gap_for_unsupported_tool():
    ...

def test_agent_profiles_provider_repair_writes_file():
    ...
```

**Files**:
- `tests/specify_cli/tool_surface/profiles/__init__.py` (new, empty)
- `tests/specify_cli/tool_surface/profiles/test_projection.py` (new, ~80 lines)
- `tests/specify_cli/tool_surface/profiles/test_renderers.py` (new, ~80 lines)
- `tests/specify_cli/tool_surface/profiles/test_manifest.py` (new, ~60 lines)
- `tests/specify_cli/tool_surface/providers/test_agent_profiles.py` (new, ~80 lines)

**Validation**:
- [ ] All tests pass
- [ ] WP02 migration compat tests still pass

## Definition of Done

- [ ] Built-in profiles are projected into `.claude/agents/` for configured Claude Code users
- [ ] `spec-kitty doctor tool-surfaces --kind agent-profile --json` reports gaps and repairs them
- [ ] Tools without native agent support show code `"research-gap-surface"` or `"profile-projection-unsupported"` at severity `"info"`; top-level `ok` remains `true`
- [ ] Profile manifest is written to `.kittify/agent-profiles-manifest.json` (NOT `tool-surface-profile-manifest.json`)
- [ ] `.kittify/agent-profiles-manifest.json` is the manifest used (NOT `tool-surface-profile-manifest.json`)
- [ ] `pytest tests/specify_cli/tool_surface/profiles/` passes
- [ ] `mypy --strict src/specify_cli/tool_surface/` passes

## Risks

- **Claude Code agent format**: The `.claude/agents/*.md` format may change between Claude Code versions. Keep the renderer isolated so it can be updated independently.
- **AgentProfileRepository DRG traversal**: `resolve_profile` does DRG traversal. Ensure projection only calls public API of the repository -- no internal bypasses.
- **Org overlay profiles**: These may be absent in a standard setup. `project()` should handle an empty org overlay gracefully.

## Reviewer Guidance (Codex)

- Verify research-gap/profile-unsupported findings use severity `"info"` (not `"error"` and not a fictional `"research_gap"` severity)
- Verify `ok: true` when only research-gap/profile-unsupported findings are present
- Verify `AgentProfileRepository` is not modified
- Verify glossary compliance: profiles are "agent profiles" (logical identities), not "tool surfaces" (but they have a tool surface representation)
