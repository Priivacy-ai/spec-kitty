# Adversarial Code Review: charter-doctrine-mission-type-configuration-01KSWJVX

**Reviewer**: Claude Sonnet 4.6 (post-implementation, adversarial pass)
**Branch**: `pr/charter-doctrine-mission-type-configuration`
**Base**: `upstream/main`
**Date**: 2026-05-31
**Scope**: WP01–WP15, claims vs actuals, architecture, test quality

---

## VERIFIED — Claims that check out

**WP02 — command-templates directories deleted**
`src/specify_cli/missions/software-dev/command-templates/` is gone. No `command-templates/` subdirectory remains under `src/specify_cli/missions/`. `TestNoOldCommandTemplateDirectories` in `tests/doctrine/missions/test_mission_steps_layout.py` enforces this.

**WP07 — `_COMPOSED_ACTIONS_BY_MISSION` and `_COMPOSED_ACTIONS_FOR_PROMPT` deleted**
`grep -r "_COMPOSED_ACTIONS" src/` returns zero results. Deletions are complete.

**WP07 — `_should_dispatch_via_composition` wired to charter**
`src/specify_cli/next/runtime_bridge.py` and `decision.py` both use lazy imports of `charter.mission_type_profiles.resolve_action_sequence` with `# noqa: PLC0415`. No frozenset fast-path remains.

**WP08 — command_renderer reads from doctrine path**
`src/specify_cli/skills/command_installer.py::_package_templates_dir()` derives the path as `doctrine.__file__.parent / "missions" / "mission-steps" / mission_type`. New layout is wired.

**WP01 — MissionStep unified model**
`src/doctrine/missions/models.py`: `MissionStep` has `display_name`, `step_type: Literal["agent","human_in_loop","integration"]`, `prompt_template`, `model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)`. The `.title` property aliases `display_name`. All WP01 fields present.

**WP04 — `_STEP_YAML_TO_MODEL` field mapping**
`src/doctrine/missions/mission_step_repository.py` maps `"display_name": "display_name"` (not `"title"`) and includes `"step_type": "step_type"`. Mapping is correct.

**WP07 — `resolve_action_sequence` returns correct software-dev sequence**
`src/doctrine/missions/mission_types/software-dev.yaml` lists `action_sequence: [specify, plan, tasks, implement, review]`. Result confirmed in tests and via CLI.

**WP15 — charter activate writes to correct path**
`src/specify_cli/charter_activate.py::activate_mission_type_override()` writes to `.kittify/overrides/mission-types/<id>.yaml`. In-flight WP warnings are emitted. Path contract met.

**FR-016 — `charter mission-type list` returns activated types only**
`src/specify_cli/cli/commands/charter/mission_type.py` calls `existing_mission_types(repo_root)` from `charter.mission_type_profiles`, which reads `PackContext.activated_mission_types`. Filtering path correct.

**Architecture C-004 — `specify_cli` does not import doctrine at module level**
All doctrine imports in `runtime_bridge.py` and `decision.py` are inside function bodies with `# noqa: PLC0415`. No top-level `import doctrine.*` found in `src/specify_cli/`.

**docs/reference/cli-commands.md — live help matches docs**
`charter activate mission-type` and `charter mission-type list` help text matches documented CLI reference.

---

## GAPS / ISSUES

### BLOCKING

**1. C-004 VIOLATION — `doctrine` imports `charter` via `TYPE_CHECKING`**

File: `src/doctrine/missions/mission_step_repository.py`, line 43:

```python
if TYPE_CHECKING:
    from charter.pack_context import PackContext
```

`pytestarch` follows import edges in the AST; `TYPE_CHECKING` guards are not excluded. `tests/architectural/test_layer_rules.py::TestDoctrineIsolation::test_doctrine_does_not_import_charter` **fails** on this branch. This is a hard C-004 violation — the `doctrine ← charter` dependency is inverted.

Fix: use a string literal annotation (`"PackContext"`) and remove the `TYPE_CHECKING` import entirely.

**2. `test_legacy_subpackage_is_gone` fails due to namespace package semantics**

File: `tests/architectural/test_layer_rules.py::TestUnifiedMissionStepBoundary::test_legacy_subpackage_is_gone`

The test calls `importlib.util.find_spec("doctrine.mission_step_contracts")` and asserts `None`. Python treats a directory containing only `__pycache__/` as a namespace package and `find_spec` returns a non-None `ModuleSpec`. The test fails in any environment where pytest has previously imported that path (including every CI run). The source-file check is correct and sufficient; the `find_spec` check is wrong.

**3. `test_template_governance_payload_contract` — 8 tests broken after WP02 deletion**

File: `tests/architectural/test_template_governance_payload_contract.py`

`_IMPLEMENT_TEMPLATE` and `_REVIEW_TEMPLATE` are hardcoded to the deleted paths:
- `src/specify_cli/missions/software-dev/command-templates/implement.md`
- `src/specify_cli/missions/software-dev/command-templates/review.md`

WP08 did not update this file. These 8 tests fail with `FileNotFoundError`. They must be updated to point to the new doctrine paths:
- `src/doctrine/missions/mission-steps/software-dev/implement/prompt.md`
- `src/doctrine/missions/mission-steps/software-dev/review/prompt.md`

**4. `test_no_new_dead_modules` — WP12 migration missing from allowlist**

File: `tests/architectural/test_no_dead_modules.py`

`m_3_2_7_activate_builtin_mission_types` (WP12) is registered via `@MigrationRegistry.register` but the static allowlist `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS` in the architectural test was not updated. Test fails.

**5. `test_no_public_symbol_in_all_is_unimported` — 12 new dead symbols**

File: `tests/architectural/test_no_dead_symbols.py`

12 newly introduced dead symbols not in the exemption list:
- `charter.drg::filter_graph_by_activation` (WP11, unwired)
- `charter.mission_steps::MissionStepRepository` (not re-exported through facade)
- `specify_cli.charter_activate::activate_mission_type_override`, `find_removed_steps`, `scan_inflight_missions`, `emit_step_removal_warnings`, `AffectedMission`, `StepRemovalWarning`
- `specify_cli.cli.commands.charter.activate::activate_cmd`
- `specify_cli.doctrine.org_charter::OrgCharterCycleError`, `OrgCharterExtensionError`
- `doctrine.missions.mission_step_repository::MissionStepRepository`

**6. `test_no_tracked_test_feature_missions` fails**

Test-feature JSON fixture files were committed under a tracked path. The architectural test that prevents test missions from polluting the main repo fails on this branch.

### SIGNIFICANT

**7. WP11 — `filter_graph_by_activation` is written but never wired**

File: `src/charter/drg.py`

`filter_graph_by_activation` is exported in `__all__` but no production call site exists. `doctrine.drg.query.resolve_context` does not invoke it. The WP11 contract ("resolved context respects activated mission types") is unmet in production. The function exists in tests and the facade but has no operational effect on actual DRG resolution.

**8. WP04 — `MissionStepRepository` is dead code in production**

`src/doctrine/missions/mission_step_repository.py` exists with a correct implementation, but `charter.mission_steps` facade does not re-export `MissionStepRepository`. No `src/` module outside the repository file itself imports or instantiates it. WP04 produced a correctly-implemented component that is never called. The stale dead-symbol allowlist entry for `doctrine.missions.models::MissionStep` should also be removed (WP01 gave it callers).

**9. WP13 — `doctrine mission-type list` docstring overclaims three layers, implements one**

File: `src/specify_cli/cli/commands/doctrine.py`

Docstring: *"Enumerates built-in, org, and project mission types from all doctrine layers."*
Implementation: calls only `_collect_built_in_mission_types()`.

The command does not scan org or project layers. Any operator reading the docstring will expect org/project types to appear; they will not. The docstring must be corrected to match the actual behavior.

**10. FR-016 — filtering invariant never tested with a non-default config**

File: `tests/cli/test_charter_mission_type_commands.py`

Every test hits the fallback path where `mission_type_activations` is absent from `config.yaml` and all 4 built-in types are returned. There is no test that writes `mission_type_activations: [software-dev]` and asserts `documentation`, `research`, and `plan` are excluded. The core filtering invariant of FR-016 is untested.

---

## ARCHITECTURE VIOLATIONS

| Violation | File | Severity |
|-----------|------|----------|
| C-004: `doctrine` imports `charter.pack_context` via `TYPE_CHECKING` | `src/doctrine/missions/mission_step_repository.py:43` | BLOCKING |
| `filter_graph_by_activation` exported in `charter.drg.__all__` but unwired | `src/charter/drg.py` | Significant |
| `MissionStepRepository` not reachable through `charter` facade | `src/doctrine/missions/mission_step_repository.py` | Significant |

---

## TEST QUALITY

**NFR-001 performance test is mock-only**
`tests/specify_cli/next/test_runtime_bridge_dispatch.py::TestPerformance::test_resolve_action_sequence_within_100ms` injects a `MagicMock` that returns immediately. It measures Python call overhead only, not YAML loading, filesystem traversal, or `PackContext` construction. The 100ms budget claim is unvalidated against real I/O.

**FR-016 filter untested**
See item 10 in Gaps/Issues. Critical filtering logic has no negative-case test.

**`test_legacy_subpackage_is_gone` conflates two orthogonal invariants**
The source-file check and the `find_spec` check should be separate tests. The `find_spec` check is factually wrong for namespace packages and will produce false failures.

**`test_template_governance_payload_contract` silently broken**
8 tests fail with `FileNotFoundError` — they only appear in the architectural suite, not in the fast/doctrine suite. A developer running `pytest tests/specify_cli/` would not see these failures before pushing.

---

## UNKNOWN / UNCHECKED

- Org/project DRG layer scanning for `doctrine mission-type list` — current scope is built-in only; it is unclear whether this will require a separate WP or in-place extension.
- Real-filesystem NFR-001 performance under load — mocked test is insufficient.
- Whether the `charter.drg.PackContext` re-export is safe to remove as part of dead-symbol cleanup — no external consumer analysis was done.
- End-to-end behavior of org-charter `extends` chains with `mission_type_activations` — not traced.

---

## SUMMARY

| Severity | Count | Items |
|----------|-------|-------|
| BLOCKING (must fix before merge) | 6 | C-004 TYPE_CHECKING violation, namespace package test, 8 broken architectural tests (template governance), dead-modules allowlist, 12 dead symbols, tracked test fixtures |
| SIGNIFICANT | 4 | WP04/WP11 dead code, WP13 docstring overclaim, FR-016 untested |
| MINOR | 3 | Mock-only NFR-001, stale allowlist entry, test conflation |

**Bottom line**: The functional deliverables (model, repository, charter API, CLI commands, deployment pipeline) are implemented correctly. The blocking issues are all in the architectural test suite and the `doctrine → charter` TYPE_CHECKING import. None require rework of the core logic. They should be fixable in one pass.
