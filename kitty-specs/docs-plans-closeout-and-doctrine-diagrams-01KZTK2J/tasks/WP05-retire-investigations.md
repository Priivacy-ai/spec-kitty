---
work_package_id: WP05
title: Retire shipped investigations records (evidence-gated, gh-verified) (IC-02)
dependencies: []
requirement_refs:
- FR-001
- NFR-002
planning_base_branch: feat/docs-plans-tier3-closeout
merge_target_branch: feat/docs-plans-tier3-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/docs-plans-tier3-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-plans-tier3-closeout unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-docs-plans-closeout-and-doctrine-diagrams-01KZTK2J
base_commit: 198a8dbca21911072cd21626b9fd52482225fbae
created_at: '2026-08-12T17:24:04.904467+00:00'
subtasks:
- T020
- T021
- T022
- T023
history:
- at: '2026-08-12'
  note: Authored by /spec-kitty.tasks (post-plan-squad model). IC-02 investigations fan-out; 3 moderate-certainty items require a gh issue view gate. Post-tasks squad dropped the spurious WP01 dep and hardened the gh gate (closed != shipped; reviewer re-runs gh).
agent_profile: curator-carla
authoritative_surface: docs/plans/investigations/
create_intent: []
execution_mode: code_change
owned_files:
- docs/plans/investigations/index.md
- docs/plans/investigations/mission-type-step-model-unification.md
- docs/plans/investigations/2026-04-14-windows-compatibility-hardening-mission-review.md
- docs/plans/investigations/mission-next-compatibility.md
- docs/plans/investigations/model-first-schema-generation.md
- docs/plans/investigations/2684-task-move-cluster-scoping.md
- docs/plans/investigations/2684-task-move-cluster-spec.md
- docs/plans/investigations/wp-runtime-state-eviction-scope.md
- docs/plans/investigations/issue-1040-scope-assessment.md
- docs/plans/investigations/issue-1111-analysis.md
- docs/plans/investigations/loop-friction-fastfollow-spec.md
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

Retire the shipped `investigations/` records (per-page `doc_status: deprecated` + evidence banner, content preserved), reconcile `investigations/index.md`, and **evidence-gate the moderate-certainty items behind a `gh issue view` check** before flipping.

## Context — retire mechanism + gh gate

- Same mechanism: per-page `doc_status: deprecated` + one-line banner citing the merged ADR/mission; never delete; do not touch top-level `docs/plans/index.md` (IC-04 owns it) — only `investigations/index.md`.
- **`gh` auth:** run `unset GITHUB_TOKEN` before any `gh` command (keyring auth).
- **DO-NOT-TOUCH (LIVE / unshipped — NOT in owned_files):** `write-path-topology-root-cause.md` (#3129, pre-spec, no mission), `review-artifact-write-integrity-3044.md` (#3044, pre-spec), `2497-external-observability-endpoints-assessment.md` (RFC #2497 OPEN), and the 6-file `wp-op-schema` corpus (`wp-op-schema-model.md`, `wp-op-schema-proposal.md`, `wp-op-schema-related-tickets.md`, `wp-op-schema-research/**`) — unbuilt schema still being pursued.

### Subtask T020 — High-confidence shipped records (merged ADR / mission)

Flip to `deprecated` with the cited evidence:
- `mission-type-step-model-unification.md` (active) — ADR `2026-07-16-2` merged; missions `templates-as-config-01KXMS1G` merged. Evidence: **#2658**.
- `2026-04-14-windows-compatibility-hardening-mission-review.md` (draft) — mission `windows-compatibility-hardening-01KP5R6K` squash-merged (`89bab26e5`). Evidence: mission 01KP5R6K.
- `mission-next-compatibility.md` (draft) — self-declared HISTORICAL, superseded by `shared-package-boundary-cutover-01KQ22DS` (ADR 2026-04-25-1). Evidence: ADR 2026-04-25-1.
- `model-first-schema-generation.md` (draft) — shipped `scripts/generate_schemas.py` pipeline. Evidence: the generate_schemas pipeline.

### Subtask T021 — 2684 runtime-state eviction cluster (merged)

- `2684-task-move-cluster-scoping.md` + `2684-task-move-cluster-spec.md` (active) and `wp-runtime-state-eviction-scope.md` (proposal) — ADR `2026-07-19-1` merged; mission `wp-runtime-state-eviction-01KXWN13` merged (impl `dfe6b2ead`). Evidence: **#2684** (+ #2093/#2816). Flip all three to `deprecated`.

### Subtask T022 — Moderate-certainty items — GATE on `gh issue view` first

For each below, run `unset GITHUB_TOKEN && gh issue view <n> --json state,title,closedAt,stateReason` (or `gh pr view`) and **only flip if the design has demonstrably SHIPPED**. **Closed ≠ shipped:** an issue closed as `not planned` / wontfix / duplicate must NOT trigger a flip. Record in the activity log, per item, the observed `state` + `stateReason` **and a one-line reason why that closure implies the design shipped** (e.g. "closed by merged PR #X" / "delivered by mission Y"). If still open, or closed-but-not-shipped, leave the page live and record `NOT-RETIREABLE (issue #<n>: <state/reason>)`:
- `issue-1040-scope-assessment.md` (draft) — verify **#1040** shipped.
- `issue-1111-analysis.md` (draft) — verify **#1111** shipped (Epic 1111 slice-landing).
- `loop-friction-fastfollow-spec.md` (active) — verify **#2581** (+ #2577/#2573) landed (`ec3e2c528` / `266d757f5` / `loop-reliability-…-01KXWWD6`).

Record each gate decision (flipped vs held, with the observed issue state) in the activity log.

### Subtask T023 — Reconcile investigations/index.md + verify

1. Update `investigations/index.md` to present the retired records as retired (keep entries; mark status). Leave the LIVE/unshipped corpus and any gate-held item as live.
2. `PWHEADLESS=1 python -m pytest tests/docs/test_docs_structural_lint.py tests/docs/test_related_validator.py -q` + `pytest tests/architectural/test_no_legacy_terminology.py -q` — green.
3. Confirm zero deletions.

## Branch Strategy

Planning/base branch: `feat/docs-plans-tier3-closeout`. Merge target: `feat/docs-plans-tier3-closeout`. Worktrees per lane from `lanes.json`.

## Definition of Done

- T020/T021 records flipped to `deprecated` with evidence banners; no deletions.
- Each T022 item carries a recorded `gh issue view` gate decision including `state`+`stateReason` **and the shipped-justification** (flipped only if demonstrably shipped, not merely closed; held with reason otherwise).
- LIVE/unshipped corpus (write-path-topology, review-artifact-write-integrity, 2497, wp-op-schema) untouched.
- `investigations/index.md` reconciled; docs lint + related + terminology green.

## Reviewer guidance

- **Independently re-run** `unset GITHUB_TOKEN && gh issue view <n> --json state,closedAt,stateReason` for each T022 item (#1040, #1111, #2581); confirm the recorded state matches and that closure genuinely means *shipped* (a `not planned`/duplicate closure that was flipped is a reject). Do not trust the activity-log text alone.
- Verify the LIVE corpus is untouched and top-level index.md was not edited.
