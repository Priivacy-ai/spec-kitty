---
work_package_id: WP01
title: Golden CLI characterization harness
dependencies: []
requirement_refs:
- FR-001
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: tests/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_merge_cli_golden.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/cli/commands/test_merge_cli_golden.py
role: implementer
tags: []
task_type: implement
shell_pid: "2997190"
---

# Work Package Prompt: WP01 – Golden CLI characterization harness

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Capture the `spec-kitty merge` byte-identity contract against the PRE-refactor module via Typer `CliRunner` on the fully registered app. This is the byte-identity proof for the entire mission and MUST be authored first (C-005).

- Requirement refs: FR-001.

## Context & Constraints

- Plan IC-01. Contract: contracts/cli-surface-contract.md. The existing suite only invokes `--abort` via CliRunner — this WP closes the CLI-surface coverage gap (research §5).
- Strictly-linear chain: this WP depends only on nothing (chain head).
- Ownership: this WP owns ONLY `tests/specify_cli/cli/commands/test_merge_cli_golden.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T001 – Author the golden test
- **Steps**: Create `tests/specify_cli/cli/commands/test_merge_cli_golden.py`. Invoke through the fully registered app object (import the real Typer app that registers `merge` at `cli/commands/__init__.py:216`) — NOT a re-wrapped command.

### Subtask T002 – Snapshot help + flags
- **Steps**: Snapshot `merge --help` output and assert every flag/default from contracts/cli-surface-contract.md, including the **hidden** `--feature` alias and the unused compat flags `--context`/`--keep-workspace`.

### Subtask T003 – Pin the --json gate
- **Steps**: Assert `merge --json` (without `--dry-run`) prints the exact error `--json is currently supported with --dry-run only.` and exits 1.

### Subtask T004 – Pin dry-run JSON + error paths
- **Steps**: [P] Assert the `--dry-run --json` payload key set exactly; pin `--resume` no-op (exit 1), unresolved-slug (exit 1), and the `REJECTED_REVIEW_ARTIFACT_CONFLICT` emission.

### Subtask T005 – Record baseline
- **Steps**: Run the test against the pre-refactor module; confirm green. This is the frozen baseline re-asserted by every later WP.

## Definition of Done

- Golden test passes on the current (pre-refactor) module.
- Help, all flags, dry-run JSON key set, and headline error/exit-code paths are pinned.
- No source module changed (test-only WP).

## Risks & Mitigations

- Re-wrapping the command instead of the registered app → invoke via the real app object so registration is pinned.

## Reviewer Guidance

- Confirm the test drives the registered app, not a hand-built Typer wrapper.
- Confirm the dry-run JSON key set matches contracts/cli-surface-contract.md exactly.

## Activity Log

- 2026-06-24T20:25:24Z – claude:opus:randy-reducer:implementer – shell_pid=2962436 – Assigned agent via action command
- 2026-06-24T20:32:33Z – claude:opus:randy-reducer:implementer – shell_pid=2962436 – Golden CLI characterization harness: 8 tests green on pre-refactor module; pins help/flags, --json gate, dry-run JSON key set, error/exit paths, REJECTED_REVIEW_ARTIFACT_CONFLICT. ruff+mypy clean.
- 2026-06-24T20:32:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=2997190 – Started review via action command
- 2026-06-24T20:33:25Z – user – shell_pid=2997190 – Review passed: 8 golden tests green on pre-refactor module; drives the real registered merge command; dry-run JSON key set matches contract; help/flags/error paths pinned; test-only diff; ruff+mypy clean.
