---
work_package_id: WP04
title: Local Session Hot Path And Cross-Process Coordination
dependencies:
- WP02
- WP03
requirement_refs:
- C-001
- C-002
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-003
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
phase: Phase 2 - Local Session Hot Path
assignee: ''
agent: "codex:gpt-5:python-pedro:reviewer"
shell_pid: "21012"
history:
- at: '2026-05-05T13:41:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/auth/session_hot_path.py
- src/specify_cli/auth/token_manager.py
- src/specify_cli/auth/refresh_transaction.py
- src/specify_cli/auth/session.py
- src/specify_cli/auth/secure_storage/file_fallback.py
- tests/auth/concurrency/test_session_hot_path.py
- tests/auth/stress/test_file_storage_concurrent.py
- tests/auth/secure_storage/test_file_fallback_windows_root.py
- tests/packaging/test_windows_no_keyring.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 - Local Session Hot Path And Cross-Process Coordination

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Reduce repeated expensive local session work for many short-lived CLI processes while preserving encrypted file-only storage as the durable root of trust. Any local handoff/cache must be derived, bounded, invalidatable, and safe to bypass.

Implementation command: `spec-kitty agent action implement WP04 --agent <name>`

## Dependencies

Depends on WP02 and WP03. Do not start this WP until refresh-lock test isolation is clear and the BLE001 guardrail exists, because this WP edits auth concurrency/storage files that must satisfy the new guard.

## Context & Constraints

Read:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/session-hot-path.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/data-model.md`

Do not introduce Keychain, keyring, Secret Service, or OS credential-manager dependencies. Do not print raw tokens. Default plan assumes no plaintext token cache. If implementation discovers a safer minimal design that avoids token caching entirely, prefer it.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` decides the lane workspace path and records the lane branch in `base_branch`.

## Subtasks & Detailed Guidance

### Subtask T015 - Measure baseline repeated durable-session operations

- **Purpose**: Ground the hot-path change in observed work and prove the final behavior improves the repeated durable-session operation count.
- **Steps**:
  1. Inspect `TokenManager`, `refresh_transaction`, and secure storage reads.
  2. Add a deterministic baseline fixture that counts repeated durable-session operations in a representative many-short-lived-process scenario.
  3. Record the baseline count in the test name, assertion comment, or implementation note.
  4. Make the post-change assertion prove fewer repeated durable-session operations than that baseline.
- **Files**: owned auth files and tests.
- **Parallel?**: Starts after WP02.
- **Notes**: This measurement is mandatory. Do not land this WP with only a narrative claim that work was reduced.

### Subtask T016 - Design and implement a bounded local handoff/cache helper

- **Purpose**: Add the smallest helper that reduces repeated work safely.
- **Steps**:
  1. Create `src/specify_cli/auth/session_hot_path.py` if a new helper is needed.
  2. Keep handoff state derived from durable encrypted storage.
  3. Include freshness/invalidation checks tied to durable state identity or mtime/content metadata.
  4. Make missing/stale/unreadable handoff a normal fallback.
- **Files**: `session_hot_path.py`, possibly `session.py` or `file_fallback.py`.
- **Parallel?**: No; follows T015.
- **Notes**: Avoid storing raw token material in a plaintext handoff artifact.

### Subtask T017 - Integrate fallback with durable encrypted storage

- **Purpose**: Preserve the storage trust model.
- **Steps**:
  1. Integrate the helper at a narrow call site in auth/session loading.
  2. Ensure durable encrypted storage remains authoritative for writes and invalidation.
  3. Ensure logout/clear-session behavior invalidates any handoff state.
- **Files**: `token_manager.py`, `session.py`, `file_fallback.py`, `session_hot_path.py`.
- **Parallel?**: No; follows T016.
- **Notes**: Keep public auth APIs stable unless a small additive helper is necessary.

### Subtask T018 - Preserve refresh coordination and benign replay handling

- **Purpose**: Avoid regressing shipped concurrency behavior.
- **Steps**:
  1. Inspect existing machine-wide refresh lock behavior.
  2. Ensure hot-path use does not bypass lock coordination.
  3. Add coverage for stale handoff plus refresh peer convergence if needed.
- **Files**: `refresh_transaction.py`, auth concurrency tests.
- **Parallel?**: No; follows T017.
- **Notes**: Do not treat benign replay or lock contention as fatal user errors.

### Subtask T019 - Add hot-path, secure-storage, and packaging regression coverage

- **Purpose**: Prove both performance intent and security constraints.
- **Steps**:
  1. Add `tests/auth/concurrency/test_session_hot_path.py`.
  2. Extend secure-storage/stress tests as needed for invalidation/fallback.
  3. Preserve `tests/packaging/test_windows_no_keyring.py` and extend only if needed.
  4. Run the WP03 guard against auth files touched by this WP.
  5. Run focused auth concurrency/stress/secure-storage/packaging tests.
- **Files**: owned test files.
- **Parallel?**: No; final verification.
- **Notes**: Tests should assert no forbidden credential-manager dependency.

## Test Strategy

```bash
uv run pytest \
  tests/auth/concurrency/test_session_hot_path.py \
  tests/auth/stress/test_file_storage_concurrent.py \
  tests/auth/secure_storage/test_file_fallback_windows_root.py \
  tests/packaging/test_windows_no_keyring.py
```

Run broader auth concurrency tests if `refresh_transaction.py` or `token_manager.py` behavior changes:

```bash
uv run pytest tests/auth/concurrency
```

Also run the WP03 guard or the focused guard test command after auth edits so new or preserved suppressions in WP04-owned auth files satisfy the guard contract.

## Definition of Done

- Many short-lived process coverage records a baseline and demonstrates fewer repeated durable-session operations than that baseline.
- Stale/missing handoff falls back to encrypted durable storage.
- Refresh coordination remains single-flight or equivalent.
- No forbidden credential-manager dependency is introduced.
- The WP03 BLE001 guard passes for auth files touched by this WP.

## Risks & Mitigations

- **Risk**: Weakening storage security for speed. **Mitigation**: derived handoff only, durable encrypted storage authoritative.
- **Risk**: Broad auth refactor. **Mitigation**: keep integration narrow and test through existing auth APIs.

## Review Guidance

Reviewers should focus on the trust boundary: no plaintext token leakage, no new credential-manager dependency, and no bypass of refresh locks.

## Integration Verification

Before moving this WP to `for_review`, verify:

- [ ] A representative many-process test records a baseline durable-session operation count.
- [ ] The final representative many-process test proves fewer repeated durable-session operations than the baseline.
- [ ] The hot path falls back to encrypted file-only storage when handoff state is missing.
- [ ] The hot path falls back to encrypted file-only storage when handoff state is stale or invalid.
- [ ] Logout or local session clear invalidates any handoff/cache state.
- [ ] Refresh coordination still uses the existing lock or an equivalent tested boundary.
- [ ] No raw token material appears in stdout, stderr, logs, or assertion failure messages.
- [ ] Packaging checks still prove `keyring` and OS credential-manager dependencies are absent.
- [ ] The WP03 BLE001 guard passes after this WP's auth edits.

## Out Of Scope

- Do not replace encrypted file-only durable storage.
- Do not introduce macOS Keychain, Python `keyring`, Linux Secret Service, or a Windows credential-manager dependency.
- Do not add SaaS server changes.
- Do not redesign OAuth refresh replay handling except where needed to preserve existing behavior under the hot path.

## Implementation Handoff Notes

Start with mandatory characterization. If the current code already avoids repeated expensive work after WP02, the representative baseline should prove that; otherwise implement the smallest coordination guard that creates a measurable reduction. Avoid a large daemon or background process unless the baseline proves a simple derived handoff cannot satisfy the requirement.

Leave a short note for WP05 explaining what work was reduced and which fallback path proves durable storage remains authoritative.
Include enough measurement context that reviewers can distinguish a real hot-path improvement from a cosmetic refactor.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-05-05T13:41:33Z – system – Prompt created.
- 2026-05-05T14:15:49Z – codex:gpt-5:python-pedro:implementer – shell_pid=84555 – Started implementation via action command
- 2026-05-05T14:27:05Z – codex:gpt-5:python-pedro:implementer – shell_pid=84555 – Ready for review: local hot path reduces representative 8-process auth checks from 8 encrypted durable reads to 0; missing/stale handoff falls back to encrypted storage; refresh single-flight remains covered.
- 2026-05-05T14:28:37Z – codex:gpt-5:python-pedro:reviewer – shell_pid=96230 – Started review via action command
- 2026-05-05T14:42:16Z – codex:gpt-5:python-pedro:reviewer – shell_pid=96230 – Moved to planned
- 2026-05-05T14:42:32Z – codex:gpt-5:python-pedro:implementer – shell_pid=99643 – Started implementation via action command
- 2026-05-05T14:52:44Z – codex:gpt-5:python-pedro:implementer – shell_pid=99643 – WP04 review fixes committed: stale summary durable auth result and fingerprint OSError miss handling.
- 2026-05-05T14:53:54Z – codex:gpt-5:python-pedro:reviewer – shell_pid=7288 – Started review via action command
- 2026-05-05T14:59:38Z – codex:gpt-5:python-pedro:reviewer – shell_pid=7288 – Moved to planned
- 2026-05-05T15:01:26Z – codex:gpt-5:python-pedro:implementer – shell_pid=8897 – Started implementation via action command
- 2026-05-05T15:10:52Z – codex:gpt-5:python-pedro:implementer – shell_pid=8897 – Ready for review: auth concurrency refresh fixtures are hermetic and broader concurrency suite passes.
- 2026-05-05T15:11:51Z – codex:gpt-5:python-pedro:reviewer – shell_pid=12682 – Started review via action command
- 2026-05-05T15:15:09Z – codex:gpt-5:python-pedro:reviewer – shell_pid=12682 – Review passed: concurrency suite 22 passed; hot-path matrix 12 passed/2 skipped; BLE001 guard 5 passed; fixtures fail fast on hosted /api/v1/me
- 2026-05-05T15:37:36Z – codex:gpt-5:python-pedro:reviewer – shell_pid=12682 – Moved to planned
- 2026-05-05T15:37:59Z – codex:gpt-5:python-pedro:implementer – shell_pid=19520 – Started implementation via action command
- 2026-05-05T15:39:53Z – codex:gpt-5:python-pedro:implementer – shell_pid=19520 – Ready for review: non-file storage bypasses hot path; FR-011 slice 146 passed; WP04 slice 30 passed, 2 skipped
- 2026-05-05T15:40:10Z – codex:gpt-5:python-pedro:reviewer – shell_pid=21012 – Started review via action command
- 2026-05-05T15:43:30Z – codex:gpt-5:python-pedro:reviewer – shell_pid=21012 – Review passed: 306bc815 bypasses non-path storage; FR-011 146 passed; WP04 focused 13 passed/2 skipped; auth concurrency 23 passed; BLE001 guard 5 passed and 0 findings
