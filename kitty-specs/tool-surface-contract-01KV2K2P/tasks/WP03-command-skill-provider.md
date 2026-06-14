---
work_package_id: WP03
title: Command-Skill Provider and doctor tool-surfaces
dependencies:
- WP01
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-010
- NFR-001
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
agent: claude
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/
create_intent:
- src/specify_cli/tool_surface/providers/command_skills.py
- src/specify_cli/tool_surface/plan.py
- src/specify_cli/tool_surface/status.py
- src/specify_cli/tool_surface/findings.py
- src/specify_cli/tool_surface/repair.py
- tests/specify_cli/tool_surface/test_plan.py
- tests/specify_cli/tool_surface/test_status.py
- tests/specify_cli/tool_surface/test_findings.py
- tests/specify_cli/tool_surface/test_repair.py
- tests/specify_cli/tool_surface/providers/test_command_skills.py
- tests/specify_cli/tool_surface/integration/test_doctor_tool_surfaces_cli.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/providers/command_skills.py
- src/specify_cli/tool_surface/plan.py
- src/specify_cli/tool_surface/status.py
- src/specify_cli/tool_surface/findings.py
- src/specify_cli/tool_surface/repair.py
- src/specify_cli/cli/commands/doctor.py
- tests/specify_cli/tool_surface/test_plan.py
- tests/specify_cli/tool_surface/test_status.py
- tests/specify_cli/tool_surface/test_findings.py
- tests/specify_cli/tool_surface/test_repair.py
- tests/specify_cli/tool_surface/providers/test_command_skills.py
- tests/specify_cli/tool_surface/integration/test_doctor_tool_surfaces_cli.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Route command-skill status through the provider model and add the first functional umbrella doctor command: `spec-kitty doctor tool-surfaces`. This is the first user-visible output of the ToolSurfaceContract registry.

**Critical**: Finding codes established in this WP are public API from day one. Use `TOOL_SURFACE_COMMAND_SKILL_*` prefix. They cannot be renamed without a deprecation cycle.

**Child issue**: #1937
**Parent epic**: #1945

## Context

The existing `specify_cli.skills.command_installer` module handles command skill installation and hash-checking. This WP wraps it as a `CommandSkillsProvider` -- a `SurfaceProvider` that delegates to the existing installer for actual file operations but exposes the surface contract interface.

The `doctor tool-surfaces` command with `--kind command-skill` must produce output conforming to `contracts/doctor-tool-surfaces-output.schema.json`.

**WP02 migration compat tests must still pass after this WP merges.**

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Command: `spec-kitty agent action implement WP03 --agent claude`

## Subtask Details

### T012 -- Implement `providers/command_skills.py`

**Purpose**: Wrap `specify_cli.skills.command_installer` as a `SurfaceProvider`.

**Key design points**:
- Import `CommandInstaller` (or equivalent) from `specify_cli.skills.command_installer`
- Do NOT copy its logic -- delegate to it
- Implement `expand()` by asking the installer what skills would be installed for a given tool key
- Implement `probe()` by checking existence and hash of each skill file
- Implement `repair()` by calling the installer's install/repair method
- Implement `remove()` by calling the installer's remove/uninstall method

```python
class CommandSkillsProvider:
    provider_key = "command_skills"

    def __init__(self, installer: CommandInstaller) -> None:
        self._installer = installer

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == SurfaceKind.COMMAND_SKILL

    def expand(self, definition: SurfaceDefinition, tool_key: str, project_root: Path) -> list[SurfaceInstance]:
        # Ask installer for the list of skills for this tool
        # Return SurfaceInstance for each
        ...

    def probe(self, instance: SurfaceInstance) -> SurfaceInstance:
        # Re-check exists + hash
        ...

    def repair(self, instance: SurfaceInstance) -> bool:
        # Delegate to installer
        ...

    def remove(self, instance: SurfaceInstance) -> bool:
        # Delegate to installer
        ...
```

**Files**: `src/specify_cli/tool_surface/providers/command_skills.py` (new, ~80 lines)

**Validation**:
- [ ] `isinstance(CommandSkillsProvider(), AbstractSurfaceProvider)` is True (runtime_checkable)
- [ ] `mypy --strict` passes
- [ ] Shared-root safety logic in the underlying installer is NOT bypassed

---

### T013 -- Implement `plan.py` `SurfacePlanBuilder`

**Purpose**: Given the configured tools (from `.kittify/config.yaml`) and the registry, compute the `SurfacePlan` for each tool.

```python
class SurfacePlanBuilder:
    def __init__(self, registry: ToolSurfaceRegistry, providers: list[AbstractSurfaceProvider]) -> None: ...

    def build(
        self,
        configured_tool_keys: list[str],
        project_root: Path,
        surface_kind_filter: SurfaceKind | None = None,
    ) -> list[SurfacePlan]: ...
```

The builder:
1. For each configured tool key, gets definitions from the registry
2. For each definition, finds the provider that can handle it (`provider.can_handle(definition)`)
3. Calls `provider.expand(definition, tool_key, project_root)` to get instances
4. Packages into a `SurfacePlan`

**Files**: `src/specify_cli/tool_surface/plan.py` (new, ~70 lines)

**Validation**:
- [ ] Building a plan for a tool with no definitions returns an empty `SurfacePlan`
- [ ] `surface_kind_filter=SurfaceKind.COMMAND_SKILL` filters to only command skill instances
- [ ] Cyclomatic complexity <= 15 (Sonar gate)

---

### T014 -- Implement `status.py` `SurfaceStatusService`

**Purpose**: Given a `SurfacePlan`, probe each instance and compute findings.

```python
class SurfaceStatusService:
    def __init__(self, providers: list[AbstractSurfaceProvider]) -> None: ...

    def compute_findings(self, plan: SurfacePlan) -> list[SurfaceFinding]:
        """Probe each instance in the plan and return findings for gaps."""
        ...
```

For each instance in the plan:
1. Call `provider.probe(instance)` to get current state
2. If `instance.exists` is False and `required_policy` is `REPAIRABLE_REQUIRED`: emit `TOOL_SURFACE_COMMAND_SKILL_MISSING`
3. If `instance.exists` is True but hash mismatches: emit `TOOL_SURFACE_COMMAND_SKILL_HASH_MISMATCH`
4. If `required_policy` is `RESEARCH_GAP`: emit `TOOL_SURFACE_AGENT_PROFILE_RESEARCH_GAP` (for future kinds)

**Note**: `status.py` is owned by this WP. WP04-WP09 extend it (as out-of-map edits) to handle new surface kinds.

**Files**: `src/specify_cli/tool_surface/status.py` (new, ~80 lines)

**Validation**:
- [ ] `compute_findings` returns empty list when all instances exist and hashes match
- [ ] Missing instance emits correct finding with `repair_command` populated
- [ ] `mypy --strict` passes

---

### T015 -- Implement `findings.py` with stable finding code constants

**Purpose**: Define all finding codes as string constants. These are the public API.

```python
# Stable finding codes -- never renamed without deprecation cycle

# Command skills
TOOL_SURFACE_COMMAND_SKILL_MISSING = "TOOL_SURFACE_COMMAND_SKILL_MISSING"
TOOL_SURFACE_COMMAND_SKILL_HASH_MISMATCH = "TOOL_SURFACE_COMMAND_SKILL_HASH_MISMATCH"

# Session presence (placeholder -- populated in WP04)
TOOL_SURFACE_SESSION_PRESENCE_MISSING = "TOOL_SURFACE_SESSION_PRESENCE_MISSING"

# Doctrine skills (placeholder -- populated in WP05)
TOOL_SURFACE_DOCTRINE_SKILL_MISSING = "TOOL_SURFACE_DOCTRINE_SKILL_MISSING"

# Agent profiles (placeholder -- populated in WP06)
TOOL_SURFACE_AGENT_PROFILE_MISSING = "TOOL_SURFACE_AGENT_PROFILE_MISSING"
TOOL_SURFACE_AGENT_PROFILE_RESEARCH_GAP = "TOOL_SURFACE_AGENT_PROFILE_RESEARCH_GAP"

# Plugin bundles (placeholder -- populated in WP09)
TOOL_SURFACE_PLUGIN_BUNDLE_INCOMPLETE = "TOOL_SURFACE_PLUGIN_BUNDLE_INCOMPLETE"

# Docs
TOOL_SURFACE_DOCS_PATH_DRIFT = "TOOL_SURFACE_DOCS_PATH_DRIFT"

def make_finding(
    code: str,
    tool_key: str,
    surface_kind: SurfaceKind,
    severity: str,
    path: Path | None,
    repair_command: str | None,
    detail: str,
) -> SurfaceFinding:
    """Factory function for creating SurfaceFinding objects."""
    return SurfaceFinding(
        code=code,
        tool_key=tool_key,
        surface_kind=surface_kind,
        severity=severity,
        path=path,
        repair_command=repair_command,
        detail=detail,
    )
```

**Files**: `src/specify_cli/tool_surface/findings.py` (new, ~60 lines)

**Note**: Define all anticipated codes now as placeholders. This prevents future WPs from accidentally choosing conflicting names.

**Validation**:
- [ ] All codes are string constants (not an Enum -- they must be stable JSON strings)
- [ ] `mypy --strict` passes

---

### T016 -- Implement `repair.py` `SurfaceRepairService`

**Purpose**: Given a `SurfaceFinding`, execute the repair.

```python
class SurfaceRepairService:
    def __init__(self, providers: list[AbstractSurfaceProvider]) -> None: ...

    def repair(self, finding: SurfaceFinding, project_root: Path) -> bool:
        """Attempt to repair the finding. Returns True on success."""
        ...
```

The service:
1. Finds the provider that can handle `finding.surface_kind`
2. Reconstructs the `SurfaceInstance` from the finding
3. Calls `provider.repair(instance)`
4. Returns success/failure

**Files**: `src/specify_cli/tool_surface/repair.py` (new, ~50 lines)

**Validation**:
- [ ] Returns `False` if no provider can handle the surface kind (does not raise)
- [ ] Delegates to provider; does not reimplement installer logic

---

### T017 -- Add `doctor tool-surfaces` subcommand to `cli/commands/doctor.py`

**Purpose**: Add `spec-kitty doctor tool-surfaces [--kind KIND] [--tool TOOL] [--json] [--fix]` as a new subcommand.

**Important**: `cli/commands/doctor.py` may already have other doctor subcommands. Add the new subcommand without modifying existing subcommands. Check Sonar complexity ceiling (<=15) for any modified functions -- extract a helper if needed.

**Command interface**:
```bash
spec-kitty doctor tool-surfaces --json
spec-kitty doctor tool-surfaces --kind command-skill --json
spec-kitty doctor tool-surfaces --tool codex --json
spec-kitty doctor tool-surfaces --fix
spec-kitty doctor tool-surfaces --kind command-skill --fix
```

**JSON output** must conform to `kitty-specs/tool-surface-contract-01KV2K2P/contracts/doctor-tool-surfaces-output.schema.json`.

**Implementation**:
1. Load configured tool keys from `.kittify/config.yaml`
2. Build registry with command-skill provider (the only one available at this WP)
3. Build `SurfacePlan` via `SurfacePlanBuilder`
4. Compute findings via `SurfaceStatusService`
5. If `--fix`: run `SurfaceRepairService` for each finding
6. Output JSON (or human-readable if `--json` not passed)

**Files**: `src/specify_cli/cli/commands/doctor.py` (MODIFIED -- add subcommand, do not remove existing logic)

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --json` runs without error even if no tools are configured
- [ ] `--kind command-skill` filters correctly
- [ ] `--json` output validates against the schema
- [ ] Existing `spec-kitty doctor` subcommands are unaffected

---

### T018 -- Write integration tests for `doctor tool-surfaces --kind command-skill`

**Purpose**: Cover the full CLI path with subprocess integration tests.

**Tests**:
```python
def test_doctor_tool_surfaces_json_schema():
    """--json output matches the contract schema."""
    ...

def test_doctor_tool_surfaces_kind_filter():
    """--kind command-skill returns only command-skill findings."""
    ...

def test_doctor_tool_surfaces_clean_when_installed():
    """Reports clean=true when all command skills are installed."""
    ...

def test_doctor_tool_surfaces_finding_when_missing():
    """Reports TOOL_SURFACE_COMMAND_SKILL_MISSING when skills absent."""
    ...

def test_migration_compat_still_passes():
    """doctor skills --json schema unchanged (re-run compat assertion)."""
    ...
```

**Files**: `tests/specify_cli/tool_surface/integration/test_doctor_tool_surfaces_cli.py` (new, ~120 lines)

**Also write unit tests**:
- `tests/specify_cli/tool_surface/test_plan.py` (~60 lines)
- `tests/specify_cli/tool_surface/test_status.py` (~80 lines)
- `tests/specify_cli/tool_surface/test_findings.py` (~40 lines)
- `tests/specify_cli/tool_surface/test_repair.py` (~50 lines)
- `tests/specify_cli/tool_surface/providers/test_command_skills.py` (~80 lines)

**Validation**:
- [ ] All integration tests pass
- [ ] WP02 migration compat tests still pass
- [ ] `pytest tests/specify_cli/tool_surface/` passes

## Definition of Done

- [ ] `spec-kitty doctor tool-surfaces --json` runs and produces schema-valid output
- [ ] `spec-kitty doctor tool-surfaces --kind command-skill --fix` repairs missing skills
- [ ] `pytest tests/specify_cli/tool_surface/integration/test_migration_compat.py` still passes
- [ ] `pytest tests/specify_cli/tool_surface/` passes
- [ ] `mypy --strict src/specify_cli/tool_surface/` passes
- [ ] `ruff check src/specify_cli/tool_surface/` passes (complexity <= 15)
- [ ] Finding codes use `TOOL_SURFACE_COMMAND_SKILL_*` prefix

## Risks

- **Complexity ceiling**: `SurfacePlanBuilder` and the doctor subcommand handler are the most likely functions to exceed complexity 15. Extract helpers proactively.
- **`doctor.py` god-module**: Do not add new logic to the top-level module body; add a subcommand function and keep it thin.
- **Finding code stability**: The codes introduced here are permanent. Consult the architecture gist before finalizing names.

## Reviewer Guidance (Codex)

- Verify `doctor skills --json` schema is unchanged (migration compat)
- Verify finding codes use stable `TOOL_SURFACE_*` prefix
- Verify `CommandSkillsProvider` delegates to the installer and does not reimplement hash logic
- Verify CLI output validates against `doctor-tool-surfaces-output.schema.json`
