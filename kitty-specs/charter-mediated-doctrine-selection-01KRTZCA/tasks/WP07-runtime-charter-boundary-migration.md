---
work_package_id: WP07
title: Runtime → Charter Boundary Migration (13 files, allowlist drop)
dependencies:
- WP03
requirement_refs:
- FR-013
- C-001
- C-003
- C-004
- NFR-004
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
- T035
- T036
- T037
- T038
- T039
- T040
agent: "claude:opus-4-7:python-pedro:implementer"
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/registry.py
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/registry.py
- src/specify_cli/invocation/router.py
- src/specify_cli/mission_loader/registry.py
- src/specify_cli/mission_loader/contract_synthesis.py
- src/specify_cli/mission_step_contracts/executor.py
- src/specify_cli/calibration/walker.py
- src/specify_cli/glossary/drg_builder.py
- src/specify_cli/missions/__init__.py
- src/specify_cli/runtime/resolver.py
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/cli/commands/charter_bundle.py
- src/specify_cli/upgrade/migrations/m_3_2_6_charter_bundle_v2.py
- src/specify_cli/bulk_edit/occurrence_map.py
- src/kernel/schema_utils.py
- tests/architectural/test_runtime_charter_doctrine_boundary.py
role: implementer
history: []
tags: []
shell_pid: "1641835"
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Migrate the 13 runtime files in `tests/architectural/test_runtime_charter_doctrine_boundary.py::_BASELINE_ALLOWLIST` from `from doctrine.*` to `from charter.<facade>` imports (using the facades from WP03). Promote `SchemaUtilities` to `src/kernel/schema_utils.py` for the special-case bulk_edit consumer.

The boundary allowlist MUST shrink from 13 entries to ≤ 2 documented exceptions (C-004). Per C-003, each file's allowlist entry is removed in the same commit as the import migration.

---

## Context

The 13-file baseline was captured at commit `bd95f1f5`. The audit at `docs/development/runtime-charter-doctrine-boundary.md` Appendix lists exactly which doctrine surface each file consumes. WP03 shipped the matching facades.

**Scope clarification (resolves analysis-report finding I2):** scope is **13 baseline-allowlist files** that migrate from direct `doctrine.*` imports to `charter.*` facade imports, **plus** 1 new module `src/kernel/schema_utils.py` that lands as part of the SchemaUtilities promotion (T040). Total: **14 paths touched, but the boundary-allowlist ratchet counts only the 13** migrating runtime files. The new kernel module is not a runtime caller of `doctrine.*` — it is the promotion target — so it never enters the allowlist.

See:
- [plan.md §1.3, §2.9](../plan.md)
- [data-model.md §8](../data-model.md)
- [contracts/charter-facade-modules.md](../contracts/charter-facade-modules.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP07 --agent claude`

Each subtask is a single file (or small bundle) + matching allowlist edit. Per C-003, never land an allowlist removal without the import swap, and vice versa.

---

## Subtasks

### T032 — Migrate `invocation/registry.py`

**File**: `src/specify_cli/invocation/registry.py`

Replace:
```python
from doctrine.agent_profiles.profile import AgentProfile
from doctrine.agent_profiles.repository import AgentProfileRepository
```
With:
```python
from charter.profiles import AgentProfile, AgentProfileRepository
```
Remove the file from `_BASELINE_ALLOWLIST`.

### T033 — Migrate `invocation/router.py`

Same pattern. Replace:
```python
from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES
from doctrine.agent_profiles.profile import Role
```
With:
```python
from charter.profiles import DEFAULT_ROLE_CAPABILITIES, Role
```
Remove from allowlist.

### T034 — Migrate `mission_loader/registry.py` + `contract_synthesis.py`

Both swap to `from charter.mission_steps import MissionStep, MissionStepContract, MissionStepContractRepository`. Remove both entries from allowlist.

### T035 — Migrate `mission_step_contracts/executor.py`

Multi-surface migration: combines `charter.mission_steps` for the contracts and `charter.drg` for the graph types:

```python
from charter.mission_steps import MissionStep, MissionStepContract, MissionStepContractRepository
from charter.drg import DRGGraph, NodeKind, ResolvedContext, resolve_context
from doctrine.artifact_kinds import ArtifactKind  # if no facade — see note below
```

**Note**: `doctrine.artifact_kinds` may need a facade. Add it to `charter/drg.py` or create a tiny `charter/artifact_kinds.py` re-export if the import is needed. Document the addition.

Remove from allowlist.

### T036 — Migrate `calibration/walker.py` + `glossary/drg_builder.py`

Both swap to `from charter.drg import ...`. Remove both entries.

### T037 — Migrate `missions/__init__.py`

Swap to `from charter.primitives import PrimitiveExecutionContext, execute_with_glossary`. Remove from allowlist.

### T038 — Migrate `runtime/resolver.py`

Swap to `from charter.resolution import ResolutionResult, ResolutionTier`. Remove from allowlist.

### T039 — Migrate the 3 versioning callers

`cli/commands/charter.py`, `cli/commands/charter_bundle.py`, `upgrade/migrations/m_3_2_6_charter_bundle_v2.py` all swap to `from charter.versioning import check_bundle_compatibility, get_bundle_schema_version`.

**HiC-facing decision per C-004**: default plan is to migrate all three. If any migration turns out to be lossy (e.g. a symbol not actually exported by `doctrine.versioning`'s public surface), document it and leave up to 2 entries in the allowlist with a clear comment explaining why.

### T040 — `SchemaUtilities` → kernel promotion + bulk_edit migration

**Files**:
- `src/kernel/schema_utils.py` (NEW) — host or re-export `SchemaUtilities`
- `src/specify_cli/bulk_edit/occurrence_map.py` — swap to `from kernel.schema_utils import SchemaUtilities`

If `doctrine.shared.schema_utils.SchemaUtilities` is small (typically the case for shared schema helpers), move the class body into `kernel/schema_utils.py` and leave `doctrine.shared.schema_utils` as a re-export for backward compatibility. If it's large or has its own dependencies, leave it in doctrine and have `kernel/schema_utils.py` re-export it (cleaner break in a follow-up mission).

Remove `bulk_edit/occurrence_map.py` from allowlist.

---

## Definition of Done

- ✅ `tests/architectural/test_runtime_charter_doctrine_boundary.py::test_runtime_has_no_new_direct_doctrine_imports` passes with `_BASELINE_ALLOWLIST` size ≤ 2
- ✅ All 13 baseline files now import from `charter.<facade>` or `kernel.schema_utils`
- ✅ Allowlist entries match exactly the migrated state (no stale entries, no new violators)
- ✅ `tests/architectural/test_layer_rules.py` — 8/8 stays green
- ✅ `tests/architectural/test_charter_facades_reexport_doctrine.py` stays green
- ✅ All previously-passing test surfaces (contract, integration, unit) for the migrated modules continue to pass
- ✅ `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 stays green

---

## Risks

| Risk | Mitigation |
|------|------------|
| A facade missing a symbol the runtime needs | WP03 audit + this WP's per-file dry-run identifies missing exports; add them to the facade before the migration commit. |
| A migration changes runtime behaviour (object identity vs alias) | Facades are pure re-exports (identity-checked by the architectural test). Behaviour is unchanged. |
| `doctrine.artifact_kinds` migration requires adding a facade | Document the addition; either extend `charter/drg.py` or add a tiny `charter/artifact_kinds.py`. |
| `SchemaUtilities` move breaks an external caller that imports from `doctrine.shared.schema_utils` directly | Leave the doctrine path as a re-export so existing direct imports continue to work. |
| Migrations land out-of-order and a partial allowlist state breaks CI | Each migration is one atomic commit (import swap + allowlist edit). Per C-003. |
| Versioning migration is lossy and forces an allowlist exception | Document the exception with the rationale in the allowlist comment. C-004 caps at 2. |

---

## Reviewer Guidance

- Verify each commit pairs an import swap with the matching allowlist edit (per C-003).
- Run the boundary ratchet test after each commit; confirm it stays green.
- Verify no commit introduces a NEW `from doctrine.*` import in a runtime file.
- Verify the final allowlist count is ≤ 2 (C-004); any exceptions are documented with a one-line rationale.
- Spot-check that facade re-exports preserve object identity (the architectural test from WP03 enforces this).

## Activity Log

- 2026-05-17T16:36:26Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1641835 – Started implementation via action command
