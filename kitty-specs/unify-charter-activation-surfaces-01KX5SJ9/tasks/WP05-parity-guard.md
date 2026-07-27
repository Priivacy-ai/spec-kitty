---
work_package_id: WP05
title: IC-03 fail-closed parity guard
dependencies:
- WP02
- WP03
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: epic/2519-charter-authoring-lifecycle
merge_target_branch: epic/2519-charter-authoring-lifecycle
branch_strategy: Planning artifacts for this mission were generated on epic/2519-charter-authoring-lifecycle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into epic/2519-charter-authoring-lifecycle unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 3 - Retire and guard
shell_pid: "3753422"
history:
- timestamp: '2026-07-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/consistency_check.py
create_intent:
- tests/doctrine/test_activation_parity_guard.py
execution_mode: code_change
mission_id: 01KX5SJ9P0HXTVWZDJ121JBP60
owned_files:
- src/charter/consistency_check.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP05
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP05 – Fail-closed parity guard (consistency_check)

## Objective
Extend `src/charter/consistency_check.py` to assert derived-vs-config parity, fail-closed (FR-005, NFR-002). This is the regression guard so a #2524-style divergence fails locally, not at CI.

## Context (squad corrections — read carefully)
- `consistency_check.py` today reads raw config activation lists (`:116-136`) vs doctrine/DRG; it does NOT read references.yaml/graph.
- **THREE ID namespaces**: config (`001-…`), references (`DIRECTIVE:001-…`), graph (`directive:DIRECTIVE_001`). `consistency_check.py:199-210` DELIBERATELY punted the config↔graph ID mapping. So:
  - assert **config↔references at ID level** (both slug-based modulo the `KIND:` prefix — this IS the #2524 dangler class),
  - assert **config↔graph at KIND level** (do NOT build the punted ID map — that would grow an ID-reconciliation sub-project).
- **DISJOINT from freshness** (`freshness/computer.py`): that module is in `specify_cli` and imports `charter`, so `consistency_check` CANNOT import it (layer rule) — and must not (freshness=temporal/advisory vs parity=set/fail-closed are different assertions). Keep them disjoint; do NOT reference it.
- The guard is invoked CLI-only today (`pack.py:31-47`) — add a **doctrine-test-tier entry point** so NFR-002 bites in the suite.

## Subtasks
- **T017** Assert every `config.activated_*` entry resolves in `references.yaml` and nothing resolves that is absent from config — at ID level; fail-closed with an actionable message.
- **T018** Assert config↔graph parity at KIND level (not ID); leave the punted ID map alone.
- **T019** Add a doctrine-test-tier entry point (not just the CLI gate) so the guard runs in `tests/doctrine/`.
- **T020** Non-vacuity self-test: plant a config↔derived divergence and assert the guard BITES; confirm no import of `freshness/computer.py` / `specify_cli`.

## Closeout (last correctness WP)
Run the aggregate gate: full `tests/doctrine/` + `tests/charter/` + `tests/architectural/` (the WHOLE dir, not just layer_rules) + graph freshness + `test_no_legacy_terminology.py` + ruff + mypy.

**T021b (required out-of-map fix — WP02 arch-gate regression surfaced by WP03).** `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` FAILS on `charter.compiler::ConfigActivatedRoots` — WP02 added it to `compiler.py`'s `__all__` but no other module imports it (it's used internally only). This blocks the aggregate gate. Fix in `src/charter/compiler.py` (out-of-map, rationale-backed — no other WP is open on that file and this WP owns the arch-gate closeout): either REMOVE `ConfigActivatedRoots` from `__all__` (correct if it's internal-only — most likely) or import it where it was intended to be public. Judge which; do not suppress the test. Record a one-line rationale in the commit.
- Also (NON-blocking, file as follow-up, do NOT fix here): the "Lynn Cole" interview alias (`apply_doctrine_intent_aliases`) is now dead code since activation no longer reads the interview — note it for the mission close.

## Branch Strategy
`spec-kitty agent action implement WP05 --agent <name>` (deps WP02, WP03).

## Definition of Done
- [ ] config↔references ID parity + config↔graph KIND parity, fail-closed; doctrine-tier test bites (non-vacuous).
- [ ] No import/reference of freshness/computer.py; layer rule green; aggregate gate green.
- [ ] `ConfigActivatedRoots` dead-symbol arch failure fixed (T021b); full `tests/architectural/` green; Lynn-Cole dead-code follow-up noted.

## Activity Log

- 2026-07-10T17:47:35Z – claude:sonnet:python-pedro:implementer – shell_pid=3668670 – Assigned agent via action command
- 2026-07-10T18:30:09Z – claude:sonnet:python-pedro:implementer – shell_pid=3668670 – Fail-closed config↔references ID + config↔graph KIND parity guard; doctrine-tier non-vacuity test; ConfigActivatedRoots __all__ fix (arch-gate green)
- 2026-07-10T18:30:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=3753422 – Started review via action command
