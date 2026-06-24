# Data Model — Target topology for `agent/mission.py` decomposition (#2056)

No persistent data structures change. This captures the **module topology** (shim + seams) and the **behavior-preservation invariants** that constrain the decomposition.

## Target topology

```
src/specify_cli/cli/commands/agent/
  mission.py                      # THIN SHIM: app=Typer(name="mission"), registers
                                  # 8 commands, re-exports every previously-public
                                  # + test-patched symbol. No business logic.
  mission/                        # (new package) OR sibling modules:
    feature_resolution.py         # Seam D — _find_feature_directory & friends, _safe_load_meta,
                                  #   _read_feature_meta, _build_setup_plan_detection_error
    parsing.py                    # Seam C — tasks.md/spec.md parsers, owned-files validation,
                                  #   JSON emit shims (_emit_json/_with_cli_version/_with_mission_aliases)
    cmd_branch_context.py         # Seam B — branch_context + _inject_branch_contract + branch helpers
    cmd_create.py                 # Seam B — create_mission (internally decomposed)
    cmd_check_prerequisites.py    # Seam B — check_prerequisites + emit helpers
    cmd_setup_plan.py             # Seam B — setup_plan (internally decomposed) + _commit_to_branch
    cmd_finalize_tasks.py         # Seam B — finalize_tasks (internally decomposed) + finalize helpers
    cmd_accept_merge.py           # Seam B — accept_feature, merge_feature, worktree helpers
    cmd_record_analysis.py        # Seam A — record_analysis + 2 analysis helpers

src/specify_cli/coordination/
  commit_router.py                # EXISTING — receives relocated _planning_commit_worktree /
                                  #   _resolve_planning_placement IF #2056 merges before #2058
                                  #   (else those are deleted as dead). Reconcile
                                  #   _stage_finalize_artifacts_in_coord_worktree with the
                                  #   existing _stage_artifacts_in_coord_worktree.
```

Module-vs-package split (`mission.py` file + `mission_*.py` siblings, vs `mission/` package) is a plan-phase decision; either preserves the import path `specify_cli.cli.commands.agent.mission`.

## Invariants (behavior preservation — MUST hold post-decomposition)

| ID | Invariant | Enforced by |
|---|---|---|
| INV-1 | `specify_cli.cli.commands.agent.mission.app` exposes exactly 8 commands with the exact names + flags in research §1. | Golden CLI characterization test (NEW). |
| INV-2 | JSON envelope shape (success + error) under `--json` is byte-identical for all 8 commands. | `test_json_envelope_strict.py` (extend) + golden test. |
| INV-3 | Every symbol currently importable/patchable as `mission.<name>` (esp. `locate_project_root`, `run_command`, `get_emitter`, `is_saas_sync_enabled`, `_find_feature_directory`, `_show_branch_context`, `validate_feature_structure`, `CommitToBranchResult`, all command fns) remains so via shim re-export. | Existing ~50 test files (no patch-target churn). |
| INV-4 | `lifecycle.py` keeps resolving `agent_feature.create_mission/setup_plan/finalize_tasks/_build_setup_plan_detection_error`. | Shim re-export + `test_wrapper_delegation.py`. |
| INV-5 | `tasks.py` keeps resolving `_parse_requirement_refs_from_tasks_md` and (until #2058) `_resolve_planning_placement`/`_planning_commit_worktree` — from their post-move home. | Import update in tasks.py if relocated; tasks tests. |
| INV-6 | `finalize_tasks --validate-only` mutates ZERO bytes on disk (in-memory bootstrap only). | `test_finalize_tasks_validate_only_readonly.py`. |
| INV-7 | Planning-commit routing (primary-kind → primary branch; coord-kind → coord worktree) unchanged; `commit_for_mission` stays the single entry point. | `test_write_surface_coherence.py`, `test_wp02_seam_migration_equivalence.py`. |
| INV-8 | One-way imports: seam modules → lower layers only; never seam → shim. `commit_router` never imports from `mission`/seams. | `test_shared_package_boundary.py` style guard (consider extending). |
| INV-9 | Every extracted phase-helper of a mega-function has complexity <=15 and a focused unit test (Sonar new-code coverage). | ruff C901 + new tests in same PR. |

## Frozen CLI contract (machine-checkable)

8 commands; flags enumerated in research.md §1. The golden test asserts this set as the immutable contract. Any diff to command names, flag names, defaults, or JSON envelope keys is a regression, not a refactor.
