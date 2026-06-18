# Phase 0 Research — Governed-State-Surface Coherence

**Date:** 2026-06-18 · **Branch:** `feat/governed-state-surface-coherence` (HEAD off main `9f98d89fe`)
Re-verifies the 4-agent pre-spec synthesis (`research/00-prespec-synthesis.md`) against current HEAD. All line numbers confirmed live by the orchestrator.

## Census re-verification (HEAD-confirmed)

### Goal A — #2016 orchestrator coord-read — CONFIRMED
| Surface | Location (HEAD) | Finding |
|---|---|---|
| Defect site | `orchestrator_api/commands.py::_resolve_mission_dir` :275–331 | reimplements mid8 via strict-only `resolve_mid8(slug, mission_id)` keyed on **primary** meta; M5 fail-closed guard at :320 only fires when `declares_coordination` |
| Canonical seam to adopt | `coordination/surface_resolver.py::_coord_mid8` :363–415 | 3-tier cascade `meta.mid8` → `resolve_mid8(meta.mission_id)` → `mid8_from_slug(slug)`, fail-closed |
| Red test | `tests/specify_cli/regression/test_issue_1615_1616_1617_1618.py::TestIssue1616OrchestratorApiCoordRead::test_coord_path_returned_when_coord_exists` | **RED on HEAD** (returns `None`); fixture `mkdir`s an empty coord dir — **no meta.json** → tier-3 `mid8_from_slug` is the operative tier (verified `mid8_from_slug("my-feature-01KT3YBD")→"01KT3YBD"`) |
| Fold-now | `_fail` typed `-> None` at :221; `raise # unreachable` at :367 & :370 | S5747 — `_fail` always raises `typer.Exit`; retype `-> NoReturn` makes both lines provably dead |

**Decision A:** route `_resolve_mission_dir` identity derivation through the `_coord_mid8` cascade (or refactor `_coord_mid8` into a shared helper both call) so the coord-only-with-tail-slug topology resolves via tier-3 `mid8_from_slug`. Preserve the typed `StatusReadPathNotFound` fail-closed for genuinely-unresolvable handles (no tail + no declared id). **No fake-primary-meta in the fixture** (C-001).

### Goal B — #2009 charter coherence — CONFIRMED (cluster)
| Facet | Location (HEAD) | Status |
|---|---|---|
| C2-a status side-effects | `_status_collectors.py:22–94` | **ALREADY FIXED** (`f892894e2`, read path pure `is_stale` only) → pin with a guard test (FR-008a) |
| C2-b JSON datetime crash | `_status_collectors.py:73–77` (`last_sync`) → `status.py:74` (`json.dumps` no `default=str`) | **LIVE** (debbie reproduced `TypeError`) → FR-005 |
| C2-d hash unification | `sync.py`/`_status_collectors.py`/`computer.py` all → `charter.hasher.hash_content` | **ALREADY UNIFIED** → pin with a 3-path-agree test (FR-008b) |
| C2-f XOR `invalid` | `computer.py:345–357` (detection); `runner.py:60` `_PASS_STATES = {fresh, skipped, built_in_only}` excludes `invalid` | **LIVE** structural → FR-006 (downgrade to read-time residue) |
| Unlink sites | `_fresh_doctrine.py:119` + `project_drg.py:343` (inside `apply_post_condition`) | two parallel sites → FR-007 (consolidate to one helper) |
| C2-e sync noop | `sync.py` `is_stale` gate | **REPRO-IN-WP** (FR-009): needs a stored-hash-drift fixture; not reproduced during planning — the B-cluster WP reproduces live before any change, else records a verified-non-reproducible verdict |

**Decision B:** FR-006 makes the `invalid` block unreachable for the residue condition by reporting `built_in_only` + a non-blocking diagnostic at the reader (manifest is declared authority). FR-007 consolidates the two unlink sites into one shared helper. C2-a/C2-d are verify-don't-redo (pin with tests). C2-e is live-repro-first.

### Goal C — merge.py baseline extract — CONFIRMED
| Item | HEAD | Finding |
|---|---|---|
| Functions | `BaselineMergeCommitError`:180, `_record_baseline_merge_commit`:1678, `_recorded_baseline_from_working_meta`:1756, `_read_committed_meta_json`:1768, `_assert_baseline_merge_commit_on_target`:1803 | exact match to synthesis (~204 LOC) |
| Coupling | zero `console`/`typer.Exit`; deps `load_meta`/`write_meta`/`run_command`/`json`/`logger` | clean domain unit |
| Cycle | `merge/` does **not** import `cli.commands.merge` | no cycle risk for new `merge/baseline.py` |
| Callers | `merge.py:2675` (`_record_…`), `merge.py:2842` (`_assert_…`) | 2 call sites in `_run_lane_based_merge_locked` |
| Test net | 9+ suites import the names (`tests/merge/test_merge_done_recording.py`, `tests/specify_cli/merge/test_1827_baseline_regression.py`, `tests/cli/commands/test_merge_status_commit.py`, review suites, coord-topology suites) | import-redirect is the regression net |
| Sonar fold | `"meta.json"` literal ×6 in merge.py | hoist `META_JSON` in `merge/baseline.py` for the moved occurrences |

**Decision C:** relocate the 5 functions to `src/specify_cli/merge/baseline.py`; re-export `record_baseline_merge_commit` / `assert_baseline_merge_commit_on_target` / `BaselineMergeCommitError` via `merge/__init__.py`; `merge.py` imports them back for its 2 call sites. Pure relocation + import redirect (NFR-001). Mega-function split is OUT (C-002).

### Goal D — green main — CONFIRMED RED
| Facet | Location | Finding |
|---|---|---|
| D1 markers | `tests/specify_cli/missions/test_read_path_resolver_validation.py` | carries `fast`, invokes git via subprocess → fails `test_pytest_marker_correctness` Rule 1 (needs `git_repo`) & Rule 2 (drop `fast`). **Reproduced locally.** |
| D2 mission-diff-scoped | `tests/architectural/test_no_worktree_name_guess.py::test_nfr001_consolidation_does_not_bleed_into_status_or_task_utils` | pins the canonical-seams one-time diff (flags `status/{emit,lifecycle_events,store,work_package_lifecycle}.py`) → remove/neutralize |
| D3 ratchet baselines | same file: `test_allow_list_entries_are_real_and_benign` / `test_name_compose_offenders_match_pinned_baseline` / `test_shortid_allow_list_entries_are_real` | stale on exact main tree; **env-sensitive** (CI py3.12+installed+parallel vs local py3.11 editable) → reconcile + verify under CI conditions (NFR-003) |

**Decision D (= WP01, C-007):** repair the gate first so the rest lands green. D1/D2 are mechanical; D3 reconciliation **must be verified GREEN on CI**, not just local.

## Ownership-overlap note (carried to tasks)
The Goal-A test file `test_read_path_resolver_validation.py` (marker fix) is **D1's** file. To keep `owned_files` overlap-free, the marker fix stays in **WP01 (Goal D)**; Goal A's WP owns only `orchestrator_api/commands.py` + the #2016 regression test. (D-overlap resolution.)

## Decisions of record
- **D-1** #2016 adopts the one `_coord_mid8` cascade (no second resolver); fail-closed preserved; no fake-primary-meta fixture.
- **D-2** #2009 `invalid`→read-time residue + one shared unlink helper; C2-a/C2-d pinned-not-redone; C2-e live-repro-first.
- **D-3** Cluster F → `merge/baseline.py`, behavior-preserving, re-export for back-compat.
- **D-4** Goal D = WP01; D3 verified on CI; D1's test file owned by WP01 (not Goal A's WP).
- **D-5** WP order: WP01=D (green base) → A, B, C independent lanes on the greened base.
