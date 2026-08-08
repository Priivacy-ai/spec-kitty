---
work_package_id: WP03
title: Verdict-seam census completeness (function-level exclusion + helper-construction classifier)
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-013
- NFR-002
planning_base_branch: hardening/verdict-seam-facade-followup
merge_target_branch: hardening/verdict-seam-facade-followup
branch_strategy: Planning artifacts for this mission were generated on hardening/verdict-seam-facade-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into hardening/verdict-seam-facade-followup unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 2 - Parallel hardening
history:
- at: '2026-08-08T09:55:00Z'
  actor: system
  action: Prompt generated from plan.md IC-02
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_verdict_seam_census.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_verdict_seam_census.py
- tests/architectural/verdict_seam_census.yaml
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3236'
- '3217'
---

# Work Package Prompt: WP03 – Census completeness

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` and behave per its guidance before parsing the rest of this prompt.

## Goal

Make the verdict-seam census see the readers it currently masks. Two coordinated blind spots of the same guard-vacuity class: #3236 (a *module-level* wholesale exclusion hides a genuine reader) and #3217 (the classifier misses *helper-constructed* reader records). Fixing only one leaves the census half-hardened — do both here. **Independent code surface from WP01/WP02** (parallel lane, no ordering dependency).

## Subtasks

### T011 — Add a function-level exclusion mechanism
The census exclusion is module-only today (`relpath in _EXCLUDED_MODULE_REASONS` drops the whole file before any function classification, ~L334 in `test_verdict_seam_census.py`). Add a **function-level** mechanism — e.g. a `_EXCLUDED_FUNCTIONS: set[tuple[relpath, qualname]]` consulted inside `_classify_module` / `_iter_functions` — so specific write-side helpers can be excluded while genuine readers still classify.

### T012 — Narrow the `verdict_provenance_backfill.py` exclusion (#3236)
Remove `migration/verdict_provenance_backfill.py` from `_EXCLUDED_MODULE_REASONS`. Exclude **only** its write-side helpers by name via the new mechanism, leaving `_legacy_frontmatter_verdict` (a genuine frontmatter reader: `read_text` + `yaml.load` + `"\n---"` delimiter) to surface as a classified reader row. The module's other functions (`_resolve_mission_id`, `_review_cycle_candidate_dirs`, `discover_wp_ids_with_review_cycles`, `_cycle_number`, `terminal_review_artifact`, `stranded_verdict_findings`, `_backfill_event_for_wp`, `backfill_verdict_provenance`) must classify as non-readers or be excluded by name — verify each; reconcile any new rows into the fixture.

### T013 — Recognize helper-constructed readers (#3217)
Extend the classifier so a reader constructed via a helper (not a direct `read_text`+parse in the function body) is recognized — specifically `migration/backfill_runtime_state.py::_review_from_frontmatter` must surface as a reader row. Keep the predicate tight enough not to over-match unrelated helpers.

### T014 — Flip the wholesale-exclusion tests + fixture; keep teeth
Update the 3 tests that assert `verdict_provenance_backfill.py` is wholesale-excluded / contributes zero rows (~L1075, L1421, L1461-1465) to assert the new function-level shape. Update `verdict_seam_census.yaml` for the newly-surfaced reader rows. **Retain / add the non-vacuity teeth** (NFR-002): a synthetic reader must still be caught; the census must fail if the classifier is neutered.

## Coordination notes
- WP02 also edits `verdict_provenance_backfill.py` **source** (a verdict_vocab import migration) — different file from this WP's census test, no overlap. Its import change does not alter reader/writer *shape*, so classification is unaffected. If both land, rebase cleanly.
- Do **NOT** merge this census file with `test_2093_authority_invariant.py` (explicit warning ~L55-59).

## Branch Strategy
Independent parallel lane off `hardening/verdict-seam-facade-followup`; merges back to same.

## Definition of Done
- `_legacy_frontmatter_verdict` and `_review_from_frontmatter` appear as reader rows; write-side helpers excluded by name.
- The 3 wholesale-exclusion tests updated to the function-level shape and green; fixture reconciled.
- Non-vacuity teeth present and passing. `ruff`/`mypy` clean, zero new suppressions.
- `pytest tests/architectural/test_verdict_seam_census.py` green.

## Reviewer Guidance
Confirm the exclusion is now function-scoped (module no longer wholesale-dropped), that exactly the intended write-side helpers are excluded (not the reader), and that the teeth test genuinely fails on a neutered classifier.

## Risks
- Over-narrow exclusion surfaces unintended rows from the module's other 8 functions — verify their classification explicitly.
- Helper-construction predicate over-matching → false reader rows elsewhere; keep it specific to the frontmatter-read shape.
