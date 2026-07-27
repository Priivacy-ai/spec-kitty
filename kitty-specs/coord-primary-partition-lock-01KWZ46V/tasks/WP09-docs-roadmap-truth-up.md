---
work_package_id: WP09
title: Docs & roadmap truth-up
dependencies: []
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: design/coord-primary-partition-lock
merge_target_branch: design/coord-primary-partition-lock
branch_strategy: Planning artifacts for this mission were generated on design/coord-primary-partition-lock. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-primary-partition-lock unless the human explicitly redirects the landing branch.
subtasks:
- T043
- T044
- T045
- T046
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1352030"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: curator-carla
authoritative_surface: docs/release-goals/3.2.x.md
create_intent: []
execution_mode: code_change
owned_files:
- docs/release-goals/3.2.x.md
- AGENTS.md
- CLAUDE.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `curator-carla` via `/ad-hoc-profile-load`. Read `spec.md` (FR-010), `plan.md` (IC-07),
`research.md` (D2, D10). Parallel — no dependency. Implement via
`spec-kitty agent action implement WP09 --agent claude`.

## Objective

Truth-up the docs to the shipped + operator-decided reality: retire the "planning happens in main"
language, correct #1716's stale decision, and rewrite the roadmap so the **whole** #1878 write-side
strangler sits in 3.2.x.

## Subtasks

### T043 — Retire "planning happens in main"
- In `AGENTS.md` and `CLAUDE.md`, replace "planning happens in the main repo checkout" /
  "planning artifacts committed to main" with the canonical partition: coord = lifecycle
  (status/notes/trace/issue-matrix/move-task); primary = stable planning (spec/plan/WP outlines);
  no-coordination topology → all to primary. Frame invocation as "planning commands may be invoked
  from the repo root" (not "planning lives on main").

### T044 — Roadmap: whole #1878 → 3.2.x (operator decision)
- Rewrite `docs/release-goals/3.2.x.md`: move the **entire** #1878 write-side strangler — placement-routing
  AND commit/protected-branch durability — out of the 3.3.x non-goals and into 3.2.x/G2. (Per operator
  decision; supersedes the doc's current split. Research D10.)

### T045 — Update #1716 issue body (manual)
- Update GitHub issue #1716's body to reflect the superseding planning-on-primary decision (the original
  "Locked Architecture Decision" is stale). This is a **manual `gh` step** (external to the repo) —
  `unset GITHUB_TOKEN && gh issue edit 1716 --repo Priivacy-ai/spec-kitty --body-file <file>`; record it done in the WP.

### T046 — Inventory prose + guards
- Correct any touched prose to the 2×2 topology + 14-kind reality, and the `resolve_feature_dir_for_mission`
  count (~**71** live sites, not "53" — read-site sweep tracked in **#2453**). Before pushing, run the
  terminology guard (`pytest tests/architectural/test_no_legacy_terminology.py`) and the docs-freshness
  check; both must pass.

## Campsite (Sonar)

Markdown/prose — Python Sonar rules do not apply. No campsite. Watch the **terminology guard** and
**docs-freshness** gates instead.

## Branch Strategy

Base / merge target `design/coord-primary-partition-lock`. Worktree per computed lane. No dependency —
parallel with all other WPs.

## Definition of Done

- No doc states planning artifacts live on `main` for coord missions.
- Roadmap places the whole #1878 write-side strangler in 3.2.x/G2.
- #1716 issue body updated (manual step recorded).
- Terminology guard + docs-freshness green.

## Risks & Reviewer guidance

- **Terminology canon**: use "Mission" not "feature"; run the guard before pushing (CI-only gate otherwise).
- The roadmap edit follows the operator decision (whole strangler → 3.2.x), NOT the narrower "placement-only" reading — reviewer confirms the durability line moved too.
- Do not hand-edit generated docs inventory — use the freshness tooling if it flags.

## Activity Log

- 2026-07-07T21:59:29Z – claude:sonnet:curator-carla:implementer – shell_pid=1305696 – Assigned agent via action command
- 2026-07-07T22:10:52Z – claude:sonnet:curator-carla:implementer – shell_pid=1305696 – Ready for review; terminology guard green; #1716 body updated
- 2026-07-07T22:11:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=1352030 – Started review via action command
- 2026-07-07T22:21:01Z – user – shell_pid=1352030 – Review passed. T043 AGENTS.md/CLAUDE.md(symlink) retire planning-on-main -> canonical coord=lifecycle/primary=stable-planning/no-coord->primary; T044 3.2.x.md moves WHOLE #1878 strangler (placement-routing AND commit/protected-branch durability) into G2 out of 3.3.x non-goals; out-of-map 3.3.x.md edit=justified rationale-backed leeway (unowned elsewhere; consistent+cross-referenced); T045 #1716 body SUPERSEDED note verified via gh; gates green: terminology guard 3 passed, docs-freshness exit=0 errors=0. Docs-only WP: code anti-patterns N/A; no frozen files. Issue-matrix resolved to unblock per-WP approval (in-mission for mission-fixed issues; verified-already-fixed #2106/#2113; deferred-with-followup #1619/#2429).
