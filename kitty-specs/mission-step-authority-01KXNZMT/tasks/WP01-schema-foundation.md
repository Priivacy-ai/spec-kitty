---
work_package_id: WP01
title: Schema foundation — MissionStep fields + MissionType projection-ready
dependencies: []
requirement_refs:
- FR-001
- FR-006
- FR-007
- FR-014
tracker_refs: []
planning_base_branch: feat/mission-step-authority
merge_target_branch: feat/mission-step-authority
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-authority unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Schema
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1054539"
shell_pid_created_at: "1784227974.41"
history:
- at: '2026-07-16T17:35:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent:
- tests/doctrine/missions/test_step_schema.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/models.py
- src/doctrine/missions/mission_step_repository.py
- tests/doctrine/missions/test_step_schema.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Schema foundation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objective

Extend the step authority (`MissionStep`) with the fields the projection needs, and make `MissionType`
projection-ready — all inside the single owner of `src/doctrine/missions/models.py`. **No other WP touches
`models.py`** (finalize rejects owned_files overlap). This is the foundation; WP02 (seam), WP03 (sw-dev data),
WP05 (unify), WP08 (offer) all depend on it.

Read first: [plan.md](../plan.md) "Post-Plan Squad Refinements", [data-model.md](../data-model.md), and
`src/doctrine/missions/models.py:87` (`MissionStep`) + `:149-202` (`MissionType`).

## Context

- `MissionStep` (`models.py:87`) is `frozen`, `extra="forbid"`. New fields not registered in
  `_STEP_YAML_TO_MODEL` (`mission_step_repository.py:120`) are **silently stripped** — a test can pass while a
  field vanishes. This is the #1 trap.
- `action_sequence` encodes order + membership that today lives only in `mission_types/*.yaml`. We relocate it
  onto the step so the projection (WP02) can derive it.
- `recommended_role` **reuses the existing `agent_profile`** — do NOT add a redundant field.

## Subtasks

### T001 — Add MissionStep fields (prompt_template STAYS required)
Add to `MissionStep` (`models.py:87`):
- `sequence_index: int | None` — position in the ordered sequence (`None` when not in sequence).
- `in_action_sequence: bool` — membership in the ordered sequence (default `False`).
- `recommended_model_tier: str | None = None` — advisory model-tier **offer** (net-new).
- `template: <ref> | None = None` — carries `(artifact_key, template_file)` (a small frozen model or a tuple field). software-dev's `specify`/`plan` will reference existing template files; 3 types stay null.
- **Do NOT touch `prompt_template`** — it stays a required `str`. (Missing prompts are handled in WP05 by seeding blank files, not by relaxing the schema.)

### T002 — Register new fields in `_STEP_YAML_TO_MODEL`
In `mission_step_repository.py:120`, add every new field's YAML→model key mapping so `extra="forbid"` does not
strip them. Verify the alias handling matches the existing `agent-profile`→`agent_profile` pattern.

### T003 — MissionType absence-tolerant + relocate the validator
- Make `MissionType.action_sequence` / `template_set` (`models.py:183-184`) **absence-tolerant** (Optional / default), so removing them from the YAML (WP07) does not fail `model_validate`. During the transition they stay present and populated from YAML — only the *requiredness* relaxes.
- **Relocate `_validate_action_sequence`** (`models.py:197`, non-empty + unique) so the invariant asserts on the **projected** value, not the raw field. (WP02 re-asserts it on the projection — this is the WP01→WP02 contract; do not drop the invariant.)

### T004 — Field-round-trip test
`tests/doctrine/missions/test_step_schema.py`: load a `MissionStep` YAML carrying all new fields through the repo
and assert every field survives (guards the `extra="forbid"` strip). Assert `prompt_template` is still required.
Assert `MissionType` loads with and without `action_sequence`/`template_set`.

## Branch Strategy

Planning base / merge target: `feat/mission-step-authority` (stacked on the S-A commit). Execution worktree is
allocated per the computed lane in `lanes.json`. Implement: `spec-kitty agent action implement WP01 --agent <name>`.

## Definition of Done
- [ ] All 4 new MissionStep fields present + registered in `_STEP_YAML_TO_MODEL`; `prompt_template` unchanged.
- [ ] `MissionType` loads with the flat fields absent; `_validate_action_sequence` invariant relocated to the projection surface.
- [ ] Field-round-trip test green (proves no `extra="forbid"` strip).
- [ ] `ruff` + `mypy --strict` clean, zero new suppressions; complexity ≤15.
- [ ] `spec-kitty doctrine regenerate-graph --check` still fresh (schema-only change, no graph impact yet).

## Risks / Reviewer guidance
- The `extra="forbid"` strip is silent — reviewer must confirm T002 registration, not just the model fields.
- Do NOT make `prompt_template` optional (operator directive; DD-06). Do NOT add a `recommended_role` field (reuse `agent_profile`).
- `recommended_model_tier` has no consumer yet — that's WP08. Here it's schema only.

## Requirements: FR-001, FR-006, FR-007, FR-014

## Activity Log

- 2026-07-16T18:44:18Z – claude:sonnet:python-pedro:implementer – shell_pid=1034096 – Assigned agent via action command
- 2026-07-16T18:52:18Z – claude:sonnet:python-pedro:implementer – shell_pid=1034096 – Schema fields + allowlist + validator relocation + round-trip test; ruff/mypy clean; graph fresh
- 2026-07-16T18:52:56Z – claude:opus:reviewer-renata:reviewer – shell_pid=1054539 – Started review via action command
- 2026-07-16T19:04:57Z – user – shell_pid=1054539 – Review passed: all 4 MissionStep fields registered in _STEP_YAML_TO_MODEL; round-trip test loads THROUGH MissionStepRepository.resolve (real strip guard, not synthetic); prompt_template stays required str (DD-06); no recommended_role (reuses agent_profile); action_sequence/template_set absence-tolerant; validate_action_sequence relocated to module level (exported for WP02) and still fires on raw field while present. Scope=only models.py+mission_step_repository.py+test_step_schema.py. Gates: 327 doctrine tests pass, ruff clean, mypy --strict clean, graph fresh. Coordination note: repaired mission issue-matrix.md (non-canonical schema+verdicts were blocking approval) to canonical columns+verdicts for all 9 spec-referenced issues; #2723 in-mission, #2712 verified-already-fixed, rest deferred-with-followup with spec.md C-004/C-005 handles; transcribed from spec not invented; matrix is review-gating only (no auto-close).
