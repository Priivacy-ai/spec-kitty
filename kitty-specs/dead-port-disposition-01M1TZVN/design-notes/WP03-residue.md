# WP03 design note — gate-adjacent residue + emitter slice (SHRUNK) + rider T014b

**Mission** `dead-port-disposition-01M1TZVN` · **Lane** `kitty/mission-dead-port-disposition-01M1TZVN-lane-c`
(based on lane-a tip `4213e000b`; shared with WP05) · **HEAD** `d18b0c98c` · **Contract** `contracts/residue-and-emitter-shrunk.md`
· **Decisions honoured** OD7 shrunk (superseded for execution by WP05), OD8 residue rides this mission, rider decision
`01M1W4WZEZZM8DM21JN1ZQY9E6` (T014b). Intended landing spot: `kitty-specs/dead-port-disposition-01M1TZVN/design-notes/WP03-residue.md`
(the lane gate refuses `kitty-specs/` commits; the operator copies it in at consolidation). The FR-011 record sits beside this
file as `emitter-adr-inputs.md`.

## 1. Commits (RED before GREEN, charter C-011)

| # | Hash | Kind | Scope |
|---|---|---|---|
| 1 | `9f8d3a0b3` | RED | pins for T011–T014 (layer-exclusion non-vacuity, package-level `team_projection` ban, facade-demotion pin, `_PUBLIC_SURFACE` wired + re-pinned) — **21 failed / 10 passed** on the lane base |
| 2 | `bb0602713` | GREEN | T011 `constitution` exclusion deleted; T012 `team_projection/` deleted |
| 3 | `f91716551` | GREEN | T013 `ActionContext` alias deleted (2 files); T014 thirteen demotions + 12 test repoints |
| 4 | `bf89e43e8` | RED | T014b pins (schema has no `orchestration`; models module has no family; `Mission` constructible) — **3 failed** |
| 5 | `f008283e1` | GREEN | T014b: family deleted, schema regenerated, fixtures, pins ×2 categories, `Mission` hash refreshed, 14 baseline rows, ratchet counts |
| 6 | `d18b0c98c` | docs | T015 `event_emitter.py` docstring (AST-identical otherwise) |

## 2. Gate states re-checked (gh, 2026-09-06T20:07:02Z)

| PR | State | Consequence |
|---|---|---|
| #3888 | MERGED 10:09:16Z, in lane as `c0054153b` | C-002 satisfied; T011 landed second (SC-008) |
| #3898 | MERGED 15:59:54Z, ADR **Accepted** | FR-012 executable → **WP05** (this lane, after WP03); WP03 kept the shrunk items (docstring + FR-011 record). Files: ADR + `docs/adr/3.x/index.md` + codemap debris + page inventory — no code |
| #3899 | MERGED 15:59:58Z | 15 files (CODEOWNERS, CONTRIBUTING, Makefile, coverage-signals.md, testing-parallel.md, pyproject.toml, pytest.ini, 6× `scripts/**`, `tests/ci/test_sonar_project_version.py`, uv.lock) — **none of the `src/mission_runtime` residue** → OD8 holds |

## 3. Residue table as landed (data-model §5)

| Item | Action | Gate touched | Result |
|---|---|---|---|
| `constitution` exclusion (`test_layer_rules.py:65-73`) | deleted; set now `frozenset()` | `test_layer_rules.py` + new `test_layer_exclusions_name_existing_packages` (the set can never go stale again) | green; C-007 `test_ledger_has_no_stale_entries` green (no ledger edit needed) |
| `team_projection/` tombstone | `git rm -r` (only `__init__.py`); no wheel entry in `pyproject.toml` | `test_no_retired_subsystems.py` — the two submodule rows in `_RETIRED_PATHS` / `_BANNED_IMPORT_PREFIXES` replaced by the package (`src/specify_cli/team_projection`, `specify_cli.team_projection`); `pyproject.toml` TID251 rows untouched (assert absence, stay) | green; `test_pyproject_shape.py` green |
| `ActionContext` alias | `context.py` alias + `__all__` entry + docstring claim deleted; `__init__.py` `_COMPAT_ATTRS` listing + `__getattr__` branch deleted | `tests/mission_runtime/test_facade_demotions.py::TestActionContextAliasDeleted` | `grep -rn "ActionContext\b" src tests docs` → only the pin and historical `docs/plans/**` / CHANGELOG lines |
| 13 test-only `__all__` exports | **demoted** (see §4) | `test_mission_runtime_surface.py::_PUBLIC_SURFACE` (now asserted) + the demotion pin; `test_no_dead_symbols.py` needed **no** re-pin (see §4.3) | green |
| emitter docstring | rewritten per contract §2 + "ADR Accepted, executed by WP05" | none; `test_bridge_parity.py` untouched, green | AST identical apart from the docstring |
| FR-011 record | `emitter-adr-inputs.md` beside this note | — | every anchor re-verified; two deltas (class line +14 from the docstring; ADR now Accepted) |
| dead DSL readers | WP04 (lane-d) — see §6 for the orphan-row hand-off | — | — |

## 4. T014 — the thirteen, enumerated (analysis finding U1)

### 4.1 Where the "13" came from — and why the gate carries no pins for them

`tests/architectural/test_no_dead_symbols.py` at the lane base has **zero** pins mentioning `mission_runtime`,
`content_present_at_primary_tip`, `get_packs_root_default` or `ActionContext`. The gate could not name them because the
facade re-export in `mission_runtime/__init__.py` is itself a `src/` importer: every re-exported name "had a caller"
(`_symbol_has_caller` via the parent/submodule rule, or the T013 re-export-shim auto-exempt). So the census behind the dossier's
"13" was **not** the gate — it was a bare-name text scan. Reconstructing it:

- An AST scan of `src/` outside the package finds **14** root-`__all__` names with no importer:
  `ArtifactPlacementFragment, BranchRefFragment, CheckoutIdentityError, IdentityFragment, MissionArtifactContext,
  MissionArtifactHome, MissionContext, MissionExecutionContext, ResolvedSurface, StatusSurfaceFragment, SurfaceLocations,
  WorkspaceFragment, artifact_home_for, translate_surface`.
- A bare-name grep counts three of them as "used": `MissionContext` (46 hits — all the unrelated
  `specify_cli.context.models.MissionContext`), `MissionExecutionContext` (2 docstring lines in `cli/commands/agent/workflow.py`),
  `CheckoutIdentityError` (3 comment/docstring lines). 14 − 3 = **11** facade names, + `content_present_at_primary_tip` +
  `get_packs_root_default` = **13**. The count reconciles exactly with the dossier's "`mission_runtime/__init__.py` re-export set + the two".

### 4.2 The list as demoted

| # | Name | Defining module | Kept alive by (in-package caller, module path) |
|---|---|---|---|
| 1 | `ArtifactPlacementFragment` | `mission_runtime.context` | `resolution.py` |
| 2 | `BranchRefFragment` | `mission_runtime.context` | `resolution.py` |
| 3 | `IdentityFragment` | `mission_runtime.context` | `resolution.py` |
| 4 | `MissionArtifactContext` | `mission_runtime.context` | `resolution.py`, `artifacts.py` |
| 5 | `StatusSurfaceFragment` | `mission_runtime.context` | `resolution.py` |
| 6 | `WorkspaceFragment` | `mission_runtime.context` | `resolution.py` |
| 7 | `MissionArtifactHome` | `mission_runtime.artifacts` | constructed by `artifact_home_for` (own module; widened-name rescue) |
| 8 | `artifact_home_for` | `mission_runtime.artifacts` | `resolution.py` |
| 9 | `ResolvedSurface` | `mission_runtime.resolution` | constructed by `resolve_artifact_surface` (own module) |
| 10 | `SurfaceLocations` | `mission_runtime.resolution` | built in `resolve_artifact_surface` (own module) |
| 11 | `translate_surface` | `mission_runtime.resolution` | called by `resolve_artifact_surface` (own module) |
| 12 | `content_present_at_primary_tip` | `mission_runtime.lifecycle_phase` | `resolution.py:52` |
| 13 | `get_packs_root_default` | `kernel.paths` | `kernel/env_expand.py:63` |

Root `__all__`: 42 → **31**. `_PUBLIC_SURFACE` (which had silently drifted by five live names — `CheckoutIdentityError`,
`ReadDegradeStrategy`, `ReadDirDecision`, `enforce_checkout_identity`, `resolve_read_dir_or_degrade` — because nothing asserted it)
is now compared to `__all__` by `test_public_surface_is_exactly_all` and pinned at the 31.

### 4.3 What the demotion revealed (the real "re-pin")

Removing the facade import made the dead-symbol gate see the truth for the first time: `resolution.__all__` still *claimed*
`ResolvedSurface` / `SurfaceLocations` / `translate_surface` as cross-module exports with no importer (`__all__` members are never
rescued by own-module use). The gate's own fix #2 ("remove it from `__all__`; it stays as an unexported internal") is the same
disposition one level down, and the file already carried the precedent (`resolve_context_for_mission: demoted`). So the three left
`resolution.__all__` too — **no allowlist row was added anywhere**; the gate is green with zero new pins. The demotion pin's
submodule-`__all__` clause was relaxed to reachability for the same reason (commit 3).

**Not demoted (finding, for the operator):** `MissionContext`, `MissionExecutionContext`, `CheckoutIdentityError` are also
imported by nobody outside the package. They stayed on the root surface because the contract's "13" excludes them and each is a
documented product of the surface (`resolve_action_context` → `MissionExecutionContext`; `mission_context_for` → `MissionContext`;
`enforce_checkout_identity` raises `CheckoutIdentityError`). If the operator wants them off the root too it is a three-line
`__all__` + `_PUBLIC_SURFACE` edit.

### 4.4 Test repoints (12 files)

`from mission_runtime import <demoted>` → `from mission_runtime.<context|artifacts|resolution> import …` in
`tests/integration/test_surface_translation_seam.py`, `tests/mission_runtime/{test_artifact_home, test_artifact_partition,
test_artifact_partition_mapping, test_context_factory_invariant, test_context_fragments, test_resolve_context_for_mission_pure}.py`,
`tests/missions/test_surface_resolution_equivalence.py` (function-scoped), `tests/next/test_query_mode_unit.py` (function-scoped),
`tests/runtime/next/test_merged_mission_terminal.py` (function-scoped), `tests/specify_cli/cli/test_accept_coord_surface_anchor.py`,
`tests/specify_cli/cli/commands/test_accept_birth_cutover_seam.py` (`mission_runtime.ResolvedSurface` attribute access ×2).
The FR-005 surface rule (`test_mission_runtime_surface.py`) scans `src/` only; tests already reached submodules
(`test_lifecycle_phase.py`, `test_consolidated_resolution.py`), so no new class of import was introduced.

## 5. T014b — outcome: **deleted** (stop condition checked, not hit)

**Stop-condition evidence.** `grep -rn "missions.models import\|missions\.models\b" src tests scripts` → every importer takes
`MissionStep`, `MissionStepTemplateRef`, `MissionType` or `IDENTIFIER_PATTERN`; the only reference to `Mission` is
`scripts/generate_schemas.py`'s `register("mission", "charter.offering.missions.models", "Mission", …)` (importlib). No `Mission(`
constructor exists in `src/`, `tests/` or `scripts/`. `orchestration`-key consumers: `src/charter/offering/missions/models.py:188`
(the field itself) and the five schema-validation fixtures under `tests/doctrine/fixtures/mission/` — in-family test data of
`mission.schema.yaml`. **Drift vs the decision record:** it says `tests/doctrine/test_schema_validation.py:17` "only checks that the
schema file is valid"; in fact `test_valid_fixtures_pass` / `test_invalid_fixtures_fail` validate those fixtures against the schema,
so the fixtures had to move in the same commit (they did). Nothing in `packs/` or `src/specify_cli/missions/*/mission.yaml` carries an
`orchestration:` key; `mission.schema.yaml` has no runtime consumer in `src/`.

**Line-number drift (all verified before editing):** `models.py` family at `:59-87`, field `:188` (as the recipe said);
`generate_schemas.py::_mission_fixups` `:385-396` (as said); `test_no_dead_symbols.py` pins at `:355-362` (Category B) and
**`:992-999`** (Category C — recipe said `:1001-1008`).

**Schema diff summary** (`PYTHONPATH=src .venv/bin/python scripts/generate_schemas.py`, then `git diff`): only
`src/charter/offering/schemas/mission.schema.yaml` changed — **62 deletions, 0 insertions**: `definitions.mission_orchestration`
(29 lines), `definitions.mission_state_object` (12), `definitions.mission_transition` (18), `properties.orchestration` (2) and the
`required: - orchestration` entry (1). Every other generated schema is byte-identical.

**Pins:** the three family `SymbolKey`s dropped from both `_CATEGORY_B_GRANDFATHERED_LEGACY` and
`_CATEGORY_C_WP_IN_FLIGHT_UNIFIED_MISSION_STEP`; the `Mission` pin's content hash changed with the field removal and was refreshed
in place by the fail-closed helper (`python -m tests.architectural._refresh_dead_symbol_hashes`, no refusals):
`15e9ee0f…` → `36ecefcd…` in both categories.

**Baseline arithmetic (measured, not derived).** The orchestration family in `_inert_slots_baseline.yaml` is **14 rows**, not the
recipe's 13: `from`(schema), `from_state`(models), `on`×2, `orchestration`×2, `required_artifacts`×2, `states`×2 (owned),
`transitions`×2 (owned), `to`×2 — the recipe listed `required_artifacts×2` and `to×2` but summed to 13. Rows 65 → 51;
`len(BASELINE_SLOTS)` **51 → 37**; `unassigned` **19 → 9**. `_baselines.yaml` carries the new numbers with a `# justification:`
naming T014b; `_inert_slots.py::MAX_UNASSIGNED_ENTRIES` lowered 19 → 9 (shrink-only; nothing consumes it today, so this is
mirror-keeping — noted as an out-of-map one-liner). `test_no_inert_schema_slots::test_live_tree_has_no_new_inert_slots` green: deleting
the declarations exposed no new inert slot.

**Fixtures:** `valid/minimal.yaml`, `valid/with-agent-profile.yaml`, `invalid/bad-key-type.yaml` lost their `orchestration:` blocks;
`invalid/invalid-agent-profile-pattern.yaml` now carries the bad profile on a `steps[]` entry (its old defect lived inside the deleted
block); `invalid/missing-orchestration.yaml` (which would have become *valid*) was replaced by `invalid/retired-orchestration-key.yaml`
so `additionalProperties: false` is exercised against the retired key.

## 6. Orchestrator hand-off from WP04 — NOT executable on lane-c (please re-route)

The Activity Log asked T014 to prune the two orphaned `_WIDENED_SCOPE_GRANDFATHERED_470` rows
`runtime.next.decision::derive_mission_state` / `::evaluate_guards`. Lane-c is based on **lane-a**, and WP04's deletion lives on
**lane-d** (unmerged, `commits_ahead 1`): on this lane `decision.py` still defines both functions (`:190`, `:221`), so pruning the
rows reds `test_no_public_symbol_in_all_is_unimported` here (verified: the gate listed both as offenders in the run before I restored
the rows). The set has no staleness ratchet, so the orphan rows do not red anything once WP04 lands; they are debris to prune in
whichever WP is based on a tree that already contains WP04's deletion — WP05 (this lane, once lane-c is rebased over the merged
target) or the consolidating merge. Recorded via `add-history`.

## 7. FR-011 emitter record — content

See `emitter-adr-inputs.md` beside this note: dossier §3.1/§3.2 verbatim, the verification-log line, and a 16-row re-verification table at
HEAD `d18b0c98c`. Deltas: the concrete class/`for_feature`/`seed_from_snapshot` anchors moved from `:23/:43/:60` to `:37/:57/:74` because
of the WP03 docstring (AST otherwise identical); the ADR is now Accepted. All 29 `sync_emitter` sites (engine 16, bridge 13), the
`TYPE_CHECKING`-only engine import (`:80`), the two constructions (`:1552`, `:2739`), the two seeds (`:1614`, `:2745`), the buffer swap
(`:2149-2150`), the flush into the inner no-op (`:2187`) vs the `DecisionGitLog` wrap (`:1560-1565`), `_BufferingRuntimeEmitter` (`:69`,
C-006), the parity oracle (`:1131-1152`, untouched, green), and `spec_kitty_events 9.1.6` `VOLATILE_EVENT_TYPES` were confirmed unchanged.

## 8. FR-012 follow-up text (contract §4) — superseded, kept for the record

"Execute RuntimeEventEmitter disposition ADR: resolve the name collision per ADR; one pass over the 29 `sync_emitter` sites (vocabulary +
signature); adjudicate the flush-target defect explicitly; update `test_side_effect_sinks_are_actually_reached` in the same PR if the capture
is removed; respect C-006/C-007." Gate: ADR merged AND Accepted; Mission A merged. **Both gates are met and the operator already minted it
as WP05** (`tasks/WP05-emitter-adr-execution.md`, this lane, depends on WP03) — no further mint is needed.

## 9. RED-first evidence

| Commit | Command | Result |
|---|---|---|
| `9f8d3a0b3` (on base `4213e000b`+RED) | `.venv/bin/pytest tests/architectural/test_layer_rules.py::TestLayerCoverage::test_layer_exclusions_name_existing_packages tests/architectural/test_no_retired_subsystems.py::test_no_retired_paths_exist tests/architectural/test_no_retired_subsystems.py::test_no_retired_import_targets_exist tests/mission_runtime/test_facade_demotions.py tests/architectural/test_mission_runtime_surface.py::TestMissionRuntimeSurface::test_public_surface_is_exactly_all -q -p no:cacheprovider` | **21 failed, 10 passed** (the 10: `test_no_retired_import_targets_exist`, `test_canonical_name_still_public`, 8 keep-the-symbol nodes for names already reachable) |
| `bf89e43e8` (on `f91716551`+RED) | `.venv/bin/pytest tests/doctrine/test_schema_validation.py::test_mission_schema_has_no_orchestration_state_machine tests/doctrine/missions/test_models.py::TestMissionOrchestrationFamilyRetired -q -p no:cacheprovider` | **3 failed** |
| T015 | no RED pin: the docstring is superseded by WP05 in this same lane, so a prose pin would be deleted within the lane; proven instead by AST identity | — |

## 10. Verification table (all foreground, `timeout 600`, `-p no:cacheprovider`, max `-n 3 --dist loadfile`)

| After | Command | Result |
|---|---|---|
| commit 2 | `.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_retired_subsystems.py tests/architectural/test_pyproject_shape.py -q` | **72 passed** |
| commit 3 (first pass) | `.venv/bin/pytest tests/mission_runtime tests/kernel tests/architectural/test_mission_runtime_surface.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_layer_rules.py tests/integration/test_surface_translation_seam.py tests/missions/test_surface_resolution_equivalence.py tests/next/test_query_mode_unit.py tests/runtime/next/test_merged_mission_terminal.py tests/specify_cli/cli/test_accept_coord_surface_anchor.py tests/specify_cli/cli/commands/test_accept_birth_cutover_seam.py tests/specify_cli/shims/test_direct_commands.py -q -n 3 --dist loadfile` | **949 passed, 4 skipped, 1 failed** (`test_no_public_symbol_in_all_is_unimported`: the three `resolution.__all__` names + the two prematurely pruned `decision::` rows) |
| commit 3 (after the fix) | `.venv/bin/pytest tests/architectural/test_no_dead_symbols.py tests/mission_runtime/test_facade_demotions.py tests/architectural/test_mission_runtime_surface.py tests/mission_runtime/test_consolidated_resolution.py tests/integration/test_surface_translation_seam.py tests/mission_runtime/test_placement_seam.py -q -n 3 --dist loadfile` | **267 passed** |
| commit 5 | `.venv/bin/pytest tests/doctrine/test_schema_validation.py tests/charter/test_schemas.py tests/charter/test_schemas_additive_fields.py tests/charter/test_schemas_selection.py tests/doctrine/missions tests/architectural/test_no_inert_schema_slots.py tests/architectural/test_ratchet_baselines.py tests/architectural/test_gate_remedy_presence.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_layer_rules.py tests/architectural/test_no_retired_subsystems.py tests/doctrine/test_schema_generation_integrity.py tests/architectural/test_refresh_dead_symbol_hashes.py -q -n 3 --dist loadfile` | **660 passed, 1 skipped** |
| commit 6 | `.venv/bin/pytest tests/runtime/test_bridge_parity.py tests/contract/test_identity_contract_matrix.py tests/specify_cli/events/test_decision_log_coord.py tests/status/test_producer_conformance.py tests/architectural/test_no_legacy_terminology.py -q -n 3 --dist loadfile` | **47 passed** |
| final HEAD `d18b0c98c` | `.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_retired_subsystems.py tests/architectural/test_pyproject_shape.py tests/architectural/test_no_inert_schema_slots.py tests/architectural/test_ratchet_baselines.py tests/architectural/test_gate_remedy_presence.py tests/architectural/test_no_legacy_terminology.py tests/architectural/test_mission_runtime_surface.py tests/mission_runtime tests/kernel tests/doctrine/missions tests/doctrine/test_schema_validation.py -q -n 3 --dist loadfile` | **1319 passed, 4 skipped** |
| every commit | `.venv/bin/ruff check <changed .py>` / `.venv/bin/ruff format --check --force-exclude <changed .py>` | All checks passed; formatted (files in the formatter-debt exclude list are skipped by `--force-exclude`) |
| every commit | `.venv/bin/mypy src/mission_runtime/__init__.py src/mission_runtime/context.py src/mission_runtime/lifecycle_phase.py src/mission_runtime/resolution.py src/kernel/paths.py src/charter/offering/missions/models.py src/runtime/next/event_emitter.py` | Success: no issues found |
| T013 | `grep -rn "ActionContext\b" src tests docs \| grep -v "MissionExecutionContext\|ActionContextError"` | only the new pin + historical `docs/plans/**`, `docs/changelog/CHANGELOG.md`, `docs/reports/**`, one ADR line — no live reference |
| T015 | AST of `event_emitter.py` with the docstring stripped, HEAD vs HEAD~1 | identical; hunks `@@ -1 +1 @@`, `@@ -2,0 +3,3 @@`, `@@ -4,6 +7,17 @@` all inside the docstring |

No baseline-red attribution was needed: every red seen was caused by (and fixed within) this WP. `make test-fast` was not run (it shells
through `uv run`, forbidden on the lane); its directories `tests/unit tests/status tests/cli tests/specify_cli/runtime` contain no importer
of the demoted names (the AST scan over all of `tests/` found exactly the 12 repointed files) — `tests/status/test_producer_conformance.py`
was run explicitly as an `event_emitter` referrer.

## 11. Deviations from the contract / prompt (each with reason)

1. **No `test_no_dead_symbols.py` re-pins for the 13** — the gate never pinned them (§4.1); the live pin was the unasserted
   `_PUBLIC_SURFACE`, which is now wired and re-pinned (out-of-map file, OD8 rationale logged).
2. **Three extra `resolution.__all__` demotions** (`ResolvedSurface`, `SurfaceLocations`, `translate_surface`) — forced by the gate
   once the facade import was gone; same disposition, gate's own fix #2, existing in-file precedent (§4.3).
3. **`_inert_slots.py::MAX_UNASSIGNED_ENTRIES` lowered** (not an owned file) — one-line shrink to keep the documented cap truthful.
4. **T014b fixtures + `tests/doctrine/missions/test_models.py` + `tests/doctrine/test_schema_validation.py` edited** (not owned) —
   the schema-validation test validates fixtures (decision record was inaccurate); the pins had to live somewhere.
5. **Baseline counts 37/9, not the recipe's 38/10** — measured; the recipe undercounted `to`/`required_artifacts` duplicates (§5).
6. **WP04 orphan-row prune not done** — not executable on lane-c (§6).
7. **No `kitty-specs/` writes from the lane** — `research/emitter-adr-inputs.md` and this note are delivered in the scratchpad
   `wp03-c-planning-artifacts/` for the operator to copy in.
8. **`_PUBLIC_SURFACE` also gained five live names** it had drifted away from — required to make the new assertion true; all five
   have `src/` importers.

## 12. Spec Kitty tool frictions

- The commit guard printed `ACTIVE_WP_SCOPE_VIOLATION` warnings for every out-of-map file (23 distinct paths across the six commits);
  warnings only, as the prompt predicted. `lanes.json` write_scope was not regenerated for the rider's six files.
- `git add … src/specify_cli/team_projection` after `git rm -r` fails with `fatal: pathspec 'src/specify_cli/team_projection' did not
  match any files` (the deletion is already staged) — a git footgun, not Spec Kitty's; re-issued without the pathspec.
- `ruff format --check --force-exclude` silently skips files in `[tool.ruff.format].exclude` and reports only the remainder ("4 files
  already formatted" for 18 inputs) — expected, but easy to misread as partial coverage.
