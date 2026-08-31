---
work_package_id: WP11
title: Activation-filtered DRG traversal
dependencies:
- WP03
- WP06
- WP10
requirement_refs:
- FR-006
- FR-018
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: acdc0d1f0cd0e1b49bbb99872c108e0007d8b282
created_at: '2026-05-30T20:10:27.025402+00:00'
subtasks:
- T064-drg
- T066b
- T066
- T067
- T068
- T069
- T070
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3302150"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/charter/drg.py
execution_mode: code_change
owned_files:
- src/charter/drg.py
- src/doctrine/drg/org_pack_loader.py
- tests/charter/test_activation_filtered_drg.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP11 — Activation-filtered DRG traversal

## Context

FR-018 specifies that DRG traversal is activation-filtered: only doctrine artifacts that are explicitly activated in the project charter are included in the resolved governance set. "Activated" and "registered" are synonyms — an artifact that is not activated is non-canonical and invisible to charter-mediated resolution.

The `PackContext` (from WP06) carries `activated_kinds` and `activated_mission_types` as frozen sets. The DRG traversal reads these sets from `PackContext` and filters the resolved artifact set accordingly.

Non-activated artifacts remain accessible via the doctrine module API on direct user request — they are not deleted, just invisible to charter-mediated resolution.

## Objective

Add activation-filter logic to the DRG traversal in `src/charter/drg.py` and/or `src/doctrine/drg/`. Apply the filter to all artifact kinds (directives, tactics, mission types, mission steps, agent profiles). Write tests verifying the filter behavior.

## FR-006 Context

FR-006 specifies two-tier directive scope:
1. **Project-scoped**: `org-charter.yaml` `required_directives` apply to all mission types
2. **Mission-type-scoped**: a mission type's `governance_refs` adds directives scoped only to that mission type

The activation filter ensures that mission-type-scoped directives (from `governance_refs`) are only included in governance resolution when that mission type is activated. Software-dev directives do not appear in non-software missions because they are in `software-dev.governance_refs`, which is only included when software-dev is activated.

## Subtasks

### T064-drg — Wire PackContext into drg.py caller

In `src/charter/drg.py`, find the call(s) to `load_org_charter_policies(repo_root)`. Update them to pass a `PackContext`:

```python
from charter.pack_context import PackContext

ctx = PackContext.from_config(repo_root)
policies = load_org_charter_policies(repo_root, pack_context=ctx)
```

This ensures that `drg.py` no longer causes indirect config.yaml reads through the loader — all pack-set data flows through `PackContext`. WP10 writes the integration test proving this works.

### T066b — Migrate org_pack_loader.py kind alias (deferred from WP01)

WP01 deferred the migration of `_ORG_DRG_CANONICAL_KINDS` in `src/doctrine/drg/org_pack_loader.py` to this WP (since WP11 owns that file).

1. Open `src/doctrine/drg/org_pack_loader.py` and find `_ORG_DRG_CANONICAL_KINDS`
2. Update it to use `mission_steps` as the canonical kind key; keep `mission_step_contracts` as an alias for one release (backward compat with pre-migration projects):
   ```python
   _ORG_DRG_CANONICAL_KINDS = {
       ...
       "mission_steps": ...,
       "mission_step_contracts": ...,  # alias; maps to mission_steps resolver
   }
   ```
3. Update any import from `doctrine.mission_step_contracts` in this file to use `doctrine.missions.models` instead

This task completes the model migration that WP01 started.

### T066 — Add activation filter to DRG traversal

Open `src/charter/drg.py` (and/or `src/doctrine/drg/org_pack_loader.py` if that is where DRG traversal happens).

Before traversal begins, read `PackContext.activated_mission_types`:
- During mission-type artifact resolution: only include mission types whose `id` is in `pack_context.activated_mission_types`
- During mission-step artifact resolution: only include steps belonging to activated mission types

This filter is applied at the start of traversal — activated types are enumerated, then their steps are resolved.

Implementation pattern:
```python
def traverse(
    artifact_kind: str,
    pack_context: PackContext,
    repo_root: Path,
) -> list[ArtifactResult]:
    # Activation filter: skip non-activated mission types
    active_mission_types = pack_context.activated_mission_types
    if artifact_kind in ("mission_type", "mission_step"):
        results = [r for r in raw_results if r.mission_type_id in active_mission_types]
    return results
```

### T067 — Apply filter across all artifact kinds

Extend the activation filter to cover all artifact kinds, not just mission types:
- `directives`: only include if the directive's source pack is activated (or if it is a project-scoped directive)
- `tactics`: same
- `agent_profiles`: only if the profile's owning pack is activated
- `mission_types`: only if `mission_type_id` in `activated_mission_types`
- `mission_steps`: only if owning `mission_type_id` in `activated_mission_types`

Use `PackContext.activated_kinds` for non-mission-type artifact kinds.

### T068 — Verify PackContext.activated_kinds is correctly populated

**Do NOT modify `src/charter/pack_context.py`** — that file is owned by WP06. WP06's T038 specifies that `activated_kinds` must be populated from the charter's activation config with a backward-compatible default.

Before writing any filter logic in this WP, read `src/charter/pack_context.py` and confirm:
1. `PackContext.activated_kinds` is a `frozenset[str]` field
2. `PackContext.from_config()` populates it from the charter config (key: `activated_kinds`)
3. If the key is absent, the default is all built-in artifact kinds (backward-compat)

If WP06 has NOT been merged yet and these guarantees are not in place, stub the filter using `frozenset` literals for testing and add a `# TODO: remove stub once WP06 is merged` comment. Do not commit the stub past review.

### T069 — Non-activated artifacts remain accessible via doctrine API

This is a documentation and test guard, not a code change:

Verify that calling `MissionTypeRepository.get("documentation")` directly (bypassing the charter/DRG path) returns the `documentation` mission type even when `documentation` is not activated in the project charter.

The activation filter applies only to charter-mediated resolution paths. Direct doctrine API calls are exempt.

Add a comment in the DRG traversal code explaining this invariant.

### T070 — Activation filter tests

Write `tests/charter/test_activation_filtered_drg.py`:

Test cases:
- **Activation filter**: project charter activates only `software-dev`; DRG traversal returns only software-dev mission type and its steps
- **Non-activated excluded**: `documentation` not in activated set; DRG traversal does not include documentation mission type or its steps
- **FR-006 directive scope**: software-dev `governance_refs` directives do not appear in governance resolution for a documentation mission (different mission type)
- **Direct doctrine API bypass**: `MissionTypeRepository.get("documentation")` returns the type even when not activated in charter
- **Empty activation set**: DRG traversal with empty `activated_mission_types` returns empty list for mission types

Use `tmp_path` fixtures for PackContext construction with test data.

## Acceptance Criteria

- [ ] DRG traversal only returns artifacts for activated mission types
- [ ] Software-dev `governance_refs` directives do not appear in documentation mission governance
- [ ] Non-activated artifacts are still accessible via direct doctrine API calls
- [ ] `PackContext.activated_kinds` drives the per-kind filter
- [ ] `tests/charter/test_activation_filtered_drg.py` passes
- [ ] `mypy --strict` clean on modified files

## References

- FR-006: Two-tier directive scope
- FR-018: Activation-filtered DRG traversal
- data-model.md §"PackContext" — activated_kinds and activated_mission_types fields
- contracts/activation-filtered-drg-contract.md

## Activity Log

- 2026-05-30T20:10:27Z – claude:opus:python-pedro:implementer – shell_pid=3231293 – Assigned agent via action command
- 2026-05-30T20:25:16Z – claude:opus:python-pedro:implementer – shell_pid=3231293 – Ready for review: activation-filtered DRG, PackContext wired, org_pack_loader alias migrated, 9 new tests pass
- 2026-05-30T20:26:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=3302150 – Started review via action command
