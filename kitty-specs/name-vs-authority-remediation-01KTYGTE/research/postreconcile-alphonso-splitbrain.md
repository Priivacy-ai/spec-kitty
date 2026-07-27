# Post-#1910-Reconcile Split-Brain / Phantom-Path Audit — architect-alphonso

**Author:** architect-alphonso (READ-ONLY; code unmodified, tests run only)
**Governance Op:** 01KV091MHWGN2YR0PT0NVB3W04
**Branch:** `feat/name-vs-authority-remediation-01KTYGTE` @ `3afe347ea` (rebased onto upstream/main incl. #1910 @ `a7f744bce`)
**Date:** 2026-06-13
**Scope:** architecture / split-brain / parallel-path lens; companion to `research/overlap-1908-vs-1910.md`.

---

## Item 1 — Dropped-API phantom references

**SEVERITY: BLOCKING.**

The reconcile correctly took #1910's `is_committed(..., placement=…)` signature and `MissionNotFoundError` for the not-found query path, AND removed `_ref_has_path` entirely (zero references tree-wide). BUT one of OUR OWN mission test files — `tests/integration/test_p0_pinning_regressions.py` (header: *"P0 coord-topology pinning … WP01 — FR-001/003/004"*) — was NEVER reconciled to the landed surfaces. It is the **sole** carrier of every phantom reference, and it **fails hard**.

Evidence (`python -m pytest tests/integration/test_p0_pinning_regressions.py -q` → **4 failed, 5 passed**):

| File:line | Phantom form | Landed reality | Failure |
|-----------|--------------|----------------|---------|
| `tests/integration/test_p0_pinning_regressions.py:364` | `is_committed(spec, repo_root, authority_ref=placement.ref)` | signature is `is_committed(file, repo_root, placement: CommitTarget\|None=None)` (`src/specify_cli/missions/_substantive.py:263`) | `TypeError: is_committed() got an unexpected keyword argument 'authority_ref'` |
| `tests/integration/test_p0_pinning_regressions.py:380` | same | same | same `TypeError` |
| `tests/integration/test_p0_pinning_regressions.py:233-239` | `pytest.raises(QueryModeValidationError)` for an UNRESOLVABLE handle + asserts `err.error_code` / `err.next_step` | unresolvable handle now raises `MissionNotFoundError` (`runtime_bridge.py:3091/3095`); `QueryModeValidationError` (`runtime_bridge.py:220`) is a **bare `ValueError` with NO `error_code`/`next_step` attributes** | `MissionNotFoundError` raised, not caught by `pytest.raises(QueryModeValidationError)` → test errors |
| `tests/integration/test_p0_pinning_regressions.py:271-276` | `pytest.raises(QueryModeValidationError)` + `err.error_code == "MISSION_DIR_NOT_MATERIALIZED"` / `err.next_step` | ghost-dir path also raises `MissionNotFoundError` (`runtime_bridge.py:3095`); no `MISSION_DIR_NOT_MATERIALIZED` code exists on the landed exception | `MissionNotFoundError` raised → not caught → test errors |

`mypy tests/integration/test_p0_pinning_regressions.py` independently confirms the rot:
`:237 "QueryModeValidationError" has no attribute "error_code"`, `:238 … "next_step"`, `:275`, `:276` (4 `attr-defined` errors).

These are not just dead lines — they are **green-looking assertions that are actually red**, pinning behaviour that the reconcile deliberately discarded (per `overlap-1908-vs-1910.md` §"Tickets to DROP", FR-001/003 were reframed to *verify-already-fixed-by-#1910*). The file documents in its own header (`:20-22`) the now-defunct *"structured `QueryModeValidationError` carrying `error_code` + `next_step`"* design — i.e. our DROPPED enrichment, never rewritten.

Scope confirmation (whole-tree grep): `authority_ref` → only this file; `_ref_has_path` → zero; `is_committed(...authority_ref...)` → only `:364`/`:380`. No phantom references survive anywhere in `src/` or in any other test file.

**Fix recommendation (do NOT apply):** Reconcile `test_p0_pinning_regressions.py` to the landed surfaces:
- Rewrite `:345-364` (`test_1884_is_committed_true_via_placement_authority`) and `:367-380` (`…no_false_positive…`) to pass `placement=` instead of `authority_ref=`. The canonical, already-passing coverage of this exact behaviour is `tests/specify_cli/missions/test_is_committed_coord_aware.py` (#1910's); these two pins are redundant with it — either retarget to `placement=` or delete and cite the coord-aware suite.
- Rewrite `:217-276` (`test_1885_residual_*`, `test_1885_resolved_dir_not_materialized_*`) to expect `MissionNotFoundError` (with `.handle` / `.error_code == "MISSION_NOT_FOUND"`) for the not-found/ghost-dir cases — matching the already-green `tests/contract/test_next_no_unknown_state.py` and `tests/next/test_query_mode_unit.py`. The `MISSION_DIR_NOT_MATERIALIZED` distinct-code assertion describes a code path #1910 did not implement; drop it or re-propose as a follow-up enrichment on top of `MissionNotFoundError`.
- Fix the header docstring `:16-26` to stop describing the dropped `QueryModeValidationError`-enrichment contract.

---

## Item 2 — Split-brain: two live paths for one concern

**SEVERITY: MEDIUM (duplicated primitive; NOT a correctness split-brain).**

### 2a. Query-mode exception path — COMPOSE (no split-brain). CLEAN.
`MissionNotFoundError` (not-found) and `QueryModeValidationError` (read-failure / no-issuable-first-step) co-survive for **distinct** concerns and are caught in the correct order in `next_cmd.py:459-479` (`MissionNotFoundError` first, then `QueryModeValidationError`). `QueryModeValidationError` is therefore NOT a phantom — it is live and legitimate for `runtime_bridge.py:3134` (read failure) and `:3170` (no issuable first step). One authority, no contradiction. The only defect is the **test** asserting the dropped enrichment (Item 1).

### 2b. `.worktrees` path-shape predicate — duplicated primitive. MEDIUM.
Two functions answer the identical "is this path under `.worktrees`?" question, both pure path-shape (`X in path.parts`), both non-routing:

| Function | File:line | Consumers |
|----------|-----------|-----------|
| `is_under_worktrees_segment` (OUR seam; docstring claims *"the blessed home for the `.worktrees in parts` idiom (C-SEAM-1)"*) | `src/specify_cli/coordination/surface_resolver.py:199` | `status/aggregate.py:354`, `coordination/status_service.py:68` |
| `path_is_under_worktrees` (#1910's; FR-035 / #1772 Bug 0) | `src/specify_cli/cli/commands/merge.py:154` | `merge.py:586/918/965`, `doctor.py:2899`, `agent/mission.py:144` |

This is **not** the correctness split-brain the mission exists to prevent: neither predicate makes a coord-vs-lane *routing* decision (both are mere shape *proposals*; routing goes through `is_registered_coord_worktree`/`classify_worktree_topology`, which consult the git registry). #1910 did **not** introduce a competing registry-backed topology classifier, a `WorktreeTopology`-equivalent enum, or a `CoordinationBranchDeleted`-style structured error — confirming `overlap-1908-vs-1910.md`'s COEXIST verdict holds post-reconcile. So the topology *authority* remains single-sourced in our seam.

What remains is a **duplicated shape helper**: our seam's own docstring asserts it is "the blessed home for the `.worktrees in parts` idiom", yet #1910 grew a second home that 5 call-sites now use. Consolidation is the seam's stated purpose.

**Recommendation (do NOT apply):** Authoritative = `surface_resolver.is_under_worktrees_segment` (the documented blessed home). Follow-up (non-blocking): redirect `merge.path_is_under_worktrees` to delegate to the seam (one-line body `return is_under_worktrees_segment(path)`), or file a debt ticket. NOT a merge blocker — the mission already allowlisted `merge.py` as a C-002 scope-reserved deferral (see Item 4), so this is consistent with the mission's documented boundary, not a regression.

---

## Item 3 — Missed parallel-path remediation

**SEVERITY: LOW.**

Swept the coordination / status / acceptance / merge read surfaces for a primary-HEAD-anchored read or a name/path-shape topology predicate that NEITHER mission routed through the unified authority:

- **Accept gate:** #1910's version landed and is coord-aware — `acceptance/__init__.py` uses `resolve_feature_dir_for_mission` → `_primary_anchor_feature_dir` → `_status_read_feature_dir` → `status_feature_dir` for all gate reads (`:1022-1123`). No primary-only straggler.
- **`is_committed` callers:** `tests/architectural/test_no_primary_anchored_gates.py` (#1910's ratchet) is GREEN — every `src/` call site passes `placement=`. The sole 2-arg site `agent/mission.py:2088` passes `placement=_spec_placement`. No straggler.
- **`coordination/transaction.py`:** reads `coordination_branch` from `meta.json` (`:230/247`) and composes via `CoordinationWorkspace.branch_name(slug, mid8)` threading mid8 (`:721`) — meta-declared authority + canonical compose, NOT path-shape inference, NOT bare-slug legacy compose. Correct.
- **Dashboard scanner:** `gather_feature_paths` routes coord detection through `classify_worktree_topology` (`scanner.py:316/345`) — our seam. Correct.

The only duplicated primitive is the non-routing shape helper in Item 2b. No residual *routing/gate* parallel path that should be unified but isn't. The `merge.py` / `merge/preflight.py` legacy-compose residuals are explicitly C-002 scope-reserved (owned by the upstream coord-merge mission = #1910's lineage) and allowlisted — a documented deferral, not a miss.

---

## Item 4 — Ratchet integrity against #1910's now-present code

**SEVERITY: CLEAN (ratchet is sound; #1910 introduced no uncaught violation).**

`python -m pytest tests/architectural/test_topology_resolution_boundary.py -q` → **3 passed**.

Verified the green is *correct*, not a silent miss:

1. **Coord-predicate scan (C-SEAM-1):** #1910's `merge.path_is_under_worktrees` (`merge.py:165`, `WORKTREES_DIR in path.parts`) IS a `.worktrees`-membership predicate the AST scan detects — but `merge.py` is **explicitly allowlisted** (`test_topology_resolution_boundary.py:106-109`) with the justification *"Path-shape merge helper … used for merge bookkeeping, not for coord-vs-lane status-surface routing."* This is a conscious, documented carve-out anticipating exactly #1910's helper class, NOT an accidental allowlist. `agent/mission.py` (#1910 rewrote 465 lines) is allowlisted for its navigation-hint shape use (`:113`); the `stale` half of the assertion proves it still contains a predicate, so the allowlist is not over-broad there.

2. **Legacy-compose scan (C-SEAM-2):** `merge.py` and `merge/preflight.py` are allowlisted as C-002 scope-reserved residuals (`:260/265`). #1910's `transaction.py` composes via `CoordinationWorkspace.branch_name(slug, mid8)` (mid8-threaded) — correctly NOT flagged (not a bare-slug legacy compose). No new unbackstopped compose escaped.

3. **Fabrication idiom (NFR-003):** zero occurrences; #1910 added none.

The ratchet's `stale` assertion (each allowlisted site must still contain a predicate) is the structural guard that prevents the allowlist from rotting into a blanket exemption — and it is green, so every allowlist entry is load-bearing. **No #1910 file should be caught but is silently allowlisted/missed.** The one #1910 predicate that lands in scope (`merge.path_is_under_worktrees`) is correctly classified as a non-routing shape helper and consciously allowed; the Item-2b consolidation is a quality follow-up, not a ratchet failure.

---

## OVERALL VERDICT

**Is the reconciled tree free of split-brain / phantom paths? — NO (one BLOCKING phantom-reference regression), but the architecture is sound.**

- The **topology authority is single-sourced** (our seam survives whole; #1910 introduced no competing classifier — COEXIST verdict confirmed). No correctness split-brain.
- The **ratchet is intact and correctly green** against #1910's now-present code; no silent allowlist miss.
- BUT a **single un-reconciled test file** (`tests/integration/test_p0_pinning_regressions.py`) carries every phantom reference to the dropped `authority_ref=` signature and the dropped `QueryModeValidationError.error_code/next_step` enrichment. It **fails 4 tests + 4 mypy errors** and pins behaviour the reconcile deliberately discarded. This is precisely the "missed parallel-path remediation due to the collision" the operator feared — caught here, on the WP01 file.

### Remediation required BEFORE merge (BLOCKING)
1. **Reconcile `tests/integration/test_p0_pinning_regressions.py`** to the landed surfaces:
   - `:364`, `:380` → `placement=` (or delete; redundant with `test_is_committed_coord_aware.py`).
   - `:217-276` → expect `MissionNotFoundError` (`.handle`, `.error_code == "MISSION_NOT_FOUND"`) for not-found/ghost-dir; drop the non-existent `MISSION_DIR_NOT_MATERIALIZED` assertion.
   - Fix header docstring `:16-26` (stop describing the dropped enrichment).
   - Re-run `pytest tests/integration/test_p0_pinning_regressions.py` + `mypy` on it → must be green.

### Quality follow-up (NON-blocking)
2. Consolidate the duplicated `.worktrees` shape predicate: have `merge.path_is_under_worktrees` delegate to `surface_resolver.is_under_worktrees_segment` (the blessed home), or file a debt ticket. Consistent with the mission's existing C-002 allowlist of `merge.py`.

**Bottom line:** the reconcile got the *architecture* right (no split-brain, single topology authority, sound ratchet); it left exactly one test file pinning the dropped API. Fix that file and the tree is clean.
