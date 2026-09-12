---
work_package_id: WP12
title: media→assets (+README logo) + operations/changelog rehome & fold
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-012
- FR-013
- FR-014
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: docs/assets/
create_intent: []
execution_mode: code_change
owned_files:
- media/**
- docs/assets/**
- README.md
- docs/operations/**
- docs/changelog/**
- docs/release-goals/**
- docs/archive/**
- HOW_TO_MAINTAIN.md
- docs/p0-baseline-refresh.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load curator-carla
```

## Objective
Move `media/` into `docs/assets/` (with the README logo fix), rehome the operations docs, and fold
`release-goals/` + `archive/` into `changelog/`. See [occurrence_map.yaml](../occurrence_map.yaml) manual_rewrites + moves.

## Subtasks
- **T034** — Move `media/` → `docs/assets/`. **Manually** rewrite `README.md:2` — the logo is an absolute
  HTML `<img src="https://github.com/Priivacy-ai/spec-kitty/raw/main/media/logo_small.webp">` that
  `relative_link_fixer` will NOT touch; repoint it to `docs/assets/logo_small.webp` (note it resolves on
  GitHub/PyPI only once merged to main). Update any other `media/` refs.
- **T035** — Rehome `HOW_TO_MAINTAIN.md` → `docs/operations/`, `docs/p0-baseline-refresh.md` →
  `docs/operations/`; fold `docs/release-goals/` (dedup its README/index) and `docs/archive/` (14 files)
  → `docs/changelog/`. `docs/archive/` holds 14 baseline redirect *targets* — record these in the
  fragment so WP13 re-points the prior redirects (NFR-010 coverage).
- **T036** — operations/ + changelog/ `index.md`; kebab-case; migrate free-text `audience:`; **rewrite
  phase** (separately reviewed) with the NFR-009 fidelity ledger. Record all moves in the fragment.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- media→assets with README logo rewritten + verified; ops docs rehomed; release-goals + archive folded
  into changelog with the 14 prior-redirect targets recorded for WP13; index/kebab/audience done;
  rewrite ledgered. Fragment recorded.

## Risks
- README logo is the highest-visibility landmine — verify the raw URL path after the move.
- archive/ retirement collides with prior redirect coverage — the fragment MUST list the 14 targets so
  WP13 preserves coverage (NFR-010).
