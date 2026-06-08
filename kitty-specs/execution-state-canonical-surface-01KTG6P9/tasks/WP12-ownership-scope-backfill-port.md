---
work_package_id: WP12
title: Ownership scope backfill-awareness + frontmatter-source port (#1757)
dependencies: []
requirement_refs:
- FR-028
- FR-029
- FR-030
- FR-031
tracker_refs:
- '1757'
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T042
- T043
- T044
- T045
- T046
phase: Phase 6 - Fold-in follow-ups
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2973013"
history:
- at: '2026-06-07T09:30:00Z'
  actor: system
  action: Prompt generated as #1757 fold-in (post-#1756 rebase)
agent_profile: python-pedro
authoritative_surface: 'src/specify_cli/ownership/'
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/ownership/models.py
- src/specify_cli/ownership/inference.py
- src/specify_cli/ownership/validation.py
- src/specify_cli/ownership/frontmatter_source.py
- src/specify_cli/migration/backfill_ownership.py
- src/specify_cli/cli/commands/agent/mission.py
- tests/specify_cli/ownership/**
role: implementer
tags:
- ownership
- single-ownership
- fold-in
task_type: implement
---

# Work Package Prompt: WP12 – Ownership `scope` backfill-awareness + frontmatter-source port (#1757)

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below).

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objectives & Success Criteria

Make the ownership `scope` field flow through one canonical owner on every path and push the finalize ownership IO boundary through a single frontmatter-source port. This closes the non-blocking follow-ups from the #1756 (#1753) adversarial review.

- FR-028/029/030/031. SC-009. NFR-003 (single ownership).

## Context & Constraints

- **Provenance**: #1757 — surfaced by the review of #1756, which is the very PR that wired `scope: codebase-wide` end-to-end and unblocked this mission's own `finalize-tasks`. These are the latent residue the fix left behind.
- **The bug class (Paula Patterns "whack-a-field")**: `scope` has three representations — `WPMetadata`, `OwnershipManifest`, raw dict — with one canonical owner (`OwnershipManifest.from_frontmatter`). The backfill and inference paths never learned about it, so the exemption only reaches validation when a human authored it on disk and it was re-read.
- **Latent failure to fix (FR-028)**: in `migration/backfill_ownership.py` the "already fully backfilled" guard checks `execution_mode` + `owned_files` + `authoritative_surface` and omits `scope`; the write step persists those three and never writes `scope`. So `scope: codebase-wide` added to an already-backfilled WP can silently fail.
- **Symmetry fix (FR-030)**: in `ownership/models.py::from_frontmatter`, the raw-`dict` branch uses `data.get("authoritative_surface", "")` (returns a present-but-`None`), whereas the `WPMetadata` branch coerces with `or ""`. Normalize the dict path with `data.get("authoritative_surface") or ""`. Pre-existing (on `main`); no regression, but make both shapes provably equivalent.
- **Half-pure seam (FR-031)**: `ownership/validation.py::build_wp_manifests` is pure, but the caller (`cli/commands/agent/mission.py` finalize ownership block) owns `read_wp_frontmatter` + the in-memory `_inmemory_frontmatter` substitution *before* the seam. Introduce a frontmatter-source port so the whole resolve→validate path is testable without stubbing the reader. This is the same one-owning-port theme as epic #1666.
- **No inference for `scope` (FR-029)**: `ownership/inference.py::infer_ownership` must stay narrow-by-design; document explicitly that `scope` is human-authored only (no inference path) so the omission is a stated contract, not a gap.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T042 – Scope-aware backfill
- **Steps**: Add `scope` to the "already present" guard and the write step in `migration/backfill_ownership.py`; persist `scope` when present on disk. Do not infer it.
- **Files**: `src/specify_cli/migration/backfill_ownership.py`.

### Subtask T043 – Document no-inference contract
- **Steps**: In `ownership/inference.py::infer_ownership`, add an explicit note that `scope` has no inference path (human-authored only); inferred manifests remain narrow.
- **Files**: `src/specify_cli/ownership/inference.py`.

### Subtask T044 – from_frontmatter dict-path symmetry
- **Steps**: Normalize the raw-`dict` branch `authoritative_surface` with `data.get("authoritative_surface") or ""`. Preserve the two existing contracts (`KeyError` on missing `execution_mode`; `authoritative_surface` defaults to `""`).
- **Files**: `src/specify_cli/ownership/models.py`.

### Subtask T045 – Frontmatter-source port
- **Steps**: Introduce a frontmatter-source port (e.g. `ownership/frontmatter_source.py`) that owns supplying WP frontmatter (disk read + in-memory substitution) to `build_wp_manifests`; route the finalize ownership block in `cli/commands/agent/mission.py` through it. The resolve→validate path must be drivable without stubbing `read_wp_frontmatter`.
- **Files**: `src/specify_cli/ownership/frontmatter_source.py`, `src/specify_cli/ownership/validation.py`, `src/specify_cli/cli/commands/agent/mission.py`.

### Subtask T046 – Tests
- **Steps**: Add tests proving: (1) backfill re-run on an already-backfilled WP persists `scope: codebase-wide`; (2) `from_frontmatter` is symmetric for `authoritative_surface: None` across `WPMetadata` and raw-dict inputs; (3) the resolve→validate path runs through the port with plain stubs (no reader mocking).
- **Files**: `tests/specify_cli/ownership/**`.

## Test Strategy

- **ATDD-first (C-011, binding):** author + commit subtask **T046 RED first** (the backfill-re-run / symmetry / port tests), before the T042–T045 implementation. Reviewer verifies the tests were RED on `planning_base_branch` and GREEN on the final commit.
- New tests green; existing ownership + finalize tests green; `ruff` + `mypy` clean on touched modules (NFR-007).

## Risks & Mitigations

- Do not introduce a parallel `scope` path — one canonical owner (`from_frontmatter`) stays authoritative (Paula-Patterns single-ownership IC).
- The port must not change finalize behavior — behavior-preserving refactor; prove with the existing finalize tests.

## Review Guidance — **Persona IC: reviewer-renata (+ Paula-Patterns single-ownership)**

- Reviewer profile: `reviewer-renata`. Verify: `scope` is now read/backfilled/validated through one owner; the backfill re-run test actually fails without the guard change; `from_frontmatter` symmetry is proven; the port removes the reader-stub from the resolve→validate test. Confirm no second scope path was introduced.

## Activity Log

- 2026-06-07T09:30:00Z – system – Prompt created as #1757 fold-in.
- 2026-06-08T10:43:22Z – claude:opus:python-pedro:implementer – shell_pid=2961111 – Started implementation via action command
- 2026-06-08T10:53:46Z – claude:opus:python-pedro:implementer – shell_pid=2961111 – Ready for review: FR-028/029/030/031 + ATDD T046 (red->green)
- 2026-06-08T10:54:29Z – claude:opus:reviewer-renata:reviewer – shell_pid=2973013 – Started review via action command
