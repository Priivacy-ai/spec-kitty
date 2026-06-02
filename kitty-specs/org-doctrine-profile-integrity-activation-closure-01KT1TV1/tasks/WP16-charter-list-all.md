---
work_package_id: WP16
title: charter list --all catalog completeness
dependencies:
- WP01
- WP09
- WP18
requirement_refs:
- FR-025
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
subtasks:
- T070
- T071
- T072
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/list_cmd.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/specify_cli/cli/commands/charter/list_cmd.py
- tests/specify_cli/test_charter_list.py
role: implementer
tags: []
---

# WP16 — `charter list --all` catalog completeness

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Add `charter list --all` showing every available artifact per kind across built-in, org-pack, and project layers (annotated by source layer), including the `template` kind (FR-025). Consumes `list_available` (WP09, now layer-aware), the canonical kinds (WP01), and template discovery (WP18). Org/project roots are resolved in `specify_cli` and passed as data (C-008).

## Context

- Spec FR-025; research R-008, R-009. Contract C4.4. Depends on WP09 (`list_available` org/project), WP01 (`_KIND_ORDER` from canonical kinds), WP18 (template kind).

### Code map

- `src/specify_cli/cli/commands/charter/list_cmd.py:39` `list_cmd` (`--show-available` at :40; `_KIND_ORDER` :25; calls `manager.list_available` :68).
- WP09 `pack_manager.list_available(..., layer_roots=...)`; resolve roots via `specify_cli.doctrine.config.resolve_org_roots`.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP01, WP09, WP18.

## Subtasks

### T070 — `--all` flag

**Steps**: Add `--all` (implies and supersedes `--show-available`). When set, resolve org/project roots in `specify_cli` and pass them as data to `list_available`. Derive `_KIND_ORDER` from the canonical kind universe (WP01) instead of the local literal.

**Validation**: - [ ] `--all` shows available-but-not-activated across layers; `--show-available` behavior preserved.

### T071 — Layer annotation + template kind

**Steps**: Render each artifact with its source layer (built-in/org/project). Include the `template` kind in the listing using WP18's discovery (mission-qualified IDs). Keep the table readable.

**Validation**: - [ ] artifacts annotated by layer; `template` kind appears with mission-qualified IDs.

### T072 — Tests

**Steps**: `tests/specify_cli/test_charter_list.py` — `list --all` with a fixture org pack + project artifacts shows built-in/org/project per kind with layer; template kind present.

**Validation**: - [ ] green; black-box CLI test (DIRECTIVE_036).

## Definition of Done

- [ ] `--all` flag with layer annotation + template kind; consumes WP09/WP18; roots passed as data. CC-2 + CC-4 pass.

## Risks

- C-008: resolve roots in `specify_cli`; do not push root resolution into `charter`.
- Depends on WP18 for the template kind — if WP18 isn't merged, gate the template column behind availability or sequence accordingly (lanes.json dependency).

## Reviewer Guidance (reviewer-renata)

- Confirm `--all` covers all three layers with source-layer annotation.
- Confirm `_KIND_ORDER` derives from the canonical kinds (no re-declared list).
