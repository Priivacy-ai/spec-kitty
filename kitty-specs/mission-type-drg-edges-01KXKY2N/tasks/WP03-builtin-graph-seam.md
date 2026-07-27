---
work_package_id: WP03
title: Canonical built-in-graph seam + src readers
dependencies:
- WP02
requirement_refs:
- FR-008
- FR-014
- FR-016
tracker_refs: []
planning_base_branch: feat/mission-type-drg-edges
merge_target_branch: feat/mission-type-drg-edges
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-drg-edges. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-drg-edges unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "270037"
shell_pid_created_at: "1784193403.04"
history:
- Seeded by /spec-kitty.tasks (edges-first two-phase decomposition)
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/loader.py
create_intent:
- tests/doctrine/drg/test_builtin_graph_seam.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/drg/loader.py
- src/doctrine/agent_profiles/repository.py
- src/doctrine/agent_profiles/schema_models.py
- src/doctrine/agent_profiles/profile.py
- src/specify_cli/doctrine/pack_validator.py
- src/specify_cli/calibration/walker.py
- src/specify_cli/charter_runtime/lint/_drg.py
- src/charter/_drg_helpers.py
- src/charter/compiler.py
- src/charter/reference_resolver.py
- src/specify_cli/cli/commands/charter/_status_collectors.py
- src/specify_cli/cli/commands/_doctrine_collect.py
- src/specify_cli/cli/commands/_profile_health_render.py
- src/specify_cli/doctrine/snapshot.py
- src/doctrine/directives/**
- src/doctrine/procedures/**
- src/doctrine/tactics/**
- src/doctrine/paradigms/**
- src/doctrine/styleguides/**
- src/doctrine/shared/**
- tests/doctrine/drg/test_builtin_graph_seam.py
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

**Phase 2, #2680 — step 1 of the sharding migration (paula-patterns finding, DD-6).** Introduce ONE canonical
built-in-graph seam and route **every source reader** of the shipped graph through it. This is
**behavior-preserving**: the monolith `src/doctrine/graph.yaml` is still present, and `load_graph_or_dir`
reads it (it prefers the monolith when present — `loader.py:93`). Nothing switches to fragments yet. The point
is that once every reader goes through the seam, WP05 can delete the monolith and every consumer transparently
flips to fragments with no further edits. Without this seam first, sharding is a whack-a-field edit across ~22
sites.

## Context — the reader inventory (from the post-plan squad)

Four bespoke src path-builders read the monolith by hardcoded path and MUST route through the seam:
- `src/doctrine/agent_profiles/repository.py` — `_default_drg_path()` (~:270-278) returns a **file**
  (`files("doctrine").joinpath("graph.yaml")`) consumed at `:289`. **The real path has NO `drg/` segment.**
  It catches `DRGLoadError` and degrades to an empty graph → route it to return the **dir** via the seam.
- `src/specify_cli/doctrine/pack_validator.py:513` — `load_graph(resolve_doctrine_root() / "graph.yaml")`.
- `src/specify_cli/calibration/walker.py:430-437` — `_built_in_graph_path()` → `.../src/doctrine/graph.yaml`;
  `_build_graph` is **unwrapped** (would hard-crash on delete without the seam).
- `src/specify_cli/charter_runtime/lint/_drg.py:52,85` — `_load_built_in_drg()` candidate loop on
  `.../graph.yaml`; returns `None` → `GraphState.MISSING` on degrade.

Six consumers already use `load_graph_or_dir(resolve_doctrine_root())` (shard-safe) — route them through the
seam too, for uniformity: `_drg_helpers.py:83`, `compiler.py:819`, `reference_resolver.py:57`,
`cli/commands/charter/_status_collectors.py:451`, `cli/commands/_doctrine_collect.py:418`,
`cli/commands/_profile_health_render.py:301`.

**OUT of scope** — org-pack fragment readers (they read `pack/drg/*.graph.yaml`, NOT the built-in graph):
`pack_assembler.py:209`, `pack_validator.py:527/:977`. Do not touch them.

## Subtasks

### T011 — Add the seam + unit test

In `src/doctrine/drg/loader.py`, add:
- `built_in_graph_source() -> Path` returning `resolve_doctrine_root()` (the fragment/monolith **directory**).
- `load_built_in_graph() -> DRGGraph` = `load_graph_or_dir(built_in_graph_source())`.

Keep the current import-time/call-time discipline: call the seam where today's readers call (lazy /
function-local where the current site is — NFR-004; no new import-time filesystem I/O). Add
`tests/doctrine/drg/test_builtin_graph_seam.py` asserting the seam returns a graph equal to the current
`load_graph(resolve_doctrine_root() / "graph.yaml")` while the monolith is present.

### T012 — Route `agent_profiles/repository.py`

Change `_default_drg_path` to yield the **directory** (or replace the `_default_drg_path()` + `load_graph`
pair at `:289` with `load_built_in_graph()`). Preserve the existing `DRGLoadError` handling shape. Confirm
`specializes_from` lineage resolution is unchanged (WP06 will prove it; here just don't regress it).

### T013 — Route `pack_validator.py:513` + `calibration/walker.py:430-437` [P]

Replace both bespoke monolith reads with `load_built_in_graph()`. For `walker.py`, retire
`_built_in_graph_path` (or repoint it at `built_in_graph_source()`).

### T014 — Route `charter_runtime/lint/_drg.py:52,85` [P]

Replace the `.../graph.yaml` candidate loop with the seam. Preserve the `GraphState` mapping semantics.

### T015 — Route the 6 already-safe consumers through the seam [P]

Swap their direct `load_graph_or_dir(resolve_doctrine_root())` calls for `load_built_in_graph()` so there is
exactly one accessor. Pure mechanical dedup; behavior identical.

### T016 — Review `snapshot.py` filename categorization (FR-014)

`snapshot.py:62` maps exact `"graph.yaml"` → `drg_fragments`; `:200` maps the `drg/` dir. Update so
`src/doctrine/*.graph.yaml` fragments categorize correctly (they will exist after WP05). Add/adjust a focused
test if the categorization has one.

### T017 — Update load-bearing docstrings (FR-016) [P]

Update **docstrings** (code prose) that assert "edges live in `src/doctrine/graph.yaml`" (singular monolith)
to the sharded layout across the `models.py` families: `directives/`, `procedures/`, `tactics/`, `paradigms/`,
`styleguides/`, plus `agent_profiles/schema_models.py:32,54` + `agent_profiles/profile.py:24,49` (post-task
squad FR-016 gap), `shared/exceptions.py`, `shared/errors.py`, `directives/common_docs.py`. **Do NOT touch
`src/doctrine/drg/models.py`** — that comment is FR-005/WP01's.

**Scope guard (DD-13):** edit only *docstrings*. Do **NOT** change the emitted *runtime* string of
`build_migration_hint` (`shared/errors.py`/`exceptions.py`) — ~10 test files pin it verbatim; that text update
is a deferred follow-up (DD-13). So your docstring edits must not alter any string a test asserts. Non-shipped
docs-tree `.md` files are OUT (tracked follow-up). After T017, run the doctrine suite and confirm no
string-assertion test went red — if one did, you touched an emitted string, not a docstring; revert that hunk.

## Branch Strategy

- Planning/base + merge target: **`feat/mission-type-drg-edges`**. Lane worktree from `lanes.json`.
- Depends on WP02 (Phase 1 complete): `spec-kitty agent action implement WP03 --agent claude`.

## Test strategy

Seam unit test (T011). Otherwise the guard is the **existing** suite staying green — because behavior is
unchanged while the monolith is present. Run `uv run pytest tests/doctrine tests/charter -q` and confirm no
regression.

## Definition of Done

- [ ] `load_built_in_graph()` / `built_in_graph_source()` exist in `loader.py`; seam unit test green.
- [ ] All 4 bespoke src readers + the 6 safe consumers route through the seam; org-pack readers untouched.
- [ ] `snapshot.py` categorization handles `*.graph.yaml` fragments.
- [ ] `models.py`-family docstrings updated (drg/models.py excluded); no `feature`/legacy terms introduced.
- [ ] Full doctrine + charter suites green (monolith still present → no behavior change).
- [ ] ruff + mypy --strict clean; zero new suppressions; complexity ≤ 15.

## Risks & reviewer guidance

- **`agent_profiles/repository.py` file-vs-dir gotcha**: the plan's original one-liner was wrong — `:289`
  receives a **file** path from `_default_drg_path`. Reviewer must confirm the seam yields the **directory**,
  or the change is a no-op that still breaks on delete.
- **Import-time I/O (NFR-004)**: reviewer confirms the seam is called at the same lazy points, not hoisted to
  module import.
- **Silent-degrade readers**: `repository.py`, `pack_validator.py`, `_drg.py` swallow `DRGLoadError`. Keep
  that shape here; WP06 proves their outputs are preserved. Do not "fix" the swallow in this WP.

## Activity Log

- 2026-07-16T08:42:36Z – claude:sonnet:python-pedro:implementer – shell_pid=203564 – Assigned agent via action command
- 2026-07-16T09:13:26Z – claude:sonnet:python-pedro:implementer – shell_pid=203564 – Ready: canonical load_built_in_graph seam in loader.py; all 4 bespoke src readers + 6 safe consumers routed through it; repository.py yields the DIRECTORY (file-vs-dir handled); DRGLoadError-swallow shapes preserved; org-pack readers untouched; snapshot.py FR-014 top-level *.graph.yaml categorization + focused test; T017 docstrings-only (DD-13: 112 validator-string tests green, no emitted string changed); monolith still present so behavior unchanged; doctrine+charter+calibration green (4175 passed), ruff+mypy --strict clean, graph fresh
- 2026-07-16T09:16:45Z – claude:opus:reviewer-renata:reviewer – shell_pid=270037 – Started review via action command
- 2026-07-16T09:29:11Z – user – shell_pid=270037 – Review PASSED (reviewer-renata). --force rationale: guard blocks only on the inherited kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md, which is WP02's approved deliverable (lane-c bases on WP02; orchestrator reconciled it in e15899d01 to keep lane-b/lane-c in sync for merge). WP03's substantive commit 6a10bf861 authored NO change to that doc. WP03 acceptance fully met: canonical seam (built_in_graph_source + load_built_in_graph) in loader.py resolves doctrine-locally via importlib.resources.files('doctrine'), does NOT import charter (C-004 clean); all 10 src readers routed, ZERO residual bespoke resolve_doctrine_root()/graph.yaml reads, org-pack readers untouched; file-vs-dir gotcha fixed (_default_drg yields directory), DRGLoadError swallow shapes preserved; T017 docstring-only (exceptions.py:26 runtime string unchanged, shared/errors.py not in diff, shared/ 94 tests green); snapshot.py FR-014 + focused test; ruff+mypy --strict clean, graph fresh, full doctrine+charter suite 4146 passed/1 skipped.
