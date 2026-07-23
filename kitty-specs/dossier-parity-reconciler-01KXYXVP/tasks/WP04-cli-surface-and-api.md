---
work_package_id: WP04
title: Reconciler CLI Surface + Library API
dependencies:
- WP03
requirement_refs:
- FR-007
tracker_refs:
- '#2180'
planning_base_branch: feat/dossier-parity-reconciler
merge_target_branch: feat/dossier-parity-reconciler
branch_strategy: Planning artifacts for this mission were generated on feat/dossier-parity-reconciler. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dossier-parity-reconciler unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 3 - Surface
assignee: ''
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "2934716"
history:
- at: '2026-07-20T06:13:30Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/reconcile.py
create_intent:
- src/specify_cli/cli/commands/reconcile.py
- tests/cli/commands/test_reconcile.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/reconcile.py
- tests/cli/commands/test_reconcile.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 — Reconciler CLI Surface + Library API

## ⚡ Do This First: Load Agent Profile

Load your assigned profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role: `implementer`) before anything else.

## Objective

Expose the WP03 reconciler as (a) a supported CLI operation and (b) a stable library API that import-history (#2262) can call to gate materialization (FR-007). The CLI exits 0 on PARITY and non-zero on DIVERGENCE, naming the differing artifacts. Prove NFR-002 (reconcile one mission dossier ≤ 2 s).

## Context

- New CLI command in `src/specify_cli/cli/commands/reconcile.py`, wired into the CLI app. Wraps the WP03 `DossierReconciler`.
- The library API is the entrypoint #2262 binds to — keep it narrow and stable (a function returning the `ReconciliationResult`), so #2262 depends on a contract, not internals.

## Subtasks

### T015 — Red tests (FR-007, NFR-002)
In `tests/cli/commands/test_reconcile.py`: CLI exits 0 on parity; non-zero on divergence with the differing artifacts named in output; the library API returns a structured `ReconciliationResult`. Add a timing assertion scaffold for NFR-002.

### T016 — Implement the CLI command (FR-007)
Implement `reconcile`/`verify` wrapping the reconciler; map PARITY→exit 0, DIVERGENCE→non-zero + named artifacts on stderr/stdout; support `--json`.

### T017 — Expose the library API (FR-007)
Expose a stable, importable entrypoint (the reconcile function + `ReconciliationResult`) documented as the surface #2262 consumes. No leakage of internals.

### T018 — Prove NFR-002 [P]
Add a test/benchmark proving a single mission dossier reconciles ≤ 2 s; confirm scaling is linear in artifact count. Run focused type/style/coverage gates.

## Branch Strategy

Planning branch: `feat/dossier-parity-reconciler`; final merge target: same. Worktrees per-lane from `lanes.json`.

## Definition of Done

- CLI reconcile/verify: exit 0 on parity, non-zero + named on divergence, `--json` supported.
- Stable library API exposed + documented for #2262.
- NFR-002 (≤ 2 s single mission) proven.
- ruff + mypy clean; ≥90% changed-code coverage.

## Risks / Reviewer Guidance

- The library API is a cross-mission contract (#2262 binds to it) — reviewer confirms it is narrow, typed, and stable, not exposing reconciler internals.
- Exit-code discipline: divergence must be non-zero so CI/automation can gate on it.

## Activity Log

- 2026-07-20T07:16:11Z – claude:sonnet:implementer:implementer – shell_pid=2894182 – Assigned agent via action command
- 2026-07-20T07:30:44Z – claude:sonnet:implementer:implementer – shell_pid=2894182 – Ready for review: reconcile CLI + library API
- 2026-07-20T07:32:10Z – claude:sonnet:reviewer:reviewer – shell_pid=2934716 – Started review via action command
