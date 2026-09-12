---
work_package_id: WP09
title: Tool-Artifact Owner — generalise, enrol subprocess byproducts, adopt in merge executor
dependencies:
- WP08
requirement_refs:
- FR-007
- FR-008
- FR-012
- NFR-002
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T046
- T047
- T048
- T049
- T050
- T051
- T052
phase: 'Phase 6 - Owner: Campsite & Generalization'
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent:
- tests/integration/test_tool_artifact_owner.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/merge/bookkeeping_projection.py
- src/specify_cli/merge/executor.py
- src/specify_cli/coordination/coherence.py
- tests/integration/test_tool_artifact_owner.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – Tool-Artifact Owner

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Generalise `BookkeepingTransaction` from *owner of writes targeting the coordination branch* to *owner of bytes spec-kitty generates, on any surface*: add a non-coord destination, subprocess-byproduct enrolment, and adopt it in the merge executor — **collapsing** the duplicate compensator in `merge/bookkeeping_projection.py`. Establish **one** canonical churn classifier (FR-012).

**Done** = owner contract C2/C3/C4/C6/C7/C10 pass; NFR-002 fork+SIGKILL harness green; `_capture_bookkeeping_snapshots`/`_restore_final_bookkeeping_snapshots` absent (C4b).

## Context & Constraints

- Contract `tool-artifact-owner.md`; data-model `ToolArtifactOwner` (TAO-1..TAO-4), `GeneratedArtifact` (GA-1).
- **Already present** (reuse, don't rebuild): policy pre-flight with stable codes, byte-snapshot `write_artifact`, `stage_path`, `defer_outbound`, `commit_idempotent` (no-op receipt on clean tree), surgical `_rollback` (truncate + restore from byte snapshots, not `git checkout --`).
- **To add**: non-coord destination; subprocess-byproduct enrolment (replace the "detected, warned, abandoned" behaviour); merge-executor adoption.
- **TAO-3 one compensator**: adding a third is a regression. Do NOT open `merge/executor.py` until the owner has a non-coord destination, or the mission maintains three compensators.
- **C4b (negative arm)**: scoped `grep_absence` over `src/specify_cli/merge/` for the named retired symbols — belongs to WP10's registry/C4b oracle; ensure the symbols are actually gone here.
- **NFR-002**: fork+SIGKILL trial harness (≥100 trials, both-outcomes non-vacuity floor, POSIX-gated) in the `tests/integration/test_intake_atomic_writes.py` idiom; commit-spanning paths verified by recovery, not kill-atomicity. Disclosed Windows gap (recovery-only there).

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T046 – Non-coord destination

- **Steps**: Add a non-coord destination to the owner so primary-surface generated writes (e.g. the VCS lock) have an owner. Edit `coordination/transaction.py` under **leeway** (owned by WP08; sequential — this is the enduring generalisation).

### Subtask T047 – Subprocess-byproduct enrolment (C3/TAO-1)

- **Steps**: Enrol bytes created by a spawned child process (e.g. a gate's pytest run); on completion/abort they are committed or reverted like any other write — never detected, warned, and abandoned.

### Subtask T048 – Adopt in executor; collapse projection (C4)

- **Steps**: Adopt the owner in `merge/executor.py`; collapse `merge/bookkeeping_projection.py`, retiring `_capture_bookkeeping_snapshots` and `_restore_final_bookkeeping_snapshots` and their confinement helpers.

### Subtask T049 – One canonical churn classifier (FR-012)

- **Steps**: Establish a single definition of toolchain-generated churn consumed by every gate; adopt in `coordination/coherence.py`. This is the classifier the retirement WPs (WP11–17) migrate their exemptions onto.

### Subtask T050 – NFR-002 harness

- **Steps**: Fork+SIGKILL harness (≥100 trials, both-outcomes floor, POSIX-gated) asserting each enrolled path is byte-identical to pre- or committed post-state; commit-spanning via recovery.

### Subtask T051 – C6/C-010 preserve behaviour

- **Steps**: Preserve behaviour the exemptions got right; no operation that previously succeeded now fails.

### Subtask T052 – C10 size

- **Steps**: Confirm `coordination/transaction.py` ≤ 1000 LOC after the generalisation (WP08 left ~914; three new capabilities fit under 1000).

## Test Strategy

- New: `tests/integration/test_tool_artifact_owner.py` (transactionality, subprocess enrolment, executor adoption).
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/integration/test_tool_artifact_owner.py -q` and `tests/specify_cli/coordination/test_transaction.py`.

## Risks & Mitigations

- Highest-LOC surface. Leeway: `coordination/transaction.py` (owned WP08) + the sibling modules WP08 created — sequential, documented.
- `executor.py`/`coherence.py` are also touched by retirement WPs (WP12/WP13) under leeway — those WPs are downstream on the chain, no concurrency.

## Review Guidance

- Confirm exactly one compensator remains (TAO-3); the projection's snapshot symbols are gone (C4b).
- Confirm the NFR-002 harness has a real both-outcomes floor (non-vacuous).

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
