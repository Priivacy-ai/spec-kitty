---
work_package_id: WP04
title: Read-path consolidation (Cluster A)
dependencies:
- WP03
requirement_refs:
- FR-002
- FR-012
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
phase: Phase 2 - Conversions
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3862211"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/missions/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/missions/feature_dir_resolver.py
- src/specify_cli/cli/commands/agent/context.py
- src/specify_cli/cli/commands/lifecycle.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Read-path consolidation

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/missions/`.

---

## Objectives & Success Criteria
- Fold the duplicate `feature_dir_resolver.candidate_feature_dir_for_mission` into the canonical `_read_path_resolver.resolve_mission_read_path` (one read primitive — FR-002).
- Replace the `_find_feature_directory` **silent fallback** to the primary checkout (in `agent/context.py` + `lifecycle.py`) with a **structured error** — no wrong-but-plausible path (FR-012, C-CTX-4).
- Route `prompt_source_dir` through the context's PromptSourceFragment (FR-012).
- **Done when:** `--mission <mid8>` and `--mission <full-slug>` resolve identically (fixes findings **F-001** decision-open + **F-003** context-resolve branch); missing surface raises a structured error; WP01 read-path parity flips green.

## Context & Constraints
- Design: `spec.md` FR-002/FR-012; `plan.md` IC-03; `contracts/...` C-CTX-1/C-CTX-4; `research/findings.md` F-001/F-003.
- The 3rd `_find_feature_directory` caller lives in `agent/mission.py` — that file is **owned by WP06**; WP06 applies the same fix there (no ownership overlap). Define the structured-error behaviour in the resolver primitive so all callers inherit it.
- C-009 selector rule: no silent fallback; ambiguity/unresolved → structured error (e.g. `FEATURE_CONTEXT_UNRESOLVED` / `MISSION_AMBIGUOUS_SELECTOR`).

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T012 — Fold duplicate read-path resolver
- Make `_read_path_resolver` the single primitive; delete/redirect `candidate_feature_dir_for_mission` (strangler-ordered, C-004).
### T013 — Structured error replaces silent fallback
- In `agent/context.py` + `lifecycle.py`, replace the primary-checkout silent fallback with the resolver's structured error. Add a regression test reproducing F-001 (`decision open --mission <mid8>`) and F-003.
### T014 — Route `prompt_source_dir`
- Resolve prompt files via the context's PromptSourceFragment, not an independent derivation.
### T015 — Flip WP01 read-path parity
- Make WP01's read-path assertions pass from both CWDs.

## Test Strategy
- Regression tests for F-001/F-003; WP01 read-path parity green; `ruff`+`mypy` zero issues.

## Risks & Mitigations
- *Silent-fallback removal surfaces latent misconfig as errors* → that is intended; ensure error messages are actionable.

## Review Guidance
- Recommended: **reviewer-renata**. Confirm one read primitive (C-005); confirm F-001/F-003 covered by tests.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-10T02:41:42Z – claude:opus:python-pedro:implementer – shell_pid=3835566 – Assigned agent via action command
- 2026-06-10T03:00:28Z – claude:opus:python-pedro:implementer – shell_pid=3835566 – Read-path consolidation done. T012: candidate_feature_dir_for_mission folded into _read_path_resolver (ONE primitive, C-005); feature_dir_resolver re-exports it. T013 (F-001/F-003/F-004): resolve_mission_read_path now canonicalizes mid8/ULID/numeric handles via resolve_mission, so --mission <mid8> resolves identically to --mission <full-slug>; ambiguity raises structured MissionSelectorAmbiguous (MISSION_AMBIGUOUS_SELECTOR), unresolved raises StatusReadPathNotFound -> context._find_feature_directory maps both to ActionContextError (FEATURE_CONTEXT_UNRESOLVED), no silent fallback (C-CTX-4); lifecycle.py routed to that resolver. T014: PromptSourceFragment(prompt_source_dir=<feature_dir>/tasks) assembled in resolve_action_context. T015: flipped test_read_path_fragment_parity (re-pointed to status_surface.status_read_dir, the consolidated read surface; WorkspaceFragment/primary_root stays WP05). NOTE: test_promptsource_fragment_parity also flipped (T014 owns prompt-source routing; xfail-map mis-attributed it to WP07) - WP07 lifecycle parity untouched/xfail. Regression tests: test_read_path_handle_resolution.py + test_context_find_feature_directory.py. Gates: parity 33 pass/4 xfail (WP05/06/07-lifecycle/08); ruff+mypy clean on changed files. 7 pre-existing baseline failures (test_find_repo_root_*, test_wrapper_delegation acknowledge) NOT caused by this WP. Edited resolution.py (T014) + parity test (T015) outside owned_files per prompt directive; guard warned (non-blocking).
- 2026-06-10T03:01:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=3862211 – Started review via action command
- 2026-06-10T03:07:07Z – user – shell_pid=3862211 – Review passed (reviewer-renata): F-001/F-003/F-004 fixed — resolve_mission_read_path canonicalizes mid8/ULID/numeric/slug handles via resolve_mission to one feature_dir; regression tests re-run green (test_read_path_handle_resolution 4/4, test_context_find_feature_directory 4/4) and genuinely assert mid8==full-slug. C-CTX-4 confirmed: StatusReadPathNotFound + MISSION_AMBIGUOUS_SELECTOR + ActionContextError(FEATURE_CONTEXT_UNRESOLVED), no silent fallback in context.py/lifecycle.py. C-005 shim re-exports primitive; 30+ callers happy-path preserved (coordination/review/core suites green). T014 PromptSourceFragment routed in resolve_action_context. Both xfail flips legit: read-path re-pointed to status_surface.status_read_dir (WP05 primary_root stays xfail), promptsource backed by T014; WP07 lifecycle parity untouched/xfail. Gates: parity 17pass/4xfail, missions+agent 266pass, ruff+mypy clean. 4 confirmed pre-existing failures (wrapper_delegation worktree-artifact; find_repo_root fails from primary too, WP04 untouched) — not regressions.
