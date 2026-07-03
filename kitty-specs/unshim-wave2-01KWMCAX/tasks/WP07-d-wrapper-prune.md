---
work_package_id: WP07
title: 'D: #2326 dead-wrapper prune + honest baseline'
dependencies:
- WP06
requirement_refs:
- FR-008
tracker_refs:
- '#'
- '2'
- '3'
- '2'
- '6'
planning_base_branch: tidy/unshim-wave2
merge_target_branch: tidy/unshim-wave2
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave2 unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
phase: Phase 1 - Sequential DAG
assignee: ''
agent: ''
history:
- at: '2026-07-03T17:18:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/frontmatter.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_baselines.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – D: #2326 dead-wrapper prune + honest baseline

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Spec FR-008 (IC-06): delete the dead `update_field` surface in `frontmatter.py`
(module wrapper `:318-320`, `__all__` entry `:373`, orphaned instance method `:142` —
verify each is truly caller-less first, Wave 1 protocol), drain the
`test_no_dead_symbols.py:235` allowlist row, and set `_baselines.yaml
category_b_grandfathered_legacy` to the HONEST live count (expected 215; re-derive by
counting the live frozenset — Wave 1's honest-216 precedent; NFR-004). Do NOT assume
215: count AFTER WP04/WP06 landed — 215 is only correct if update_field is the sole
newly-dead row; pin whatever the live count IS and document the arithmetic.

## Subtasks & Detailed Guidance

### Subtask T019 – Verify + delete
- Paste the caller-greps for `update_field` (module fn, `__all__`, instance method — the plural `update_fields` twin is LIVE, do not confuse) BEFORE deleting. Delete all three dead pieces.

### Subtask T020 – Atomic drain (C-005)
- Remove the `:235` row; re-derive category_b live count via AST/len and pin the TRUE number (215 only if update_field is the sole newly-dead row — document the arithmetic either way). Do NOT touch the `:517-518` charter_activate rows.

### Subtask T021 – Gates
- `PWHEADLESS=1 pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_ratchet_baselines.py tests/specify_cli/test_frontmatter*.py -q` (locate the frontmatter tests by grep) green; mypy 0; ruff; commit atomically.

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_ratchet_baselines.py -q
grep -rn "update_field\b" src/ | grep -v update_fields || echo CLEAN
```

## Risks & Mitigations
- Deleting the live `update_fields` twin by regex slip — the `\b`-anchored greps above discriminate.

## Review Guidance
- Caller-grep evidence precedes deletion; baseline equals the live count (re-derive yourself); :517-518 untouched.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
