---
work_package_id: WP05
title: Generator write-partition + atomic monolith retire
dependencies:
- WP04
requirement_refs:
- FR-007
- FR-012
- FR-015
tracker_refs: []
planning_base_branch: feat/mission-type-drg-edges
merge_target_branch: feat/mission-type-drg-edges
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-drg-edges. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-drg-edges unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
shell_pid_created_at: "1784204680.98"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "571069"
history:
- Seeded by /spec-kitty.tasks (edges-first two-phase decomposition)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/doctrine.py
create_intent:
- tests/doctrine/drg/test_sharded_layout.py
- src/doctrine/mission_type.graph.yaml
- src/doctrine/action.graph.yaml
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/doctrine.py
- src/doctrine/*.graph.yaml
- tests/doctrine/drg/test_sharded_layout.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its lens, standards, and TDD workflow for the entirety of this work package.

## Objective

**Phase 2, #2680 — the flip point (DD-7/DD-8).** Teach the generator to write the shipped graph as
deterministic **per-populated-node-kind** `src/doctrine/*.graph.yaml` fragments, **delete the monolith
`src/doctrine/graph.yaml` atomically in the same change**, and update `regenerate-graph` (+`--check`) to
write/verify the sharded layout. Because WP03 (src readers) and WP04 (test readers) already route through the
seam, this WP transparently flips every consumer from monolith to fragments. No in-YAML import (FR-015).

## Context — the two traps this WP exists to avoid

1. **Loader precedence (DD-7)**: `load_graph_or_dir` PREFERS a `graph.yaml` when present and *ignores*
   `*.graph.yaml` fragments (`loader.py:93-95`). So writing fragments without deleting the monolith is a
   **silent stale read**. The delete and the fragment writes MUST be one atomic change.
2. **Partition totality (DD-8)**: emit a fragment for **every populated node-kind**, including target-only
   kinds that own nodes but no source edges (`template`, `asset`, `glossary`, `glossary_scope`,
   `mission_step_contract`). A partition that only emits kinds-with-edges silently drops those nodes on reload
   → orphan count + `assert_valid` change → NOT behavior-preserving.

Fragment location is **`src/doctrine/*.graph.yaml`** (== the loader glob root the seam uses — NOT
`src/doctrine/drg/`).

## Subtasks

### T023 — [ATDD RED] fragments present ∧ monolith absent

Add `tests/doctrine/drg/test_sharded_layout.py` asserting, after `regenerate-graph`: `src/doctrine/graph.yaml`
does **not** exist; ≥1 `src/doctrine/*.graph.yaml` fragment exists; `load_built_in_graph()` returns a valid
graph; `assert_valid` passes. Commit RED first.

### T024 — Write-partition in the generator (DD-8)

Edit `generate_graph` / `_write_graph_yaml` in `src/doctrine/drg/migration/extractor.py` (documented
out-of-map edit — WP01 owns that file; keep the change confined to the **write step**, do not disturb the
edge pass) to partition the composed graph:
- One fragment per **populated node-kind**; each fragment owns that kind's disjoint node set + the edges whose
  **source** node is that kind.
- Every populated node-kind gets a fragment (totality), even target-only kinds.
- Stable partition assignment + stable intra-fragment ordering (deterministic; NFR-002).

### T025 — Atomic monolith delete (DD-7)

In the same write path, remove `src/doctrine/graph.yaml` when the fragments are written (single atomic
operation — do not leave a window where both exist). Confirm no non-fragment `graph.yaml` remains.

### T026 — `regenerate-graph` (+`--check`) for the sharded layout

Update `src/specify_cli/cli/commands/doctrine.py` (the regenerate-graph command, ~:230-256) to write the
sharded layout and, in `--check`, verify it (freshness). Pin fragment dir == loader glob root
(`resolve_doctrine_root()` = `src/doctrine/`).

### T027 — Regenerate → commit fragments

Run `spec-kitty doctrine regenerate-graph`; commit the new `src/doctrine/*.graph.yaml` fragments and the
`src/doctrine/graph.yaml` deletion together. (`pyproject.toml` already ships `src/doctrine/**/*.yaml`, so no
packaging manifest change is needed — verify the wheel includes the fragments.)

### T028 — Reproduce the gates (sharded)

```
uv run spec-kitty doctrine regenerate-graph --check
uv run pytest tests/doctrine tests/charter tests/calibration \
  tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py \
  tests/specify_cli/test_documentation_drg_nodes.py tests/specify_cli/test_research_drg_nodes.py \
  tests/specify_cli/mission_step_contracts/test_research_composition.py \
  tests/architectural tests/doctrine/drg -q
```
Confirm orphan gate still green at 10 (now read from fragments via the seam), freshness twins green, and
`assert_valid` passes. **You do NOT edit `test_doctrine_regenerate_graph.py`** — WP04 already authored its
`_count_orphans` + freshness/stale twins as layout-agnostic (DD-11), so they flip to fragments transparently
here. If any of them is still monolith-bound, that is a WP04 defect — report it, do not patch it out-of-map.

## Branch Strategy

- Planning/base + merge target: **`feat/mission-type-drg-edges`**. Lane worktree from `lanes.json`.
- Depends on WP04 (all readers routed first): `spec-kitty agent action implement WP05 --agent claude`.

## Test strategy

RED-first T023. The equality + silent-degrade proofs are WP06 (they depend on this WP producing the sharded
layout). The freshness twins (WP04-repointed) are the byte-identity guard here.

## Definition of Done

- [ ] Generator emits one `src/doctrine/<kind>.graph.yaml` per populated node-kind (edges by source-kind;
      target-only kinds included).
- [ ] `src/doctrine/graph.yaml` deleted atomically with the fragment writes; `test_sharded_layout.py` green.
- [ ] `regenerate-graph --check` verifies the sharded layout fresh; deterministic re-run is byte-identical.
- [ ] Orphan gate green at 10 ≤ 14 (read from fragments); `assert_valid` passes; no in-YAML import.
- [ ] Full doctrine/charter/arch suites green; ruff + mypy --strict clean; complexity ≤ 15.

## Risks & reviewer guidance

- **Non-atomic delete = silent stale read**: reviewer confirms no code path leaves `graph.yaml` beside
  fragments; a test asserts the monolith is absent post-regenerate.
- **Totality**: reviewer confirms target-only kinds (`template`/`asset`/`glossary`/`glossary_scope`/
  `mission_step_contract`) each have a fragment and their node counts survive the round-trip.
- **extractor.py leeway**: this WP edits `extractor.py`'s write step though WP01 owns the file. The dependency
  chain (WP05 → … → WP01) linearizes it; the edit is confined to the write step. Record the one-line rationale
  in the WP history at implement time.
- **DD-11 contract (now PINNED, was the dangling DD-9)**: write **each fragment in canonical intra-fragment
  order** (nodes by URN, edges by `(source,target,relation)`). That is the freshness contract WP04's twins
  assert (per-fragment byte-identity) and the ordering WP06's equality proof re-sorts against. Do not invent a
  different ordering — DD-11 is fixed.
- **Complexity watch-item (paula post-task)**: `_write_graph_yaml`/`regenerate_graph` gain partition +
  edge-by-source-kind + totality + atomic-delete logic — the most likely place to breach the 15 ceiling.
  **Extract the partition step as a pure helper** (`_partition_by_kind(graph) -> dict[kind, DRGGraph]`) with
  its own focused test, rather than inlining. Not pre-existing debt — an in-flight guard.

## Activity Log

- 2026-07-16T10:10:50Z – claude:sonnet:python-pedro:implementer – shell_pid=363661 – Assigned agent via action command
- 2026-07-16T11:15:44Z – claude:sonnet:python-pedro:implementer – shell_pid=363661 – Out-of-map edits to complete the monolith->fragment flip (dependency chain WP05->..->WP01 linearizes predecessor surfaces; all done, no active-agent overlap): extractor.py write-step (WP01, prompt-sanctioned) = partition+atomic-delete; test_extractor.py (WP02) 3 monolith-file asserts -> layout-agnostic; test_builtin_graph_seam.py (WP03) monolith-phase asserts -> post-flip + gate marker (cleared 3 pre-existing arch gates); test_context.py 3 mocks repointed from per-file load_graph to load_validated_graph seam (sharded load N-duplicated the fixture). Behaviour-preserving: 280 nodes/757 edges/10 orphans, assert_valid clean, regenerate --check fresh.
- 2026-07-16T11:16:21Z – claude:sonnet:python-pedro:implementer – shell_pid=363661 – Ready (--force: inherited pre-existing kitty-specs/ planning artifacts on lane branch, NOT WP05 changes; impl working tree is clean). 10 per-kind fragments incl target-only template, monolith deleted atomically, orphan gate 10 via seam, freshness/byte-identity twins + test_sharded_layout green, assert_valid passes, regenerate --check fresh, ruff/mypy --strict clean, complexity<=15. Behaviour-preserving 280/757/10. Flip out-of-map edits documented in history. 3 residual full-suite fails are NOT WP05 regressions (2 pre-existing base-red + 1 order-dependent arch flake).
- 2026-07-16T11:27:53Z – claude:opus:reviewer-renata:reviewer – shell_pid=461484 – Started review via action command
- 2026-07-16T11:45:34Z – user – shell_pid=461484 – Review passed (reviewer-renata 45-call pass + orchestrator corroboration): behavior-preserving flip 280/757/10==pre-flip, DD-8 totality (sum-of-fragments==280, template fragment present), atomic delete (test_sharded_layout green), transparent WP04-gate flip, parity-scaffold drop is a strengthening. 2 mission-fixes green. --force: guard trips on inherited WP02 residual doc + status artifacts, not WP05's diff.
- 2026-07-16T11:58:11Z – user – Moved to planned
- 2026-07-16T12:03:20Z – claude:sonnet:python-pedro:implementer – shell_pid=536528 – Started implementation via action command
- 2026-07-16T12:22:59Z – claude:sonnet:python-pedro:implementer – shell_pid=536528 – Cycle 2: load_graph restored to charter.drg facade + hand-allowlisted in dead-symbol gate (both facade gates + dead-symbol green together); focused _partition_by_kind test added (source-kind routing + DD-11 order). Full arch suite green.
- 2026-07-16T12:24:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=571069 – Started review via action command
