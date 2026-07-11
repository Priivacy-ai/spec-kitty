# Tracer: acceptance module decomposition

Seeded at planning (2026-07-11). Append during implement; assess at close.

## Extraction decisions (WP04, T021-T025)

- **`summary_core.py`** (T021): `WorkPackageState`, `build_work_package_state`
  (the per-WP lane-bucket + metadata-issue computation `collect_feature_summary`'s
  loop body used to run inline), `_path_prefix_for_mission`,
  `evaluate_path_conventions` (the mission-path-convention block),
  `build_warnings` (final warnings assembly), `_build_recommended_fix_order`
  plus its 3 new predicate helpers (`_has_blocked_check`,
  `_has_non_terminal_lane`, `_has_issue_containing`) that replaced its CC22
  if-chain with a data table. `collect_feature_summary` itself **stays defined
  in `__init__.py`** — it could not move: the WP01 characterization suite
  (`test_trio_pure_cores.py::TestCollectFeatureSummaryWiring`) monkeypatches
  ~14 of its collaborators (`_primary_anchor_feature_dir`,
  `_status_read_feature_dir`, `_iter_work_packages`, `_check_lane_gates`,
  `_missing_artifacts`, `get_mission_for_feature`, `_build_recommended_fix_order`,
  etc.) directly on the `specify_cli.acceptance` module object. A Python
  function's free variables resolve through the globals of the module it is
  *defined* in — moving `collect_feature_summary`'s definition into
  `summary_core.py` would have made those monkeypatches silently no-op (the
  real, unpatched collaborator would run instead of the test double), turning
  every wiring test green-for-the-wrong-reason or outright broken. Only the
  sub-computations NOT on that patch list were safe to extract.

- **`gates_core.py`** (T022): `AcceptanceCheckDiagnostic` (moved — canonical
  home is now here, `__init__.py` re-imports it), `_all_work_packages_terminal`,
  `_normalized_unchecked_tasks`, `_find_unchecked_tasks`,
  `_append_skipped_lane_checks`, `_check_workflow_run_evidence` + its full
  helper chain (`_changed_workflow_files`, `_workflow_evidence_missing`,
  `_contains_workflow_run_id`, `_normalize_workflow_evidence_line`,
  `_extract_workflow_run_remainder`, `_git_ref_exists`,
  `WORKFLOW_EVIDENCE_FILE`, `WORKFLOW_RUN_URL_RE`), and `_check_lane_gates`
  split into 3 named guard-clause stages (`_resolve_lanes_manifest_or_stop`,
  `_evaluate_branch_gate`, `_evaluate_acceptance_matrix`).
  `_target_branch_for_feature` **stays in `__init__.py`** (not in T022's
  explicit move list) for the same monkeypatch reason as above: the WP01 suite
  patches `specify_cli.acceptance.read_target_branch_from_meta` directly, and
  `_target_branch_for_feature` is the only caller. `gates_core.py`'s two call
  sites (`_evaluate_branch_gate`, `_changed_workflow_files`) reach it via a
  **deferred** `from specify_cli import acceptance as _acceptance_pkg; …`
  import inside the function body rather than a top-level import — a top-level
  import would bind a private copy in `gates_core.py`'s own globals, invisible
  to a patch applied to the `specify_cli.acceptance` module object. Same
  reasoning for `_find_unchecked_tasks`'s use of `_read_text_strict`
  (unmoved, in `__init__.py`, needed for `ArtifactEncodingError` identity —
  `accept.py` catches that exception type broadly and a duplicate class
  definition in `gates_core.py` would silently break that catch).

- **T023 (thin executor)**: `perform_acceptance` (CC13) and
  `_commit_acceptance_meta` (CC15) were *already* within the S3776≤15 gate at
  baseline (confirmed via `radon` before touching this file) and needed no
  further split — T023's "if wiring raises complexity, re-split" condition
  did not trigger. Both stayed in `__init__.py` with only their call sites to
  moved collaborators (`_target_branch_for_feature` — unmoved, so unaffected)
  updated for import-path continuity.

- **T024 (seam routing)**: no raw `kitty-specs/<slug>` path joins were found
  bypassing the seam in `acceptance/__init__.py` — confirmed via
  `tests/architectural/test_gate_read_literal_ban.py::test_dir_read_arm_default_deny_accept_package_clean`,
  which AST-walks every function under `src/specify_cli/acceptance/` (recurses
  into the new submodules automatically) and stayed green unmodified. Prior
  missions (#2085/#2107/closeout N+1) already routed every leaf resolver call
  onto the kind-aware seam; this WP's job was decomposition, not routing.
  `_status_read_feature_dir`'s LENIENT degrade
  (`status_dir if status_dir.exists() else feature_dir`, `require_exists=False`)
  is untouched, byte-for-byte, in `__init__.py`.

- **T025 (shims)**: `AcceptanceCheckDiagnostic`, `_changed_workflow_files`,
  `_check_lane_gates`, `_check_workflow_run_evidence`, `_find_unchecked_tasks`,
  `_normalized_unchecked_tasks` re-imported from `gates_core`;
  `WorkPackageState`, `_build_recommended_fix_order`, `build_warnings`,
  `build_work_package_state`, `evaluate_path_conventions` re-imported from
  `summary_core`. None added to `__all__` (still `AcceptanceError`,
  `AcceptanceMode`, `AcceptanceResult`, `AcceptanceSummary`,
  `acceptance_lane_derivations`, `ArtifactEncodingError`, `WorkPackageState`,
  `choose_mode`, `collect_feature_summary`, `detect_mission_slug`,
  `normalize_feature_encoding`, `perform_acceptance`, `resolve_acceptance_actor`
  — unchanged from pre-WP04). `_changed_workflow_files` needed a narrow
  `# noqa: F401` (it has no in-module caller post-extraction; it is re-exported
  solely because `tests/specify_cli/test_acceptance_regressions.py` imports it
  directly off the package) — the rationale is inline at the import site.
  `tests/architectural/test_no_dead_symbols.py`'s `_SYMBOL_ALLOWLIST` carried a
  stale `specify_cli.acceptance::WorkPackageState` "grandfathered legacy"
  entry; moving the class into `summary_core.py` gave it a genuine cross-file
  `from .summary_core import WorkPackageState` caller, tripping the ratchet's
  own ["ok this now has a caller, shrink the allowlist"] check
  (`test_no_public_symbol_in_all_is_unimported`) — removed per the ratchet's
  documented contract, not a workaround.

## S3776 before → after (radon `cc -s -n B` proxy)

| Function | Before | After | Where |
|---|---|---|---|
| `collect_feature_summary` | D (25) | B (8) | `__init__.py` |
| `_build_recommended_fix_order` | D (22) | (removed; see predicates below) | `summary_core.py` |
| `_check_lane_gates` | C (19) | (removed; see stages below) | `gates_core.py` |
| `_commit_acceptance_meta` | C (15) | C (15) — unchanged, already ≤15 | `__init__.py` |
| `perform_acceptance` | C (13) | C (13) — unchanged, already ≤15 | `__init__.py` |
| `build_work_package_state` (new) | — | B (9) | `summary_core.py` |
| `evaluate_path_conventions` (new) | — | B (7) | `summary_core.py` |
| `_evaluate_branch_gate` (new) | — | B (10) | `gates_core.py` |
| `_evaluate_acceptance_matrix` (new) | — | B (8) | `gates_core.py` |
| `_resolve_lanes_manifest_or_stop` (new) | — | A (2) | `gates_core.py` |
| `_check_lane_gates` (thin orchestrator, new body) | — | A (3) | `gates_core.py` |

Every function in the three touched files is now ≤15 (highest is
`normalize_feature_encoding` at C(16), pre-existing and out of WP04 scope —
untouched). Ruff C901/mccabe (blind per the mission's own framing, but aligned
in this repo's config) and `mypy` are clean on all three files: the same 5
pre-existing `no-any-return`/`misc` findings that existed before this WP
(verified via `git stash` diff) now simply live in different files;
zero NEW findings.

## Surprises / friction

- The single biggest surprise was that "extract `collect_feature_summary` into
  `summary_core.py`" (as literally read in the WP prompt) is **not actually
  achievable** without breaking the WP01 characterization suite's ~14
  module-attribute monkeypatches — Python's free-variable resolution is bound
  to the *defining* module's globals, not the caller's. The achievable and
  behavior-preserving interpretation is: extract the *sub-computations*
  `collect_feature_summary` orchestrates into pure helpers, keep the
  orchestrator itself (and every one of its directly-monkeypatched
  collaborator names) in `__init__.py`, wired via ordinary shim imports.
  Verified empirically (not just reasoned) by running the full
  `tests/characterization/` suite (73 tests) green both before and after.
- Same ripple for `_check_lane_gates`'s `read_target_branch_from_meta` — the
  test patches the re-exported package attribute, not the origin
  (`specify_cli.core.paths`) module. `_target_branch_for_feature` had to stay
  put; `gates_core.py`'s callers use a deferred package-level lookup instead
  of a top-level import. No Typer entanglement (this package has none — it's
  a pure library module consumed by `cli/commands/accept.py`).
- One mechanical downstream fix required: `tests/architectural/test_no_dead_symbols.py`
  had a stale allowlist entry (`specify_cli.acceptance::WorkPackageState`)
  that the ratchet itself flagged for removal once the class gained a real
  cross-file caller from the move — expected ratchet behavior, not a defect.
- Confirmed 3 pre-existing, unrelated architectural failures
  (`test_no_new_tmp_literals_in_tests`, `test_no_new_orphan_surfaces`,
  `test_split_preserves_zero_orphans`) all point at
  `tests/characterization/test_trio_json_envelope.py` (a WP01-owned file, never
  touched by this WP) — confirmed via inspecting the failure output naming
  that file exclusively; not introduced by this diff.
