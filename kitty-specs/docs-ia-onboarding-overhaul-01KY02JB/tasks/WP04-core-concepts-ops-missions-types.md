---
work_package_id: WP04
title: 'Core Concepts: Ops vs. Missions & Mission Types'
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
history: []
agent_profile: curator-carla
authoritative_surface: docs/context/ops-vs-missions.md
create_intent:
- docs/context/ops-vs-missions.md
- docs/context/mission-types.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/context/ops-vs-missions.md
- docs/context/mission-types.md
role: implementer
tags: []
shell_pid_created_at: "1784572324.709418"
agent: "claude:sonnet-5:curator-carla:reviewer"
shell_pid: "19963"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load curator-carla` (role: implementer). Then read, in order:
[spec.md](../spec.md) User Story 2 + FR-004/FR-005, [plan.md](../plan.md) §IC-03, and
[research.md](../research.md) items 7-8 for the ground-truth vocabulary already established.

## Objective

Author the two missing core-concept explanation pages that let a user who has finished their
first mission understand the tool's operating model: the distinction between a lightweight
ad-hoc Op and a full Mission, and the four available mission types. This content is currently
entirely absent from the docs site.

## Context

- **Ops vs. Missions** (spec.md Domain Language): an **Op** is "a lightweight, governed ad-hoc
  invocation via `spec-kitty dispatch` that does not create a mission." A **Mission** is "the
  canonical product term for a full spec-to-merge workflow unit." This page must ground the
  distinction in the real CLI/code (the `spec-kitty dispatch` command and profile-invocation
  flow), not restate the glossary definitions alone — give a concrete decision rule a user can
  apply.
- **Mission types**: this repository has exactly 4, each with its own `mission.yaml` under
  `src/specify_cli/missions/`: `software-dev`, `research`, `documentation`, `plan`. Do not
  invent a 5th or omit one — verify by listing that directory yourself.
- Both pages land in the end-user zone WP02 already established — check `docs/toc.yml` for
  where WP02 placed (or reserved space for) a "Core Concepts" group and link these pages there;
  if WP02 hasn't reserved a slot, add one under the end-user zone (small toc.yml addition is
  fine here since your `owned_files` doesn't include `toc.yml` — coordinate by checking if WP02
  already added placeholder entries; if not, note in this WP's Activity Log that `toc.yml` needs
  a follow-up addition rather than editing it yourself, since it's WP02's exclusive surface).

## Subtask guidance

- **T015 — Research the real Ops mechanism.** Read the `spec-kitty dispatch` command
  implementation and the "Op" / profile-invocation concept in the codebase (search for
  `dispatch`, `profile-invocation`, `Op` in `src/specify_cli/`). Confirm: what triggers an Op,
  what state (if any) it creates, how it differs mechanically from `mission create` starting a
  full mission lifecycle. Do not guess — cite the actual command/module you found.
- **T016 — Author `docs/context/ops-vs-missions.md`.** Structure: (1) one-paragraph definition
  of each, (2) a concrete decision table or rule ("use an Op when X; use a Mission when Y"), (3)
  a short example of each in practice (an example Op invocation, an example mission lifecycle
  reference). Add Divio frontmatter `type: explanation` (per NFR-005). Keep it tight — this is a
  concept page, not a full command reference (that's `docs/api/`'s job).
- **T017 — Verify each mission type's real purpose/phases.** Read all 4
  `src/specify_cli/missions/*/mission.yaml` files directly. Extract: name, description, and
  workflow phases for each. Do not rely on memory of this conversation's earlier summaries — the
  files are the ground truth.
- **T018 — Author `docs/context/mission-types.md`.** One section per mission type (name,
  one-line description, phase list, "best for" guidance) plus a short "how to choose" framing at
  the top. Add Divio frontmatter `type: explanation`. Link both new pages to each other.

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement`, after WP02 has landed, and merges back into
`feat/docs-ia-onboarding-overhaul`. Runs in parallel with WP05, WP06, WP07 (disjoint file sets).

## Definition of Done

- [ ] `docs/context/ops-vs-missions.md` exists with a concrete decision rule, grounded in the
      actual `dispatch` mechanism found in code.
- [ ] `docs/context/mission-types.md` lists exactly the 4 real mission types with accurate
      purpose/phases sourced from their `mission.yaml` files.
- [ ] Both pages carry valid `type: explanation` frontmatter.
- [ ] Both pages are cross-linked to each other.
- [ ] Any needed `toc.yml` placement gap is flagged in the Activity Log if WP02 didn't already
      reserve a slot (not edited directly — out of this WP's ownership).

## Risks & Mitigations

- **Inaccuracy risk**: this content describes governance-critical concepts; an inaccurate
  decision rule actively misleads users. Ground every claim in a specific file/command you
  actually read, not assumption.
- **Scope creep into full command reference**: keep this at the concept/decision-rule level;
  exhaustive flag-by-flag documentation belongs in `docs/api/`, not here.

## Review Guidance

- Trace the "Ops vs Missions" decision rule against the actual `dispatch` code path — does it
  hold up?
- Confirm the mission-types list matches `ls src/specify_cli/missions/` exactly (4 entries, no
  more, no fewer).

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T17:57:27Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Assigned agent via action command
- 2026-07-20T18:04:45Z – claude:sonnet-5:curator-carla:implementer – shell_pid=91148 – Ready for review: authored docs/context/ops-vs-missions.md and docs/context/mission-types.md, grounded in real dispatch/executor code and the 4 real mission.yaml files. toc.yml already reserves a 'Core Concepts > Context & Terminology' slot (context/index.md) for these; context/index.md's Explanation list still needs entries added for both new pages — out of WP04's owned_files (docs/context/ops-vs-missions.md, docs/context/mission-types.md only), flagged here as a follow-up for WP10's final nav pass.
- 2026-07-20T18:23:11Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=11323 – Started review via action command
- 2026-07-20T18:29:25Z – user – Moved to planned
- 2026-07-20T18:29:59Z – claude:sonnet-5:curator-carla:implementer – shell_pid=18409 – Started implementation via action command
- 2026-07-20T18:31:41Z – claude:sonnet-5:curator-carla:implementer – shell_pid=18409 – Cycle 2: corrected kitty-ops/*.jsonl claim per review feedback
- 2026-07-20T18:32:07Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=19963 – Started review via action command
- 2026-07-20T18:36:26Z – user – shell_pid=19963 – Review passed cycle 2: independently re-verified corrected kitty-ops/*.jsonl distinction against writer.py/executor.py/lifecycle.py/next_cmd.py; mission-types.md confirmed untouched. See review-cycle-2.md for full evidence.
