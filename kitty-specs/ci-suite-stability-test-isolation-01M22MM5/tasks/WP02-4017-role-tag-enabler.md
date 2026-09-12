---
work_package_id: WP02
title: '#4017 role-tag observe() source vs destination (enabler)'
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: issue-4017-ci-suite-stability
merge_target_branch: issue-4017-ci-suite-stability
branch_strategy: Planning artifacts for this mission were generated on issue-4017-ci-suite-stability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-4017-ci-suite-stability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-suite-stability-test-isolation-01M22MM5
base_commit: 8214b06e115d12a00701a80e458b35cf8b975b28
created_at: '2026-09-09T09:38:11.329726+00:00'
subtasks: []
phase: Phase 1 - Lane A enabler
history:
- at: '2026-09-09T09:10:03Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/runtime/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/runtime/asset_preparation.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer). Read the mission [spec.md](../spec.md), [plan.md](../plan.md), and [research.md](../research.md) — they carry the grounded mechanism + squad dispositions.

## Objective
Tag observe() entries source-read vs destination-probe and filter destination-probe nodes at the check_assets compare-site so a peer materializing HOME destination is not mis-read as an asset-input change. Do NOT strip PreparedAssets.observations (they feed the fingerprint :361/:439 + cross-family invariants :396-405). (FR-002, C-002)

## Subtasks
### T003 — Role-tag observe()
In asset_preparation.py (observe() ~:177-195) add a role tag (source_read vs destination_probe) per observation. Classify by ROLE (call site: source()/tree(source)=source; asset()/tree(dest)/parents()/finish() inventory=destination), NOT geography (sources can share the HOME prefix under test layouts).
### T004 — Filter at the compare-site
In check_assets (~:482-496) compare only source_read observations for the "asset input changed" raise; destination_probe changes do not raise. Keep the stored observation set intact.
### T005 — Document the intermediate state
Run the WP01 interleave test after this change alone: it should flip from "Global asset input changed" to "global_asset_write_failed: File exists" (role-tag-alone is insufficient — proves the P1 blocker). Record in the Activity Log. Do NOT make it green here (WP03 does).

## Validation
ruff+mypy clean on asset_preparation.py; existing tests/runtime + tests/architectural asset tests stay green (single-process behavior preserved); WP01 interleave now shows File-exists.
## Definition of Done
- observe() role-tagged; check_assets filters destinations; observations NOT stripped; intermediate File-exists documented.
## Reviewer guidance
- Classification by ROLE not geography; observations retained (fingerprint intact); source-drift detection still present (WP03 T009 tests it).
