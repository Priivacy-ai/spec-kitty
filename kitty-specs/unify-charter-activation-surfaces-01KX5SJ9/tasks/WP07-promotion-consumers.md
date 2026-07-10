---
work_package_id: WP07
title: Promotion consumers - migration + interview wiring (FR-007)
dependencies:
- WP06
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: epic/2519-charter-authoring-lifecycle
merge_target_branch: epic/2519-charter-authoring-lifecycle
branch_strategy: Planning artifacts for this mission were generated on epic/2519-charter-authoring-lifecycle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into epic/2519-charter-authoring-lifecycle unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
phase: Phase 3 - Promotion consumers
shell_pid: "3611945"
history:
- timestamp: '2026-07-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/charter/interview.py
create_intent:
- src/specify_cli/upgrade/migrations/m_unify_charter_activation.py
- tests/specify_cli/upgrade/test_unify_charter_activation_migration.py
execution_mode: code_change
mission_id: 01KX5SJ9P0HXTVWZDJ121JBP60
owned_files:
- src/specify_cli/cli/commands/charter/interview.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP07
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP07 – Promotion consumers: migration + interview wiring

## Objective
Wire BOTH consumers of the WP06 append-promotion primitive: the config-seeded migration (FR-006, zero-drop, promotes answers-only paradigms) and the interview command (FR-007 append-promotion of captured selections). DEFER only the re-interview replace/deselect refinement to a tracked follow-up.

## Context
- Migration host: `src/specify_cli/upgrade/migrations/` (registry `BaseMigration`, sibling of the existing `m_3_2_0rc35_*` charter-pack migrations). It may import `charter` (layer-legal).
- The migration promotes `answers.selected_<kind>` MINUS `config.activated_<kind>` into config via the WP06 primitive, for every kind (not roots-only — matches the broadened primitive and the direct-root reader). Promote, never drop.
- **Real repo state (squad-measured — the fixture must be synthetic).** In THIS repo today `activated_directives` (25) and `selected_directives` (25) are the **same 25**, differing only in ID-form (`039-…` stem vs `DIRECTIVE_039`) — exact parity, NOT a 25-vs-24 skew (the 24 figure predates `DIRECTIVE_046` landing in answers.yaml). Every other kind shows config as a strict superset with **zero** answers-only entries (`selected_paradigms` is empty; config has 8). So the reverse-skew path has NO live example to reproduce — T025's fixture must be a **constructed synthetic** project, not a mirror of the current repo.
- Interview: after `write_interview_answers` (`interview.py:332-345`), call the WP06 primitive to append-promote the captured selections into config.

## Subtasks
- **T023** Migration: config-seeded reconcile — promote answers-only roots (incl. paradigms) into `config.activated_*` via the WP06 primitive; zero drop.
- **T024** Interview wiring: append-promote the captured interview selections into `config.activated_*` (FR-007) via the WP06 primitive (orchestrate from the CLI command; primitive stays in `charter`).
- **T025** Migration fixture — a **constructed synthetic** project (NOT the live repo, which has no reverse-skew) with an answers-only directive AND an answers-only paradigm not present in `config.activated_*` → 0 dropped after migration (both promoted). Add a one-line note (spec + a follow-up) that the re-interview REPLACE/deselect refinement is deferred; this slice ships append-only.

## Branch Strategy
`spec-kitty agent action implement WP07 --agent <name>` (deps WP06).

## Definition of Done
- [ ] Migration promotes answers-only roots incl. paradigms; 0 drop on the skew fixture.
- [ ] Interview append-promotes selections into config (FR-007); ruff/mypy clean; layer rule green.
- [ ] Re-interview deselect refinement documented as a deferred follow-up.

## Activity Log

- 2026-07-10T16:21:17Z – claude:sonnet:python-pedro:implementer – shell_pid=3509554 – Assigned agent via action command
- 2026-07-10T17:01:58Z – claude:sonnet:python-pedro:implementer – shell_pid=3509554 – Migration + interview promote selections into config via WP06 primitive; real built-in default_ids at both call sites; synthetic reverse-skew fixture
- 2026-07-10T17:02:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=3611945 – Started review via action command
- 2026-07-10T17:08:05Z – user – shell_pid=3611945 – Verified. CRITICAL default_ids check PASS: BOTH call sites pass default_ids=load_default_pack_ids() (migration m_unify_charter_activation.py:311/323; interview.py:~419) and default.yaml uses activated_<kind> keys that match the promotion keys, so absent-key built-in preservation is NON-INERT. Non-vacuous absent-key tests at BOTH sites: migration test_apply_absent_key_preserves_real_builtins_not_bare_list (omits key, asserts real builtins subset + PackContext three-state) and interview test_interview_promotes_selections_preserving_builtins_on_absent_key (live CLI, absent config). Migration registered via @MigrationRegistry.register + migration_id, auto-discovered (sibling of m_3_2_0rc35). T025 fixture synthetic (answers-only DIRECTIVE_010 + domain-driven-design paradigm, real ids), 0-drop + promotion asserted. Interview wiring invoked live after write_interview_answers, best-effort. 21 tests pass; ruff clean; mypy clean on both WP07 files under authoritative full-package run (single-file BaseMigration/Any errors are isolation artifacts, also present on sibling + base). Deferred deselect note present (spec FR-007 + tasks.md:140). Scope clean (4 files). No layer/terminology violations.
