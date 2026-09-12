---
work_package_id: WP06
title: Post-consolidation verification seam (zero merge/ footprint)
dependencies:
- WP04
requirement_refs:
- FR-004
- FR-005
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
phase: Phase 5 - Post-Consolidation & Preview
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/post_consolidation.py
create_intent:
- src/specify_cli/acceptance/post_consolidation.py
- tests/acceptance/test_post_consolidation.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/acceptance/post_consolidation.py
- tests/acceptance/test_post_consolidation.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Post-consolidation verification seam

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

A new `acceptance/post_consolidation.py` — **and nothing else** — that judges `deferred_to_consolidation` invariants against the consolidated mission tree and writes outcomes back with `verified_surface_kind = CONSOLIDATED`; a genuine violation fails **its Op**, not the consolidation.

**Done** = contract `negative-invariant-provenance.md` C6/C7 pass: a `still_present` deferred invariant fails the Op and names it, while the completed consolidation is untouched (US1.4).

## Context & Constraints

- Contract `negative-invariant-provenance.md` C6/C7; spec FR-004/FR-005; data-model result state machine.
- **Decided 2026-07-23: ZERO `merge/` footprint.** No new CLI verb, no call-in from `merge/executor.py`. The verification is an ordinary governed Op dispatched through the canonical surface (`spec-kitty dispatch`, closed with `profile-invocation complete`). This supersedes the earlier "narrow call-in from executor" shape (`DM-01KY7AKXNJZCB2J2W411YM3B9F` and `tracers/design-decisions.md` are historical logs, left unedited).
- **The op runs AFTER consolidation** — it does NOT add an abort path inside the consolidation transaction and does NOT interact with the rollback machinery IC-06 (WP09) is collapsing. That decoupling is deliberate and must be preserved.
- Enforcement is the external CI check (FR-016 / WP18), not a loop guardrail — do NOT add a matrix-reader guardrail here.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T031 – New module, dispatched as an Op

- **Steps**: Create `acceptance/post_consolidation.py` that reads the consolidated tree and the matrix and writes back outcomes. It is dispatched as a governed Op; it does not import `merge/`.

### Subtask T032 – Judge against the consolidated tree (C6)

- **Steps**: For each `deferred_to_consolidation` invariant, judge it against the consolidated tree; write the outcome with `verified_surface_kind = CONSOLIDATED` and the consolidation commit as `verified_ref`.

### Subtask T033 – Fail the Op, not the consolidation (C7/FR-005)

- **Steps**: A deferred invariant that proves `still_present` on the consolidated tree fails **the Op**, naming the specific invariant. Lane consolidation is unaffected (already completed cleanly); no rollback of the consolidation is attempted.

### Subtask T034 – Preserve decoupling

- **Steps**: Assert (in tests and by construction) no coupling to `merge/executor.py` or the rollback machinery.

### Subtask T035 – Tests + baseline registration

- **Steps**: Tests on a consolidated fixture (a `confirmed_absent` case and a `still_present` case). **This WP likely creates `tests/acceptance/` first** — register the new dir with BOTH gate-coverage baselines deliberately (gc3b orphan `--update-baseline`; gc2b selection `--freeze-baselines`) per C-006. Coordinate with WP03 if it created the dir first.

## Test Strategy

- New: `tests/acceptance/test_post_consolidation.py`.
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/acceptance/test_post_consolidation.py -q`.

## Risks & Mitigations

- **File-disjoint from the main chain → genuine lane-B parallelism.** Keep it that way (no `merge/` imports).

## Review Guidance

- Confirm zero `merge/` import/footprint.
- Confirm a `still_present` deferred invariant fails the Op and leaves the consolidation untouched.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
