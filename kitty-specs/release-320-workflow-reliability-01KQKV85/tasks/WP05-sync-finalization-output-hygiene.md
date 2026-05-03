---
work_package_id: WP05
title: Sync Finalization Output Hygiene
dependencies:
- WP01
requirement_refs:
- C-002
- FR-009
- FR-010
- FR-011
- NFR-002
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
phase: Phase 2 - Sync Diagnostics
assignee: ''
agent: "codex:gpt-5.3-codex:python-pedro:implementer"
shell_pid: "83940"
history:
- at: '2026-05-02T08:10:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/**
- tests/sync/**
- tests/contract/test_body_sync.py
role: implementer
tags: []
---

# Work Package Prompt: WP05 – Sync Finalization Output Hygiene

## ⚡ Do This First: Load Agent Profile

Before reading further or changing files, load the assigned agent profile:

```text
/ad-hoc-profile-load python-pedro
```

Use that profile's implementation discipline for the rest of this WP.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` decides the lane workspace path and records the lane branch in `base_branch`.

## Objectives & Success Criteria

Fix #952. After a local state mutation succeeds, final sync failures must be reported as non-fatal diagnostics without corrupting stdout or making local success look like a red command failure.

## Context & Constraints

- Contract: `kitty-specs/release-320-workflow-reliability-01KQKV85/contracts/sync-diagnostics-output.yaml`
- Owned source: `src/specify_cli/sync/**`
- On this computer, command paths that exercise sync behavior must use `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- Tests should mock external services unless a hosted path is explicitly scoped.

## Subtasks & Detailed Guidance

### Subtask T025 – Add strict JSON stdout tests
- **Purpose**: Prove JSON command consumers can parse output when sync warnings happen.
- **Steps**:
  1. Force final-sync failure after local success.
  2. Capture stdout/stderr separately.
  3. Parse stdout with `json.loads` and assert diagnostics do not leak as raw text.
- **Files**: `tests/sync/**`, `tests/contract/test_body_sync.py`.
- **Parallel?**: Yes.

### Subtask T026 – Add sync diagnostic dedupe tests
- **Purpose**: Prevent repeated lock/shutdown messages from overwhelming output.
- **Steps**:
  1. Simulate repeated sync-lock and interpreter-shutdown diagnostics.
  2. Assert one rendered diagnostic per dedupe key per invocation.
  3. Preserve enough detail for remediation.
- **Files**: `tests/sync/**`.
- **Parallel?**: Yes.

### Subtask T027 – Implement non-fatal sync diagnostics
- **Purpose**: Represent final-sync failure separately from local mutation result.
- **Steps**:
  1. Add or reuse a structured diagnostic type/helper in sync modules.
  2. Mark fatality explicitly.
  3. Preserve local success result when local persistence succeeded.
- **Files**: `src/specify_cli/sync/**`.
- **Parallel?**: No.

### Subtask T028 – Route diagnostics correctly
- **Purpose**: Keep command surfaces parseable.
- **Steps**:
  1. For text surfaces, route non-fatal sync diagnostics to stderr.
  2. For JSON surfaces, use stderr or an explicit JSON field allowed by the command contract.
  3. Avoid red failure prefixes for non-fatal sync diagnostics.
- **Files**: `src/specify_cli/sync/**`.
- **Parallel?**: No.

### Subtask T029 – Deduplicate sync diagnostics
- **Purpose**: Keep output actionable.
- **Steps**:
  1. Define a per-invocation dedupe key.
  2. Collapse repeated diagnostics with the same normalized code/phase/message.
  3. Keep tests for repeated lock and shutdown cases.
- **Files**: `src/specify_cli/sync/**`.
- **Parallel?**: No.

### Subtask T030 – Run targeted sync tests
- **Purpose**: Validate behavior without real network dependence.
- **Steps**:
  1. Run targeted sync tests.
  2. Use `SPEC_KITTY_ENABLE_SAAS_SYNC=1` for command paths that intentionally touch sync.
  3. Record commands and results in Activity Log.
- **Files**: sync tests owned by this WP.
- **Parallel?**: No.

## Test Strategy

Run:

```bash
uv run pytest tests/sync tests/contract/test_body_sync.py -q
```

For command paths that intentionally exercise sync:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 <command>
```

## Risks & Mitigations

- **Risk**: Diagnostics get hidden. Keep stderr/JSON diagnostic visibility.
- **Risk**: JSON contracts drift. Validate with actual JSON parsing tests.

## Integration Verification

Before marking this WP complete, verify:
- [ ] Local success remains success after non-fatal final-sync failure.
- [ ] stdout remains parseable for JSON commands.
- [ ] Diagnostics are deduplicated per invocation.

## Review Guidance

Reviewers should inspect stdout/stderr behavior closely and reject any solution that masks local success as command failure.

## Activity Log

**Initial entry**:
- 2026-05-02T08:10:17Z – system – Prompt created.
- 2026-05-03T14:25:15Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Started implementation via action command
- 2026-05-03T14:34:29Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Ready for review: non-fatal final sync diagnostics preserve local success and strict JSON stdout
- 2026-05-03T14:34:58Z – codex:gpt-5.3-codex:reviewer-renata:reviewer – shell_pid=83940 – Started review via action command
- 2026-05-03T14:43:23Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Started implementation via action command
- 2026-05-03T14:52:17Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Ready for review: structured non-fatal final-sync diagnostics cover text local success and targeted sync tests pass
- 2026-05-03T14:52:53Z – codex:gpt-5.3-codex:reviewer-renata:reviewer – shell_pid=83940 – Started review via action command
- 2026-05-03T15:01:43Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Started implementation via action command
- 2026-05-03T15:10:37Z – codex:gpt-5.3-codex:python-pedro:implementer – shell_pid=83940 – Ready for review: clean-output e2e contract updated for structured final-sync diagnostics
