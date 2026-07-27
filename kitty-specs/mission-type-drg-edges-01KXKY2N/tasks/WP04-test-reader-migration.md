---
work_package_id: WP04
title: Test-reader migration to the seam fixture
dependencies:
- WP03
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/mission-type-drg-edges
merge_target_branch: feat/mission-type-drg-edges
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-drg-edges. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-drg-edges unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T034
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "350349"
shell_pid_created_at: "1784195968.54"
history:
- Seeded by /spec-kitty.tasks (edges-first two-phase decomposition)
agent_profile: python-pedro
authoritative_surface: tests/doctrine/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/doctrine/conftest.py
- tests/doctrine/test_service.py
- tests/doctrine/test_debugger_debbie_artifacts.py
- tests/doctrine/test_paula_patterns_artifacts.py
- tests/doctrine/test_mattpocock_skill_doctrine.py
- tests/doctrine/test_relationship_migration.py
- tests/doctrine/test_directive_consistency.py
- tests/doctrine/test_template_asset_e2e.py
- tests/doctrine/drg/test_resolve_transitive_refs.py
- tests/doctrine/drg/test_tiered_standards_non_orphan.py
- tests/doctrine/drg/test_glossary_node_kind.py
- tests/doctrine/drg/test_shipped_graph_valid.py
- tests/doctrine/drg/test_cross_grain_integrity.py
- tests/charter/test_surface_calibration.py
- tests/charter/test_model_task_routing_resolves.py
- tests/charter/test_merged_graph_on_live_path.py
- tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py
- tests/specify_cli/test_research_drg_nodes.py
- tests/specify_cli/test_documentation_drg_nodes.py
- tests/specify_cli/mission_step_contracts/test_research_composition.py
- tests/doctrine/drg/migration/test_path_ref_resolver.py
- tests/calibration/test_walker.py
- tests/architectural/test_builtin_override_policy.py
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

**Phase 2, #2680 — step 2 (FR-009).** Migrate every test module that reconstructs a `.../graph.yaml` monolith
path to **one shared seam fixture**, so that when WP05 deletes the monolith, no test breaks on a hardcoded
path. This WP is behavior-preserving: the monolith is still present, `load_graph_or_dir` reads it, everything
stays green. The **critical** one is `test_doctrine_regenerate_graph.py::_count_orphans` — it reads the
monolith directly AND is the orphan gate, so it must read through the seam/sharded layout or the gate breaks
in WP05.

## Context

**~22 test modules** each independently rebuild `parents[N] / "src"/"doctrine"/"graph.yaml"` (paula-patterns +
planner-priti post-task inventory — the original 16 PLUS 6 the first pass missed). There is no shared fixture
today. `tests/doctrine/conftest.py` already has a `SHIPPED_GRAPH_PATH` (`:26`) + a cached `graph` fixture
(`:63`) — extend that into the canonical seam-backed fixture the rest consume.

**The 6 readers the post-task squad added (T023) are load-bearing:** two of them
(`tests/architectural/test_builtin_override_policy.py`, `tests/doctrine/drg/migration/test_path_ref_resolver.py`)
sit inside the arch/freshness gates that WP05/WP06 assert green — miss them and WP05's own DoD is
unsatisfiable. Three (`test_research_drg_nodes.py`, `test_documentation_drg_nodes.py`,
`mission_step_contracts/test_research_composition.py`) use `graph.yaml`'s existence as a **repo-root
sentinel** — deleting it raises `RuntimeError("Could not locate repo root")`, so they need the sentinel
repointed to a delete-stable marker (`pyproject.toml`), not a seam swap.

## Subtasks

### T018 — Shared seam fixture in `conftest.py`

In `tests/doctrine/conftest.py`, add a session/module fixture (e.g. `built_in_graph`) backed by
`load_built_in_graph()` (the WP03 seam), and a `built_in_graph_dir` fixture backed by `built_in_graph_source()`.
Keep the existing caching intent (each `load_graph` is ~0.18 s). Retire the bespoke `SHIPPED_GRAPH_PATH`
string constant in favor of the seam source.

### T019 — Migrate the doctrine test modules

Repoint these to the fixture / seam (no local `.../graph.yaml` path constant remains):
`test_service.py`, `test_debugger_debbie_artifacts.py`, `test_paula_patterns_artifacts.py`,
`test_mattpocock_skill_doctrine.py`, `test_relationship_migration.py`, `test_directive_consistency.py`,
`test_template_asset_e2e.py`, `drg/test_resolve_transitive_refs.py`, `drg/test_tiered_standards_non_orphan.py`,
`drg/test_glossary_node_kind.py`, `drg/test_shipped_graph_valid.py`, `drg/test_cross_grain_integrity.py`.
Where a test does `merge_layers(load_graph(SHIPPED_GRAPH), None)`, use the fixture graph (already merged).

### T020 — Migrate the charter test modules [P]

`tests/charter/test_surface_calibration.py` (`_GRAPH_PATH`), `test_model_task_routing_resolves.py`
(`GRAPH_PATH`), `test_merged_graph_on_live_path.py` (`:117`). Same pattern.

### T021 — Make `_count_orphans` + the freshness twins LAYOUT-AGNOSTIC (the gate; DD-11 / renata M2)

In `tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py` — author these so they survive WP05's
monolith→fragments flip with **no further edit** (WP05 does NOT own this file):
- `_count_orphans` (`:47`) — repoint from raw `YAML().load(DOCTRINE_ROOT / "graph.yaml")` to
  `load_graph_or_dir(built_in_graph_source())`, counting orphans from **whatever layout is on disk**. Orphan
  gate stays green at 10 ≤ 14.
- `test_check_reports_committed_graph_fresh` (`:66`) — **drop** the `payload["path"].endswith("graph.yaml")`
  assertion (path-shape assertion breaks under fragments); assert freshness via the `--check` result, not the
  monolith filename.
- `test_regenerate_twice_is_byte_identical` (`:80-88`) — compare **per-fragment / per-file byte-identity over
  `built_in_graph_source()`** (iterate the dir's graph files), not `graph.yaml`'s bytes. This is the DD-11
  freshness contract (per-fragment byte-identity), valid for the monolith-as-single-file today and fragments
  after WP05.
- `test_check_detects_stale_graph` (`:103`) — repoint its write/read off `graph.yaml` to the dir/seam so it
  still exercises stale-detection under either layout.
- The phantom-java reader (`:134`) — repoint to the seam.
- Do **not** raise `DOCUMENTED_ORPHAN_RESIDUAL` (still 14).

### T022 — Full-suite green + zero residual monolith-path reads (grep-gate)

Run the affected suites and confirm zero regressions while the monolith is still present:
```
uv run pytest tests/doctrine tests/charter tests/calibration tests/architectural/test_builtin_override_policy.py \
  tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py \
  tests/specify_cli/test_documentation_drg_nodes.py tests/specify_cli/test_research_drg_nodes.py \
  tests/specify_cli/mission_step_contracts/test_research_composition.py -q
```
**Grep-gate (the WP is not done until this returns zero built-in-monolith reads):**
```
grep -rnE '"src"\s*/\s*"doctrine"\s*/\s*"graph.yaml"|shutil.copy.*graph\.yaml|/ "graph.yaml"|graph\.yaml"\)\.is_file' tests/ | grep -v conftest
```
Only the `conftest.py` seam source may reference the graph path. Everything else routes through the fixture.

### T034 — Route the 6 post-task-squad readers (specify_cli / calibration / arch + sentinels)

The first inventory missed these; each breaks on WP05's delete. Fix per its idiom:
- **Repo-root sentinels → stable marker**: `tests/specify_cli/test_research_drg_nodes.py:49`,
  `tests/specify_cli/test_documentation_drg_nodes.py:81` (+ its `:123` `graph.yaml` `read_text` FR-006 edge
  check → seam), `tests/specify_cli/mission_step_contracts/test_research_composition.py:93` — change the
  `_repo_root()` sentinel from `(parent/"src"/"doctrine"/"graph.yaml").is_file()` to a delete-stable marker
  like `(parent/"pyproject.toml").is_file()`.
- **Byte-identity twin → dir/seam**: `tests/doctrine/drg/migration/test_path_ref_resolver.py:358`
  (`test_shipped_graph_is_fresh`) — read via `built_in_graph_source()`; its byte-identity assertion follows the
  DD-11 per-fragment contract.
- **`shutil.copy` source → seam dir**: `tests/calibration/test_walker.py:131,144` — copy from
  `built_in_graph_source()` (the dir) instead of the hardcoded `graph.yaml` file.
- **`load_graph_or_dir` on a FILE path → dir/seam**: `tests/architectural/test_builtin_override_policy.py:40,69`
  — `_BUILT_IN_GRAPH` currently points at the `graph.yaml` file; point it at `built_in_graph_source()` (the
  dir) so `load_graph_or_dir` resolves the monolith today and fragments after WP05.

## Branch Strategy

- Planning/base + merge target: **`feat/mission-type-drg-edges`**. Lane worktree from `lanes.json`.
- Depends on WP03 (needs the seam): `spec-kitty agent action implement WP04 --agent claude`.

## Test strategy

This WP edits tests only; the guard is that the migrated suite stays green against the monolith. No new
behavior. The equality/silent-degrade proofs are WP06.

## Definition of Done

- [ ] `conftest.py` exposes a seam-backed `built_in_graph` / `built_in_graph_dir` fixture; `SHIPPED_GRAPH_PATH`
      string retired.
- [ ] All **22** listed modules (16 original + 6 from T023) read through the fixture / a delete-stable marker;
      no residual monolith-path reconstruction remains (grep-gate returns zero, T022).
- [ ] `_count_orphans` + the 4 freshness/stale twins are LAYOUT-AGNOSTIC (dir/seam-based, DD-11) so WP05 needs
      no ownership of `test_doctrine_regenerate_graph.py`; orphan gate green at 10 ≤ 14 (ceiling unchanged).
- [ ] The 3 repo-root sentinels use a delete-stable marker (`pyproject.toml`), not `graph.yaml` existence.
- [ ] Full doctrine + charter + calibration + the named specify_cli/arch suites green against the still-present
      monolith.
- [ ] ruff + mypy --strict clean; zero new suppressions.

## Risks & reviewer guidance

- **Do not overlap WP02's test files**: `test_mission_type_nodes.py` and `migration/test_extractor.py` are
  WP02's — do not touch them here.
- **Layout-agnostic is the whole point (renata M2)**: reviewer must confirm the `_count_orphans` + freshness
  twins read the dir (via `built_in_graph_source()`), so they survive WP05's monolith delete with no edit —
  otherwise WP05's "suites green" DoD is unsatisfiable because WP05 can't legally touch this file.
- **Sentinel trap (paula/priti)**: reviewer confirms the 3 `_repo_root()` finders no longer key on
  `graph.yaml` existence — else the repo-root locator breaks the instant the file is deleted.
- **grep-gate is the completion proof**: the T022 grep must return zero built-in-monolith reads (conftest
  seam excepted). WP04's own DoD is unsatisfiable if any of the 22 still reconstructs the path.

## Activity Log

- 2026-07-16T09:31:38Z – claude:sonnet:python-pedro:implementer – shell_pid=315724 – Assigned agent via action command
- 2026-07-16T09:58:29Z – claude:sonnet:python-pedro:implementer – shell_pid=315724 – Ready: 22 test readers migrated to built-in-graph seam. --force: kitty-specs-on-lane guard trips on INHERITED planning artifacts (drg-orphan-residual.md from unrelated mission 01KV0S99) merged from lane-c base; my commit 9ca8abfd3 touches tests/ ONLY (0 non-test files). grep-gate: zero built-in-monolith reads in owned files; layout-agnostic _count_orphans + byte-identity twins via built_in_graph_source(); 3 sentinels->pyproject.toml; suite green 4231 passed, monolith present; ruff clean
- 2026-07-16T09:59:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=350349 – Started review via action command
- 2026-07-16T10:09:49Z – user – shell_pid=350349 – Review passed (--force: guard trips on unrelated .kittify/charter/synthesis-manifest.yaml test-pollution, NOT WP04's diff which is tests-only 22 files). T018 seam fixtures present, SHIPPED_GRAPH_PATH retired. T021 gate layout-agnostic: _count_orphans via load_built_in_graph(), path-shape assertion dropped, byte-identity via genuine dir-enum _graph_files helper (degrades monolith->fragments), residual=14. T034: 3 sentinels->pyproject.toml, 3 squad readers->built_in_graph_source(). Grep-gate: all owned-file hits legit. Suite 4231 passed/1 skipped, 0 src changed, ruff clean.
