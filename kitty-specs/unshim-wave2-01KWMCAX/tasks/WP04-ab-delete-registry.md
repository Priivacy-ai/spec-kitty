---
work_package_id: WP04
title: 'A+B delete: next + glossary shims + registry drain'
dependencies:
- WP02
- WP03
requirement_refs:
- FR-003
- FR-004
tracker_refs:
- '#'
- '2'
- '2'
- '9'
- '1'
planning_base_branch: tidy/unshim-wave2
merge_target_branch: tidy/unshim-wave2
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave2 unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
phase: Phase 1 - Sequential DAG
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2926956"
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
- src/specify_cli/next/
- src/specify_cli/glossary/
- tests/glossary/test_legacy_import_shim.py
- tests/runtime/next/test_import_paths.py
- docs/migrations/shim-registry.yaml
- tests/architectural/test_shim_registry_schema.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – A+B delete: next + glossary shims + registry drain

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

Spec FR-003 + FR-004 (IC-03): with every reference re-pointed (WP01-03 approved), delete
`src/specify_cli/next/` and `src/specify_cli/glossary/` and drain the governance spine
ATOMICALLY (C-005): both `docs/migrations/shim-registry.yaml` rows out AND the
`test_shim_registry_schema.py:44-45` presence-assertions edited in the SAME commit
(the test hard-asserts both rows present — removing a row without the test edit reds).
`tests/glossary/test_legacy_import_shim.py` deletes with the husk (it tests the shim
itself — record as intentionally-removed in the log, judge-the-test framework).

## Subtasks & Detailed Guidance

### Subtask T010 – Deletions
- Pre-check (C-001): `grep -rnE "(from|import)\s+specify_cli\.(next|glossary)\b|patch(\.dict)?\(\s*[\"']?(sys\.modules[\"',\s{]*[\"'])?specify_cli\.(next|glossary)|setattr\(|ModuleType\(" src/ tests/ | grep "specify_cli\.\(next\|glossary\)"` MUST be empty before any `git rm` — paste the empty output FIRST (imports AND patch/setattr/ModuleType string residue; a plain import-only grep passes while a straggler patch-string still resolves through the shim). Then `git rm -r src/specify_cli/next src/specify_cli/glossary` + `git rm tests/glossary/test_legacy_import_shim.py`.

### Subtask T011 – Spine drain (same commit)
- Remove both rows from `shim-registry.yaml`; convert `test_shim_registry_schema.py:44-45` per the refactor-stable doctrine — the presence-asserts become absence/registry-empty assertions or the test re-shapes to schema-only (justify per the convert-or-delete framework; do NOT simply delete the schema test).

### Subtask T012 – Gates + smoke
- `python -c "import specify_cli.next"` and `"import specify_cli.glossary"` both `ModuleNotFoundError` (paste); `spec-kitty next --help` exit 0; `PWHEADLESS=1 pytest tests/architectural/test_shim_registry_schema.py tests/architectural/test_unregistered_shim_scanner.py tests/architectural/ -q` green; whole-tree mypy 0; ruff; NFR-002 grep for next+glossary empty. Commit (single atomic commit for T010+T011).

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/next/ tests/glossary/ -q
```

## Risks & Mitigations
- Deletion with any straggler reference = ModuleNotFoundError storm → the T010 pre-check gate is mandatory-first.
- Registry drain without the same-commit schema-test edit = red tip (C-005/C-006).

## Review Guidance
- Verify T010's empty-grep evidence PRECEDES the deletion in the log; the schema-test conversion is principled (not deleted); single atomic commit.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
- 2026-07-03T18:35:02Z – claude:opus:python-pedro:implementer – shell_pid=2885747 – Assigned agent via action command
- 2026-07-03T18:38:39Z – claude:opus:python-pedro:implementer – shell_pid=2885747 – T010 pre-check BLOCKED (STOP per protocol): resolving-residue found outside allowed sites. tests/runtime/next/test_import_paths.py:27 (test_legacy_next_package_import_warns_and_aliases_submodules) dynamically imports 'specify_cli.next.runtime_bridge' via importlib.import_module and asserts DeprecationWarning + aliasing to runtime.next.runtime_bridge. This is a shim-BEHAVIOR test (analogous to the glossary shim test in my owned_files) that will red with ModuleNotFoundError once src/specify_cli/next/ is deleted. It is NOT in WP04 owned_files and NOT owned by any WP (WP02 owns tests/next/, not tests/runtime/next/; WP03 list excludes it) — a spec/plan ownership gap. Did NOT delete anything. Needs: either the legacy sub-test removed/re-pointed (WP02/WP03 territory) or test_import_paths.py added to WP04 owned_files. All other next/glossary refs are non-breaking guards/comments (session_presence guards, test_layer_rules forbidden_prefixes, _baselines/test_no_dead_symbols comments, schema.py:22 WP09 comment).
- 2026-07-03T18:53:16Z – claude:opus:python-pedro:implementer – shell_pid=2885747 – WP04 complete: T010 pre-check initially found ONE resolving straggler (tests/runtime/next/test_import_paths.py:27 importlib legacy-alias test) -> STOPPED; coordinator added the file to owned_files + occurrence-map exception. Re-run pre-check clean (only non-resolving negative guards/comments remain: session_presence guards, test_layer_rules forbidden_prefixes, _baselines/_no_dead_symbols comments, schema.py:22 WP09 comment). Atomic commit 6cf0d4e99 (C-005): deleted src/specify_cli/next/ + src/specify_cli/glossary/ + tests/glossary/test_legacy_import_shim.py; legacy alias sub-test converted to absence pin; shim-registry.yaml drained to shims: []; schema-test presence-asserts converted to refactor-stable absence pins. Gates: import specify_cli.next -> ModuleNotFoundError (next-GONE); import specify_cli.glossary -> ModuleNotFoundError (glossary-GONE); spec-kitty next --help exit 0; registry schema+scanner 44 passed; tests/next+specify_cli/next+runtime/next+glossary 887 passed; tests/architectural/ 641 passed 4 skipped; ruff clean; mypy Success 1056 files. All with PYTHONPATH pinned to lane worktree (verified specify_cli.__file__).
- 2026-07-03T18:54:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=2926956 – Started review via action command
- 2026-07-03T19:05:57Z – user – shell_pid=2926956 – Review passed: atomic commit 6cf0d4e99 (6 files, +27/-187) deletes specify_cli.next + specify_cli.glossary trees + glossary shim-test, drains shim-registry.yaml to shims:[], converts schema-test to absence pin (test_drained_glossary_and_runtime_shims_stay_out_of_registry) and import_paths.py legacy sub-test to absence pin (test_legacy_specify_cli_next_shim_is_gone) in the SAME commit (C-005). Verified: both imports ModuleNotFoundError, ls empty, next --help exit 0. Flip-check schema pin: RED on re-added row, green on revert. Flip-check import pin: RED with stub next/__init__.py, green removed. canonical test_runtime_next_is_canonical_decision_home unchanged. At-scale: tests/next+specify_cli/next+runtime/next 717 passed; tests/architectural 641 passed 4 skipped. Residual import grep empty (only a negative-guard assertion string matches). _baselines/no_dead_symbols untouched (WP07 spine). ruff clean, mypy 1056 files Success. Only non-merge commit touching owned files is 6cf0d4e99 (no fixups).
