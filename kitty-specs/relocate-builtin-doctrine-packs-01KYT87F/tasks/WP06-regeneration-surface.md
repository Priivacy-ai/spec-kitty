---
work_package_id: WP06
title: Graph-regeneration surface repoint
dependencies:
- WP03
- WP04
requirement_refs:
- FR-010
- FR-013
planning_base_branch: feat/relocate-builtin-doctrine-packs
merge_target_branch: feat/relocate-builtin-doctrine-packs
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-builtin-doctrine-packs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-builtin-doctrine-packs unless the human explicitly redirects the landing branch.
created_at: '2026-07-30T19:45:00Z'
subtasks:
- T016
- T017
- T018
phase: Phase 1 - Integrity
history:
- at: '2026-07-30T19:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/drg/migration/
create_intent:
- tests/doctrine/drg/test_regen_roundtrip.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/migration/extractor.py
- src/specify_cli/cli/commands/doctrine.py
- tests/doctrine/drg/test_graph_sharding_equality.py
- tests/doctrine/drg/test_sharding_silent_degrade.py
- tests/doctrine/drg/migration/test_extractor.py
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/doctrine/drg/migration/test_path_ref_resolver.py
- tests/doctrine/drg/test_regen_roundtrip.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP06 — Graph-regeneration surface repoint

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for the frontmatter profile first.
- **Profile**: `doctrine-daphne` · **Role**: `implementer` · **Agent/tool**: `claude`
Resolve with **`spec-kitty agent profile show doctrine-daphne`**. Do not read the raw `*.agent.yaml`.

---

## Objective
Keep `spec-kitty doctrine regenerate-graph` working after the flatten move. The extractor and `_doctrine_root()` hardcode `src/doctrine/<kind>/built-in/…` and the two-level nesting; without repointing, regeneration scans an emptied tree and writes fragments to the wrong home — a silent, build-green break of the "fragments are generated, not hand-maintained" invariant. **Not severable.**

## Subtasks
### T016 — Repoint `_doctrine_root()` (`specify_cli/cli/commands/doctrine.py`)
- Its detection (`(src_doctrine/"directives"/"built-in").is_dir()`) and its use as the fragment **write-target** must resolve the flattened `packs/built-in/` home (via `resolve_pack_root("built-in")` where in-layer, else an equivalent that respects layering — `doctrine.py` is specify_cli, so importing the resolver is allowed).

### T017 — Repoint `extractor.py` (BOTH directions)
- `_PATH_KIND_PATTERNS` (lines ~60–107) are hardcoded `src/doctrine/<kind>/built-in/…$` regexes; rewrite them for the **flattened** `packs/built-in/<kind>/…$` layout (drop the inner `built-in`). Repoint the content walks (`extractor.py:477` and siblings) from `doctrine_root/<kind>/"built-in"` to `packs/built-in/<kind>/`.
- **Both directions**: extraction *writes* `src:` path-refs into the fragments and projection *reads* them back — verify the rewritten patterns match the `src:` paths recorded **inside** the moved `*.graph.yaml` fragments, not just the walk root.

### T018 — Fix the 5 regen-parity tests + a NEW committed round-trip test
- Update the 5 existing tests to the new home/layout. **Change only path/layout literals — do NOT weaken any assertion** (reviewer must diff for assertion-strength changes; this WP owns both the production regex and its guards — the self-marking trap).
- **New** `tests/doctrine/drg/test_regen_roundtrip.py` (distinct from the 5): run `spec-kitty doctrine regenerate-graph` and assert regenerated fragments == the moved fragments as a **full projection** (incl. `when`) — a committed test, not a manual command.

## Branch Strategy
Planning branch & merge target: `feat/relocate-builtin-doctrine-packs`. Worktrees per `lanes.json` lane.

## Definition of Done
- `regenerate-graph` writes to `packs/built-in/` and round-trips to identical fragments.
- The 5 regen-parity tests pass against the flattened home.
- `mypy --strict` + `ruff` clean.

## Risks
- Flatten breaks the regex patterns — rewrite them, don't just swap the root prefix.
- Regeneration writing to the old/wrong home — assert the write-target explicitly.

## Reviewer guidance
Confirm the round-trip test actually runs regeneration and diffs full projections (not counts); confirm patterns dropped the inner `built-in` level.
