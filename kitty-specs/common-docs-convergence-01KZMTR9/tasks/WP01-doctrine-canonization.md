---
work_package_id: WP01
title: Doctrine canonization (audience field + routing + lint config)
dependencies: []
requirement_refs:
- FR-002
- FR-009
- FR-023
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: packs/built-in/styleguides/common-docs.styleguide.yaml
create_intent: []
execution_mode: code_change
owned_files:
- packs/built-in/directives/042-common-docs.directive.yaml
- packs/built-in/directives/047-audience-oriented-writing.directive.yaml
- packs/built-in/styleguides/common-docs.styleguide.yaml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load curator-carla
```

Confirm in your first message which boundaries/directives you applied (doctrine maintenance;
canonical-source discipline; do not implement product features).

## Objective
Canonize the `audience:` field and the audience-based concern routing + new lint-config fields in the
Common Docs doctrine SSOT, so every downstream WP consumes one authority. This is a **foundation** — it
runs before any mover. See [plan.md](../plan.md) IC-01/IC-06(config)/IC-03(config), [research.md](../research.md) D2,
and [contracts/audience-resolution-contract.md](../contracts/audience-resolution-contract.md).

Note: T004 (structural_lint_config invariant fields) is reconciled to WP04 — the three-way
schema/LintConfig/YAML parity guard requires those fields to land together with WP04's LintConfig
dataclass + check-fns.

## Context
`audience:` already exists on 13 pages as free-text and a rich catalog exists at `docs/context/audience/`,
but the field is not canonized. The loaded `structural_lint_config` routes `how_to → development/` and
pins `guides_boundary`; the operator chose an **audience-based** split (contributor→development/,
user→guides/). OB-2: do NOT turn single-root into a standing blocking lint (reverses #2851) — only add
config fields for the invariants WP04 will check as advisory/terminal.

## Subtasks
- **T001** — In `042-common-docs.directive.yaml` and `047-audience-oriented-writing.directive.yaml`, add
  `audience:` as a governed frontmatter field: a resolvable repo-relative `.md` path (or list) targeting
  a persona under `docs/context/audience/`; required on touched pages only; explicitly NOT in
  `frontmatter_required_fields` (C-012).
- **T002** — In `common-docs.styleguide.yaml`, add an `audience-resolvable` rule with a `tooling:` row
  naming the WP02 resolver, and document the field in the principles/patterns.
- **T003** — Update `structural_lint_config.concern_bucket_to_section` to the audience-based routing
  (how_to → development/ for internal-audience, guides/ for external-audience) and reconcile
  `guides_boundary` accordingly, with a recorded rationale comment. This is the single routing edit all
  movers consume.

## Branch Strategy
Planning/base branch: `docs/common-docs-cleanup`. Final merge target: `docs/common-docs-cleanup`.
Execution worktree is allocated per the computed lane in `lanes.json`.

## Definition of Done
- `audience:` is documented in 042 + 047 + styleguide with a tooling row; NOT added to
  `frontmatter_required_fields`.
- `concern_bucket_to_section`/`guides_boundary` reflect audience routing with rationale.
- The styleguide still loads via `docs_structural_lint.py` without error and the current tree stays green.
- `pytest tests/architectural/test_no_legacy_terminology.py` green; ruff/mypy clean on any touched code.

## Risks
- Editing the styleguide is a shared surface (C-011): WP01 is its sole doctrine-config owner; WP04 owns
  the asset *code*. Keep the two edits depth-separated.
