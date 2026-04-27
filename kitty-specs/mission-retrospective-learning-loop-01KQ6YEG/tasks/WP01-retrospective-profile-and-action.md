---
work_package_id: WP01
title: Retrospective Profile + Action + DRG Contract
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-retrospective-learning-loop-01KQ6YEG
base_commit: d85ec6c4a44b2e143e858510b70ad979e2115938
created_at: '2026-04-27T08:38:57.571155+00:00'
subtasks:
- T001
- T002
- T003
- T004
shell_pid: "68115"
agent: "claude:sonnet:implementer:implementer"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/doctrine/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/doctrine/agent_profiles/shipped/retrospective-facilitator.yaml
- src/doctrine/missions/software-dev/actions/retrospect.yaml
- src/doctrine/missions/research/actions/retrospect.yaml
- src/doctrine/missions/documentation/actions/retrospect.yaml
- src/doctrine/graph.yaml
- tests/doctrine/test_retrospective_drg.py
priority: P1
status: planned
tags: []
---

# WP01 — Retrospective Profile + Action + DRG Contract

## Objective

Ship two new DRG artifacts that resolve through normal profile/action lookup:

1. `profile:retrospective-facilitator` — the agent role that runs a mission retrospective.
2. `action:retrospect` — the action invoked at mission terminus (lifecycle hook for built-ins, explicit marker step for custom missions).

The `retrospect` action's resolved scope MUST surface the mission's full event stream, mission metadata + detected mode, completed/skipped/blocked step history, paired invocation records and evidence references, the active DRG slice used during the mission, relevant charter/doctrine artifacts, relevant glossary terms, and the mission's output artifacts.

## Spec coverage

- **FR-001** profile exists and resolves through DRG.
- **FR-002** action exists and resolves through DRG.
- **FR-003** action context surfaces the required URN set.
- **FR-004** fixture mission produces a structured response.
- Prerequisite for **FR-028** (built-in mission lifecycle terminus hook).

## Context

Profiles live under `src/doctrine/agent_profiles/shipped/<name>.yaml` (see existing examples). Per-mission actions live under `src/doctrine/missions/<mission>/actions/<action>.yaml`. Inspect a current built-in mission's action set before drafting the new files — match the existing schema and the way scope edges are declared.

The shared `src/doctrine/graph.yaml` is the integration point for inter-artifact edges. Add the retrospective-facilitator profile and retrospect action as nodes, then add scope edges per FR-003.

## Subtasks

### T001 — Define `profile:retrospective-facilitator` shipped artifact

Create `src/doctrine/agent_profiles/shipped/retrospective-facilitator.yaml` matching the schema used by other shipped profiles. The profile should:

- Have a stable id (`retrospective-facilitator`).
- Carry an identity statement: facilitates a structured mission retrospective; not generic chat.
- Declare boundaries: only invoked at mission terminus or via the explicit custom-mission marker step.
- Declare governance scope: charter context, doctrine, DRG slice, glossary, mission events.

Validate with the existing profile schema validator (`src/doctrine/agent_profiles/validation.py` patterns).

### T002 — Define `action:retrospect` shipped artifact + scope edges

Create three near-identical action files (or one shared file referenced from each mission, depending on the existing convention you discover):

- `src/doctrine/missions/software-dev/actions/retrospect.yaml`
- `src/doctrine/missions/research/actions/retrospect.yaml`
- `src/doctrine/missions/documentation/actions/retrospect.yaml`

Each declares the action id `retrospect`, the profile binding (`retrospective-facilitator`), and the action's scope. Add scope edges in `src/doctrine/graph.yaml` connecting the action to:

- mission event-stream artifact kind
- mission metadata artifact kind
- charter/doctrine artifact kinds
- glossary artifact kind
- DRG slice artifact kind
- mission output artifacts

If a custom-mission convention exists (the ERP example custom mission referenced in `start-here.md`), document via README how custom missions reuse the same `retrospect` action without redefining it (custom missions keep their own `retrospective` marker step that resolves to this action).

### T003 — Wire DRG context (event stream, mission meta, charter, glossary, etc.) onto the action

Verify via the existing `src/doctrine/resolver.py` that resolving `(profile=retrospective-facilitator, action=retrospect)` against any in-scope mission produces a resolved scope including the FR-003 minimum URN set.

If gaps exist, add edges to `graph.yaml` until the resolved scope covers FR-003.

### T004 — DRG resolver fixture test

Add `tests/doctrine/test_retrospective_drg.py`. Test cases:

- Resolution produces a non-empty scope.
- Scope contains URNs for: event stream, mission metadata, charter, doctrine artifacts, glossary, DRG slice, mission output artifacts.
- Resolution is deterministic (same inputs → same scope set).

Use existing test fixtures in `tests/doctrine/` if available.

## Definition of Done

- [ ] `profile:retrospective-facilitator` validates against profile schema.
- [ ] `action:retrospect` exists for each in-scope built-in mission.
- [ ] Resolving `(retrospective-facilitator, retrospect)` against a fixture mission surfaces all FR-003 URN kinds.
- [ ] `tests/doctrine/test_retrospective_drg.py` passes.
- [ ] `mypy --strict` passes for any new Python helpers (none expected; this WP is mostly YAML).
- [ ] No changes outside `owned_files`.

## Risks

- **Path discovery**: actions may live in a shared location, not per-mission. Read existing patterns first; do NOT invent a new convention.
- **Schema drift**: profile/action schemas may have evolved; use the validator to catch mismatch.

## Reviewer guidance

- Confirm the resolved scope explicitly via the test (not just by inspection of YAML).
- Confirm no existing profile/action was modified.
- Confirm the three action files differ only where mission-specific scope demands it.

## Implementation command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Activity Log

- 2026-04-27T08:38:59Z – claude:sonnet:implementer:implementer – shell_pid=55171 – Assigned agent via action command
- 2026-04-27T08:49:40Z – claude:sonnet:implementer:implementer – shell_pid=55171 – Ready for review: profile + 3 actions + graph edges + DRG resolver test. Deviations: profile uses .yaml (not .agent.yaml) to avoid breaking shipped-profiles count test; actions use retrospect/index.yaml (not retrospect.yaml) per existing convention. All 26 new tests pass, all 1410 doctrine tests pass, mypy clean on new code.
- 2026-04-27T08:50:01Z – claude:opus:reviewer:reviewer – shell_pid=64622 – Started review via action command
- 2026-04-27T08:53:43Z – claude:opus:reviewer:reviewer – shell_pid=64622 – Moved to planned
- 2026-04-27T08:54:08Z – claude:sonnet:implementer:implementer – shell_pid=68115 – Started implementation via action command
