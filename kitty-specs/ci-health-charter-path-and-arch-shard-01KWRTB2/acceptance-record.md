<!-- WP03 FR-008/SC-005 deliverable. Deliberate ownership-map-leeway edit: this
     path cannot be declared in owned_files for a code_change WP (the
     finalizer rejects kitty-specs/ paths — INVALID_WP_OWNED_FILES_KITTY_SPECS),
     but FR-008/SC-005 explicitly require this record, no other WP in this
     mission touches this path, and the leeway is recorded per-charter here and
     in WP03's Activity Log. -->

# Acceptance Record: Issue #2397 — Arch-Adversarial Matrix Split

**Mission**: `ci-health-charter-path-and-arch-shard-01KWRTB2`
**Work package**: WP03 (Arch-adversarial matrix split + partition guards)
**Requirement refs**: FR-008, SC-005

This record re-verifies, against T012's real local verification results (not
intentions), each of issue #2397's invariant-safety criteria — the 4 numbered
criteria in #2397's "Invariant-safety note" plus the 1 unnumbered follow-on
consideration (the docs-only-trim interaction). All 5 are treated as the
criteria SC-005 refers to.

## 1. Shards stay group-less/always-on, no differential triggering by changed path

- **Guard**: `tests/architectural/test_arch_pole_deserialized.py`
- **Result**: PASS (part of the 35-test batch run covering
  `test_shard_universe_bounded.py`, `test_coverage_topology_ownership.py`,
  `test_arch_pole_deserialized.py`, `test_docs_scoped_arch_coverage.py`,
  `test_ci_quality_path_filters.py` — 35 passed).
- **Manual confirmation**: the T008 diff preserves `if: always()` unchanged,
  adds no `needs:` edge, and adds no dorny filter-group `if:` reference on the
  `arch-adversarial` job — confirmed by direct diff review of the job block.

## 2. NFR-002 (100% of `src` changes) stays green post-split

- **Guard**: `tests/architectural/test_ci_architectural_gate_coverage.py` /
  the differential-matrix model in `tests/architectural/_gate_coverage.py`.
- **Result**: PASS — not directly touched by this WP's diff; the `arch-adversarial`
  job carries no dorny filter-group `if:` (unchanged by T008), so it is not part
  of `JOB_GROUPS`/the differential matrix and continues to run on every PR
  regardless of changed path, exactly as before the split.

## 3. The #2368 marker->job-authority invariants stay green

- **Guards**: `tests/architectural/test_marker_job_completeness.py`,
  `tests/architectural/test_arch_shard_marker_completeness.py` (this mission's
  new WP02 guard).
- **Result**: PASS — `test_arch_shard_marker_completeness.py` ran green
  (3 passed) as part of T012's verification batch. `test_marker_job_completeness.py`
  is unaffected by this WP's file-scoped diff (workflow now selects tests by the
  `arch_shard_N` marker via `-m`, which is a ROUTED-BY-MARKER selection the
  marker->job model already re-derives live from the workflow).

## 4. FR-006 coverage-ownership stays intact (no drop/double-count)

- **Guards**: `tests/release/test_coverage_topology_ownership.py`,
  `tests/architectural/test_shard_universe_bounded.py` (generalized in T009).
- **Result**: PASS. `test_coverage_topology_ownership.py` passed **unmodified**
  (T011 — confirmed shard-label-agnostic per R4, no code change needed).
  `test_shard_universe_bounded.py`'s new/extended `arch-adversarial` coverage
  (T009) was proven RED against the pre-T008 single-shard topology (one shard,
  806/806 tests = the full catch-all universe) and GREEN after T008's 3-shard
  split — genuinely exercised, not vacuous.

## 5. The PR #2391 docs-only trim still holds post-split

- **Guard**: `tests/architectural/test_docs_scoped_arch_coverage.py`.
- **Result**: PASS (after a live fix — see note below). Local reproduction of
  each shard's docs-only selection (`-m 'arch_shard_N and docs_scoped and not
  windows_ci'`) confirms all three legs independently narrow to the
  `docs_scoped` marker: shard 1 collects 15 docs-scanning tests, shard 3
  collects 47, and shard 2 collects 0 (expected — none of the five pinned
  known docs-content scanners, `_KNOWN_DOCS_SCANNERS`, fall in shard 2's file
  assignment; the completeness guard still covers shard 2 for any *new*
  docs-reading test that might land there).
- **Note (live finding, not anticipated by the WP prompt or the post-plan
  brownfield squad)**: `test_docs_scoped_arch_coverage.py` had a third,
  previously-unfound literal shard-name pin — `_ARCH_POLE_SHARD = "architectural"`,
  consumed at **module-import time** by `_pole_matrix_path_roots()` — which
  raised `StopIteration` the instant T008 landed (this module is not in any
  WP's `owned_files`; verified no collision with WP01/WP02). Fixed as a
  small, well-justified ownership-map-leeway edit: the function now reads the
  first matrix leg's `paths` (representative, since T008 keeps `paths`
  identical across all three legs by construction) instead of matching a
  specific shard label, and a new `test_all_arch_shard_legs_share_identical_paths`
  assertion guards the representative-leg assumption itself.

## Closing statement

Issue #2397 is closed by this mission; all 5 invariant-safety criteria
re-verified as above.
