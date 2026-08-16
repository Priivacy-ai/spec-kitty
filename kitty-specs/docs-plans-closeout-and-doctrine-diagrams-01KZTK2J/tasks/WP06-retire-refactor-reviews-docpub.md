---
work_package_id: WP06
title: Retire shipped refactor + reviews + 3-2-doc-publication working notes (IC-02)
dependencies: []
requirement_refs:
- FR-001
- NFR-002
planning_base_branch: feat/docs-plans-tier3-closeout
merge_target_branch: feat/docs-plans-tier3-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/docs-plans-tier3-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-plans-tier3-closeout unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-docs-plans-closeout-and-doctrine-diagrams-01KZTK2J
base_commit: ae6c76802b04188641c50ccead569da8c8294b0a
created_at: '2026-08-12T17:21:54.841549+00:00'
subtasks:
- T024
- T025
- T026
- T027
history:
- at: '2026-08-12'
  note: Authored by /spec-kitty.tasks (post-plan-squad model). IC-02 refactor/reviews/doc-publication fan-out; one HOLD-for-ruling item. Post-tasks squad dropped the spurious WP01 dep.
agent_profile: curator-carla
authoritative_surface: docs/plans/3-2-doc-publication/
create_intent: []
execution_mode: code_change
owned_files:
- docs/plans/reviews/**
- docs/plans/3-2-doc-publication/**
- docs/plans/refactor/index.md
- docs/plans/refactor/slice-f-mission-debrief.md
- docs/plans/refactor/slice-f-gap-analysis.md
- docs/plans/refactor/epic-1111-slice-landing-plan.md
- docs/plans/refactor/tasks-py-degod-followup-mission-debrief.md
- docs/plans/refactor/wp04-resection-classification-audit.md
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

Retire the shipped working notes in `reviews/` (whole cluster), `3-2-doc-publication/` (mission 01KS4KSZ notes), and the shipped subset of `refactor/` — per-page `doc_status: deprecated` + evidence banner, content preserved. **`refactor/` is MIXED — do not bulk-flip it.** One `3-2-doc-publication` item is a HOLD-for-ruling.

## Context — retire mechanism

Same mechanism: per-page `doc_status: deprecated` + one-line banner; never delete; do not touch top-level `docs/plans/index.md` (IC-04 owns it) — only the three **section** indexes (`reviews/index.md`, `3-2-doc-publication/index.md`, `refactor/index.md`).

### Subtask T024 — reviews/ (whole cluster — PR #305 shipped)

All 5 pages are per-PR review artifacts for **PR #305** (`feature/agent-profile-implementation`); the agent-profile system shipped (`045-agent-profile-system`, #136/#1975). Flip to `deprecated` with evidence PR #305:
- `code-review-2026-03-25.md`, `pr305-review-resolution-plan.md`, `test-execution-report-pr305.md`, `test-plan-pr305.md`, `index.md` (the index page itself is a retired-cluster landing — mark it deprecated too or annotate it as a retired-cluster index; keep it as the section index).

### Subtask T025 — refactor/ (shipped subset ONLY)

Flip these 5 to `deprecated`:
- `slice-f-mission-debrief.md`, `slice-f-gap-analysis.md`, `epic-1111-slice-landing-plan.md` — Slice-F mission `01KRX5C8` merged (`2623a22db`), Epic **#1111**.
- `tasks-py-degod-followup-mission-debrief.md` (**active** → deprecated) — shipped as `tasks-py-degod-wave2-01KWH9EQ`, PR **#2308** (closed #2305/#2116).
- `wp04-resection-classification-audit.md` — #2054 re-section shipped in 3.2.3.

**DO-NOT-TOUCH (durable live program plan — correctly `active`, NOT in owned_files):** `refactor/degod-unshim-roadmap.md`, `refactor/degod-unshim-inventory.md` — open waves remain (#2291/#2293, WS4/WS6, Wave 3–4). `refactor/index.md` stays live (the dir retains the roadmap + inventory) — annotate the retired entries but keep the section index live.

### Subtask T026 — 3-2-doc-publication/ (mission 01KS4KSZ shipped) + HOLD

Mission `spec-kitty-3-2-docs-01KS4KSZ` finished (14/14 WPs done 2026-05-21); docs published (now 3.2.6). Flip these 8 to `deprecated` (evidence: mission 01KS4KSZ):
- `3-2-archive-migration-plan.md`, `3-2-cli-reference-audit-meta-issues.md`, `3-2-cli-reference-methodology.md`, `3-2-coord-merge-issue-hygiene-log.md`, `3-2-harness-research-method.md`, `3-2-navigation-plan.md`, `3-2-publication-checklist.md`, `3-2-information-architecture.md`.
- `index.md` — annotate as a retired-effort audit trail (mark deprecated or note retired).

**HOLD — do NOT flip:** `3-2-doc-publication/3-2-version-taxonomy.md` — its frontmatter asserts it is the **source of truth** for per-page version classification. Check for live inbound references first: `grep -rn "3-2-version-taxonomy" docs/ src/`. If anything live still cites it as the classification authority, leave it live (consider re-status `active`) and record `HOLD: 3-2-version-taxonomy.md — operator ruling (keep-as-authority vs retire); N live inbound refs found` in the activity log. It is intentionally NOT in `owned_files`.

### Subtask T027 — Reconcile 3 section indexes + verify

1. Update `reviews/index.md`, `3-2-doc-publication/index.md`, `refactor/index.md` to present retired clusters as retired (keep entries; mark status). Keep the `refactor` roadmap/inventory + the HOLD taxonomy doc listed as live.
2. `PWHEADLESS=1 python -m pytest tests/docs/test_docs_structural_lint.py tests/docs/test_related_validator.py -q` + `pytest tests/architectural/test_no_legacy_terminology.py -q` — green.
3. Confirm zero deletions and the HOLD/DO-NOT-TOUCH items are unchanged.

## Branch Strategy

Planning/base branch: `feat/docs-plans-tier3-closeout`. Merge target: `feat/docs-plans-tier3-closeout`. Worktrees per lane from `lanes.json`.

## Definition of Done

- reviews/ (5), the refactor shipped-subset (5), and 3-2-doc-publication (8) flipped to `deprecated` with evidence banners whose citations **resolve** (merged mission dir / PR #2308 / #305 / 3.2.3 release — not merely present); no deletions.
- `degod-unshim-roadmap.md` + `-inventory.md` left `active`; `3-2-version-taxonomy.md` left untouched + HOLD noted.
- Three section indexes reconciled; docs lint + related + terminology green.

## Reviewer guidance

- Verify refactor was NOT bulk-flipped (roadmap + inventory still active) and the HOLD taxonomy doc is untouched with its inbound-ref check recorded.
- Verify each evidence citation resolves (merged mission dir / PR #2308 / #305 / 3.2.3 release).
- Confirm top-level index.md untouched.
