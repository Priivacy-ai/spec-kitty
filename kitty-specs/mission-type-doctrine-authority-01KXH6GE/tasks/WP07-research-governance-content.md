---
work_package_id: WP07
title: Author research governance content
dependencies:
- WP03
- WP05
requirement_refs:
- FR-005
- NFR-002
- NFR-003
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
- T041
- T042
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "1781805"
shell_pid_created_at: "1784089344.32"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-06b, Lane C — closes the spike-timebox-policy dangler)
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/missions/research/
create_intent:
- src/doctrine/procedures/built-in/spike-timebox-policy.procedure.yaml
- src/doctrine/styleguides/built-in/research-citation-discipline.styleguide.yaml
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/missions/research/governance-profile.yaml
- src/doctrine/missions/research/actions/**
- src/doctrine/procedures/built-in/spike-timebox-policy.procedure.yaml
- src/doctrine/styleguides/built-in/research-citation-discipline.styleguide.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load doctrine-daphne` (role: implementer). Then read: [plan.md](../plan.md) §IC-06 (incl.
the "Campsite bonus: spike-timebox-policy closes a dangler" note), [spec.md](../spec.md) FR-005 (research
domain: decision/evidence + investigation), and the ADR net-new-artifact inventory.

## Objective

Populate the **research** mission type's governance set (type-grain + action-grain) so a research mission
resolves its own domain doctrine (FR-005) and no software-dev doctrine — **reference-first** plus **two
net-new artifacts**. Authoring `spike-timebox-policy` also closes a pre-existing dangler
(`researcher-robbie.agent.yaml:60` references a file that does not exist).

## Context

- `research/governance-profile.yaml` ships empty; `research/actions/` has 6 actions (gathering,
  methodology, output, retrospect, scoping, synthesis).
- **Invariant from WP05:** the profile must carry `id: research`.
- **Reference-first** existing research doctrine to WIRE: the `003-decision-doc` directive, the
  `dialectic-research` / `premortem` / `reverse-speccing` tactics, and the `situational-assessment`
  procedure.
- **Two net-new artifacts** to author: `spike-timebox-policy.procedure.yaml` (also closes the
  `researcher-robbie.agent.yaml:60` dangler) and `research-citation-discipline.styleguide.yaml`.

## Subtask guidance

- **T037 — reference-wire existing doctrine.** Reference `003-decision-doc`, the dialectic-research /
  premortem / reverse-speccing tactics, and the situational-assessment procedure by canonical id; verify
  each resolves in the DRG.
- **T038 — `spike-timebox-policy.procedure.yaml`.** Author the procedure (spike timeboxing: hypothesis,
  budget, exit criteria, decision-or-abandon). Confirm it satisfies the existing reference at
  `researcher-robbie.agent.yaml:60` (dangler → resolvable).
- **T039 — `research-citation-discipline.styleguide.yaml`.** Author citation/evidence discipline (claims
  carry sources; evidence tiers; no unsourced assertions).
- **T040 — profile.** Populate `research/governance-profile.yaml` (`id: research`) with the referenced +
  net-new artifacts, covering the FR-005 research domain (decision/evidence + investigation).
- **T041 — action indices.** Populate `research/actions/*/index.yaml` where domain-appropriate; empty
  grains stay empty (FR-004). Respect cross-grain disjointness (FR-013).
- **T042 — DRG + gates.** Confirm the 2 net-new artifacts + all references resolve in the DRG (no
  danglers); run the terminology guard. Do NOT run the terminal `regenerate-graph --check` (WP12 owns it).

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It depends on WP03 + WP05, runs parallel to WP06/WP08.

## Definition of Done

- [ ] `spike-timebox-policy.procedure.yaml` + `research-citation-discipline.styleguide.yaml` authored,
      schema-valid, DRG-resolvable.
- [ ] `researcher-robbie.agent.yaml:60` reference now resolves (dangler closed).
- [ ] `research/governance-profile.yaml` populated (`id: research`), covering the FR-005 research domain.
- [ ] Action indices populated where appropriate; empty grains valid (FR-004); no cross-grain double
      declaration (FR-013).
- [ ] All references resolve in the DRG; terminology guard green; **zero** software-dev doctrine resolved.

## Risks

- **DRG danglers** — the two net-new ids + all references must resolve; do NOT regenerate here (WP12).
- **Cross-grain double declaration** — keep each artifact in exactly one grain.
- **Re-authoring shipped content** — wire existing research doctrine by reference; only the 2 artifacts are new.

## Reviewer guidance (reviewer-renata, opus)

- Confirm `id: research` and full FR-005 research-domain coverage.
- Confirm `spike-timebox-policy` closes the `researcher-robbie.agent.yaml:60` dangler.
- Confirm references resolve and no artifact is double-declared across grains.
- Confirm no `regenerate-graph` leaked in (WP12 owns it).

## Activity Log

- 2026-07-15T04:22:33Z – claude:sonnet:python-pedro:implementer – shell_pid=1781805 – Assigned agent via action command
