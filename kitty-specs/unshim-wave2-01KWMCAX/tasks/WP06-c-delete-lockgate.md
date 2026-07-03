---
work_package_id: WP06
title: 'C-delete: charter shim packages + lock-gate retirement'
dependencies:
- WP05
requirement_refs:
- FR-006
- FR-007
tracker_refs:
- '#'
- '2'
- '2'
- '9'
- '0'
planning_base_branch: tidy/unshim-wave2
merge_target_branch: tidy/unshim-wave2
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave2 unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
phase: Phase 1 - Sequential DAG
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2849766"
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
- src/specify_cli/charter_lint/
- src/specify_cli/charter_freshness/
- src/specify_cli/charter_preflight/
- tests/architectural/test_charter_runtime_shim_paths.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – C-delete: charter shim packages + lock-gate retirement

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

Spec FR-006 part 2 + FR-007 (IC-05): delete the 3 charter shim packages; retire the
6-test lock-gate with a per-test disposition table; record the charter_activate
documented-canonical adjudication. NO registry work (charter shims were never
registered; full-delete means no rows to drain). The `test_no_dead_symbols.py:517-518`
charter_activate rows STAY (touching them is a review reject).

## Subtasks & Detailed Guidance

### Subtask T016 – Deletions (pre-check first)
- `grep -rnE "(from|import|patch.*)specify_cli\.charter_(lint|freshness|preflight)\b" src/ tests/ | grep -v test_charter_runtime_shim_paths` MUST be empty — paste, THEN `git rm -r` the 3 packages.

### Subtask T017 – Lock-gate retirement with the disposition table
- `test_charter_runtime_shim_paths.py` (6 tests): produce the per-test disposition table in the Activity Log — each row maps the retired test to its replacement `file::test` exercising the equivalent canonical behavior, or records intentionally-removed (legacy importability is deleted BY DESIGN). `test_canonical_paths_import` RE-HOMES (it pins canonical imports — move it into an existing canonical-path arch/test file or keep the file reduced to it with a renamed module docstring; justify your choice). Then delete/reshape the file accordingly (C-006 convert-or-delete, never silent drop).

### Subtask T018 – charter_activate record + gates
- Record the documented-canonical adjudication (spec census evidence) in the Activity Log + a one-line code comment is NOT needed (C-002 — no live-code edits); the mission artifacts + #2290 closeout comment (WP09) carry it.
- Gates: `PWHEADLESS=1 pytest tests/architectural/ -q` green; the 5 CI-only shards + charter suites green; NFR-002 charter grep empty in src/ AND tests/ (paste); mypy 0; ruff. Commit atomically.

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
python -c "import specify_cli.charter_lint" 2>&1 | grep -q ModuleNotFoundError && echo lint-GONE
```

## Risks & Mitigations
- Hand-waved disposition table = review reject (renata's fold; 6 explicit rows required).
- The :517-518 rows and `charter_activate.py` itself are NO-TOUCH.

## Review Guidance
- The 6-row disposition table is the headline; spot-verify 2 replacement tests actually exercise the claimed behavior; verify :517-518 untouched.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
- 2026-07-03T18:08:11Z – claude:opus:python-pedro:implementer – shell_pid=2813357 – Assigned agent via action command
- 2026-07-03T18:21:32Z – claude:opus:python-pedro:implementer – shell_pid=2813357 – Bug #2324: move-task cited T019-T021 which belong to another WP (not WP06). WP06's own subtasks T016-T018 are all done. Deleted 3 charter shim packages; pre-check clean (only functional residue = WP03-owned test_next_no_implicit_success.py:38/46/49, lands via DAG). Retired lock-gate; 6-row disposition table + re-homed test_canonical_paths_import in tests/architectural/test_charter_runtime_canonical_paths.py. C-005: no charter rows in shim-registry.yaml. charter_activate.py NO-TOUCH (C-002). Gates: arch 637 passed, mypy Success, ruff clean, 3x ModuleNotFoundError confirmed.
- 2026-07-03T18:22:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=2849766 – Started review via action command
- 2026-07-03T18:35:22Z – user – shell_pid=2849766 – Review passed (--force solely for bug #2324: gate cited T019-T021 which belong to another WP; WP06's own subtasks T016-T018 are done). Evidence: 3 charter shim packages deleted (ModuleNotFoundError verified for all 3 with worktree PYTHONPATH); 6-row disposition table verified against reality (row 3: test_next_preflight.py/test_implement_preflight.py patch charter_runtime.preflight.hook confirmed; row 4: test_engine.py imports charter_runtime.lint.engine confirmed); test_legacy_charter_paths_are_gone flip-checked RED with stub charter_lint, GREEN after removal; charter_activate.py + test_no_dead_symbols.py:517-518 untouched (git log empty over lane range); no charter rows in shim-registry.yaml; only functional residual = WP03-owned test_next_no_implicit_success.py (exactly 4 errors, all ModuleNotFoundError charter_preflight); arch suite 637 passed/4 skipped; ruff+mypy clean; charter lint/status --help OK
