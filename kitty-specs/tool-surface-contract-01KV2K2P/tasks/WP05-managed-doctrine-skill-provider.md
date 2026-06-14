---
work_package_id: WP05
title: Managed Doctrine Skill Provider
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-003
- FR-006
- FR-010
- FR-018
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
agent: claude
shell_pid: '29783'
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/providers/
create_intent:
- src/specify_cli/tool_surface/providers/managed_skills.py
- tests/specify_cli/tool_surface/providers/test_managed_skills.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/providers/managed_skills.py
- tests/specify_cli/tool_surface/providers/test_managed_skills.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Add a `SurfaceProvider` for managed doctrine skills, explicitly separating them from command skills in `doctor tool-surfaces` output. The existing managed-skill infrastructure (`skills.registry`, `skills.installer`, `skills.verifier`) is wrapped as a provider -- its logic is not changed.

**Out-of-map edits required**: Extends `status.py`, `findings.py`, `repair.py` (owned by WP03) for `SurfaceKind.DOCTRINE_SKILL`. Rationale: "WP05 sequential; no parallel conflict."

**Child issue**: #1939
**Parent epic**: #1945

## Context

Managed doctrine skills are separate from command skills:
- Command skills: slash-command invocations (e.g., `.agents/skills/spec-kitty.plan/SKILL.md`)
- Doctrine skills: managed knowledge/mission-step surfaces (managed by `skills.installer`/`skills.verifier`)

They share some infrastructure but are distinct surface kinds with separate manifests (`.kittify/skills-manifest.json` vs `.kittify/command-skills-manifest.json`).

**Important**: The managed doctrine skill verifier already has its own reporting. The provider wrapper must not duplicate or conflict with that logic -- it only adds the surface contract view on top of it.

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Command: `spec-kitty agent action implement WP05 --agent claude`

## Subtask Details

### T024 -- Implement `providers/managed_skills.py`

**Purpose**: Wrap `specify_cli.skills.registry`, `specify_cli.skills.installer`, and `specify_cli.skills.verifier` as a `SurfaceProvider`.

**Key design points**:
- Read the managed-skill manifest (`.kittify/skills-manifest.json`) to know what skills should exist
- Use the verifier to check current state
- Delegate repair to the installer

```python
class ManagedSkillsProvider:
    provider_key = "managed_skills"

    def __init__(self, registry: SkillRegistry, installer: SkillInstaller, verifier: SkillVerifier) -> None:
        ...

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == SurfaceKind.DOCTRINE_SKILL

    def expand(self, definition: SurfaceDefinition, tool_key: str, project_root: Path) -> list[SurfaceInstance]:
        # Ask registry what doctrine skills should exist for this tool
        ...

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        # Use verifier to check current state and return SurfaceStatus
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
```

**Critical**: Do not change the behavior of the underlying `skills.installer`, `skills.verifier`, or `skills.registry` modules. Do not modify their internal state or output.

**Files**: `src/specify_cli/tool_surface/providers/managed_skills.py` (new, ~90 lines)

**Validation**:
- [ ] `isinstance(ManagedSkillsProvider(...), AbstractSurfaceProvider)` is True
- [ ] `mypy --strict` passes
- [ ] Does not modify any existing `skills.*` module behavior

---

### T025 -- Extend `status.py` and `findings.py` for doctrine-skill kind

**Out-of-map edit to `status.py`** (owned by WP03):
- Extend the `SurfaceStatusService.collect()` status/finding mapping to handle `SurfaceKind.DOCTRINE_SKILL`
- Use finding code `"generated-surface-missing"` (kebab-case JSON wire value) for missing doctrine skills; Python constant `GENERATED_SURFACE_MISSING` maps to this string

**Out-of-map edit to `findings.py`** (owned by WP03):
- Confirm `GENERATED_SURFACE_MISSING = "generated-surface-missing"` constant exists; document that this WP activates it for `DOCTRINE_SKILL` kind

**Rationale**: Sequential after WP03; no parallel conflict.

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind doctrine-skill --json` returns doctrine-skill findings
- [ ] Findings appear as `surface_kind: "doctrine_skill"` (not `"command_skill"`)

---

### T026 -- Extend repair service for doctrine-skill findings

**Out-of-map edit to `repair.py`** (owned by WP03):
- Add case for `SurfaceKind.DOCTRINE_SKILL` delegating to `ManagedSkillsProvider.repair()`

**Validation**:
- [ ] `spec-kitty doctor tool-surfaces --kind doctrine-skill --fix` repairs missing doctrine skills
- [ ] Does not affect command-skill repair

---

### T027 -- Write tests for managed-skill provider

**Tests**:
```python
def test_managed_skills_provider_can_handle_doctrine_skill():
    ...

def test_managed_skills_provider_cannot_handle_command_skill():
    ...

def test_managed_skills_expand_returns_per_tool_skills():
    """Skills count must match what the manifest expects."""
    ...

def test_managed_skills_probe_detects_missing():
    ...

def test_managed_skills_repair_calls_installer():
    """Verifies repair delegates to installer, not a reimplementation."""
    ...

def test_doctrine_vs_command_skill_in_doctor_output():
    """doctor tool-surfaces output separates doctrine and command kinds."""
    ...
```

**Files**: `tests/specify_cli/tool_surface/providers/test_managed_skills.py` (new, ~100 lines)

**Validation**:
- [ ] All tests pass
- [ ] WP02 migration compat tests still pass
- [ ] `pytest tests/specify_cli/tool_surface/` passes

## Definition of Done

- [ ] `spec-kitty doctor tool-surfaces --kind doctrine-skill --json` works
- [ ] Doctrine skills and command skills appear as separate `surface_kind` values in output
- [ ] `pytest tests/specify_cli/tool_surface/providers/test_managed_skills.py` passes
- [ ] WP02 migration compat tests pass
- [ ] `mypy --strict src/specify_cli/tool_surface/` passes

## Risks

- **Verifier output overlap**: The existing verifier may already report managed-skill gaps. Ensure the provider wrapper does not emit duplicate findings or interfere with existing verifier output.
- **Manifest schema**: The `skills-manifest.json` schema may differ from `command-skills-manifest.json`. Treat them as separate data sources.

## Reviewer Guidance (Codex)

- Verify `surface_kind: "doctrine_skill"` is distinct from `"command_skill"` in output
- Verify provider does not modify `skills.installer`/`skills.verifier` internals
- Verify no duplicate findings with existing verifier output
