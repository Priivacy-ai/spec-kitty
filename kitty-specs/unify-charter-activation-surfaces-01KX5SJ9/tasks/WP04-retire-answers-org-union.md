---
work_package_id: WP04
title: IC-02 retire answers + org-feeder union
dependencies:
- WP02
- WP03
- WP06
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: epic/2519-charter-authoring-lifecycle
merge_target_branch: epic/2519-charter-authoring-lifecycle
branch_strategy: Planning artifacts for this mission were generated on epic/2519-charter-authoring-lifecycle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into epic/2519-charter-authoring-lifecycle unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
phase: Phase 3 - Retire and guard
shell_pid: "3721769"
history:
- timestamp: '2026-07-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/doctrine/org_charter.py
create_intent:
- tests/charter/test_answers_inert_and_org_union.py
execution_mode: code_change
mission_id: 01KX5SJ9P0HXTVWZDJ121JBP60
owned_files:
- src/specify_cli/doctrine/org_charter.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP04
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP04 – Retire answers as activation source + org-feeder union

## Objective
Make `answers.selected_*` inert for activation (FR-003, SC-004) and prevent the org-feeder break the squad found: `org_charter.apply_org_charter_to_interview` (`:670-718`) mutated `interview_data.selected_*` so org `required_*` artefacts reached the compiler. Once the compiler reads config (WP02), that feeder is INERT — so **union org `required_*` into `config.activated_*`** instead, or org-required artefacts silently drop. Keep the THIRD ledger (`governance.yaml doctrine.selected_*`) + `spdd_reasons/activation.py` untouched (C-007).

## Subtasks
- **T014** In `org_charter.py`, union org `required_*` into `config.activated_*` via the WP06 append-promotion primitive (hard dep — do NOT hand-roll a second write path, and do NOT use the raw `commit_plan` absent-key branch that seeds the default pack). **Mechanism note (squad):** `apply_org_charter_to_interview` (`:670-723`) unions all 8 `required_<kind>` (directives, tactics, paradigms, styleguides, toolguides, procedures, agent_profiles, step_contracts) — NOT just roots. The WP06 primitive must therefore accept an arbitrary `{kind: [ids]}` set (WP06 is broadened for exactly this) and write the non-root `activated_<kind>` lists directly; a roots-only promotion would silently drop org-required tactics/styleguides/etc. that no activated directive reaches. This dovetails with WP02 T026's direct-root reader — a directly-activated non-root kind must be both **written** here and **read** by the derivation.
- **T015** SC-004 test: editing `answers.selected_*` without a `config.activated_*` change has NO effect on the compiled reference set.
- **T016** Confirm/leave: `governance.yaml doctrine.selected_*` (ledger C) + `spdd_reasons/activation.py` are NOT touched (they read governance/directives, not answers); note `resolver.py:372` `resolve_governance_for_profile` goes stale (latent, no in-tree caller — flag, don't fix here).

## Branch Strategy
`spec-kitty agent action implement WP04 --agent <name>` (deps WP02, WP03).

## Definition of Done
- [ ] org-required artefacts resolve under config-authority; answers inert (SC-004 green).
- [ ] Third ledger + spdd untouched; ruff/mypy clean; layer rule green.

## Activity Log

- 2026-07-10T17:47:26Z – claude:sonnet:python-pedro:implementer – shell_pid=3668670 – Assigned agent via action command
- 2026-07-10T18:11:42Z – claude:sonnet:python-pedro:implementer – shell_pid=3668670 – org-union write path added: apply_org_charter_to_interview now unions all 8 required_<kind> into config.yaml activated_<kind> via promote_activations (WP06), with real built-in default_ids loaded from src/charter/packs/default.yaml (absent-key test proves built-ins preserved, not dropped). SC-004 test proves answers.selected_* edits have zero effect on compile_charter's reference set (control test proves config edits DO change it). Ledger C (governance.yaml) + spdd_reasons/activation.py untouched -- confirmed by inspection + a regression test pinning no governance.yaml write. resolver.py:372 resolve_governance_for_profile still reads interview.selected_directives but has no in-tree caller (latent, flagged not fixed). 13 new tests in tests/charter/test_answers_inert_and_org_union.py; ruff+mypy clean; full tests/charter/ suite (1500 passed) + doctrine/org-pack/layer-rule suites green.
- 2026-07-10T18:12:29Z – claude:opus:reviewer-renata:reviewer – shell_pid=3721769 – Started review via action command
