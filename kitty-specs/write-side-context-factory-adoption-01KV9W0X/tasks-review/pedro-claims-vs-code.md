# Pedro — Claims-vs-Code Adversarial Review of the Mission B WP Decomposition

**Reviewer:** python-pedro (profile-loaded; pragmatic implementer / feasibility lens; DIR-010 spec-fidelity,
DIR-024 locality, DIR-025 boy-scout, DIR-030 quality-gate, DIR-034 test-first).
**Date:** 2026-06-17
**Branch HEAD reviewed:** `eba2448d8` ("Add tasks for feature write-side-context-factory-adoption-01KV9W0X").
**Research-pinned HEAD:** `efb28158f` (the inventories/census/feasibility were line-pinned here; it is an
ancestor of the current HEAD, and the cited src line numbers HOLD on the current HEAD — re-verified below).
**Method:** every cited site / line ref / "0-reader" / "byte-identical" / "already-exists" claim read against
the actual source on HEAD. Did NOT trust prompt text.

---

## A. Line-ref drift sweep — RESULT: NO SRC LINE DRIFT

Every concrete `file:line` the WP prompts + research cite was verified against the live source on HEAD. All
match exactly:

| Site | Cited | Verified on HEAD | Verdict |
|------|-------|------------------|---------|
| R1 `emit.py::_feature_status_lock_root` | :388-424, walks :417/:422/:424, call :545 | def :388, walks :417/:422/:424, call :545 | ✅ exact |
| R2 `work_package_lifecycle.py::_repo_root_for_lock` | :55-89, walks :82/:87/:89 | def :55, walks :82/:87/:89, calls :136/:253 | ✅ exact |
| R3 `lifecycle_events.py::_repo_root_for_lifecycle_log` | :234-239 | def :229, walks :234/:237/:239 | ✅ exact |
| R4 `store.py::_find_mission_specs_root` | :119-130 (candidate/two_up) | def :119, candidate :121, two_up :126 | ✅ exact |
| R5 `status_transition.py::_repo_root_for_feature` | :49-54, walk :53 | def :49, `_current_branch` :57 | ✅ exact |
| S1 `_identity_for_request` | :234-295, target select :291 | def :234, `destination_ref=coord_branch or _current_branch(repo_root)` :291 | ✅ exact |
| P1 `core/worktree.py` placement joins | :384 AND :396 | both `feature_dir = worktree_path / KITTY_SPECS_DIR / branch_name` at :384 and :396 | ✅ exact |
| WP04 orthogonal DeprecationWarning | :304 | DeprecationWarning at :304 | ✅ exact |
| FR-006 `resolution.py` | :761-778, :908, :929 | `_assemble_prompt_source_fragment` :761, return :778, call :908, build field :929 | ✅ exact |
| FR-006 `context.py` | :181, :246, :254 | `prompt_source_dir` :181, field :246, export :254 | ✅ exact |
| FR-006 `aggregate.py` | :199 + `if surface is not None` | param :199, threaded :266/:309, dead branch :329 | ✅ exact |
| WP06 `implement.py` `_lanes_feature_dir` | :979-984, :1140 | C-LANES-1 comment :979, assign :984, `require_lanes_json` :1140 | ✅ exact |

**Owned-files test paths all exist:** `tests/status/test_emit.py`, `test_work_package_lifecycle.py`,
`test_lifecycle_events.py`, `test_store.py`, `tests/git_ops/test_worktree.py`, `tests/lanes/test_persistence.py`.
**Owned-files partition is overlap-free** across WP02–WP08 (confirmed; clean parallel-lane partition).

No stale line refs found. The drift hunt comes up clean on the cited *src* sites.

---

## B. WP02 "byte-identical" + "root_resolver already exists" claims — CONFIRMED

- **Byte-identical lock-root bodies:** CONFIRMED. `emit.py:410-424` and `work_package_lifecycle.py:75-89`
  are identical line-for-line (same `repo_root` short-circuit, same `classify_worktree_topology`, same
  `resolve_canonical_root`, same 3× `feature_dir.parent.parent` fallbacks). Only the docstrings + the
  `canonical_root: Path` annotation line differ trivially. The consolidation is real and safe.
- **`workspace/root_resolver.py` already exists + owns `resolve_canonical_root`:** CONFIRMED with a nuance.
  The module exists (4243 bytes) and re-exports `resolve_canonical_root` + `WorkspaceRootNotFound` from
  `core.paths` (it no longer *defines* them — IC-04/WP05 collapsed the parser into `core/paths.py`). WP02's
  framing "it owns `resolve_canonical_root`" is accurate enough (it is the canonical import site). The new
  `resolve_status_lock_root` helper WP02 adds slots in cleanly. **No blocker.**

---

## C. FR-006 "0-reader / deletion behavior-neutral" claims — TWO REAL READERS FOUND

The census grepped only `src/` for *consumers* and concluded `prompt_source` is "0 readers." That is FALSE at
the **test-contract** layer. Live readers that WILL break on deletion:

1. **`tests/architectural/test_execution_context_parity.py::test_promptsource_fragment_parity` (:1779-1801)** —
   a LIVE (non-xfail; the comment at :1772 says "xfail removed") architectural parity test that reads
   `PromptSourceFragment.prompt_source_dir` from a resolved context. Deleting the fragment makes this test
   error/fail. WP07 names only "paula S-2/S-3" and directs the reviewer to "grep `prompt_source` across
   `src/` excluding the deleted defs" — it does NOT point the implementer at this `tests/architectural/`
   parity test, nor is `tests/architectural/` in WP07's owned_files.
2. **`tests/architectural/test_mission_runtime_surface.py`** and **`tests/mission_runtime/test_context_fragments.py`**
   (`:118`, `:184`) also reference `prompt_source` / `PromptSourceFragment` as contracts.

The `surface=` half of FR-006 IS genuinely 0-reader at the call layer: confirmed no `src/` caller passes
`surface=` (both `MissionStatus.load()` callers at `agent/status.py:163,199` pass `repo_root`+`mission_slug`
only). So the WP07 surface= claim is true; the `prompt_source` "behavior-neutral" claim is not — it is
behavior-neutral for *production* code but breaks *contract tests* the WP doesn't enumerate.

---

## D. Ownership-leeway gaps (subtask cannot be done inside declared owned_files)

1. **WP07 must edit `src/mission_runtime/__init__.py` (NOT owned).** `PromptSourceFragment` is exported at
   `__init__.py:36` and `:63`. Deleting the class without removing the export leaves a dangling import that
   breaks module import + ruff/mypy. WP07 owns `resolution.py`, `context.py`, `aggregate.py` only.
   `__init__.py` is unowned by any WP. → WP07 needs `__init__.py` added to owned_files (or explicit leeway).
2. **WP02's lock-root consolidation breaks an UNOWNED test.**
   `tests/specify_cli/coordination/test_worktree_topology.py` imports `_feature_status_lock_root` (:280, :353)
   AND `_repo_root_for_lock` (:307, :377) by name. WP02 T010 retires by-name tests in
   `test_emit.py`/`test_work_package_lifecycle.py` ONLY. If the consolidation keeps the two private functions
   as thin delegators (the prompt's "both callsites delegate" wording implies this) the imports survive and
   this is fine; but if the implementer removes/renames the private helpers, this unowned test breaks and the
   WP cannot fix it within its owned_files. → WP02 needs either an explicit "keep `_feature_status_lock_root`
   / `_repo_root_for_lock` as delegators" instruction OR leeway to touch `test_worktree_topology.py`.
3. **WP07 must retire the unowned `tests/architectural/` parity test** (per finding C). Same class of gap.

---

## E. WP05 complexity-ceiling check — NOT currently at risk

`_identity_for_request` (`status_transition.py:234-291`) passes `ruff --select C901` cleanly today
(`All checks passed!`) and has ~14 branch-bearing tokens in-body — comfortably under the ≤15 ceiling. T024's
"reduce to consume the projection" REMOVES branches (the inline meta-read + `coord_branch or _current_branch`
selector), so the change shrinks complexity rather than risking the ceiling. The T026 "extract helpers if it
nears the ceiling" subtask is appropriately precautionary; it is NOT currently triggered. **Adequate.**

---

## F. Lesser observations (NIT)

- **WP06 title is truncated:** `title: Lanes/coord adoption (FR-008,` — dangling open paren + comma. Cosmetic.
- **WP06 D-6 "derive from the context's `status_surface` fragment" is slightly mis-framed for the call site.**
  `implement.py` does NOT build a full `build_execution_context`; it already resolves the coord surface
  directly via `resolve_status_surface_with_anchor(...).read_dir` at :1016/:1028 (a *different* region than the
  `_lanes_feature_dir` block at :979-984). T028 correctly allows the existing-seam path, so this is workable,
  but the prompt's "consume the `status_surface` fragment" language should read "the existing coord-surface
  resolver" to match reality. NIT.
- **WP03 T014 "PR-3 early-return tidy" is near-vacuous:** `_find_mission_specs_root` (:119-130) is ALREADY in
  early-return form (returns on each branch). The boy-scout tidy has essentially nothing to do. Harmless. NIT.
- **WP01 frontmatter mismatch:** `agent: claude:opus:reviewer-renata:reviewer` but `agent_profile: python-pedro`
  (same on every WP). The `agent:` line carries the reviewer; `agent_profile:` carries the implementer. This is
  the normal two-actor encoding, not an error — flagged only for awareness.

---

## Structured Verdict

### BLOCKER
- **B1 (WP07, finding C+D1):** `prompt_source` is NOT 0-reader — `tests/architectural/test_execution_context_parity.py::test_promptsource_fragment_parity` (:1779, LIVE) + `test_mission_runtime_surface.py` + `test_context_fragments.py` read `PromptSourceFragment.prompt_source_dir` as contracts and WILL break on deletion. The WP's "0-reader / behavior-neutral / grep `src/` only" framing under-scopes the deletion. **Fix:** add `tests/architectural/test_execution_context_parity.py` + the two other test files to WP07 owned_files (or grant leeway) and extend T033 to name them explicitly; correct the "0 readers" claim in tasks.md/plan to "0 *production* readers; contract tests retired atomically."
- **B2 (WP07, finding D1):** deleting `PromptSourceFragment` requires editing `src/mission_runtime/__init__.py:36,63` (the export) which is NOT in WP07 owned_files; the dangling export otherwise breaks import + mypy. **Fix:** add `src/mission_runtime/__init__.py` to WP07 owned_files.

### SHOULD-FIX
- **S1 (WP02, finding D2):** `tests/specify_cli/coordination/test_worktree_topology.py` imports `_feature_status_lock_root` + `_repo_root_for_lock` by name (unowned by WP02). **Fix:** add an explicit instruction to WP02 to KEEP both private functions as thin delegators after consolidation (so the imports survive), OR add `test_worktree_topology.py` to WP02 owned_files + name it in T010.

### NIT
- **N1 (WP06):** truncated title `Lanes/coord adoption (FR-008,`.
- **N2 (WP06):** "consume the `status_surface` fragment" should read "the existing coord-surface resolver" — `implement.py` uses the resolver directly, not a built context.
- **N3 (WP03):** T014 early-return tidy is near-vacuous (`_find_mission_specs_root` is already early-return).

---

NEEDS-REMEDIATION
