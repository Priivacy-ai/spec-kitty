---
work_package_id: WP06
title: 'doctrine-relationships.md: DRG diagram + unguarded-15 prose note'
dependencies:
- WP01
requirement_refs:
- C-003
- FR-003
- NFR-001
planning_base_branch: feat/doctrine-schema-diagrams-impl
merge_target_branch: feat/doctrine-schema-diagrams-impl
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-schema-diagrams-impl. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-schema-diagrams-impl unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
phase: Phase 3 - Diagrams
history:
- at: '2026-08-12T16:41:10Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: diagram-daisy
authoritative_surface: docs/architecture/doctrine-relationships.md
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/architecture/doctrine-relationships.md
role: diagram-author
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – doctrine-relationships.md DRG diagram + "15" prose note

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `diagram-daisy` (diagram-author) and behave per its guidance first.

---

## Objectives & Success Criteria

**Sole owner of `docs/architecture/doctrine-relationships.md`** (shared surface for IC-03 + IC-06).

**Definition of Done:**

1. A ` ```plantuml ` `@startyaml` **DRG diagram** depicting `DRGNode` + `DRGEdge` + `NodeKind` + `Relation`,
   with **all enum members derived by `list(...)`** (NOT hand-typed): `NodeKind` = 16 live members,
   `Relation` = 15. Real `title` for alt-text.
2. A prose note flags that the existing "15" (and any "16") **prose literals are diagram-unguarded** —
   they are narrative, not enforced by the drift guard (which introspects `list(...)`).
3. The WP08 drift guard binds this diagram (`DRGNode`/`DRGEdge`/`NodeKind`/`Relation`) and passes.
4. Page `updated: 2026-08-12`; terminology guard green.

## Context & Constraints

- **Source of truth**: [plan.md](../plan.md) IC-03 + IC-06, spec FR-003 / C-003 / NFR-001,
  [contracts/diagram-drift-guard.md](../contracts/diagram-drift-guard.md).
- **Depends on WP01** (render mechanism proven).
- **The DRG is FLAT** — do NOT use it for WP08's nested depth-2 test (that uses `AgentProfileSchema →
  AgentSpecialization`). Here, `DRGNode`/`DRGEdge` are flat structures + `NodeKind`/`Relation` StrEnums.
- **Introspect the live models** — find `DRGNode`, `DRGEdge`, `NodeKind`, `Relation` under `src/doctrine/`
  (e.g. `src/doctrine/drg/`). Derive members via `list(NodeKind)` / `list(Relation)`; the counts (16/15)
  are consequences of introspection, not literals you type into the diagram.
- Read the existing page first; **extend**, preserve the accessibility-discharging prose.

## Subtasks & Detailed Guidance

### Subtask T021 – DRG `@startyaml` diagram

- **Steps**:
  1. Locate and introspect `DRGNode`, `DRGEdge`, `NodeKind`, `Relation`. Confirm field sets +
     `list(NodeKind)` (16) / `list(Relation)` (15).
  2. Author a `@startyaml` block: node schema (`DRGNode` fields), edge schema (`DRGEdge` fields incl.
     `relation`), and the `NodeKind`/`Relation` vocabularies. Top-level YAML keys must equal the declared
     field sets (so WP08's diagram-side parser matches). Descriptive `title`.
  3. Place it in the relationships/graph section.
- **Files**: `docs/architecture/doctrine-relationships.md`.

### Subtask T022 – Unguarded-"15" prose note  `[P]`

- **Steps**: add a short note that the prose "15" (Relation) / "16" (NodeKind) counts are **narrative and
  diagram-unguarded** — the guard enforces the diagram↔model field/member match via `list(...)`, not the
  prose literal. This documents the deliberate scope boundary (the plan calls the prose "15" out explicitly).

## Branch Strategy

- **Strategy**: merge back into `feat/doctrine-schema-diagrams-impl`.
- **Planning base branch**: `feat/doctrine-schema-diagrams-impl`
- **Merge target branch**: `feat/doctrine-schema-diagrams-impl`

## Test Strategy

- WP08 drift guard is the fidelity test. Locally: terminology guard + docs freshness.

## Risks & Mitigations

- **Hand-typing NodeKind/Relation members** → drift + WP08 failure. Mitigation: introspect `list(...)`.
- **Using the flat DRG for a depth test** → wrong (WP08 uses AgentProfileSchema). Mitigation: keep DRG flat.

## Review Guidance

- Confirm every `NodeKind` (16) + `Relation` (15) member appears (cross-check `list(...)`).
- Confirm `DRGNode`/`DRGEdge` field sets match the models.
- Confirm the unguarded-"15" note is present.
- Reviewer ≠ implementer.

## Activity Log

> Append newest entries at the END, chronological.
