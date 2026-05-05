---
work_package_id: WP03
title: Auth/Storage BLE001 Guardrail
dependencies: []
requirement_refs:
- FR-006
- FR-007
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 1 - Guardrails
assignee: ''
agent: "codex:gpt-5:python-pedro:reviewer"
shell_pid: "82254"
history:
- at: '2026-05-05T13:41:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/review.py
- src/specify_cli/cli/commands/auth.py
- src/specify_cli/cli/commands/_auth_doctor.py
- src/specify_cli/cli/commands/_auth_login.py
- src/specify_cli/cli/commands/_auth_logout.py
- src/specify_cli/cli/commands/_auth_status.py
- src/specify_cli/auth/flows/revoke.py
- src/specify_cli/auth/transport.py
- src/specify_cli/auth/http/transport.py
- tests/review/test_ble001_guardrail.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 - Auth/Storage BLE001 Guardrail

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Make auth/storage broad exception suppressions auditable. Unjustified `# noqa: BLE001` suppressions in scoped auth/storage paths must fail with actionable file and line output; justified suppressions with specific safety reasons must pass.

Implementation command: `spec-kitty agent action implement WP03 --agent <name>`

## Context & Constraints

Read:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/ble001-guardrail.md`
- Existing BLE001 audit code in `src/specify_cli/cli/commands/review.py`

This WP owns guard implementation plus scoped cleanup in auth command, auth revoke, and auth transport files. It does not own the auth hot-path files assigned to WP04 (`token_manager.py`, `refresh_transaction.py`, `session.py`, `secure_storage/file_fallback.py`). WP04 depends on this guard and must clean up suppressions in its own auth files after the guard exists.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` decides the lane workspace path and records the lane branch in `base_branch`.

## Subtasks & Detailed Guidance

### Subtask T011 - Extract or isolate the auth/storage BLE001 audit helper

- **Purpose**: Make the guard testable without running a full mission review.
- **Steps**:
  1. Inspect the existing BLE001 audit in `src/specify_cli/cli/commands/review.py`.
  2. Extract a helper or refactor locally so tests can pass synthetic files/lines.
  3. Preserve current review command behavior where possible.
- **Files**: `review.py`.
- **Parallel?**: Can run independently from WP01 and WP02.
- **Notes**: Keep the extraction small and local.

### Subtask T012 - Define scoped suppression rule and reason-quality checks

- **Purpose**: Enforce "specific reason required" rather than a blanket ban.
- **Steps**:
  1. Define scoped paths from the contract.
  2. Treat missing reason as failure.
  3. Treat generic reasons such as "ignore", "broad catch", or empty punctuation as failure.
  4. Treat specific safety reasons as passing.
- **Files**: `review.py`.
- **Parallel?**: No; follows T011.
- **Notes**: Avoid NLP-heavy complexity; use a small deterministic rule.

### Subtask T013 - Add guardrail tests

- **Purpose**: Prove both pass and fail behavior.
- **Steps**:
  1. Create `tests/review/test_ble001_guardrail.py`.
  2. Add fixtures for justified, missing, and generic reasons.
  3. Include a fixture outside scoped paths to prove this mission does not overreach.
- **Files**: `tests/review/test_ble001_guardrail.py`.
- **Parallel?**: Can be written alongside T012 after helper shape is known.
- **Notes**: Tests should assert file and line in findings.

### Subtask T014 - Wire actionable output into review/check surface

- **Purpose**: Make failures useful to implementers.
- **Steps**:
  1. Ensure failure output names file path, line number, suppression text, and remediation.
  2. Preserve existing review output style.
  3. Run focused review tests and ruff.
- **Files**: `review.py`, `test_ble001_guardrail.py`.
- **Parallel?**: No; final integration.
- **Notes**: Avoid broad changes to review flow semantics.

## Test Strategy

```bash
uv run pytest tests/review/test_ble001_guardrail.py
uv run pytest tests/review/
uv run ruff check src/specify_cli/cli/commands/review.py tests/review/test_ble001_guardrail.py
```

## Definition of Done

- Justified scoped BLE001 suppressions pass.
- Missing/generic scoped BLE001 suppressions fail.
- Failure output includes file and line.
- Existing review tests still pass.

## Risks & Mitigations

- **Risk**: Creating a second lint system. **Mitigation**: keep it inside existing review/check tooling.
- **Risk**: False positives from terse but valid reasons. **Mitigation**: reject only clearly missing/generic text.

## Review Guidance

Reviewers should inspect the reason-quality rule for determinism and low false-positive risk.

## Integration Verification

Before moving this WP to `for_review`, verify:

- [ ] The helper can be tested directly with synthetic file content.
- [ ] A scoped auth/storage suppression with a specific safety reason passes.
- [ ] A scoped suppression with no reason fails.
- [ ] A scoped suppression with a generic reason fails.
- [ ] Failure output includes file path and line number.
- [ ] Existing review command behavior still works for normal mission review.
- [ ] Existing scoped suppressions in WP03-owned auth command/transport/revoke files either pass the new reason rule or are cleaned up.

## Out Of Scope

- Do not audit the entire repository as part of this WP.
- Do not ban all broad catches. Some broad catches are acceptable when they translate or isolate failure at a documented boundary.
- Do not create a separate linter command unless the existing review/check surface cannot support the guard.
- Do not edit WP04-owned auth hot-path files. If the guard finds violations there, record them for WP04 to clean up after this guard lands.

## Implementation Handoff Notes

The useful product is a deterministic, low-noise rule. Keep the unacceptable-reason list short and obvious: empty reason, bare `BLE001`, "ignore", "broad catch", and similarly generic placeholders. A valid reason should name the safety boundary, for example "optional telemetry must not abort command" or "storage cleanup failure is logged and local deletion continues".

## Reviewer Checklist

Reviewers should inspect the helper API, not just the command output. Confirm tests cover both scoped and out-of-scope paths so future maintainers do not accidentally expand this guard beyond the mission.

## Suggested Helper Shape

A small helper is enough. Prefer a pure function that accepts a path and line text, then returns either no finding or a finding object with path, line, reason, and remediation. The review command can collect matching lines from files and pass them through that helper.

Keep these behaviors explicit:

1. `# noqa: BLE001` with no trailing reason fails.
2. `# noqa: BLE001 - ignore` fails.
3. `# noqa: BLE001 - broad catch` fails.
4. `# noqa: BLE001 - optional telemetry must not abort command` passes.
5. Paths outside the scoped auth/storage set are ignored by this mission guard unless the existing review command separately audits them.

## Evidence To Leave For WP05

Record:

- The focused test command for the guard.
- Whether any existing auth/storage suppressions needed reason updates.
- Which scoped cleanup files were handled by WP03 and which WP04-owned files remain for WP04.
- A short description of the accepted reason format.
- Confirmation that failure output includes file and line.

## Boundary Examples

Use these examples to calibrate the implementation:

- A broad catch around optional observability can be acceptable if the reason says observability must not abort the command.
- A broad catch around auth/session parsing is only acceptable if the code converts the failure into a precise auth diagnostic or repair path.
- A broad catch around secure-storage deletion is only acceptable if local cleanup continues safely and the failure is logged or surfaced appropriately.
- A broad catch that hides refresh, token, or storage corruption without a recovery path should fail review even if it has a long comment.

Prefer direct tests over snapshotting the whole review command output. The guard's finding data should be stable even if Rich rendering changes.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-05-05T13:41:33Z – system – Prompt created.
- 2026-05-05T14:05:35Z – codex:gpt-5:python-pedro:implementer – shell_pid=64656 – Started implementation via action command
- 2026-05-05T14:11:51Z – codex:gpt-5:python-pedro:implementer – shell_pid=64656 – Ready for review
- 2026-05-05T14:12:14Z – codex:gpt-5:python-pedro:reviewer – shell_pid=82254 – Started review via action command
- 2026-05-05T14:14:39Z – codex:gpt-5:python-pedro:reviewer – shell_pid=82254 – Review passed: guard helper enforces scoped BLE001 reasons, WP03-owned suppressions are justified, tests and ruff pass
