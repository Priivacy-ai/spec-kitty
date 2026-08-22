---
work_package_id: WP01
title: Rebaseline org-awareness + worktree investigation
dependencies: []
requirement_refs:
- FR-003
planning_base_branch: pr/up-cascade-org-inert
merge_target_branch: pr/up-cascade-org-inert
branch_strategy: Planning artifacts for this mission were generated on pr/up-cascade-org-inert. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/up-cascade-org-inert unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cascade-org-inert-01M07E9P
base_commit: 6b0e2c971d5612eb89303de758fdc6ea59110779
created_at: '2026-08-17T13:32:17.033506+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1
history:
- timestamp: '2026-08-17T00:00:00Z'
  agent: phase-agent
  action: Prompt authored during tasks phase, cascade-org-inert-01M07E9P
authoritative_surface: src/specify_cli/dossier/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/dossier/rebaseline.py
- tests/dossier/test_rebaseline.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Rebaseline org-awareness + worktree investigation

## Read first

- `kitty-specs/cascade-org-inert-01M07E9P/spec.md` — FR-003 (all 5 ACs + Design Notes), User
  Story 5.
- `kitty-specs/cascade-org-inert-01M07E9P/plan.md` — IC-03 (Purpose, Affected surfaces,
  Sequencing/depends-on, Risks, the mission-level sequencing recommendation), Test Strategy's
  FR-003 bullet, Gate Set table.
- `.kittify/charter/charter.md` — ATDD-First Discipline (C-011, binding): a failing test pinning
  the defect must be committed BEFORE the fix commit, red on this WP's own starting commit, green
  on its final commit.

## Why this WP exists

`src/specify_cli/dossier/rebaseline.py:166` currently constructs `Indexer(ManifestRegistry())`
with no `repo_root`, so `migrate rebaseline` is permanently org-blind — it never consults a
configured org pack's `expected-artifacts.yaml` override, unlike every other caller of `Indexer`
in this codebase (`reconcile.py`, `sync/dossier_pipeline.py`, both of which already thread
`repo_root`).

## T001 — Worktree investigation (do this FIRST, it gates T002/T003)

Read `src/specify_cli/workspace/context.py::resolve_workspace_for_wp` and CLAUDE.md's "Execution
Workspace Strategy (2.x)" section. Determine: does a spec-kitty execution worktree
(`.worktrees/<slug>-<mid8>-lane-<id>/`) ever contain its own
`kitty-specs/<slug>/.kittify/dossiers/...` tree, distinct from the primary checkout's? Trace how
`migrate rebaseline`'s sole production caller (`src/specify_cli/cli/commands/migrate_cmd.py:937`)
resolves `repo_root` — via `locate_project_root()`, invoked from wherever the operator ran
`spec-kitty migrate`.

**Write your finding, with file:line evidence, into this WP's own commit message or a short note
in the PR — do not silently assume either outcome.**

- **Outcome (a)**: worktrees never carry dossier snapshots (rebaseline only ever runs against the
  primary/coord checkout). → proceed to T002.
- **Outcome (b)**: worktrees CAN carry dossier snapshots. → proceed to T003 instead of T002.

## T002 — Derivation (B), if T001 found outcome (a)

In `src/specify_cli/dossier/rebaseline.py::rebaseline_snapshot_file`:
- `feature_dir` is already computed via `_resolve_feature_dir(snapshot_path)` — this is the
  mission's own `kitty-specs/<slug>/` directory (confirmed: it has a nested `.kittify/dossiers/...`
  subtree, verified live during the spec phase — `kitty-specs/066-review-loop-stabilization/.kittify`
  exists on this checkout).
- Derive `repo_root = feature_dir.parent.parent` (peel off `kitty-specs/` then the slug dir —
  `KITTY_SPECS_DIR = "kitty-specs"` is a fixed, non-configurable constant,
  `src/specify_cli/core/constants.py:5`).
- Change `Indexer(ManifestRegistry())` to `Indexer(ManifestRegistry(), repo_root=repo_root)`.

## T003 — Worktree-aware correction, if T001 found outcome (b)

Design a correction that resolves the project's REAL org-pack-configured root rather than the
worktree's local one — e.g. `git rev-parse --path-format=absolute --git-common-dir` or an
equivalent superproject-root resolution. Document why derivation (B) alone was insufficient,
concretely (not just "worktrees exist").

## T004 — Red-first test (write before T002/T003's fix commit)

Assert `Indexer` receives a non-`None` `repo_root` matching the project root after
`rebaseline_snapshot_file` runs, for a project with a healthy org pack (spec.md SC-005). Must be
RED against this WP's starting commit (`Indexer(ManifestRegistry())`, no `repo_root`) and GREEN
after T002/T003.

## T005 — No-org-pack regression test

Confirm rebaseline behavior is unchanged from today when no org pack is configured (FR-003 AC2) —
this is the revert-discipline companion: a test that would fail if T002/T003's derivation
accidentally broke the org-agnostic path.

## T006 — Malformed org-pack test

Confirm rebaseline does not raise an unhandled exception to the operator's `migrate` command when
the org pack is malformed (FR-003 AC4). Degrade specifics are this WP's own judgment call — make
it deliberate and documented, not an accidental stack trace.

## T007 — Multi-pack inheritance check

`src/specify_cli/dossier/manifest.py:253`'s `ManifestRegistry.load_manifest` already calls the
PLURAL `_resolve_existing_org_roots(repo_root)` once `repo_root` is non-`None`. Confirm this
actually delivers pack-2 content once T002/T003 threads `repo_root` in (FR-003 AC3). If it does
NOT hold on inspection, implement multi-pack support explicitly and say so — do not leave the gap
undocumented either way.

## Gates before calling this WP done

- `.venv/bin/python -m pytest tests/dossier/test_rebaseline.py -v` — baseline recorded BEFORE
  T004's red-first commit; green (or explicitly-pre-existing-red-only) after.
- `uvx --with-requirements pyproject.toml mypy --strict src/specify_cli/dossier/rebaseline.py` —
  before/after, no new errors.
- `uvx ruff check src/specify_cli/dossier/rebaseline.py`.
- `_resolve_org_root` in `charter/_drg_helpers.py` is untouched by this WP (out of this WP's file
  scope entirely — just a sanity check).
