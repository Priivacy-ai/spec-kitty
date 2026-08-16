---
work_package_id: WP04
title: Retire shipped doctrine working-notes clusters (IC-02)
dependencies: []
requirement_refs:
- FR-001
- NFR-002
planning_base_branch: feat/docs-plans-tier3-closeout
merge_target_branch: feat/docs-plans-tier3-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/docs-plans-tier3-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-plans-tier3-closeout unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-docs-plans-closeout-and-doctrine-diagrams-01KZTK2J
base_commit: bb74c335aed2a342000014c848c3db600b787d39
created_at: '2026-08-12T17:23:40.864111+00:00'
subtasks:
- T016
- T017
- T018
- T019
history:
- at: '2026-08-12'
  note: Authored by /spec-kitty.tasks (post-plan-squad model). IC-02 doctrine fan-out; one HOLD-for-ruling item flagged. Post-tasks squad dropped the spurious WP01 dep. Cross-WP note - the durable doctrine-charter plan references 3 pages this WP retires; WP07 (owns the moved plan) reconciles those references.
agent_profile: curator-carla
authoritative_surface: docs/plans/doctrine/
create_intent: []
execution_mode: code_change
owned_files:
- docs/plans/doctrine/index.md
- docs/plans/doctrine/manifesto-tier-primary-drivers.md
- docs/plans/doctrine/manifesto-tier-verdict-and-handover.md
- docs/plans/doctrine/creed-and-values-design-as-proposed.md
- docs/plans/doctrine/creed-and-values-design-hardened.md
- docs/plans/doctrine/squad-reports/**
- docs/plans/doctrine/org-doctrine-layer-architecture-review.md
- docs/plans/doctrine/doctrine-inclusion-assessment.md
- docs/plans/doctrine/doctrine-migration-architecture-review.md
- docs/plans/doctrine/charter-path-resolution-gaps.md
- docs/plans/doctrine/doctrine-artifact-selection-preflight.md
- docs/plans/doctrine/runtime-charter-doctrine-boundary.md
- docs/plans/doctrine/wp-prompt-governance-atdd-findings.md
- docs/plans/doctrine/mission-b-proposed-scope.md
- docs/plans/doctrine/391-doctrine-usage-test.md
- docs/plans/doctrine/delivery-reachability-wiring-table.md
- docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md
- docs/plans/doctrine/3179-public-api-surface-scoping.md
- docs/plans/doctrine/next-slice-wheel-mission-types-public-api-research.md
- docs/plans/doctrine/built-in-doctrine-repo-coupling-audit.md
- docs/plans/doctrine/charter-activation-reachability-assessment.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load curator-carla
```

Apply its initialization, boundaries, directives, and tactics. Then read this WP, `spec.md` (FR-001, NFR-002), `plan.md` (IC-02), `research.md` (D2).

## Objective

Retire the shipped/superseded doctrine working-note clusters by flipping each page's `doc_status` to `deprecated` in place (content preserved) with a shipped/superseded-evidence citation, and reconcile `doctrine/index.md`. **One item is a HOLD-for-ruling — do NOT flip it.**

## Context — retire mechanism

Same mechanism as the mission's other retire WPs: per-page `doc_status: deprecated` + a one-line retirement banner citing the evidence; never delete; do **not** touch top-level `docs/plans/index.md` (IC-04 owns it) — only `doctrine/index.md`.

**DO-NOT-TOUCH (keep, outside owned_files):**
- **AUTHORITY docs:** `doctrine/foundational-values-and-creed.md`, `doctrine/manifesto-program-delivery-sequence.md` (still the live roadmap — only Mission A of the 5-mission split merged; B1/B2/C/D are spec-only).
- `doctrine/charter-sole-door-deferred-issues.md` (relocated by PR #3324 — the brief forbids sweeping it).
- `doctrine/test_quality/` ×3 — input for the **unmerged** Mission C (#2935/#2934); design not shipped.
- Sidecars `doctrine/_ammerse-*.json` (3) + `doctrine/_reproduce_matrix_findings.py` — no frontmatter; leave as-is.

### Subtask T016 — Creed/manifesto RECORD + EVIDENCE (superseded by AUTHORITY doc)

Supersession is by the canonical creed AUTHORITY doc (`foundational-values-and-creed.md`), not a merged mission — cite the in-file "RECORD/SUPERSEDED" banners, no `gh` needed.
- `manifesto-tier-primary-drivers.md` (draft — in-file "SUPERSEDED IN PART — mechanism REJECTED").
- `manifesto-tier-verdict-and-handover.md` (draft).
- `creed-and-values-design-as-proposed.md`, `creed-and-values-design-hardened.md` (draft — hardened self-labels "RECORD — superseded by foundational-values-and-creed.md").
- `squad-reports/**` (index + architect + connascence-matrix-measurement + doctrine-curator + implementer + reviewer + review-round-2026-07-26; all draft) — evidence base for the superseded hardened design.

Cite `foundational-values-and-creed.md` as the superseding authority in each banner.

### Subtask T017 — Org-layering blueprint reviews (shipped programme)

Evidence: the org-doctrine-layer three-layer model shipped ("all 8 layer-rule tests pass"), PRs **#305/#348**, drivers **#832/#883/#1013/#391**.
- `org-doctrine-layer-architecture-review.md`, `doctrine-inclusion-assessment.md`, `doctrine-migration-architecture-review.md`, `charter-path-resolution-gaps.md`, `doctrine-artifact-selection-preflight.md`, `runtime-charter-doctrine-boundary.md`, `wp-prompt-governance-atdd-findings.md`, `mission-b-proposed-scope.md`, `391-doctrine-usage-test.md` (9, draft).

**HOLD — do NOT flip:** `doctrine/layered-doctrine-resolution-design.md` (draft, "approved for mission planning 2026-05-15"). It reads as a possibly-durable canonical reference architecture. Leave `doc_status` unchanged; add a one-line note in this WP's activity log: `HOLD: layered-doctrine-resolution-design.md — operator ruling needed (durable-exempt vs retire).` It is intentionally NOT in `owned_files`.

### Subtask T018 — Reachability / relocation / public-API scoping (fed merged missions)

Evidence = merged missions (each carries RetrospectiveCaptured):
- `delivery-reachability-wiring-table.md` (active) — `doctrine-delivery-reachability-01KYMXD6` (15 WPs done).
- `missions-reader-inventory-01KZ6G6H.md` (active) — `doctrine-consumer-surface-missions-extraction-01KZ6G6H`.
- `3179-public-api-surface-scoping.md` + `next-slice-wheel-mission-types-public-api-research.md` (active) — `doctrine-public-api-surface-01KZPDSR`. Evidence: **#3179** (+ #3101/#3176/#3182).
- `built-in-doctrine-repo-coupling-audit.md` (active) — relocation shipped via 01KZ6G6H.
- `charter-activation-reachability-assessment.md` (active) — landing pass for PR **#3007** (#3009); superseded by the delivery-reachability table.

### Subtask T019 — Reconcile doctrine/index.md + verify

1. Update `doctrine/index.md` to present the retired clusters as retired (keep entries, mark status). Leave the AUTHORITY docs, `test_quality/`, and the HOLD item listed as live.
2. Run `PWHEADLESS=1 python -m pytest tests/docs/test_docs_structural_lint.py tests/docs/test_related_validator.py -q` + `pytest tests/architectural/test_no_legacy_terminology.py -q` — green.
3. Confirm zero deletions and that the HOLD item's `doc_status` is unchanged.

## Branch Strategy

Planning/base branch: `feat/docs-plans-tier3-closeout`. Merge target: `feat/docs-plans-tier3-closeout`. Worktrees per lane from `lanes.json`.

## Definition of Done

- Listed clusters carry `doc_status: deprecated` + an evidence banner whose citation **resolves** to a real merged `kitty-specs/<mission>/` dir / PR / the AUTHORITY creed doc (not merely present); no deletions.
- **Cross-WP hand-off recorded:** `charter-activation-reachability-assessment.md`, `runtime-charter-doctrine-boundary.md`, and `next-slice-wheel-mission-types-public-api-research.md` are retired here **and** are referenced by the durable `doctrine-charter-domain-plan.md` — note in the activity log that WP07 must reframe/drop those references so the durable throughline does not route readers into retired notes (US1 trust goal).
- `layered-doctrine-resolution-design.md` left untouched + HOLD noted in activity log.
- AUTHORITY docs, `charter-sole-door-deferred-issues.md`, `test_quality/`, and JSON sidecars untouched.
- `doctrine/index.md` reconciled; docs lint + related + terminology green.

## Reviewer guidance

- Verify each merged-mission citation resolves to a real `kitty-specs/<mission>/` dir (RetrospectiveCaptured where claimed).
- Verify the creed RECORD banners cite the AUTHORITY doc, and that the AUTHORITY docs themselves were NOT flipped.
- Confirm the HOLD item is untouched and surfaced for operator ruling.
