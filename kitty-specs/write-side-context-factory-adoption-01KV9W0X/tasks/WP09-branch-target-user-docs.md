---
work_package_id: WP09
title: Branch-target user documentation (FR-009)
dependencies: []
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2950561"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: curator-carla
authoritative_surface: docs/explanation/
create_intent:
- docs/explanation/branch-target-routing.md
execution_mode: code_change
owned_files:
- docs/explanation/branch-target-routing.md
- docs/development/3-2-page-inventory.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

(If `curator-carla` is unavailable, load `python-pedro` and apply documentation discipline.) Then read:
`spec.md` **FR-009** + **SC-009** + **C-005** (edit SOURCE `docs/`, never generated copies) + **C-007** (the
routing table this documents); `plan.md` **D-11** + **IC-DOCS**.

## Objective

Author the user-facing **Explanation** page (Divio "Explanation") that demystifies lane-based behaviour for
users by presenting the **branch-target routing table** — "this is where everything goes" — plus the
**simple case**. This is an operator requirement: the table should make the entire lane/coordination model
legible to a user who has never read the internals.

## Subtask guidance

### T039 — Author the Explanation page
Create `docs/explanation/branch-target-routing.md` (Divio "Explanation" — the *why/how it fits together*,
not a how-to). Present the routing table verbatim from C-007:

| Diff type | Lands on |
|-----------|----------|
| Planning artifacts (spec/plan/tasks) | coordination |
| Status / task events | coordination |
| Lanes (`lanes.json`) | coordination |
| Code changes | the lane (per-WP worktree) |
| Shared docs | base |
| Merge target | base |

Then the **simple case**: when every target is set to the base branch (no coordination branch declared, no
lane worktree), spec-kitty runs flat — exactly as it did before lanes/coordination existed. Explain that the
context object decides routing per diff type, and that the all-base collapse is the guaranteed simple case
(tie it to NFR-006 in user terms, not internal symbols). Keep it user-facing: no `build_execution_context` /
fragment jargon — describe behaviour.

### T040 — docs-freshness page-inventory
Add the new page's row to `docs/development/3-2-page-inventory.yaml` (QUOTE any note containing `: ` — an
unquoted colon breaks the YAML; this bit Mission A). Run the docs-freshness check and confirm green.

### T041 — Cross-link + classify
Cross-link from the existing lanes/coordination explanation surface (`docs/explanation/execution-lanes.md` /
`git-worktrees.md`) so the new page is discoverable. Confirm Divio "Explanation" classification (frontmatter
`type: explanation` if the docs system uses it).

## Definition of Done
- [ ] `docs/explanation/branch-target-routing.md` exists with the routing table + the simple-case section,
      user-facing (no internal jargon), Divio "Explanation" (FR-009/SC-009).
- [ ] page-inventory row added; **docs-freshness green** (notes quoted).
- [ ] Cross-linked from the lanes/coordination explanation surface.
- [ ] SOURCE `docs/` edited only (C-005). **C-008**: adjacent doc breakage fixed in-change.

## Reviewer guidance
Read it as a user who has never seen lanes. Is the routing table the "demystify everything" artifact the
operator asked for? Confirm the simple-case is explained in behavioural terms. Confirm docs-freshness is green
and the page-inventory note is quoted. Confirm no generated agent-copy docs were edited (C-005).

## Activity Log

- 2026-06-17T06:21:41Z – claude:sonnet:curator-carla:implementer – shell_pid=2897020 – Assigned agent via action command
- 2026-06-17T06:29:03Z – claude:sonnet:curator-carla:implementer – shell_pid=2897020 – WP09 docs complete (branch-target Explanation + simple case; docs-freshness 39 green). FORCE: flattened-mission kitty-specs-on-lane guard false-positive (status lives on planning branch). Orchestrator-driven transition.
- 2026-06-17T06:29:14Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2950561 – Started review via action command
- 2026-06-17T06:32:39Z – user – shell_pid=2950561 – Review passed: branch-target-routing.md is correct Divio Explanation with routing table + simple case; user-facing prose, no internal jargon; page-inventory row added with quoted notes (YAML valid); docs-freshness 70 passed; cross-links added to execution-lanes.md + git-worktrees.md; C-005 clean (SOURCE docs/ only, no agent copies); terminology guard 2 passed.
