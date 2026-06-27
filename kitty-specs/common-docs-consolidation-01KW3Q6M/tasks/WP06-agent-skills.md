---
work_package_id: WP06
title: Common Docs Agent Skills resolution
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: docs/2165-consolidation-research
merge_target_branch: docs/2165-consolidation-research
branch_strategy: Planning artifacts for this mission were generated on docs/2165-consolidation-research. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-consolidation-research unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
agent: "claude:sonnet:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: .agents/skills/spec-kitty.common-docs-scaffold/
create_intent: []
execution_mode: code_change
owned_files:
- .agents/skills/spec-kitty.common-docs-scaffold/**
- .agents/skills/spec-kitty.common-docs-write/**
- .agents/skills/spec-kitty.common-docs-find/**
- .kittify/command-skills-manifest.json
- docs/engineering_notes/651-docs-consolidation/index.md
- docs/engineering_notes/651-docs-consolidation/02-common-docs-standard.md
role: implementer
tags: []
shell_pid: "675608"
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load python-pedro` (or read the profile YAML and adopt it). State which directives apply, then proceed.

## Objective

Resolve the dangling `common-docs-write` reference: **either** install the three Common Docs Agent Skills (`common-docs-scaffold` / `-write` / `-find`) into the skills layer **or** declare them out of scope and remove every reference to them. The repo must end consistent — no requirement or doc may reference a skill that isn't installed.

## Context

Depends on WP01 (the ADR records the install-vs-out-of-scope decision). The research (`docs/engineering_notes/651-docs-consolidation/02-common-docs-standard.md`) found the standard's skills automate *nothing load-bearing* (scaffold/authoring aids only) — so installing is optional; the dangling reference is the real defect. spec-kitty's skill layer is `.agents/skills/` with manifest `.kittify/command-skills-manifest.json` (read `src/specify_cli/skills/` for the renderer/installer). No doc-tree mutation beyond removing a dangling reference.

## Subtasks

### T026 — Decide (per the ADR)
Read WP01's ADR decision on the skills. If **out of scope**: skip T027's install and do the removal in T028 only. If **install**: proceed to T027.

### T027 — Install (only if decided)
Author `.agents/skills/spec-kitty.common-docs-{scaffold,write,find}/SKILL.md` and register them in `.kittify/command-skills-manifest.json` via the canonical installer (do not hand-edit the manifest if the installer owns it — see `src/specify_cli/skills/`).

### T028 — Consistency check
Grep the repo for `common-docs-write` / `common-docs-scaffold` / `common-docs-find`. If installed: confirm each reference resolves to an installed skill. If out of scope: remove the dangling references in `docs/engineering_notes/651-docs-consolidation/{index,02-common-docs-standard}.md` (the **sanctioned C-006 exception** — FR-008 authorizes this single doc-text edit). Assert (grep): **no reference points to an absent skill.**

## Branch Strategy

Planning + merge target: `docs/2165-consolidation-research`. Worktree per `lanes.json` (after WP01; parallel to WP02/03/04).

## Definition of Done

- [ ] The install-vs-out-of-scope decision from the ADR is implemented.
- [ ] No requirement, scenario, or doc references a skill that isn't installed (grep clean).
- [ ] If installed: manifest registers all three; the renderer produces them. `ruff` clean.

## Risks & Reviewer Guidance

- Low risk. Reviewer: run the grep — the failure mode is a half-resolution (install two, reference three; or remove one reference, leave another).

## Activity Log

- 2026-06-27T06:56:20Z – claude:sonnet:python-pedro:implementer – shell_pid=559234 – Assigned agent via action command
- 2026-06-27T07:07:16Z – claude:sonnet:python-pedro:implementer – shell_pid=559234 – Ready for review: declared Common Docs skills out of scope per ADR Neutral consequences; removed dangling 'install as peer skills' claim from 02-common-docs-standard.md and resolved open-question reference in index.md; grep clean (no reference points to an absent installed skill)
- 2026-06-27T07:07:52Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=600453 – Started review via action command
- 2026-06-27T07:16:02Z – user – shell_pid=600453 – Moved to planned
- 2026-06-27T07:47:22Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=600453 – Citation now honest: skills implemented as doctrine tactics (WP02); ADR Neutral consequences superseded by doctrine-tactics decision; reconciliation deferred to Mission B
- 2026-06-27T07:47:50Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=675608 – Started review via action command
