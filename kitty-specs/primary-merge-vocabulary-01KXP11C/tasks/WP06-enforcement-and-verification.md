---
work_package_id: WP06
title: Enforcement disclosure + verification wrap
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-009
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: feat/terminology-primary-merge-disambiguation
merge_target_branch: feat/terminology-primary-merge-disambiguation
branch_strategy: Planning artifacts for this mission were generated on feat/terminology-primary-merge-disambiguation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/terminology-primary-merge-disambiguation unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
phase: Phase 3 - Verification
assignee: ''
agent: "claude"
shell_pid: "1294336"
shell_pid_created_at: "1784232726.58"
history:
- at: '2026-07-16T18:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_no_legacy_terminology.py
role: reviewer
tags: []
task_type: review
---

# Work Package Prompt: WP06 – Enforcement disclosure + verification wrap

## ⚡ Do This First: Load Agent Profile
Load `reviewer-renata` via `/ad-hoc-profile-load`.

## Objectives & Success Criteria
- Verify SC-001..SC-006 against `quickstart.md`; confirm exempt-token invariance (SC-002) and occurrence_map per-category diff-compliance.
- All gates green with zero new suppressions; exempt-surface pins (`test_mission_runtime_surface`, `test_shared_package_boundary`, `test_tasks_compat_surface`) still green.
- Enforcement model honestly disclosed (FR-011). OPTIONALLY extend the terminology guard with non-Sense-C alias bans, gated on a zero-residual grep.

## Context & Constraints
- Depends on WP01–WP05.
- The terminology guard is a hardcoded 2-literal grep — it does NOT enforce sense-correctness. Any new alias ban must NOT red on legitimate/Sense-C residual (those persist until Track 2).

## Subtasks & Detailed Guidance
### T021 – SC-002 exempt-token invariance grep (quickstart) + occurrence_map diff-compliance.
### T022 – Run all gates: anti-sprawl `--strict`, description-length, relative-link, terminology guard (prove it executes, #2701), `ruff`, `mypy --strict`; confirm exempt-surface pins green.
### T023 – (optional) Add `"primary target"`/`"primary ref"` bans to `test_no_legacy_terminology.py` ONLY if `git grep` shows zero legitimate residual in scanned dirs (src/tests/docs); else document deferral to Track 2 (#2730).
### T024 – Confirm FR-011 disclosure present; run the `quickstart.md` SC walkthrough end-to-end.

## Test Strategy
- Full gate battery + `quickstart.md`. T023 is opt-in and MUST be preceded by a clean grep.

## Risks & Mitigations
- Repo-wide alias ban reds on residual → default to deferral; only ban after zero-residual proof.

## Review Guidance
- This WP is the mission's acceptance gate — do not approve on spot-checks; run the FULL arch suite.

## Activity Log
- 2026-07-16T18:15:00Z – system – Prompt created.
- 2026-07-16T20:06:51Z – claude – shell_pid=1278903 – Assigned agent via action command
- 2026-07-16T20:12:14Z – claude – shell_pid=1278903 – T021/T022 (aggregate SC verification) deferred to post-merge accept gate per lane-isolation — checklist authored; FR-011 confirmed; alias-ban deferred to Track 2 (60 residual, evidence-backed)
- 2026-07-16T20:12:20Z – claude – shell_pid=1294336 – Started review via action command
- 2026-07-16T20:12:31Z – user – shell_pid=1294336 – Verification-wrap decisions confirmed: FR-011/NFR-003/SC-006 disclosure present+honest; alias-ban correctly deferred to Track2 (#2730) per 60-residual evidence; post-merge accept checklist authored. Aggregate SC verification runs at accept.
