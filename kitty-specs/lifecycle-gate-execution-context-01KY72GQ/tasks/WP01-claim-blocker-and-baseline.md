---
work_package_id: WP01
title: Claim-time consolidation blocker — live reproduction & fix
dependencies: []
requirement_refs:
- C-002
- FR-011
- NFR-005
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-lifecycle-gate-execution-context-01KY72GQ
base_commit: 8357984376e5786618a420c348decce08512fc95
created_at: '2026-07-24T03:04:07.174777+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation & Claim-Blocker
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/implement.py
create_intent:
- tests/regression/test_issue_2795_claim_blocker.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/merge/preflight.py
- src/specify_cli/git/ref_advance.py
- tests/regression/test_issue_2795_claim_blocker.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Claim-time consolidation blocker — live reproduction & fix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

- **FR-011**: Establish the *actual* claim-time consolidation blocker by **live reproduction**, not by trusting the reported cause (dirty coord `meta.json`). The quickstart records the reported cause as **refuted**: the VCS-lock write targets the PRIMARY partition dir via `placement_seam(...).read_dir(SPEC)`.
- **NFR-005**: Capture the interactive-latency baseline (`spec-kitty accept --diagnose` on the coord and flat fixtures) **as the very first action**, before any tree mutation. Nobody else can — every later WP has already changed the surface.
- **C-002 / SC-003**: This mission runs on coordination topology and cannot consolidate itself until this blocker is fixed. A mission must run claim→consolidation with zero manual intervention in the coord working tree.

**Done** = RED-first repro through the pre-existing entry point turns green; the baseline artifact is committed; escape-hatch/rollback regression tests remain green **unmodified** (NFR-004).

## Context & Constraints

- Spec: [spec.md](../spec.md) US3, FR-011, C-002, C-009. Plan: [plan.md](../plan.md) IC-01. Quickstart "Verifying the three live defects".
- **C-009**: never hand-commit into the coord working tree. If a defect forces it, that is mission evidence — record it in `tracers/tooling-friction.md`, do not work around it.
- Bugfix discipline (DIRECTIVE_041): the RED test must exercise the **pre-existing** entry point, not a bespoke harness. Live evidence over static-looks-fixed.
- **Baseline-red gotcha**: there are NO known baseline reds on base `6d9ed490d`. If an architectural test goes red it is yours until re-run on `upstream/main` proves otherwise.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `remediation/coord-lifecycle-gates`; completed changes merge back into `remediation/coord-lifecycle-gates`.
- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T001 – Capture the NFR-005 baseline (FIRST action)

- **Purpose**: NFR-005 is measured against a baseline that can only be captured before any WP mutates the tree.
- **Steps**: Run `spec-kitty accept --diagnose` against a coord fixture and a flat fixture; record wall-clock timings per gate. Append the numbers to `tracers/tooling-friction.md` (or a new `tracers/nfr005-baseline.md`) with the base sha `6d9ed490d`, the command, and per-gate timings — mission artifacts live under the mission dir, not in `owned_files`.
- **Notes**: This is the reference every downstream WP's ≤5s ceiling is measured against. Do this before T002.

### Subtask T002 – RED-first reproduction

- **Purpose**: Confirm the real mechanism, since the reported one is refuted.
- **Steps**: Inspect `implement.py:1166` and `:1760` (the lock write sites) and confirm the write resolves through `placement_seam(...).read_dir(SPEC)` to the PRIMARY partition. Write `tests/regression/test_issue_2795_claim_blocker.py` that drives a claim→consolidation on a coord fixture through the **existing** entry point and fails on the real blocker.
- **Files**: `tests/regression/test_issue_2795_claim_blocker.py` (new).
- **Notes**: If the observed blocker is on the primary checkout rather than coord, record that — it changes the fix (see T004).

### Subtask T003 – Fix at the reproduced site

- **Purpose**: Address the real cause.
- **Steps**: Correct the lock-write target / dirty-state classification at the reproduced site (`implement.py`; `git/ref_advance.py` dirty scan; `merge/preflight.py` classification). If the fix commits the VCS lock rather than dropping it, note that it **pre-empts part of IC-07(d)/WP14** — flag for WP14.
- **Files**: `implement.py`, `git/ref_advance.py`, `merge/preflight.py`.

### Subtask T004 – C-002 fallback (only if no repro within timebox)

- **Purpose**: The mission must not proceed on coord topology against an unexplained blocker.
- **Steps**: If no repro, convert IC-01 to a documented finding and choose exactly one: (a) pin `auto_commit=True` for this mission's own run, or (b) self-flatten this mission's topology for closeout. Record the choice and rationale in `tracers/design-decisions.md`.

### Subtask T005 – Turn the repro green

- **Steps**: Make `test_issue_2795_claim_blocker.py` pass; confirm `merge/preflight.py` classifies the lock write correctly (not as destructive dirt).

### Subtask T006 – NFR-004 regression check

- **Steps**: Run the shipped escape-hatch and rollback regression tests; they must stay green **without modification**.

## Test Strategy

- New: `tests/regression/test_issue_2795_claim_blocker.py` (RED→green through the pre-existing entry point).
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/regression/ -q` and the escape-hatch/rollback suites (NFR-004).

## Risks & Mitigations

- **Repro shows a different site** → fix changes; timeboxed, with the recorded C-002 fallback (T004).
- `implement_cores.py` is owned by WP14; if T003 must touch it, edit under a one-line rationale (leeway) — WP14 lands much later, no concurrency.

## Review Guidance

- Verify the repro drives the **pre-existing** entry point (not a bespoke harness).
- Verify the baseline artifact exists and predates any code change.
- Verify NFR-004 suites are untouched.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
