# Coverage-Parity Inventory (FR-004d)

Mission `scopesource-gate-followup-01KY6S9P`, WP05 (M-inv gate artifact).

**Provenance.** The census-tier deletion (removal of the public
`pre_review_gate.derive_test_scope` census duplicate and its
`filter_groups=`/`composite_routing=` params) landed in WP04, commit
`d19bd566c` ("feat(WP04): retire dead census tier + SOURCE_MISMATCH +
head-path rewire + parity (157->156)"). That commit's test-surface migration
already discharged FR-004a/FR-004b/FR-004c/M-mut in full — every row below
was verified against `d19bd566c`'s diff and the current on-branch test files,
not written aspirationally. WP05's remaining scope was limited to this
inventory (FR-004d), a docstring scrub of stale `derive_test_scope`
references in `test_pre_review_gate_integration.py` (T029), and confirming
the WP `create_intent` file `test_gate_coverage_census_topology.py` is
unnecessary (see the closing note).

Columns: `former test` — the pre-WP04 test identity; `disposition` —
retired / migrated / migrated-forward / deleted; `surviving id or rationale`
— the current test id that carries the coverage forward, or an explicit
"not carried forward because X".

## FR-004a — census-only tests (deleted file + retired `_derive` tests)

| former test | disposition | surviving id or rationale |
|---|---|---|
| `tests/review/test_census_parity.py` (whole file, 81 lines, comparing the `pre_review_gate.py` census duplicate against `scope_source.py`'s copy) | deleted | Not carried forward because both compared copies no longer coexist — `pre_review_gate.py`'s duplicate is gone, so there is nothing left to diff against `GateCoverageScopeSource`. The single-source-of-truth property it guarded is now structural (only one census implementation exists), and the remaining live-derivation guarantees are covered by `tests/architectural/test_pre_review_scope_singlesource.py` (migrated in place, see FR-004/M-mut section below) and `tests/review/test_scope_source.py::test_internal_scope_derivation_pinned_golden` (below). |
| `test_pre_review_gate_engine.py::test_per_shard_group_contributes_its_own_test_globs_and_excludes_core_misc` | migrated-forward | `tests/review/test_pre_review_gate_engine.py::test_per_shard_group_contributes_its_own_test_globs_and_excludes_core_misc` (same name, unchanged assertions). The module-level `_derive()` helper it calls was retargeted from `pre_review_gate.derive_test_scope(...)` onto `GateCoverageScopeSource(...)` + `pre_review_gate._scope_result_from_source(...)` — the test body did not need to change, only the helper underneath it. |
| `test_pre_review_gate_engine.py::test_recall_over_precision_ambiguous_file_gets_every_focused_group` | migrated-forward | `tests/review/test_pre_review_gate_engine.py::test_recall_over_precision_ambiguous_file_gets_every_focused_group` — same mechanism (shared `_derive()` helper retarget). |
| `test_pre_review_gate_engine.py::test_composite_group_with_nonempty_cone_contributes_cone_roots` | migrated-forward | `tests/review/test_pre_review_gate_engine.py::test_composite_group_with_nonempty_cone_contributes_cone_roots` — same mechanism. |
| `test_pre_review_gate_engine.py::test_composite_group_with_empty_cone_is_a_no_coverage_warn_not_clean` | migrated-forward | `tests/review/test_pre_review_gate_engine.py::test_composite_group_with_empty_cone_is_a_no_coverage_warn_not_clean` — same mechanism. |
| `test_pre_review_gate_engine.py::test_catch_all_only_file_is_excluded_and_scope_warns` | migrated-forward | `tests/review/test_pre_review_gate_engine.py::test_catch_all_only_file_is_excluded_and_scope_warns` — same mechanism. |
| `test_pre_review_gate_engine.py::test_unmatched_file_is_excluded_and_scope_warns` | migrated-forward | `tests/review/test_pre_review_gate_engine.py::test_unmatched_file_is_excluded_and_scope_warns` — same mechanism. |

**Note on the "6 `_derive` tests":** the WP prompt (T026) anticipated these
6 tests would need to be *removed* because they "exercised only the deleted
duplicate." Investigation of `d19bd566c` shows WP04 instead retargeted the
shared `_derive(changed_files)` module helper (`test_pre_review_gate_engine.py:179`)
from `pre_review_gate.derive_test_scope(...)` onto
`GateCoverageScopeSource(repo_root=_DUMMY_ROOT, filter_groups_override=FAKE_GROUPS,
composite_routing_override=FAKE_ROUTING)` + `pre_review_gate._scope_result_from_source(...)`
— a strictly better outcome than deletion: all 6 tests survive unmodified
and now exercise the surviving `GateCoverageScopeSource` composition instead
of the retired duplicate, so no coverage is lost and no test body needed to
change.

## FR-004b — the 2 oracle tests (repointed to literal goldens)

| former test | disposition | surviving id or rationale |
|---|---|---|
| `tests/review/test_scope_source.py::test_internal_scope_derivation_micro_parity_with_old_derive_test_scope` (parametrized ×4, diffed `GateCoverageScopeSource.file_to_scope` against a live call to `pre_review_gate.derive_test_scope`) | migrated | `tests/review/test_scope_source.py::test_internal_scope_derivation_pinned_golden` (same 4 parametrize cases). The self-referential-oracle comparison (`old_scope = pre_review_gate.derive_test_scope(...)`) was replaced with the literal `frozenset` values that comparison produced immediately before the deletion (`{"tests/status"}`, `{"tests/git", "tests/git_ops"}`, `frozenset()`, `frozenset()`), captured over the SAME `_MICRO_GOLDEN_GROUPS`/`_MICRO_GOLDEN_ROUTING` fixtures. This keeps it a genuine pinned-behaviour regression guard rather than a comparison against a function that no longer exists. |
| `tests/review/test_pre_review_gate_engine.py::test_scope_result_from_source_reconstructs_full_breakdown_for_narrowing_source` (asserted `scope == incumbent` where `incumbent = pre_review_gate.derive_test_scope(...)`) | migrated | `tests/review/test_pre_review_gate_engine.py::test_scope_result_from_source_reconstructs_full_breakdown_for_narrowing_source` (same name). The `incumbent` oracle comparison was replaced with a literal assertion (`assert set(scope.test_targets) == {"tests/status", "tests/specify_cli/status", "tests/architectural/test_execution_context_parity.py"}`), pinning the exact value the retired oracle used to produce. The `matched_shard_groups`/`empty_cone_composite_dirs`/`excluded_scope_files` assertions above it (NFR-001's full-breakdown guard) are unchanged. |

## FR-004c — the 8 verdict-diff tests (migrated to `scope_source=`/`evaluate_with_scope`)

All 8 live in `tests/review/test_pre_review_gate_engine.py`. Each row's
"former" column cites the pre-WP04 call shape
(`pre_review_gate.evaluate_pre_review_gate([...], repo_root=..., baseline=...,
filter_groups=FAKE_GROUPS, composite_routing=FAKE_ROUTING)`); the surviving
id is unchanged (same test function name in place) but the body now either
(a) builds the equivalent `ScopeResult` literal directly and calls
`pre_review_gate.evaluate_with_scope(<ScopeResult>, repo_root=..., baseline=...)`
— the C-002 keep-live tail — or (b) for the one end-to-end test, injects a
real `GateCoverageScopeSource(..., filter_groups_override=..., composite_routing_override=...)`
via the new `scope_source=` kwarg on `evaluate_pre_review_gate`.

| former test (unique coverage intent) | disposition | surviving id or rationale |
|---|---|---|
| `test_empty_scope_short_circuits_before_running_or_diffing` (empty-cone scope must short-circuit before `run_scoped_tests_at_head` is ever called) | migrated | `tests/review/test_pre_review_gate_engine.py::test_empty_scope_short_circuits_before_running_or_diffing` — now calls `evaluate_with_scope(_VALIDATORS_EMPTY_CONE_SCOPE, repo_root=_DUMMY_ROOT, baseline=None)`; `_VALIDATORS_EMPTY_CONE_SCOPE` is the literal `ScopeResult` the retired `derive_test_scope` call used to produce for the validators fixture. |
| `test_run_that_does_not_complete_degrades_to_no_coverage_warn` (a run that never completes degrades to `NO_COVERAGE` warn, not a crash) | migrated | `tests/review/test_pre_review_gate_engine.py::test_run_that_does_not_complete_degrades_to_no_coverage_warn` — now calls `evaluate_with_scope(_GIT_NONEMPTY_SCOPE, repo_root=_DUMMY_ROOT, baseline=None)`. |
| `test_terminal_interruption_remains_typed_in_gate_verdict` (SIGKILL/SIGTERM interruption stays typed, not swallowed) | migrated | `tests/review/test_pre_review_gate_engine.py::test_terminal_interruption_remains_typed_in_gate_verdict` — same `evaluate_with_scope(_GIT_NONEMPTY_SCOPE, ...)` retarget. |
| `test_uncomputable_baseline_none_degrades_to_warn_and_surfaces_all_failures` (a `None` baseline degrades to `UNVERIFIED_BASELINE` and surfaces every current failure) | migrated | `tests/review/test_pre_review_gate_engine.py::test_uncomputable_baseline_none_degrades_to_warn_and_surfaces_all_failures` — same retarget. |
| `test_sentinel_baseline_degrades_to_warn` (a sentinel/placeholder baseline degrades to `UNVERIFIED_BASELINE`) | migrated | `tests/review/test_pre_review_gate_engine.py::test_sentinel_baseline_degrades_to_warn` — same retarget. |
| `test_pre_existing_failure_does_not_block_no_new_failures_outcome` (a failure already present at baseline does not block `NO_NEW_FAILURES`) | migrated | `tests/review/test_pre_review_gate_engine.py::test_pre_existing_failure_does_not_block_no_new_failures_outcome` — same retarget. |
| `test_new_failure_is_surfaced_via_the_real_diff_baseline` (a genuinely new failure surfaces via the real `diff_baseline` as `NEW_FAILURES`) | migrated | `tests/review/test_pre_review_gate_engine.py::test_new_failure_is_surfaced_via_the_real_diff_baseline` — same retarget. |
| `test_end_to_end_new_failure_detected_via_real_subprocess_and_real_diff` (full composition: real subprocess pytest run + real `diff_baseline`, only the scope-derivation inputs synthetic) | migrated | `tests/review/test_pre_review_gate_engine.py::test_end_to_end_new_failure_detected_via_real_subprocess_and_real_diff` — this one keeps the `evaluate_pre_review_gate(...)` entry point (it is the only surviving production call site) but swaps `filter_groups=`/`composite_routing=` for `scope_source=GateCoverageScopeSource(repo_root=tmp_path, filter_groups_override=..., composite_routing_override=...)`. |

## M-mut — the mutation-bite (migrated in place, not to a new file)

| former test | disposition | surviving id or rationale |
|---|---|---|
| `tests/architectural/test_pre_review_scope_singlesource.py` (whole file: 10 tests proving census derivation consults the LIVE `.github/workflows` topology via `tests/architectural/_gate_coverage.py`, not a hardcoded/shadowed table) | migrated-forward (in place) | Same file, same 10 test names, unchanged assertions — retargeted from `pre_review_gate.derive_test_scope(...)` / `pre_review_gate._glob_matches_file` / `pre_review_gate._glob_to_pytest_target` / `pre_review_gate.NAMED_CATCHALL_GROUPS` / `pre_review_gate.resolve_excluded_catchall_groups` onto `scope_source.GateCoverageScopeSource(repo_root=..., *_override=...).scope_breakdown(...)` / `scope_source._glob_matches_file` / `scope_source._glob_to_pytest_target` / `scope_source._NAMED_CATCHALL_GROUPS` / `scope_source._resolve_excluded_catchall_groups` (via a new `_live_impl()` helper at the top of the file). The two mutation-bite tests specifically — `test_stale_filter_groups_map_changes_the_derived_scope` and `test_composite_routing_override_is_genuinely_consulted_not_only_filter_groups` — are unchanged in substance: they still prove a stale/hand-authored `filter_groups_override`/`composite_routing_override` genuinely changes the derived scope (i.e. the derivation isn't shadowing its input with a hardcoded table). The live-CI-topology proof (reading real `.github/workflows` via `tests/architectural/_gate_coverage.py`) is fully preserved — `_gate_coverage.py` itself was not touched. |

## Closing note — the planned `test_gate_coverage_census_topology.py` re-home is unnecessary

The WP05 `create_intent` (and the WP prompt's T028) anticipated a **new**
file, `tests/review/test_gate_coverage_census_topology.py`, to carry the
mutation-bite forward onto `GateCoverageScopeSource`'s private helpers.
Investigation of `d19bd566c` shows WP04 already migrated the mutation-bite
**in place** inside the existing
`tests/architectural/test_pre_review_scope_singlesource.py` (see the M-mut
row above) rather than creating a sibling file. Re-homing it into a new
`tests/review/test_gate_coverage_census_topology.py` would therefore be a
pure duplication of already-migrated coverage, not a coverage-parity fix —
WP05 does **not** create that file. This inventory records the decision so a
later gate reviewer does not read the absent `create_intent` file as a
regression.

## Row count summary

- FR-004a: 1 deleted file row + 6 migrated-forward `_derive` test rows = **7 rows**.
- FR-004b: 2 migrated oracle test rows.
- FR-004c: 8 migrated verdict-diff test rows.
- M-mut: 1 migrated-forward file row (covering 10 test functions, 2 of which are the mutation-bite proper).
- Closing note: 1 explicit non-creation rationale (the planned re-home file).

**Total: 18 disposition rows**, every one mapping to either a named
surviving test id or an explicit "not carried forward because X" rationale.
No row is unresolved.
