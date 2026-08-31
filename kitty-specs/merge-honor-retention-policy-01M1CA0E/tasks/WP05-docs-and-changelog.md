---
work_package_id: WP05
title: Docs, CLAUDE.md correction, specify opt-in, CHANGELOG
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- C-004
- C-005
- C-006
planning_base_branch: fix/3131-merge-retention
merge_target_branch: fix/3131-merge-retention
branch_strategy: Planning artifacts for this mission were generated on fix/3131-merge-retention. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3131-merge-retention unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
history:
- at: '2026-08-31T16:30:00Z'
  actor: claude
  action: created
agent_profile: scribe-sally
authoritative_surface: docs/guides/how-to/missions/
create_intent: []
execution_mode: code_change
owned_files:
- CLAUDE.md
- CHANGELOG.md
- docs/guides/how-to/missions/merge-mission.md
- packs/built-in/missions/mission-steps/software-dev/specify/prompt.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load scribe-sally` (role: implementer). Then read `plan.md` decision D-3 and `spec.md` C-004/C-005/C-006. Docs mirror SHIPPED behavior — implement AFTER WP02/03/04 land.

## Objective

Make the docs tell the truth about the new retention behavior and correct the
stale merge-preflight doc that the scouts found does not match the code.

## Context — read, do not re-derive
- **CLAUDE.md "Merge & Preflight Patterns" section** describes a
  `PreflightResult`/`run_preflight()`/`WPStatus` merge surface that DOES NOT
  EXIST in `src/specify_cli/merge/` (removed in the #2057 decomposition; the only
  `PreflightResult` is the unrelated sync daemon-ownership one). It is stale (C-005).
- `docs/guides/how-to/missions/merge-mission.md` — the merge how-to (carries an
  `updated:` frontmatter date → bump it when edited; docs-freshness SLA).
- `packs/built-in/missions/mission-steps/software-dev/specify/prompt.md` — the
  SOURCE specify prompt (edit the source, not the generated agent copies).

## Subtask guidance

### T017 — Correct the stale CLAUDE.md doc (C-005) + retain⇔keep mapping (C-004)
- Rewrite the "Merge & Preflight Patterns" `PreflightResult`/`run_preflight`/`WPStatus`
  description to match reality: that specific **API is absent** from the merge
  domain (note `src/specify_cli/merge/preflight.py` DOES exist but exposes a
  different API — git/target-branch/review-artifact preflights — and the only
  `PreflightResult` class is the unrelated sync daemon-ownership one). The
  retention conflict is surfaced through the merge-gates render path + the dry-run
  forecast. Keep the section accurate and concise.
- Add the retention policy: `retain_branches`/`retain_worktrees` in meta.json,
  fail-closed resolution (`CLI > meta > default`), and the mapping
  "`retain_branches` ⇔ effective `--keep-branch`; `retain_worktrees` ⇔ effective
  `--keep-worktree`."

### T018 — Merge how-to doc (C-006)
- In `docs/guides/how-to/missions/merge-mission.md`: document the retention
  policy, the fail-closed + explicit-override behavior, the coupled coordination
  teardown, and that the internal merge scratch worktree is always cleaned (not a
  retained resource). Bump the `updated:` frontmatter date.
- (CLI help text for the flags lives in `merge.py` and is delivered by WP02 — do
  not duplicate it here beyond a reference.)

### T019 — Specify prompt opt-in note
- In the specify SOURCE prompt, add a short note that a mission requiring workspace
  retention should declare it at create via `--retain-branches`/`--retain-worktrees`
  (the create-time opt-in from WP04). Keep it minimal; do not restructure the prompt.

### T020 — CHANGELOG
- Add a `### Fixed` entry under the current version referencing #3131: merge now
  honors mission retention policy (fail-closed); create-time opt-in flags. Bump the
  frontmatter `updated:` date.

## Branch Strategy
Planning base and final merge target: `fix/3131-merge-retention`. Depends on
WP02/WP03/WP04.

## Definition of Done
- CLAUDE.md no longer references the non-existent merge `PreflightResult` surface;
  retain⇔keep mapping documented.
- merge how-to + specify prompt reflect shipped behavior; `updated:` dates bumped.
- CHANGELOG entry present.
- `pytest tests/architectural/test_no_legacy_terminology.py` green (terminology guard).

## Test surface
`pytest tests/architectural/test_no_legacy_terminology.py -q` + docs-freshness gate.

## Reviewer guidance
- Confirm the CLAUDE.md correction is accurate against the actual merge code.
- Confirm no new docs PAGE was added (edits only) to avoid the docs-index triple-registration gates.
