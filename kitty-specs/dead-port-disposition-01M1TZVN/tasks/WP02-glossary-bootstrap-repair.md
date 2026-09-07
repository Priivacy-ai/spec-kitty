---
work_package_id: WP02
title: Glossary Runner Design-Story Repair
dependencies: []
requirement_refs:
- FR-008
- FR-009
- FR-010
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
phase: Wave 0 - Docs-shaped repair
history:
- at: '2026-09-06T12:40:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/kernel/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/kernel/glossary_runner.py
- src/kernel/__init__.py
- src/kernel/README.md
- src/charter/offering/missions/glossary_hook.py
- tests/doctrine/missions/test_glossary_hook.py
role: implementer
agent: claude
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Glossary Runner Design-Story Repair

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log. Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

User Story 2 (P2). The kernel glossary-runner registry is **LIVE** (this is a documentation repair, not a deletion). Four verified sites tell three variants of a fiction ("`specify_cli`/`glossary` registers the runner at import/startup"); the real mechanism is the lazy self-bootstrap inside `src/charter/offering/missions/glossary_hook.py:127-137`.

Done means:

- **SC-004**: the four sites (`src/kernel/glossary_runner.py:14-16,33-38` + the dependency diagram at `:3`; `src/charter/offering/missions/glossary_hook.py:16-17`; `src/kernel/README.md:18`; `src/kernel/__init__.py:38-42`) describe the self-bootstrap contract from `contracts/glossary-bootstrap.md` §1; the SC-004 grep (§5) yields no registration-by-`specify_cli`/`glossary` phrasing.
- **FR-009**: a behaviour test pins that, with a cleared registry, `execute_with_glossary` leaves `get_runner()` returning a `GlossaryAwarePrimitiveRunner`; a second test pins that degradation happens only when `glossary.attachment` is unimportable.
- **SC-005 / FR-010**: the FR-020 enforcement-honesty `.. note::` is in `glossary_hook.py`; the #1868 tracker-note text is drafted in `kitty-specs/dead-port-disposition-01M1TZVN/design-notes/WP02-glossary.md` (the operator posts it).
- Zero behaviour change (the optional `_ensure_runner_registered()` extraction is code motion only).

## Context & Constraints

- Spec US2, FR-008..010. Contract `contracts/glossary-bootstrap.md` (binding: the contract text, site edits, pins, note wording). Data model §4. Research §2 (OD5 (a): `01M1VAHKNXJTCMQNBQ350CWGEM`; OD6 deferred, working assumption "documented-but-unwired accepted").
- Layer rules: `kernel ← charter ← glossary`; the hook (in `charter.offering`) importing `glossary.attachment` lazily is the existing direction — do not add a `kernel → glossary` import.
- Terminology guard runs before any doc push (`tests/architectural/test_no_legacy_terminology.py`).
- Leave the three-link re-export chain (`charter/offering/missions/__init__.py:10` → `charter/primitives.py:14` → `specify_cli/missions/__init__.py:28`) alone (US2-4; pins in `test_no_dead_symbols.py`).

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP02 --mission dead-port-disposition-01M1TZVN`.

## Subtasks & Detailed Guidance

### Subtask T008 – Rewrite the four sites

- **Purpose**: FR-008.
- **Steps**: read all four files fully first, plus `src/glossary/attachment.py` (to confirm the class name and that it registers nothing at import). Then apply `contracts/glossary-bootstrap.md` §2 site by site. In `glossary_runner.py`: new module docstring (registry purpose; the contract; the degradation rule; the corrected diagram `doctrine → kernel.glossary_runner ← charter.offering.missions.glossary_hook (lazy provider) ← glossary.attachment`); replace the "provider (specify_cli)" usage block with the hook's bootstrap snippet. In `glossary_hook.py`: replace `:16-19`; optionally extract the `:127-137` bootstrap into `_ensure_runner_registered() -> GlossaryRunnerProtocol | None` (identical behaviour, same exception handling) so docstrings can name it. `kernel/__init__.py:38-42` and `kernel/README.md:18`: one-line contract each.
- **Files**: the four sites.
- **Parallel?**: No.

### Subtask T009 – Behaviour pins

- **Purpose**: FR-009.
- **Steps**: in `tests/doctrine/missions/test_glossary_hook.py`, using its existing fixtures: (1) `clear_registry()`; assert `get_runner() is None`; call `execute_with_glossary(...)` with glossary checking enabled; assert `get_runner()` is an instance whose type name is `GlossaryAwarePrimitiveRunner`; (2) `clear_registry()`; `monkeypatch.setitem(sys.modules, "glossary.attachment", None)` so `import_module` raises `ImportError`; call `execute_with_glossary(...)`; assert the primitive result is returned directly and `get_runner()` is still `None`. Ensure `clear_registry()` teardown so other tests are unaffected (check the file's existing autouse fixture).
- **Files**: `tests/doctrine/missions/test_glossary_hook.py`.
- **Parallel?**: Yes (alongside T008).

### Subtask T010 – FR-020 honesty note + tracker text + guards

- **Purpose**: FR-010, SC-004, SC-005.
- **Steps**: add the `.. note::` from `contracts/glossary-bootstrap.md` §4 to `glossary_hook.py`'s module docstring (re-verify the two facts before writing: `grep -rn "execute_with_glossary(" src --include='*.py' | grep -v "def "` → zero production call sites; `grep -rn "glossary_check" packs/` → zero). Write `design-notes/WP02-glossary.md` with the tracker-note text for #1868 (same facts + the OD6 working assumption + the statement that wiring is a separate feature decision). Run the SC-004 grep and the terminology guard.
- **Files**: `glossary_hook.py`, design note.
- **Parallel?**: No.

## Test Strategy

```bash
.venv/bin/pytest tests/doctrine -q
.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py -q
PWHEADLESS=1 make test-fast
grep -n "at import time\|at startup\|registers the concrete\|specify_cli.*register" src/kernel/glossary_runner.py src/kernel/__init__.py src/kernel/README.md src/charter/offering/missions/glossary_hook.py
.venv/bin/ruff check src/kernel src/charter/offering/missions/glossary_hook.py tests/doctrine/missions && .venv/bin/mypy src/kernel/glossary_runner.py src/charter/offering/missions/glossary_hook.py
```

## Risks & Mitigations

- The note reads as a promise to wire the hook → use the contract's wording ("separate feature decision").
- Test isolation: registry is process-global → always `clear_registry()` in setup and teardown.

## Review Guidance

- Grep SC-004 clean; four sites consistent with each other and with the code at `:127-137`.
- Pins present and green; no behaviour change (`git diff` on `glossary_hook.py` shows docstring + optional pure extraction only).
- Design note has the #1868 text; terminology guard green.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T12:40:00Z – system – Prompt created.
