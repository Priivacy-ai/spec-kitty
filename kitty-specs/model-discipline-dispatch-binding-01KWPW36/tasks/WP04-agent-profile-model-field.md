---
work_package_id: WP04
title: Agent-profile model/effort field
dependencies: []
requirement_refs:
- FR-005
- NFR-003
- C-005
tracker_refs:
- '2364'
planning_base_branch: design/model-discipline-dispatch-2364
merge_target_branch: design/model-discipline-dispatch-2364
branch_strategy: Planning artifacts for this mission were generated on design/model-discipline-dispatch-2364. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/model-discipline-dispatch-2364 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-model-discipline-dispatch-binding-01KWPW36
base_commit: 4053c73530e864fadad988c37be9822ad7dff2b7
created_at: '2026-07-04T17:21:13.765790+00:00'
subtasks:
- T018
- T019
- T020
- T021
- T022
phase: Phase 1 - Implementation
assignee: ''
agent: "claude"
shell_pid: '553107'
history:
- at: '2026-07-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/agent_profiles/
create_intent:
- tests/doctrine/test_agent_profile_model_field.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/agent_profiles/profile.py
- src/doctrine/agent_profiles/schema_models.py
- src/doctrine/schemas/agent-profile.schema.yaml
- tests/doctrine/test_agent_profile_model_field.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Agent-profile model/effort field

## Load Agent Profile (python-pedro)

Use the `/ad-hoc-profile-load` skill to load the `python-pedro` agent profile (role: `implementer`) before doing any work, and behave according to its guidance while executing this prompt.

## Objectives & Success Criteria

- Add an optional per-profile `model`/`effort` field that reaches the WP02 evaluator: a profile declaring `model` exposes it on the loaded `AgentProfile` object (not dropped by `extra='ignore'`).
- An existing profile without the field validates unchanged (NFR-003, back-compat).
- No dependencies — this WP is a foundation; it is consumed by WP02.

## Context & Constraints

- Source of truth: `kitty-specs/model-discipline-dispatch-binding-01KWPW36/spec.md` FR-005, NFR-003, C-005; `plan.md` IC-04; `tasks.md` WP04 section; `adversarial-review.md` Round 2 fold #2.
- **Load-bearing trap — domain model, not schema-only**: the field MUST land on the `profile.py` DOMAIN model (`AgentProfile`), with a kebab alias mirroring `routing_priority` (`profile.py:264`). A schema-only add is a silent no-op — `extra='ignore'` drops any field not declared on the Pydantic model itself.
- **Load-bearing trap — generated schema discipline**: add the field to `schema_models.py` (the schema SOURCE) and REGENERATE `src/doctrine/schemas/agent-profile.schema.yaml`. Never hand-edit the `.yaml` — it is generated.
- **Load-bearing trap — protected namespace, pinned deterministically**: the Python attribute name is EXACTLY `preferred_model: str | None = Field(default=None, alias="model")` and `effort: str | None = Field(default=None, alias="effort")` on `AgentProfile` in `profile.py`. `preferred_model` avoids Pydantic v2's `model_` protected namespace entirely; the YAML author writes `model:`/`effort:` (aliases). This is the fixed contract — no conditional "if a warning appears" branching.
- Keep `ruff`/`mypy` clean; complexity ≤ 15.

## Subtasks

- [ ] T018 [red-first] `tests/doctrine/test_agent_profile_model_field.py`: a YAML profile with `model:`/`effort:` → the value is present on the loaded `AgentProfile` (proves it reaches the domain model); a profile without it loads unchanged (NFR-003). RECORD pre-fix RED (field dropped today).
- [ ] T019 [FR-005] add optional fields to `AgentProfile` in `src/doctrine/agent_profiles/profile.py`: EXACTLY `preferred_model: str | None = Field(default=None, alias="model")` and `effort: str | None = Field(default=None, alias="effort")` (mirror the `routing_priority` alias pattern, :264); `preferred_model` avoids Pydantic v2's `model_` protected namespace deterministically — no conditional aliasing.
- [ ] T020 [FR-005] add the field to `src/doctrine/agent_profiles/schema_models.py` (schema source) and REGENERATE `src/doctrine/schemas/agent-profile.schema.yaml` (do not hand-edit).
- [ ] T021 [NFR-003] back-compat: existing profiles load; schema parity test green.
- [ ] T022 `ruff`/`mypy` clean; complexity ≤ 15.

## Branch Strategy

- **Strategy**: Planning artifacts are generated on design/model-discipline-dispatch-2364; completed changes merge back there.
- **Planning base branch**: `design/model-discipline-dispatch-2364`
- **Merge target branch**: `design/model-discipline-dispatch-2364`

## Definition of Done

- [ ] T018 recorded RED pre-fix (field dropped today), GREEN post-implementation.
- [ ] `AgentProfile` in `profile.py` carries `preferred_model` (alias `model`) and `effort` (alias `effort`), both `str | None = Field(default=None, ...)`; a declared value is observable on the loaded object.
- [ ] `schema_models.py` updated and `agent-profile.schema.yaml` regenerated from it (not hand-edited).
- [ ] Existing profiles without the field load unchanged; schema parity test green.
- [ ] `ruff check` and `mypy` clean on owned files; complexity ≤ 15.
- [ ] No changes outside `owned_files`.

## Activity Log

- 2026-07-04T17:51:01Z – claude – shell_pid=553107 – Moved to for_review
- 2026-07-04T17:52:01Z – user – shell_pid=553107 – APPROVE (opus, uv-run): red-first genuine; field on domain model + schema exposes model/effort (fold verified); FR-028 drift cleaned.
