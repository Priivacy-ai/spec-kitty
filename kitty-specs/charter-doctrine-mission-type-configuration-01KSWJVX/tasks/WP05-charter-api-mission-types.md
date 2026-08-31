---
work_package_id: WP05
title: 'Charter API: existing_mission_types() + resolve_action_sequence() + open Literal→str'
dependencies:
- WP03
- WP04
- WP06
requirement_refs:
- FR-007
- FR-008
- FR-009
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 43f4cc6cb12e7a4a554491ba4d63db28920e8e05
created_at: '2026-05-30T20:09:12.948944+00:00'
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
- T035
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3297273"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/charter/mission_type_profiles.py
execution_mode: code_change
owned_files:
- src/charter/mission_type_profiles.py
- tests/charter/test_mission_type_profiles.py
- tests/charter/test_action_sequence_dispatch.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP05 — Charter API: existing_mission_types() + resolve_action_sequence() + open Literal→str

## Context

The charter module (`src/charter/`) is the anti-corruption layer (ACL) between `specify_cli.next` and the doctrine layer. This WP adds two new public API functions to `src/charter/mission_type_profiles.py` that `spec-kitty next` will use to replace the hardcoded frozenset dispatch tables (deleted in WP07).

Additionally, `MissionTypeProfile.mission_type` is currently typed as `Literal["software-dev", "documentation", "research", "plan"]`. FR-009 requires opening this to `str` so custom mission types can be supported. Validation moves from Pydantic model construction time to call-time via `charter.existing_mission_types()`.

## Objective

Add `charter.existing_mission_types()` and `charter.resolve_action_sequence()` to `src/charter/mission_type_profiles.py`; open `MissionTypeProfile.mission_type` from `Literal` to `str`; update `UnknownMissionTypeError` to include `registered_ids`; update the ATDD test suite.

## Public API to Implement

```python
# src/charter/mission_type_profiles.py

def existing_mission_types(repo_root: Path) -> list[str]:
    """Return sorted, deduplicated IDs of activated mission types for the project.

    Only types that are explicitly activated in the project charter are returned.
    Non-activated types are excluded regardless of their presence in the doctrine layer.
    """
    ...

def resolve_action_sequence(
    mission_type_id: str,
    repo_root: Path,
) -> list[str]:
    """Return the live action sequence for the given mission type.

    Reads MissionType YAML through the built-in → org → project DRG chain.
    Called fresh at each invocation; not cached across calls.
    Raises UnknownMissionTypeError if mission_type_id is not in existing_mission_types(repo_root).
    """
    ...
```

## Subtasks

### T029 — Open MissionTypeProfile.mission_type from Literal to str

In `src/charter/mission_type_profiles.py`, find `mission_type: Literal["software-dev", "documentation", "research", "plan"]` and change the type annotation to `mission_type: str`.

**Important Pydantic v2 detail**: In Pydantic v2, `Literal["a", "b"]` is enforced via the type annotation itself — there is no separate `@field_validator` to remove. Simply changing the annotation from `Literal[...]` to `str` is the complete change. Do NOT search for or remove a validator that does not exist; removing code that is not there would cause test failures.

Validation against the activation list moves to `resolve_mission_type_governance()` (T033).

### T030 — Update UnknownMissionTypeError with registered_ids

Find `UnknownMissionTypeError` in `src/charter/mission_type_profiles.py`. Add a `registered_ids: list[str]` field to the exception. Update the error message to include the list of registered IDs:

```
Unknown mission type 'compliance-audit'. Registered types: documentation, plan, research, software-dev.
```

This satisfies FR-009's requirement that the error includes the list of registered IDs.

### T031 — Implement existing_mission_types()

Implementation approach:
1. Use `PackContext.from_config(repo_root)` (from WP06) to load the charter activation set
2. Return `sorted(pack_context.activated_mission_types)` — the set of types activated in the project charter
3. `PackContext.from_config()` already handles the new-project fallback (when no config.yaml exists, it defaults all built-in types as activated per FR-019 intent) — do NOT add a separate fallback here

**FR-018 alignment**: Do NOT return types that are not in `pack_context.activated_mission_types`. A non-activated type is invisible to charter-mediated resolution. The FR-019 migration (WP12) ensures every existing project has all built-in types activated before this code is first exercised; the fallback lives in `PackContext.from_config()`, not here.

Ensure this function is the single source of truth for "what mission types are activated" — do not duplicate this logic elsewhere.

### T032 — Implement resolve_action_sequence()

Implementation approach:
1. Call `existing_mission_types(repo_root)` to validate the mission type is registered
2. If not found, raise `UnknownMissionTypeError` with `registered_ids`
3. Load `PackContext` and construct the DRG layer context
4. Use `MissionTypeRepository` to load the mission type through the `built-in → org → project` chain
5. Apply `extends:` chain resolution if the loaded definition has `extends:` set
6. Return the resolved `action_sequence`

This function must not be cached across calls (FR-007): it reads from disk each time. NFR-001 ≤100ms budget applies.

### T033 — Update resolve_mission_type_governance()

Find `resolve_mission_type_governance(repo_root, feature_dir)` in `src/charter/mission_type_profiles.py`.

Update the validation check from:
```python
if mission_type not in {"software-dev", "documentation", "research", "plan"}:
    raise UnknownMissionTypeError(mission_type)
```

To:
```python
registered = existing_mission_types(repo_root)
if mission_type not in registered:
    raise UnknownMissionTypeError(mission_type, registered_ids=registered)
```

### T034 — Update ATDD test suite

Find `tests/` files that pin the `Literal` constraint on `MissionTypeProfile.mission_type`. These tests likely assert that `"custom-type"` raises a `ValidationError` at Pydantic model construction time.

Update them to reflect the new behavior:
- `MissionTypeProfile(mission_type="custom-type", ...)` should succeed (no model-construction error)
- `resolve_action_sequence("custom-type", repo_root)` should raise `UnknownMissionTypeError` when `custom-type` is not activated

Also update `tests/` files that test `test_wp_prompt_governance_contract.py` if they reference the `Literal` set.

### T035 — Write charter API tests

Write `tests/charter/test_action_sequence_dispatch.py`:

Test cases:
- `existing_mission_types(repo_root)` returns sorted list of built-in types when no charter config exists
- `existing_mission_types(repo_root)` returns only activated types when charter config specifies activation
- `resolve_action_sequence("software-dev", repo_root)` returns the built-in action sequence
- `resolve_action_sequence("nonexistent", repo_root)` raises `UnknownMissionTypeError` with `registered_ids`
- `UnknownMissionTypeError.registered_ids` contains the sorted list of activated types
- `MissionTypeProfile(mission_type="anything", ...)` succeeds (no Literal constraint at model time)

Extend `tests/charter/test_mission_type_profiles.py` with tests for `resolve_mission_type_governance()` using the new call-time validation.

## Acceptance Criteria

- [ ] `MissionTypeProfile.mission_type` is typed as `str` (no `Literal`)
- [ ] `UnknownMissionTypeError` includes `registered_ids` in message
- [ ] `existing_mission_types()` returns only activated types
- [ ] `resolve_action_sequence()` raises `UnknownMissionTypeError` for unknown types
- [ ] All updated ATDD tests pass
- [ ] `tests/charter/test_action_sequence_dispatch.py` passes
- [ ] `mypy --strict` clean on `src/charter/mission_type_profiles.py`
- [ ] `__all__` updated with new public functions

## References

- FR-007: resolve_action_sequence dispatch chain
- FR-009: custom mission types + UnknownMissionTypeError with registered_ids
- data-model.md §"New Public APIs"
- research.md §"Research Task 2" — Literal removal impact
- contracts/action-sequence-dispatch-contract.md

## Activity Log

- 2026-05-30T20:09:13Z – claude:sonnet:python-pedro:implementer – shell_pid=3223825 – Assigned agent via action command
- 2026-05-30T20:22:58Z – claude:sonnet:python-pedro:implementer – shell_pid=3223825 – Ready for review: T029-T035 complete. Opened Literal to str, added UnknownMissionTypeError.registered_ids, implemented existing_mission_types() and resolve_action_sequence(), updated resolve_mission_type_governance() validation, added 30 tests (all passing). Lazy imports with graceful fallback for parallel WP development.
- 2026-05-30T20:24:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=3297273 – Started review via action command
