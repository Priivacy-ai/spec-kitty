---
work_package_id: WP05
title: Doc parity surface restructure
dependencies:
- WP04
requirement_refs:
- C-006
- FR-006
- NFR-003
planning_base_branch: doctrine/drg-completeness-2843
merge_target_branch: doctrine/drg-completeness-2843
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-completeness-2843. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-completeness-2843 unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
history:
- timestamp: '2026-07-22T08:11:16Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: docs/architecture/doctrine-relationships.md
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/architecture/doctrine-relationships.md
- tests/doctrine/test_relation_doc_parity.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `doctrine-daphne` profile via the `/ad-hoc-profile-load`
skill. Adopt its doctrine-curation identity and init declaration. This WP is **verbatim-precision**
work — the parity test enforces exact (whitespace-normalized) content equality.

## Objective

Bring the single parity-enforced surface `docs/architecture/doctrine-relationships.md` into lockstep
with `RELATION_DESCRIPTIONS` (authored in WP04) and widen the parity test to all 15 relations. This is
a **restructure**, not a constant bump (research.md D3): the content-equality comparator requires a
dedicated `### …` heading per relation whose body equals the registry entry, and it raises
`LookupError` on a missing heading.

Read: `contracts/relation-registry-contract.md`, `research.md` D3. **Depends on WP04** (descriptions
must exist first).

## Subtasks

### T019 — Restructure the doc into 15 per-relation sections (WP05)

In `docs/architecture/doctrine-relationships.md`:
- Add dedicated `### …` sections for the ~7 relations with no heading today (`requires, suggests,
  applies, scope, vocabulary, instantiates, refines`).
- **Split** the grouped `### Augmentation — enhances, overrides (and legacy replaces)` heading
  (~`:62`) into three separate per-relation sections (the comparator extracts one shared body → three
  distinct registry strings cannot all content-equal a shared heading).
- **Trim** the multi-paragraph Lineage (`:28`) and Delegation (`:51`) bodies down to exactly their
  registry description (re-home any extra prose elsewhere in the doc if worth keeping).
- Each section body must equal `RELATION_DESCRIPTIONS[relation]` (whitespace-normalized).

### T020 — Widen `_SCOPED_RELATIONS` 3→15 (WP05)

In `tests/doctrine/test_relation_doc_parity.py`, widen `_SCOPED_RELATIONS` from the 3 tension
relations to all 15.

### T021 — Update stale non-goal docstrings (WP05)

The test's docstring (`test_relation_doc_parity.py:5-8`, `:39-45`) and the doc's "Tension vocabulary"
prose assert the other twelve are "out of scope / a follow-up." This mission IS that follow-up —
update both so they document what is now enforced.

### T022 — Green the parity gate (WP05)

`uv run pytest tests/doctrine/test_relation_doc_parity.py -q` (all 15 scoped, green) +
`uv run pytest tests/architectural/test_no_legacy_terminology.py -q` +
`npx markdownlint-cli2@0.18.1 --config .markdownlint-cli2.jsonc docs/architecture/doctrine-relationships.md`.

## Branch Strategy

Generated on **`doctrine/drg-completeness-2843`**; merges back into it. Worktrees per lane from
`lanes.json`. Depends on WP04.

## Definition of Done

- [ ] 15 per-relation `###` sections; grouped heading split; Lineage/Delegation prose trimmed to registry.
- [ ] `_SCOPED_RELATIONS` = 15; `test_relation_doc_parity.py` green.
- [ ] Stale non-goal docstrings updated; terminology + markdownlint clean; no edges touched (C-006).

## Risks

- A missing per-relation heading raises `LookupError` (test errors, not just fails) — every one of the
  15 needs its own section. Verbatim body equality is unforgiving; copy from the registry exactly.

## Reviewer Guidance (reviewer-renata / opus)

Confirm each of the 15 relations has its own heading with body == registry (no grouped heading
survives), the widened `_SCOPED_RELATIONS` is 15, and the stale "out of scope" prose is gone.
