---
work_package_id: WP04
title: Tiered-standards styleguide + DRG edge (doctrine-only)
dependencies: []
requirement_refs:
- FR-010
- FR-011
tracker_refs: []
subtasks:
- T016
- T017
- T018
- T019
phase: Phase 1 - Thread C
assignee: ''
agent: claude
history:
- at: '2026-06-23T09:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/styleguides/built-in/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/styleguides/built-in/tiered-standards.styleguide.yaml
- src/doctrine/graph.yaml
- tests/doctrine/drg/test_tiered_standards_non_orphan.py
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Tiered-standards styleguide + DRG edge

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter before parsing the rest of this prompt.

- **Profile**: `doctrine-daphne`
- **Role**: `curator`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Give the DDD tiered coding standard a canonical, **non-orphan** home in doctrine — the bounded doctrine-only slice of #1843 (tracked as child #2096). NO CI gates, NO agent-effort routing (C-001).

**Done when:** a `styleguide` artifact defines core-vs-glue tiers mapped to **named existing `src/` areas** with a per-tier rigour table; it has ≥1 inbound DRG edge (non-orphan); `graph.yaml` is regenerated via the generator; a test asserts non-orphan status.

## Context

- Spec FR-010/011, SC-005, C-001/C-004. Research D-4. Child issue #2096 (parent #1843).
- The #1843 epic body defines the taxonomy direction (core / supporting / generic / experimental) and an illustrative repo tier map (e.g. `commit_guard`, `mission_runtime/*`, `status/*` reducer+store, DRG/merge = core; CLI shells, render helpers = supporting; scripts/, demos = generic/experimental). Use that as the seed — map to **real** current `src/` areas.
- Generator: `spec-kitty doctrine regenerate-graph [--check]`. Styleguides auto-discovered from `styleguides/built-in/**`. Orphan nodes ARE permitted by the graph → an inbound edge is required to be meaningful (squad finding).
- Freshness/smoke test: `tests/doctrine/drg/test_shipped_graph_valid.py`.

## Subtasks & Detailed Guidance

### T016 — Author the styleguide [P]
- Create `src/doctrine/styleguides/built-in/tiered-standards.styleguide.yaml` following the schema of an existing styleguide (e.g. `python-implementation.styleguide.yaml`). Define tiers (≥ core, glue) mapped to **named existing `src/` packages**, and a per-tier rigour table (coverage / duplication / smell / lint / typing). **Do NOT** declare `applies_to_languages: [any]`/`[all]` (would trip Thread D / #2092 — omit the field for always-applicable).

### T017 — Inbound DRG edge [P]
- Add at least one `suggests`/`requires` edge **to** the new styleguide from an existing directive or paradigm (doctrine-only — a `suggests` edge is not CI/agent-effort). Editing one existing directive/paradigm YAML to add the edge is an expected, justified out-of-map edit; record the one-line rationale. Prefer a directive about code quality/rigour as the source.

### T018 — Regenerate graph [P]
- Run `spec-kitty doctrine regenerate-graph` and commit the regenerated `src/doctrine/graph.yaml`. Do NOT hand-edit `graph.yaml` (C-004). Run `regenerate-graph --check` to confirm freshness.

### T019 — Non-orphan test [P]
- Add `tests/doctrine/drg/test_tiered_standards_non_orphan.py` asserting the styleguide node exists in the graph AND has ≥1 inbound edge (not an orphan). This is the non-fakeable anchor (SC-005).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}
- Parallel lane. `graph.yaml` regen is a single-writer step — this is the only WP touching it.

## Definition of Done

- [ ] Styleguide exists; tiers map to named real `src/` areas; rigour table present.
- [ ] ≥1 inbound DRG edge; `graph.yaml` regenerated via generator; `regenerate-graph --check` clean.
- [ ] Non-orphan test green; `test_shipped_graph_valid.py` green.
- [ ] No CI/agent-effort change (C-001).

## Risks & Reviewer Guidance

- **Risk**: an orphan stub or abstract tiers = doctrine theater. **Reviewer**: confirm the inbound edge resolves, the test fails if the edge is removed, and the tiers name real packages. Confirm no `[any]`/`[all]` language scope.
