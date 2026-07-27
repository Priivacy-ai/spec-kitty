---
work_package_id: WP03
title: Software-dev step data — author order/membership + template refs
dependencies:
- WP01
- WP02
requirement_refs:
- FR-001
- FR-014
tracker_refs: []
planning_base_branch: feat/mission-step-authority
merge_target_branch: feat/mission-step-authority
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-authority unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
phase: Phase 2 - Data
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1221167"
shell_pid_created_at: "1784231380.26"
history:
- at: '2026-07-16T17:35:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission-steps/software-dev/
create_intent:
- tests/doctrine/missions/test_softwaredev_roundtrip.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/mission-steps/software-dev/**
- tests/doctrine/missions/test_softwaredev_roundtrip.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Software-dev step data

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for `python-pedro` (`implementer`, `claude`).

---

## Objective

Author the relocated order/membership + template references onto software-dev's **12** existing `step.yaml`
files, so the projection (WP02) reproduces today's authored `action_sequence` + `template_set` **byte-for-byte**.
This is the parity substrate for NFR-001a. Depends on WP01 (fields) + WP02 (projection).

## Context (grounded)
- `mission-steps/software-dev/` has 12 step dirs: `specify, plan, tasks, implement, review, accept, analyze, charter, research, tasks-outline, tasks-finalize, tasks-packages`.
- Today's authored `action_sequence` (`mission_types/software-dev.yaml`) = **`[specify, plan, tasks, implement, review]`** (5 of 12).
- Today's `template_set` = `{spec: spec-template.md, plan: plan-template.md}`.

## Subtasks

### T009 — sequence_index + in_action_sequence on 12 step.yaml
- The **5 in-sequence** steps: `specify`(sequence_index 0), `plan`(1), `tasks`(2), `implement`(3), `review`(4), each `in_action_sequence: true`.
- The **7 others** (`accept, analyze, charter, research, tasks-outline, tasks-finalize, tasks-packages`): `in_action_sequence: false`, `sequence_index: null`. (They keep their `scope` edges → stay non-orphan, D5.)

### T010 — template refs + round-trip test
- Add `template:` `(artifact_key, template_file)` to the `specify` step (`{spec, spec-template.md}`) and `plan` step (`{plan, plan-template.md}`), referencing the **existing** template files (a reference to existing files = structure, not content — within C-004). Leave the other 10 steps' `template` null.
- `tests/doctrine/missions/test_softwaredev_roundtrip.py`: assert `project_action_sequence(sw-dev steps) == ["specify","plan","tasks","implement","review"]` and `project_template_set(...) == {"spec":"spec-template.md","plan":"plan-template.md"}` — **byte-for-byte** vs the pre-mission authored values (NFR-001a).

## Branch Strategy
Base/merge: `feat/mission-step-authority`. Implement: `spec-kitty agent action implement WP03 --agent <name>`.

## Definition of Done
- [ ] 12 step.yaml carry correct `sequence_index`/`in_action_sequence`; only the 5 in-sequence steps flagged true.
- [ ] `specify`/`plan` carry the template refs to existing files; others null.
- [ ] Round-trip test proves byte-for-byte parity of the projected `action_sequence` + `template_set` (NFR-001a).
- [ ] `regenerate-graph --check` fresh (data-only; no graph change yet — extractor still reads YAML until WP04).
- [ ] `ruff`/`mypy` clean where applicable.

## Risks / Reviewer guidance
- Order MUST match the authored sequence exactly — a wrong `sequence_index` silently reorders `action_sequence`. Reviewer diff-checks against `mission_types/software-dev.yaml`.
- Do not invent template refs for steps that have none today.

## Requirements: FR-001, FR-014

## Activity Log

- 2026-07-16T19:44:10Z – claude:sonnet:python-pedro:implementer – shell_pid=1195962 – Assigned agent via action command
- 2026-07-16T19:49:08Z – claude:sonnet:python-pedro:implementer – shell_pid=1195962 – 12 sw-dev step.yaml annotated (5 in-sequence); template refs on specify/plan; round-trip parity green; graph fresh
- 2026-07-16T19:49:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=1221167 – Started review via action command
- 2026-07-16T19:52:29Z – user – shell_pid=1221167 – Review passed: 5 in-sequence steps carry in_action_sequence:true with sequence_index specify=0/plan=1/tasks=2/implement=3/review=4 (matches authored mission_types/software-dev.yaml action_sequence exactly); 7 non-sequence steps carry in_action_sequence:false + sequence_index:null with depends_on/scope edges unchanged (additions-only diff); specify->{spec,spec-template.md} and plan->{plan,plan-template.md} reference existing template files, other 10 template null. LIVE PROJECTION: independently loaded MissionTypeRepository.default().get('software-dev') and confirmed action_sequence==['specify','plan','tasks','implement','review'] and template_set=={'spec':'spec-template.md','plan':'plan-template.md'} byte-for-byte vs authored YAML (NFR-001a live via WP02 injection). Round-trip test invokes real production paths (not synthetic). Gates: 350 doctrine/missions tests pass, ruff clean, mypy --strict clean, regenerate-graph --check fresh. Scope=12 step.yaml + 1 test only.
