---
work_package_id: WP03
title: Retire shipped engineering-notes clusters (auto trio + evidence-gated) (IC-02)
dependencies: []
requirement_refs:
- FR-001
- NFR-002
planning_base_branch: feat/docs-plans-tier3-closeout
merge_target_branch: feat/docs-plans-tier3-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/docs-plans-tier3-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-plans-tier3-closeout unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-docs-plans-closeout-and-doctrine-diagrams-01KZTK2J
base_commit: b4278ad6d11b50fbdec8d3be3cc95275107e330e
created_at: '2026-08-12T17:15:57.250407+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
history:
- at: '2026-08-12'
  note: Authored by /spec-kitty.tasks (post-plan-squad model). IC-02 engineering-notes fan-out; folds the auto-retire trio (shared engineering-notes/index.md owner). Post-tasks squad dropped the spurious WP01 dep (retire writes `deprecated`, already in the enum — does not consume `durable`).
agent_profile: curator-carla
authoritative_surface: docs/plans/engineering-notes/
create_intent: []
execution_mode: code_change
owned_files:
- docs/plans/engineering-notes/index.md
- docs/plans/engineering-notes/runtime_and_state_overhaul/**
- docs/plans/engineering-notes/naming-identity-ssot-strangler/**
- docs/plans/engineering-notes/3-2-x-goal-corroboration/**
- docs/plans/engineering-notes/3-2-0-training-bugs-2007/**
- docs/plans/engineering-notes/3-2-3-surface-resolution-cluster/**
- docs/plans/engineering-notes/triage/**
- docs/plans/engineering-notes/coord-splitbrain-rootcause.md
- docs/plans/engineering-notes/coord-trust-mission-scope.md
- docs/plans/engineering-notes/2173-infra-logic-separation/**
- docs/plans/engineering-notes/2342-retro-summary-nfr/**
- docs/plans/engineering-notes/context-factory-readwrite-symmetry/**
- docs/plans/engineering-notes/2841-residual-2917-mission-scope.md
- docs/plans/engineering-notes/2917-runtime-state-birth-cutover-research.md
- docs/plans/engineering-notes/883-mission-type-authority-brief.md
- docs/plans/engineering-notes/883-research-synthesis.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load curator-carla
```

Apply its initialization, boundaries, directives, and tactics. Then read this WP, `spec.md` (FR-001, NFR-002, US1), `plan.md` (IC-02), and `research.md` (D2).

## Objective

Retire the shipped/superseded engineering-notes working-note clusters by flipping each contained page's `doc_status` to `deprecated` **in place** (content preserved, never deleted) and recording a shipped-evidence citation, then reconcile `engineering-notes/index.md` so retired clusters are no longer presented as live.

## Context — retire mechanism (applies to every subtask)

For each cluster:
1. In **every** `.md` in the cluster, set frontmatter `doc_status: deprecated` (many are currently `draft`; a couple are `active`). Do **not** change `updated`, `title`, `description`, or body content.
2. Add a one-line **retirement banner** at the top of the cluster's `README.md`/`index.md` (or, for single-file clusters, in the file body under the H1): `> **Retired (deprecated).** Design shipped/superseded via <evidence>. Preserved as a historical record.` — with the evidence citation from the subtask.
3. Do **NOT** edit `docs/plans/index.md` (top-level) — the top-level index reconciliation is owned by the IC-04 migration WP (shared-file merge). This WP only touches `engineering-notes/index.md`.
4. **Never delete a file.** Retirement = status flip + banner, nothing removed.

**Do NOT touch these NOT-RETIREABLE / already-retired engineering-notes paths** (they are live, durable, or already deprecated): `architectural-review/`, `finding/`, `reflections/`, `2026-07-18-…-field-report.md`, `2026-07-19-…-field-report.md`, `common-docs-section-audit.md`, `agent-knowledge-canonical-homes.md`, `651-docs-consolidation/`, `architecture-audits/`, `drg-completeness-2843-research.md`, `3.2.6-maintenance-brief.md`, `mission-notes/`, `01KSMG8Y-closeout/`, `2026-06-12-coordination-topology-stabilization.md`, `01KYW895-verification-evidence.md`, and any file already `deprecated`/`superseded`/`closeout`. They are outside `owned_files` by design.

### Subtask T010 — Auto-retire trio (evidence: open-core delivery plan)

Retire (evidence = `docs/plans/3-2-x-open-core-delivery-plan.md`, no `gh` needed):
- `runtime_and_state_overhaul/` (19 files, draft) — shipped as execution-context unification (#1619; open-core plan line ~140).
- `naming-identity-ssot-strangler/` — identity-primitive lower-layer move (open-core plan §naming/identity).
- `3-2-x-goal-corroboration/` — goal-corroboration research folded into the open-core plan.

Cite the open-core plan section in each banner.

### Subtask T011 — Version-tagged bug/surface research (shipped releases)

- `3-2-0-training-bugs-2007/` (7, draft) — 3.2.0 training-bug repro/synthesis; 3.2.0 shipped (now 3.2.6rc1). Evidence: **#2007**.
- `3-2-3-surface-resolution-cluster/` (4, draft) — 3.2.3 coord surface-resolution research; 3.2.3 shipped. Evidence: 3.2.3 release / `fix/3.2.3-coord-surface-regressions`.

### Subtask T012 — Mission-scoped closeout records (merged missions)

- `triage/` (5, draft) — closeout for `test-stabilization-and-debt-pass-01KSF9HJ` (merged). Evidence: mission **01KSF9HJ**.
- `coord-splitbrain-rootcause.md` + `coord-trust-mission-scope.md` (2, draft) — delivered by `coord-write-placement-closure-01KYCF83`. Evidence: **#2841**.
- `2173-infra-logic-separation/` (draft) — Phase 1 shipped via `#2531` (`runtime-bridge-degod-01KX8M1C`). Evidence: **#2173 / #2531**; note Phase 2 (#1619) was deferred in the banner.

### Subtask T013 — Verdict / design-refinement records

- `2342-retro-summary-nfr/` (2, draft) — closed verdict (hardware variance, test quarantined). Evidence: **#2342**.
- `context-factory-readwrite-symmetry/` (draft) — informed `read-path-error-fidelity-adoption-01KV8NPC` (merged); write-side #1716/#1878 deferred. Evidence: mission 01KV8NPC (note deferred follow-on).

### Subtask T014 — Secondary (`active`) clusters whose scoped mission merged

- `2841-residual-2917-mission-scope.md` + `2917-runtime-state-birth-cutover-research.md` (2, active) — delivered by `runtime-state-birth-cutover-all-paths-01KYH654`. Evidence: **#2917**.
- `883-mission-type-authority-brief.md` + `883-research-synthesis.md` (2, active) — superseded by ADR `2026-07-14-2` + canonical `docs/architecture/mission-type-resolution.md`. Evidence: **#883**.

### Subtask T015 — Reconcile engineering-notes/index.md + verify

1. Update `docs/plans/engineering-notes/index.md`: move/annotate the retired clusters so they are listed as **retired (deprecated)**, not live. Keep entries (do not delete); mark status.
2. Run `PWHEADLESS=1 python -m pytest tests/docs/test_docs_structural_lint.py tests/docs/test_related_validator.py -q` and `pytest tests/architectural/test_no_legacy_terminology.py -q` — green (`deprecated` is a valid `doc_status`; no broken `related:`; no terminology regression).
3. Confirm **zero** files deleted (`git diff --stat` shows only frontmatter/banner/index changes).

## Branch Strategy

Planning/base branch: `feat/docs-plans-tier3-closeout`. Final merge target: `feat/docs-plans-tier3-closeout`. Worktrees per computed lane from `lanes.json`.

## Definition of Done

- Every listed cluster's pages carry `doc_status: deprecated` + a retirement banner whose evidence citation **resolves to a real merged `kitty-specs/<mission>/` dir, merged PR, or the named open-core-plan section** (not merely present — resolvable); **no content deleted**.
- `engineering-notes/index.md` presents retired clusters as retired, not live.
- No NOT-RETIREABLE path touched; top-level `docs/plans/index.md` untouched (IC-04 owns it).
- Docs structural-lint + related-validator + terminology guard green.

## Reviewer guidance

- Spot-check that each banner's evidence actually corresponds to a merged mission dir / shipped release (open the cited `kitty-specs/<mission>/` or confirm the release). A banner with no verifiable evidence is a reject.
- Confirm the auto-trio cites the open-core plan (no fabricated issue).
- Confirm zero deletions and that NOT-RETIREABLE living notes (architectural-review/, finding/, reflections/, field-reports) were left `active`/untouched.
