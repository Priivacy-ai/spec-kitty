---
work_package_id: WP07
title: Legacy Agent Config Refactor
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-008
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
agent: claude
shell_pid: '30035'
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/test_agent_config.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/config.py
- tests/specify_cli/cli/commands/test_agent_config.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Refactor `spec-kitty agent config list/status/sync` to compute install state via `SurfacePlan` internally, removing duplicated recomputation logic. The external interface -- command names, option flags, JSON output schema -- must not change.

**The WP02 migration compat tests are the acceptance gate for this WP.** If `test_agent_config_compat.py` fails after this refactor, the WP must not merge.

**Child issue**: #1941
**Parent epic**: #1945

## Context

`src/specify_cli/cli/commands/agent/config.py` currently has its own `SKILL_ONLY_AGENTS`, `GLOBAL_COMMAND_AGENTS`, `VALID_AGENTS`, and status logic that recomputes install state independently of the registry. This duplicated logic is the source of inconsistency between `doctor skills` and `agent config status` output.

After this WP, `agent config status` consults the `SurfacePlan` for configured tools rather than recomputing its own list. The output JSON schema must remain identical.

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Command: `spec-kitty agent action implement WP07 --agent claude`

## Subtask Details

### T034 -- Refactor `config.py` to route through `SurfacePlan`

**Purpose**: Replace the local status-computation logic in `agent/config.py` with a call to `SurfacePlanBuilder` + `SurfaceStatusService`.

**Approach**:
1. Read the current `agent/config.py` fully before making changes. Understand all existing status-computation paths.
2. Identify the sections that currently compute "what should exist" (e.g., `SKILL_ONLY_AGENTS` lookup, command-dir scan).
3. Replace those sections with:
   ```python
   builder = SurfacePlanBuilder(registry=get_registry(), providers=get_providers())
   plans = builder.build(configured_tool_keys=get_configured_tools(), project_root=project_root)
   status_svc = SurfaceStatusService(providers=get_providers())
   report = status_svc.collect(project_root=project_root, plans=plans)
   ```
4. Map `report.surfaces` and `report.findings` back to the existing output format (`agent config status` JSON schema).

**Critical**: The output schema of `agent config list --json` and `agent config status --json` must not change. Add any new fields only additively; do not remove or rename existing fields.

**Files**: `src/specify_cli/cli/commands/agent/config.py` (MODIFIED)

**Validation**:
- [ ] `spec-kitty agent config list --json` output is unchanged (WP02 compat test passes)
- [ ] `spec-kitty agent config status --json` output is unchanged
- [ ] `spec-kitty agent config sync` behavior is unchanged

---

### T035 -- Remove duplicated recomputation logic

**Purpose**: After the routing is working and compat tests pass, remove the duplicated local status-computation code.

**Safe to remove** (after routing is verified):
- Local `SKILL_ONLY_AGENTS`, `GLOBAL_COMMAND_AGENTS`, `VALID_AGENTS` constants that are now derived from the registry
- Local status-computation functions that have been replaced by `SurfaceStatusService`

**Preserve**:
- Any validation or error-handling logic that is not covered by the provider model
- Any config-specific flags or options that are not part of the surface contract

**Approach**: Remove incrementally. After each removal, run `pytest tests/specify_cli/cli/commands/test_agent_config.py` to verify nothing broke.

**Files**: `src/specify_cli/cli/commands/agent/config.py` (MODIFIED further)

**Validation**:
- [ ] No orphaned local constants that now have registry equivalents
- [ ] Sonar complexity ceiling (<=15) still respected in modified functions

---

### T036 -- Verify migration compat fixtures still pass

**Purpose**: Run the WP02 compat tests explicitly and verify they still pass after the refactor.

```bash
pytest tests/specify_cli/tool_surface/integration/test_migration_compat.py \
       tests/specify_cli/tool_surface/integration/test_agent_config_compat.py \
       -v
```

If any test fails, stop and diagnose before proceeding. The refactor must not change external behavior.

**Validation**:
- [ ] Both compat test files pass with zero failures

---

### T037 -- Write/update tests for refactored `agent config`

**Purpose**: Ensure the refactored command is fully tested with the new routing.

**Update existing tests**: `tests/specify_cli/cli/commands/test_agent_config.py`
- Add test that verifies `SurfacePlanBuilder` is called (not the local computation)
- Add test for any edge cases that the new routing handles differently

**Do not** remove existing tests that verify external behavior -- those are part of the compatibility contract.

**Files**: `tests/specify_cli/cli/commands/test_agent_config.py` (MODIFIED)

**Validation**:
- [ ] `pytest tests/specify_cli/cli/commands/test_agent_config.py` passes
- [ ] Coverage for the refactored paths is >= 90%

## Definition of Done

- [ ] `spec-kitty agent config list --json` output identical to pre-refactor
- [ ] `spec-kitty agent config status --json` output identical to pre-refactor
- [ ] `pytest tests/specify_cli/tool_surface/integration/test_agent_config_compat.py` passes
- [ ] `pytest tests/specify_cli/cli/commands/test_agent_config.py` passes
- [ ] Duplicated local constants removed
- [ ] `mypy --strict src/specify_cli/cli/commands/agent/config.py` passes
- [ ] Cyclomatic complexity <= 15 for all modified functions

## Risks

- **Semantic mismatch**: `agent config status` may have subtly different semantics than `doctor tool-surfaces`. The refactor must preserve `agent config`'s semantics exactly, even if they differ from the surface contract model. Map carefully rather than assuming equivalence.
- **Shared constants**: `SKILL_ONLY_AGENTS` etc. may be imported by other modules. Check all importers before removing.

## Reviewer Guidance (Codex)

- Verify WP02 compat tests still pass
- Verify no external interface changes (no removed fields, no renamed flags)
- Verify local duplicate constants are removed
- Verify `SurfacePlanBuilder` is used (not local recomputation)
