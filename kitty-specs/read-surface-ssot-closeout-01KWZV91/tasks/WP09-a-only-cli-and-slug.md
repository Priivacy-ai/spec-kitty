---
work_package_id: WP09
title: 'A-only routing cluster 2: cli/commands + 4 slug sites + misc'
dependencies: []
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3256292"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/decision.py
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/cli/commands/materialize.py
- src/specify_cli/cli/commands/research.py
- src/specify_cli/cli/commands/validate_encoding.py
- src/specify_cli/workspace/context.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/manifest.py
- src/specify_cli/verify_enhanced.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-001), `plan.md`. **Append to `traces/*.md`.**

## Objective

Route the remaining Thread-A-only feature_dir reads (incl. the **4 `resolve_feature_dir_for_slug`
sites**) onto `read_dir(kind)`.

## Context

- **`resolve_feature_dir_for_mission` reads** → `read_dir(kind)`: `decision.py`, `mission_type.py`,
  `next_cmd.py`, `manifest.py`, `verify_enhanced.py`, `acceptance/__init__.py`.
- **The 4 `resolve_feature_dir_for_slug` sites** (currently outside the gate) → route onto
  `read_dir(kind)` per-kind: `materialize.py:71`, `research.py:64`, `validate_encoding.py:80`,
  `workspace/context.py:475`.
- **`acceptance/__init__.py` file-granular** — this is part of the `acceptance/` package 3-way
  (accept.py=Thread C/WP02, `__init__.py`=Thread A/here, matrix.py=Thread B/WP15). Keep `owned_files`
  file-level, never `acceptance/` dir-level.
- NFR-001: kind-correct surface; do not pin the old coord husk.

## Subtasks

### T029 — cli/commands reads
Route `decision.py`, `mission_type.py`, `next_cmd.py` feature_dir reads onto `read_dir(kind)`.

### T030 — 4 slug sites
Route the 4 `resolve_feature_dir_for_slug` sites (`materialize.py`, `research.py`,
`validate_encoding.py`, `workspace/context.py`) onto `read_dir(kind)` per-kind.

### T031 — misc + acceptance/__init__
Route `acceptance/__init__.py`, `manifest.py`, `verify_enhanced.py` feature_dir reads onto
`read_dir(kind)`. Keep acceptance ownership file-granular.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP09 --agent <name>`.

## Definition of Done
- [ ] All A-only reads (incl. 4 slug sites) route via `read_dir(kind)` (kind-correct).
- [ ] acceptance ownership file-granular; ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Confirm the 4 slug sites are routed. Verify acceptance/__init__.py is file-granular (no dir-level
overlap with WP02/WP15). Check kind correctness.

## Activity Log

- 2026-07-08T08:11:49Z – claude:sonnet:python-pedro:implementer – shell_pid=2804699 – Assigned agent via action command
- 2026-07-08T09:06:13Z – claude:sonnet:python-pedro:implementer – shell_pid=2804699 – T029-T031 done. next_cmd.py routed onto STATUS_STATE; decision.py + mission_type.py (current_cmd/close_cmd) deliberately kept on resolve_feature_dir_for_mission (fail-closed ActionContextError contract pinned by tests, not replicated by either read_dir(kind) leg -- documented inline). 4 slug sites routed: materialize/research/workspace-context -> STATUS_STATE, validate_encoding -> PRIMARY_METADATA (off coord husk). acceptance/__init__.py (file-granular)/manifest.py/verify_enhanced.py -> PRIMARY_METADATA. resolve_feature_dir_for_slug dropped from _read_path_resolver.py __all__ (dead-symbols gate, function kept) -- out-of-owned-files edit, gate-mandated. Updated one collateral test mock target (specify_cli.acceptance.resolve_feature_dir_for_mission -> mission_runtime.placement_seam). Full tests/architectural/: 796 passed/4 skipped/0 failed. No kitty-specs/ trace edits from this lane (traces live on coord/primary branch, not materialized here).
- 2026-07-08T09:07:24Z – claude:opus:reviewer-renata:reviewer – shell_pid=3256292 – Started review via action command
- 2026-07-08T09:31:16Z – user – shell_pid=3256292 – Review passed: A-only + 4 slug routed kind-correct; 3 fail-closed-dependent sites correctly left un-routed (FR-001 exception, documented for SC-001); no floor edits
