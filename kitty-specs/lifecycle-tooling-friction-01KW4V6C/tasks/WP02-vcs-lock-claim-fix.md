---
work_package_id: WP02
title: vcs-lock claim-friction fix
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: mission/lifecycle-tooling-friction
merge_target_branch: mission/lifecycle-tooling-friction
branch_strategy: Planning artifacts for this mission were generated on mission/lifecycle-tooling-friction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/lifecycle-tooling-friction unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
phase: Mission-Lifecycle Tooling Friction
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1803548"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/implement.py
create_intent:
- tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement.py
- tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – vcs-lock claim-friction fix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: update the Activity Log as you address each item.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks: ` ```python `, ` ```bash `.

---

## Objectives & Success Criteria

- Back-to-back dependency-free root claims under `auto_commit=False` are NOT blocked by the first claim's own uncommitted vcs-lock write to `meta.json`.
- The vcs-lock-only `meta.json` change is excluded from the dirty-tree guard `_ensure_planning_artifacts_committed_git` in `implement.py`.
- The `auto_commit=True` (default) claim path is byte-identical — no behaviour change (NFR-001).
- **SC-003** is satisfied. `ruff` + `mypy` clean on new code.

## Context & Constraints

- Spec: [spec.md](../spec.md) — User Story 3, FR-006, SC-003.
- Plan: [plan.md](../plan.md) — IC-03.
- Research: [research.md](../research.md) — `#2222` reproduces only on `auto_commit=False`: the lock self-write via `set_vcs_lock` at `implement.py` ~:843 causes the next claim to `Exit(1)` at ~:374 (the `auto_commit=False` abort in `_print_planning_artifact_commit_instructions`). The dirty-tree guard itself is `_ensure_planning_artifacts_committed_git` at ~:632 (it assembles `files_to_commit` ~:632-714).
- **C-003 — the fix is STOP-GATING, not auto-committing**: the vcs-lock (`set_vcs_lock`) is one-time, in-process VCS-TYPE state, never the concurrency mutex. Excluding it from the dirty-tree guard introduces no race. Do NOT "fix" this by auto-committing the lock.
- **C-005 — causal sequencing**: land this (Lane C) with/before WP03 (Lane B) — create-time non-coord missions (#2218) make this friction more common, and WP03's end-to-end non-coord proof depends on this fix being in place.
- **C-006 — red-first** through the pre-existing surface: `spec-kitty agent action implement`.
- **NFR-001**: keep the `auto_commit=True` path unchanged; existing missions unaffected.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> Populated automatically by `spec-kitty agent mission tasks`. Do NOT edit manually.

## Subtasks & Detailed Guidance

### Subtask T004 – RED test: second claim not blocked by the first lock self-write

- **Purpose**: Reproduce #2222 through the pre-existing entry point before touching production code (red-first).
- **Steps**:
  1. Create `tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py`.
  2. Seed a realistic scratch mission with two dependency-free root WPs (real-format ids, C-007).
  3. Claim the first WP with `auto_commit=False` (so the vcs-lock write to `meta.json` stays uncommitted in the working tree).
  4. Claim the second dependency-free WP with `auto_commit=False`; assert it does NOT `Exit(1)` / is NOT blocked citing uncommitted planning artifacts.
  5. Confirm the test is RED against current `implement.py` (the second claim currently aborts on the dirty-tree guard).
- **Files**: `tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py` (new — in `owned_files` + `create_intent`).
- **Parallel?**: WP02 internal; this WP is parallel-safe with WP01/WP04/WP05/WP06.
- **Notes**: Drive the real `spec-kitty agent action implement` claim surface — not a direct call to the guard helper (red-first through the pre-existing path).

### Subtask T005 – Exclude the vcs-lock-only meta change from the dirty-tree guard

- **Purpose**: Make the second claim pass without weakening the real concurrency protection.
- **Steps**:
  1. In `src/specify_cli/cli/commands/implement.py`, locate `_ensure_planning_artifacts_committed_git` (the dirty-tree guard, ~:632; it assembles `files_to_commit` ~:632-714) and the vcs-lock self-write via `set_vcs_lock` (~:843). The `auto_commit=False` `Exit(1)` lives at ~:374 in `_print_planning_artifact_commit_instructions`.
  2. Narrowly exclude a `meta.json` diff that is ONLY the vcs-lock field change from the "uncommitted planning artifacts" set — so the guard ignores the mission's own one-time lock write while still catching genuine uncommitted planning edits.
  3. **DoD — extract a pure helper**: the "is this `meta.json` diff only the vcs-lock fields?" decision MUST be an extracted pure helper, NOT a new inline branch in the guard. `_ensure_planning_artifacts_committed_git` already carries `# noqa: C901`; do NOT add a new inline branch to it, and do NOT add any new `# noqa` / `# type: ignore`. Reference the vcs-lock field names via the existing import (the symbol already imported from `mission_metadata.py`) — do NOT edit `mission_metadata.py`. Type-annotate the helper.
- **Files**: `src/specify_cli/cli/commands/implement.py`.
- **Parallel?**: After T004 is red.
- **Notes**: `set_vcs_lock`/`mission_metadata.py` is reference only — do not modify it. Scope the exclusion to the lock field, not all `meta.json` edits. The lock-field set is referenced through the existing import, not re-declared.

### Subtask T006 – Regression: `auto_commit=True` path byte-identical

- **Purpose**: Prove the default path is unchanged (NFR-001).
- **Steps**:
  1. Add a regression assertion (same test file) exercising the `auto_commit=True` claim path; assert behaviour/commit semantics are unchanged.
  2. **DoD — explicit negative guard (required, not just a risk note)**: add an assertion that a `meta.json` dirtied with a **NON-lock** field (any field other than the vcs-lock fields) STILL causes the claim to `Exit(1)` on the dirty-tree guard. This proves the exclusion is narrow (lock-field-only) and did NOT degrade into "exclude all `meta.json`".
  3. Make the green case of T004 pass after T005; rerun the full file.
- **Files**: `tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py`.
- **Parallel?**: After T005.
- **Notes**: This guards the operator decision that only the `False` path changes, AND that the exclusion is scoped strictly to the vcs-lock fields.

## Test Strategy

- New test: `tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py`.
- Red-first via `spec-kitty agent action implement` (the pre-existing surface), proven RED before T005.
- Run: `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py -q`.
- Realistic scratch-mission fixtures (C-007).

## Risks & Mitigations

- **Over-broad exclusion**: scope strictly to the vcs-lock field; an exclusion that swallows other `meta.json` edits would mask real uncommitted-artifact bugs — this is now a required T006 DoD assertion (a non-lock dirty `meta.json` STILL `Exit(1)`s), not just a risk note.
- **False race fear**: the lock is VCS-type state not a mutex (C-003) — no concurrency regression; document this in the PR.
- **Green-before-and-after**: ensure the RED case genuinely fails pre-fix.

## Review Guidance

- Confirm the second `auto_commit=False` claim succeeds and the RED case was real.
- Confirm the exclusion is narrow (lock field only) and a genuinely dirty non-lock `meta.json` still blocks.
- Confirm the `auto_commit=True` path is unchanged.
- Confirm the lock-diff decision is an extracted pure helper (no new inline branch in the already-`# noqa: C901` guard), references the lock fields via the existing import, adds no new `# noqa`/`# type: ignore`, and does NOT touch `mission_metadata.py`.
- Confirm `ruff`/`mypy` clean and the new helper is ≤ 15 complexity.

## Activity Log

> **CRITICAL**: Append new entries at the END in chronological order. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T16:23:44Z – claude:opus:python-pedro:implementer – shell_pid=1735250 – Assigned agent via action command
- 2026-06-27T16:46:12Z – claude:opus:python-pedro:implementer – shell_pid=1735250 – Ready: second auto_commit=False claim no longer blocked by first lock-write; auto_commit=True unchanged; non-lock dirty meta still Exit(1)
- 2026-06-27T16:47:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=1803548 – Started review via action command
- 2026-06-27T16:51:25Z – user – shell_pid=1803548 – Review APPROVE (reviewer-renata, isolated): _VCS_LOCK_META_FIELDS exactly matches set_vcs_lock keys (vcs,vcs_locked_at) — not under/over-broad; negative guard authentic (non-lock dirty meta still Exit(1)); RED-first proven via real implement(); auto_commit=True byte-identical; gates green
