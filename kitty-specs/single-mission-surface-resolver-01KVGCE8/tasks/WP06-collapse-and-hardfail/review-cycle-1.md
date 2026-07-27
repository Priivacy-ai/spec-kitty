# WP06 Review — Cycle 1 (reviewer-renata)

**Verdict: REJECT** (narrow, documentation-only fix — the code collapse, the #1900 drain, the FR-006 hard-fail, and the ADR are all correct and verified. The block is on the *accuracy of the two aggregate-seam xfail rationales*, which is the one auditable artifact the CRUX hinges on.)

The collapse is sound. I verified items 2–6 by RUNNING; they all pass. The reject is surgical: the `_XFAIL_AGGREGATE_SEAM_OUT_OF_SCOPE` reason text is **factually wrong about the runtime divergence it claims to document**, on both cells it is attached to. An allowlist whose stated justification contradicts observed behavior cannot serve as the "auditable record replacing the `rg → 0` drain" — which is precisely its declared purpose. This is fixable in `tests/missions/test_surface_resolution_equivalence.py` with no production-code change.

---

## Issue 1 (BLOCKING) — the `_XFAIL_AGGREGATE_SEAM` rationale misdescribes both cells it marks

I ran the two cells live (worktree `src` on the path) and observed:

**`coord-empty/slug-mid8`:**
```
resolve_mission_read_path           : StatusReadPathNotFound      / STATUS_READ_PATH_NOT_FOUND
resolve_status_surface_with_anchor  : CoordinationWorktreeEmpty   / STATUS_READ_PATH_NOT_FOUND
MissionStatus.load                  : CoordAuthorityUnavailable   / None
```

**`coord-deleted/slug-mid8`:**
```
resolve_mission_read_path           : <PRIMARY DIRECTORY>         / (dir, no error)
resolve_status_surface_with_anchor  : CoordinationBranchDeleted   / COORDINATION_BRANCH_DELETED
MissionStatus.load                  : CoordAuthorityUnavailable   / None
```

The constant `_XFAIL_AGGREGATE_SEAM_OUT_OF_SCOPE` asserts: *"read_path+surface agree on the error_code (STATUS_READ_PATH_NOT_FOUND), but MissionStatus.load keeps its CoordAuthorityUnavailable single-seam contract … ONLY the aggregate diverges."* That statement is **wrong on three points**:

1. **`coord-deleted/slug-mid8`: read_path does NOT agree with surface — it returns a primary *directory*, not an error.** It is a dir-vs-error divergence, not a code-equality. And the surface's code there is `COORDINATION_BRANCH_DELETED`, not `STATUS_READ_PATH_NOT_FOUND`. The "read_path+surface agree on STATUS_READ_PATH_NOT_FOUND" claim is simply false for this cell.
2. **The aggregate's `error_code` is `None`, not `STATUS_READ_PATH_NOT_FOUND`.** `CoordAuthorityUnavailable(RuntimeError)` carries no `error_code` (the matrix's own `Outcome.from_error` comment confirms this). So even on `coord-empty/slug-mid8` the aggregate diverges on **both class AND code**, not "same code, different class" as the WP history note and the constant imply.
3. **`coord-empty/slug-mid8` ALSO diverges surface-vs-read_path on *class*** — `CoordinationWorktreeEmpty` is not `StatusReadPathNotFound` under the matrix's `type() is type()` gate. This divergence was **introduced by WP06 itself** (the diff changed the surface's coord-empty `raise StatusReadPathNotFound(...)` → `raise CoordinationWorktreeEmpty(...)`). The rationale says "ONLY the aggregate diverges," hiding the WP06-introduced surface/read_path class split.

**Why this blocks:** the WP's own T026/T021 contract elevates this allowlist to the *auditable substitute* for the `rg "xfail" → 0` mechanical drain. The whole point is that "each remaining xfail names exactly why the collapse does not close it." Two of the six do not — they name a reason that is not what actually happens. A future agent reading the allowlist to decide whether the cell is safe to drain would be misled.

**Fix (no production code change required):**
- Rewrite `_XFAIL_AGGREGATE_SEAM_OUT_OF_SCOPE` so it is true per the observed outcomes, OR split it into two honest reasons:
  - `coord-empty/slug-mid8`: surface raises the WP06 `CoordinationWorktreeEmpty` carve-out (code `STATUS_READ_PATH_NOT_FOUND`); read_path raises bare `StatusReadPathNotFound` (same code, **different class** — a WP06-introduced subclass split that the `type() is` gate flags); aggregate raises `CoordAuthorityUnavailable` (**no error_code**). State plainly that the aggregate is owned by WP04 and un-editable here, and that the surface/read_path *class* split is the WP06 carve-out trading exact `type()` identity for a richer diagnostic at a stable `error_code`.
  - `coord-deleted/slug-mid8`: read_path resolves to **PRIMARY (a directory)** — the bare/twin coord-deleted read_path gap (FR-005 typed-error convergence, NOT in WP06's `requirement_refs`); surface raises `CoordinationBranchDeleted` (`COORDINATION_BRANCH_DELETED`); aggregate raises `CoordAuthorityUnavailable`. This is a multi-way divergence, not an aggregate-only one.
- Correct the WP history-log note ("SAME error_code, different class") — the aggregate's code is `None`, so it is *different error_code AND different class*.

This is the only blocker. Once the two reason constants tell the truth, the allowlist is legitimate and I will approve.

---

## What I verified and ACCEPT (for the implementer's context — these are NOT blockers)

**CRUX ruling (the substantive question):** Allowlisting the 2 aggregate-seam cells is **legitimate in principle**:
- `status/aggregate.py` is NOT in WP06's `owned_files`; WP06 cannot edit it.
- `CoordAuthorityUnavailable` is WP04's *approved* public contract (exported, caught by the `agent status` CLI, pinned by `test_aggregate_surface_resolution` / `test_mission_status_aggregate` / `test_handle_equivalence_matrix`). Converging it is out of WP06's scope.
- FR-005 (typed-error convergence, which the coord-deleted read_path gap needs) is NOT in WP06's `requirement_refs` (FR-001/FR-006/FR-007 only).
- The substantive FR-006 guarantee — a stable `error_code` for routing + the actionable two-path message — IS delivered at the resolver seam and is mutation-proven. FR-002's "identical typed error" is satisfied in substance (error_code), even though the matrix's stricter `type() is` gate cannot converge cross-WP-owned seams here.

So the *decision* to allowlist is correct; only the *stated reasons* are wrong. That is why this is a doc fix, not a re-architecture.

**Item 2 — #1900 migration + drain (PASS):** `_is_coordination_feature_dir`/`_is_coord_worktree_feature_dir` are gone; `_is_under_worktree` → `is_under_worktrees_segment` and `_is_coord_worktree_status_surface` → `is_registered_coord_worktree` (registry authority, fail-open-to-non-coord on `WorktreeRegistryUnavailable` — old no-raise contract preserved). The allowlist entry is removed. I re-injected a raw `-coord`/`.worktrees` predicate into `status_transition.py` → `test_coord_path_predicate_only_in_blessed_modules` **FAILS** (ratchet bites). Zero live raw predicates remain (the grep hits are all comments/docstrings). SC-005 proven.

**Item 3 — coord-empty hard-fail (PASS, mutation-verified):** message names both paths, `error_code == STATUS_READ_PATH_NOT_FOUND`, fires for BOTH handle forms, no silent fallback; no-coord and create→first-write window still resolve PRIMARY. I ran both mutations: (1) dropping the recreate/populate token → test FAILS; (2) disabling the surface's coord-empty raise (silent fallthrough) → `DID NOT RAISE` → test FAILS. Restored → green.

**Item 4 — path-(b) #1918 re-attribution (PASS):** `test_read_path_resolver_transitional` confirms `resolve_mission_read_path` MUST return primary for a declared-but-unmaterialized coord (#1718), which is a genuinely different contract from the surface (composes coord path). Blindly routing read_path through the surface WOULD regress #1718. The 4 #1918 cells are `xfail(strict=True)` with the out-of-scope reason in the documented constant. (The `_XFAIL_READPATH_MID8_OUT_OF_SCOPE` reason is accurate; only the AGGREGATE constant is wrong.)

**Item 5 — gates (PASS):** equivalence matrix = 7 passed / 6 xfailed / **0 XPASS**. `tests/coordination/ tests/architectural/{topology,no_write_side,no_dead_symbols}` = 16 passed. `ruff check` clean on all changed files. mypy `no-any-return` hits on single-file runs are a **pre-existing** artifact (the base `status_transition.py` errors on the identical lines; full-tree `mypy --strict src/specify_cli src/charter src/doctrine` reports 0 errors in either owned src file). `test_handle_equivalence_matrix` (13 failed) is **pre-existing** — I ran it on base `b70be7801` (WP06 does not touch the file) and it fails identically. Not a WP06 regression; reported per the charter rule, not blocked.

**Item 6 — ADR (PASS, high quality):** records the hard-fail decision, the benign-state distinctions (no-coord, create-window, coord-deleted), alternatives, and is bound to the single resolver. Notably, ADR §"Known scope boundary" (lines 97–105) *honestly documents the aggregate-seam deferral* — the same divergence the matrix constant misdescribes. Recommend the corrected matrix constants point back to this ADR section so the two artifacts agree.

**Anti-pattern checklist:** 1 Dead code — PASS (`CoordinationWorktreeEmpty` raised at 2 live sites; transitive-consumption allowlist entry justified, mirrors `CoordinationBranchDeleted`). 2 Synthetic-fixture — PASS (mutation-killed). 3 Silent empty return — PASS. 4 FR coverage — PASS (FR-001 sole-authority + #1900 drain; FR-006 mutation-verified; FR-007 predicates migrated). 5 Frozen surface — PASS. 6 Locked decision — PASS (no silent fallback; the un-editable `status/aggregate.py` was correctly NOT touched). 7 Shared-file ownership — PASS (the two non-owned architectural allowlists are sanctioned cross-edits, documented). 8 Production fragility — PASS (the new `raise` is the decided FR-006 fail-loud, ADR-recorded).
