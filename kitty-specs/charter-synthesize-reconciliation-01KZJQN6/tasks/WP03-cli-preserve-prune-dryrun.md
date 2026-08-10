---
work_package_id: WP03
title: CLI preserve/prune/dry-run + narrow refusal
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-007
- FR-010
- FR-014
planning_base_branch: fix/charter-synthesize-reconciliation
merge_target_branch: fix/charter-synthesize-reconciliation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-synthesize-reconciliation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-synthesize-reconciliation unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 2 - Spine
history:
- timestamp: '2026-08-09T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/charter/
create_intent:
- tests/specify_cli/cli/commands/charter/test_synthesize_cli_reconcile.py
execution_mode: code_change
mission_id: 01KZJQN68SWZ7T1YKGDB4Q4EVH
owned_files:
- src/specify_cli/cli/commands/charter/synthesize.py
- src/specify_cli/cli/commands/charter/_synthesis.py
- src/specify_cli/cli/commands/charter/_fresh_doctrine.py
- tests/specify_cli/cli/commands/charter/test_synthesize_cli_reconcile.py
tags: []
tracker_refs: []
agent_profile: python-pedro
role: implementer
agent: claude
wp_code: WP03
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role:
implementer) before anything else. Then read `plan.md`, `data-model.md`, and
`contracts/synthesize-seam.md` (the CLI flag→mode→exit table is authoritative).

# Work Package Prompt: WP03 – CLI preserve/prune/dry-run + narrow refusal

## Objectives & Success Criteria

- `charter synthesize` (CLI) consumes the library `ReconciliationDelta` and implements the
  confirmed UX:
  - **default** → preserve; exit 0; report retained content + any preserved-conflict warnings.
  - **`--dry-run`** → report the delta (removable + conflicts); **write nothing**; exit 0.
  - **`--prune`** → remove the divergent content; **list every deletion**; exit 0.
  - **refuse (exit 1)** only for unpreservable cases: orphaned content (backing artifact deleted)
    targeted for removal without `--prune`, or an **unparseable on-disk overlay**.
- Refusal / prune / dry-run output reuses the DRG typed-conflict object shape.

## Context & Constraints

- The library seam (WP01) already defaults to preserve and returns the delta; the CLI owns the
  **policy** (mode selection + refusal). Do not move refusal into the library (it would break the
  flagless boundary `auto_refresh`, see WP04).
- Today the non-fresh dry-run path (`synthesize.py:356-388`) emits no `planned_deletes`; only the
  fresh-seed branch does. This WP brings `planned_deletes` (the delta) to the normal path.
- The CLI signals failure via `raise typer.Exit(code=1)`. Reserve that for the two unpreservable
  cases only.

## Subtasks & Detailed Guidance

### Subtask T011 – Map flags → mode; preserve-and-warn default
- Add `--prune` and ensure `--dry-run` exist on `charter synthesize`. Map: none→`preserve`,
  `--dry-run`→`dry_run`, `--prune`→`prune` (reject `--prune --dry-run` combined, or define
  `--dry-run` wins and only previews). Call `synthesize(..., mode=…)`. On preserve, print retained
  summary + any `delta.conflicts` as warnings; exit 0.

### Subtask T012 – `--prune` removes and lists
- On `prune`, the library removes `delta.removable`; the CLI prints each removed node/edge/manifest
  entry (typed-conflict/reference shape). Exit 0.

### Subtask T013 – `--dry-run` reports, writes nothing
- On `dry_run`, print the delta (`removable` + `conflicts`) and assert no file was written. Extend
  the JSON envelope (`synthesize.py:367-381`) with a `planned_deletes` field for the normal path.

### Subtask T014 – Narrow refusal
- Refuse (exit 1) when: (a) a plain run would need to remove **orphaned** content (backing artifact
  missing) — instruct the operator to `--prune`; or (b) the on-disk overlay is unparseable — abort
  with no write (never fall back to a wholesale rebuild). List the conflicts + remediation.
- Backed divergence is **not** a refusal case — it is preserved and warned (exit 0).

### Subtask T015 – Reuse the conflict message shape
- Render refusal/prune/dry-run lines from `ReconciliationConflict` (`kind` + `target_id` +
  `backing_artifact` + `remediation`). Do not hand-roll a parallel format.

### Subtask T016 – Tests
- New `tests/specify_cli/cli/commands/charter/test_synthesize_cli_reconcile.py` (CLI runner):
  - `--prune` removes divergent content and lists each deletion (exit 0).
  - `--prune` with nothing to prune → no-op, empty deletions list (exit 0).
  - `--dry-run` on a superset overlay → non-empty `planned_deletes`, **no file written** (exit 0).
  - `--dry-run` with no divergence → empty `planned_deletes` (exit 0).
  - Orphaned removal without `--prune` → exit 1, lists the orphan + remediation.
  - Unparseable `graph.yaml` → exit 1, no write.
  - Backed divergence (plain run) → exit 0, content preserved, warning emitted.

## Branch Strategy

- Planning-base / merge-target: `fix/charter-synthesize-reconciliation` (PRs into `main`).
- Depends on WP01, WP02; run `spec-kitty agent action implement WP03 --agent <name>` after both are
  approved/done. Execution worktree per computed lane from `lanes.json`.

## Definition of Done

- [ ] Preserve default (exit 0), `--prune` (remove+list), `--dry-run` (delta+no-write) all work.
- [ ] Refusal is narrow (orphan-without-prune, unparseable overlay) — backed divergence never refuses.
- [ ] Messaging reuses the DRG conflict shape.
- [ ] CLI tests green; `ruff` + `mypy` clean; complexity ≤ 15.

## Risks & Reviewer Guidance

- **Risk**: dry-run computing a different delta than a real run. Reviewer: verify both derive the
  delta from the same library call.
- **Risk**: over-broad refusal re-introducing the trap. Reviewer: confirm backed divergence is
  exit-0 preserve, and only orphan/unparseable cases refuse.

## 🔴 Post-tasks squad amendments (MUST READ before implementing)

1. **[MINOR] Atomic edge assertion (IC-08 "edge preservation on prune/refuse paths").** Extend
   T016 so a `--prune` that removes a node asserts the node's edges are dropped **together**, and a
   refusal path asserts the node's edges are **retained** with it (FR-002 atomicity on the
   prune/refuse paths, not only the committed preserve-path test).
2. **[CLARIFY] Refusal is by design for orphan/unparseable.** Backed divergence is exit-0 preserve;
   only orphaned-removal-without-`--prune` and unparseable-overlay refuse (exit 1). The unparseable
   guard itself lives at the library seam (WP01 amendment #2) — the CLI surfaces it as exit 1.
3. **[DEFENSE-IN-DEPTH — sentinel coercion for the in-process call path].** `charter_synthesize` is
   also invoked **in-process** by `activate.py`/`deactivate.py` (WP05), where an unset Typer param
   resolves to a truthy `OptionInfo` sentinel rather than the declared default. WP05 owns passing
   `prune=False` explicitly, but as a belt-and-braces guard, `charter_synthesize` SHOULD coerce a
   non-`bool` `prune`/`dry_run` value (i.e. an `OptionInfo` sentinel) to `False` at the top of the
   body before acting on it. This prevents a silent boundary prune if any future in-process caller
   forgets the explicit flag. (The authoritative fix is WP05's explicit-flag pass; this is defense
   in depth, not a substitute.)
