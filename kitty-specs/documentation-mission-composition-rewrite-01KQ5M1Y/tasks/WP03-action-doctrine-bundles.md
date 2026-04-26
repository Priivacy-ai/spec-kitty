---
work_package_id: WP03
title: Action Doctrine Bundles
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
agent: "claude:opus-4.7:implementer-ivan:implementer"
shell_pid: "51028"
history:
- action: created
  at: '2026-04-26T19:46:00Z'
  by: tasks
authoritative_surface: src/doctrine/missions/documentation/actions/
execution_mode: code_change
owned_files:
- src/doctrine/missions/documentation/actions/discover/index.yaml
- src/doctrine/missions/documentation/actions/discover/guidelines.md
- src/doctrine/missions/documentation/actions/audit/index.yaml
- src/doctrine/missions/documentation/actions/audit/guidelines.md
- src/doctrine/missions/documentation/actions/design/index.yaml
- src/doctrine/missions/documentation/actions/design/guidelines.md
- src/doctrine/missions/documentation/actions/generate/index.yaml
- src/doctrine/missions/documentation/actions/generate/guidelines.md
- src/doctrine/missions/documentation/actions/validate/index.yaml
- src/doctrine/missions/documentation/actions/validate/guidelines.md
- src/doctrine/missions/documentation/actions/publish/index.yaml
- src/doctrine/missions/documentation/actions/publish/guidelines.md
tags: []
---

# WP03 — Action Doctrine Bundles

## Objective

Author 12 files (6 actions × `index.yaml` + `guidelines.md`) under `src/doctrine/missions/documentation/actions/<action>/`, modeled on the existing research bundles. The directives/tactics list in each `index.yaml` MUST match the URN edges that WP04 will add to `src/doctrine/graph.yaml` (the URN suffix matches the slug — e.g. `directive:DIRECTIVE_010` ↔ `010-specification-fidelity-requirement`). WP04's `test_action_bundle_matches_drg_edges` enforces that.

## Context

Reference: `src/doctrine/missions/research/actions/scoping/index.yaml` and `…/scoping/guidelines.md` are the canonical templates. Each action directory has exactly two files. The `guidelines.md` is governance prose (~30-50 lines) for the host LLM; it is NOT executable code and contains no implementation directives.

The directive/tactic mix per action is:

| action | directives | tactics |
|---|---|---|
| `discover` | 010, 003 | requirements-validation-workflow, premortem-risk-identification |
| `audit` | 003, 037 | requirements-validation-workflow |
| `design` | 001, 003, 010 | adr-drafting-workflow, requirements-validation-workflow |
| `generate` | 010, 037 | requirements-validation-workflow |
| `validate` | 010, 037 | premortem-risk-identification, requirements-validation-workflow |
| `publish` | 010, 037 | requirements-validation-workflow |

Slug names use the kebab form (`010-specification-fidelity-requirement`); URN form is for graph.yaml edges (WP04).

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution: `spec-kitty agent action implement WP03 --agent <name>`.

## Subtasks

### T011 — `discover/{index.yaml,guidelines.md}`

**Steps**:
1. Create `src/doctrine/missions/documentation/actions/discover/index.yaml`:
   ```yaml
   action: discover
   directives:
     - 010-specification-fidelity-requirement
     - 003-decision-documentation-requirement
   tactics:
     - requirements-validation-workflow
     - premortem-risk-identification
   styleguides: []
   toolguides: []
   procedures: []
   ```
2. Create `discover/guidelines.md`. ~30-50 lines. Cover:
   - Core authorship focus: identify documentation needs, target audience, iteration mode (initial / gap-filling / mission-specific), goals.
   - Stakeholders and constraints: who reads the docs, what tooling/format constraints apply (Divio types, accessibility).
   - Scoping discipline: in scope / out of scope; document iteration mode upfront.
   - Success criteria standards: measurable, technology-agnostic, user-focused.

   Use the same writing style and section structure as `src/doctrine/missions/research/actions/scoping/guidelines.md`. Read it first as the model.

**Files**: 2 new files.

**Validation**:
- [ ] `index.yaml` parses; `action` field equals `discover`.
- [ ] `guidelines.md` exists and is non-empty.

### T012 — `audit/{index.yaml,guidelines.md}`

```yaml
action: audit
directives:
  - 003-decision-documentation-requirement
  - 037-living-documentation-sync
tactics:
  - requirements-validation-workflow
styleguides: []
toolguides: []
procedures: []
```

`guidelines.md` covers: documentation gap analysis, evidence-based audit, coverage matrix per Divio type, prioritization by user impact.

### T013 — `design/{index.yaml,guidelines.md}`

```yaml
action: design
directives:
  - 001-architectural-integrity-standard
  - 003-decision-documentation-requirement
  - 010-specification-fidelity-requirement
tactics:
  - adr-drafting-workflow
  - requirements-validation-workflow
styleguides: []
toolguides: []
procedures: []
```

`guidelines.md` covers: documentation architecture (Divio four-type system), generator selection (JSDoc/Sphinx/rustdoc), navigation hierarchy, ADR-style design decisions.

### T014 — `generate/{index.yaml,guidelines.md}`

```yaml
action: generate
directives:
  - 010-specification-fidelity-requirement
  - 037-living-documentation-sync
tactics:
  - requirements-validation-workflow
styleguides: []
toolguides: []
procedures: []
```

`guidelines.md` covers: implementation discipline for documentation output, faithfulness to plan.md, generator invocation, source-of-truth alignment.

### T015 — `validate/{index.yaml,guidelines.md}`

```yaml
action: validate
directives:
  - 010-specification-fidelity-requirement
  - 037-living-documentation-sync
tactics:
  - premortem-risk-identification
  - requirements-validation-workflow
styleguides: []
toolguides: []
procedures: []
```

`guidelines.md` covers: quality gates (Divio-type adherence, accessibility, completeness), risk review against publication, audit-report.md as the canonical evidence artifact.

### T016 — `publish/{index.yaml,guidelines.md}`

```yaml
action: publish
directives:
  - 010-specification-fidelity-requirement
  - 037-living-documentation-sync
tactics:
  - requirements-validation-workflow
styleguides: []
toolguides: []
procedures: []
```

`guidelines.md` covers: release readiness, deployment handoff, release.md as the publication-handoff artifact, post-publish living-documentation sync expectations.

## Definition of Done

- [ ] All 12 files exist (6 × 2).
- [ ] All 6 `index.yaml` files parse as YAML with `action` field matching the directory name.
- [ ] All 6 `guidelines.md` files are at least 30 lines and follow the research bundle's writing style.
- [ ] Slug references in every `index.yaml` map to existing directives/tactics in `src/doctrine/graph.yaml` (verify via `grep '037-living-documentation-sync' src/doctrine/graph.yaml` etc.).
- [ ] No edits outside `src/doctrine/missions/documentation/actions/`.

## Risks

1. A slug might not match an existing graph.yaml URN — e.g. `037-living-documentation-sync` may not be the canonical slug form. Mitigation: grep `src/doctrine/graph.yaml` and `src/doctrine/directives/` for the directive's authoritative slug before authoring; use that exact slug.
2. Action bundle directive/tactic mismatch with WP04's edge table breaks the `test_action_bundle_matches_drg_edges` test. Mitigation: WP03 and WP04 share the directives/tactics table from data-model.md verbatim; if either WP changes the mix, both must update.

## Reviewer Guidance

- Compare each `index.yaml` to `src/doctrine/missions/research/actions/scoping/index.yaml` for shape.
- Compare each `guidelines.md` to `src/doctrine/missions/research/actions/scoping/guidelines.md` for tone and structure.
- Verify the slug forms are the kebab form (no `directive:` prefix in `index.yaml`).
- Verify no edits outside the 12 owned files.

## Activity Log

- 2026-04-26T20:08:30Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=51028 – Started implementation via action command
- 2026-04-26T20:12:46Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=51028 – T011-T016 complete; 12 files; all slugs validated against graph.yaml
