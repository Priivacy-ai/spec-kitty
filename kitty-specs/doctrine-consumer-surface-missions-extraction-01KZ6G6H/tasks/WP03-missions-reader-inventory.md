---
work_package_id: WP03
title: Cross-layer missions/ reader inventory
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
planning_base_branch: research/doctrine-wheel-mission-types-public-api
merge_target_branch: research/doctrine-wheel-mission-types-public-api
branch_strategy: Planning artifacts for this mission were generated on research/doctrine-wheel-mission-types-public-api. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/doctrine-wheel-mission-types-public-api unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 1 - Gate preconditions
history:
- at: '2026-08-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: researcher-robbie
authoritative_surface: docs/plans/doctrine/
create_intent:
- docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md
execution_mode: planning_artifact
model: ''
owned_files:
- docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md
role: researcher
tags: []
task_type: research
tracker_refs: []
---

# Work Package Prompt: WP03 – Cross-layer missions/ reader inventory

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `researcher-robbie`
- **Role**: `researcher`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Produce the committed, reviewable inventory of every reader of `src/doctrine/missions/` content — the artifact WP05 (the actual relocation) depends on to know what it must repoint. This is a **research/analysis WP**: its deliverable is a document, not a code change.

This WP is done when:
- `docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md` exists, committed, with one row per reader: `(file:line, current path assumption, decision: move|stay|repoint, rationale)`. (Note: this lives under `docs/plans/doctrine/`, not `kitty-specs/<mission>/`, because `finalize-tasks` currently rejects any WP `owned_files` entry under `kitty-specs/` — a known CLI gap tracked at issue #2643. Do not attempt to route around this by disabling the check; this WP's artifact location is the workaround.)
- Every row has a non-empty `decision` and `rationale`.
- The inventory **explicitly includes** the two sites already identified during this mission's planning (do not treat finding these as this WP's job — confirming and placing them correctly in the inventory is):
  - `doctrine.missions.repository.MissionTemplateRepository.default_missions_root()` — decision: `repoint` (converges onto WP04's kernel primitive).
  - `src/doctrine/drg/migration/extractor.py::_missions_root()` — decision: `repoint`, plus a note that `packs/built-in/mission_type.graph.yaml`/`mission_step_contract.graph.yaml` must be regenerated once this repoints (WP05's job to execute, this WP's job to record).
- The inventory explicitly classifies the `.py`-vs-data split within `src/doctrine/missions/` itself (which of the 11 `.py` modules stay — expected: all of them — vs. which data subdirectories move).

## Context & Constraints

Read `spec.md` (FR-003, User Story 1/AS1), `plan.md` (IC-03), and `research.md` (R6, R7, R8, R9) in full before starting — R7/R8/R9 already contain verified findings you must incorporate, not rediscover from scratch.

**Method — trace symbols, don't just grep paths.** A bare `grep -rn "doctrine.missions\|doctrine/missions" src/ tests/` sweep is a starting point but is known to miss load-bearing sites (during this mission's own post-plan review, `repository.py`'s own `files("doctrine") / "missions"` call was found only via an unrelated comment nearby, not the grep pattern). Trace every symbol imported from `doctrine.missions.*`, and every caller of `MissionTemplateRepository`, to its actual implementation.

**Search surfaces**: `src/kernel/paths.py`, `src/doctrine/pack_paths.py`, `src/doctrine/missions/repository.py`, `src/doctrine/drg/migration/extractor.py`, any `charter` reader of mission-type content, `src/specify_cli/**`, `src/runtime/**`, and `src/specify_cli/upgrade/migrations/*.py` (upgrade migrations are historically easy to miss — they read old layouts by design).

**Precedent**: `kitty-specs/relocate-builtin-doctrine-packs-01KYT87F/` (the prior mission that relocated the sibling `agent_profiles/`/`directives/`/etc. content) has its own reader-inventory artifacts still on `main` — read them as a format precedent.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### T011 – Trace every `doctrine.missions.*` symbol usage

- **Purpose**: Build the raw candidate list of readers.
- **Steps**: Trace symbol usage (not path-literal grep alone) across doctrine, kernel, charter, `specify_cli`, `runtime`, and upgrade migrations.
- **Files**: n/a (analysis).
- **Parallel?**: [P] — can run alongside T012/T013's confirmation work.

### T012 – Record the two already-identified sites explicitly

- **Purpose**: Ensure the inventory doesn't silently omit what's already known.
- **Steps**: Add `MissionTemplateRepository.default_missions_root()` and `extractor.py::_missions_root()` as explicit rows, with the decisions and rationale given in Objectives above.
- **Files**: n/a (analysis).
- **Parallel?**: [P] — can run alongside T011/T013.

### T013 – Classify the `.py`-vs-data-content split

- **Purpose**: Prevent WP05 from conflating the Python package with its data content.
- **Steps**: List all 11 `.py` modules in `src/doctrine/missions/` (expected `decision: stay` for each, since `packs/built-in/` cannot host Python modules) and all data subdirectories (expected `decision: move`).
- **Files**: n/a (analysis).
- **Parallel?**: [P] — can run alongside T011/T012.

### T014 – Commit the inventory artifact

- **Purpose**: Make the inventory a real, reviewable artifact — SC-007's own requirement.
- **Steps**: Write `docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md` with the full table (all rows from T011-T013), and add a one-line pointer to it from `kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/research.md` so it's discoverable from the mission itself. Commit both via the normal git flow for this WP (this file is outside `kitty-specs/`, so the ordinary WP commit path applies, not `spec-kitty spec-commit`).
- **Files**: `docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md`, plus a pointer edit to `kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/research.md`.
- **Parallel?**: No — final step, depends on T011-T013.

## Risks & Mitigations

- **Risk**: A shallow inventory (e.g. skipping upgrade migrations) silently under-scopes WP05. **Mitigation**: T014's commit is reviewed before WP05 is allowed to start (WP05 depends on this WP).

## Review Guidance

- Confirm both explicitly-named sites (T012) are present as their own rows, not folded into a generic "various callers" entry.
- Confirm every row has a non-empty decision and rationale — an empty `decision` field means the inventory isn't actually complete.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append new entries at the end.

- 2026-08-04T15:30:00Z – system – Prompt created.
