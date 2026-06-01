---
work_package_id: WP04
title: Doctrine Prose Semantic Rewrite
dependencies: []
requirement_refs:
- FR-001
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rename-ceremony-to-status-commit-01KSPN6C
base_commit: 6a553f0a7841a3e2c17652192160cd11af4bfcfa
created_at: '2026-06-01T07:34:24.406692+00:00'
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 1 - Foundation
agent: claude
shell_pid: '59803'
history:
- at: '2026-05-28T07:11:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/
execution_mode: code_change
owned_files:
- src/doctrine/procedures/README.md
- src/doctrine/missions/software-dev/actions/tasks/guidelines.md
- src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 — Doctrine Prose Semantic Rewrite

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

Scope governance context to terminology curation before reading anything else. This WP rewrites doctrine prose — load the curator profile so the doctrine voice + canonical-term enforcement apply.

---

## Objective

Rewrite 6 prose occurrences in `src/doctrine/` according to **Rule R2** (semantic rewrite per context) from the [term-rename contract](../contracts/term-rename-contract.md). These are **workflow-sense** occurrences — bare "ceremony" or "full ceremony" meaning "the multi-phase mission workflow" (specify/plan/tasks/implement/review/merge), not a single auto-commit.

A mechanical substitution would produce nonsense like "full status commit". Apply the per-line replacement text from `occurrence_map.yaml`.

Decision authority: `01KSPP3SSZ5GKHTTB1C9EJQ13V` (semantic_rewrite_per_context). See [decisions/DM-01KSPP3SSZ5GKHTTB1C9EJQ13V.md](../decisions/DM-01KSPP3SSZ5GKHTTB1C9EJQ13V.md).

## Context

- **Spec anchors**: [FR-001](../spec.md#functional-requirements), [FR-008](../spec.md#functional-requirements).
- **Occurrence-map entries**: `dd-001`, `dd-002`, `dd-003`, `dd-004`, `dd-005`, `dd-006`.
- **Style note**: doctrine prose has a teaching voice. Avoid jargon-stuffed substitutions; prefer "the full mission workflow" over "all six phases of specify/plan/tasks/implement/review/merge" unless the reader needs the explicit enumeration.

## Subtask Detail

### T015 — `src/doctrine/procedures/README.md` line 15

**Current**:

```
- Feature merge ceremony
```

**Replacement** (occurrence_map `dd-001`):

```
- Feature merge workflow
```

If line 15 is a heading or list item inside a section labeled "Procedures" or "Ceremonies", verify the surrounding section heading does not also use the word "ceremony". Open the file and read the surrounding 20 lines before saving.

### T016 — `src/doctrine/missions/software-dev/actions/tasks/guidelines.md` line 26

**Current**:

```
- Prefer splitting an oversized WP over padding a small one; prefer merging trivially short WPs over inflating them with ceremony.
```

**Replacement** (occurrence_map `dd-002`):

```
- Prefer splitting an oversized WP over padding a small one; prefer merging trivially short WPs over inflating them with workflow overhead.
```

### T017 — `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md` — 4 occurrences

This file is the largest doctrine occurrence cluster. All four are workflow-sense.

**Line 9** (occurrence_map `dd-003`):

Current:

```
  repos", "orchestrate a cross-repo release", "run the full ceremony on
```

Replacement:

```
  repos", "orchestrate a cross-repo release", "run the full mission workflow on
```

**Line 269** (occurrence_map `dd-004`):

Current:

```
- If the user has authorized autonomy on repo C, spawn the full-ceremony
```

Replacement:

```
- If the user has authorized autonomy on repo C, spawn the full-mission-workflow
```

**Line 343** (occurrence_map `dd-005`):

Current:

```
| Silent repo fallback when target isn't initialized | Phase 1 on a repo without `.kittify/` scaffold | Detect via `ls <target>/kitty-specs/` after ceremony; if empty and another repo got the artifacts, relocate + `spec-kitty init --ai <agent>` in the real target | #773 |
```

Replacement:

```
| Silent repo fallback when target isn't initialized | Phase 1 on a repo without `.kittify/` scaffold | Detect via `ls <target>/kitty-specs/` after the mission workflow runs; if empty and another repo got the artifacts, relocate + `spec-kitty init --ai <agent>` in the real target | #773 |
```

**Line 366** (occurrence_map `dd-006`):

Current:

```
  the most time, which parts of the ceremony they valued, what they
```

Replacement:

```
  the most time, which parts of the mission workflow they valued, what they
```

### T018 — Verify zero stragglers in `src/doctrine/`

```bash
grep -rn 'ceremony' src/doctrine/
```

Expected: **zero hits**. If any hit appears, classify per occurrence_map (commit_class or workflow_sense) and apply the matching replacement.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution workspace: allocated per lane in `lanes.json` after `finalize-tasks`.
- Resolve via `spec-kitty agent context resolve --action implement --wp WP04 --mission rename-ceremony-to-status-commit-01KSPN6C --json`.

## Test Strategy

- No new tests. Doctrine docs are not executed.
- WP06 regression guard will assert no `ceremony` substring remains in `src/`.
- Optionally run `spec-kitty doctor` if available — surfaces broken doctrine references.

## Definition of Done

- [ ] All 6 prose lines updated exactly per the replacement text above.
- [ ] `grep -rn 'ceremony' src/doctrine/` returns zero hits.
- [ ] Surrounding prose remains coherent (no orphaned grammar / dangling references).
- [ ] No code, no other files modified — only the 3 doctrine markdown files in owned_files.
- [ ] `ruff check .` passes (markdown isn't linted by ruff, but full repo passes).

## Risks & Reviewer Guidance

- **Risk 1**: A surrounding section heading or table-of-contents in one of these files also says "ceremony". Mitigation: read 20 lines around each edit point before saving.
- **Risk 2**: Replacement text reads awkwardly in context. Mitigation: apply the occurrence_map text exactly; if the result truly reads awkwardly, surface in the PR review rather than silently changing the contract.
- **Risk 3**: Implementer reads only the spec FR-001 ("replace ceremony with status commit") and mechanically substitutes, producing "full status commit" or similar nonsense. Mitigation: this prompt explicitly classifies these as workflow_sense per Rule R2 — apply the per-line replacement.
- **Reviewer check 1**: Diff touches only the 3 files in owned_files.
- **Reviewer check 2**: Each edited line matches occurrence_map exactly.
- **Reviewer check 3**: `grep -rn 'ceremony' src/doctrine/` returns zero hits.

## References

- Spec: [../spec.md](../spec.md) — FR-001, FR-008
- Plan: [../plan.md](../plan.md) — research item R4 (doctrine rewording strategy)
- Decision: [../decisions/DM-01KSPP3SSZ5GKHTTB1C9EJQ13V.md](../decisions/DM-01KSPP3SSZ5GKHTTB1C9EJQ13V.md)
- Occurrence map: [../occurrence_map.yaml](../occurrence_map.yaml) — `dd-001` through `dd-006`
- Term-rename contract: [../contracts/term-rename-contract.md](../contracts/term-rename-contract.md) — Rule R2

## Activity Log

- 2026-06-01T07:36:54Z – claude – shell_pid=59803 – Ready for review
