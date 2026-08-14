---
work_package_id: WP09
title: Reflexivity — In-Flight Mission Census & PR Description
dependencies:
- WP02
- WP03
- WP05
- WP06
- WP08
requirement_refs: []
subtasks:
- T041
- T042
- T043
- T044
phase: Phase 4 - Closeout (sequential, last)
history:
- at: '2026-08-14T02:50:21Z'
  actor: system
  action: Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)
agent_profile: ''
authoritative_surface: kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/
create_intent: []
execution_mode: planning_artifact
model: ''
owned_files: []
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – Reflexivity — In-Flight Mission Census & PR Description

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, or select via `spec-kitty agent profile list` for an
`implement`-typed WP whose surface is verification/documentation, not new production
code.

---

## Objectives & Success Criteria

Implement Story 6 / FR-009: state plainly what happens to every other mission
currently in flight when this change lands, including confirmation that this mission's
own spec.md does not block. This is the mission's own close-out step.

Success: the implementing PR's description names any currently in-flight mission (at
merge time) whose spec.md would newly block under the shipped detector, and states the
operator-facing remediation.

## Context & Constraints

- **This WP depends on every other implementation WP (WP02, WP03, WP05, WP06, WP08)
  having landed** — it audits the *shipped* detector's real-world blast radius, not a
  plan-time projection. It is the mission's last step by design.
- Read plan.md's "Reflexivity (Story 6 / FR-009)" section — it already confirms, at
  plan time, that this mission's own spec.md contains zero bare-prose requirements
  (every FR/NFR/C row is a proper markdown table row). This WP re-confirms that live,
  against the shipped detector, not the plan-time claim alone.
- Per spec.md: **no code-level grandfathering is proposed** — the remediation for any
  newly-blocking in-flight mission is to rewrite its bare-prose requirements into a
  declared shape.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `pr/bare-prose-requirements-uncounted`;
  completed changes must merge back into `pr/bare-prose-requirements-uncounted`
  (base `op/3394-requirement-citation-scope` @ `ab15225ea`).
- **Planning base branch**: `pr/bare-prose-requirements-uncounted`.
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

## Subtasks & Detailed Guidance

### Subtask T041 – Run the census

- **Purpose**: FR-009's in-flight mission census, deferred to implementation/close-out
  time since the in-flight set changes daily.
- **Steps**: Run the finished, fully-wired `find_bare_prose_requirement_ids` against
  every `kitty-specs/*/spec.md` belonging to a mission not yet merged at the time this
  WP executes. Record which ones would newly block.

### Subtask T042 – Re-confirm this mission's own spec.md

- **Purpose**: Story 6 AC2.
- **Steps**: Re-run the shipped detector against this mission's own
  `kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/spec.md` and confirm it does
  not block, live — do not rely solely on plan.md's plan-time claim.

### Subtask T043 – Draft the PR description content

- **Purpose**: FR-009's operator-facing disclosure requirement.
- **Steps**: Name any newly-blocking in-flight missions found in T041, and state the
  remediation path (rewrite bare-prose requirements into a declared shape — no
  code-level grandfathering).

### Subtask T044 – Final close-out verification

- **Purpose**: NFR-003/NFR-004 close-out; confirm the mission's overall test/lint state
  before the PR is marked ready.
- **Steps**: Run the full Targeted Test Surface one final time (never the full
  `pytest tests/`):
```bash
PWHEADLESS=1 pytest \
  tests/specify_cli/test_requirement_mapping.py \
  tests/specify_cli/test_requirement_mapping_coord_surface.py \
  tests/next/ tests/specify_cli/next/ tests/runtime/ \
  tests/architectural/test_bare_prose_corpus_ratchet.py \
  tests/architectural/test_bridge_cores_import_boundary.py \
  -n 8 --dist loadfile -q
```
  Then run `ruff check` and `mypy --strict` on every file this mission touched;
  confirm zero new issues/suppressions.

## Test Strategy

- No new test file. This WP's own "test" is T044's final full targeted-surface run.

## Risks & Mitigations

- A stale census (run too early, missing a mission that entered the in-flight set
  later) — mitigated by this WP's sequencing (last, as close to actual merge time as
  the mission's own execution allows).

## Review Guidance

- Confirm the PR description actually contains the T041 census results and the T043
  remediation statement — not merely a claim that it was checked.
- Confirm T044's `ruff`/`mypy --strict` run is clean with zero new suppressions.

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
