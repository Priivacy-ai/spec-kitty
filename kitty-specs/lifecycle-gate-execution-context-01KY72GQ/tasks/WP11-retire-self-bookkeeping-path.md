---
work_package_id: WP11
title: Retire is_self_bookkeeping_path (IC-07a)
dependencies:
- WP02
- WP09
- WP10
requirement_refs:
- C-010
- FR-009
- NFR-006
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T059
- T060
- T061
- T062
phase: Phase 8 - Exemption Retirements
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/git_probes.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/merge/git_probes.py
- src/specify_cli/cli/commands/agent/mission_record_analysis.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP11 – Retire is_self_bookkeeping_path (IC-07a)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Objectives & Success Criteria

Retire `is_self_bookkeeping_path` and its filename/suffix sets, migrating behaviour to the tool-artifact owner / canonical churn classifier (WP09). Delete this mechanism's registry row (WP10 turns green for it).

**Done** = the symbol is absent from `src/` (owner contract C5, per-symbol); its registry row is deleted; no previously-succeeding operation now fails (C6/C-010).

## Context & Constraints

- Owner contract C5 (registry row #1), C6/C-010 (behaviour-preserving). data-model GA-1 (classify by kind+origin, not filename).
- **Consumers (grep-confirmed on base)**: `merge/git_probes.py`, `review/dirty_classifier.py`, `cli/commands/agent/mission_record_analysis.py`, `acceptance/__init__.py`; declared in `mission_runtime/artifacts.py` (+ `mission_runtime/__init__.py` re-export).
- **Preserve** `git_probes.py:173` behaviour (the tracked-modified `meta.json` case) — route it through the canonical classifier, do not drop the correct handling (this is the WP10 cross-gate RED that must turn green).

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T059 – Retire the symbol

- **Steps**: Remove `is_self_bookkeeping_path` and its filename/suffix sets; repoint the 4 consumers onto the canonical churn classifier / owner.

### Subtask T060 – Delete the registry row

- **Steps**: Delete this mechanism's row in `tests/architectural/test_exemption_registry_ratchet.py` (WP10).

### Subtask T061 – Preserve correct behaviour (C6/C-010)

- **Steps**: Ensure `git_probes.py:173` `meta.json` handling is preserved via the canonical classifier; the WP10 cross-gate agreement test turns green for this leg.

### Subtask T062 – Migrate mechanism tests

- **Steps**: Any test asserting on the *mechanism* migrates to assert on the owner/classifier behaviour.

## Test Strategy

- Run: the WP10 registry + cross-gate suites; `PWHEADLESS=1 uv run --extra test pytest tests/architectural/ tests/merge/ -q`.

## Risks & Mitigations

- Owns `merge/git_probes.py`, `mission_record_analysis.py`. Leeway (serial, owned elsewhere): the symbol **definition** `is_self_bookkeeping_path` + `_SELF_BOOKKEEPING_FILENAMES` live in `mission_runtime/artifacts.py` (`:400`/`:215`) and its re-export in `mission_runtime/__init__.py` — **both owned by WP02**; this WP now depends on **WP02** so those def-site deletions serialize after the seam rebuild (fixes the cross-half `artifacts.py` collision the squad found). Also record leeway on `cli/commands/implement.py` (WP01) and `coordination/commit_router.py` (WP13) — plan B4 attributes them to group (a); if symbol (a) has no consumer there, note that at implement. Other leeway: `acceptance/__init__.py`/`review/dirty_classifier.py` (WP17), the registry row (WP10). Sequential with WP12 (shares 5 files).

## Review Guidance

- Confirm per-symbol absence from `src/`; behaviour preserved (no false block reintroduced).

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
