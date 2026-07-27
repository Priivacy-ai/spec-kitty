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
- T049
agent: claude
shell_pid: '23520'
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/
create_intent:
- src/specify_cli/tool_surface/providers/command_skills.py
- src/specify_cli/tool_surface/providers/slash_commands.py
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
- src/specify_cli/tool_surface/providers/slash_commands.py
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

**Critical**: Finding codes established in this WP are public API from day one. The **JSON wire format** uses kebab-case codes (e.g. `"generated-surface-missing"`, `"managed-file-drift"`) — these are immutable once published. Python constants in `findings.py` may use `SCREAMING_SNAKE` names but MUST map to the kebab-case string values. Do not emit uppercase codes in JSON output.

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
- Implement `probe()` by checking existence and hash of each skill file, returning `SurfaceStatus`
- Implement `repair()` by calling the installer's install/repair method for the supplied `SurfaceStatus` objects
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

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        # Re-check on-disk state and return SurfaceStatus(state=..., findings=...)
        ...

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        # Delegate to installer using provider-owned status/manifest context
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

**Purpose**: Given one or more `SurfacePlan` objects, probe each instance and return a `SurfaceReport` containing both per-surface statuses and flattened findings.

```python
class SurfaceStatusService:
    def __init__(self, providers: list[AbstractSurfaceProvider]) -> None: ...

    def collect(
        self,
        project_root: Path,
        plans: Sequence[SurfacePlan],
    ) -> SurfaceReport:
        """Probe every instance and return statuses + flattened findings."""
        ...
```

For each instance in the plan:
1. Call `provider.probe(instance)` to get a `SurfaceStatus`
2. If the status is `missing` and `required == REPAIRABLE_REQUIRED`: include a `SurfaceFinding` with code `"generated-surface-missing"`
3. If the status is `drifted`: include a `SurfaceFinding` with code `"managed-file-drift"`
4. If `required == RESEARCH_GAP`: include a `SurfaceFinding` with code `"research-gap-surface"` and severity `"info"`
5. Return a `SurfaceReport` with `surfaces[]`, flattened `findings[]`, summary counts, and top-level `ok`

**Note**: `status.py` is owned by this WP. WP04-WP09 extend it (as out-of-map edits) to handle new surface kinds.

**Files**: `src/specify_cli/tool_surface/status.py` (new, ~80 lines)

**Validation**:
- [ ] `collect` returns `SurfaceReport.ok == true` when all instances are present and hashes match
- [ ] Missing instance emits `"generated-surface-missing"` with `repair_command` populated
- [ ] Report includes both `surfaces[]` and flattened `findings[]`
- [ ] `mypy --strict` passes

---

### T015 -- Implement `findings.py` with stable finding code constants

**Purpose**: Define all finding codes as string constants. These are the public API.

```python
# Stable finding codes -- never renamed without deprecation cycle
# Codes are kebab-case strings (stable JSON API)

# Command skills / command files
GENERATED_SURFACE_MISSING = "generated-surface-missing"
MANAGED_FILE_DRIFT = "managed-file-drift"
STALE_GENERATED_SURFACE = "stale-generated-surface"
UNSAFE_MANAGED_PATH = "unsafe-managed-path"
UNMANAGED_SPEC_KITTY_SURFACE = "unmanaged-spec-kitty-surface"
CONFIGURED_TOOL_SURFACE_UNINSTALLED = "configured-tool-surface-uninstalled"

# Session presence / context files (placeholder -- populated in WP04)
CONTEXT_FILE_MISSING = "context-file-missing"
SESSION_PRESENCE_INCOMPLETE = "session-presence-incomplete"
NATIVE_CONFIG_MISSING = "native-config-missing"
NATIVE_CONFIG_DRIFT = "native-config-drift"

# Agent profiles (placeholder -- populated in WP06)
NATIVE_AGENT_PROFILE_MISSING = "native-agent-profile-missing"
NATIVE_AGENT_PROFILE_DRIFT = "native-agent-profile-drift"
PROFILE_PROJECTION_UNSUPPORTED = "profile-projection-unsupported"
RESEARCH_GAP_SURFACE = "research-gap-surface"

# Plugin bundles (placeholder -- populated in WP09)
BUNDLE_COMPONENT_MISSING = "bundle-component-missing"
PLUGIN_MANIFEST_STALE_PATH = "plugin-manifest-stale-path"

# Docs (placeholder -- populated in WP08)
DOCS_REF_STALE = "docs-ref-stale"

def make_finding(
    code: str,              # kebab-case JSON wire code, e.g. "generated-surface-missing"
    severity: str,          # "error" | "warning" | "info"  (NOT "research_gap" — use "info" for gaps)
    message: str,           # human-readable explanation
    *,
    tool_key: str | None = None,
    surface_id: str | None = None,
    path: Path | None = None,
    repair_command: str | None = None,
    docs_ref: str | None = None,
    details: Mapping[str, object] | None = None,
) -> SurfaceFinding:
    """Factory function for creating SurfaceFinding objects.

    IMPORTANT: `code` must be a kebab-case string from the stable code table in data-model.md.
    Do NOT pass SCREAMING_SNAKE_CASE here — Python constants are fine as intermediates
    but the string VALUE must be kebab-case.
    """
    return SurfaceFinding(
        code=code,
        severity=severity,
        message=message,
        tool_key=tool_key,
        surface_id=surface_id,
        path=path,
        repair_command=repair_command,
        docs_ref=docs_ref,
        details=details or {},
    )
```

**Files**: `src/specify_cli/tool_surface/findings.py` (new, ~60 lines)

**Note**: Define all anticipated codes now as placeholders. This prevents future WPs from accidentally choosing conflicting names.

**Validation**:
- [ ] All codes are kebab-case string constants (not an Enum -- they must be stable JSON strings)
- [ ] No SCREAMING_SNAKE_CASE in the JSON output; constants may have SCREAMING names but their values are kebab-case
- [ ] `mypy --strict` passes

---

### T016 -- Implement `repair.py` `SurfaceRepairService`

**Purpose**: Given `SurfaceStatus` objects, execute repair.

**Repair API contract (critical)**:

`SurfaceRepairService.repair()` MUST take `Sequence[SurfaceStatus]` (not findings or raw paths) and return `RepairResult`. This preserves manifest/source/hash/refcount context from the provider.

```python
class SurfaceRepairService:
    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        kinds: set[SurfaceKind] | None = None,
        dry_run: bool = False,
    ) -> RepairResult: ...
```

Do NOT reconstruct `SurfaceInstance` from `SurfaceFinding` fields. Findings are for reporting; `SurfaceStatus` objects (containing the full `SurfaceInstance`) are what repair receives. The `--fix` CLI flag passes the status objects from the preceding probe call into `repair()`.

**Files**: `src/specify_cli/tool_surface/repair.py` (new, ~60 lines)

**Validation**:
- [ ] Returns `RepairResult` with `failed` list if no provider can handle the surface kind (does not raise)
- [ ] Delegates to provider; does not reimplement installer logic
- [ ] Takes `Sequence[SurfaceStatus]` not `SurfaceFinding` objects

---

### T017 -- Add `doctor tool-surfaces` subcommand to `cli/commands/doctor.py`

**Purpose**: Add `spec-kitty doctor tool-surfaces [--kind KIND] [--tool TOOL] [--json] [--fix]` as a new subcommand.

**Thin wiring only**: C-001 prohibits adding logic to `doctor.py`. T017 adds ONLY the Typer command registration (`@doctor_app.command("tool-surfaces")`) and argument parsing. All behavior is delegated to `SurfaceStatusService`, `SurfaceRepairService`, and the provider layer in `tool_surface/`. Zero business logic in `doctor.py`.

**`doctor skills` backward compat**: Wire `doctor skills` to call `doctor tool-surfaces --kind command-skill --kind command-file` internally. The JSON output of `doctor skills --json` must remain identical. This is the ONLY change to existing `doctor skills` behavior.

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
4. Call `SurfaceStatusService.collect()` → `SurfaceReport` (containing `surfaces[]` and `findings[]`)
5. If `--fix`: pass the `SurfaceReport.surfaces` list (not the findings) to `SurfaceRepairService.repair(project_root, statuses=report.surfaces, dry_run=False)` → `RepairResult`
6. Output JSON (or human-readable if `--json` not passed); top-level key is `ok` (bool), not `clean`

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

def test_doctor_tool_surfaces_ok_when_installed():
    """Reports ok=true when all command skills are installed."""
    ...

def test_doctor_tool_surfaces_finding_when_missing():
    """Reports generated-surface-missing when skills are absent."""
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

---

### T049 -- Implement `providers/slash_commands.py`

**Purpose**: Add a `SurfaceProvider` for slash-command files (`command_file` kind), wrapping the existing global command directory machinery.

**Wraps**:
- `specify_cli.core.config.AGENT_COMMAND_CONFIG`
- `specify_cli.runtime.agent_commands` (or equivalent command-file loader)
- existing `_load_slash_command_state()` function

**Expected behavior**:
- Expand one `SurfaceInstance` per configured slash-command agent that supports command files.
- Status includes the global command path (not a project path).
- Repair can regenerate global commands if existing command-file logic already supports it.
- Findings clearly indicate user-global path when relevant.
- `NullWriter` or unsupported agents yield `research-gap-surface`, not silent OK.

**Finding codes**: use `generated-surface-missing`, `managed-file-drift`, `stale-generated-surface` (see findings.py constants updated in T015).

**Files**:
- `src/specify_cli/tool_surface/providers/slash_commands.py` (new, ~80 lines)

**Validation**:
- [ ] Provider integrates into the same `doctor tool-surfaces --kind command-file` path established in T017
- [ ] `doctor skills` continues to work via the `--kind command-skill --kind command-file` delegation

---

## Definition of Done

- [ ] `spec-kitty doctor tool-surfaces --json` runs and produces schema-valid output
- [ ] `spec-kitty doctor tool-surfaces --kind command-skill --fix` repairs missing skills
- [ ] `pytest tests/specify_cli/tool_surface/integration/test_migration_compat.py` still passes
- [ ] `pytest tests/specify_cli/tool_surface/` passes
- [ ] `mypy --strict src/specify_cli/tool_surface/` passes
- [ ] `ruff check src/specify_cli/tool_surface/` passes (complexity <= 15)
- [ ] Finding codes are stable kebab-case strings (e.g., `generated-surface-missing`, `managed-file-drift`)

## Risks

- **Complexity ceiling**: `SurfacePlanBuilder` and the doctor subcommand handler are the most likely functions to exceed complexity 15. Extract helpers proactively.
- **`doctor.py` god-module**: Do not add new logic to the top-level module body; add a subcommand function and keep it thin.
- **Finding code stability**: The codes introduced here are permanent. Consult the architecture gist before finalizing names.

## Reviewer Guidance (Codex)

- Verify `doctor skills --json` schema is unchanged (migration compat)
- Verify finding codes use stable kebab-case JSON values; Python constants may be SCREAMING_SNAKE but must map to kebab-case strings
- Verify `CommandSkillsProvider` delegates to the installer and does not reimplement hash logic
- Verify CLI output validates against `doctor-tool-surfaces-output.schema.json`
