---
work_package_id: WP18
title: Doctrine template discovery + DRG addressing (#1333)
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-033
- FR-034
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
subtasks:
- T077
- T078
- T079
- T080
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/template_catalog.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/doctrine/resolver.py
- src/doctrine/template_catalog.py
- tests/doctrine/test_template_discovery.py
role: implementer
tags: []
---

# WP18 — Doctrine template discovery + DRG addressing (#1333)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Make doctrine templates discoverable and DRG-addressable (#1333, FR-033/034): a discovery surface that enumerates templates across tiers/missions (annotated by tier), and mission-qualified DRG template nodes (`template:<mission>/<name>`) so `charter list --all` (WP16) and `charter context --include template:<id>` (WP17) work. No template-file frontmatter churn — identity derives from the existing tier+mission+filename layout.

## Context

- Spec FR-033/034; research R-013/#1333 (templates resolved by name through the 5-tier chain in `resolver.py`; `ArtifactKind.TEMPLATE` has an empty glob; templates live in mission-scoped tier dirs; absent from list/include).
- Plan decision: mission-qualified-name identity (`software-dev/spec`). Data model §8. Contract C4.5.

### Code map

- `src/doctrine/resolver.py:221` `resolve_template` (5-tier: override→legacy→global-mission→global→package); `_content_template_path`/`_command_template_path`.
- `src/doctrine/artifact_kinds.py` — `ArtifactKind.TEMPLATE` (plural `templates`, empty glob).
- Templates on disk: `src/doctrine/templates/`, `src/doctrine/missions/<m>/templates/`, `.../command-templates/`.
- DRG node kind: `doctrine/drg/models.py` `NodeKind.TEMPLATE` (exists). Merged DRG from WP03.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP01 (kind), WP02/WP03 (DRG node/merge).

## Subtasks

### T077 — Template discovery surface

**Steps**: Create `src/doctrine/template_catalog.py` with `discover_templates(*, tier_roots) -> list[TemplateRef]` where `TemplateRef{template_id: "<mission>/<name>", mission, name, tier, path}`. Walk the tier+mission directories (handle the empty-glob/no-extension reality and both `templates/` and `command-templates/`). Annotate by source tier (override→…→package). Roots passed as data (C-008 spirit — caller provides them).

**Validation**: - [ ] enumerates built-in + mission templates with tier annotation; same name in two missions → two distinct refs.

### T078 — Mint DRG template nodes (mission-qualified IDs)

**Steps**: Provide a function to mint `DRGNode`(kind=TEMPLATE, urn=`template:<mission>/<name>`) for discovered templates so templates are addressable in the (doctrine-merged) DRG. Reuse WP03's merge ownership — emit nodes as data the merge/aggregation can include; do not import `charter`.

**Validation**: - [ ] template nodes have URNs `template:<mission>/<name>`; cross-mission duplicates are distinct nodes.

### T079 — Resolution by template ID

**Steps**: Add `resolve_template_by_id(template_id, *, tier_roots)` that maps `<mission>/<name>` back through `resolver.resolve_template` (respecting the 5-tier precedence) to return the resolved content/path. This is what WP17's `--include template:<id>` calls.

**Validation**: - [ ] `resolve_template_by_id("software-dev/spec")` returns the highest-precedence template content.

### T080 — Tests

**Steps**: `tests/doctrine/test_template_discovery.py` — discovery enumerates + annotates tier; cross-mission disambiguation; DRG node URN format; resolution by ID respects tier precedence.

**Validation**: - [ ] green; ruff/mypy clean; zero-dependency (`doctrine` imports only kernel/doctrine).

## Definition of Done

- [ ] Discovery surface + mission-qualified DRG template nodes + resolution-by-ID; tests green. Consumed by WP16/WP17. CC-2 pass.

## Risks

- Empty-glob/no-extension templates: discovery must not assume the flat `built-in/*.<suffix>` layout — walk the mission-scoped tier dirs.
- Keep `doctrine` zero-dependency; template node minting must not import `charter`/`specify_cli`.

## Reviewer Guidance (reviewer-renata)

- Confirm mission-qualified IDs disambiguate same-named templates across missions.
- Confirm resolution respects the existing 5-tier precedence.
- Confirm no upward imports from `doctrine`.
