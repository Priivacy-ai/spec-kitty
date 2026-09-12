---
work_package_id: WP08
title: Structural read-side gate + sanctions + allow-list
dependencies:
- WP03
- WP04
- WP05
- WP06
- WP07
requirement_refs:
- FR-003
- FR-005
- FR-006
- NFR-003
- NFR-004
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 4 - Gate
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_read_side_bypass.py
create_intent:
- tests/architectural/test_no_read_side_bypass.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_no_read_side_bypass.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – Structural read-side gate

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `python-pedro` (implementer, claude).

## Objective
Add the structural gate that makes new read-side bypasses unrepresentable. Binding contract: [contracts/read-side-gate.md](../contracts/read-side-gate.md). Mirror the STRUCTURAL write gate `tests/architectural/test_no_write_side_rederivation.py` (AST grammar) — NOT the behavioral `test_read_surface_placement_guard.py`. **Lands last** (after WP03–WP07); if scheduled earlier, seed it red with a shrinking allow-list (C-002).

## Subtasks
### T017 — Gate module
`tests/architectural/test_no_read_side_bypass.py`: walk `ast.Call` over `_placement_whole_tree_scan.scan_scope()` (REUSE — do NOT fork the walk, NFR-003); flag callees `candidate_feature_dir_for_mission` / `resolve_planning_read_dir`.
### T018 — Sanctions + allow-list
Sanction the infra authority modules (`_read_path_resolver.py`, `coordination/surface_resolver.py`, `mission_runtime/write_target_degrade.py`) — asserted-sanctioned, not silently skipped (FR-003). Encode the WP02 `stay-lenient` residuals as content-descriptor allow-list entries via `_ratchet_keys.resolve_descriptor` with rationale; **shrink-only** with a staleness twin-guard that reds until a routed entry is deleted (FR-006, NFR-004). No file-scoped blanket exemptions (C-003).
### T019 — Bite + symmetry
Bite test: planted `candidate_feature_dir_for_mission(root,slug)` in a fixture reds; prose/docstring mention stays green. Symmetry meta-test: the read gate and write gate consume the same `scan_scope()` object.
### T020 — Green with shrinking allow-list
With WP03–WP07 merged, the gate is green; the allow-list contains only genuine stay-lenient/sanctioned residuals, each live (twin-guard).

## Gates
`PWHEADLESS=1 uv run pytest tests/architectural/test_no_read_side_bypass.py -q`; then the aggregate `tests/architectural/` suite (parallel: `-n auto --dist loadfile`); `ruff`; `mypy` project-mode.

## DoD / Review
Gate reuses the shared scanner (symmetry proven); bite test reds on a planted bypass; every allow-list entry live (non-vacuous); infra sanctioned with rationale. Finish: commit, `mark-status T017 T018 T019 T020 --status done`, `move-task WP08 --to for_review`.
