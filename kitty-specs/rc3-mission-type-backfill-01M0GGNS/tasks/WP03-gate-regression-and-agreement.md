---
work_package_id: WP03
title: Gate regression + cross-authority agreement + predicate regression
dependencies:
- WP01
- WP02
requirement_refs:
- FR-009
planning_base_branch: pr/rc3-mission-type-backfill
merge_target_branch: pr/rc3-mission-type-backfill
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-mission-type-backfill. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-mission-type-backfill unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-mission-type-backfill-01M0GGNS-lane-b
base_commit: aab27d78ed512c52d12b5d612a9fe82bb9f5cd12
created_at: '2026-08-21T07:13:23.591052+00:00'
subtasks:
- T007
- T008
- T009
history: []
authoritative_surface: tests/specify_cli/test_backfill_mission_type_gate_agreement.py
create_intent:
- tests/specify_cli/test_backfill_mission_type_gate_agreement.py
execution_mode: code_change
owned_files:
- tests/specify_cli/test_backfill_mission_type_gate_agreement.py
tags: []
tracker_refs: []
wp_code: WP03
---

# Work Package WP03 — Gate regression + cross-authority agreement

## Objective

Prove the reused census gate reds-then-greens around the backfill, that the writer's candidate set
equals the audit's `legacy-key-only` set (non-vacuously), and pin the predicate-correctness
regression that fails against the rejected `registered ∧ roster` predicate.

## Context & anchors

- Gate entry point: `spec-kitty doctor mission-type --fail-on <states>` →
  `specify_cli.cli.commands._mission_type_audit.run_mission_type_audit(repo_root, json, mission, fail_on)`
  (takes an injected `repo_root` — drive it over synthetic temp repos; this repo is 410/410 resolved).
- Completeness gate: `--fail-on legacy-key-only`. Release-safety gate:
  `--fail-on legacy-key-only,typeless,error` (corrected states — operator B).
- Audit classifier for the agreement test: `_mission_type_audit.audit_mission_types` /
  `classify_mission_type` (import in the TEST only — the migration→cli edge is fine in a test).

## Subtasks

### T007 — Cross-authority agreement + completeness gate (`pytestmark = [pytest.mark.integration]`)
- `test_writer_candidates_equal_audit_legacy_key_only`: over a corpus that INCLUDES a blank-type
  `typeless` (`{"mission_type":"","mission":"software-dev"}`) AND a non-string legacy
  (`{"mission":123}`), assert the writer's candidate set (missions it would write or flag
  needs_manual) == the audit's `legacy-key-only` set, and the writer SKIPS the blank-type and
  non-string (audit `typeless`) — non-vacuous (R-3).
- `test_completeness_gate_red_then_green` (AC-11): `doctor mission-type --fail-on legacy-key-only`
  exits non-zero before backfill, zero after (resolving candidates), via `run_mission_type_audit`.

### T008 — Predicate-correctness regression (`pytestmark = [pytest.mark.regression]`)
- `test_unactivated_builtin_written_and_release_gate_greens` (AC-5): a temp repo with
  `{"mission":"research"}` where `research` is NOT in `.kittify/config.yaml`'s
  `mission_type_activations` → backfill WRITES `mission_type: research`, and
  `--fail-on legacy-key-only,typeless,error` greens. (This RED-fails against `registered ∧ roster`.)
- `test_release_gate_reds_on_typeless_and_needs_manual` (AC-6 gate side): the release-safety gate
  reds while a `typeless` mission or a non-resolving `needs_manual` (legacy-key-only) mission remains.

### T009 — Command docs
- Document the release-safety predicate (`legacy-key-only,typeless,error`) and the residual
  `unknown`-typo gap (M3 coordination) in the command docstring/help. (Changelog entry is closeout.)

## Definition of Done

- All WP03 tests green, each red-first; the AC-5 test verified to RED against the rejected predicate
  (note the evidence in the tracer). `ruff` + `mypy` clean.

## Terminal state

`done` when the above hold.

## Added coverage (squad #3 anti-laziness — m2)

- **m2**: AC-5's temp repo is a SINGLE `{"mission":"research"}` mission (research NOT in
  `mission_type_activations`) so the release-gate-green is attributable to the research write (no
  unrelated legacy-key-only/typeless missions lingering to red it for the wrong reason).
