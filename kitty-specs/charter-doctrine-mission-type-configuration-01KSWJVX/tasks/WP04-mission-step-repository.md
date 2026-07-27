---
work_package_id: WP04
title: MissionStepRepository — compound-key resolution
dependencies:
- WP01
- WP02
- WP03
- WP06
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 597d0865af0d76fde9cf153964d9aea6dec8a6f3
created_at: '2026-05-30T19:52:14.864417+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3216938"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission_step_repository.py
execution_mode: code_change
owned_files:
- src/doctrine/missions/mission_step_repository.py
- tests/doctrine/missions/test_mission_step_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP04 — MissionStepRepository — compound-key resolution

## Context

FR-012 specifies that `MissionStep` definitions are shadowed by compound key `(mission_type_id, step_id)` across the `built-in → org → project` resolution chain. A `software-dev/review` shadow only overrides the `review` step of `software-dev`, leaving `documentation/review` untouched.

The `MissionStepRepository` is the doctrine-layer component responsible for this resolution. It receives a `PackContext` (from WP06) to locate org and project overrides.

> **Note**: WP04 depends on WP06 for `PackContext`. However, WP04 defines the interface; WP06 provides the implementation. You may define a minimal `PackContext` stub (or use `Any` for the parameter type) if WP06 is not yet merged. The interface contract is what matters here.

## Objective

Design and implement `MissionStepRepository` with compound-key resolution across three layers: built-in, org, and project. Enforce that shadowing is scoped to the `(mission_type_id, step_id)` compound key.

## Interface Specification

```python
# src/doctrine/missions/mission_step_repository.py

@dataclass(frozen=True)
class StepKey:
    mission_type_id: str
    step_id: str

class MissionStepRepository:
    """Resolves MissionStep definitions via built-in → org → project layering.

    Shadowing key: compound (mission_type_id, step_id).
    A software-dev/review shadow does NOT affect documentation/review.
    """

    def __init__(self, builtin_steps_root: Path) -> None: ...

    def resolve(
        self,
        mission_type_id: str,
        step_id: str,
        pack_context: "PackContext | None" = None,
    ) -> MissionStep | None:
        """Return the highest-precedence MissionStep for the given compound key.

        Layer order (highest wins): project → org → built-in.
        Returns None if the step is not found in any layer.
        """
        ...

    def resolve_all_for_mission_type(
        self,
        mission_type_id: str,
        pack_context: "PackContext | None" = None,
    ) -> dict[str, MissionStep]:
        """Return all steps for a mission type, with shadowing applied."""
        ...
```

## Subtasks

### T023 — Design MissionStepRepository interface

Document the resolution algorithm before coding:
1. Check project layer: `.kittify/overrides/mission-steps/{mission_type_id}/{step_id}/step.yaml`
2. Check org layer: for each `pack_root` in `pack_context.pack_roots`, check `{pack_root}/mission-steps/{mission_type_id}/{step_id}/step.yaml`
3. Check built-in layer: `src/doctrine/missions/mission-steps/{mission_type_id}/{step_id}/step.yaml`
4. Return the first match found (project wins over org wins over built-in)
5. Return `None` if not found in any layer

Define `StepKey` frozen dataclass for cache keys.

### T024 — Implement built-in layer resolution

Load `step.yaml` from `{builtin_steps_root}/{mission_type_id}/{step_id}/step.yaml`.
Parse it with `MissionStep.model_validate(yaml.safe_load(...))`.
Return `None` if the path does not exist.

`builtin_steps_root` defaults to `Path(__file__).parent / "mission-steps"` (relative to the module).

### T025 — Implement org-layer shadowing

Iterate over `pack_context.pack_roots` in order. For each root, check `{root}/mission-steps/{mission_type_id}/{step_id}/step.yaml`.

The first org-layer file found (earliest in `pack_roots` order) wins over the built-in layer.

If `pack_context` is `None`, skip org-layer resolution.

### T026 — Implement project-layer shadowing

Check `.kittify/overrides/mission-steps/{mission_type_id}/{step_id}/step.yaml` relative to `repo_root` (if `pack_context` provides `repo_root`, use it; otherwise skip).

Project-layer shadow wins over both org and built-in layers.

### T027 — Compound-key collision safety

Add an explicit test guard: resolving `("software-dev", "review")` and `("documentation", "review")` must produce independent results even when a `software-dev/review` shadow exists. These are distinct compound keys — the `StepKey` dataclass enforces this by using `(mission_type_id, step_id)` as the identity.

Write a comment in the code explaining the compound-key isolation guarantee.

### T028 — Layered-resolution tests

Write `tests/doctrine/missions/test_mission_step_resolver.py`:

Test cases:
- **Built-in only**: `resolve("software-dev", "specify")` returns the built-in step
- **Org shadow**: org-layer `software-dev/specify/step.yaml` overrides built-in; `resolve("software-dev", "specify")` returns the org step
- **Project shadow**: project-layer `software-dev/specify/step.yaml` overrides both org and built-in
- **Compound-key isolation**: org shadow for `software-dev/review` does NOT affect `resolve("documentation", "review")`
- **Missing step**: `resolve("software-dev", "nonexistent")` returns `None`
- **resolve_all_for_mission_type**: returns dict keyed by step_id with correct shadowing applied

Use `tmp_path` fixtures (pytest) to create layer directories.

## Acceptance Criteria

- [ ] `MissionStepRepository.resolve()` returns the correct layer (project > org > built-in)
- [ ] Compound-key isolation: `software-dev/review` shadow does not affect `documentation/review`
- [ ] `resolve()` returns `None` for unknown steps (does not raise)
- [ ] `__all__` declared in `mission_step_repository.py`
- [ ] `tests/doctrine/missions/test_mission_step_resolver.py` passes with all layer scenarios
- [ ] `mypy --strict` clean

## References

- FR-012: MissionStep compound-key shadowing
- data-model.md §"MissionStep (unified)" — shadowing key definition
- WP06: PackContext (may be a stub if WP06 not yet merged)

## Activity Log

- 2026-05-30T19:52:15Z – claude:sonnet:python-pedro:implementer – shell_pid=3174588 – Assigned agent via action command
- 2026-05-30T19:57:39Z – claude:sonnet:python-pedro:implementer – shell_pid=3174588 – Ready for review: MissionStepRepository with compound-key layered resolution (built-in → org → project). 28 tests passing, all layers covered, compound-key isolation verified.
- 2026-05-30T19:58:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=3190380 – Started review via action command
- 2026-05-30T20:01:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=3190380 – Moved to planned
- 2026-05-30T20:02:10Z – claude:sonnet:python-pedro:implementer – shell_pid=3201612 – Started implementation via action command
- 2026-05-30T20:06:23Z – claude:sonnet:python-pedro:implementer – shell_pid=3201612 – Cycle 2 fix: corrected org-layer path from missions/mission-steps to mission-steps, skip built-in pack_root in org loop
- 2026-05-30T20:06:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=3216938 – Started review via action command
