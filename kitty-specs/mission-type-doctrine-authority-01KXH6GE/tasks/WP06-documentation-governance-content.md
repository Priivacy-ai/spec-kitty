---
work_package_id: WP06
title: Author documentation governance content
dependencies:
- WP03
- WP05
requirement_refs:
- FR-002
- FR-005
- NFR-002
- NFR-003
- NFR-006
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
- T033
- T034
- T035
- T036
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "1780760"
shell_pid_created_at: "1784089331.31"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-06a, Lane C — heaviest content WP, 5 net-new styleguides)
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/missions/documentation/
create_intent:
- src/doctrine/styleguides/built-in/divio-type-discipline.styleguide.yaml
- src/doctrine/styleguides/built-in/plain-language.styleguide.yaml
- src/doctrine/styleguides/built-in/docs-accessibility.styleguide.yaml
- src/doctrine/styleguides/built-in/publication-authority.styleguide.yaml
- src/doctrine/styleguides/built-in/docs-freshness-sla.styleguide.yaml
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/missions/documentation/governance-profile.yaml
- src/doctrine/missions/documentation/actions/**
- src/doctrine/styleguides/built-in/divio-type-discipline.styleguide.yaml
- src/doctrine/styleguides/built-in/plain-language.styleguide.yaml
- src/doctrine/styleguides/built-in/docs-accessibility.styleguide.yaml
- src/doctrine/styleguides/built-in/publication-authority.styleguide.yaml
- src/doctrine/styleguides/built-in/docs-freshness-sla.styleguide.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load doctrine-daphne` (role: implementer). Then read: [plan.md](../plan.md) §IC-06 (the
"size off the artifact inventory, not equal thirds" directive), [spec.md](../spec.md) FR-005 (documentation
domain list) + FR-002 + NFR-006, the ADR's net-new-artifact inventory, and the mission-wrap-up doctrine
authoring guidance (author + activate: this WP creates artifacts and wires them into the DRG-resolvable
governance set).

## Objective

Populate the **documentation** mission type's governance set — type-grain
(`governance-profile.yaml selected_*`) plus action-grain (`actions/*/index.yaml`) — so a documentation
mission resolves its own domain doctrine (FR-005) and **no** software-dev doctrine (FR-002), making the
non-leakage guard (NFR-006) **non-vacuous**. This is the **heaviest** content WP: **reference-first**
(wire existing docs doctrine) **plus author 5 net-new styleguides**.

## Context

- `documentation/governance-profile.yaml` currently ships empty `selected_*` (all `[]`, `template_set:
  null`). `documentation/actions/` already has 8 actions (accept, audit, design, discover, generate,
  publish, retrospect, validate) — populate their `index.yaml` governance.
- **Invariant from WP05:** the profile must carry `id: documentation` (== `mission_type`) or the overlay
  field-merge mis-keys silently.
- **FR-005 documentation coverage — every one of the 8 named items must be HOMED to a specific artifact
  or action-grain entry (no unhomed item):**
  | # | FR-005 item | Home |
  |---|-------------|------|
  | 1 | Divio type | `divio-type-discipline.styleguide.yaml` (T031) |
  | 2 | plain language | `plain-language.styleguide.yaml` (T032) |
  | 3 | accessibility | `docs-accessibility.styleguide.yaml` (T033) |
  | 4 | source-of-truth | `publication-authority.styleguide.yaml` (T034, source-of-truth section) |
  | 5 | publication | `publication-authority.styleguide.yaml` (T034, publication-gate section) |
  | 6 | freshness | `docs-freshness-sla.styleguide.yaml` (T035) |
  | 7 | **audience** | action-grain `actions/discover/index.yaml` (target-audience is a discovery-time concern) — wire an audience entry there; if a referenced audience tactic exists, cite it, else add a `target-audience` section to `plain-language.styleguide.yaml` and note the dual-home in the profile |
  | 8 | **review flow** | action-grain `actions/validate/index.yaml` + `actions/accept/index.yaml` (review/accept actions) — wire the doc review-flow governance there (reference an existing review tactic rather than authoring a 6th styleguide) |
  The 5 net-new styleguides cover items 1–6; **audience (7)** and **review flow (8)** are homed to the
  action-grain so none is unhomed. WP12's T067 membership check asserts these ids appear in the resolved set.
- **Reference-first, author-only-the-gaps.** Existing docs doctrine to WIRE (do not re-author): the
  `042-common-docs` / `037-living-docs` directives, the `common-docs.styleguide.yaml`, the
  `common-docs-{find,scaffold,write,curation}.tactic.yaml` curation tactics, the
  `drill-down-documentation` / `documentation-gap-prioritization` procedures, and the mermaid/plantuml
  toolguides. The **5 net-new** styleguides are the authored deliverables.

## Subtask guidance

- **T030 — reference-wire existing doctrine.** In `governance-profile.yaml` and the action indices,
  reference the existing docs artifacts above by their canonical ids. Verify each id resolves in the DRG
  (no danglers). Do NOT duplicate content that already ships — wire, don't re-author.
- **T031 — `divio-type-discipline.styleguide.yaml`.** Author: Tutorial / How-To / Reference / Explanation
  discipline (one doc = one Divio type; no mixing).
- **T032 — `plain-language.styleguide.yaml`.** Author: plain-language / readability rules for docs prose.
- **T033 — `docs-accessibility.styleguide.yaml`.** Author: accessibility rules (alt text, heading order,
  link text, contrast-in-diagrams).
- **T034 — `publication-authority.styleguide.yaml`.** Author: source-of-truth + publication authority
  (docs mirror shipped behaviour; code is the source of truth; publication gate).
- **T035 — `docs-freshness-sla.styleguide.yaml`.** Author: freshness SLA (staleness thresholds, review
  cadence, generated-page freshening).
- **T036 — profile + action indices.** Wire all 5 net-new styleguides + the referenced artifacts into
  `governance-profile.yaml` (`selected_styleguides`, `selected_tactics`, `selected_procedures`,
  `selected_directives`, `selected_toolguides`) and into the relevant `actions/*/index.yaml`. Add
  `id: documentation`. Respect the **cross-grain disjointness** (FR-013): an artifact appears in the
  type-grain **or** an action-grain, never both. Do NOT run the terminal `regenerate-graph --check` — that
  is owned once by WP12.

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It depends on WP03 (schema stable) and WP05 (`id`
invariant), and runs parallel to WP07/WP08. The DRG regenerate is deferred to WP12.

## Definition of Done

- [ ] 5 net-new styleguides authored, schema-valid, DRG-resolvable.
- [ ] `governance-profile.yaml` populated (`id: documentation`), covering the FR-005 documentation domain
      list, wiring existing docs doctrine (reference-first) + the 5 net-new styleguides.
- [ ] **All 8 FR-005 items homed** per the Context table — including **audience** (action-grain
      `discover`) and **review flow** (action-grain `validate`/`accept`); no item unhomed.
- [ ] `actions/*/index.yaml` populated where domain-appropriate; empty grains left empty (FR-004 — valid).
- [ ] No artifact appears in both type-grain and action-grain (FR-013, canonical URN).
- [ ] Every referenced id resolves in the DRG (no danglers).
- [ ] **Terminology guard green** — run `pytest tests/architectural/test_no_legacy_terminology.py` before
      push (heaviest prose WP; CI-only gate — must pass locally first).
- [ ] Resolved documentation governance contains **zero** software-dev-only doctrine (feeds NFR-006).

## Risks

- **Undersizing** — this WP is materially heavier than research/plan; size off the 5-styleguide inventory,
  not "one of three".
- **DRG freshness / danglers** — every authored + referenced id must resolve; do NOT regenerate here (WP12).
- **Cross-grain double declaration** — the FR-013 guard (in WP03) will hard-fail at construction; keep each
  artifact in exactly one grain.
- **Re-authoring shipped content** — wire existing docs doctrine by reference; only the 5 styleguides are new.

## Reviewer guidance (reviewer-renata, opus)

- Confirm the profile carries `id: documentation` and covers the full FR-005 domain list.
- Confirm existing docs doctrine is referenced (not duplicated) and every id resolves in the DRG.
- Spot-check no artifact is double-declared across grains (FR-013).
- Confirm no `regenerate-graph` run leaked in (WP12 owns it).

## Activity Log

- 2026-07-15T04:22:20Z – claude:sonnet:python-pedro:implementer – shell_pid=1780760 – Assigned agent via action command
