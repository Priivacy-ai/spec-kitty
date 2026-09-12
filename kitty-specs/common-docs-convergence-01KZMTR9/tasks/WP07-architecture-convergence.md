---
work_package_id: WP07
title: docs/architecture convergence (version-shadow collapse + rehome + authority doc)
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
- FR-007
- FR-008
- FR-012
- FR-013
- FR-014
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: docs/architecture/
create_intent: []
execution_mode: code_change
owned_files:
- docs/architecture/**
- docs/status-model.md
- docs/trail-model.md
- docs/host-surface-parity.md
- docs/doctrine/**
- spec-kitty-mission-workflow.md
- src/doctrine/templates/diagrams/README.md
- scripts/lint_canonical_producers.py
- tests/status/test_producer_conformance.py
- tests/docs/test_no_retrospect_preview.py
- .github/workflows/canonical-producer-lint.yml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load curator-carla
```

## Objective
Collapse the `architecture/` per-version README shadow into one living design (closes #2215), rehome the
homeless explanation files + doctrine explanation, and move the canonical workflow authority doc with its
code/CI refs. See [plan.md](../plan.md) IC-05, [occurrence_map.yaml](../occurrence_map.yaml), post-plan landmine C2.

## Subtasks
- **T020** — Fold the living design into one canonical `architecture/index.md`. **FIRST** repoint the
  shipped `src/doctrine/templates/diagrams/README.md` anchors (`#usage-flow`, `#domain-breakdown`) that
  point at `README-2.x.md`. Produce the distilled era-history content from `README-1.x/2.x/3.x.md` as a
  handoff artifact for **WP08** (which owns `docs/adr/**` and authors it into `adr/<era>/` — do NOT write
  into `docs/adr/` from this WP), then delete the `architecture/README-*.x.md` source stubs. Record the
  source deletions in this WP's fragment.
- **T021** — Rehome `docs/status-model.md`, `docs/trail-model.md`, `docs/host-surface-parity.md` and the
  explanation half of `docs/doctrine/` (`doctrine-kinds.md`, `spdd-reasons.md`) into `architecture/`;
  update the enumerated test refs (`test_asset_howto`, `test_charter_context_spdd_reasons:290`).
- **T022** — Rehome `spec-kitty-mission-workflow.md` (a canonical-**authority** doc, NOT a user how-to) →
  `docs/architecture/`; update the 4 refs: `scripts/lint_canonical_producers.py:5,723,812`,
  `tests/status/test_producer_conformance.py:15`, `tests/docs/test_no_retrospect_preview.py:36`,
  `.github/workflows/canonical-producer-lint.yml:4`.
- **T023** — Ensure `architecture/index.md` is complete (this is the one curated-complete section — the
  extended lint checks it); kebab-case names; migrate `audience:`; **rewrite phase** (separately
  reviewed) with the NFR-009 fidelity ledger. Record all moves in this WP's fragment.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- Version shadow gone; one living `architecture/` with complete index; src/doctrine diagram anchors
  repointed BEFORE deletion; workflow authority doc moved with all 4 refs updated (canonical-producer
  lint + 2 tests green); audience migrated; rewrite ledgered. Fragment recorded.

## Risks
- The src/doctrine diagram README ships to consumers — broken anchors ship. Repoint first, verify.
- `docs/architecture/` moves interact with charter authority paths (`architecture/3.x/adr`, `architecture/adrs`
  are dead) — WP11 repairs those; coordinate.
