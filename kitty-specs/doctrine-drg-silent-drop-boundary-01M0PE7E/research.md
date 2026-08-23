# Phase 0 Research — Doctrine DRG Silent-Drop Boundary Fix

All clarifications are resolved; no open `[NEEDS CLARIFICATION]`. Detailed
evidence lives in [`research/context-sources-drg-projection.md`](./research/context-sources-drg-projection.md)
(3-agent squad + convention round). This file records the decisions.

## Decision 1 — #3608: derive, don't copy

- **Decision**: Replace the hand-maintained `_DRG_NODE_KINDS` frozenset
  (`src/charter/synthesizer/topic_resolver.py:37`) with a set derived from
  `NodeKind` (`frozenset(k.value for k in NodeKind)`), and add a drift-guard test
  asserting exact set equality.
- **Rationale**: The copy has drifted 6 kinds (`anti_pattern`, `asset`,
  `glossary`, `glossary_pack`, `mission_step_contract`, `template`), silently
  dropping legitimate DRG-URN resolution at `topic_resolver.py:236`. `mission_type`
  was hand-patched since the ticket (whack-a-copy proof). Derivation prevents drift;
  the guard catches any residual copy that survives.
- **Alternatives considered**: keep the copy + guard only (rejected — a guard
  catches drift after it lands; derivation prevents it). Verify the URN membership
  keys on the enum *value* (the resolution gate compares against values), so the
  derivation uses `.value`.

## Decision 2 — #3629 part 1: consolidate on `*-references`, remove `context-sources.*`

- **Decision**: DM-01M0PEAQ5G1VDR3CSJSV51SD8Y — full consolidation. Remove all
  `context-sources.*` fields; migrate authored artefact refs onto the top-level
  `*-references` surface; drop `additional`/`doctrine-layers` (no edge shape);
  extractor projects `agent_profile` edges from `*-references`.
- **Rationale**: The renderer that delivers profile text to a dispatched agent
  (`profile_sections.py`) reads `*-references`, not `context-sources.*`.
  `context-sources.*` is a redundant, mostly-inert second surface (5 of 6 fields
  never read; the object attribute never read at all). The canonical
  DRG-provisioned home already exists; the honest move is cleanup.
- **Alternatives considered**: wire `context-sources.*` into edges (rejected —
  preserves duplication); remove dead fields but keep `context-sources.directives`
  (rejected — leaves the two-surface split). Operator chose full consolidation.
- **Blast-radius note**: 25 shipped profiles carry `context-sources.*`; migration
  must preserve every authored artefact reference (C-006) and drop only the
  non-artefact fields.

## Decision 3 — #3629 part 2: already fixed, verify + close

- **Decision**: Do not re-implement. Verify `assert_governance_scope_edges_resolve`
  (`extractor.py:1406`, commit `d8beee2761`, wired `:1574`, tested
  `test_extractor.py:1608-1653`) and confirm the **org-tier** governance-profile
  path is equally covered; add a targeted org-tier test/guard only if a gap exists.
- **Rationale**: The built-in guard fails loud on unresolved `selected_*` targets
  and is tested. The only open question is org-tier parity, which overlaps #3530.
- **Alternatives considered**: rebuild the guard (rejected — already present + tested).

## Decision 4 — #3530 / operator: fix the `org_roots=` seam, verify chain on spec-kitty-internal

- **Decision**: Fix `load_validated_graph`'s `org_roots=` seam
  (`_drg_helpers.py:138-182`) to fold `drg/fragment.yaml` per root and stop
  suppressing the "no graph" warning when a fragment exists; ensure the executor
  (`executor.py:362`) and `action_doctrine_bundle.py:192` consume org fragments.
  Then verify built-in + spec-kitty-internal chain delivery via that seam and a
  misconfigured-variant fail-loud, and close #3530.
- **Rationale**: `packs/internal/` is already structurally conformant (plural
  kinds + `drg/fragment.yaml` are canonical org shape; `pack.yaml`/manifest
  deferred; validator green). The actual defect is a silent-drop at the `org_roots`
  seam — a new instance of the mission's own family. An existing test
  (`test_executor.py:878-916`) documents the degrade.
- **Alternatives considered**: ship a root `*.graph.yaml` in `packs/internal`
  (rejected — that is the built-in shape, would be a deliberate convention change
  requiring validator/ADR edits; org convention is the fragment). Fix only the two
  callers (viable, but the seam fix covers all `org_roots` callers with one change).

## Supply-chain

N/A — no dependency added, upgraded, or removed. No adversarial supply-chain
evidence pass required.

## Adversarial evidence

Per the operator's directive, this mission runs the **brownfield point-cut review
squad** at post-plan and post-tasks.

- **Post-plan squad (2026-08-23):** 4 profile-loaded delegates
  (architect-alphonso, doctrine-daphne, debugger-debbie, reviewer-renata). Verdict
  REQUEST-CHANGES; 15 findings, all **accepted** (2 with operator scope decisions).
  Full record + dispositions: [`research/post-plan-brownfield-squad.md`](./research/post-plan-brownfield-squad.md).
  Net effect on the plan: IC-4 approach inverted (F1), IC-2 re-scoped
  (F2–F6, +golden re-ledger), IC-3 expanded to implement org-tier fail-loud (F9,
  operator decision), IC-5 gains a 2nd org fixture (F10, operator decision),
  IC-1 drift-guard behaviour-pinned (F7), contracts sharpened (F11).
- **Post-tasks squad:** pending (runs after `/spec-kitty.tasks`).
