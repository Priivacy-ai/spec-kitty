---
work_package_id: WP06
title: References-parity auto-refresh completion (#2777)
dependencies:
- WP04
requirement_refs:
- FR-011
planning_base_branch: fix/charter-synthesize-reconciliation
merge_target_branch: fix/charter-synthesize-reconciliation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-synthesize-reconciliation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-synthesize-reconciliation unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
phase: Phase 3 - Folds
history:
- timestamp: '2026-08-09T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/charter_runtime/preflight/
create_intent:
- src/specify_cli/charter_runtime/preflight/references_refresh.py
- tests/specify_cli/charter_runtime/test_references_parity_refresh.py
execution_mode: code_change
mission_id: 01KZJQN68SWZ7T1YKGDB4Q4EVH
owned_files:
- src/specify_cli/charter_runtime/preflight/references_refresh.py
- src/specify_cli/cli/commands/charter/generate.py
- tests/specify_cli/charter_runtime/test_references_parity_refresh.py
tags: []
tracker_refs: []
agent_profile: python-pedro
role: implementer
agent: claude
wp_code: WP06
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role:
implementer) before anything else. Then read `plan.md`, `research.md` (#2777 fold), and the
issue context for #2777 / #2772.

# Work Package Prompt: WP06 – References-parity auto-refresh completion (#2777)

## Objectives & Success Criteria

- The boundary auto-refresh, when the stale cause is **references-parity**, runs a **targeted
  `generate`** that recompiles `references.yaml` — without clobbering a curated `charter.md`
  (honoring the landed #2772 contract).
- Implemented behind WP04's `refresh_references_if_needed` extension point (no `runner.py` edit
  here — WP04 owns that call site).

## Context & Constraints

- **Why** (research.md, #2777): `synthesize` never recompiles `references.yaml`; only `generate`
  does. Adding `generate` naively risks clobbering curated `charter.md` (#2772) and tripping the
  dirty-tree guard — run it **only** for the references-parity cause and honor the preservation
  contract.
- **#2772 is merged** — there is a landed curated-`charter.md` preservation contract to honor
  (charter.md is a curated reference, never a charter-resolving input). Verify `generate` respects it.
- **Scope**: you own the new `references_refresh.py` and `generate.py`. WP04 installed the hook
  call; you implement the hook. Do not modify `runner.py`.

## Subtasks & Detailed Guidance

### Subtask T024 – References-parity refresh helper
- Create `src/specify_cli/charter_runtime/preflight/references_refresh.py` with
  `refresh_references_if_needed(repo_root, cause)`:
  - Detect the references-parity stale cause (config ↔ `references.yaml` drift).
  - When present, invoke the targeted `generate` path (recompile `references.yaml` only) — reuse
    the `charter generate` code in `generate.py`, guarded to not rewrite curated `charter.md`.
  - No-op for any other cause.

### Subtask T025 – Honor #2772 + wire the hook
- Ensure the `generate` invocation preserves a curated `charter.md` (0 bytes changed). If
  `generate.py` needs a "references-only" mode to avoid touching `charter.md`, add it here.
- Confirm WP04's `_attempt_auto_refresh` call to `refresh_references_if_needed` now performs the
  recompile for the references-parity cause.

### Subtask T026 – Tests
- New `tests/specify_cli/charter_runtime/test_references_parity_refresh.py`:
  - References-parity drift → helper recompiles `references.yaml` (content reflects current
    activation).
  - Curated `charter.md` is **0 bytes changed** by the refresh.
  - Non-references-parity cause → helper is a no-op.

## Branch Strategy

- Planning-base / merge-target: `fix/charter-synthesize-reconciliation` (PRs into `main`).
- Depends on WP04; run `spec-kitty agent action implement WP06 --agent <name>` after WP04 is
  approved/done. Execution worktree per computed lane from `lanes.json`.

## Definition of Done

- [ ] References-parity cause recompiles `references.yaml` via targeted generate.
- [ ] Curated `charter.md` untouched (#2772 honored).
- [ ] Helper is a no-op for other causes; tests green; `ruff` + `mypy` clean; complexity ≤ 15.
- [ ] Run `tests/architectural/test_no_legacy_terminology.py` on the touched `src/` surfaces (C-005; Mission not feature).

## Risks & Reviewer Guidance

- **Risk**: clobbering curated `charter.md`. Reviewer: verify the 0-bytes-changed test and the
  references-only guard.
- **Risk**: running `generate` for the wrong cause. Reviewer: confirm the cause detection is precise.
