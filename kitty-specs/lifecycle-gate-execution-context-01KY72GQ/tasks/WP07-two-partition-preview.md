---
work_package_id: WP07
title: Two-partition consolidation-readiness preview
dependencies:
- WP03
requirement_refs:
- C-007
- FR-006
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
- T040
phase: Phase 5 - Post-Consolidation & Preview
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/forecast.py
create_intent:
- tests/integration/test_two_partition_preview.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/merge/forecast.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- tests/integration/test_two_partition_preview.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Two-partition consolidation-readiness preview

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

The readiness preview resolves lane-state and review-cycle from **their own declared homes** rather than one caller-supplied directory, so preview and real consolidation agree.

**Done** = SC-002: on a coord mission with a genuinely rejected review outcome, the preview reports not-ready and names the WP (US2.1); a stale leftover review file does not cause a false not-ready (US2.2).

## Context & Constraints

- Spec US2, FR-006, SC-002; plan IC-05; contract `gate-execution-context.md` C1 (each fact from its own surface).
- **#2885**: the preview asked one gate to judge two things (lane state + review outcome) while handing it a single directory — the surface correct for one and empty for the other, so every WP looked stateless and the gate passed by default.
- **C-007**: harvest the two coord integration tests from PR #2834 **with attribution to @rayjohnson** — do not rewrite them.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T036 – Two-partition resolution in forecast

- **Steps**: `forecast.py::feature_dir_for_preview` (already repointed onto the WP02 seam) — resolve lane-state and review-cycle each from its own declared home (two partitions), not one caller-supplied dir.

### Subtask T037 – Partition split in review_artifact_consistency

- **Steps**: `review_artifact_consistency.py::_resolve_review_cycle_read_dir` — split the partition resolution and remove the silent-degradation branch that produced #2885.

### Subtask T038 – Harvest PR #2834 tests (attribution)

- **Steps**: Bring the two coord-topology integration tests from PR #2834 into `tests/integration/test_two_partition_preview.py`, **crediting @rayjohnson** in the test docstring/comment. Do not rewrite from scratch (C-007).

### Subtask T039 – SC-002 agreement

- **Steps**: Assert preview and real consolidation agree on the rejected-review case that currently disagrees; a stale leftover review file does not cause a false not-ready.

### Subtask T040 – Conditional preflight-signature check

- **Steps**: Determine whether the fix changes the signature of `run_review_artifact_consistency_preflight`. If it does, it pulls in `merge/preflight.py` (IC-01/WP01's surface) — do **NOT** co-own `preflight.py`; edit it under leeway (WP01 already landed, no concurrency) and record the rationale. Report the outcome so lane-B parallelism can be confirmed or retracted.

## Test Strategy

- New: `tests/integration/test_two_partition_preview.py` (harvested + SC-002).
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/integration/test_two_partition_preview.py -q`.

## Risks & Mitigations

- **Verify the T040 signature check before assuming lane B exists** (plan File Ownership note).
- Serial after WP02 (shares `forecast.py`/`review_artifact_consistency.py` — WP02 touched only their translator functions).

## Review Guidance

- Confirm each fact resolves from its own surface (C1/FR-006), not one caller dir.
- Confirm attribution to @rayjohnson on the harvested tests.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
