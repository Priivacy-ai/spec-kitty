---
work_package_id: WP03
title: Migrate raw DoctrineService construction sites
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: feat/charter-sole-door-bypass-closure
merge_target_branch: feat/charter-sole-door-bypass-closure
branch_strategy: Planning artifacts for this mission were generated on feat/charter-sole-door-bypass-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-sole-door-bypass-closure unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 2 - Bypass closure
history:
- at: '2026-08-03T14:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/_doctrine_collect.py
create_intent:
- tests/charter/test_doctrine_service_unfiltered_mode.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/compiler.py
- src/specify_cli/cli/commands/_doctrine_asset.py
- src/specify_cli/cli/commands/_doctrine_collect.py
- tests/charter/test_doctrine_service_unfiltered_mode.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Migrate raw DoctrineService construction sites

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer role, claude agent) before parsing
the rest of this prompt.

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` in the event log before starting. Address all feedback; log changes in the Activity Log.

---

## Objectives & Success Criteria

Close the 6 originally-flagged raw `doctrine.service.DoctrineService(...)` construction sites (FR-002).
(The 3 additional sites the post-plan squad found — `org_layer.py`, `generate.py` — are WP01's, not this
WP's; do not duplicate that work here.)

**Success criteria**:
- `charter/compiler.py:802` and `_doctrine_asset.py:75` route through `charter.activation.resolver.DoctrineService`
  (normal activation-aware construction).
- `_doctrine_collect.py`'s 4 diagnostic sites (`:193,283,420,828` — corrected line numbers, post-tasks squad
  found the original citations drifted +2 lines) route through the factory's **explicit
  unfiltered mode** (`pack_context=None`), not the activation-aware path — preserving today's doctor/health
  completeness.
- A regression test proves the unfiltered mode's output equals the raw unwrapped service's output.

## Context & Constraints

- **Depends on WP01** — the unified builder must exist.
- Read `research.md`'s R4 finding: `_collect_profile_health`, `_collect_glossary_pack_health`,
  `_collect_doctrine_collisions`, and `_build_selection_block` all deliberately need the full, unfiltered,
  all-layer view — an activation-aware swap here is a silent regression (narrows doctor/health output for
  deactivated packs), not a fix.
- Read `contracts/charter-doctrine-service-contract.md`'s "unfiltered-diagnostic contract" section: the
  shape is `charter.activation.resolver.DoctrineService(inner, pack_context=None)`, same class, distinguished only by
  the explicit argument — never a raw `doctrine.service.DoctrineService(...)` construction.

## Branch Strategy

- **Strategy**: lane-per-WP (normalized by `finalize-tasks`)
- **Planning base branch**: feat/charter-sole-door-bypass-closure
- **Merge target branch**: feat/charter-sole-door-bypass-closure

## Subtasks & Detailed Guidance

### Subtask T011 – Migrate `charter/compiler.py:802`

- **Purpose**: This site lives inside `charter.*` itself — the smallest, most direct fix in the WP.
- **Steps**: Wrap the existing raw construction: `charter.activation.resolver.DoctrineService(doctrine.service.
  DoctrineService(project_root=project_root), pack_context=<resolved context>)` — or better, call the
  unified builder from WP01 if a `repo_root`/`pack_context` pair is already available at this call site.
- **Files**: `src/charter/activation/compiler.py`.
- **Parallel?**: Yes.
- **Notes**: `compile_charter` does its own *separate* parallel activation filtering via `config_roots`,
  independent of this wrapper swap — that duplication is a WP01/FR-005 concern, not this subtask's. Do not
  attempt to resolve it here.

### Subtask T012 – Migrate `_doctrine_asset.py:75`

- **Purpose**: Close the raw construction; note this site reads `.assets`, a non-charter-activatable kind
  (excluded via `_NON_AUGMENTATION_ELIGIBLE_KINDS`), so it falls through `__getattr__` unfiltered either way
  — the fix here is about the *construction site*, not adding new filtering for `.assets`.
- **Steps**: Route through `charter.activation.resolver.DoctrineService` (normal construction, `pack_context` supplied
  normally); preserve the existing `repo_root is None` clean-install branch unchanged.
- **Files**: `src/specify_cli/cli/commands/_doctrine_asset.py`.
- **Parallel?**: Yes.

### Subtask T013 – Migrate `_doctrine_collect.py`'s 4 diagnostic sites (unfiltered mode)

- **Purpose**: Preserve full diagnostic visibility while still routing through the one canonical class.
- **Steps**:
  1. At each of `:193` (`_collect_profile_health`), `:283` (`_collect_glossary_pack_health`), `:420`
     (`_collect_doctrine_collisions`), `:828` (`_build_selection_block`) — corrected line numbers, verify
     against the current file before editing — replace the raw
     `doctrine.service.DoctrineService(...)` construction with
     `charter.activation.resolver.DoctrineService(inner, pack_context=None)`.
  2. Add an inline comment at each site naming the diagnostic-completeness rationale (per the contract
     file's requirement that unfiltered-mode call sites carry documented rationale).
- **Files**: `src/specify_cli/cli/commands/_doctrine_collect.py`.
- **Parallel?**: No — same file, do all 4 in one pass to keep the diff coherent.
- **Notes**: This is the subtask most likely to be "fixed wrong" — a plain activation-aware swap compiles
  and looks correct but silently narrows doctor/health output. T014 exists specifically to catch this.

### Subtask T014 – Regression test: unfiltered mode equals raw service output

- **Purpose**: Non-fakeable proof that `pack_context=None` construction preserves pre-mission diagnostic
  behaviour exactly.
- **Steps**: For a project with some packs deactivated, assert
  `charter.activation.resolver.DoctrineService(inner, pack_context=None).<prop>` equals
  `inner.<prop>` (the raw unwrapped service) for every gated property that exists today — equality, not "not
  empty."
- **Files**: `tests/charter/test_doctrine_service_unfiltered_mode.py` (new).
- **Parallel?**: No — depends on T013.

## Test Strategy

- `pytest tests/charter/ tests/specify_cli/cli/commands/ -v` — targeted surfaces.
- `mypy --strict src/charter/activation/compiler.py src/specify_cli/cli/commands/_doctrine_asset.py
  src/specify_cli/cli/commands/_doctrine_collect.py`.

## Risks & Mitigations

- **T013 silently narrows doctor/health output.** Mitigation: T014's equality test is the non-negotiable
  guard — do not consider T013 done without it passing.

## Review Guidance

- Confirm all 4 `_doctrine_collect.py` sites use `pack_context=None` explicitly, with a rationale comment.
- Confirm T014's assertion is equality against the raw service, not an existence/non-empty check.

## Activity Log

- 2026-08-03T14:10:00Z – system – Prompt created.
