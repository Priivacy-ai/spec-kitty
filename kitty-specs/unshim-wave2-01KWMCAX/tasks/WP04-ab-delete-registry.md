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
- src/specify_cli/next/
- src/specify_cli/glossary/
- tests/glossary/test_legacy_import_shim.py
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
