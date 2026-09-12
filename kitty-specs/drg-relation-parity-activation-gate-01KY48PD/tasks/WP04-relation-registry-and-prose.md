---
work_package_id: WP04
title: Relation registry + completeness gate + glossary prose
dependencies: []
requirement_refs:
- C-006
- FR-005
- FR-007
- FR-008
- NFR-003
planning_base_branch: doctrine/drg-completeness-2843
merge_target_branch: doctrine/drg-completeness-2843
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-completeness-2843. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-completeness-2843 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-drg-relation-parity-activation-gate-01KY48PD
base_commit: 957384d53f9881246b9db9eac498109464381110
created_at: '2026-07-22T09:02:11.652840+00:00'
subtasks:
- T015
- T016
- T017
- T018
history:
- timestamp: '2026-07-22T08:11:16Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/drg/models.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/drg/models.py
- tests/doctrine/drg/test_models.py
- docs/context/doctrine.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `doctrine-daphne` profile via the `/ad-hoc-profile-load`
skill. Adopt its doctrine-artifact-curation identity, boundaries, and init declaration. This WP
authors doctrine *semantics* (relation meanings) — accuracy over prose polish.

## Objective

Make `RELATION_DESCRIPTIONS` (`src/doctrine/drg/models.py`) complete and self-describing for all 15
`Relation` members, convert the code-side completeness gate, and extend the non-enforced glossary.
This is an **adjudication**, not transcription (FR-007) — ground each description in the relation's
actual emission status.

Read: `contracts/relation-registry-contract.md`, `research.md` D3 (emission-status wording), `spec.md`
US2/AC3. Item A is independent of Item B (parallel lane).

## Subtasks

### T015 — Backfill `RELATION_DESCRIPTIONS` for the 12 members (WP04) [P]

Add descriptions for: `requires, suggests, refines, replaces, enhances, overrides, specializes_from,
delegates_to, scope, instantiates, applies, vocabulary`. Grounding (verified counts):
- `applies` (1 edge) vs `scope` (157 edges): **distinct** descriptions naming each distinct edge-role
  (`RELATION_DESCRIPTIONS[APPLIES] != RELATION_DESCRIPTIONS[SCOPE]`).
- `vocabulary` / `refines` / `delegates_to`: 0 edges everywhere → describe as **intended-but-dormant**.
- `enhances` / `overrides` / `replaces`: 0 edges in built-in **by design** (org-pack overlay
  relations, legacy `replaces`) → describe by actual emission status, NOT as actively-exercised
  built-in relations.
- `requires`/`suggests`/`specializes_from`/`instantiates`: describe their real DRG role.
**Constraint C-006**: describe intent only — do **not** rewire any graph edges.
**Files**: `src/doctrine/drg/models.py`. **Validation**: `RELATION_DESCRIPTIONS` has all 15 members.

### T016 — Convert the completeness gate (WP04)

`tests/doctrine/drg/test_models.py` currently pins `set(RELATION_DESCRIPTIONS) == {IN_TENSION_WITH,
RECONCILES_TENSION, REJECTS}` (`:53-59`) and a non-empty test parametrized over those 3 (`:62`).
Convert to `set(RELATION_DESCRIPTIONS) == set(Relation)` and re-parametrize the non-empty test over
**all** members. **Files**: `tests/doctrine/drg/test_models.py`. **Validation**:
`uv run pytest tests/doctrine/drg/test_models.py -q` green.

### T017 — Extend the glossary prose (non-enforced) (WP04)

Extend `docs/context/doctrine.md` to cover the relations for reader completeness — as **paraphrased
prose explicitly NOT under the parity test** (the glossary deliberately paraphrases; FR-008). Do NOT
try to make it verbatim-equal the registry. **Files**: `docs/context/doctrine.md`.

### T018 — Gates (WP04)

`uv run ruff check` + `uv run python -m mypy --strict src/doctrine`;
`uv run pytest tests/architectural/test_no_legacy_terminology.py -q`;
`npx markdownlint-cli2@0.18.1 --config .markdownlint-cli2.jsonc docs/context/doctrine.md`.

## Branch Strategy

Generated on **`doctrine/drg-completeness-2843`**; merges back into it. Worktrees per lane from
`lanes.json`. No dependencies (Item A root).

## Definition of Done

- [ ] All 15 `Relation` members described; mechanical floor `RELATION_DESCRIPTIONS[APPLIES] != [SCOPE]` holds.
- [ ] **Reviewer-adjudicated (NOT gate-enforced)**: each of the 6 zero-edge relations is described by its
  correct emission status per research.md D3 (`vocabulary`/`refines`/`delegates_to` = dormant everywhere;
  `enhances`/`overrides`/`replaces` = org-pack overlay, not active built-in), and the `applies`/`scope`
  descriptions each **name their edge-role** (1 vs 157), not merely differ. "Gates green" ≠ "wording accurate".
- [ ] `test_models.py` completeness gate converted to `==set(Relation)` + non-empty over all, green.
- [ ] `context/doctrine.md` extended as non-enforced prose; no edges rewired (C-006).
- [ ] ruff/mypy/terminology/markdownlint clean.

## Risks

- Misdescribing `enhances`/`overrides` as active built-in relations (they are overlay) — daphne's
  MEDIUM finding. Ground each in the verified emission status.

## Reviewer Guidance (reviewer-renata / opus)

Confirm the descriptions are adjudicated (distinct `applies` vs `scope`; honest dormancy/overlay
wording), the completeness gate is `==set(Relation)`, and no graph edge was touched.
