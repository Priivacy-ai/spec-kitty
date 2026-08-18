---
work_package_id: WP04
title: doctor mission-state reconciliation + manifest honesty
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-009
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
phase: Phase 2 - Fail-closed adopters
history:
- at: '2026-08-18T20:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/migration/mission_state.py
create_intent:
- tests/specify_cli/migration/test_mission_state_identity.py
- tests/specify_cli/status/test_repair_preservation_sentinel.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/_mission_state_doctor.py
- src/specify_cli/migration/mission_state.py
- tests/specify_cli/migration/test_mission_state_identity.py
- tests/specify_cli/status/test_repair_preservation_sentinel.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – doctor mission-state reconciliation + manifest honesty

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

This WP **reconciles** a real contradiction the squad surfaced: `_anchor_repair_root` documents its worktree→primary re-anchor as deliberate (#2320, keep the primary `status.json` fresh), yet #3129/#3051 lists the same collapse-to-primary as a defect. Resolution: **keep** the primary status-home (#2320) AND **add checkout-identity awareness** so a lane invocation is not a silent, unannounced primary canonicalization, and the audit reports no false-green. Plus manifest honesty (FR-009).

Done when:
- The deliberate #2320 primary status-home target is **preserved** (not flipped to the invoking checkout).
- A lane invocation of `--fix` is surfaced (announced/refused) rather than silently canonicalizing the primary; `--audit` reports no false-green from a redirected read.
- The repair manifest enumerates **every** field it touches, including removed fields (FR-009).
- A **green sentinel** pins `bec7c25273` (review_result preservation at `mission_state.py:1879`) — this test is GREEN on base and stays green (NFR-004); it is NOT red-first.

## Context & Constraints

- Depends on **WP01**.
- **C-002**: verdict destruction is already fixed (`bec7c25273`, `_build_canonical_row:1858-1879` keeps `review_result`). Do NOT add a destruction/quarantine fix.
- Anchors: `_anchor_repair_root:504-535` (re-anchors via `resolve_canonical_root:532`, #2320 docstring `:505-521`); repair entry `repair_repo`; manifest built in `_build_canonical_row:1858-1879`; CLI `_mission_state_doctor.py` `--fix` path (~`:227/261`).
- Read: [spec.md](../spec.md) FR-004/FR-009/US1+US3, [research.md](../research.md) Decision 2 (#3051 reconciliation), [contracts](../contracts/resolver-and-verdict-contracts.md) C-4.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

## Subtasks & Detailed Guidance

### Subtask T012 – Red-first: lane invocation false-green / silent canonicalization [P]

- **Purpose**: Prove the missing identity awareness, with a green-after only a fail-closed refusal / honest-disagreement can satisfy.
- **Steps**: Fixture: primary + lane worktree with differing state. Run `doctor mission-state --audit`/`--fix` from the lane.
  - **RED on base**: assert either the audit reports agreement from a redirected read, or `--fix` silently canonicalizes the primary with no lane-invocation signal.
  - **GREEN after (positive) — for `--fix`**: assert (a) a `FailClosedRefusal` is raised, (b) its message names the primary path, (c) the primary is **unchanged**, (d) no lane write occurred. **For `--audit`**: assert it reports the invoking-checkout-vs-primary **disagreement** (not a false-green).
  - `@pytest.mark.regression`, pin `#3051`/`#3541`.
- **Files**: `tests/specify_cli/migration/test_mission_state_identity.py` (new).

### Subtask T013 – Preserve #2320 + add identity awareness

- **Purpose**: Reconcile deliberate-vs-defect.
- **Steps**:
  1. Keep `_anchor_repair_root` returning the **primary** canonical target (do NOT flip to invoking checkout — #2320).
  2. Before a `--fix` mutation, resolve the invocation's ownership via `resolve_checkout_identity(Path.cwd(), Intent.WRITE)`. When `not is_owner` (foreign lane), **refuse** via `FailClosedRefusal` naming the primary `canonical_target` — do NOT silently canonicalize. (Owner invocation proceeds unchanged.)
  3. **Concrete audit-comparison mechanism (no hand-waving):** `--audit` must compare the **invoking checkout's own state** against the **primary canonical** and report *disagreement* — it MUST NOT read only the redirected primary path and call that agreement. Specifically: obtain the invoking-checkout root by parsing `cwd`'s `.git` directly (the same decidable resolution WP01's guard uses — NOT `locate_project_root`, which re-anchors), obtain the primary canonical via `_anchor_repair_root` (`Intent.PRIMARY_READ`), and surface a mismatch when the invoking checkout's status/frontmatter differs from the primary's. A `--audit` that reads the primary at both ends (the current base behavior) is exactly the false-green this subtask removes.
- **Files**: `src/specify_cli/cli/commands/_mission_state_doctor.py`, `src/specify_cli/migration/mission_state.py`.

### Subtask T014 – Manifest honesty (FR-009)

- **Purpose**: The repair manifest must list every touched field, incl. removed.
- **Steps**: Extend the manifest produced around `_build_canonical_row` to enumerate added/changed/**removed** fields per row. Do not change what is preserved (C-002) — only make the manifest complete.
- **Files**: `src/specify_cli/migration/mission_state.py`.
- **Validation**: a repair that removes a field lists it in the manifest.

### Subtask T015 – Green sentinel for `bec7c25273` [P]

- **Purpose**: Prevent any WP from manufacturing a red by regressing the already-fixed preservation (NFR-004).
- **Steps**: Assert `_build_canonical_row` preserves `review_result` (and the FSM-guard inputs) — GREEN on base and after. Reference `bec7c25273` in the test docstring.
- **Files**: `tests/specify_cli/status/test_repair_preservation_sentinel.py` (new).
- **Notes**: This is a guard, not a red-first regression.

## Test Strategy (required)

- `pytest tests/specify_cli/migration/test_mission_state_identity.py tests/specify_cli/status/test_repair_preservation_sentinel.py -q`.
- Owner-checkout `--fix` still canonicalizes the primary normally.

## Risks & Mitigations

- **Risk**: flipping the #2320 target breaks 4 existing tests (`test_canonical_root_when_in_worktree.py`, `test_root_resolver.py`). **Mitigation**: T013 preserves the primary target; do not touch those tests' asserted behavior.
- **Risk**: over-refusing owner `--fix`. **Mitigation**: gate on foreign-lane invocation only.

## Review Guidance

- Confirm the #2320 primary target is preserved (diff `_anchor_repair_root`).
- Confirm no destruction fix was added (C-002).
- Confirm the sentinel is green and the identity regression is red-on-base/green-after.

## Activity Log

- 2026-08-18T20:00:00Z – system – Prompt created.
