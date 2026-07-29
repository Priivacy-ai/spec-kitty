---
work_package_id: WP06
title: Reader migration - doctrine, skills, completeness
dependencies:
- WP05
requirement_refs:
- C-008
- FR-002
- NFR-005
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T025
- T026
- T027
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/
create_intent:
- tests/architectural/test_issue_matrix_json_migration_completeness.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/skills/spec-kitty-implement-review/SKILL.md
- src/doctrine/skills/spec-kitty-mission-review/SKILL.md
- src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml
- tests/architectural/test_issue_matrix_json_migration_completeness.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Reader migration: doctrine, skills, completeness

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `implementer`

## Objective

Finish the C-008 issue-matrix reader migration on the **doctrine/skills** surface (M8), judge the `.md`-shaped **test fallout** (m3), and add a **completeness assertion** proving no live consumer parses markdown. The code consumers already inherit JSON via WP05's one canonical reader — this WP closes the doctrine + test + gate residue.

## Context — scope boundary (m2 / E2)

The **live** migration consumer set is: doctor, post-merge review, move-task/approval, finalize-lint, the `kind_for_mission_file` recognition consumers, the merge-driver + registration, and the doctrine skills. The **dashboard** (net-new build, follow-up **#3068**, parent epic #650) and **`merge_gates`** (net-new reader via FR-004/WP08) are **NOT** migration targets — do not "migrate" them.

## Subtasks

### T025 — M8: doctrine/skills `.md`→`.json` [P]
Update the issue-matrix references from `.md` to `.json` in:
- `src/doctrine/skills/spec-kitty-implement-review/SKILL.md`
- `src/doctrine/skills/spec-kitty-mission-review/SKILL.md` (incl. the mission-review gate definition + any `ISSUE_MATRIX_SCHEMA_DRIFT` reference)
- `src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml`
If a `mission-wrap-up-sequence.procedure.yaml` or `planning-and-tracking.styleguide.yaml` carries a live `issue-matrix.md` reference, update it too (record an out-of-map rationale). Then run `pytest tests/architectural/test_no_legacy_terminology.py` (≈0.1 s) — it is a CI-only gate; must stay green.

### T026 — m3: test fallout [P]
Judge each `.md`-shaped issue-matrix test as **stale-vs-valid** (per the failing-test-remediation framework): re-pin to `.json`, migrate the fixture, or delete an obsolete markdown-parser-only test. Prioritize the review-suite parser tests (`review/test_issue_matrix_validator.py`, `review/test_existing_matrix_remediation.py`, `review/test_issue_matrix_finalize_lint.py`). For a test owned by another WP's file, make a small **rationale-backed out-of-map edit** (the no-overlap rule is the real guard; a one-line rationale is acceptable).

### T027 — C-008 completeness assertion [P]
Add `tests/architectural/test_issue_matrix_json_migration_completeness.py`: assert no live consumer (doctor, review, finalize-lint, move-task, doctrine skills) parses `issue-matrix.md`; assert no code path emits `issue-matrix.md` going forward (failover-read of a legacy file is allowed). Explicitly exclude dashboard + `merge_gates` from the assertion set (net-new, not migration).

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP06` (depends on WP05).

## Definition of Done
- Doctrine/skills reference `.json`; `test_no_legacy_terminology.py` green.
- Test fallout judged (each: re-pin / migrate / delete with rationale).
- Completeness test green; dashboard/`merge_gates` correctly excluded.

## Risks / Reviewer guidance
- **Do not "migrate" the dashboard or `merge_gates`** — they are net-new (E2/m2).
- Do not delete a valid test to make the suite pass — judge stale-vs-valid honestly.
- **Commit each slice** so worktree progress is durable.
