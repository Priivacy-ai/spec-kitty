# WP01 Review Feedback — cycle 1 (re-opened from `approved` by orchestrator)

**Source:** WP03 implementer escalation (C-003 / "invariant genuinely can't go green" clause), independently confirmed from source by the orchestrator. WP01's `live_derived_worklist()` has a derivation defect that makes WP02's `test_ci_topology_worklist.py` **internally unsatisfiable once WP03 does its job**. The prior approval only verified the *pre-WP03* state; the contradiction surfaces the moment the 32 worklist dirs get mapped.

## [HIGH] tests/architectural/_gate_coverage.py:912 — `live_derived_worklist()` subtracts the LIVE mapped set, so the mission's own success empties the worklist

Three WP02 test functions in `test_ci_topology_worklist.py` cannot be simultaneously green for any non-empty census under the current `live_derived_worklist()`:

| Test | Requires (post-WP03) |
|------|----------------------|
| `test_no_worklist_dir_falls_to_unmatched_run_all` (:110) | `worklist ⊆ mapped_src_dirs(models)` — every worklist dir is mapped by a live src-backed group |
| `test_census_worklist_matches_live_derivation` (:56) | `census.worklist == live_derived_worklist()`, and `live_derived_worklist() = {dirs ≥ T_LOC} \ mapped_src_dirs(models)` ⟹ `worklist ∩ mapped = ∅` |
| `test_worklist_is_non_empty` (:67) | `worklist ≠ ∅` |

`worklist ⊆ mapped` **and** `worklist ∩ mapped = ∅` ⟹ `worklist = ∅`, contradicting non-empty. **The routing test cannot be satisfied without globbing `src/specify_cli/<dir>/**` (which is exactly what `mapped_src_dirs` counts), so post-WP03 the 32 dirs are necessarily mapped and `live_derived_worklist()` returns ∅ while the committed census still lists 32 → freshness reds.**

### Root cause
`live_derived_worklist()` (`_gate_coverage.py:890-928`) computes `mapped = mapped_src_dirs(resolved)` **live** (:912) and excludes it (:915). The worklist is therefore "dirs ≥ T_LOC that are *currently* unmapped" — a moving target that the mission is explicitly chartered to shrink to ∅.

### Prescribed fix (derive against the FROZEN pre-mission baseline)
The census already carries the correct frozen baseline: `mapped_dirs` (23 pre-mission mapped dirs — `cli`, `sync`, …), disjoint from the 32-dir worklist. Change `live_derived_worklist()` so membership subtracts a **frozen** baseline, not the live mapped set:

- Add a committed module constant, e.g. `_PRE_MISSION_MAPPED_SRC_DIRS: frozenset[str]` = the 23 pre-mission mapped dirs (the same set the census `mapped_dirs` field records). Keep `_gate_coverage.py` self-contained (do NOT have the "live" function read the census JSON it is meant to validate against).
- `live_derived_worklist()` = `{ dir : dir ∈ src/specify_cli/*, live_LOC(dir) ≥ t_loc, dir ∉ _PRE_MISSION_MAPPED_SRC_DIRS }`, annotated with the committed `_COMPOSITE_ROUTING` overlay (unchanged).
- Leave `mapped_src_dirs()` (used live by `differential_arch_matrix` / the routing test) UNCHANGED — only `live_derived_worklist()` switches to the frozen baseline.

### Why this reconciles all three + strengthens the NFR-006 teeth
- **Pre-WP03:** live-mapped = frozen = 23 → `{live ≥ T_LOC} \ 23` = 32 = census.worklist → freshness GREEN (unchanged from today).
- **Post-WP03:** live-mapped = 55, but frozen stays 23 → `{live ≥ T_LOC} \ 23` = 32 = census.worklist → freshness GREEN; routing test (live mapped = 55 ⊇ 32) GREEN; non-empty GREEN. **All three reconcile.**
- **Teeth preserved + strengthened:** a hand-trim of `census.worklist` still reds (live re-derivation includes the dir); a dir crossing the LOC floor changes membership; and a **new** hot dir added to the tree (≥ T_LOC, ∉ frozen baseline) now grows `live_derived` beyond the committed census → reds (this was NOT caught before — a genuine improvement).

## Acceptance for this cycle
1. `live_derived_worklist()` derives against the frozen `_PRE_MISSION_MAPPED_SRC_DIRS` baseline; `mapped_src_dirs()` unchanged.
2. The committed census content is unchanged (still the same 32-dir worklist + 23 mapped_dirs; only the derivation function changes).
3. **Prove reconciliation by simulation:** apply a throwaway in-memory/patched model where the 32 worklist dirs ARE mapped (simulate WP03's globs) and show `test_census_worklist_matches_live_derivation`, `test_no_worklist_dir_falls_to_unmatched_run_all`, and `test_worklist_is_non_empty` are ALL green together. Record the simulation output. (Do NOT commit the simulated workflow edit — it's WP03's.)
4. Pre-WP03 today: `census.worklist == live_derived_worklist()` still green; the 4 #2368 consumer suites still green untouched; ruff + mypy clean on the diff.
5. Additive-only contract holds: `git diff --stat` shows only `_gate_coverage.py` (+ census only if regeneration proves identical — expected no census delta).
