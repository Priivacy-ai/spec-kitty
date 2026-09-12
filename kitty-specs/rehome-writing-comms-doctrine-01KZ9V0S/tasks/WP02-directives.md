---
work_package_id: WP02
title: Writing-comms directives (047-050) — relocate & reconcile
dependencies: []
requirement_refs:
- FR-001
- FR-008
- FR-009
- FR-010
planning_base_branch: feat/rehome-writing-comms-doctrine
merge_target_branch: feat/rehome-writing-comms-doctrine
branch_strategy: Planning artifacts for this mission were generated on feat/rehome-writing-comms-doctrine. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/rehome-writing-comms-doctrine unless the human explicitly redirects the landing branch.
created_at: '2026-08-05T21:14:46Z'
subtasks:
- T009
- T010
- T011
- T012
- T013
history:
- at: '2026-08-05T21:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: packs/built-in/directives/
create_intent:
- packs/built-in/directives/047-audience-oriented-writing.directive.yaml
- packs/built-in/directives/048-version-governance.directive.yaml
- packs/built-in/directives/049-agent-declaration-and-self-introduction.directive.yaml
- packs/built-in/directives/050-credential-handling-discipline.directive.yaml
execution_mode: code_change
model: ''
owned_files:
- packs/built-in/directives/047-audience-oriented-writing.directive.yaml
- packs/built-in/directives/048-version-governance.directive.yaml
- packs/built-in/directives/049-agent-declaration-and-self-introduction.directive.yaml
- packs/built-in/directives/050-credential-handling-discipline.directive.yaml
role: curator
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load doctrine-daphne
```

## Objective

Land directives 047-050 on `packs/built-in/directives/` and reconcile the content blockers the
squad reviews flagged (research D-06 §3, §4, §5c): repoint 047's references to its own concept,
add a boundary between 048 and 018, narrow 049 to match its advisory enforcement, and re-anchor
050 on prevention. Source is on ref `pr-2918` at `src/doctrine/directives/built-in/`.
Relocation commit carries the `Co-Authored-By` contributor trailer (FR-011).

## Context & Constraints

- 047-050 are **free** on current main (directives top out at 046) — verified; re-confirm at
  start with `ls packs/built-in/directives/ | grep -E '04[7-9]|050'` (expect empty before you
  create them). If any collided, renumber the file + `id:` + all cross-refs (C-006).
- Directive `references:` entries mint DRG edges (WP04 regenerates). Endpoint ids must resolve to
  real artifacts on the current surface.
- Do not touch existing directives (018, 031, 037, use-c4-model-techniques) — 048's boundary is a
  one-line cross-reference *from* 048.
- Keep the Terminology Canon; no version numbers in scope (directive numbers are identifiers).

## Subtask T009 — Relocate directives 047-050

- `git show pr-2918:src/doctrine/directives/built-in/<file>` → `packs/built-in/directives/<file>`
  for all four. Commit with the `Co-Authored-By` trailer.
- **Validation:** old path empty; `doctrine validate` runs on each (pre-reconciliation).

## Subtask T010 — Directive 047: repoint references to the writing-audience concept

- The `references` block currently wires 047 to `stakeholder-persona-template` and
  `stakeholder-alignment` — which the writing-audience README explicitly says must NOT be wired to
  the writing-audience concept (research D-06 §5c, a direct self-contradiction). Repoint to
  `tactic: writing-audience-catalog` (047's own head concept) and drop the two stakeholder refs.
- **Validation (non-fakeable):** `grep -iE 'stakeholder-persona-template|stakeholder-alignment'
  packs/built-in/directives/047-*.yaml` → empty; `grep 'writing-audience-catalog'
  packs/built-in/directives/047-*.yaml` → present.

## Subtask T011 — Directive 048: boundary vs Directive 018

- Add a one-line cross-reference/boundary: `018` = version the artifact you author; `048` = read
  the current version of an artifact you consume (research D-06 §5a). Add a `references`/prose
  cross-ref to `DIRECTIVE_018` so the two authorities are explicitly distinct, not competing.
- **Validation:** boundary text present; `DIRECTIVE_018` reference resolves.

## Subtask T012 — Directive 049: narrow "must self-declare" to advisory

- `enforcement` is `advisory` but intent/validation say specialists "must declare" / "states its
  role", and only 1/7 profiles wire the declaration (research D-06 §4). Narrow the intent and
  validation_criteria language from "must declare / states its role" to "should open with a short
  role/scope declaration", matching the advisory field and shipped reality (no runtime gate
  enforces self-introduction).
- **Validation (non-fakeable):** `grep -iE 'must (declare|state|self-declare|introduce)'
  packs/built-in/directives/049-*.yaml` → empty (intent/validation reworded to "should");
  `enforcement: advisory` unchanged.

## Subtask T013 — Directive 050: re-anchor on prevention

- The operative procedure strips secrets *after* they enter the error text, though 050's own
  integrity rule already requires redaction *before* output (research D-06 §3). Re-anchor the
  primary procedure on (i) connector-side injection / pre-model redaction, (ii) least privilege
  (link `secure-design-checklist`), and reframe "strip from error text" as an explicit
  defense-in-depth *fallback* for third-party error strings — so the procedure agrees with its own
  pre-exposure integrity rule.
- **Validation (non-fakeable):** `grep -iE 'connector-side|pre-model redaction|least[- ]privilege'
  packs/built-in/directives/050-*.yaml` → present; the strip-after step is explicitly labelled
  `fallback`/`defense-in-depth` (`grep -iE 'fallback|defense-in-depth' 050-*.yaml` → present) and
  the prevention control appears before it in the procedure body.

## Branch Strategy

Planning base and mission merge target are both `feat/rehome-writing-comms-doctrine`. The WP's
worktree is allocated per computed lane from `lanes.json`. Completed work merges back into
`feat/rehome-writing-comms-doctrine`; the operator merges the eventual PR to `origin/main`.

## Definition of Done

- [ ] 047-050 relocated; old path empty; relocation commit carries the contributor trailer.
- [ ] 047 references point at `writing-audience-catalog`; no `stakeholder-*` refs (T010).
- [ ] 048 carries an explicit 018 boundary (T011).
- [ ] 049 language matches its `advisory` enforcement (T012).
- [ ] 050 primary control is prevention; strip-after is a labelled fallback (T013).
- [ ] `spec-kitty doctrine validate` clean on all four; terminology guard passes.

## Risks & Mitigations

- **Numbering collision (C-006):** re-verify 047-050 free at start; renumber + fix cross-refs if not.
- **Dangling references:** every `references` id must resolve on the current surface — check before handing to WP04's regenerate.
- **Over-trimming 047:** keep the audience concept's own references intact; only drop the stakeholder ones.

## Reviewer Guidance

- Confirm 047 no longer contradicts the writing-audience README boundary.
- Confirm 049's normative strength matches `advisory`.
- Confirm 050 reads as prevention-first, fallback-second.
- Confirm no existing directive (018/031/037) was edited.

## Activity Log

- 2026-08-05T21:14:46Z — system — Prompt generated via /spec-kitty.tasks
