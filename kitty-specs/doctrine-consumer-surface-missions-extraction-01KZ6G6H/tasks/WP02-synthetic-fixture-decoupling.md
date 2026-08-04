---
work_package_id: WP02
title: Synthetic-fixture decoupling + daphne cleanup
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: research/doctrine-wheel-mission-types-public-api
merge_target_branch: research/doctrine-wheel-mission-types-public-api
branch_strategy: Planning artifacts for this mission were generated on research/doctrine-wheel-mission-types-public-api. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/doctrine-wheel-mission-types-public-api unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Gate preconditions
history:
- at: '2026-08-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_no_dead_doctrine_paths.py
- packs/built-in/agent_profiles/doctrine-daphne.agent.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Synthetic-fixture decoupling + daphne cleanup

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Issue #3036 documents a real gate/rule contradiction: `test_forbidding_mention_would_false_red_without_its_discriminator` (in WP01's narrowed Gate-C module) currently **requires** a repo-local reference to exist in shipped doctrine content, when the "Shippable doctrine" rule says built-in content must be valid with no access to this repo's source tree. Issue #3036's own tracker comment (2026-07-28, stijn-dejongh) **explicitly rejects** "loosen the assertion to tolerate zero" as the fix — read that comment before starting (`gh issue view 3036 --comments`).

This WP is done when:
- The discriminator proof is redriven from a `tmp_path`-planted synthetic fixture, not the live shipped artifact.
- The proof still catches a real planted violation (the anti-widening property is preserved — a discriminator that can't fail proves nothing).
- `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml`'s `avoidance-boundary` no longer mentions `src/doctrine/graph.yaml` (line 136 today), and the gate suite is green with that removal in place.

## Context & Constraints

Read `spec.md` (FR-002, User Story 2/AS2-AS3), `research.md` (R2), `contracts/architectural-gates.md`, and issue #3036's full comment thread before starting.

**This repo already has the exact idiom you need**, in the same file (now WP01's module): `test_gate_a_rejects_a_planted_violation` and `test_gate_b_rejects_a_planted_violation` both construct a `tmp_path` fixture and assert the gate reds against it. Follow that established local pattern — do not invent a new mechanism.

**The literal-compliance trap to avoid**: deleting the proof test entirely (rather than redesigning it) technically "stops it from failing" but proves nothing — this is exactly the "gate that can't fail" regression the mission exists to prevent. Your fixture-based proof must still demonstrably catch a planted violation.

`packs/built-in/agent_profiles/doctrine-daphne.agent.yaml` — **note this is the current path**; the file was relocated from `src/doctrine/agent_profiles/built-in/` by an earlier, already-merged mission. Don't be misled by an older reference to the pre-relocation path if you encounter one elsewhere in the codebase.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### T006 – Design and implement the planted synthetic fixture

- **Purpose**: Decouple "the discriminator is provable" from "shipped doctrine must carry a repo-local path forever."
- **Steps**: Following the `test_gate_a_rejects_a_planted_violation` idiom, construct a `tmp_path` fixture carrying a forbidding-mention string. Design it so the discriminator's effect-set pin still runs meaningfully against it.
- **Files**: WP01's narrowed Gate-C module.
- **Parallel?**: No — foundation for T007/T008.

### T007 – Redrive the discriminator proof against the fixture

- **Purpose**: Replace the live-artifact dependency with the fixture from T006.
- **Steps**: Rewrite `test_forbidding_mention_would_false_red_without_its_discriminator` to assert against the planted fixture instead of `doctrine-daphne.agent.yaml`. Preserve the anti-widening property: an unexpected new exclusion in the fixture must still be a visible diff.
- **Files**: WP01's narrowed Gate-C module.
- **Parallel?**: No.

### T008 – Apply the same treatment to Gate C's cross-link case

- **Purpose**: The on-disk-resolution requirement has the same "must exist forever" shape for legitimately-external links.
- **Steps**: Apply the fixture-decoupling principle to whatever Gate C's cross-link discriminator currently pins against live content, so a relative link legitimately pointing outside the built-in-doctrine package boundary can be exempted rather than perpetually required to resolve.
- **Files**: WP01's narrowed Gate-C module.
- **Parallel?**: Can run alongside T007.

### T009 – The daphne cleanup

- **Purpose**: Perform the content cleanup the fixture decoupling enables.
- **Steps**: Remove the `src/doctrine/graph.yaml` mention from `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml`'s `avoidance-boundary` field (verify the exact current line before editing — it was line 136 as of planning).
- **Files**: `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml`.
- **Parallel?**: No — depends on T007 landing first (the live assertion must no longer require this reference before it's safe to remove).

### T010 – Verify

- **Purpose**: Prove both halves of SC-006.
- **Steps**: Run the full gate suite with the daphne cleanup applied (must be green). Separately, plant a violation against the new fixture and confirm the gate still reds (the anti-widening proof).
- **Files**: n/a (verification).
- **Parallel?**: No — final gate.

## Test Strategy

```bash
PYTHONPATH=src python -m pytest tests/architectural/ -k "forbidding_mention or cross_link" -q
```

## Risks & Mitigations

- **Risk**: Loosening the live assertion instead of decoupling it — the explicitly rejected remedy. **Mitigation**: re-read issue #3036's comment before writing any code; if you find yourself writing `assert excluded == []` as a permanent tolerance, stop.
- **Risk**: A fixture-based proof that doesn't actually exercise the same discriminator logic. **Mitigation**: T010's planted-violation check is the falsification test — do not skip it.

## Review Guidance

- Confirm the reviewer independently re-derives that a planted violation still reds the gate (T010) — do not accept "tests pass" alone as proof of the anti-widening property.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append new entries at the end.

- 2026-08-04T15:30:00Z – system – Prompt created.
