---
work_package_id: WP09
title: Plugin Bundle Projection and Validation
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- FR-015
- FR-016
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
subtasks:
- T043
- T044
- T045
- T046
- T047
- T048
agent: "claude:opus:reviewer:reviewer"
shell_pid: "55569"
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/tool_surface/bundles/
create_intent:
- src/specify_cli/tool_surface/bundles/__init__.py
- src/specify_cli/tool_surface/bundles/model.py
- src/specify_cli/tool_surface/bundles/claude.py
- src/specify_cli/tool_surface/bundles/copilot.py
- src/specify_cli/tool_surface/bundles/vscode.py
- src/specify_cli/tool_surface/providers/plugin_bundle.py
- tests/specify_cli/tool_surface/bundles/__init__.py
- tests/specify_cli/tool_surface/bundles/test_model.py
- tests/specify_cli/tool_surface/bundles/test_claude.py
- tests/specify_cli/tool_surface/bundles/test_copilot.py
- tests/specify_cli/tool_surface/providers/test_plugin_bundle.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/bundles/__init__.py
- src/specify_cli/tool_surface/bundles/model.py
- src/specify_cli/tool_surface/bundles/claude.py
- src/specify_cli/tool_surface/bundles/copilot.py
- src/specify_cli/tool_surface/bundles/vscode.py
- src/specify_cli/tool_surface/providers/plugin_bundle.py
- tests/specify_cli/tool_surface/bundles/__init__.py
- tests/specify_cli/tool_surface/bundles/test_model.py
- tests/specify_cli/tool_surface/bundles/test_claude.py
- tests/specify_cli/tool_surface/bundles/test_copilot.py
- tests/specify_cli/tool_surface/providers/test_plugin_bundle.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load implementer-ivan
```

## Objective

Implement plugin bundle projection and pre-publish validation as a release/staging capability. This WP projects all canonical tool surfaces into plugin package layouts for Claude Code, Copilot CLI, and VS Code distribution targets, and validates that the resulting bundles are complete before publication.

**Hard scope limit** (FR-015, C-006): No auto-install, no marketplace push, no project-local installation replacement. This is purely projection + validation for release pipelines.

**Out-of-map edits required**: Extends `status.py` and `findings.py` (owned by WP03) for `SurfaceKind.PLUGIN_MANIFEST`. Rationale: "WP09 sequential after WP06; no parallel conflict."

**Plugin bundle payload (per architecture)**:
- Plugin manifest (`plugin.json` or `.claude-plugin/plugin.json`)
- Command skills (`skills/<name>/SKILL.md`)
- Agent profiles (`agents/<profile-id>.md` or `agents/<profile-id>.agent.md`)
- Hooks (`hooks.json` or `hooks/hooks.json` depending on target)
- MCP config (`.mcp.json`)

**NOT in plugin bundle**: session-presence files (CLAUDE.md, AGENTS.md, rules/steering files). Those are project install surfaces, not plugin bundle components.

**Supported initial targets**:
- Claude Code plugin format (`.claude-plugin/plugin.json`, skills, agents, hooks, .mcp.json)
- Copilot CLI / VS Code plugin format (root `plugin.json`, agents, skills, hooks.json, .mcp.json)

**Child issue**: #1943
**Parent epic**: #1945

## Context

Plugin bundles group tool surfaces for distribution. When Spec Kitty ships as a Claude Code plugin, the plugin bundle must include:
- All command skills
- All doctrine skills
- Native agent profile projections
- Plugin manifest
- Hooks and MCP config

Session-presence files (CLAUDE.md, AGENTS.md, rules files) are NOT included in the plugin bundle — they are project install surfaces.

The `PluginBundleBuilder` projects the canonical `SurfacePlan` into the appropriate package layout for each distribution target. The `BundleValidator` checks that the resulting bundle is complete before it is published.

This is a staging/release tool, not a user-facing daily workflow.

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Command: `spec-kitty agent action implement WP09 --agent claude`

## Subtask Details

### T043 -- Implement `bundles/model.py`

**Purpose**: Define the data model for plugin bundles and validation results.

```python
@dataclass(frozen=True)
class BundleEntry:
    """One surface included in a plugin bundle."""
    surface_kind: SurfaceKind
    source_path: Path           # where the surface lives in the project
    bundle_relative_path: str   # where it goes inside the bundle package

@dataclass(frozen=True)
class PluginBundle:
    distribution_target: str    # "claude_code_plugin" | "copilot_skill_package" | "vscode_extension"
    entries: tuple[BundleEntry, ...]
    manifest_path: Path | None  # path to the bundle's own manifest file (if any)

@dataclass(frozen=True)
class BundleValidationResult:
    passed: bool
    missing_surfaces: tuple[SurfaceFinding, ...]
    warnings: tuple[str, ...]
    distribution_target: str
```

**Files**: `src/specify_cli/tool_surface/bundles/__init__.py` (new, empty), `src/specify_cli/tool_surface/bundles/model.py` (new, ~60 lines)

**Validation**:
- [ ] All dataclasses are `frozen=True`
- [ ] `mypy --strict` passes

---

### T044 -- Implement `bundles/claude.py` Claude Code plugin bundle projection

**Purpose**: Project all canonical surfaces into Claude Code's plugin bundle layout.

Claude Code plugin bundle layout (`.claude-plugin/`):
```
.claude-plugin/
├── plugin.json           # Plugin manifest
├── skills/               # Command skills
│   ├── spec-kitty.plan/SKILL.md
│   ├── spec-kitty.specify/SKILL.md
│   └── ...
├── agents/               # Native agent profile projections
│   ├── architect-alphonso.md
│   └── ...
├── hooks/
│   └── hooks.json        # Hook config (NOT settings.json)
└── .mcp.json             # MCP config (NOT settings.json)
```

```python
class ClaudeCodeBundleProjector:
    distribution_target = "claude_code_plugin"

    def project(
        self,
        plan: list[SurfacePlan],
        project_root: Path,
        output_dir: Path,
    ) -> PluginBundle:
        """Project all surfaces into Claude Code plugin layout under output_dir."""
        ...

    def validate(self, bundle: PluginBundle, required_surface_kinds: set[SurfaceKind]) -> BundleValidationResult:
        """Validate that all required surface kinds are present in the bundle."""
        ...
```

**Files**: `src/specify_cli/tool_surface/bundles/claude.py` (new, ~100 lines)

**Validation**:
- [ ] `project()` creates the correct directory structure
- [ ] `validate()` returns `passed=False` if command skills are missing from bundle
- [ ] `plugin.json` is created with required fields (consult Claude Code plugin manifest docs)
- [ ] `mypy --strict` passes

---

### T045 -- Implement `bundles/copilot.py` and `bundles/vscode.py`

**Purpose**: Projectors for GitHub Copilot CLI and VS Code bundle targets. Both are confirmed supported targets with known layouts.

**Copilot CLI / VS Code plugin bundle layout** (root `plugin.json` format):
```
<output-dir>/
├── plugin.json           # Plugin manifest (root-level for Copilot/VS Code)
├── skills/               # Command skills
│   └── spec-kitty.plan/SKILL.md
├── agents/               # Native agent profile projections (.agent.md format)
│   ├── architect-alphonso.agent.md
│   └── ...
├── hooks.json            # Hook config
└── .mcp.json             # MCP config
```

```python
class CopilotBundleProjector:
    distribution_target = "copilot_skill_package"

    def project(
        self,
        plan: list[SurfacePlan],
        project_root: Path,
        output_dir: Path,
    ) -> PluginBundle: ...

    def validate(self, bundle: PluginBundle, required_surface_kinds: set[SurfaceKind]) -> BundleValidationResult: ...
```

The VS Code projector (`VsCodeBundleProjector`) uses the same layout as Copilot — both use `plugin.json` at root and `.agent.md` files in `agents/`.

**Files**:
- `src/specify_cli/tool_surface/bundles/copilot.py` (new, ~80 lines)
- `src/specify_cli/tool_surface/bundles/vscode.py` (new, ~40 lines — delegates to CopilotBundleProjector with `vscode_extension` target key)

**Validation**:
- [ ] `CopilotBundleProjector.project()` creates the correct directory structure
- [ ] `validate()` returns `passed=False` if skills or agent profiles are missing
- [ ] `plugin.json` is created at output root (not in a subdirectory)
- [ ] Copilot and VS Code projector files exist, are importable, and implement projection rather than stubs

---

### T046 -- Implement `providers/plugin_bundle.py`

**Purpose**: Wire the bundle projectors as a `SurfaceProvider`.

```python
class PluginBundleProvider:
    provider_key = "plugin_bundle"

    def __init__(
        self,
        projectors: list[ClaudeCodeBundleProjector | ...],
        output_dir: Path,
    ) -> None: ...

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == SurfaceKind.PLUGIN_MANIFEST

    def expand(self, definition: SurfaceDefinition, tool_key: str, project_root: Path) -> list[SurfaceInstance]:
        # Returns instances for the bundle's entry points (manifest files)
        ...

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        # Check if the bundle output dir and manifest exist; return SurfaceStatus
        ...

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        # Re-project bundles for the supplied statuses
        ...
```

**Files**: `src/specify_cli/tool_surface/providers/plugin_bundle.py` (new, ~80 lines)

**Validation**:
- [ ] `isinstance(PluginBundleProvider(...), AbstractSurfaceProvider)` is True
- [ ] `mypy --strict` passes

---

### T047 -- Extend `status.py` and `findings.py` for plugin-bundle kind

**Out-of-map edit to `status.py`** (owned by WP03):
- Handle `SurfaceKind.PLUGIN_MANIFEST`: incomplete bundle → code `"bundle-component-missing"`, severity `"error"`; stale path → `"plugin-manifest-stale-path"`, severity `"warning"`

**Out-of-map edit to `findings.py`** (owned by WP03):
- Activate `BUNDLE_COMPONENT_MISSING = "bundle-component-missing"` and `PLUGIN_MANIFEST_STALE_PATH = "plugin-manifest-stale-path"` (kebab-case string values; Python constant names are SCREAMING_SNAKE)

**Rationale**: Sequential after WP06; no parallel conflict.

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind plugin-manifest --json` works
- [ ] Incomplete bundle produces finding with code `"bundle-component-missing"`, severity `"error"`

---

### T048 -- Write tests for plugin bundle validation

**Tests**:
```python
# test_model.py
def test_bundle_validation_result_passed():
    ...

def test_bundle_validation_result_failed_with_missing():
    ...

# test_claude.py
def test_claude_code_bundle_layout_is_correct():
    """project() creates .claude-plugin/ with expected structure."""
    ...

def test_claude_code_bundle_validate_fails_when_skills_missing():
    ...

def test_claude_code_bundle_plugin_json_exists():
    ...

# test_plugin_bundle.py
def test_plugin_bundle_provider_copilot_projects_correctly():
    """Copilot bundle projection produces plugin.json at root."""
    ...

def test_plugin_bundle_provider_probe_detects_missing_bundle():
    ...
```

**Files**:
- `tests/specify_cli/tool_surface/bundles/__init__.py` (new, empty)
- `tests/specify_cli/tool_surface/bundles/test_model.py` (new, ~50 lines)
- `tests/specify_cli/tool_surface/bundles/test_claude.py` (new, ~80 lines)
- `tests/specify_cli/tool_surface/providers/test_plugin_bundle.py` (new, ~70 lines)

**Validation**:
- [ ] All tests pass
- [ ] WP02 migration compat tests still pass
- [ ] `pytest tests/specify_cli/tool_surface/` passes

## Definition of Done

- [ ] `ClaudeCodeBundleProjector.project()` produces the correct `.claude-plugin/` layout (including `hooks/hooks.json` and `.mcp.json`, not `settings.json`)
- [ ] `ClaudeCodeBundleProjector.validate()` catches incomplete bundles (missing command skills, doctrine skills, or agent profiles)
- [ ] `CopilotBundleProjector.project()` produces the correct root-`plugin.json` layout with `hooks.json` and `.mcp.json`
- [ ] `VSCodeBundleProjector.project()` produces a valid VS Code bundle layout
- [ ] `spec-kitty doctor tool-surfaces --kind plugin-manifest --json` works
- [ ] `pytest tests/specify_cli/tool_surface/bundles/` passes
- [ ] `mypy --strict src/specify_cli/tool_surface/bundles/` passes
- [ ] No auto-install, marketplace push, or project-local installation logic

## Risks

- **Claude Code plugin manifest format**: The `plugin.json` format may change. Keep the manifest generation isolated and versioned in the projector.
- **Bundle output dir**: The bundle output directory is a staging artifact (e.g., `dist/claude-plugin/`). It must not be placed in `.kittify/` or any project-managed directory.

## Reviewer Guidance (Codex)

- Verify no auto-install or marketplace push logic anywhere in this WP
- Verify Claude Code bundle layout: `hooks/hooks.json` for hooks, `.mcp.json` for MCP — NOT `settings.json`
- Verify Copilot/VS Code bundle layout: root `plugin.json`, `hooks.json` at root, `.mcp.json` at root
- Verify all three projectors (Claude, Copilot, VS Code) are implemented — no `NotImplementedError` stubs in this WP
- Verify Claude Code bundle includes all required surface kinds (command skills, doctrine skills, agent profiles)
- Verify `PluginBundleProvider` delegates to projectors (not reimplements projection)
- Verify finding codes are kebab-case in JSON output (`"bundle-component-missing"`, not `TOOL_SURFACE_PLUGIN_BUNDLE_INCOMPLETE`)

## Activity Log

- 2026-06-14T11:34:45Z – user – Moved to planned
- 2026-06-14T11:34:47Z – claude:opus:implementer:implementer – shell_pid=48513 – Started implementation via action command
- 2026-06-14T11:53:44Z – claude:opus:implementer:implementer – shell_pid=48513 – Ready for review: WP09 plugin bundle projection + validation (Claude/Copilot/VSCode projectors, PluginBundleProvider wired into doctor tool-surfaces via build_providers/build_registry + plugin-manifest --kind token). Live wiring confirmed: doctor tool-surfaces --kind plugin-manifest --json surfaces 3 manifests (one per target). Diff-scoped ruff check exit 0; mypy (config) exit 0; full tool_surface suite 207 passed (was 177, +30). FR-016/C-006 negative-assertion test added (AST scan + behavioural guards) and proven to fail on injected publish logic. --force used only for the documented base-ref preflight false-positive (lane base is kitty/mission-tool-surface-contract-01KV2K2P); tree clean, commit present.
- 2026-06-14T11:54:22Z – claude:opus:reviewer:reviewer – shell_pid=55569 – Started review via action command
- 2026-06-14T12:00:40Z – user – shell_pid=55569 – Review passed (arbiter override of stale review-cycle-1.md = dependency-lane auto-merge re-dispatch note, affected_files:[], reviewer_agent:unknown, NOT a code defect; --force for documented base-ref preflight false-positive: real lane base is kitty/mission-tool-surface-contract-01KV2K2P, tree clean, WP09 commit 11b0aa67e present). FR-016/C-006 prohibition guard reproduced: injected marketplace_publish -> AST-scan + behavioural staging-only tests both FAILED; reverted -> green. Live no-stub doctor --kind plugin-manifest --json surfaces 3 targets all missing ok=true OPTIONAL. Default --fix succeeds, writes confined to dist/spec-kitty-plugins/ staging only (no live agent dir, no network). 7-provider union intact + plugin-manifest tokens added; prior providers untouched. Schema conformant. ruff/mypy(config) clean; 207 passed.
