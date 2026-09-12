---
work_package_id: WP09
title: Learned-facts seeding
dependencies: []
requirement_refs:
- FR-007
- C-003
- NFR-005
planning_base_branch: kitty/mission-workflow-self-doc
merge_target_branch: kitty/mission-workflow-self-doc
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-workflow-self-doc. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-workflow-self-doc unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-workflow-mechanics-self-doc-01M02SF1
base_commit: 2ea8f124cec22257f380f3cf4c16becd12407b3d
created_at: '2026-08-15T14:14:34.479690+00:00'
subtasks:
- T020
- T021
history: []
authoritative_surface: .kittify/memory/
create_intent:
- .kittify/memory/sync-identity-form-split.md
- .kittify/memory/lane-base-vs-moving-upstream.md
- .kittify/memory/no-recursionerror-is-not-no-cycle.md
execution_mode: code_change
owned_files:
- .kittify/memory/README.md
tags: []
tracker_refs: []
---

## Objective
Seed the git-tracked `.kittify/memory/` learned-facts store with the genuinely-narrow-but-shareable heuristics + a one-note format convention.

## Subtasks
- **T020** Add notes (each a short `.md`, stating its own "why it's here" per the README discipline): `sync-identity-form-split.md` (producer/consumer identity-form mismatch; the canonical `resolve_mission_identity` seam exists; ref #883), `lane-base-vs-moving-upstream.md` (guard a lane base against a FIXED rebase-target SHA, not `is-ancestor upstream/main` which advances → false BASE_STRANDED; CITE ADR `2026-07-29-1`, don't restate the recorded-planning-commit design), `no-recursionerror-is-not-no-cycle.md` (no crash ≠ no cycle; trace the call graph). RECONSIDER `collect-universe-once`: it's already embodied in `_gate_coverage.collect_universe` (code) — drop it or route to `EFFICIENT_LOCAL_TOOLING.md` rather than a note.
- **T021** Update `.kittify/memory/README.md` with a one-note format convention (each note declares its own rationale) so the store doesn't reproduce the grab-bag failure mode.

## Rules
Read `.kittify/memory/README.md` first for the store convention. `.venv/bin/python`, never bare `uv run`.

## Done
3 notes seeded (each self-justifying); README convention added; collect-universe adjudicated.
