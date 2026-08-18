---
work_package_id: WP03
title: doctor tool-surfaces --fix fail-closed refusal
dependencies:
- WP01
requirement_refs:
- FR-003
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
phase: Phase 2 - Fail-closed adopters
history:
- at: '2026-08-18T20:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/_command_surface_doctor.py
create_intent:
- tests/specify_cli/cli/commands/test_tool_surfaces_fail_closed.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/_command_surface_doctor.py
- src/specify_cli/tool_surface/repair.py
- tests/specify_cli/cli/commands/test_tool_surfaces_fail_closed.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – doctor tool-surfaces --fix fail-closed refusal

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

**Cleanest confirmed defect (#3129 §1).** `doctor tool-surfaces --fix` invoked from a lane worktree silently repairs the **primary's** per-checkout agent-surface manifest (`.claude/commands/*` etc.). It must fail closed instead (FR-003).

Done when:
- A red-first regression proves the silent primary mutation on base.
- After the fix, a lane invocation refuses (via the WP01 seam) naming the primary checkout; an owner invocation still repairs normally.

## Context & Constraints

- Depends on **WP01**.
- Tool surfaces are **per-checkout tracked** agent files — NOT status. The #2320 status-doctrine does NOT apply here; there is no deliberate-centralization defense for this command. It is unambiguously a defect.
- Anchors: `_command_surface_doctor.py:755-773` `_resolve_tool_surfaces_project` calls `locate_project_root()` with no start-arg (re-anchors worktree→primary); `run_tool_surfaces_audit:776-812` passes that primary `project_path` into `run_tool_surfaces(..., fix=fix)`; repair engine `tool_surface/repair.py`.
- Read: [spec.md](../spec.md) FR-003/US1, [contracts](../contracts/resolver-and-verdict-contracts.md) C-2.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

## Subtasks & Detailed Guidance

### Subtask T010 – Red-first regression [P]

- **Purpose**: Prove the silent primary mutation, with a green-after that ONLY a fail-closed refusal can satisfy (not the forbidden redirect).
- **Steps**: Fixture: primary + linked lane worktree, drift/delete a `.claude/commands/*.md` surface in the lane. Run `doctor tool-surfaces --fix` from the lane.
  - **RED on base**: assert the **primary's** manifest was repaired while the lane's surface stayed broken.
  - **GREEN after (positive, non-fakeable) — assert ALL of**: (a) a `FailClosedRefusal` is raised; (b) its message contains the primary checkout path verbatim; (c) the primary's manifest is **unchanged**; AND (d) the command did **not** repair the lane's surface either (it refused, it did not redirect the repair into the lane — closing the C-003/#3128-forbidden redirect fake).
  - `@pytest.mark.regression`, pin `#2613`.
- **Files**: `tests/specify_cli/cli/commands/test_tool_surfaces_fail_closed.py` (new).

### Subtask T011 – Adopt guard; fail closed

- **Purpose**: Refuse a foreign-checkout `--fix`.
- **Steps**:
  1. In `_resolve_tool_surfaces_project` / `run_tool_surfaces_audit`, before performing a `fix`, call `resolve_checkout_identity(Path.cwd(), Intent.WRITE)`.
  2. If `not is_owner`, raise `FailClosedRefusal` naming the primary `canonical_target`; do not mutate.
  3. Owner invocation (or `--audit` read-only) proceeds unchanged. Keep the audit (read-only) path working from anywhere.
- **Files**: `src/specify_cli/cli/commands/_command_surface_doctor.py`, `src/specify_cli/tool_surface/repair.py` (only if the refusal must be threaded through the repair entry).
- **Notes**: canonical remediation is refusal (#3128), consistent with #3128's fail-closed identity approach.

## Test Strategy (required)

- `pytest tests/specify_cli/cli/commands/test_tool_surfaces_fail_closed.py -q` — red on base, green after.
- Owner-checkout `--fix` still repairs; `--audit` from a lane still reads.

## Risks & Mitigations

- **Risk**: over-refusing the read-only `--audit`. **Mitigation**: gate only the `fix` mutation, not the audit read.

## Review Guidance

- Confirm the refusal is specific to the mutating `--fix` from a foreign checkout.
- Confirm the message names the primary path.

## Activity Log

- 2026-08-18T20:00:00Z – system – Prompt created.
