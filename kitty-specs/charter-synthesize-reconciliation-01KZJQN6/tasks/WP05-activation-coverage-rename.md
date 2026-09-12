---
work_package_id: WP05
title: Activation coverage + naming footgun
dependencies:
- WP01
- WP03
requirement_refs:
- FR-005
- FR-013
planning_base_branch: fix/charter-synthesize-reconciliation
merge_target_branch: fix/charter-synthesize-reconciliation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-synthesize-reconciliation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-synthesize-reconciliation unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T023b
phase: Phase 2 - Spine
history:
- timestamp: '2026-08-09T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/charter/
create_intent:
- tests/specify_cli/cli/commands/charter/test_activate_preserve.py
execution_mode: code_change
mission_id: 01KZJQN68SWZ7T1YKGDB4Q4EVH
owned_files:
- src/specify_cli/cli/commands/charter/activate.py
- src/specify_cli/cli/commands/charter/deactivate.py
- tests/specify_cli/cli/commands/charter/test_activate_preserve.py
tags: []
tracker_refs: []
agent_profile: python-pedro
role: implementer
agent: claude
wp_code: WP05
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role:
implementer) before anything else. Then read `plan.md` and `research.md` (the third lossy surface).

# Work Package Prompt: WP05 – Activation coverage + naming footgun

## Objectives & Success Criteria

- `charter activate` / `charter deactivate` never silently truncate the overlay. They call the CLI
  **command body** `charter_synthesize` **in-process** (`activate.py:348-355`, `deactivate.py:248`),
  so once WP03 adds a `--prune` Typer param, an **unset** `prune` argument resolves to a **truthy
  `OptionInfo` sentinel** (not the declared default) and every activate/deactivate would silently
  prune (#3270 reintroduced). This WP passes the CLI flags **explicitly** (`prune=False,
  dry_run=False`) at both in-process call sites so the sentinel never leaks in.
- The mis-named `run_resynthesize_pipeline` (which actually calls the full `synthesize`, not the
  bounded resynthesize) is renamed so the intent is legible, with imports/tests updated.

## Context & Constraints

- `activate.py:305` `run_resynthesize_pipeline` calls `_synthesize(adapter="generated",
  dry_run=False, …)` (`activate.py:348-355`) — the CLI **command function** `charter_synthesize`
  invoked in-process, NOT the library seam. Its Typer params only get their declared defaults when
  Typer parses a real CLI invocation; called in-process, any argument you omit resolves to the
  param's **`OptionInfo` sentinel** (truthy). Today the call passes `dry_run=False` explicitly; WP03
  adds `--prune`, so you must **also pass `prune=False` explicitly** at this call site and in the
  deactivate path — otherwise activation silently prunes.
- **Depends on WP03** (which introduces the `prune` param on `charter_synthesize`): the explicit
  `prune=False` can only be added once that param exists, and it must exist before activation is
  frozen — hence the WP03→WP05 edge.
- The rename is a small refactor (the naming-footgun cleanup, FR-013). Keep it mechanical and
  behavior-preserving; update all import sites and any tests referencing the old name.
- **Scope**: you own `activate.py`, `deactivate.py`. Do not touch the library seam (WP01) or
  `runner.py` (WP04).

## Subtasks & Detailed Guidance

### Subtask T021 – Pass the CLI flags explicitly (no sentinel silent-prune)
- At the in-process `_synthesize(...)` call in `activate.py:348-355` (and the deactivate path via
  `run_resynthesize_pipeline`), pass the CLI flags **explicitly** — including **`prune=False`** and
  keeping `dry_run=False` — so an unset Typer `OptionInfo` sentinel can never make activation prune.
  This is the **CLI-command call path**; do NOT pass `SynthesizeMode.preserve` here (that is the
  library seam's parameter, which the CLI command owns/derives — wrong layer for this call site).

### Subtask T022 – Rename the footgun
- Rename `run_resynthesize_pipeline` → an intent-revealing name (e.g. `run_full_synthesize` or
  `run_activation_synthesize`). Update the definition, all call sites (`activate.py:448-449`,
  `deactivate.py:248-249`), and any imports/tests. Add a one-line docstring clarifying it calls the
  full synthesize (preserve mode), not the bounded resynthesize.

### Subtask T023 – Tests
- New `tests/specify_cli/cli/commands/charter/test_activate_preserve.py`:
  - `activate` over a backed superset overlay preserves backed nodes/edges (0 silent drop).
  - `deactivate` likewise preserves backed content.
  - The renamed function is referenced (guards against a stale name regression).
  - **Corrupt-overlay via activate (in-process fail-closed):** with an unparseable on-disk
    `graph.yaml`, `activate` fails closed with **no write** — proving the WP01 library-seam guard
    (FR-007) fires on the in-process path that bypasses WP03's CLI, not only via the CLI.

### Subtask T023b – Sentinel-prune regression (once `--prune` exists)
- Assert that **`activate` AND `deactivate`** over a **backed** overlay never enter prune after
  WP03's `--prune` param lands: backed content is preserved (0 deletions), proving the in-process
  call does not leak the truthy `OptionInfo` sentinel into `prune`. This is the direct #3270
  re-introduction guard — it must fail if the explicit `prune=False` is dropped from the call site.

## Branch Strategy

- Planning-base / merge-target: `fix/charter-synthesize-reconciliation` (PRs into `main`).
- Depends on WP01; run `spec-kitty agent action implement WP05 --agent <name>` after WP01 is
  approved/done. Execution worktree per computed lane from `lanes.json`.

## Definition of Done

- [ ] activate/deactivate pass `prune=False, dry_run=False` **explicitly** at the in-process
      `charter_synthesize` call sites — no `OptionInfo` sentinel can trigger a silent prune (#3270).
- [ ] Sentinel-prune regression (T023b) covers **both** activate and deactivate over a backed overlay.
- [ ] `run_resynthesize_pipeline` renamed; all call sites/imports/tests updated.
- [ ] Activation tests green; `ruff` + `mypy` clean; complexity ≤ 15.
- [ ] Run `tests/architectural/test_no_legacy_terminology.py` on the touched `src/` surfaces (C-005; Mission not feature).

## Risks & Reviewer Guidance

- **Risk**: a missed call site of the renamed function → import error. Reviewer: grep for the old
  name across `src/` and `tests/`.
