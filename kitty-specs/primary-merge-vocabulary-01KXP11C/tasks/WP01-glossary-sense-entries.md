---
work_package_id: WP01
title: Glossary sense entries (docs/context)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-004
tracker_refs: []
planning_base_branch: feat/terminology-primary-merge-disambiguation
merge_target_branch: feat/terminology-primary-merge-disambiguation
branch_strategy: Planning artifacts for this mission were generated on feat/terminology-primary-merge-disambiguation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/terminology-primary-merge-disambiguation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Vocabulary
assignee: ''
agent: "claude"
shell_pid: "1113770"
shell_pid_created_at: "1784229532.93"
history:
- at: '2026-07-16T18:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/context/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/context/orchestration.md
- docs/context/execution.md
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Glossary sense entries (docs/context)

## ⚡ Do This First: Load Agent Profile
Load `curator-carla` via `/ad-hoc-profile-load` before proceeding.

## Objectives & Success Criteria
- Author one canonical glossary entry per sense in `docs/context/` using the existing per-term table format (Definition / Context / Status / Applicable to / Do NOT use when / Related terms).
- 4 `primary` senses: **PRIMARY partition** (A), **Primary Branch** (B — extend the EXISTING entry, do not duplicate), **repository root checkout** (C — prose only; the Sense-C *symbols* stay Track 2), **target ref / commit target** (D).
- 3 `merge` operations: **lane consolidation** (1), **branch integration / git merge** (2), **publish to origin/main** (3).
- Gates green: description-length (≤180), anti-sprawl ratchet (`--strict`).

## Context & Constraints
- Canonical terms + authority: `research.md` table; charter §Branch-Intent Terminology Governance (Sense C = "repository root checkout").
- **C-006**: `docs/context/orchestration.md` is also edited by in-flight `mission-step-authority-01KXNZMT` — keep additions **append-only** blocks to minimize conflict.
- Occurrence map: this is `user_facing_strings`/doc authoring — no code symbol touched.

## Subtasks & Detailed Guidance
### T001 – primary Sense-A + Sense-D entries (orchestration.md)
- Add "PRIMARY partition" and "target ref / commit target" entries; `Do NOT use when` steers readers off bare "primary".
### T002 – primary Sense-B extend + Sense-C prose (execution.md)
- Extend existing "Primary Branch" entry cross-refs (D1 — keep the term); add/confirm "repository root checkout" entry; note the code symbols are unchanged this slice (Track 2).
### T003 – merge Sense 1/2/3 entries (orchestration.md)
- lane consolidation (`merge_lane_to_mission`), branch integration (`merge_mission_to_target`, `git merge`), publish to origin (`push_requested`).
### T004 – cross-links + Do-NOT-use guidance
- Wire `Related terms` between the new entries and existing Base/Current/Target/Merge-Target Branch entries.

## Test Strategy
- No unit tests; validation is the docs gates. Run: anti-sprawl ratchet `--strict`, description-length gate.

## Risks & Mitigations
- Hot-file collision on `orchestration.md` (C-006) → append-only blocks; coordinate land order with `mission-step-authority`.

## Review Guidance
- Confirm every sense has exactly one entry, no duplication of "Primary Branch", Sense-C is prose-only.

## Activity Log
- 2026-07-16T18:15:00Z – system – Prompt created.
- 2026-07-16T19:06:44Z – claude – shell_pid=1075941 – Assigned agent via action command
- 2026-07-16T19:13:01Z – claude – shell_pid=1075941 – Glossary sense entries authored
- 2026-07-16T19:19:00Z – claude – shell_pid=1113770 – Started review via action command
- 2026-07-16T19:21:39Z – user – shell_pid=1113770 – APPROVED: 7 sense entries (primary A/B/C/D + merge 1/2/3) in per-term table format with Do-NOT-use-when + resolving cross-links; scope=2 owned docs only, no code/serialized-key touched; Primary Branch extended not duplicated (D1); Sense-C prose-only w/ explicit Track-2 (#2730) disclaimer; append-only (C-006). Gates green in lane worktree: anti-sprawl --strict 0, description-length 0/459, terminology 3 passed.
