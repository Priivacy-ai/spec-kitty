---
work_package_id: WP07
title: Parity, guards and overlay behavior
dependencies:
- WP04
- WP05
- WP06
requirement_refs:
- FR-008
- FR-009
- NFR-001
- NFR-006
planning_base_branch: feat/relocate-builtin-doctrine-packs
merge_target_branch: feat/relocate-builtin-doctrine-packs
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-builtin-doctrine-packs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-builtin-doctrine-packs unless the human explicitly redirects the landing branch.
created_at: '2026-07-30T19:45:00Z'
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 1 - Integrity
history:
- at: '2026-07-30T19:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: tests/doctrine/
create_intent:
- tests/doctrine/test_pack_relocation_identity.py
- tests/doctrine/test_pack_relocation_guard.py
- tests/doctrine/test_overlay_precedence.py
execution_mode: code_change
model: ''
owned_files:
- tests/doctrine/test_pack_relocation_identity.py
- tests/doctrine/test_pack_relocation_guard.py
- tests/doctrine/test_overlay_precedence.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP07 — Parity, guards and overlay behavior

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for the frontmatter profile first.
- **Profile**: `doctrine-daphne` · **Role**: `implementer` · **Agent/tool**: `claude`
Resolve with **`spec-kitty agent profile show doctrine-daphne`**. Do not read the raw `*.agent.yaml`.

---

## Objective
The non-fakeable proofs that the relocation preserved doctrine behavior. These are the acceptance gates for SC-001/002/003.

## Subtasks
### T019 — Full-projection identity (`test_pack_relocation_identity.py`) — NFR-001
- Load `graph-identity.baseline.json` (WP01). Assert post-move `load_built_in_graph()` projections **equal** it: nodes `(urn,label,sorted(tags))`, edges `(source,relation,target,when,reason)`. Cardinality 324/892 is a smoke check only. A dropped `when` gate must fail here.

### T020 — Three-part guard + loud-failure (`test_pack_relocation_guard.py`) — FR-009
- (1) *filesystem*: the moved trees are ABSENT under `src/doctrine/**` (exact set vs manifest). (2) *resolved-path*: every built-in resolution `is_relative_to(packs/built-in)`. (3) *anchor*: no `files("doctrine.<kind>")` content anchor remains (grep/AST).
- **Loud-failure**: parametrized over the 9 kinds, assert each repository's resolved `built_in_dir` **exists AND is non-empty** — a missed repoint returns `[]` build-green otherwise.

### T021 — Overlay behavioral test (`test_overlay_precedence.py`) — FR-008
- On a synthetic org+project overlay: (a) higher tier overriding a built-in URN wins (`built-in < org < project`); (b) `_tag_source` tags a moved built-in URN as `built-in` (origin tier, path-independent); (c) no built-in edge dropped when an overlay adds edges. Verify against `merge.py` semantics (additive edges; full-node replacement on override).

### T022 — Full doctor-health gate + charter catalog + clean-install load — NFR-006, NFR-002
- Assert `spec-kitty doctor doctrine --json` reports FULL health: `skipped_profiles == []`, 18/18 profiles valid, **no `org_drg` errors, no skipped glossary packs** (glossary_packs/built-in + assets/built-in moved — a profiles-only gate would miss their degradation), glossary term count unchanged (108).
- **Charter catalog non-empty** (the post-tasks BLOCKER guard): assert `charter.activation.catalog.load_doctrine_catalog()` returns **non-empty** built-in sets for the 7 catalog kinds — doctor does NOT exercise the catalog, so a missed `catalog.py` repoint (WP04) slips through every other gate.
- **Clean-install full-graph proof** (moved here from WP05 — depends on WP04+WP05): install the wheel in a clean venv and assert `load_built_in_graph()` returns the full-projection identity (324/892) — the packaged end-to-end proof of US3.

## Branch Strategy
Planning branch & merge target: `feat/relocate-builtin-doctrine-packs`. Worktrees per `lanes.json` lane.

## Definition of Done
- Identity assertion green against the baseline (full projection).
- Three-part guard + per-kind non-empty assertion green.
- Overlay behavioral test green; full doctor-health gate green.

## Risks
- Using bare triples instead of full projection would miss a `when` drop — use the full projection.
- A profiles-only doctor gate misses glossary/asset degradation — assert full health.

## Reviewer guidance
Confirm the identity test pins `when`; confirm the guard has all three parts + the non-empty per-kind loop.
