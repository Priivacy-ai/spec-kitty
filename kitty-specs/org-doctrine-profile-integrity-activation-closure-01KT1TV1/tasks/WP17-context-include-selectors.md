---
work_package_id: WP17
title: charter context --include selectors (agent-profile + template)
dependencies:
- WP01
- WP18
requirement_refs:
- FR-022
- FR-023
- FR-024
- FR-034
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts were generated on mission/org-doctrine-profile-integrity-activation-closure. During implement this WP runs in its computed lane; completed changes merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human redirects the landing branch.
subtasks:
- T073
- T074
- T075
- T076
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/context.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/charter/context.py
- src/specify_cli/cli/commands/charter/context.py
- tests/charter/test_context_include.py
role: implementer
tags: []
---

# WP17 — `charter context --include` selectors (agent-profile + template)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Make `charter context --include agent-profile:<id>` work (FR-022/023) by routing the selector kind through the canonical resolver (WP01), collapse the duplicated renderer table onto the canonical kinds, advertise the agent-profile kind in help (FR-024), and wire `template:<id>` resolution (FR-034) using WP18.

## Context

- Spec FR-022/023/024/034; research R-007 (no hyphen normalization; renderer keyed on underscore; help omits agent-profile), R-009 (duplicated renderer table + candidate tuple in `_render_generic_artifact_include`).
- Contract C4.4 (agent-profile + template include). Depends on WP01 (`from_operator_token`), WP18 (template resolution).

### Code map

- `src/charter/context.py:282` `build_charter_context_include` (kind partition + lowercase, no hyphen norm), `_render_doctrine_artifact_include` (~:399, renderers dict keyed on `agent_profile`), `_render_generic_artifact_include` (~:360, duplicated candidate tuple).
- `src/specify_cli/cli/commands/charter/context.py:26` `--include` option help.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP01, WP18.

## Subtasks

### T073 — Route `--include` through `from_operator_token`

**Steps**: In `build_charter_context_include`, normalize the selector kind via `ArtifactKind.from_operator_token` so `agent-profile` (hyphen) resolves to the `agent_profile` renderer. Keep `section`/`artifact` special selectors working.

**Validation**: - [ ] `--include agent-profile:<id>` resolves (human + JSON); underscore/lowercase still work.

### T074 — Collapse renderer table; advertise help

**Steps**: Derive the supported `--include` kinds from the canonical set (remove the duplicated candidate tuple in `_render_generic_artifact_include` and the hand-keyed renderer table where possible). Update the `--include` option help (CLI `context.py:29`) to advertise `agent-profile` (and `template`) alongside directive/styleguide/section.

**Validation**: - [ ] help lists agent-profile + template; no duplicated kind enumeration remains.

### T075 — Wire `template:<id>` resolution (FR-034)

**Steps**: Add `template` handling to `--include`: resolve `template:<mission>/<name>` via WP18's resolver/discovery and render the template content. Catch `CharterPackConfigError` fail-closed here too (parity with WP12 for the context entry).

**Validation**: - [ ] `--include template:software-dev/spec` renders the template; malformed config fails closed.

### T076 — Tests

**Steps**: `tests/charter/test_context_include.py` — agent-profile include (human + JSON), hyphen kinds for siblings (e.g. mission-step-contract), template include, unknown-kind structured error.

**Validation**: - [ ] green; ruff/mypy clean.

## Definition of Done

- [ ] Hyphenated kinds resolve via the canonical resolver; renderer table consolidated; help advertises agent-profile + template; template include works. CC-2 + CC-4 pass.

## Risks

- Don't regress the `section`/`artifact` special selectors.
- Template addressing depends on WP18 — sequence via lanes.json.

## Reviewer Guidance (reviewer-renata)

- Confirm `agent-profile:<id>` renders in BOTH human and JSON (the original bug).
- Confirm the duplicated kind enumeration is gone (CC-4).
- Incorrect doc/contract references are blocking.
