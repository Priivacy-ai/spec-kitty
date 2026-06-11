---
work_package_id: WP11
title: '#391 doctrine usage-test (validation)'
dependencies:
- WP04
- WP05
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
agent: "claude:opus:tbd:implementer"
shell_pid: "874911"
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: planner-priti
authoritative_surface: docs/development/391-doctrine-usage-test.md
execution_mode: code_change
owned_files:
- docs/development/391-doctrine-usage-test.md
role: planner
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load planner-priti`.

## Objective
**Dogfood** the new doctrine (WP04/WP05) by organizing the #391 epic's CURRENT state — inventory, classify residual OPEN children, reparent/collapse only where the procedure prescribes; **#391 itself stays OPEN** as the canonical debt bucket (operator decision 2026-06-11; SC-6 amended — the close-as-superseded wording predated the 2026-06-09 restructure) — using *only* the authored procedure/styleguide/toolguide (FR-012, SC-1/SC-6). NOTE: #391 is already substantially organized (57 sub-issues, majority closed); honest recording of 'already-organized' findings IS valid SC-1 evidence.

## Context
- #391 ("Tech/Functional Debt Remediation") is a dumping ground, not a coherent functional epic (operator aside). This WP validates the doctrine on a real messy epic.
- Apply the WP04 procedure + WP05 styleguide + toolguide verbatim; follow the toolguide's gh/GraphQL mechanics + rate-limit guidance and the community-precedence rule.
- Tracker-only mutations (no repo source files); the deliverable record is the owned `docs/development/391-doctrine-usage-test.md` (a planning artifact).
- NOTE: the `work/` traces cited here predate the 2026-06-09 tracker cleanup — re-verify referenced tickets/epics against the live tracker at claim time.

## Subtasks
### T032 — Classify + propose
Inventory #391's children; classify (functional/meta/orphan/closed) per the procedure; propose reparenting to functional homes. Record proposal in `docs/development/391-doctrine-usage-test.md`.
### T033 — Execute
Reparent residual OPEN children where the procedure prescribes (native sub-issues; node-id-vs-db-id per toolguide); apply community-precedence on any dedup; post a status comment on #391 recording the doctrine-driven organization pass — do NOT close #391.
### T034 — Record + validate
Capture the run in `docs/development/391-doctrine-usage-test.md`; assess whether the doctrine alone was sufficient (SC-1); note any doctrine gaps found (feeds back to WP04/WP05).

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json`.

## Ownership & out-of-map edits
Owned: the `docs/development/391-doctrine-usage-test.md` record. Tracker operations are external (GitHub). **Out-of-map edits allowed with a recorded one-line rationale** (e.g. a doctrine wording fix discovered during the dogfood — flag back to WP04/WP05).

## Review / Sign-off (R-07)
Reviewer profile (reviewer-renata); success = SC-1/SC-6 demonstrated (doctrine sufficient; #391 organized per doctrine, remains open).

## Definition of Done
- #391 organized per the doctrine (residual open children classified/reparented where prescribed; #391 stays open); usage-test record written; doctrine-sufficiency assessed (gaps, if any, fed back).

## Risks
- Doctrine gaps surface mid-dogfood — that's the point; record them rather than improvising silently (validates the doctrine).

## Activity Log

- 2026-06-11T15:44:40Z – claude:opus:tbd:implementer – shell_pid=874911 – Assigned agent via action command
- 2026-06-11T18:57:19Z – claude:opus:tbd:implementer – shell_pid=874911 – Moved to for_review
