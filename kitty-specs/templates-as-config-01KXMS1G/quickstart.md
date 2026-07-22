# Phase 1 Quickstart: Implement and Validate Issue #2658

## Preconditions

- Work from the Spec Kitty-created implementation worktree for each future work package, not from an existing unrelated checkout.
- Load the implementation action context before editing.
- Keep issue #2658's scope boundary: do not implement #2659–#2661.
- Start with failing acceptance behavior through the existing mission creation or plan setup entry point.

## Implementation Path

1. Add red doctrine/context tests for exact software-development mapping, explicit null mappings, determinism, and the existing hot-path budget.
2. Project the doctrine mapping into `ResolvedMissionType` lazily/cached without consulting profile defaults.
3. Add red selector tests for present key, null mapping, missing key, and unresolved mapped filename.
4. Introduce the narrow two-stage selection seam and retain the existing five-tier file resolver unchanged.
5. Add red production-path tests, then migrate specification creation and plan scaffold/pristine comparison to the shared seam.
6. Run the temporary software-development parity scaffold, record the proof, and delete the scaffold before final review.
7. Run enduring targeted tests and architecture/terminology/type/style gates.

## Targeted Validation

Use the repository's environment/runner conventions resolved during task authoring. The expected validation surfaces are:

```text
tests/charter/test_resolved_mission_type_context.py
tests/doctrine/
tests/specify_cli/core/test_feature_creation.py
tests/specify_cli/core/test_mission_creation_specify_started.py
tests/specify_cli/cli/commands/agent/test_mission_create*.py  # read-only adjacent regression
tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
tests/integration/test_specify_plan_commit_boundary.py
tests/e2e/test_cli_smoke.py              # only the affected smoke cases
tests/architectural/test_no_parity_scaffold.py
```

Also run Ruff on changed Python files, mypy strict on affected modules, the repository terminology guard for changed prose/code, a focused performance assertion for resolved mission-type context, and pytest-cov plus diff-cover enforcing at least 90% coverage of changed/new production lines against each lane base. Do not substitute a full-suite run for targeted red/green evidence during scoped work packages.

## Completion Evidence

- Exact doctrine mappings, including null, reach resolved context.
- `spec` and `plan` readers select filenames from activated configuration.
- Existing override winners are unchanged.
- Null/missing/unresolved cases select no software-development template and produce actionable diagnostics.
- Effective shipped software-development content is unchanged.
- No file or symbol matching the transitional parity scaffold remains.
- No enumeration, runtime discovery, meta-less fallback, copy-step, derived-tree deletion, or version change entered the diff.
