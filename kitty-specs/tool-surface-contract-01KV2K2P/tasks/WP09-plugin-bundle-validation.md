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
agent: claude
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

Implement plugin bundle projection and pre-publish validation as a release/staging capability. This WP projects all canonical tool surfaces into plugin package layouts for Claude Code, Copilot, and VS Code distribution targets, and validates that the resulting bundles are complete before publication.

**Hard scope limit** (FR-015, C-006): No auto-install, no marketplace push, no project-local installation replacement. This is purely projection + validation for release pipelines.

**Out-of-map edits required**: Extends `status.py` and `findings.py` (owned by WP03) for `SurfaceKind.PLUGIN_MANIFEST`. Rationale: "WP09 sequential after WP06; no parallel conflict."

**Child issue**: #1943
**Parent epic**: #1945

## Context

Plugin bundles group tool surfaces for distribution. When Spec Kitty ships as a Claude Code plugin, the plugin bundle must include:
- All command skills
- All doctrine skills
- Session presence files
- Native agent profile projections
- Plugin manifest

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
└── settings.json         # Hook and MCP config
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

**Purpose**: Stub projectors for GitHub Copilot and VS Code extension bundle targets.

For this WP, these can be stubs that:
1. Define the `distribution_target` string
2. Define the expected bundle layout (comments OK)
3. Raise `NotImplementedError` for `project()` with a clear message: "Copilot bundle projection is a RESEARCH_GAP -- contribute at <issue>"
4. Validate that the required entries are structurally correct (even if projection is not implemented)

**Files**:
- `src/specify_cli/tool_surface/bundles/copilot.py` (new, ~40 lines -- stub with `RESEARCH_GAP` note)
- `src/specify_cli/tool_surface/bundles/vscode.py` (new, ~40 lines -- stub with `RESEARCH_GAP` note)

**Validation**:
- [ ] Calling `project()` on a stub raises `NotImplementedError` (not crashes silently)
- [ ] Stub files exist and are importable

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

    def probe(self, instance: SurfaceInstance) -> SurfaceInstance:
        # Check if the bundle output dir and manifest exist
        ...

    def repair(self, instance: SurfaceInstance) -> bool:
        # Re-project the bundle
        ...
```

**Files**: `src/specify_cli/tool_surface/providers/plugin_bundle.py` (new, ~80 lines)

**Validation**:
- [ ] `isinstance(PluginBundleProvider(...), AbstractSurfaceProvider)` is True
- [ ] `mypy --strict` passes

---

### T047 -- Extend `status.py` and `findings.py` for plugin-bundle kind

**Out-of-map edit to `status.py`** (owned by WP03):
- Handle `SurfaceKind.PLUGIN_MANIFEST`: incomplete bundle → `TOOL_SURFACE_PLUGIN_BUNDLE_INCOMPLETE`

**Out-of-map edit to `findings.py`** (owned by WP03):
- Activate the placeholder constant `TOOL_SURFACE_PLUGIN_BUNDLE_INCOMPLETE`

**Rationale**: Sequential after WP06; no parallel conflict.

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind plugin-manifest --json` works
- [ ] Incomplete bundle produces `TOOL_SURFACE_PLUGIN_BUNDLE_INCOMPLETE` finding

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
def test_plugin_bundle_provider_research_gap_for_copilot():
    """Copilot bundle projection returns RESEARCH_GAP (NotImplementedError handled)."""
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

- [ ] `ClaudeCodeBundleProjector.project()` produces a correct `.claude-plugin/` layout
- [ ] `ClaudeCodeBundleProjector.validate()` catches incomplete bundles
- [ ] `spec-kitty doctor tool-surfaces --kind plugin-manifest --json` works
- [ ] Copilot and VS Code stubs are `NotImplementedError` (not silent failures)
- [ ] `pytest tests/specify_cli/tool_surface/bundles/` passes
- [ ] `mypy --strict src/specify_cli/tool_surface/bundles/` passes
- [ ] No auto-install, marketplace push, or project-local installation logic

## Risks

- **Claude Code plugin manifest format**: The `plugin.json` format may change. Keep the manifest generation isolated and versioned in the projector.
- **Bundle output dir**: The bundle output directory is a staging artifact (e.g., `dist/claude-plugin/`). It must not be placed in `.kittify/` or any project-managed directory.
- **Stub footguns**: Ensure `NotImplementedError` stubs don't silently succeed in CI. The test must explicitly verify the error is raised.

## Reviewer Guidance (Codex)

- Verify no auto-install or marketplace push logic anywhere in this WP
- Verify stub projectors raise `NotImplementedError` (not silent no-ops)
- Verify Claude Code bundle includes all required surface kinds (command skills, doctrine skills, agent profiles)
- Verify `PluginBundleProvider` delegates to projectors (not reimplements projection)
