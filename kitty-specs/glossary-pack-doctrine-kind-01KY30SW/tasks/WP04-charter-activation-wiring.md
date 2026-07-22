---
work_package_id: WP04
title: Charter activation wiring + three-way drift-guard + default-on
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- C-005
- FR-007
- FR-008
- FR-009
planning_base_branch: research/glossary-doctrine-artefact
merge_target_branch: research/glossary-doctrine-artefact
branch_strategy: Planning artifacts for this mission were generated on research/glossary-doctrine-artefact. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/glossary-doctrine-artefact unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_glossary_pack_activation.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/charter/activations.py
- src/charter/pack_context.py
- src/charter/consistency_check.py
- src/charter/drg.py
- src/charter/schemas.py
- src/doctrine/drg/org_pack_loader.py
- src/specify_cli/doctrine/org_charter.py
- tests/doctrine/test_org_pack_augmentation.py
- tests/charter/test_pack_manager.py
- tests/charter/test_pack_manager_catalog.py
- tests/charter/test_pack_context.py
- tests/charter/test_glossary_pack_activation.py
role: implementer
tags: []
tracker_refs: []
shell_pid: "1696888"
shell_pid_created_at: "1784673512.67"
---

# WP04 — Charter activation wiring + three-way drift-guard + default-on

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and adopt it fully. **Boundary**: the activation surfaces and
the default-on mechanism are ratified in `plan.md` IC-03, `data-model.md` (default-on + the maps
table), and `reviews/post-plan-squad.md` (F2/M2/M3/M6). Wire exactly those surfaces; do not invent
new activation paths.

## Objective

Make `GLOSSARY_PACK` activate/cascade/deactivate generically across **all** activation surfaces, ship
the built-in `spec-kitty-core` pack **active by default**, and — critically — **extend the drift-guard
to actually protect default-on**. The squad proved the existing guard binds only 2 of the 3 kind-lists;
the one it omits (`_BUILTIN_ARTIFACT_KINDS`) is the one that delivers default-on, so a green suite can
silently ship without it. This WP closes that hole.

## Context — the surfaces (all verified against source)

- **Three kind-lists** (hold **plural strings** like `"directives"`, add `"glossary_packs"`):
  - `src/charter/activations.py` → `_ALLOWED_KINDS`; also add `_SINGULAR_TO_PLURAL_KIND["glossary_pack"] = "glossary_packs"`.
  - `src/charter/pack_context.py` → `_BUILTIN_ARTIFACT_KINDS` (this is the **default-on** list) +
    `activated_glossary_packs` field + `_read_activated_glossary_packs` + wiring in `from_config`/`from_activation`.
  - `src/doctrine/drg/org_pack_loader.py` → add to `_ORG_DRG_KIND_ALIASES` (the **dict** behind the
    derived `_ORG_DRG_CANONICAL_KINDS` frozenset), NOT the frozenset directly.
- **Two more per-kind maps**: `src/charter/consistency_check.py` → `_CLI_KIND_TO_DRG_SINGULAR["glossary-pack"] = "glossary_pack"`; `src/charter/drg.py` → the two kind-map entries.
- **Default-on mechanism (named)**: three-state `None` default + `_BUILTIN_ARTIFACT_KINDS` membership +
  the root graph fragment shipped in WP03. No `config.yaml` entry, no `suggests`/`requires` edge.
- **The drift-guard**: `tests/doctrine/test_org_pack_augmentation.py:411-431` currently binds only
  `_ALLOWED_KINDS ↔ _ORG_DRG_CANONICAL_KINDS ∪ mission-type`. `_BUILTIN_ARTIFACT_KINDS` is unbound.
- **Exact-set tests that will go red until updated**: `tests/charter/test_pack_manager.py` (`YAML_KEY_MAP`
  equality ~61), `tests/charter/test_pack_manager_catalog.py` (~94/98),
  `tests/charter/test_pack_context.py` (`test_packcontext_has_all_ten_activated_fields` ~388, 10→11).

## Subtasks

### T018 — `activations.py` wiring · FR-008, FR-009

- Add `"glossary_packs"` to `_ALLOWED_KINDS`.
- Add `_SINGULAR_TO_PLURAL_KIND["glossary_pack"] = "glossary_packs"` so an operator writing
  `artifact_kind: glossary_pack` in a governance.yaml activation entry normalises correctly.

### T019 — `pack_context.py` default-on wiring · FR-007, SC-003

- Add `"glossary_packs"` to `_BUILTIN_ARTIFACT_KINDS` (this is what makes the kind active when
  `activated_kinds` config is absent — the default-on seam).
- Add the `activated_glossary_packs` field, a `_read_activated_glossary_packs` reader, and wire it into
  `from_config`/`from_activation` (mirror an existing `activated_*` field end-to-end).
- **Exhaustiveness gate (surfaced during WP03 implementation, squad miss).** `src/charter/schemas.py`
  `DoctrineSelectionConfig` must gain `selected_glossary_packs` (mirror `selected_directives`) or
  `tests/architectural/test_artifact_selection_completeness.py::test_every_doctrine_kind_has_a_charter_selected_field`
  stays RED (it asserts every `DoctrineService` kind has a `selected_<kind>` field). This is a
  transient red since WP01 added the kind; WP04 closes it.

### T020 — org-pack alias + consistency map + charter DRG maps · FR-008, FR-009

- `src/doctrine/drg/org_pack_loader.py`: add `"glossary_packs"` to `_ORG_DRG_KIND_ALIASES`.
- `src/charter/consistency_check.py`: add `_CLI_KIND_TO_DRG_SINGULAR["glossary-pack"] = "glossary_pack"`.
- `src/charter/drg.py`: add the two kind-map entries (mirror `directive`).
- **Org-required exhaustiveness gate (squad miss, surfaced in WP03).** `src/specify_cli/doctrine/org_charter.py`
  `OrgCharterPolicy` must gain `required_glossary_packs` (mirror `required_directives` at ~:156) AND be
  wired into the merge plumbing (`merged_required["glossary_packs"]` ~:596, `list(...required_glossary_packs)`
  ~:822, `apply_org_charter_to_interview` ~:827, and the `"required_glossary_packs"` payload ~:937), or
  `test_artifact_selection_completeness::test_every_doctrine_kind_has_an_org_required_field` stays RED.
  The test's own message names these exact edit points.

### T021 — Update exact-set tests (10→11) · C-005

- Update `tests/charter/test_pack_manager.py` and `test_pack_manager_catalog.py` expected `YAML_KEY_MAP`
  values to include `glossary-pack → activated_glossary_packs` (the map derives; only the expected
  literals need updating).
- Update `tests/charter/test_pack_context.py::test_packcontext_has_all_ten_activated_fields` to expect
  **eleven** activated fields (rename if the name encodes the count).

### T022 — Extend drift-guard to three-way + default-on assertion (RED-FIRST) · C-005, SC-003

- In `tests/doctrine/test_org_pack_augmentation.py`, extend `test_lockstep_drift_guard_against_allowed_kinds`
  (or add a sibling) so the equality **includes `_BUILTIN_ARTIFACT_KINDS`** — a genuine three-way check.
- Add a **positive default-on assertion**: `"glossary_packs" ∈ _BUILTIN_ARTIFACT_KINDS` AND the built-in
  `spec-kitty-core` pack is in the default (absent-config) activated set.
- **Squad F3 — credible RED-first ordering.** The three-way equality would be GREEN-on-arrival if
  authored after T018–T021 make all lists consistent. So the **RED-first anchor is the positive
  default-on assertion**, authored **before** T019 adds `glossary_packs` to `_BUILTIN_ARTIFACT_KINDS`
  (it is RED until T019 lands). Alternatively, author the three-way guard while one list entry is still
  deliberately absent, witness it go RED, then complete the wiring — but do NOT claim "RED-first" for a
  guard written after the wiring is already consistent. The DoD's "guard extension was RED-first" must
  be demonstrable (RED commit before the completing-wiring commit).

### T023 — Default-on + cascade end-to-end · FR-007, FR-009, SC-003

- File: `tests/charter/test_glossary_pack_activation.py`.
- With no manual `charter activate`, the built-in pack resolves as **active** in the compiled charter
  references. `charter activate/deactivate glossary-pack spec-kitty-core --cascade all` operate through
  the generic DRG edges (cascade is `kind`-agnostic — do not add per-kind cascade logic).

## Branch Strategy

Planning base `research/glossary-doctrine-artefact`; per-lane worktree; merge back unless redirected.
Depends on WP03 (the graph fragment) for the default-on resolution to succeed.

## Definition of Done

- [ ] All five activation surfaces updated with the plural string `"glossary_packs"` (and the singular
      alias where required).
- [ ] `activated_glossary_packs` field + reader + `from_config`/`from_activation` wiring complete.
- [ ] Exact-set tests updated (10→11; `YAML_KEY_MAP`).
- [ ] Drift-guard is genuinely **three-way** (incl `_BUILTIN_ARTIFACT_KINDS`) + positive default-on
      assertion; guard extension was RED-first.
- [ ] Default-on + cascade end-to-end green.
- [ ] `ruff` + `mypy --strict` clean; complexity ≤ 15; ≥ 90% coverage.
- [ ] `pytest tests/charter/ tests/doctrine/test_org_pack_augmentation.py -q` green.

## Risks & Reviewer Guidance

- **Risk (the squad's central finding)**: omitting `_BUILTIN_ARTIFACT_KINDS` — default-on silently off,
  suite green. Reviewer confirms the guard now binds all three lists AND a positive default-on assertion
  exists that would fail if the built-in list entry were removed.
- **Risk**: editing the derived `_ORG_DRG_CANONICAL_KINDS` frozenset instead of the `_ORG_DRG_KIND_ALIASES`
  dict — reviewer confirms the dict was the edit target.
- **Risk**: adding per-kind cascade branches — reviewer confirms cascade stayed generic.

## Activity Log

- 2026-07-21T22:12:02Z – claude:sonnet:python-pedro:implementer – shell_pid=1658448 – Assigned agent via action command
- 2026-07-21T22:37:41Z – claude:sonnet:python-pedro:implementer – shell_pid=1658448 – WP04 complete; glossary_packs wired across all 7 activation surfaces + DoctrineSelectionConfig.selected_glossary_packs + OrgCharterPolicy.required_glossary_packs; three-way drift-guard RED-first (2ae624d59); exact-set tests 9->10/10->11 updated; default-on+cascade e2e green; 114 target-gate tests pass. Justified out-of-map: charter_yaml_io._ACTIVATION_KEYS += activated_glossary_packs (documented).
- 2026-07-21T22:38:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=1696888 – Started review via action command
- 2026-07-21T22:47:33Z – user – shell_pid=1696888 – Review passed (reviewer-renata). All 8 activation surfaces carry plural 'glossary_packs' (activations _ALLOWED_KINDS + singular alias; pack_context _BUILTIN_ARTIFACT_KINDS + activated_glossary_packs field/reader/from_config; org_pack_loader _ORG_DRG_KIND_ALIASES dict not frozenset; consistency_check _CLI_KIND_TO_DRG_SINGULAR; drg _SINGULAR_TO_PLURAL + _SINGULAR_TO_PER_KIND_FIELD; charter_yaml_io _ACTIVATION_KEYS out-of-map one-liner, documented+justified). RED-FIRST PROVEN EMPIRICALLY: checked out commit 2ae624d59 (guard+default-on assertion, before wiring commit 5925848cd); _BUILTIN_ARTIFACT_KINDS lacked glossary_packs there; ran the 2 guard tests -> 2 FAILED. Guard is genuinely three-way (_ALLOWED_KINDS == _BUILTIN_ARTIFACT_KINDS bare equality + org-pack universe) plus positive default-on membership assertion. GATING FIX CONFIRMED: adding glossary_pack to _SINGULAR_TO_PLURAL closes the Step-2 unknown-kind default-allow (plural is None -> return True) bypass; test_negative_control (activated_kinds omitting glossary_packs) proves the built-in pack node is genuinely FILTERED OUT while other kinds survive -> non-vacuous. Default-on e2e (no config + minimal config) resolves pack active; not a tautology. Exhaustiveness fields present: DoctrineSelectionConfig.selected_glossary_packs + OrgCharterPolicy.required_glossary_packs (REQUIRED_KIND_FIELDS + _fold_policies wiring); test_artifact_selection_completeness green. Exact-set tests updated 9->10 (YAML_KEY_MAP) / 10->11 (pack_context). Cascade stayed generic (cascade.py untouched). MYPY BASELINE VERIFIED: sole error org_charter.py:308 (no-any-return from resolve_config_id) authored 2026-07-10 by 161d5c0b62, 12 days pre-WP04, in untouched code; all 7 other changed src files pass mypy --strict clean; WP04 introduced NO new mypy errors. ruff clean. Gate suite: 1666 passed, 1 skipped. Anti-pattern checklist all PASS.
