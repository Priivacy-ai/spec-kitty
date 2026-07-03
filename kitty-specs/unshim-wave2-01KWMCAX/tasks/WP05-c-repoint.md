---
work_package_id: WP05
title: 'C-repoint: charter callers + tests'
dependencies: []
requirement_refs:
- FR-005
- FR-006
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
- T013
- T014
- T015
phase: Phase 1 - Sequential DAG
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2787905"
history:
- at: '2026-07-03T17:18:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/charter/lint.py
- src/specify_cli/cli/commands/charter/status.py
- src/specify_cli/charter_runtime/preflight/runner.py
- tests/agent/cli/commands/test_implement_preflight.py
- tests/agent/cli/commands/test_next_preflight.py
- tests/architectural/test_no_shipped_layer_label.py
- tests/charter/test_org_drg_edge_source_urn_preserved.py
- tests/integration/test_charter_synthesize_fresh.py
- tests/integration/test_quickstart_end_to_end.py
- tests/specify_cli/charter_freshness/test_computer.py
- tests/specify_cli/charter_lint/checks/test_contradiction.py
- tests/specify_cli/charter_lint/checks/test_orphan.py
- tests/specify_cli/charter_lint/checks/test_reference_integrity.py
- tests/specify_cli/charter_lint/checks/test_staleness.py
- tests/specify_cli/charter_lint/test_drg_fallback.py
- tests/specify_cli/charter_lint/test_engine.py
- tests/specify_cli/charter_preflight/test_config.py
- tests/specify_cli/charter_preflight/test_performance.py
- tests/specify_cli/charter_preflight/test_runner.py
- tests/specify_cli/cli/commands/charter/test_status_json_safe.py
- tests/specify_cli/cli/commands/test_charter_lint.py
- tests/specify_cli/test_provenance_integration.py
- tests/test_dashboard/test_dashboard_preflight.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – C-repoint: charter callers + tests

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

Spec FR-005 + FR-006 part 1 (IC-04): re-point every charter legacy-namespace consumer to
`specify_cli.charter_runtime.*`: the 4-5 src caller lines — `charter/lint.py:45,93`,
`charter/status.py:55`, and the DEFECT at `charter_runtime/preflight/runner.py:36`
(canonical importing its own legacy shim; also its TYPE_CHECKING sibling at `:41`) —
plus the 20 owned test files (32 charter patch-string sites total; the ledger lists them).
`tests/contract/test_next_no_implicit_success.py` is WP03's (excluded here). Shims are NOT
deleted in this WP (WP06's).

## Subtasks & Detailed Guidance

### Subtask T013 – Src callers (the defect fix first)
- `runner.py:36` (+`:41` TYPE_CHECKING) → `from specify_cli.charter_runtime.freshness import compute_freshness` — import-path-only (C-002). Then lint.py (GraphState, LintEngine) and status.py (compute_freshness).

### Subtask T014 – Test re-points + proofs
- Re-point the plain imports (36 statements across your 18 owned files — the map's 19th file, `tests/contract/test_next_no_implicit_success.py`, is WP03's: its charter refs are handled there, do NOT touch it) and the 30 `charter_lint` + 1 freshness + 1 preflight patch-strings with per-site proofs. **Ledger protocol (FR-002)**: every patch-string site you rewrite gets its proof recorded TWICE: (a) a row in this WP file's Activity Log table `file:line → new target → proof form (assertion file::test | red-first flip) → outcome`, and (b) the orchestrator syncs your table into `occurrence_map.yaml`'s `interception_proof` fields on the planning branch at approval (the lane guard blocks kitty-specs edits on lanes — do NOT edit the map yourself from the lane). A site without a proof row is a review reject; bulk sed is a review reject.
- Patch-target trap: `charter_lint.LintEngine`-style patches must target where the CONSUMER looks the symbol up post-re-point (read each consumer; package `__init__` re-exports exist in charter_runtime).

### Subtask T015 – CI-only shards + gates
- Run locally: `tests/integration/test_quickstart_end_to_end.py`, `tests/agent/cli/commands/test_next_preflight.py`, `test_implement_preflight.py`, `tests/test_dashboard/test_dashboard_preflight.py` (+ any owned contract files); then the charter suites; `grep -rnE "specify_cli\.charter_(lint|freshness|preflight)\b" src/` empty (tests may still reference until WP06 verifies; YOUR owned files must be clean — paste both greps); ruff; mypy. Commit.

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/specify_cli/charter_lint/ tests/specify_cli/charter_freshness/ tests/specify_cli/charter_preflight/ -q 2>/dev/null || true  # paths per map
PWHEADLESS=1 pytest <owned files> -q
python -m mypy src/ 2>&1 | tail -2; ruff check .
```

## Risks & Mitigations
- The lock-gate `test_charter_runtime_shim_paths.py` still pins legacy importability — it stays GREEN in this WP (shims still exist); do NOT touch it (WP06 retires it).
- CI-only shards skipped locally = missed surface (renata's finding) — T015 makes them explicit.

## Review Guidance
- runner.py:36 defect fix present and import-only; sample ≥6 charter ledger rows; the excluded special-case file untouched.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
- 2026-07-03T17:41:03Z – claude:opus:python-pedro:implementer – shell_pid=2754409 – Assigned agent via action command
- 2026-07-03T17:56:44Z – claude:opus:python-pedro:implementer – shell_pid=2754409 – FR-005+FR-006p1: re-pointed 6 src caller lines (incl. runner.py:36/:41 canonical->legacy DEFECT fix + docstring:6) + 20 owned test files to charter_runtime.*. 32 charter patch-string sites re-pointed with per-site proofs in /tmp/wave2-proofs-WP05.yaml (all 5 target classes red-first bogus-flip proven; 7 sample flips FAILED then restored). Gates: 5 CI-only charter shards 32 passed; 153 owned tests passed; shim arch tests 44 passed; diff-scoped ruff exit 0; mypy Success. --force used: rejection cited T016-T018 which are NOT WP05 subtasks (WP05=T013-T015, all done) = known bug #2324. test_next_no_implicit_success.py untouched (WP03). Shims NOT deleted (WP06).
- 2026-07-03T17:57:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=2787905 – Started review via action command
- 2026-07-03T18:06:29Z – user – shell_pid=2787905 – Review passed (--force: gate cited T016-T018 which are WP06's subtasks per tasks.md L26-28/85-87, NOT WP05 — known bug #2324; WP05's own T013-T015 all done). Import-path-only charter re-point (C-002 zero behavior change). 3 SRC callers clean: lint.py GraphState/LintEngine, status.py compute_freshness, runner.py:36/:41 canonical->legacy DEFECT fixed to charter_runtime.freshness. Object-identity proven (shim re-exports SAME 5 symbols). 3 INDEPENDENT red-first flips beyond implementer's 7: test_orphans_flag_passed_to_engine (charter_lint.py:196), test_duration_within_limit (test_engine.py:122), test_returns_built_in_only_when_project_missing (test_drg_fallback.py:71) — each FAILED on bogus target resolving from canonical charter_runtime.* module, PASSED on restore. Residual grep clean in 3 owned src + all owned test files (src-wide hits are docstrings/comments in non-owned shim files, WP06). startswith prefix-filter has teeth (10 real charter_runtime.lint modules). Excluded test_next_no_implicit_success.py untouched; no shim/kitty-specs edits; 23 changed==owned set. Gates: 5 CI shards 32 passed, charter suites 134 passed, shim lock-gate 52 passed (untouched), ruff clean, mypy src/ Success (1058 files).
