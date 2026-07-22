---
work_package_id: WP02
title: Retire charter.extractor + its deferred allowlist entries
dependencies: []
requirement_refs:
- FR-003
- FR-004
- NFR-002
- C-003
- C-004
tracker_refs:
- '#1797'
planning_base_branch: feat/charter-deadcode-noop-campsite
merge_target_branch: feat/charter-deadcode-noop-campsite
branch_strategy: Planning artifacts for this mission were generated on feat/charter-deadcode-noop-campsite. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-deadcode-noop-campsite unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/extractor.py
- tests/architectural/_baselines.yaml
- tests/architectural/test_no_dead_modules.py
- tests/architectural/test_no_dead_symbols.py
- tests/charter/test_chokepoint_coverage.py
- tests/charter/test_extractor.py
- tests/charter/test_extractor_activations.py
- tests/charter/test_extractor_selection.py
- tests/charter/test_sync_authority_paths.py
- tests/charter/test_sync_references.py
- tests/charter/test_activate_resolves_no_answers_edit.py
- tests/charter/test_charter_context_spdd_reasons.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1622149"
shell_pid_created_at: "1784429760.61"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile via `/ad-hoc-profile-load python-pedro`
(implementer). Load the YAML — do not act on the persona name alone.

## Objective

Delete the dead `charter.extractor` module (`Extractor` husk — the prose→triad scraper retired by
#2773 WP04) and remove its three deferred arch-gate allowlist entries **in the same change**, so
the dead-code baseline shrinks downward and the gates stay green. Zero non-test `src/` callers.

**Authoritative grounding** (read first): [`research.md` §2](../research.md),
[`data-model.md` LM-2](../data-model.md).

## Context / grounding (verified at `main@4c93a0f58`)

- `src/charter/extractor.py` — `Extractor` class + `_detect_catalog_references` + `ExtractionResult`.
  `SECTION_MAPPING`/`write_extraction_result`/`extract_with_ai`/`_classify_section` already deleted
  by #2773. **Zero non-test `src/` callers**; NOT reexported in `src/charter/__init__.py`.
- **FOUR** gate surfaces key on the extractor — ALL must be edited atomically with T005, else the
  respective gate goes red (LM-2):
  1. `tests/architectural/_baselines.yaml:58` — `category_5_wp_in_flight_adapters: 1` → **0** (+ trim the
     stale justification comment at :57-58).
  2. `tests/architectural/test_no_dead_modules.py:339-344` — the `"charter.extractor"` entry (+ its
     comment) in `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS` (empties the frozenset). If left → stale-entry
     assert fails at `:596-598`.
  3. `tests/architectural/test_no_dead_symbols.py:907-913` — the `Extractor` `SymbolKey` frozenset
     `_CATEGORY_C_WP_IN_FLIGHT_EXTRACTOR_RETIREMENT` **and** its `|` term in the `_SYMBOL_ALLOWLIST`
     union (search downstream of `:951`). If left → dangling assert fails at `:1753-1790`. No
     symbol-baseline *number* changes (this category has no key in the baseline section).
  4. **`tests/charter/test_chokepoint_coverage.py:61`** (found by the post-tasks squad) — remove the
     `"src/charter/extractor.py"` member of the `_CARVE_OUTS` frozenset. `test_carve_out_files_exist()`
     at `:251` asserts every carve-out path EXISTS; deleting the module without dropping this line
     fails with `Carve-out entries reference missing files: ['src/charter/extractor.py']`. This gate
     lives under `tests/charter/`, NOT `tests/architectural/` — easy to miss.
- Extractor-importing test files: `test_extractor.py`, `test_extractor_activations.py`,
  `test_extractor_selection.py`, `test_sync_authority_paths.py`, `test_sync_references.py`
  (line 156 already-broken `Extractor(tactic_registry=...)`), plus Extractor *usage* in
  `test_activate_resolves_no_answers_edit.py:213` and `test_charter_context_spdd_reasons.py:459`.

## Subtasks

### T005 — Delete `src/charter/extractor.py`
Remove the module entirely.

### T006 — Retire / de-Extractor the test files (C-003 — preserve non-Extractor coverage)
For EACH of the 7 files, classify before editing:
- **Extractor-dedicated** (`test_extractor.py`, `test_extractor_activations.py`,
  `test_extractor_selection.py`, `test_sync_authority_paths.py`, `test_sync_references.py`) — the
  covered code (the scraper) is being deleted, so retire the file (or its Extractor-only body).
- **Incidental import — RECONSTRUCT the fixture, do NOT just delete the usage**
  (`test_activate_resolves_no_answers_edit.py:213`, `test_charter_context_spdd_reasons.py:459`): the
  squad found the `Extractor().extract(...)` call is a **fixture-builder** whose `.governance`/
  `.directives` output feeds LIVE assertions (`save_charter_yaml` → `is_spdd_reasons_active(...) is
  True`). Deleting only the usage leaves `extraction` undefined (NameError); deleting the whole test
  drops live SPDD-activation coverage (C-003/INV-4). **Reconstruct** `GovernanceConfig`/
  `DirectivesConfig` inline from the already-available `interview.selected_directives` /
  `compiled.selected_tactics` so the live `is_spdd_reasons_active` assertions survive without Extractor.

### T007 — Remove ALL FOUR gate entries (LM-2 — atomic with T005)
Apply the four edits from Context above (3 arch-gate + the chokepoint carve-out at
`test_chokepoint_coverage.py:61`). The baseline edit is a legal DOWNWARD move; do not green-wash upward.

### T008 — Verify
- `PWHEADLESS=1 pytest tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_ratchet_baselines.py tests/charter/test_chokepoint_coverage.py -q`
  → green; no `stale_allowlist_entries`, no `dangling`, no missing carve-out.
- `git grep -n "charter.extractor\|\bExtractor\b" -- src tests` → only the intended removals remain
  (the unrelated `doctrine.drg.migration.extractor` is a different module — leave it).
- `ruff check` + `mypy --strict` on touched files → clean.

## Definition of Done
- `src/charter/extractor.py` deleted; 7 test files retired/de-Extractored (incidental files
  reconstructed, no unrelated coverage lost); all FOUR gate entries removed; `category_5` baseline = 0;
  dead-code + chokepoint gates green; ruff + mypy clean. Net LOC negative.

## Landmines
- **LM-2**: module deletion + `_baselines.yaml` 1→0 + the two arch-gate edits + the chokepoint
  carve-out drop are ONE atomic change (FOUR gate surfaces) — never split across separately-landing WPs.

## Reviewer guidance
Confirm no stale/dangling gate reds; confirm the two incidental-import files retained their
non-Extractor tests; confirm the baseline moved downward (1→0), never up.

## Activity Log

- 2026-07-19T02:37:49Z – claude:sonnet:python-pedro:implementer – shell_pid=1510808 – Assigned agent via action command
- 2026-07-19T02:55:17Z – claude:sonnet:python-pedro:implementer – shell_pid=1510808 – extractor retired; 4 gates edited; incidental fixtures reconstructed; gates green
- 2026-07-19T02:56:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=1622149 – Started review via action command
