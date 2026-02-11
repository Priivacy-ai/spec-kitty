# Data Model: Mid-Stream Change Command

**Feature**: `029-mid-stream-change-command`  
**Date**: 2026-02-09

## Relationship Overview

```
BranchStash
  |
  | 1..n
  v
ChangeRequest --1..1-- ComplexityAssessment
  |
  | 1..1
  v
ChangePlan --1..n-- ChangeWorkPackage --0..n-- DependencyEdge
  |                            |
  | 0..n                       | 0..n
  v                            v
MergeCoordinationJob       ConsistencyReport
```

## Entities

### BranchStash

Scope-aware destination for generated change work.

**Fields**:
- `stash_key` (string): `main` or feature slug.
- `scope_type` (enum): `main` | `feature`.
- `stash_path` (string):
  - `kitty-specs/change-stack/main/` for `main`
  - `kitty-specs/<feature>/tasks/` for `feature`
- `tasks_doc_path` (string|null):
  - `kitty-specs/change-stack/main/tasks.md` for `main` when present
  - `kitty-specs/<feature>/tasks.md` for `feature`

**Validation rules**:
- `scope_type=main` requires `stash_key=main` and embedded path.
- `scope_type=feature` requires non-empty feature slug and feature tasks path.

### ChangeRequest

User-authored request to adjust in-flight implementation.

**Fields**:
- `request_id` (string): deterministic trace ID.
- `raw_text` (string): original request text.
- `submitted_branch` (string)
- `submitted_by` (string): contributor identity.
- `submitted_at` (timestamp)
- `stash_key` (string): resolved target stash.
- `validation_state` (enum): `valid` | `ambiguous` | `blocked`.
- `continue_after_warning` (bool)

**Validation rules**:
- `raw_text` must be non-empty.
- `submitted_by` must map to repository contributor access.
- `validation_state=ambiguous` blocks apply.

### ComplexityAssessment

Deterministic score output.

**Fields**:
- `request_id` (string)
- `scope_breadth_score` (int, 0-3)
- `coupling_score` (int, 0-2)
- `dependency_churn_score` (int, 0-2)
- `ambiguity_score` (int, 0-2)
- `integration_risk_score` (int, 0-1)
- `total_score` (int, 0-10)
- `classification` (enum): `simple` | `complex` | `high`
- `recommend_specify` (bool)

**Validation rules**:
- `total_score` equals sum of sub-scores.
- `recommend_specify=true` iff `classification=high`.

### ChangePlan

Planner decision layer for decomposition and guardrails.

**Fields**:
- `request_id` (string)
- `mode` (enum): `single_wp` | `orchestration` | `targeted_multi`
- `affected_open_wp_ids` (list[string])
- `closed_reference_wp_ids` (list[string])
- `guardrails` (list[string])
- `requires_merge_coordination` (bool)

**Validation rules**:
- Closed WP IDs in `closed_reference_wp_ids` cannot appear in reopen actions.
- `mode=single_wp` emits one change WP.
- `mode=targeted_multi` emits two or more change WPs.

### ChangeWorkPackage

Generated WP entry written into flat stash task locations.

**Frontmatter fields**:
- `work_package_id` (string): `WP##`
- `title` (string)
- `lane` (enum): `planned` | `doing` | `for_review` | `done`
- `dependencies` (list[string])
- `change_stack` (bool): always true
- `change_request_id` (string)
- `change_mode` (enum): `single` | `orchestration` | `targeted`
- `stack_rank` (int)
- `review_attention` (enum): `normal` | `elevated`
- `closed_reference_links` (list[string]): optional links to closed/done WPs

**Body requirements**:
- Includes acceptance guardrails.
- Includes final testing task.

**Validation rules**:
- Dependency graph must be valid (no missing refs, self-edge, or cycles).
- Dependencies may include normal open WPs when ordering requires.
- Closed/done WP IDs may only appear in `closed_reference_links`, never as reopened targets.

### MergeCoordinationJob

Cross-stream integration coordination output.

**Fields**:
- `job_id` (string)
- `request_id` (string)
- `target_wp_ids` (list[string])
- `reason` (string)
- `status` (enum): `planned` | `done`

**Validation rules**:
- `target_wp_ids` must resolve to existing or generated WPs.
- Jobs are created only when deterministic conflict heuristics trigger.

### ConsistencyReport

Post-apply reconciliation output.

**Fields**:
- `request_id` (string)
- `updated_tasks_doc` (bool)
- `created_wp_files` (list[string])
- `dependency_validation_passed` (bool)
- `broken_links_fixed` (int)
- `issues` (list[string])

**Validation rules**:
- Successful apply requires `dependency_validation_passed=true` and empty `issues`.

## State and Selection Model

### Change request lifecycle

`submitted -> validated -> previewed -> applied`

`validated` may stop at `ambiguous` until user clarification is provided.

### Lane lifecycle

Generated change WPs follow standard lane progression:

`planned -> doing -> for_review -> done`

### Next-doable selection order

1. Select any dependency-ready planned change WP, ordered by `stack_rank` then `work_package_id`.
2. If pending change WPs exist but none are ready, return blockers and stop normal progression.
3. Only when change stack is empty, select normal planned WPs.

---

**END OF DATA MODEL**
