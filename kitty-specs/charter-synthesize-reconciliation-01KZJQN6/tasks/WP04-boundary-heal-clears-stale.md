---
work_package_id: WP04
title: Non-destructive boundary heal that clears stale
dependencies:
- WP01
- WP03
requirement_refs:
- FR-008
planning_base_branch: fix/charter-synthesize-reconciliation
merge_target_branch: fix/charter-synthesize-reconciliation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-synthesize-reconciliation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-synthesize-reconciliation unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 2 - Spine
history:
- timestamp: '2026-08-09T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/charter_runtime/
create_intent:
- tests/specify_cli/charter_runtime/test_boundary_heal.py
execution_mode: code_change
mission_id: 01KZJQN68SWZ7T1YKGDB4Q4EVH
owned_files:
- src/specify_cli/charter_runtime/preflight/runner.py
- src/specify_cli/charter_runtime/preflight/hook.py
- src/specify_cli/charter_runtime/freshness/computer.py
- tests/specify_cli/charter_runtime/test_boundary_heal.py
tags: []
tracker_refs: []
agent_profile: python-pedro
role: implementer
agent: claude
wp_code: WP04
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role:
implementer) before anything else. Then read `plan.md`, `research.md` (D2 + boundary heal), and
`contracts/synthesize-seam.md` (boundary reconciler contract).

# Work Package Prompt: WP04 – Non-destructive boundary heal that clears stale

## Objectives & Success Criteria

- The implement/next boundary reconciler `_attempt_auto_refresh` heals **non-destructively**:
  it invokes synthesize in **preserve** mode (never `prune`, never a refusing path), so a flagless
  boundary heal is exit-0 and loses no content.
- A successful heal **clears `synthesized_drg` to fresh**, so `implement`/`next` proceed and a
  second invocation is not re-blocked (no infinite non-destructive loop).
- A references-parity **extension point** is installed (stub) for WP06 to implement — WP04 does not
  implement `generate`.

## Context & Constraints

- Today `_attempt_auto_refresh` (`runner.py:405-416`) runs a flagless `charter synthesize`
  subprocess judged purely by exit code (`runner.py:508`). With WP01+WP03, the preserve default is
  exit-0 and non-destructive — this WP ensures the boundary uses that path and never a prune/refuse.
- Freshness **self-clears** (amendment #2): `synthesized_drg` compares
  `compute_bundle_content_hash(repo_root)` against the manifest's stored `bundle_content_hash`,
  which WP01's `_rewrite_manifest` re-stamps on every write. So a successful non-destructive heal
  recomputes to `fresh` without a destructive rebuild — verify this by test; only fall back to
  `computer.py` (without weakening its hash comparison) if a proven case fails to clear.
- **Scope**: you own `runner.py`, `hook.py`, `computer.py`. Do not implement references-parity
  `generate` here (WP06 owns `references_refresh.py`); install a call to a stub/hook only.

## Subtasks & Detailed Guidance

### Subtask T017 – Route auto_refresh to preserve mode
- Ensure the synthesize the boundary runs is the preserve path (exit-0, non-destructive). If the
  subprocess invocation can hit a refusing/pruning path, pass the preserve-explicit invocation (a
  flag or dedicated entry so it can never refuse). Confirm a backed-divergence boundary heal returns
  0 and drops nothing.

### Subtask T018 – Verify `synthesized_drg` clears after the heal (self-clearing; computer.py fallback only)
- Per amendment #2: the signal **self-clears** — `_rewrite_manifest` (WP01) re-stamps the manifest's
  `bundle_content_hash` on every write, and freshness compares that against
  `compute_bundle_content_hash(repo_root)`. So after WP01 writes the merged manifest, the
  non-destructive heal makes `synthesized_drg` recompute to `fresh` on its own. **Primarily prove
  this with a test** (heal → recompute → fresh → second run not re-blocked). Only touch
  `freshness/computer.py` if a **proven** case fails to clear, and even then **do NOT weaken the
  hash comparison** (relaxing it would blind the boundary to real drift). Treat `computer.py` as a
  **guarded fallback**, not the primary mechanism.

### Subtask T019 – Install the references-parity extension point
- Add a call in `_attempt_auto_refresh` to a `refresh_references_if_needed(repo_root, cause)` hook
  that, in this WP, is a no-op stub (WP06 implements it in
  `src/specify_cli/charter_runtime/preflight/references_refresh.py`). This keeps runner.py owned by
  WP04 while WP06 owns the implementation — no ownership overlap.

### Subtask T020 – Tests
- New `tests/specify_cli/charter_runtime/test_boundary_heal.py`:
  - Authoring-only charter edit trips `synthesized_drg` stale → boundary heal runs → `implement`
    (or the preflight) proceeds, **0 nodes/edges lost**, `synthesized_drg` resolves `fresh`.
  - Second invocation is **not re-blocked** (freshness stays fresh; no re-trigger loop).
  - The heal never invokes a prune/refuse path (assert the preserve invocation).

## Branch Strategy

- Planning-base / merge-target: `fix/charter-synthesize-reconciliation` (PRs into `main`).
- Depends on WP01, WP03; run `spec-kitty agent action implement WP04 --agent <name>` after both are
  approved/done. Execution worktree per computed lane from `lanes.json`.

## Definition of Done

- [ ] Boundary heal is preserve-mode, exit-0, non-destructive.
- [ ] `synthesized_drg` clears to fresh after a heal; no re-block loop.
- [ ] References-parity stub hook installed (no behavior yet).
- [ ] Boundary tests green; `ruff` + `mypy` clean; complexity ≤ 15.

## Risks & Reviewer Guidance

- **Risk**: freshness not clearing → infinite non-destructive re-block. Reviewer: verify the
  second-run-not-re-blocked test.
- **Risk**: the boundary reaching a refusing path. Reviewer: confirm the preserve-explicit invocation.

## 🔴 Post-tasks squad amendments (MUST READ before implementing)

1. **[MAJOR] Do not promise "never refuses"; the boundary inherits WP03's preserve default.** The
   flagless `charter synthesize` the boundary runs is exit-0 for **backed** divergence (preserve
   default) — no new flag is needed or exists. Orphaned/unparseable inputs still refuse by design;
   define how a boundary refusal surfaces (a blocked_reason the operator can act on), rather than
   claiming the boundary can never refuse. Replace T017's "a flag or dedicated entry" with "invoke
   with no prune/dry-run flags (default preserve)".
2. **[MAJOR] Do NOT weaken `computer.py`'s hash comparison.** `synthesized_drg` freshness compares
   `compute_bundle_content_hash(repo_root)` (hashes `charter.yaml`) against the manifest's stored
   `bundle_content_hash`, which `_rewrite_manifest` re-stamps on every write (WP01). So the signal
   **clears on its own** once WP01 writes the merged manifest — verify this with a test; only touch
   `computer.py` if a proven case fails to clear. Relaxing the hash check would blind the boundary
   to real drift (a fresh-regression). Treat `computer.py` in owned_files as a guarded fallback only.
