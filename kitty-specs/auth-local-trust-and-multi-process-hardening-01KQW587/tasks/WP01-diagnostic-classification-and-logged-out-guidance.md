---
work_package_id: WP01
title: Diagnostic Classification And Logged-Out Guidance
dependencies: []
requirement_refs:
- C-003
- C-005
- C-006
- FR-001
- FR-002
- FR-003
- NFR-002
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-auth-local-trust-and-multi-process-hardening-01KQW587
base_commit: e087f100e629f815be9179f984af9ff8236c53ae
created_at: '2026-05-05T13:57:39.087097+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Diagnostics
assignee: ''
agent: "codex:gpt-5:python-pedro:reviewer"
shell_pid: "90620"
history:
- at: '2026-05-05T13:41:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/_team.py
- src/specify_cli/sync/batch.py
- src/specify_cli/sync/body_transport.py
- src/specify_cli/sync/client.py
- src/specify_cli/tracker/saas_client.py
- tests/sync/test_batch_error_surfacing.py
- tests/sync/test_body_transport.py
- tests/sync/test_team_ingress_resolver.py
- tests/sync/tracker/test_saas_client.py
- tests/sync/tracker/test_saas_service.py
- tests/cli/commands/test_sync_routes.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 - Diagnostic Classification And Logged-Out Guidance

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Make hosted-sync and tracker-bound CLI workflows classify auth-adjacent failures truthfully. Logged-out Teamspace/tracker-bound commands must tell the user to run `spec-kitty auth login`; missing Private Teamspace direct ingress must keep the direct-ingress category and must not collapse into `server_error`.

Implementation command: `spec-kitty agent action implement WP01 --agent <name>`

## Context & Constraints

Read:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/spec.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/diagnostic-classification.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/data-model.md`

Do not change SaaS route contracts. Do not edit `spec-kitty-tracker` unless a focused investigation proves the CLI cannot classify correctly without a package change. Do not expose raw tokens, lookup hashes, peppers, family IDs, or audit metadata.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` decides the lane workspace path and records the lane branch in `base_branch`.
- **If human instructions contradict these fields**: stop and resolve the intended landing branch before coding.

## Subtasks & Detailed Guidance

### Subtask T001 - Inventory hosted-sync and tracker-bound diagnostic entry points

- **Purpose**: Find the exact CLI-owned paths that can report vague tracker/sync/server failures when auth or Private Teamspace state is the real issue.
- **Steps**:
  1. Inspect `src/specify_cli/cli/commands/sync.py`, `src/specify_cli/sync/_team.py`, `src/specify_cli/sync/batch.py`, `src/specify_cli/sync/body_transport.py`, `src/specify_cli/sync/client.py`, and `src/specify_cli/tracker/saas_client.py`.
  2. Trace where `server_error`, direct-ingress skipped, missing Private Teamspace, and `spec-kitty auth login` messages are emitted.
  3. Identify the smallest set of code paths needed to satisfy FR-001, FR-002, and FR-003.
- **Files**: owned files only.
- **Parallel?**: This can be done independently of WP02 and WP03.
- **Notes**: Keep a short implementation note in the final handoff naming the changed entry points.

### Subtask T002 - Define classification mapping

- **Purpose**: Make category selection deterministic.
- **Steps**:
  1. Apply this mapping: no usable local session -> `unauthenticated`; missing Private Teamspace/direct ingress -> `direct_ingress_missing_private_team` or the existing peer; temporary network failure -> retryable transport; true 5xx -> `server_error`.
  2. Preserve existing field names where consumers exist; add explicit peer fields only if needed.
  3. Keep user-facing wording aligned with machine-facing categories.
- **Files**: likely `sync.py`, `_team.py`, `batch.py`, `body_transport.py`, `client.py`, `saas_client.py`.
- **Parallel?**: No; complete inventory first.
- **Notes**: Do not introduce a broad new auth taxonomy if existing categories are enough.

### Subtask T003 - Fix direct-ingress missing Private Teamspace classification for #889

- **Purpose**: Ensure the known missing Private Teamspace path is not reported as `server_error`.
- **Steps**:
  1. Reproduce the classification path with an existing or new fixture.
  2. Adjust the code so direct-ingress 403/missing Private Teamspace uses the direct-ingress category.
  3. Verify stderr/stdout routing still respects strict JSON stdout tests where applicable.
- **Files**: likely `_team.py`, `batch.py`, `body_transport.py`, and sync tests.
- **Parallel?**: No; depends on T002.
- **Notes**: Preserve the existing `CATEGORY_MISSING_PRIVATE_TEAM` language if practical.

### Subtask T004 - Add logged-out Teamspace/tracker guidance for #829

- **Purpose**: Make recovery obvious for users with bound repos but no active session.
- **Steps**:
  1. Add or adjust tests for a Teamspace/tracker-bound workflow with no active auth session.
  2. Ensure output includes `spec-kitty auth login`.
  3. Ensure the same path does not report generic tracker, sync, or server failure.
- **Files**: `sync.py`, `client.py`, `saas_client.py`, `test_sync_routes.py`, tracker/sync tests.
- **Parallel?**: Can be implemented after T002 and alongside T003 if files do not conflict.
- **Notes**: Use concise CLI guidance; avoid dumping internal state.

### Subtask T005 - Add diagnostic regression tests and verify focused slices

- **Purpose**: Lock the behavior down.
- **Steps**:
  1. Add regression coverage for unauthenticated, missing Private Teamspace, retryable transport, and true server failure.
  2. Include the exact #889 path.
  3. Include the logged-out Teamspace/tracker-bound path for #829.
  4. Run focused tests.
- **Files**: owned test files.
- **Parallel?**: No; this validates the package.
- **Notes**: Tests should fail on the old `server_error` misclassification.

## Test Strategy

Run the focused suite:

```bash
uv run pytest \
  tests/sync/test_batch_error_surfacing.py \
  tests/sync/test_body_transport.py \
  tests/sync/test_team_ingress_resolver.py \
  tests/sync/tracker/test_saas_client.py \
  tests/sync/tracker/test_saas_service.py \
  tests/cli/commands/test_sync_routes.py
```

If a command path touches hosted auth, tracker, SaaS, or sync behavior against the dev deployment on this computer, set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

## Definition of Done

- Logged-out Teamspace/tracker-bound workflows show `spec-kitty auth login`.
- Missing Private Teamspace direct ingress never classifies as `server_error`.
- Retryable transport and true server failures remain distinguishable.
- Focused tests pass.

## Risks & Mitigations

- **Risk**: JSON stdout gets polluted by warning text. **Mitigation**: preserve strict stdout/stderr separation in sync tests.
- **Risk**: Tracker package ownership is assumed too early. **Mitigation**: keep changes in CLI surfaces unless a failing fixture proves otherwise.

## Review Guidance

Reviewers should verify category semantics, user recovery guidance, and strict JSON behavior. Confirm no SaaS contract changes or token leaks were introduced.

## Integration Verification

Before moving this WP to `for_review`, verify:

- [ ] A logged-out Teamspace-bound workflow prints `spec-kitty auth login`.
- [ ] A tracker-bound workflow without an active session does not report generic tracker, sync, or server failure.
- [ ] Missing Private Teamspace direct ingress uses the direct-ingress category.
- [ ] True hosted 5xx still maps to `server_error`.
- [ ] Retryable transport failure does not map to missing Private Teamspace.
- [ ] Strict JSON stdout tests still keep diagnostics off stdout.
- [ ] User-facing output contains no raw tokens, lookup hashes, peppers, family IDs, or audit metadata.

## Out Of Scope

- Do not change `/oauth/token`, `/oauth/revoke`, `/api/v1/session-status`, or hosted route contracts.
- Do not add rollout gating to `spec-kitty-tracker`.
- Do not edit the sibling `spec-kitty-tracker` checkout from this WP.
- Do not introduce a new cross-repo tracker release requirement.

## Implementation Handoff Notes

If investigation proves `spec-kitty-tracker` owns a specific normalization bug, stop after adding the failing CLI-side fixture and record the exact tracker contract gap in the Activity Log. The planner explicitly made tracker context-only unless evidence proves ownership. Prefer a narrow CLI adapter fix if the tracker package already exposes enough information to classify correctly.

Leave WP05 enough detail to connect each changed path to #829 and #889. Include the command output category names, not just "tests passed", so review can verify the user-facing recovery story.
If you add a new helper, keep its API private to the CLI unless multiple command surfaces prove they need it.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-05-05T13:41:33Z – system – Prompt created.
- 2026-05-05T13:57:40Z – codex:gpt-5:python-pedro:implementer – shell_pid=40006 – Assigned agent via action command
- 2026-05-05T14:08:38Z – codex:gpt-5:python-pedro:implementer – shell_pid=40006 – Ready for review
- 2026-05-05T14:10:35Z – codex:gpt-5:python-pedro:reviewer – shell_pid=80335 – Started review via action command
- 2026-05-05T14:14:02Z – codex:gpt-5:python-pedro:reviewer – shell_pid=80335 – Moved to planned
- 2026-05-05T14:14:59Z – codex:gpt-5:python-pedro:implementer – shell_pid=84343 – Started implementation via action command
- 2026-05-05T14:21:29Z – codex:gpt-5:python-pedro:implementer – shell_pid=84343 – Ready for review: no-token hosted sync now returns unauthenticated BatchSyncResult without mutating the durable queue; sync now summary/report use the service category.
- 2026-05-05T14:22:34Z – codex:gpt-5:python-pedro:reviewer – shell_pid=90620 – Started review via action command
- 2026-05-05T14:25:20Z – codex:gpt-5:python-pedro:reviewer – shell_pid=90620 – Review passed: cycle 3 verified prior no-token sync blocker fixed; unauthenticated failures/report agree and queue preserved; focused sync/tracker tests passed
