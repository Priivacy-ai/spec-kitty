---
work_package_id: WP02
title: Builder overlay seam (#3176) — reach .kittify/agent_profiles
dependencies: []
requirement_refs:
- FR-006
- FR-007
- NFR-002
planning_base_branch: m4-doctrine-delivery
merge_target_branch: m4-doctrine-delivery
branch_strategy: Planning artifacts for this mission were generated on m4-doctrine-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into m4-doctrine-delivery unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-deliver-loaded-doctrine-01M0DSQM
base_commit: 7fdec0995d96d8974343f64331a13be6b7d3647b
created_at: '2026-08-19T20:28:48.476645+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
history:
- Created by /spec-kitty.tasks (M4 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/charter/doctrine_service_builder.py
create_intent:
- tests/charter/test_builder_overlay_seam.py
execution_mode: code_change
owned_files:
- src/charter/doctrine_service_builder.py
- src/doctrine/service.py
- src/specify_cli/tool_surface/profiles/projection.py
- tests/charter/test_builder_overlay_seam.py
- tests/specify_cli/tool_surface/profiles/test_projection.py
role: implementer
tags: []
tracker_refs:
- '3176'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Thread an optional agent-profile overlay directory through the doctrine-service builders so a caller can point the project-profile overlay at `.kittify/agent_profiles`, then migrate `default_profile_repository` onto it and delete the carve-out — closing #3176.

- **SC (FR-006)**: `agent_profile_overlay_dir: Path | None = None` is threaded `build_activation_aware_doctrine_service` → `_build_activation_aware_doctrine_service` → `_build_doctrine_service` → `doctrine.service.DoctrineService`. Unset ⇒ byte-identical kwargs/behaviour (NFR-002).
- **SC (FR-007)**: a profile authored at `.kittify/agent_profiles/<id>.agent.yaml` stays visible through `default_profile_repository` (with `project` provenance) **after** the migration onto the factory+overlay seam; the C-002 carve-out docstring in `projection.py` is deleted. (The project-overlay assertions live in `test_projection.py` — e.g. `test_project_populates_manifest_source_provenance_for_project_profile`, `test_default_profile_repository_loads_builtins`, `test_diagnose_emits_profile_overlay_conflict` — they pass today via direct construction and must keep passing through the seam; they are not separate carved-out files.)
- **SC (C-006)**: only `_build_activation_aware_doctrine_service` constructs the activation-aware wrapper; the public builder stays a thin delegate; the service is always wrapped (R5).
- **SC (C-001/C-008)**: `charter` does not import `specify_cli`; `default_profile_repository` still merges org profiles via `resolve_activated_org_profiles` (the activation gate), not a raw `org_dirs` splice.

## Context & Constraints

Read `kitty-specs/deliver-loaded-doctrine-01M0DSQM/{spec.md,plan.md,research.md,data-model.md}` and `contracts/builder-overlay-contract.md`.

Current state (verified against `upstream/main`):
- `doctrine/service.py::DoctrineService.__init__` stores `project_root`/`org_roots`/`active_languages`. `agent_profiles` property builds `AgentProfileRepository(org_dirs=self._org_dirs("agent_profiles"), project_dir=self._project_dir("agent_profiles"), …)`. `_project_dir("agent_profiles")` returns `<doctrine-root>/agent_profiles` — **never** `.kittify/agent_profiles`.
- `charter/doctrine_service_builder.py`: `_build_doctrine_service(repo_root, *, org_roots=None)` constructs the raw `DoctrineService`; `_build_activation_aware_doctrine_service(repo_root, *, org_roots=None)` wraps it (the single wrapper body); `build_activation_aware_doctrine_service(repo_root)` is a thin delegate.
- `specify_cli/tool_surface/profiles/projection.py::default_profile_repository` (L80): builds `AgentProfileRepository(project_dir=project_root / ".kittify/agent_profiles")` directly, then `_merge_activated_org_profiles`. Its docstring (L94–125) documents WHY the factory migration was blocked — "no parameter on the factory's one sanctioned builder to point its inner project directory at an arbitrary caller-chosen path" — and names option (a) a builder-level override as the correct fix. This WP delivers option (a).

**Constraints**: default `None` byte-identical (NFR-002). Single-wrapper-body invariant (C-006). `charter` must not import `specify_cli` (C-001). Preserve C-008 activation-gated org merge. Zero `ruff`/`mypy --strict` suppressions (C-002). Red-first (C-003).

## Branch Strategy

Planning base **`m4-doctrine-delivery`**; final merge target **`m4-doctrine-delivery`** (single_branch topology). Execution worktrees are allocated per computed lane from `lanes.json`; do not hand-create branches. One PR to `main` lands the whole mission later.

## Subtasks & Detailed Guidance

### Subtask T008 – Red: project-overlay profile dropped through the factory
Write `tests/charter/test_builder_overlay_seam.py`: seed `.kittify/agent_profiles/<id>.agent.yaml` under a `tmp_path` repo; build `build_activation_aware_doctrine_service(tmp_path, agent_profile_overlay_dir=tmp_path / ".kittify/agent_profiles")` and assert the seeded profile is present in `.agent_profile_repository`. Also assert the **unset** call (`agent_profile_overlay_dir=None`) does NOT see it (byte-identical to today — it resolves the doctrine-root `agent_profiles`, not `.kittify/agent_profiles`). This must **fail** on `upstream/main` (no such parameter — `TypeError`), which is the red signal. Note the existing `test_projection.py` project-overlay tests pass today via `default_profile_repository`'s direct `AgentProfileRepository(project_dir=…)` construction; they are the regression guard that the seam migration (T011) must keep green — do not weaken them.

### Subtask T009 – DoctrineService honours the overlay dir
In `doctrine/service.py`: add `agent_profile_overlay_dir: Path | None = None` to `__init__` (store it). In the `agent_profiles` property, use `self._agent_profile_overlay_dir` as the `project_dir` when set, else `self._project_dir("agent_profiles")`. No other repository is affected. Keep the property cached. `mypy --strict` clean.

### Subtask T010 – Thread the param through both builders
In `charter/doctrine_service_builder.py`: add `agent_profile_overlay_dir: Path | None = None` to `_build_doctrine_service`, `_build_activation_aware_doctrine_service`, and the public `build_activation_aware_doctrine_service`. Pass it into the `DoctrineService(...)` construction in `_build_doctrine_service` **only when set** (mirror the `org_roots` "only pass when it carries a value" pattern so charter-internal callers see byte-identical kwargs — NFR-002). Preserve the single-wrapper-body invariant: the public builder stays a thin delegate to `_build_activation_aware_doctrine_service`; do not add a second wrapper construction site (C-006).

### Subtask T011 – Migrate default_profile_repository onto the seam
In `projection.py::default_profile_repository`: build the base repository through `build_activation_aware_doctrine_service(project_root, agent_profile_overlay_dir=project_root / _PROJECT_PROFILE_SUBDIR).agent_profile_repository` instead of `AgentProfileRepository(project_dir=…)` directly. Keep `_merge_activated_org_profiles` (the C-008 activation-gated org merge) unchanged. Delete the long "NOT migrated" carve-out docstring block (L94–125) and replace it with a concise note that the builder overlay seam now resolves `.kittify/agent_profiles`. Confirm `charter` is not imported into a cycle and that `projection.py` (in `specify_cli`) consuming the `charter` builder is the correct dependency direction (C-001).

### Subtask T012 – Green + byte-identical + strict types
- Make T008 pass and keep every existing `test_projection.py` project-overlay test green (the seam-migration regression guard).
- Add/keep an assertion that with `agent_profile_overlay_dir` unset, the constructed `DoctrineService` and its `agent_profiles` project dir are unchanged vs pre-mission (NFR-002).
- `mypy --strict src/charter src/doctrine` and `ruff check` clean on all three source files. Record subtasks: `spec-kitty agent tasks mark-status T008 T009 T010 T011 T012 --status done --mission deliver-loaded-doctrine-01M0DSQM`.

## Test Strategy
Red-first (T008 fails on base). Run targeted:
`PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/charter/test_builder_overlay_seam.py tests/specify_cli/tool_surface/profiles/test_projection.py -q`.
Then `mypy --strict src/charter src/doctrine` and `ruff check src/charter src/doctrine src/specify_cli/tool_surface/profiles`.

## Risks & Mitigations
- **Second wrapper construction site** (C-006 regression) → keep the public builder a thin delegate; only `_build_activation_aware_doctrine_service` wraps.
- **Bypassing the org activation gate** (C-008) → keep `_merge_activated_org_profiles`; do NOT add a raw `org_dirs` splice for agent profiles.
- **Non-byte-identical unset path** (NFR-002) → only pass the overlay kwarg when set; assert unchanged construction in T012.
- **Import-direction violation** (C-001) → the param lives in `charter`/`doctrine`; `specify_cli` consumes it. No `charter → specify_cli` import.

## Review Guidance
Verify: the overlay param defaults to `None` and is byte-identical unset; `.kittify/agent_profiles` profiles are visible via `default_profile_repository`; the `test_projection.py` project-overlay tests stay green with the code carve-out docstring deleted; single-wrapper-body preserved; C-008 org gate intact; `charter` does not import `specify_cli`; zero new suppressions; `mypy --strict` clean.

## Activity Log
- (implementer appends entries here)
