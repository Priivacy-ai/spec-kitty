---
work_package_id: WP01
title: Shared directive-resolution helper + synthesizer refactor
dependencies: []
requirement_refs:
- FR-002
- FR-004
tracker_refs: []
planning_base_branch: gk/2758-2759
merge_target_branch: gk/2758-2759
branch_strategy: Planning artifacts for this mission were generated on gk/2758-2759. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into gk/2758-2759 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
phase: Phase 1 - Single Authority
assignee: ''
agent: ''
history:
- timestamp: '2026-07-17T13:20:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
create_intent:
- tests/charter/test_synthesis_graph_directives.py
execution_mode: code_change
mission_id: 01KXR0M1FQTBPSQ8S2GNM6K7XZ
authoritative_surface: src/charter/compiler.py
owned_files:
- src/charter/compiler.py
- src/specify_cli/cli/commands/charter/_synthesis.py
tags: []
wp_code: WP01
---

# Work Package Prompt: WP01 – Shared directive-resolution helper + synthesizer refactor

## Objectives & Success Criteria

- ONE public helper `charter.compiler.resolve_synthesis_graph_directives(repo_root) -> list[str]` that
  returns exactly the resolved directive list the synthesizer feeds `graph.yaml`: `[] if
  PackContext.from_config(repo_root).activated_directives is None else
  resolve_config_activated_roots(repo_root=repo_root).directives` (the #2577 absent→`[]` rule).
- `_synthesis.py` refactored so `selected_directives` AND `drg_nodes` source from the helper —
  **behavior-preserving** (`selected_paradigms` stays inline; it is inert for the graph).
- The helper is the single authority WP02's freshness hash will reuse (FR-002/FR-004, C-004).

## Context & Constraints

- Read `plan.md` (IC-01, OQ-5) and `spec.md` FR-002/FR-004/C-004. Ground truth is `_synthesis.py:57-107`.
- Do NOT change the synthesizer's output. `test_synthesize_path_parity` MUST stay green.
- The helper is PUBLIC (added to `charter/compiler.py` `__all__`) — it will have two real callers (this WP's
  synthesizer refactor + WP02's `bundle.py`), satisfying `test_no_dead_symbols` (C-007).

## Subtasks & Detailed Guidance

### T001 — (RED-FIRST) Test the helper contract
- **Purpose**: pin absent→`[]` and present→resolved BEFORE implementing (C-011).
- **Steps**:
  1. New `tests/charter/test_synthesis_graph_directives.py`.
  2. Seed a repo fixture with `activated_directives` **absent** → assert `resolve_synthesis_graph_directives(repo)` == `[]`.
  3. Seed with `activated_directives` present (a real stem) → assert it equals `resolve_config_activated_roots(repo_root=repo).directives`; derive the expected ids from the resolver (do NOT hardcode `default.yaml`).
  4. Commit RED (helper does not exist yet) as the first commit of the WP.
- **Files**: `tests/charter/test_synthesis_graph_directives.py`.

### T002 — Implement the helper + refactor the synthesizer
- **Steps**:
  1. In `src/charter/compiler.py`, add `resolve_synthesis_graph_directives(repo_root: Path) -> list[str]` implementing the exact expression above (it already imports `PackContext`/`resolve_config_activated_roots` context). Add it to `__all__`.
  2. In `src/specify_cli/cli/commands/charter/_synthesis.py`, replace the inline `directives_for_synthesis` computation (lines ~76-79) with a call to the helper; keep `selected_directives`, `drg_nodes` (lines ~101-107), and `selected_paradigms` (line ~85, unchanged) sourcing consistent (same list for directives + drg_nodes).
  3. Run `pytest tests/charter/test_synthesis_graph_directives.py tests/charter/synthesizer/test_synthesize_path_parity.py` → GREEN.
- **Files**: `src/charter/compiler.py`, `src/specify_cli/cli/commands/charter/_synthesis.py`.
- **Notes**: `mypy --strict` + `ruff` clean; no new suppressions.

## Validation
- `pytest tests/charter/test_synthesis_graph_directives.py tests/charter/test_config_sourced_derivation.py tests/charter/synthesizer/test_synthesize_path_parity.py -q`
  (`test_config_sourced_derivation.py` is the behavior-preservation proof — it
  asserts the actual `selected_directives`/`drg_nodes` snapshot values the
  refactor must not change; `test_synthesize_path_parity.py` guards the
  end-to-end synthesize output.)
- `ruff check src/charter/compiler.py src/specify_cli/cli/commands/charter/_synthesis.py && mypy src/charter/compiler.py`
- Red→green witnessed: T001 RED on `gk/2758-2759` base, GREEN on WP final commit.

## Dependencies
- None.
