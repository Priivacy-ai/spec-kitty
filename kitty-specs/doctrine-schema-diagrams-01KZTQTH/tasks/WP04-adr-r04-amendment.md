---
work_package_id: WP04
title: ADR + R-04 amendment (govern the rendering decision + schema-diagram genre)
dependencies: []
requirement_refs:
- C-006
- FR-002
- NFR-005
planning_base_branch: feat/doctrine-schema-diagrams-impl
merge_target_branch: feat/doctrine-schema-diagrams-impl
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-schema-diagrams-impl. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-schema-diagrams-impl unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
phase: Phase 2 - Governance
history:
- at: '2026-08-12T16:41:10Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: docs/adr/3.x/
create_intent:
- docs/adr/3.x/2026-08-12-1-plantuml-schema-diagram-rendering.md
execution_mode: code_change
model: ''
owned_files:
- docs/adr/3.x/2026-08-12-*-plantuml-schema-diagram-rendering.md
- docs/architecture/diagrams/README.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – ADR + R-04 amendment

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `architect-alphonso` (implementer role here) and behave per its
guidance first.

---

## Objectives & Success Criteria

Record the rendering decision as an ADR and amend the diagrams README's R-04 so the two do not
contradict.

**Definition of Done:**

1. New ADR at `docs/adr/3.x/2026-08-12-<n>-plantuml-schema-diagram-rendering.md` that:
   - **Cites** the active `plantuml-diagramming` toolguide (charter-prose active, not runtime-resolved).
   - Positions **schema diagrams as a NEW genre** distinct from C4 progressive-zoom (the charter's
     `USE_C4_MODEL_TECHNIQUES`); explains they depict *code models*, not architecture zoom levels.
   - Records the **accessibility carve-out** (NFR-005): the `docs-accessibility` "restate the diagram's
     facts in prose" duty is discharged by the surrounding doctrine-kinds prose — NOT by re-listing
     fields (which would recreate the drift surface C-005 forbids).
   - States the **local-jar / no-egress** decision (C-001) and the **docsite-only** tradeoff (C-002):
     the new lane trades github.com-source rendering for generated fidelity.
2. `docs/architecture/diagrams/README.md` R-04 amended: R-04 is **unchanged for hand-authored C4**; the
   **new lane** = generated, docsite-only schema diagrams. The two must be internally consistent.
3. Terminology guard + docs freshness (`updated: YYYY-MM-DD` frontmatter) green.

## Context & Constraints

- **Source of truth**: [research.md](../research.md) (D4), [plan.md](../plan.md) IC-02, spec FR-002 / C-006.
- Follow the ADR template/format of the existing `docs/adr/3.x/` entries (read
  `docs/adr/3.x/2026-08-05-1-*.md` for the house style). Divio quadrant = Explanation.
- Independent, prose-only WP — **no code dependency**; may co-land with the capability WPs.
- Charter diagramming doctrine: `.kittify/charter/charter.md` §"Writing, Communication & Diagramming".

## Subtasks & Detailed Guidance

### Subtask T015 – Write the ADR  `[P]`

- **Purpose**: govern FR-001's decision + the schema-diagram genre (FR-002, C-006, NFR-005 carve-out).
- **Steps**:
  1. Number the ADR by the next free `3.x` index for `2026-08-12` (likely `-1-`); update
     `docs/adr/3.x/index.md`/`README.md` only if that is the house convention (check first — those may
     be owned elsewhere; if so, note the needed index entry in the Activity Log rather than editing).
  2. Sections: Context (docsite renders Mermaid not PlantUML; doctrine has no schema diagrams) →
     Decision (local sha256-pinned jar, docker `--network=none`, post-`glossary_linker`, SANDBOX) →
     Consequences (docsite-only C-002; new genre vs C4; accessibility carve-out; drift guard is the
     fidelity control) → the toolguide citation + R-04 reconciliation.
  3. Add `updated: 2026-08-12` frontmatter + a Divio `type` if the house style uses it.
- **Files**: `docs/adr/3.x/2026-08-12-1-plantuml-schema-diagram-rendering.md`.

### Subtask T016 – Amend R-04 in `docs/architecture/diagrams/README.md`  `[P]`

- **Purpose**: stop R-04 ("generation out of scope") from contradicting the new capability (C-006).
- **Steps**:
  1. Read the current R-04 text. Add a precise carve-out: R-04 stays as-is for **hand-authored C4**;
     a **new lane** covers **generated, docsite-only schema diagrams** (link the ADR).
  2. Keep the amendment minimal and localized (locality-of-change); refresh the page `updated:` date.
- **Files**: `docs/architecture/diagrams/README.md`.

## Branch Strategy

- **Strategy**: merge back into `feat/doctrine-schema-diagrams-impl`.
- **Planning base branch**: `feat/doctrine-schema-diagrams-impl`
- **Merge target branch**: `feat/doctrine-schema-diagrams-impl`

## Test Strategy

- `pytest tests/architectural/test_no_legacy_terminology.py` (terminology canon).
- Docs freshness check if the repo runs one (`scripts/docs/check_docs_freshness.py`).

## Risks & Mitigations

- **ADR/R-04 contradiction** → reviewer confusion. Mitigation: cross-link both; state the carve-out
  identically in both places.
- **Editing an index file owned by another WP** → overlap. Mitigation: if `index.md`/`README.md` under
  `docs/adr/3.x/` is not in this WP's `owned_files`, do not edit it — record the needed entry instead.

## Review Guidance

- Confirm the toolguide citation, the new-genre framing, the accessibility carve-out, and the
  docsite-only tradeoff are all present in the ADR.
- Confirm R-04 is amended, not overwritten, and cross-links the ADR.
- Reviewer ≠ implementer.

## Activity Log

> Append newest entries at the END, chronological.
