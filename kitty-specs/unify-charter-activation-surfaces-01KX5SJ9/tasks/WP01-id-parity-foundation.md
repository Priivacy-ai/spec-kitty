---
work_package_id: WP01
title: ID-form parity foundation (stem to canonical)
dependencies: []
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: epic/2519-charter-authoring-lifecycle
merge_target_branch: epic/2519-charter-authoring-lifecycle
branch_strategy: Planning artifacts for this mission were generated on epic/2519-charter-authoring-lifecycle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into epic/2519-charter-authoring-lifecycle unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Foundation
shell_pid: "3456697"
history:
- timestamp: '2026-07-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_config_stem_parity.py
execution_mode: code_change
mission_id: 01KX5SJ9P0HXTVWZDJ121JBP60
owned_files:
- src/charter/kind_vocabulary.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP01
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP01 – ID-form parity foundation (stem ↔ canonical)

## Objective
The #1 correctness guard (spec C-006). Provide a charter-package resolver that maps a `config.activated_*` slug-stem (e.g. `001-architectural-integrity-standard`) to its canonical artefact id (`DIRECTIVE_001` / URN `directive:DIRECTIVE_001`) **exactly** as the live `DoctrineService`/DRG resolution does — and **rejects** (never silently drops) a malformed/unresolvable stem. This is the foundation both the derivation switch (WP02) and the promotion primitive (WP06) build on. A silent drop here removes a directive AND its entire transitive closure (tactics→styleguides→toolguides→procedures) from references+graph, invisibly.

## Context
- Read `../spec.md` (C-006), `../plan.md` (Post-Plan Corrections, IC-01), `../research.md`.
- **Use the correct direction.** `resolve_config_id` (`kind_vocabulary.py:223-274`) is URN→stem — the WRONG direction. The function that already does **stem→canonical URN** with reject-not-drop (raises `UnknownArtifactIdError`) is **`resolve_artifact_urn(kind, config_id)`** (`kind_vocabulary.py:176-220`), already wired into `activate.py:93` / `deactivate.py:66,99`. VERIFY/reuse `resolve_artifact_urn` for the derivation; the net-new work here is likely just the T003/T004 fixtures, not new resolver logic. Stay in the `charter` package (layer rule).

## Subtasks
- **T001** Verify/reuse `resolve_artifact_urn` (stem→canonical, per kind) as the `charter`-package resolver, matching the live DoctrineService/DRG resolution used by the dangler test's `_compiled_reference_id_suffixes()`.
- **T002** On a stem that does not resolve to a known artefact, RAISE a clear error (reject-not-drop) — never return None/skip that would shrink the set silently.
- **T003** Fixture: assert stem↔canonical round-trip for ALL 25 activated directives in `.kittify/config.yaml` (and spot-check other kinds).
- **T004** Non-vacuity: a deliberately malformed stem is REJECTED (raises), proving the guard is not inert.

## Branch Strategy
Planning/base = merge target = `epic/2519-charter-authoring-lifecycle`. `spec-kitty agent action implement WP01 --agent <name>`.

## Definition of Done
- [ ] Stem→canonical resolver present in `charter`, matching live resolution; ruff+mypy clean; complexity ≤15.
- [ ] Malformed stem rejected (not dropped); 25-directive parity fixture + non-vacuity test green.
- [ ] No import of `specify_cli` from `charter` (layer rule).

## Activity Log

- 2026-07-10T15:38:50Z – claude:sonnet:python-pedro:implementer – shell_pid=3438452 – Assigned agent via action command
- 2026-07-10T15:51:15Z – claude:sonnet:python-pedro:implementer – shell_pid=3438452 – resolve_artifact_urn reused as-is for stem->canonical (reject-not-drop, UnknownArtifactIdError). Hardened _iter_artifact_paths to rglob built-in dirs (tactics/styleguides/toolguides nest into category subfolders e.g. built-in/testing/) matching BaseDoctrineRepository's live built-in-rglob loading -- non-recursive glob was silently missing real activated tactics, a C-006 violation caught by the T003 spot-check. New tests/charter/test_config_stem_parity.py: 35 tests, all pass (25-directive full parity sweep + 5-kind spot-check + non-vacuity malformed-stem rejection). ruff check: All checks passed. mypy: Success, no issues. Full tests/charter/test_kind_vocabulary.py + test_kind_cascade_exhaustive.py + tests/doctrine/drg/test_kind_mapping_totality.py (57 tests) + tests/architectural/test_layer_rules.py (16 tests) + charter activate/deactivate/list CLI tests (37 tests) all green -- no regressions from the rglob change.
- 2026-07-10T15:51:37Z – claude:opus:reviewer-renata:reviewer – shell_pid=3456697 – Started review via action command
- 2026-07-10T15:57:03Z – user – shell_pid=3456697 – PASS. resolve_artifact_urn reused as-is (stem->canonical, raises UnknownArtifactIdError) — no duplicate resolver. In-file _scan_roots/_iter_artifact_paths fix: recursive rglob for built-in dirs vs non-recursive glob for layer/project, mirroring BaseDoctrineRepository (base.py:169 rglob built-in / base.py:146 glob project); old non-recursive glob silently missed nested tactics (built-in/analysis, built-in/architecture) — genuine C-006 silent-drop bug, within owned file. T003 fixture real: parametrized over all 25 actual activated_directives from .kittify/config.yaml (count pinned ==25), asserts urn startswith directive:DIRECTIVE_ AND resolve_config_id round-trip; +5-kind spot-check. T004 non-vacuity: 3 malformed stems assert pytest.raises(UnknownArtifactIdError). 35 tests pass; ruff clean; mypy clean; layer rule intact. Scope limited to owned kind_vocabulary.py + new test. Filled mission issue-matrix rows unknown->in-mission (accurate: multi-WP mission in progress). Restored a charter-test-leaked synthesis-manifest.yaml (test-isolation bug, unrelated to WP01).
