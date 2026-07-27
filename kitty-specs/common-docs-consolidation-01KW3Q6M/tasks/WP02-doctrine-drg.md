---
work_package_id: WP02
title: Common Docs doctrine artifacts + DRG wiring
dependencies:
- WP01
requirement_refs:
- C-003
- C-005
- FR-002
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: docs/2165-consolidation-research
merge_target_branch: docs/2165-consolidation-research
branch_strategy: Planning artifacts for this mission were generated on docs/2165-consolidation-research. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-consolidation-research unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/directives/**
- src/doctrine/styleguides/**
- src/doctrine/tactics/**
- src/doctrine/graph.yaml
role: implementer
tags: []
shell_pid: "662363"
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load doctrine-daphne` (or read `src/doctrine/agent_profiles/built-in/doctrine-daphne.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Make the Common Docs conventions **governed, distributable doctrine**: a binding directive, a styleguide whose every rule maps to a live check, and tactic(s) for applying them — all wired into the DRG and freshness-gated.

## Context

Depends on WP01 (the ADR fixes the conventions you codify). Read the existing doctrine-artifact format under `src/doctrine/{directive,styleguide,tactic}/` for the canonical YAML shape, and read **#1755** (the DRG generator/freshness footgun) before touching `graph.yaml`. **Do NOT depend on the `documentation_policy` charter-codegen path — it is buggy (#2153).** No doc-tree mutation (C-006).

## Subtasks

### T007 — The Common Docs directive
Author `src/doctrine/directives/<id>-common-docs.directive.yaml` binding documentation to: the 13-section structure, in-file-frontmatter SSOT, and the delete-stale curation policy. Give it a stable id — **this id is the binding contract** WP05's ratchet must reference (C-003).

### T008 — The Common Docs styleguide
Author `src/doctrine/styleguides/<id>-common-docs.styleguide.yaml` codifying: the structure, the frontmatter schema (incl. `doc_status` + the SEO `description` 50–180 constraint), naming, `adr/<era>/`, the `related:` resolvable-path form, the curation policy. Provide an explicit **rule→check mapping table** in the styleguide: each row names one live check (frontmatter → WP04's lockfile gate; `related:` → WP03's validator; structure → WP05's ratchet). **Zero rows may have check = none** — that is the checkable artifact.

### T009 — The Common Docs tactic(s)
Author `src/doctrine/tactics/<id>-*.tactic.yaml` for how-we-apply (place a doc; author an ADR with era + frontmatter incl. the `PROPOSED`/`superseded` mapping; run the rulers). Reference the actual commands/gates, not narrative.

### T010 — Wire into the DRG
Add the 3 nodes + their relations to `src/doctrine/graph.yaml` via `spec-kitty doctrine regenerate-graph` (do not hand-edit if a generator owns it — read #1755 first).

### T011 — Freshness gate
Ensure `spec-kitty doctrine regenerate-graph --check` is green (the committed `graph.yaml` matches a fresh regeneration).

### T012 — The directive-binding contract
Define the directive id as a **single shared constant** referenced by BOTH the directive artifact and WP05's ratchet. The C-003 binding is only real if WP05's self-test asserts the id **resolves to a loaded directive** (a node in `graph.yaml` / loads via DoctrineService) — not merely that the string appears. Coordinate the constant with WP05.

## Branch Strategy

Planning + merge target: `docs/2165-consolidation-research`. Worktree per `lanes.json` (Lane B, after WP01; parallel to WP03/WP04).

## Definition of Done

- [ ] directive + styleguide + tactic(s) authored in canonical format.
- [ ] Every styleguide rule names its enforcing check.
- [ ] `regenerate-graph --check` green with the 3 new nodes + declared relations.
- [ ] The directive id is published as the binding contract for WP05.
- [ ] `ruff`/terminology guard clean; no doc-tree mutation.

## Risks & Reviewer Guidance

- **#1755**: regenerate the graph with the canonical command; do not hand-edit asymmetric edges.
- Reviewer: confirm the directive is **not an orphan** — its id must be referenced by WP05's ratchet (C-003); a directive nothing consults is the fakeable failure mode renata flagged.

## Activity Log

- 2026-06-27T06:55:36Z – claude:opus:doctrine-daphne:implementer – shell_pid=556992 – Assigned agent via action command
- 2026-06-27T07:07:36Z – claude:opus:doctrine-daphne:implementer – shell_pid=556992 – Ready for review: Common Docs directive (DIRECTIVE_042) + styleguide (rule->check table) + tactic; DRG wired, regenerate-graph --check green; shared binding constant COMMON_DOCS_DIRECTIVE_ID published for WP05
- 2026-06-27T07:08:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=602143 – Started review via action command
- 2026-06-27T07:12:09Z – user – shell_pid=602143 – Review passed: directive(042)+styleguide+tactic under plural dirs, schema-valid (extractor validator green). DIRECTIVE_042 RESOLVES: shared constant COMMON_DOCS_DIRECTIVE_ID == artifact id == fresh-extraction node directive:DIRECTIVE_042 in graph.yaml (not a hand-edited string). regenerate-graph --check EXIT 0 (fresh, 3 new nodes + relations). Rule->check tooling map: 8 rows, zero check=none (WP03/04/05). #2153 codegen NOT used; C-006 clean (WP02 commit touches only src/doctrine/); ruff+terminology guard green. WP05 may bind on COMMON_DOCS_DIRECTIVE_ID.
- 2026-06-27T07:29:29Z – claude:opus:doctrine-daphne:implementer – shell_pid=645804 – Started implementation via action command
- 2026-06-27T07:38:55Z – claude:opus:doctrine-daphne:implementer – shell_pid=645804 – Added scaffold/write/find skill-tactics as doctrine per operator decision
- 2026-06-27T07:39:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=662363 – Started review via action command
