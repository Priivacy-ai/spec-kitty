---
work_package_id: WP02
title: intake fail-closed identity check
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
phase: Phase 2 - Fail-closed adopters
history:
- at: '2026-08-18T20:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/intake.py
create_intent:
- tests/specify_cli/cli/commands/test_intake_identity.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/intake.py
- tests/specify_cli/cli/commands/test_intake_identity.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – intake fail-closed identity check

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

`intake` must perform a fail-closed checkout-identity check before writing the shared untracked brief slot when invoked from a foreign checkout, and `--force` must not overwrite a slot owned by a different checkout without that check (FR-002).

Done when:
- A red-first regression proves that on base, `intake` invoked from a lane worktree clobbers the **primary's** shared brief slot.
- After the fix, `intake` from a foreign checkout refuses via the WP01 `FailClosedRefusal` seam, naming the target slot path.
- `--force` still routes through the identity check.

## Context & Constraints

- Depends on **WP01** (`resolve_checkout_identity` + `FailClosedRefusal`).
- Read: [spec.md](../spec.md) FR-002/US1, [research.md](../research.md) Decision 2, [contracts](../contracts/resolver-and-verdict-contracts.md) C-2.
- Anchors: `intake.py:57-62` `_resolve_repo_root` returns `find_repo_root(Path.cwd())` (re-anchors worktree→primary); brief slot written at `intake.py:95-96` / `:236-237`; slots are gitignored (`.gitignore:204-205`) — the hazard is the **shared untracked-slot clobber** (spec C-003), not a tracked diff.
- The remediation is fail-closed refusal (#3128), NOT a checkout-local redirect. Do not silently redirect the write.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

## Subtasks & Detailed Guidance

### Subtask T007 – Red-first regression [P]

- **Purpose**: Prove the defect on base through the real CLI, and lock the green-after so it can ONLY be satisfied by a fail-closed refusal — not the forbidden redirect.
- **Steps**: Fixture: a primary with an existing brief slot + a linked lane worktree. Invoke `intake` from the lane.
  - **RED on base**: assert the primary's `.kittify/mission-brief.md` was overwritten.
  - **GREEN after (positive, non-fakeable) — assert ALL of**: (a) a `FailClosedRefusal` is raised; (b) its message contains the target checkout path verbatim; (c) the primary's slot is **unchanged** (byte-identical to before); AND (d) **no** brief slot was written in the lane worktree either. Assertion (d) is critical: it forecloses the C-003/#3128-**forbidden** "redirect the write into the lane" fake — a redirect would also make (c) true, so (c) alone is insufficient.
  - Mark `@pytest.mark.regression`, pin `#3540`.
- **Files**: `tests/specify_cli/cli/commands/test_intake_identity.py` (new).
- **Validation**: red on base; after T008 all of (a)–(d) hold.

### Subtask T008 – Adopt the identity guard; fail closed

- **Purpose**: Stop the silent cross-checkout clobber.
- **Steps**:
  1. At the write decision (`_resolve_repo_root` / the write site around `:95-96`/`:236-237`), call `resolve_checkout_identity(Path.cwd(), Intent.WRITE)`.
  2. If `not is_owner`, raise the `FailClosedRefusal` naming `canonical_target`; do not write.
  3. If owner, proceed as today.
- **Files**: `src/specify_cli/cli/commands/intake.py`.
- **Notes**: reuse the WP01 seam; do not construct an ad-hoc refusal string (NFR-003 gate will catch it).

### Subtask T009 – `--force` identity check

- **Purpose**: `--force` must not bypass identity.
- **Steps**: Ensure the `--force` path still calls the identity check before overwriting; a foreign-owned slot is refused even with `--force` (owner-of-slot may proceed).
- **Files**: `src/specify_cli/cli/commands/intake.py`.
- **Validation**: `--force` from a lane against a primary-owned slot refuses.

## Test Strategy (required)

- `pytest tests/specify_cli/cli/commands/test_intake_identity.py -q` — red on base, green after.
- Confirm owner-checkout intake still writes normally (no new refusal).

## Risks & Mitigations

- **Risk**: breaking normal owner-checkout intake. **Mitigation**: explicit owner-path test stays green.

## Review Guidance

- Verify the refusal message names the concrete slot path.
- Verify `--force` cannot bypass the check.

## Activity Log

- 2026-08-18T20:00:00Z – system – Prompt created.
