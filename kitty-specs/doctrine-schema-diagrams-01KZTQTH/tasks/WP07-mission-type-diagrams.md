---
work_package_id: WP07
title: 'mission-type-resolution.md: mission-type/step + action-index diagrams with prose'
dependencies:
- WP01
requirement_refs:
- C-004
- FR-003
planning_base_branch: feat/doctrine-schema-diagrams-impl
merge_target_branch: feat/doctrine-schema-diagrams-impl
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-schema-diagrams-impl. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-schema-diagrams-impl unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
phase: Phase 3 - Diagrams
history:
- at: '2026-08-12T16:41:10Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: diagram-daisy
authoritative_surface: docs/architecture/mission-type-resolution.md
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/architecture/mission-type-resolution.md
role: diagram-author
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – mission-type-resolution.md diagrams + standalone prose

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `diagram-daisy` (diagram-author) and behave per its guidance first.

---

## Objectives & Success Criteria

**Sole owner of `docs/architecture/mission-type-resolution.md`.**

**Definition of Done:**

1. A ` ```plantuml ` `@startyaml` **mission-type/step** diagram depicting `MissionStep` /
   `MissionStepContract` (+ its nested step/I-O structure), fields derived by introspection. Real `title`.
2. An **`action-index`** diagram **accompanied by standalone explanatory prose** (C-004 — a picture alone
   is insufficient; the prose must explain what an action index is and how resolution uses it).
3. `action-index` is documented **here**, NOT in the kinds catalog (it is a mission concept, not an
   `ArtifactKind`); a one-line note states `mission-type` is likewise a mission concept.
4. The WP08 drift guard binds the mission-type/step diagram and passes; page `updated: 2026-08-12`.

## Context & Constraints

- **Source of truth**: [plan.md](../plan.md) IC-03, spec FR-003 / C-004,
  [contracts/diagram-drift-guard.md](../contracts/diagram-drift-guard.md).
- **Depends on WP01** (render mechanism proven).
- **Introspect the live models**: find `MissionStep` / `MissionStepContract` (+ nested step/inputs types)
  and `ActionIndex` (a **frozen dataclass** — WP08 introspects it via `fields()`). Do not transcribe.
- **`MissionStepContract → MissionStepContractStep → inputs`** is a genuine nested structure — WP08 may
  use it (or `AgentProfileSchema → AgentSpecialization`) for the depth-2 test; author the diagram so
  nested sub-maps are visible (top-level keys recurse).
- **C-004**: action-index carries **standalone prose**, not just a diagram. `mission-type` and
  `action-index` are NOT artefact kinds — keep them out of the WP05 kinds catalog.

## Subtasks & Detailed Guidance

### Subtask T023 – Mission-type/step `@startyaml` diagram

- **Steps**: introspect `MissionStep`/`MissionStepContract` (+ nested step/I-O). Author a `@startyaml`
  block with the field sets (top-level keys = declared fields; nested sub-maps for nested models).
  Descriptive `title`. Place in the resolution/step section.
- **Files**: `docs/architecture/mission-type-resolution.md`.

### Subtask T024 – Action-index diagram + standalone prose

- **Steps**:
  1. Introspect `ActionIndex` (frozen dataclass). Author a `@startyaml` diagram of its shape.
  2. Write **standalone explanatory prose** around it: what the action index is, how mission-type
     resolution consumes it, why it is a mission concept and not an artefact kind (C-004). The prose,
     not the picture, is the load-bearing explanation.
- **Files**: `docs/architecture/mission-type-resolution.md`.

### Subtask T025 – Filing note  `[P]`

- **Steps**: add a one-line note that `action-index` and `mission-type` are mission concepts documented
  here (not `ArtifactKind` members, so absent from the kinds catalog). This complements WP05's C-004 filing.

## Branch Strategy

- **Strategy**: merge back into `feat/doctrine-schema-diagrams-impl`.
- **Planning base branch**: `feat/doctrine-schema-diagrams-impl`
- **Merge target branch**: `feat/doctrine-schema-diagrams-impl`

## Test Strategy

- WP08 drift guard is the fidelity test. Locally: terminology guard + docs freshness.

## Risks & Mitigations

- **Action-index as a picture only** → violates C-004. Mitigation: standalone prose is mandatory.
- **Filing action-index/mission-type as kinds** → wrong. Mitigation: keep them here; note the distinction.
- **Hand-typed fields** → drift. Mitigation: introspect the models.

## Review Guidance

- Confirm both diagrams present; action-index has real standalone prose (not just an image).
- Confirm action-index/mission-type are NOT in the kinds catalog and the note is present.
- Confirm field sets match `MissionStep`/`MissionStepContract`/`ActionIndex`.
- Reviewer ≠ implementer.

## Activity Log

> Append newest entries at the END, chronological.
