---
work_package_id: WP01
title: Retire charter.generator (dead WP03 wrapper)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-002
- C-003
tracker_refs:
- '#1797'
planning_base_branch: feat/charter-deadcode-noop-campsite
merge_target_branch: feat/charter-deadcode-noop-campsite
branch_strategy: Planning artifacts for this mission were generated on feat/charter-deadcode-noop-campsite. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-deadcode-noop-campsite unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/generator.py
- src/charter/__init__.py
- tests/charter/test_generator.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1542680"
shell_pid_created_at: "1784428988.57"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile via `/ad-hoc-profile-load python-pedro`
(implementer). Load the YAML — do not act on the persona name alone.

## Objective

Delete the confirmed-dead `charter.generator` module (`CharterDraft`, `build_charter_draft`,
`write_charter`) — a WP03 wrapper over `compile_charter` superseded by the `charter interview` +
`charter generate` flow — and remove its package reexport. Pure removal, no behavior change.

**Authoritative grounding** (read first): [`research.md` §1](../research.md),
[`data-model.md` LM-3/LM-4](../data-model.md).

## Context / grounding (verified at `main@4c93a0f58`)

- `src/charter/generator.py:12-73` — `__all__` (12-16), `CharterDraft` (20-31), `build_charter_draft`
  (34-59), `write_charter` (62-73). **Zero live `src/` callers.**
- `src/charter/__init__.py:31` — `from .generator import CharterDraft, build_charter_draft, write_charter`;
  `__all__` entries at lines 108-110.
- `tests/charter/test_generator.py:10` — the ONLY test import of the generator symbols.

## Subtasks

### T001 — Delete `src/charter/generator.py`
Remove the module entirely.

### T002 — De-reexport in `src/charter/__init__.py`
Remove the `from .generator import …` import (line 31) and the three `__all__` entries
(`"CharterDraft"`, `"build_charter_draft"`, `"write_charter"`, lines 108-110). Nothing else in
`__init__.py` references generator. **C-007:** deleting a module requires removing its `__all__`
entries in the same change.

### T003 — Surgically retire the dead-API tests (LM-3 — do NOT delete the file)
`tests/charter/test_generator.py` hosts BOTH dead-API tests and LIVE compiler tests. Remove ONLY:
- the `from charter.generator import build_charter_draft, write_charter` line (10), and
- the 4 generator-API tests: `test_build_charter_draft_defaults`,
  `test_build_charter_draft_invalid_template_set_raises`, `test_write_charter_respects_force`,
  `test_write_charter_rejects_symlink_even_with_force`.

**KEEP** (they import `charter.compiler.write_compiled_charter`, not generator — live coverage, C-003):
`test_write_compiled_charter_ignores_stale_symlinked_charter_md`,
`test_write_compiled_charter_rejects_symlinked_output_dir`,
`test_write_compiled_charter_rejects_symlinked_output_dir_without_repo_root`,
`test_write_compiled_charter_rejects_output_dir_that_resolves_outside_repo`.
Keep the `from charter.compiler import CompiledCharter, write_compiled_charter` and
`from charter.catalog import load_doctrine_catalog` imports (lines 8-9).

### T004 — Verify
- `git grep -nE "generator|build_charter_draft|CharterDraft|\bwrite_charter\b" -- src/charter` →
  zero live references (excluding removed lines).
- `pytest tests/charter/test_generator.py tests/architectural/test_no_dead_modules.py -q` → green
  (generator was NOT allowlisted, so no baseline edit is needed for it — unlike WP02's extractor).
- `ruff check src/charter/__init__.py tests/charter/test_generator.py` and
  `mypy --strict src/charter/__init__.py` → clean.

## Definition of Done
- `src/charter/generator.py` deleted; `__init__.py` reexport gone; the 4 compiler tests survive and
  pass; zero live refs; gates + ruff + mypy green. Net LOC negative.

## Landmines
- **LM-3**: never delete `test_generator.py` wholesale — surgical edit only.
- **LM-4**: removing `build_charter_draft` leaves NO `charter.md` scaffold gap (confirmed research §1);
  if you think you found one, surface it — do not reintroduce a writer.

## Reviewer guidance
Confirm the 4 `write_compiled_charter` tests still present + passing; confirm no `charter.md`
initial-scaffold path was silently dropped; confirm `git grep` is clean.

## Activity Log

- 2026-07-19T02:37:33Z – claude:sonnet:python-pedro:implementer – shell_pid=1508118 – Assigned agent via action command
- 2026-07-19T02:42:12Z – claude:sonnet:python-pedro:implementer – shell_pid=1508118 – generator retired; 4 compiler tests preserved; gates green
- 2026-07-19T02:43:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=1542680 – Started review via action command
