---
work_package_id: WP07
title: Migration + fail-loud + git-class (fold four files + activation → charter.yaml)
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP06
requirement_refs:
- FR-010
- FR-011
- NFR-003
- C-003
tracker_refs:
- '#2773'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/migrations/
create_intent:
- src/specify_cli/upgrade/migrations/m_unify_charter_activation_finalize.py
- tests/upgrade/test_consolidate_charter_bundle_migration.py
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/migrations/m_unify_charter_activation_finalize.py
- src/specify_cli/state/contract.py
- .gitignore
- src/doctrine/versioning.py
- tests/upgrade/test_consolidate_charter_bundle_migration.py
- tests/upgrade/test_unified_bundle_migration.py
- tests/merge/test_profile_charter_e2e.py
- tests/specify_cli/test_state_contract.py
- tests/specify_cli/test_state_gitignore_migration.py
- tests/charter/test_sync.py
- tests/charter/test_sync_authority_paths.py
- tests/charter/test_sync_paths.py
- tests/charter/test_sync_references.py
- tests/charter/test_worktree_charter_via_canonical_root.py
- tests/charter/test_charter_context_spdd_reasons.py
- tests/charter/test_resolver.py
- tests/charter/test_resolved_mission_type_context.py
- tests/charter/test_activate_resolves_no_answers_edit.py
- tests/charter/test_chokepoint_overhead.py
- tests/charter/test_context.py
- tests/charter/test_bundle_validate_cli.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/test_no_dead_modules.py
- tests/architectural/_baselines.yaml
- pyproject.toml
- CHANGELOG.md
role: implementer
tags: []
shell_pid_created_at: "1784399681.13"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "976981"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML.

## Objective
Author the one-pass, idempotent, **fail-loud** migration that folds the four legacy bundle files **plus the relocated `activated_*`** into `charter.yaml`, retires the four from emission/manifest/gitignore/state-contract, and adds the `config.yaml` `charter:` pointer. Lands LAST so no consumer is orphaned.

**Authoritative**: [`contracts/migration-contract.md`](../contracts/migration-contract.md) (MG1–MG6), [`data-model.md`](../data-model.md) INV-2/5/6.

## Context / grounding
- Fold body pattern = `src/doctrine/versioning.py:299 migrate_v1_to_v2` (yaml→yaml write-and-stamp), NOT the rc35 refresh-only shape. Register via `@MigrationRegistry.register`; `runs_on_worktrees = False`; lazy `charter.*` imports (C-002).
- **Existing seed migrations (paula MAJOR-3)**: `m_unify_charter_activation.py` (encodes the now-REVERSED "config is the activation authority" + promotes INTO config), `m_3_2_0rc35_default_charter_pack.py` + `m_3_2_0rc35_activate_builtin_mission_types.py` (write `activated_*` INTO config, `detect()` on absence).
- `state/contract.py:420-462` (git-class), `versioning.py:165 get_bundle_schema_version` (reads `metadata.yaml:176`; NOTE — the symbol is `get_bundle_schema_version`, not `read_bundle_schema_version`).
- ⚠ **TWO `metadata.yaml`**: touch ONLY `.kittify/charter/metadata.yaml`; NEVER `.kittify/metadata.yaml` (project identity).

## Subtasks
### T028 — The fold migration
- Read `governance.yaml`+`directives.yaml`+`metadata.yaml`+`references.yaml` + `config.yaml activated_*` → compose `charter.yaml` (governance/directives/catalog/flat-activation/metadata.bundle_schema_version=2). Delete the four; remove `activated_*` from config; add `charter: .kittify/charter/charter.yaml` pointer.
- **VERBATIM** activation-list copy — absent key stays absent (NEVER →`[]`), `[]` stays `[]` (MG1/SC-008).
- **Fail-loud** (MG3/C-003): a charter op on four-present/no-charter.yaml raises the re-homed #2530 with a "run the migration" message; no silent legacy read.
- **Ordering (MG6)**: sequence STRICTLY AFTER the seed migrations (their post-state = config has `activated_*` = this fold's pre-state); reconcile/annotate `m_unify_charter_activation`'s reversed invariant; idempotent against re-seeding.
### T028b — Fix `test_unified_bundle_migration.py` (orphan-assigned)
- WP01's manifest v2 (tracked/derived → `content_hash_files`; `derived_files=[]`) + the four-file retirement break `tests/upgrade/test_unified_bundle_migration.py` (5 `bundle_validation` tracked/derived manifest-shape tests). Update them to the v2 manifest + charter.yaml world.

### T028c — FINAL TEST-RECONCILIATION SWEEP (lands last; sees the fully-merged behavior)
This WP is the mission finalizer — after all behavior WPs (WP01–06, WP08, WP09) merge, update EVERY residual charter-behavior test to the charter.yaml world and confirm aggregate-green (NFR-005). The WP04 review catalogued the ripple (all verified WP04-caused, green at WP04's parent):
- **sync retirement** — `test_sync.py` (10), `test_sync_authority_paths.py` (5), `test_sync_paths.py` (1), `test_sync_references.py` (2): `sync()` no longer scrapes/writes the triad; update to `synced=False`/charter.yaml semantics.
- **resolver/mission_type** — `test_resolver.py` (14), `test_resolved_mission_type_context.py` (1): loaders auto-follow to charter.yaml.
- **spdd_reasons** — `test_charter_context_spdd_reasons.py` (9): activation re-pointed to charter.yaml.
- **worktree/chokepoint/activate** — `test_worktree_charter_via_canonical_root.py` (2: no derivative governance.yaml), `test_chokepoint_overhead.py` (3 errors: bundle-priming retired), `test_activate_resolves_no_answers_edit.py` (1 collection error: imports retired `write_extraction_result`).
- **context** — `test_context.py::TestBuildContextV2` (4): governance now `DIR-*` from charter.yaml. (Owned here, NOT WP05, to avoid the WP05/WP08 overlap on this file.)
- **dead-symbols arch gate** — `tests/architectural/test_no_dead_symbols.py`: `charter_yaml_io::OWNED_SECTIONS`/`UnknownCharterYamlSectionError` (WP01 `__all__`, no external importer — red at WP04 parent too) + the deferred `charter.extractor::Extractor` (dead production post-WP04). Wire the write-helper caller / trim `__all__` / update the allowlist so the gate is green.
- **Final proof**: `PWHEADLESS=1 uv run pytest tests/charter tests/architectural tests/upgrade -q` green (or the residual reds are pre-existing-unrelated, explicitly listed).

### T029 — state/contract + .gitignore
- `state/contract.py`: mark `charter.yaml` git-tracked; retire the four ignored entries. `.gitignore`: remove the four; do not ignore charter.yaml.
### T030 — versioning.py repoint
- `get_bundle_schema_version:165` reads `bundle_schema_version` from `charter.yaml.metadata` (not the retired `metadata.yaml:176`). ⚠ Its callers (the rc35 migrations `m_3_2_0rc35_charter_bundle_v2.py`, `..._charter_manifest_defaults_repair.py`, `charter_bundle.py:38`) use it as a **`detect()` gate** — re-verify re-sourcing to charter.yaml does NOT perturb migration-ordering detection (paula MAJOR-3).
### T031 — Tests
- `test_consolidate_charter_bundle_migration.py`: legacy fixture → fail-loud pre-migration; migrate; assert charter.yaml composed (flat activation) + four gone + config activation-free + pointer added; re-run → 0 changes; absent-key fidelity; ordering after seed migrations. `test_state_contract.py` / `test_state_gitignore_migration.py`: charter.yaml tracked, four retired.

## ATDD (red-first)
Red-first through the migration runner on a legacy fixture: assert a charter op fails loud before migration, and idempotent 0-changes after (RED until T028).

## Branch Strategy
Base `feat/consolidate-charter-bundle` per `lanes.json` (deps WP01/02/03/04/06); merges back to `feat/consolidate-charter-bundle`.

## Definition of Done
- Deterministic idempotent fail-loud fold; verbatim activation copy; sequenced after + reconciles the seed migrations; charter.yaml git-tracked; four retired; versioning repointed. ONLY `.kittify/charter/metadata.yaml` touched.
- ruff + mypy --strict clean; complexity ≤15.

## Reviewer guidance
- Verify idempotency + fail-loud + verbatim absent-key handling; verify the migration ordering vs the 3 seed migrations; verify `.kittify/metadata.yaml` (project identity) is untouched.

## Activity Log

- 2026-07-18T16:13:32Z – claude:sonnet:python-pedro:implementer – shell_pid=705476 – Assigned agent via action command
- 2026-07-18T17:34:01Z – claude:sonnet:python-pedro:implementer – shell_pid=705476 – Migration + reconciliation complete against fully-merged state. Foreground (orchestrator-verified): migration+state 81 passed, reconciliation sweep 157 passed, dead-symbols+dead-modules+ratchet green, ruff clean, mypy consistent-with-existing-migration-pattern (subclass-Any is pre-existing follow_imports=skip). (Implementer completed the code + stalled on the whole-suite background run; orchestrator verified gates foreground + finished handoff + added the dead-modules/_baselines arch-gate leeway fixes.)
- 2026-07-18T17:34:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=874561 – Started review via action command
- 2026-07-18T18:00:57Z – user – Moved to planned
- 2026-07-18T18:01:25Z – claude:sonnet:python-pedro:implementer – shell_pid=918908 – Started implementation via action command
- 2026-07-18T18:34:24Z – claude:sonnet:python-pedro:implementer – shell_pid=918908 – Cycle-2 complete; 681 passed foreground, ruff clean.
- 2026-07-18T18:34:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=976981 – Started review via action command
