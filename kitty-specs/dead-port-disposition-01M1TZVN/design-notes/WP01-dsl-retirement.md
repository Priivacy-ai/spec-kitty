# WP01 design note — mission-DSL v1 retirement (FULL) + `transitions` drop

Mission `dead-port-disposition-01M1TZVN`, lane `kitty/mission-dead-port-disposition-01M1TZVN-lane-a`,
base `1ceba9f22` (Mission A merged; PR #3899 merged 2026-09-06T15:59:58Z — `truststore` already gone,
so the lock was regenerated on top of it). OD2 resolved by the operator as "retire" (`plan.md:26`).

## Drift found while implementing (beyond research.md D-1..D-4)

| # | Where the plan said | What the tree has | Disposition |
|---|---|---|---|
| D-5 | `test_no_dead_symbols.py:3278` pins `strip_v1_keys` | pin is at `:3320` (same `_WIDENED_SCOPE_GRANDFATHERED_470` set) | removed; the set has no staleness ratchet so nothing else moves |
| D-6 | `tests/specify_cli/mission_v1/test_mission_v1_events_unit.py` (trim) | file lives at `tests/missions/test_mission_v1_events_unit.py`; `tests/specify_cli/mission_v1/` held only `test_guards_bulk_edit.py` | trimmed in place; `tests/specify_cli/mission_v1/` now holds `__init__.py` + the new ratchet |
| D-7 | trim only the `validate_mission_v1` halves of the two integration tests | `tests/missions/test_mission_software_dev_integration.py` reads the **pack** (`MissionTemplateRepository.default_missions_root()`), so every class reading `states:`/`transitions:` breaks once T006 deletes the blocks | those classes (`TestStateMachineStructure`, `TestForwardTransitions`, `TestGuardConditions`, `TestStateReachability`) were removed with the schema half; `TestGuardsSection`/`TestInputsAndOutputs`/`TestMissionBlock`/`TestV0BackwardCompatibility` stay (they read tolerated keys). `tests/research/test_research_plan_missions_integration.py` reads `src/specify_cli/missions/{plan,research}/mission.yaml` — a *different* copy that still carries the blocks — so only its schema half was trimmed |
| D-8 | fold gate: "remove the tuple at `:60`" | the tuple was the **only** parametrize case; removing it alone leaves an empty parametrize (vacuous gate, NFR-003) | re-pointed at the two live consumers the gate's own docstring names: `specify_cli.status.bootstrap`, `specify_cli.dossier.indexer` (both call `read_wp_frontmatter` by bare name; AST check passes) |
| D-9 | `_gate_coverage.py:1456` row stays; "verify the census" | `ci_topology_census.json` is **already stale on the base** in `worklist` AND `mapped_dirs` (`--verify-census` on the main checkout says so); no test consumes it (`test_ci_topology_worklist.py` no longer exists; not in CI). Post-retirement `mission_v1` (120 LOC) drops below the 500-LOC worklist floor, so the live derivation no longer lists it | routing row kept as instructed; census NOT regenerated (regeneration folds unrelated churn: `mission_step_contracts`, `zeitgeist_client`, `mapped_dirs` removal). Reported for a follow-up owner |
| D-10 | pack diff "block-only: states/transitions" | the packs also carry `mission:`, `initial:`, `guards:`, `inputs:`, `outputs:` (all in `MISSION_COMPAT_IGNORED_FIELDS`) and a `# v1 State Machine Definition` header | left untouched per the binding block-only rule; flagged as residue for a follow-up. Also `src/specify_cli/missions/{software-dev,plan,research}/mission.yaml` (the `_packaged_missions_dir()` copies) still carry full DSL blocks and `tests/next/test_plan_mission_runtime.py:301-304` asserts the research copy has `states` — outside WP01's owned files |

## RED proof (T001, base tree `1ceba9f22`)

```
FAILED tests/specify_cli/mission_v1/test_import_hygiene.py::test_events_import_does_not_load_transitions
FAILED tests/specify_cli/mission_v1/test_import_hygiene.py::test_events_import_loads_only_the_package_and_events
E   AssertionError: unexpected specify_cli.mission_v1 modules loaded: specify_cli.mission_v1,specify_cli.mission_v1.compat,specify_cli.mission_v1.events,specify_cli.mission_v1.guards,specify_cli.mission_v1.runner,specify_cli.mission_v1.schema
2 failed in 79.97s
# base-tree probe (git archive HEAD src):
hot path loaded: six,transitions,transitions.core,transitions.extensions,transitions.extensions.asyncio,transitions.extensions.diagrams,transitions.extensions.factory,transitions.extensions.locking,transitions.extensions.markup,transitions.extensions.nesting,transitions.version
```

## Lock diff (T007)

`git diff uv.lock | grep '^[-+]name = '` → `-name = "transitions"` only; `six` remains (`python-dateutil`).
Clean-install smoke in a throwaway venv (`UV_PROJECT_ENVIRONMENT=<scratch>/wp01-b-venv uv sync --frozen --all-extras`):
`transitions installed: False`, `six installed: True`, `mission_v1 exports ['emit_event', 'read_events']`, `spec-kitty-cli version 3.2.7rc1`; venv deleted afterwards.

## Same-WP gate follow-through found by the full architectural run (commit 2)

| # | Gate | Cause | Action |
|---|---|---|---|
| D-11 | `test_ruff_format_exclude_ratchet.py` ×2, `test_ruff_format_enforcement.py::test_formatter_debt_exclude_only_names_live_files` | `[tool.ruff.format].exclude` still named the 7 deleted test files | entries removed. Also removed two entries that were **already formatted on the base** (`src/specify_cli/decisions/emit.py`, `tests/status/test_work_package_lifecycle.py`) — pre-existing red of `test_every_exclude_entry_still_genuinely_reformats`, folded because it is a 2-line deletion in an owned file (`pyproject.toml`); the 3 trimmed test files still genuinely reformat, so their entries stay |
| D-12 | `test_no_inert_schema_slots.py::test_live_tree_has_no_new_inert_slots` | the built-in packs' top-level `states:`/`transitions:` keys were the ONLY (name-only) producer match for the charter offering's `MissionOrchestration.states/transitions` slots (`src/charter/offering/missions/models.py:84-85`, `schemas/mission.schema.yaml`). That model is schema-generation-only, nothing constructs it, its classes are pinned dead in `test_no_dead_symbols.py:355-362`, and its parent `orchestration` rows are already in `_inert_slots_baseline.yaml` (unassigned, provisional). `MAX_UNASSIGNED_ENTRIES = 19` "may only ever go DOWN", so the `unassigned` route is closed | four rows added with `owner: mission:dead-port-disposition-01M1TZVN`, `disposition: delete-the-declaration`; `_baselines.yaml` `baseline_entries` 47→51 with `# justification:`; `unassigned_entries` stays 19. **Open item for the orchestrator**: this binds Mission B — `test_a_baseline_entry_does_not_survive_its_owner` fires once all five WPs are approved/done with the rows still present. Either add a rider (WP03 residue, or WP05) deleting the dead `orchestration` state machine from `models.py` + `mission.schema.yaml` (and its `_SYMBOL_ALLOWLIST` pins + the existing `from`/`from_state`/`on`/`orchestration`/`required_artifacts` ledger rows), or re-own the four rows. Not done in WP01: `src/charter/**` is outside its owned files and the parent rows' wire-vs-delete disposition is recorded as un-adjudicated |

> **Orchestrator correction (2026-09-06, after review cycle 1):** the D-12 claim that `test_a_baseline_entry_does_not_survive_its_owner` "fires once all five WPs are approved/done" is wrong at HEAD — that test and `test_every_named_owner_resolves` were deleted upstream in `177e06269` (#3285); the owner-resolution helpers in `_inert_slots.py:574-629` have zero callers. Nothing fires automatically. The four owned rows are nevertheless a promise this mission keeps: WP03 carries rider T014b (delete the `MissionOrchestration` family, regenerate `mission.schema.yaml`, drop both pin categories and the 13 orchestration-family baseline rows). The orphaned owner gate is filed as an upstream gap from the retrospective.
