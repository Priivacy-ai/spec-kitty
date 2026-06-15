---
work_package_id: WP05
title: Retire dead hidden_feature_option helper + reconcile legacy-alias tests
dependencies:
- WP02
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: mission/codebase-sanitization-1060-1622
merge_target_branch: mission/codebase-sanitization-1060-1622
branch_strategy: Planning artifacts for this mission were generated on mission/codebase-sanitization-1060-1622. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/codebase-sanitization-1060-1622 unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
phase: Phase 2 - Regression lock
assignee: ''
agent: claude
shell_pid: '315738'
history:
- at: '2026-06-15T12:04:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (adversarial-squad fold-in F1)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/_legacy_aliases.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/missions/_legacy_aliases.py
- tests/integration/test_legacy_feature_alias.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/test_no_dead_modules.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Retire dead `hidden_feature_option` helper + reconcile legacy-alias tests

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Boyscout dead-code removal in the same surface (epic #1797). `hidden_feature_option()`
and `LEGACY_FEATURE_HELP` in `_legacy_aliases.py` have **zero `src/` callers**
(commands declare `--feature` inline) — they are kept alive only by their own
tests and a dead-symbol allowlist carrying a `TODO(triage)`. Remove them.

**Done when:**
- `hidden_feature_option` + `LEGACY_FEATURE_HELP` are gone; `_legacy_aliases.py`
  is either deleted or reduced to a docstring-only stub (whichever leaves imports
  valid).
- The tests that exercised them are retired with a rationale (C-001).
- The `test_no_dead_symbols` / `test_no_dead_modules` allowlist entries for these
  symbols are removed and those gates stay green.
- `resolve_selector` (in `selector_resolution.py`) is UNTOUCHED (FR-008).

## Context & Constraints

- Spec FR-009 (and FR-008 reword). Surfaced by the adversarial squad (fold-in F1).
- **Depends on WP02** — `tests/integration/test_legacy_feature_alias.py` also
  asserts `charter/lint.py` keeps a `--feature` block (L91-96); WP02 removes that
  block, so this WP (which owns that test) must reconcile it AFTER WP02 lands.
- Zero-caller proof (run at WP start to confirm still true):
  `git grep -n 'hidden_feature_option\|LEGACY_FEATURE_HELP' -- src/` → only
  `_legacy_aliases.py` self-references.
- **Do NOT** touch `selector_resolution.py` / `resolve_selector` (FR-008) or any
  command file (those are WP01/WP02).

## Branch Strategy

- **Strategy**: lane-per-WP from `lanes.json`
- **Planning base branch**: `mission/codebase-sanitization-1060-1622`
- **Merge target branch**: `mission/codebase-sanitization-1060-1622`
- **Implement command**: `spec-kitty agent action implement WP05 --agent claude --base mission/codebase-sanitization-1060-1622`
  (the `--base` is REQUIRED — `lanes.json` records a stale `mission_branch`; see
  the mission's flatten note).

## Subtasks & Detailed Guidance

### Subtask T020 – Remove the dead helper
- **Steps**: In `src/specify_cli/missions/_legacy_aliases.py`, delete
  `hidden_feature_option()` and `LEGACY_FEATURE_HELP` (and the now-unused
  `typer`/`cast` imports). If nothing substantive remains, reduce the module to a
  short docstring-only stub (keep the file importable) OR delete it and confirm
  no `src/` import references it (`git grep -n '_legacy_aliases' -- src/`).
- **Files**: `src/specify_cli/missions/_legacy_aliases.py`

### Subtask T021 – Reconcile the legacy-alias test
- **Steps**: In `tests/integration/test_legacy_feature_alias.py`:
  - Remove `test_hidden_feature_option_*` tests + the `hidden_feature_option`
    import (the symbol is gone) — record a one-line rationale per C-001.
  - The `charter/lint.py` "keeps a `--feature` block" assertion (L91-96) is now
    false (WP02 removed it) — delete/repurpose that assertion. If the whole file
    is now obsolete, delete it and note why.
- **Files**: `tests/integration/test_legacy_feature_alias.py`

### Subtask T022 – Remove allowlist entries + confirm gates
- **Steps**: Remove the `hidden_feature_option`/`LEGACY_FEATURE_HELP` entries from
  `tests/architectural/test_no_dead_symbols.py` (~L281) and
  `tests/architectural/test_no_dead_modules.py` (~L339 `TODO(triage)`). Run
  `PWHEADLESS=1 pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py tests/integration/test_legacy_feature_alias.py -q`
  — must stay green (the symbols are gone, so the allowlist entries are no longer
  needed; leaving them would itself fail the "allowlist references a missing
  symbol" check if one exists).
- **Validation**:
  - [ ] `git grep -n 'hidden_feature_option\|LEGACY_FEATURE_HELP'` → 0 (whole repo)
  - [ ] `selector_resolution.py` UNCHANGED
  - [ ] dead-symbol + dead-module gates green; allowlist entries removed
  - [ ] ruff + mypy clean

## Definition of Done
- Dead helper + constant removed; tests retired with rationale; allowlist entries
  gone; gates green; resolver untouched; net LOC-negative.

## Reviewer Guidance
- Confirm zero `hidden_feature_option`/`LEGACY_FEATURE_HELP` repo-wide,
  `resolve_selector` untouched, and that test deletions carry a rationale (not
  silent deletion to pass). Confirm the allowlist entries were removed (not just
  the symbols).

## Activity Log

- 2026-06-15T14:41:42Z – user – shell_pid=315738 – Review passed (renata, off-lane consolidation): see review evidence; code on mission/
- 2026-06-15T14:41:50Z – user – shell_pid=315738 – Moved to done
