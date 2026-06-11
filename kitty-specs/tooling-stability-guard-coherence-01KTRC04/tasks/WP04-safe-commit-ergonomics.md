---
work_package_id: WP04
title: 'safe-commit ergonomics: dir/bulk args, --to-branch, env-var retirement'
dependencies:
- WP02
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T15:47:19.931369+00:00'
subtasks:
- T014
- T015
- T016
- T017
phase: Phase 2 - Spine riders
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "220388"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/safe_commit_cmd.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/safe_commit_cmd.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – safe-commit ergonomics

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match if none assigned.

---

## Objectives & Success Criteria
Fix the operator-facing papercuts (#1820, #1330) on the now-CommitTarget-based entry point:
- **Directory & bulk arguments** expand to contained files validated against `CommitTarget`'s worktree, with an **explicit expansion report** in the output (never silent inclusion).
- **`--to-branch` resolves INTO the CommitTarget** before evaluation (single destination authority, C-GUARD-3a) and is always honored.
- **Retire `SPEC_KITTY_INFER_DESTINATION_REF`** — the env-var inference path + its constant + its tests (deletions ledger). Two destination resolvers is exactly what this mission kills. The explicit `--to-branch` or context-resolved destination are the only sources.
- Also convert this CLI's own `assert_not_protected_branch` rim-call to the WP02 facade path (it was deferred from WP02 because this file is yours).
- **Done when:** #1820 + #1330 regression repros pass; "No requested changes" never fires for files genuinely differing from HEAD.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-002), plan.md (IC-03), contracts/ (C-GUARD-5, C-GUARD-3a), research/plan-review-reducer-randy.md (env-var retirement adjudication)}`.
- Live repro material: this session's own history — dir args produced "staging area contains unexpected paths"; `SPEC_KITTY_INFER_DESTINATION_REF=1` produced false "No requested changes" (see findings F-002 in the 01KTPKST mission's research/findings.md).
- WP02 (merged into your lane) provides `safe_commit(CommitTarget, …)` — consume it.

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T014 — Dir/bulk expansion + report
- A directory argument expands to its tracked+modified / untracked-new contained files (relative to the CommitTarget worktree). Print the expansion (`Expanding dir/ → N files: …`). The staged-paths match compares against the EXPANDED set, killing the "unexpected paths" refusal for dir args.

### T015 — `--to-branch` → CommitTarget
- The flag value constructs/validates the CommitTarget used for evaluation; mismatch between current branch and `--to-branch` follows the existing redirect/refusal semantics but through the ONE authority. No second derivation in this file.

### T016 — Retire the env-var path
- Delete `SPEC_KITTY_INFER_DESTINATION_REF` handling + constant + its tests (locate via `rg SPEC_KITTY_INFER_DESTINATION_REF src tests`). Update the CLI help text: explicit `--to-branch` (or resolved context destination) only. Out-of-map edits for the constant's home file: one-line rationale.

### T017 — Regression tests
- (a) dir arg with mixed modified+untracked contents commits all + reports expansion; (b) `--to-branch <branch>` honored from a non-target CWD; (c) the old env-var set has NO effect (deleted); (d) files genuinely differing from HEAD are never reported "No requested changes" (the F-002 misfire repro).

## Definition of Done
- Repros green; `rg SPEC_KITTY_INFER_DESTINATION_REF` → zero hits; `ruff`+`mypy` clean; WP01 invariants still green.

## Risks & Mitigations
- *Silent over-inclusion on dir expansion* → the report + a test asserting the expansion list is printed.

## Review Guidance
- Recommended: **reviewer-renata**. Verify single-destination-authority (no derivation in this file) and the expansion report UX.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T20:28:16Z – user – shell_pid=158021 – Dir/bulk args expand to contained changed+untracked files (validated against CommitTarget worktree) with explicit 'Expanding dir/ -> N files' report; --to-branch resolves into a single CommitTarget (one authority, rim assert_not_protected_branch dropped in favor of safe_commit's embedded guard); SPEC_KITTY_INFER_DESTINATION_REF retired (constant+handling+tests, rg zero). WP01 suite 4/5xfail unchanged; +4 T017 regressions green; ruff+mypy clean.
- 2026-06-10T20:28:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=220388 – Started review via action command
- 2026-06-10T20:30:59Z – user – shell_pid=220388 – Review passed: dir/bulk expansion via git status --porcelain -- <dir> (pathspec confined, no sibling-prefix leak; out-of-repo dirs raise via relative_to, no silent inclusion); explicit 'Expanding dir/ -> N files' report in human + --json; staged-paths backstop compares EXPANDED set. Single destination authority C-GUARD-3a: one _resolve_commit_target, one CommitTarget per branch, no second derivation, rim assert_not_protected_branch removed (guard fires solely via safe_commit). WP01 invariants 4 passed/5 xfailed no XPASS. SPEC_KITTY_INFER_DESTINATION_REF: constant+handling gone, only the has-no-effect regression test references it. F-002 misfire test present+green. 7/7 CLI tests pass; ruff+mypy clean on touched files.
