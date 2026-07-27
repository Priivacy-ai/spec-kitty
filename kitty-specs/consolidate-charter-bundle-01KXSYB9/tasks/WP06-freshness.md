---
work_package_id: WP06
title: 'Freshness on charter.yaml + retire #2758/#2759 stopgaps'
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-011
- NFR-001
- NFR-002
tracker_refs:
- '#2773'
- '#2758'
- '#2759'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/charter_runtime/freshness/computer.py
- tests/charter/test_bundle_content_hash.py
- tests/charter/synthesizer/test_orchestrator_resynthesize.py
- tests/charter/synthesizer/test_performance_envelopes.py
- tests/specify_cli/charter_freshness/test_computer.py
- tests/specify_cli/charter/test_freshness_hash_unification.py
- tests/specify_cli/charter_runtime/test_preflight_one_pass.py
- tests/specify_cli/charter_runtime/test_freshness_activation_visibility.py
- tests/integration/test_charter_status_freshness.py
role: implementer
tags: []
shell_pid: "398991"
shell_pid_created_at: "1784382545.72"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML.

## Objective
Point the freshness content-hash at `charter.yaml` (via the WP01 `content_hash_files`), rework/retire the `charter.md`-hash staleness (Landmine 2), resolve the spurious-authoring-staleness question, and remove the now-moot #2758/#2759 stopgaps.

**Authoritative**: [`data-model.md`](../data-model.md) **Landmine 2** (+ the spurious-staleness extension), [`contracts/manifest-v2.md`](../contracts/manifest-v2.md) M3. C-002: this file lives in `specify_cli.charter_runtime` (may import charter; the parity read stays here).

## Context / grounding
- `computer.py:137 _BUNDLE_FILES`, `:270 _compute_charter_source` (charter.md-hash staleness — the OLD model), `:324 _compute_synced_bundle`, `:372 fresh-seed early-exit`, `:475` content-hash read, the **#2759** parity read (`_activation_parity_drift_reason:499` / `_PARITY_DRIFT_REMEDIATION:144`).
- ⚠ NOTE (post-tasks squad): the **#2758 `first_missing_bundle_file` is NOT in `computer.py`** — it lives in `bundle.py:187` (WP01, kept/auto-narrowed) with its caller in `_synthesis.py` (WP03). This WP owns ONLY the #2759 removal.

## Subtasks
### T024 — Freshness content-hash over charter.yaml
- `_BUNDLE_FILES` / the content-hash input → `charter.yaml` (through the WP01 `content_hash_files` single point). Preserve the #2732 recipe (per-file BOM-strip/CRLF, write-side stamps, `built_in_only` normalization, fresh-seed early-exit `:372`).
### T025 — Rework/retire charter.md-hash staleness + spurious-staleness
- Retire `_compute_charter_source`'s charter.md-hash staleness (charter.md is a never-resolving companion). Do NOT carry a self-referential `charter_hash` into charter.yaml.
- **Decide + test** the spurious-authoring-staleness question (alphonso MINOR-3): either (a) ground the freshness signal on `catalog`↔`activation` parity so an authored governance-only edit doesn't flip stale; or (b) document that authored edits read stale until the next synth (and confirm that's acceptable to freshness-consuming gates). Record the choice in `traces/decisions.md`.
### T026 — Retire the #2759 references-parity read (computer.py only)
- Remove the **#2759** references-parity read (`_activation_parity_drift_reason` / `_PARITY_DRIFT_REMEDIATION`) from `computer.py` — moot once freshness reads charter.yaml. Update `test_preflight_one_pass`, `test_freshness_activation_visibility`. (The #2758 `first_missing_bundle_file` disposition is WP01's, its caller WP03's — NOT this WP.)
### T027 — Tests
- Freshness reflects a mutation (SC-001); no permanent-stale reachable; unchanged charter.yaml → identical hash (SC-005/#2732); NFR-002 subprocess-spy = 0.
- **Landmine-2 assertion**: `charter.yaml.metadata` carries NO `charter_hash` field (no self-reference).
- **Hash-narrowing fallout (WP01 review, orphan-assigned here)**: WP01's `BUNDLE_CONTENT_HASH_FILES` narrowing (4→charter.yaml) breaks tests that seed the four legacy files but no charter.yaml. Update these owned tests to the charter.yaml world: `tests/charter/test_bundle_content_hash.py` (hash over charter.yaml), `tests/charter/synthesizer/test_orchestrator_resynthesize.py::TestBundleContentHashRecomputesOnDrift` (drift charter.yaml, not governance.yaml), `tests/charter/synthesizer/test_performance_envelopes.py` (NFR-002 freshness perf), plus the freshness suites already owned (`test_computer` — narrow the mirror `_BUNDLE_FILES`; `test_freshness_activation_visibility`). Also fix the stale "four files" docstring in `compute_bundle_content_hash` (bundle.py is WP01's — leave a note; or a rationale-backed one-line doc fix).

## ATDD (red-first)
Red-first through `compute_freshness`: mutate charter.yaml, assert the signal flips; assert no permanent-stale dead-end (RED until T024).

## Branch Strategy
Base `feat/consolidate-charter-bundle` per `lanes.json` (dep WP01); merges back to `feat/consolidate-charter-bundle`.

## Definition of Done
- Freshness over charter.yaml; charter.md-hash staleness retired; spurious-staleness decided + tested; #2758/#2759 removed; #2732 preserved; NFR-002 spy 0.
- ruff + mypy --strict clean; complexity ≤15.

## Reviewer guidance
- Verify no self-referential `charter_hash`; verify the #2732 recipe is intact (single `content_hash_files` point); verify the spurious-staleness decision is recorded + tested; verify #2758/#2759 code paths are gone.

## Activity Log

- 2026-07-18T13:11:19Z – claude:sonnet:python-pedro:implementer – shell_pid=298325 – Assigned agent via action command
- 2026-07-18T13:48:17Z – claude:sonnet:python-pedro:implementer – shell_pid=298325 – Freshness content-hash re-pointed to charter.yaml (WP01 content_hash_files single point, #2732 recipe preserved). Landmine 2: charter.md-hash staleness retired outright from _compute_charter_source (missing/invalid/fresh only, never stale, no self-referential charter_hash). Spurious-authoring-staleness decision: (b) -- authored charter.yaml edits read stale until next synth, always self-healing (traces/decisions.md D9-D12). #2759 activation-parity read removed from computer.py (moot: activation relocates into the hash-covered charter.yaml). Gates: ruff clean, mypy --strict computer.py has 3 pre-existing unrelated errors (follow_imports=skip single-file-check artifact on charter.* imports, confirmed pre-existing via HEAD diff, reduced 5->3 by deleting dead _charter_hash_of), complexity <=15. 120/120 targeted tests green (8 owned files + necessary fallout in charter_preflight/_fixtures.py + test_runner.py + test_freshness_residue.py, broken by WP01's bundle narrowing / this WP's charter_source rework, unowned by any WP). NFR-002 subprocess-spy=0 test added. Known out-of-scope pre-existing red: tests/upgrade/test_unified_bundle_migration.py (5 tests, bundle_validation tracked/derived checks -- unrelated subsystem, WP01/WP07 territory, not freshness).
- 2026-07-18T13:49:08Z – claude:opus:reviewer-renata:reviewer – shell_pid=398991 – Started review via action command
- 2026-07-18T13:54:16Z – user – shell_pid=398991 – APPROVED. Landmine 2: _compute_charter_source's charter.md-hash-vs-metadata staleness retired outright (missing/invalid/fresh only, never stale); no self-referential charter_hash reintroduced (grep clean; dead _charter_hash_of deleted -> mypy 5->3). Freshness now reads charter.yaml via single _BUNDLE_FILES=('charter.yaml',) mirroring WP01 BUNDLE_CONTENT_HASH_FILES; #2732 recipe intact (compute_bundle_content_hash single point, built_in_only short-circuit :379, legacy fresh-seed early-exit, unchanged-yaml->identical-hash test green). #2759 _activation_parity_drift_reason/_PARITY_DRIFT_REMEDIATION removed from computer.py (only prose refs remain). Spurious-staleness decision (b) RULED SOUND: authored-only charter.yaml edit reads stale until next synth, but the preflight gate (_attempt_auto_refresh, runner.py:405) auto-runs 'charter synthesize' on a clean tree which re-stamps the manifest -> fresh; dirty tree blocks with 'commit or stash and retry' -> heal on commit. No permanent-stale dead-end; SC-001 mutation-flip + reconcile-to-fresh tested through the real compute_freshness path (test_freshness_activation_visibility.py:130/146/167). Recorded traces/decisions.md D9-D12. NFR-002 subprocess-spy=0 test present+green (fresh/stale/missing branches). Leeway: 3 unowned fallout files (_fixtures.py, test_runner.py, test_freshness_residue.py) confirmed owned by no other WP, broken by WP01 narrowing / this WP's charter_source rework, minimally scoped (seed_charter_yaml helper + re-pin stale->invalid preserving the blocking invariant) -- ACCEPTABLE leeway per ownership-map rationale. Gates: ruff clean, complexity <=15, mypy 3 pre-existing charter.* follow_imports=skip Path-from-Any artifacts (confirmed pre-existing vs base, zero new), 109/109 owned+fallout tests green. Anti-pattern checklist all PASS/N-A (no dead code, no synthetic fixtures, no silent empty return, no frozen-surface touch).
