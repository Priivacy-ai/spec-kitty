---
affected_files: []
cycle_number: 1
mission_slug: relocation-hardened-dead-code-scanners-01KX958P
reproduction_command: uv run pytest tests/architectural/test_no_tmp_paths_in_tests.py tests/unit/test_symbol_key.py -q
reviewed_at: '2026-07-11T20:45:00+00:00'
reviewer_agent: claude:opus:reviewer-renata
verdict: rejected
wp_id: WP02
review_artifact_override_at: "2026-07-11T20:55:14Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP02"
review_artifact_override_reason: "APPROVED cycle-2 (opus/reviewer-renata). Cycle-1 blocker RESOLVED: pending sentinel-swap committed (0faa93811, out-of-map WP01 coordination note); committed HEAD verified clean of /tmp (git grep empty; line 158 no longer /tmp/cache; worktree clean; only new commits = fix + status/merge bookkeeping, no substantive code change). All cycle-1 substantive criteria remain PASS: classifier CONSUMED live in production _compute_offenders (collision_index threaded per __all__ symbol via key_tier; None fail-closes); (i) test_bite_i drives a NEW byte-identical GateDecision pair through the PRODUCTION path (L1810), catches the rogue sibling (C-007, not standalone self-validation); bite a/c/e/f/i/k all through production path; C-005 byte-frozen VERIFIED via AST compare; 0 un-keyable. FLAG1 (missions/__init__.py hoist) ACCEPTABLE (behavior-preserving; entries escalate to module_path tier, not silently exempted). FLAG2 (30 removals/6 categories) ACCEPTABLE (all FR-010 auto-exempt/gained-caller; green suite + live classifier forbid dead-and-unexempt slip). Non-blocking note: 4 T004 detector tests whitespace-reflowed by ruff format (verbatim logic, invariant preserved+green; C-005 machinery byte-frozen). Cycle-1 artifact was repaired to add missing YAML frontmatter (verdict: rejected) so this override records correctly."
---

# WP02 (WP-REKEY-A) Review — Cycle 1

Reviewer: claude:opus:reviewer-renata. Verdict: **CHANGES REQUESTED (one blocker).**

The substantive re-key work is **correct and passes every make-or-break criterion** (details
below). There is exactly **one blocker**: the committed lane deliverable is not clean and its
committed state currently fails a hard architectural gate. Fix that one thing and this is an
approve.

---

## BLOCKER — committed lane HEAD fails the hard gate `test_no_new_tmp_literals_in_tests`; the green suite is an uncommitted-working-tree artifact

`tests/unit/test_symbol_key.py` line 158 at **committed HEAD** is:

```python
src = "CACHE_PATH: str = '/tmp/cache'\n"
```

That `/tmp/` literal trips `tests/architectural/test_no_tmp_paths_in_tests.py::test_no_new_tmp_literals_in_tests`.
The ratchet baseline is **empty** (`test_baseline_is_empty` enforces `frozenset()`), so this is a
true hard gate with no grandfathering — proven directly by running the gate's own
`scan_file_for_tmp_literal` against the committed blob: **hit at line 158**.

Your working tree already contains the correct fix (uncommitted, unstaged):

```python
src = "CACHE_PATH: str = '/opt/app-cache'\n"   # inert sentinel, non-shared-temp
```

…which is why your local `full arch 896/0` came up green — but **that fix is uncommitted**, so it
will NOT survive commit/merge. The committed state that would actually land is RED on the tmp gate,
violating DoD "full `tests/architectural/` 0-failed (baseline 887)" and NFR-004, and making the
Ready-claim's `896/0` inaccurate for the deliverable.

The move-task clean-worktree guard already refused approval for this reason ("Staged but
uncommitted changes in worktree: M tests/unit/test_symbol_key.py").

### Required fix
1. **Commit the pending `/tmp/cache` → `/opt/app-cache` fix** in `tests/unit/test_symbol_key.py`
   so the committed lane HEAD is actually green on the full arch suite.
2. `tests/unit/test_symbol_key.py` is **WP01's file** (not in WP02 `owned_files`, which is only
   `tests/architectural/test_no_dead_symbols.py`). WP01 shipped the offending literal. Committing a
   one-line inert-literal fix here is defensible under ownership-leeway, but **add an explicit
   out-of-map coordination note** in your commit message / move-task reason (same as you did for the
   `missions/__init__.py` hoist). Alternatively fold the fix into WP01 — either way it must be
   committed, not left dirty.
3. Re-run `pytest tests/architectural/test_no_tmp_paths_in_tests.py -q` against the **committed**
   tree (not just the dirty working tree) to prove green, then re-request review.

---

## Everything else — PASS (recorded so cycle-2 can move fast)

**Make-or-break #1 — classifier CONSUMED, not just imported: PASS.** The production gate
`test_no_public_symbol_in_all_is_unimported` (L1437) computes `collision_index =
classify_collisions(corpus)` **live each run** (L1435) and threads it through
`_compute_offenders` → `_resolve_final_key` (L1414) → `resolve_symbol_key` +
`key_tier(key, mod_dotted, collision_index)` for **every** `__all__` symbol. Exemption fires only
when `final_key is not None and final_key in allowlist` (L1415); a `None` key fail-closes to the
offender path (no silent exempt). The **(i)** regression guard `test_bite_i_live_collision_escalation_regression_guard`
(L1770) plants a NEW byte-identical `class GateDecision` pair, allow-lists ONLY the escalated
`module_path` key, drives BOTH occurrences through the **production** `_compute_offenders` (L1810),
and asserts the rogue sibling is STILL caught (`["synthetic.rogue::GateDecision"]`) — this is the
GateDecision-collapse vector proven through the production path, not a standalone key-fn (C-007).
`_is_reexport_shim_symbol` additionally refuses to auto-exempt any non-content-tier key (L1340),
closing the structural-swallow loophole.

**Make-or-break #2 — bite battery through production path (C-007): PASS.** (a) L1634, (c) L1714,
(e) L1744, (f) L1766, (i) L1810 all drive `_compute_offenders`. (k) L1816 asserts hand-key
well-formedness + auto-exempt keyability.

**Make-or-break #3 — C-005 byte-unchanged: PASS.** AST byte-compare base→HEAD:
`_record_module_attr_edges`, `_record_getattr_str_edges`, `_record_facade_edges`,
`_imports_by_target`, `_find_facade_lazy_dict_name`, `_resolve_relative_module` all IDENTICAL.
`known_modules` local (L1148) constructed identically.
Minor note (NOT a blocker): the 4 T004 detector tests are whitespace-reflowed (multi-line calls
collapsed to single-line — verbatim-identical logic/assertions/args, almost certainly ruff format);
NFR-003's literal "byte-diff=0" on the tests is not met, but the no-false-negative invariant is
fully preserved and green, and the load-bearing machinery itself IS byte-frozen.

**Make-or-break #4 — 0 un-keyable (k): PASS.** 314 unique well-formed `SymbolKey` members; green
suite proves every hand key matches live resolution (no dangling); None-keys fail-closed (f).

**FLAG 1 — `missions/__init__.py` hoist: ACCEPTABLE.** Behavior-preserving mechanical hoist of the
function-local lazy dict to module-level `_LAZY_IMPORTS`; `__getattr__` lazy semantics unchanged;
static `from charter import primitives` preserves the dead-modules caller edge (no orphan); aligns
with the canonical facade shape `_find_facade_lazy_dict_name` recognizes. The two entries resolve
and are correctly **escalated to `module_path` tier** by the live classifier (L326/328) — not
silently content-exempted, not fail-closed. Right call.

**FLAG 2 — baseline 215→194: ACCEPTABLE, but your flag understated the scope.** Actual removals =
30 `module::Name` (28 non-stale) across **6** categories (category_b −20, plus A_SLICE_F −1,
CHARTER_SCOPE −2, CHARTER_ACTIVATION −1, ORG_DOCTRINE_CLOSEOUT −2, and the **entire**
`_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT` −3) — not just "19 registered-migration entries." Spot-checked:
migration classes (`UnifiedBundleMigration`, `RefreshOrientationBlockMigration`) ARE
`@MigrationRegistry.register` (FR-010 auto-exempt); `project_identity.*` / `tracker.origin.*` are
re-export shims whose origins have live callers. The green suite structurally forbids a
dead-and-unexempt removal, and the live classifier defeats the content-key-collapse re-blind vector
(a ≥2-location collision escalates), so every removal is legitimate. For cycle-2, please make the
baseline comment / Ready-claim reflect the full 6-category scope so it's honest.

## Anti-pattern checklist
1. Dead code — PASS (test file; the one prod edit is a live-code hoist). 2. Synthetic-fixture —
PASS (bite tests fail if impl deleted). 3. Silent empty return — PASS (`_resolve_final_key` None is
documented fail-closed, falls through). 4. FR coverage — PASS. 5. Frozen surface — PASS (C-005
machinery byte-frozen; 4 detector tests whitespace-reflow noted). 6. Locked decision — PASS (no
`if key is None: exempt`). 7. Shared-file ownership — the **blocker** is exactly this: an
out-of-map WP01 file left dirty with no committed coordination note. 8. Production fragility — PASS.
