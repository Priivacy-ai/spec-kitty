---
work_package_id: WP05
title: Worktree-pointer parser collapse (Cluster C)
dependencies:
- WP03
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
phase: Phase 2 - Conversions
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3943175"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/workspace/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/paths.py
- src/specify_cli/workspace/root_resolver.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Worktree-pointer parser collapse

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/workspace/`.

---

## Objectives & Success Criteria
- Make `core/paths.py` the **single** worktree-pointer parser feeding the context's WorkspaceFragment (`primary_root`).
- Delete the duplicate parser in `workspace/root_resolver.py` (~200 LOC) after re-pointing its callers (FR-002, NFR-005).
- **Done when:** one parser; callers re-pointed; net LOC down; WP01 workspace parity flips green.

## Context & Constraints
- Design: `spec.md` FR-002/NFR-005; `plan.md` IC-04; `research.md` R-B (Cluster C, ~200 LOC).
- C-004 strangler order: re-point callers to `core/paths` FIRST, prove parity, THEN delete the duplicate.

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T016 — Single parser in `core/paths`
- Ensure `core/paths` exposes the canonical worktree-pointer parse; the context consumes it for `primary_root`.
### T017 — Delete duplicate; re-point callers
- Grep all callers of `workspace/root_resolver`'s parser; redirect to `core/paths`; delete the now-dead parser.
### T018 — Net-LOC-down + parity
- Report delete-vs-add in the handoff (NFR-005); flip WP01 workspace parity.

## Test Strategy
- Existing path-resolution tests stay green; WP01 workspace parity green; `ruff`+`mypy` zero issues.

## Risks & Mitigations
- *Missed caller* → grep thoroughly before deletion; rely on type-check + suite.

## Review Guidance
- Recommended: **reviewer-renata**. Confirm one parser remains (C-005); confirm LOC subtraction.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-10T03:36:59Z – claude:opus:python-pedro:implementer – shell_pid=3932181 – Assigned agent via action command
- 2026-06-10T03:43:46Z – claude:opus:python-pedro:implementer – shell_pid=3932181 – Single worktree-pointer parser: core/paths.resolve_canonical_root is now canonical; workspace/root_resolver duplicate parser internals deleted (~119 LOC, re-exports public surface so 3 importers stay re-pointed without edits, C-004). WorkspaceFragment assembled in resolve_action_context with CWD-invariant primary_root; WP01 workspace parity flipped green. WP07/WP08 xfails intact.
- 2026-06-10T03:44:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=3943175 – Started review via action command
- 2026-06-10T03:48:03Z – user – shell_pid=3943175 – Review passed (reviewer-renata): One worktree-pointer parser confirmed — core/paths.resolve_canonical_root is canonical; root_resolver re-exports it (no duplicate). canonicalize_feature_dir is a genuine consumer (calls resolve_canonical_root), not a second parser. Net -120 LOC in root_resolver (205->85); deleted internals (_read_worktree_pointer/_canonical_from_worktree_gitdir/_CACHE) have zero dangling refs; all 5 importers consume the public surface (C-004 re-point-before-delete honoured). WorkspaceFragment.primary_root = get_main_repo_root (single parser), CWD-invariant; parity test test_workspace_fragment_parity flipped green via real resolve_action_context (not synthetic); WP07/WP08 xfails intact. Gates: parity+workspace+contract 27 passed/2 xfailed; ruff clean; only failure test_non_git_directory_raises (stray /tmp/.git host artifact, identical .git.is_dir() logic on base) + 3 mypy errors all in untouched pre-existing code (get_feature_target_branch, canonicalize_feature_dir return) — confirmed on base, zero in WP05-added region. No --feature/terminology regressions. Scope: exactly the 4 directed files.
