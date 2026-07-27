---
work_package_id: WP01
title: Kind registration — ArtifactKind + NodeKind + URN + token
dependencies: []
requirement_refs:
- C-001
- FR-001
- FR-002
- FR-003
- FR-010
- NFR-001
planning_base_branch: research/glossary-doctrine-artefact
merge_target_branch: research/glossary-doctrine-artefact
branch_strategy: Planning artifacts for this mission were generated on research/glossary-doctrine-artefact. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/glossary-doctrine-artefact unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent:
- tests/architectural/test_glossary_pack_urn.py
- tests/doctrine/test_glossary_pack_kind.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/doctrine/artifact_kinds.py
- src/doctrine/drg/models.py
- tests/doctrine/test_artifact_kinds.py
- tests/architectural/test_glossary_pack_urn.py
- tests/doctrine/test_glossary_pack_kind.py
role: implementer
tags: []
tracker_refs: []
shell_pid: "1528455"
shell_pid_created_at: "1784666652.07"
---

# WP01 — Kind registration (ArtifactKind + NodeKind + URN + token)

## ⚡ Do This First: Load Agent Profile

Before reading further, run `/ad-hoc-profile-load python-pedro` and adopt it in full: idiomatic,
type-safe Python 3.11+; TDD red→green→refactor; run the `pytest`/`ruff`/`mypy` gate before handoff.
**Boundary**: the design is ratified in `plan.md` (IC-01) and `data-model.md`. Do not redesign the
kind system; implement the ratified shape. If a genuine structural ambiguity surfaces, stop and
escalate rather than inventing a shape.

## Objective

Make `GLOSSARY_PACK` a first-order, charter-activatable doctrine `ArtifactKind` and a DRG-addressable
`NodeKind`, with the **underscore** URN `glossary_pack:<id>`. This is the foundation every other WP
builds on. It is deliberately additive — the derived token/classification machinery
(`from_operator_token`, `CHARTER_KIND_TOKENS`, `YAML_KEY_MAP`) must pick the kind up **for free**
once the enum member exists and is kept out of the `{template, asset}` exclusion set.

## Context

- **Design of record**: `plan.md` IC-01; `data-model.md` (enum + NodeKind sections);
  `research.md` (URN-underscore decision); `reviews/post-plan-squad.md` (confirmed-sound spine).
- **Requirements owned**: FR-001 (enum member), FR-002 (charter-activatable classification), FR-003
  (DRG node + underscore URN), FR-010 (operator-token normalisation), NFR-001 (URN regression),
  C-001 (copy `directive`, NOT `asset` — stay out of `_NON_AUGMENTATION_ELIGIBLE_KINDS`).
- **Verified anchors** (from the squad, re-checked against source):
  - `src/doctrine/artifact_kinds.py`: `ArtifactKind` enum (~82-91), `_NON_AUGMENTATION_ELIGIBLE_KINDS`
    (~178-190), `from_operator_token` on the enum (~128), `CHARTER_KIND_TOKENS` derived from the enum
    minus the exclusion set. There are `_PLURALS`/`_PATTERNS` maps to extend.
  - `src/doctrine/drg/models.py`: URN regex `_URN_RE = ^[a-z_]+:…` (~19), the `prefix != kind.value`
    raise (~103-121), `NodeKind` enum with existing `GLOSSARY`/`GLOSSARY_SCOPE` runtime term nodes (~44-45).

## Subtasks

### T001 — URN hyphen-rejection regression (RED-FIRST) · NFR-001

Write this test **before** any production edit; it must be RED on the base (the kind does not exist
yet) and GREEN at WP end.

- File: `tests/architectural/test_glossary_pack_urn.py`.
- Assert: a DRG node with URN `glossary_pack:spec-kitty-core` (underscore) is **accepted**; the
  hyphenated `glossary-pack:spec-kitty-core` is **rejected** (raises / fails the regex), at BOTH the
  `_URN_RE` layer and the `prefix == kind.value` assertion. Reference the two guard layers explicitly.
- Also assert `NodeKind.GLOSSARY_PACK.value == "glossary_pack"`.

### T002 — Add `ArtifactKind.GLOSSARY_PACK` + plurals/patterns; classification · FR-001, FR-002, C-001

- Add `GLOSSARY_PACK = "glossary_pack"` to `ArtifactKind`.
- Add `_PLURALS["glossary_pack"] = "glossary_packs"` and the matching `_PATTERNS` entry (mirror how
  `directive`/`directives` is declared — copy that kind's shape exactly).
- Do **NOT** add it to `_NON_AUGMENTATION_ELIGIBLE_KINDS`. Add an explicit assertion in T005 that it
  is absent from that set and present in `CHARTER_KIND_TOKENS`.

### T003 — Add `NodeKind.GLOSSARY_PACK` + comment fence · FR-003

- Add `GLOSSARY_PACK = "glossary_pack"` to `NodeKind` in `src/doctrine/drg/models.py`.
- Add a comment fence grouping the **retiring runtime** term nodes (`GLOSSARY`, `GLOSSARY_SCOPE` —
  deleted in Mission C) separately from the new **doctrine-owned** `GLOSSARY_PACK` (keep). This
  de-risks Mission C's deletion (squad LOW finding). Do not alter the runtime nodes.

### T004 — Assert derived token/classification is free · FR-010

- In `tests/doctrine/test_glossary_pack_kind.py`, assert (no production change should be needed here —
  these must derive):
  - `ArtifactKind.from_operator_token("glossary-pack") is ArtifactKind.GLOSSARY_PACK`.
  - `"glossary-pack" in CHARTER_KIND_TOKENS`.
  - `YAML_KEY_MAP["glossary-pack"] == "activated_glossary_packs"` (import `YAML_KEY_MAP` from
    `charter/pack_manager.py` — NOT `kind_vocabulary.py`).
- If any of these does NOT derive for free, STOP — it means the enum wiring in T002 is incomplete;
  fix T002 rather than special-casing here.

### T005 — Kind-classification test + update the hard exact-set assertion · FR-002, C-001

- Assert `ArtifactKind.GLOSSARY_PACK not in _NON_AUGMENTATION_ELIGIBLE_KINDS`.
- Assert `_PLURALS[ArtifactKind.GLOSSARY_PACK.value] == "glossary_packs"`.
- **Squad H1 — mandatory**: `tests/doctrine/test_artifact_kinds.py:18-31` hard-asserts
  `{m.value for m in ArtifactKind} == {…11 literal values…}`. Adding `GLOSSARY_PACK` turns this RED.
  This test is in this WP's `owned_files` — **update the expected set to include `"glossary_pack"`**
  (the sibling assertions at ~:57 plural-uniqueness and ~:80 empty-pattern stay green given the
  `*.glossary-pack.yaml` glob). Do NOT leave it red; it is not a pre-existing failure, it is your
  enum addition.

## Branch Strategy

Planning artifacts were generated on `research/glossary-doctrine-artefact`. Execution worktrees are
allocated per computed lane from `lanes.json` during `/spec-kitty.implement`. Completed changes merge
back into `research/glossary-doctrine-artefact` unless the human redirects the landing branch.

## Definition of Done

- [ ] T001 URN regression committed RED-first, then GREEN.
- [ ] `ArtifactKind.GLOSSARY_PACK` + plural/pattern added; NOT in the exclusion set.
- [ ] `NodeKind.GLOSSARY_PACK` added + comment fence.
- [ ] Derived-token/classification assertions pass with **no** special-casing.
- [ ] `ruff` + `mypy --strict` clean; complexity ≤ 15; new code ≥ 90% covered.
- [ ] Targeted suites green: `pytest tests/doctrine/test_glossary_pack_kind.py tests/architectural/test_glossary_pack_urn.py -q`; the existing `tests/doctrine/` kind/URN suites stay green.

## Risks & Reviewer Guidance

- **Risk**: adding the member to the exclusion set (would silently make the kind non-activatable) —
  reviewer verifies T005 membership assertion.
- **Risk**: hand-writing token normalisation instead of letting it derive — reviewer verifies T004
  has **no** production edit to `kind_vocabulary.py`/`pack_manager.py` logic.
- **Reviewer**: confirm T001 was RED on the base (git-show the pre-change file) and GREEN at HEAD;
  confirm the comment fence in `models.py` names Mission C.

## Activity Log

- 2026-07-21T20:26:44Z – claude:opus:python-pedro:implementer – shell_pid=1512431 – Assigned agent via action command
- 2026-07-21T20:42:33Z – claude:opus:python-pedro:implementer – shell_pid=1512431 – WP01 kind registration complete; URN regression + exact-set + derive tests green. NOTE: enum addition also required 1-line canonical fix to unowned executor.py::_ARTIFACT_TO_NODE_KIND (squad wrongly cleared totality guard); 5 WP04-owned charter test_pack_manager* hard-count assertions now expect the derived 9->10 YAML_KEY_MAP growth (WP04 to absorb on rebase).
- 2026-07-21T20:44:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=1528455 – Started review via action command
- 2026-07-21T20:50:01Z – user – shell_pid=1528455 – Review passed. Additive kind registration correct: ArtifactKind.GLOSSARY_PACK + _PLURALS/_PATTERNS added, kept OUT of _NON_AUGMENTATION_ELIGIBLE_KINDS (template/asset only); token/CHARTER_KIND_TOKENS/YAML_KEY_MAP all derive for free (pack_manager.py + kind_vocabulary.py verified untouched; YAML_KEY_MAP is a comprehension over CHARTER_KIND_TOKENS). T001 URN regression confirmed RED-first (base lacked GLOSSARY_PACK in both enums; test files absent on base) and now GREEN, exercising BOTH real guard layers (_URN_RE + prefix==kind.value in DRGNode._validate_urn). T005 exact-set updated to include glossary_pack; NodeKind fence names Mission C. Gates green: 55 targeted tests pass incl. tests/doctrine/drg/test_kind_mapping_totality.py; ruff + mypy --strict exit 0. Executor.py leeway CONFIRMED: exactly one canonical line added to the non-exempt TOTAL _ARTIFACT_TO_NODE_KIND dict, required to keep the repo-wide totality guard green; no other edits rode in. WP04-owned tests/charter/test_pack_manager*.py correctly LEFT ALONE (their 9->10 YAML_KEY_MAP redness is the expected WP04 transient, not a WP01 defect). Filled issue-matrix #1418 verdict as in-mission (keystone landed in WP01; terminal at mission close).
