---
work_package_id: WP12
title: Retire is_coordination_artifact_residue_path (IC-07b)
dependencies:
- WP11
requirement_refs:
- C-010
- FR-009
- NFR-006
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T063
- T064
- T065
- T066
phase: Phase 8 - Exemption Retirements
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/auto_rebase.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/lanes/auto_rebase.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP12 – Retire is_coordination_artifact_residue_path (IC-07b)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Objectives & Success Criteria

Retire `is_coordination_artifact_residue_path` (**8 consumer files** — grep confirms real call-sites incl. `commit_router.py:468`, `merge/executor.py:906`, `implement.py:734`; re-count at implement), migrating behaviour to the owner. Delete its registry row.

**Done** = the symbol is absent from `src/`; `lanes/auto_rebase.py`'s correct abort-on-unrecognised-dirt behaviour is preserved via the owner (C6/C-010).

## Context & Constraints

- Owner contract C5 (registry row #2), C6/C-010.
- **Consumers (grep-confirmed)**: `merge/executor.py`, `merge/git_probes.py`, `coordination/commit_router.py`, `cli/commands/implement.py`, `cli/commands/implement_cores.py`, `cli/commands/agent/mission_record_analysis.py`, `acceptance/__init__.py`, `lanes/auto_rebase.py`; declared in `mission_runtime/artifacts.py`.
- **`lanes/auto_rebase.py` aborts a rebase on unrecognised dirt** — this is correct behaviour and must be preserved through the owner/classifier (C-010). Losing it silently corrupts a rebase.
- **Plan ownership-table gap (surfaced during tasking)**: (b) also lives in `implement.py`/`implement_cores.py`, which the plan's table attributed only to (a)/(c)/(d). The a→b→c→d chain serializes these; edit them under leeway.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T063 – Retire the symbol

- **Steps**: Remove `is_coordination_artifact_residue_path`; repoint the 7 consumers onto the owner/canonical classifier.

### Subtask T064 – Preserve auto_rebase abort-on-dirt (C-010)

- **Steps**: `lanes/auto_rebase.py` must still abort a rebase on genuinely unrecognised dirt, now via the owner/classifier's judgement.

### Subtask T065 – Delete the registry row

- **Steps**: Delete this mechanism's row in the WP10 registry.

### Subtask T066 – Migrate mechanism tests

- **Steps**: Migrate mechanism-asserting tests to the owner/classifier.

## Test Strategy

- Run: `PWHEADLESS=1 uv run --extra test pytest tests/architectural/ tests/merge/ tests/specify_cli/lanes/ -q`.

## Risks & Mitigations

- Owns `lanes/auto_rebase.py` only; all other sites are leeway serialized by the a→b→c→d chain: `executor.py` (WP09), `git_probes.py`/`mission_record_analysis.py` (WP11), `commit_router.py` (WP13), `implement.py` (WP01), `implement_cores.py` (WP14), `acceptance/__init__.py` (WP17), `artifacts.py` (WP02).

## Review Guidance

- Confirm the auto_rebase abort-on-dirt behaviour is preserved (the highest-risk regression here).

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
