---
affected_files:
- path: src/mission_runtime/resolution.py
  line_range: 1-1465
- path: tests/architectural/surface_resolution_audit/inventory.md
  line_range: 1-120
cycle_number: 1
mission_slug: mission-resolver-port-01KX1C05
reproduction_command: PWHEADLESS=1 python -m pytest tests/architectural/ -q -p no:cacheprovider
reviewed_at: '2026-07-08T21:00:00.000000+00:00'
reviewer_agent: claude:opus:reviewer-renata:reviewer
verdict: rejected
wp_id: WP03
review_artifact_override_at: "2026-07-08T21:14:31Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP03"
review_artifact_override_reason: "Cycle 2 review passed (resolves cycle-1 census-desync rejection): census synced via canonical rekey_inventory.py (--check reports fresh, exit 0), allowlist pointer 1282 matches live primitive def, trunk byte-identical to approved cycle-1 (git diff a2e10385b HEAD on resolution.py + _read_path_resolver.py EMPTY), 3 previously-red arch tests green (19 passed), full tests/architectural/ suite 827 passed/4 skipped/0 failed"
---

# WP03 Review — Cycle 1 — CHANGES REQUESTED

## Summary

The trunk-threading work itself is **excellent and correct** — I verified every high-risk
item on the critical path and they all pass (see "What passed" below). There is **one
blocking issue**: WP03 changed the surface-resolution callsites (added `resolver=resolver`
and shifted line numbers) but did **not** update the companion architectural-audit census
files that track those exact callsites. As a result **3 architectural-gate tests are RED**,
which violates this WP's own Definition of Done ("full `tests/architectural/` green") and
will also fail from the primary checkout at merge.

This is **not** a marker-vacuous-under-`.worktrees` artifact — the tests executed and
produced concrete, diff-attributable findings that name your own `resolver = resolver`
edits. Fix is straightforward census maintenance; do **not** revert the trunk work.

---

## BLOCKING — Issue 1: Surface-resolution audit census desynced by this diff

Run (from lane-c or primary):

```
PWHEADLESS=1 python -m pytest \
  tests/architectural/test_single_mission_surface_resolver.py \
  tests/architectural/test_surface_resolution_audit.py -q
```

Three failures, all caused by WP03's own edits:

### 1a. `test_surface_resolution_audit.py::test_audit_passes_on_current_tree`
`inventory.md` (`tests/architectural/surface_resolution_audit/inventory.md`) is out of sync
with the code. Your commit `a2e10385b` added `resolver=resolver` to the
`candidate_feature_dir_for_mission(...)` callsites and shifted their line numbers, so the
audit reports both under- and over-count tripwires:

**Undercount — new callsites MISSING from `inventory.md`** (add a row for each, with the
current line number and the new `... , resolver = resolver )` token):
- `mission_runtime/resolution.py:1046` (`_resolve_status_surface_dir`)
- `mission_runtime/resolution.py:891` (`mission_context_for`)
- `mission_runtime/resolution.py:1300` (`resolve_placement_only`)
- `mission_runtime/resolution.py:840` (`resolve_topology`)
- `specify_cli/missions/_read_path_resolver.py:1429` (`resolve_planning_read_dir`)

**Overcount — ghost rows in `inventory.md` with NO live callsite** (these carry the OLD
pre-`resolver=` tokens/line numbers; re-point them to the new callsites above, or remove/
retag per the file's own `[inventory-only]` convention citing this WP):
- `mission_runtime/resolution.py:985` (`_resolve_status_surface_dir`)
- `mission_runtime/resolution.py:858` (`mission_context_for`)
- `mission_runtime/resolution.py:1220` (`resolve_placement_only`)
- `mission_runtime/resolution.py:816` (`resolve_topology`)
- `specify_cli/missions/_read_path_resolver.py:1369` (`resolve_planning_read_dir`)

### 1b. `test_single_mission_surface_resolver.py::test_zero_functional_raw_bypass_on_collapsed_tree`
The `_ALLOWLISTED_RAW_JOINS` entry for the topology-blind primitive
`primary_feature_dir_for_mission` is keyed at `_read_path_resolver.py:1239`, but WP03 shifted
that definition down (the raw join now sits at ~`:1282`). The join is legitimately TBYD
(topology-blind-by-design) — nothing about the primitive changed — so **do not** refactor it;
just update the allowlist line pointer to the new line and extend the existing re-key
rationale comment (it already documents `:869 -> ... -> :1239`; append the WP03 shift, e.g.
`-> :1282`) following the convention already in that entry.

### 1c. `test_single_mission_surface_resolver.py::test_allowlist_entries_are_not_stale`
Same root cause as 1b — the allowlist's expected line for `primary_feature_dir_for_mission`
no longer matches the live definition. Resolved by the same one-line pointer update.

**Ownership note:** `inventory.md` and `test_single_mission_surface_resolver.py` are not in
WP03's `owned_files`, but your diff is what desynced them. Updating a companion arch-census
that your own change moves is standard arch-gate / boy-scout discipline and is required to
satisfy the WP's DoD. This is exactly the surface-resolution split-brain safety net this
mission exists to protect — keep the ratchet honest.

**Definition of done for this fix:** the two test files above go green, and the full
`tests/architectural/` suite is green.

---

## What passed (verified against code, not the note) — no action needed

- **Split-brain / trunk threading (the crux): PASS.** Every read path threads the injected
  resolver. `_read_path_resolver.py` is the only place calling `resolve_mission(handle,
  repo_root, resolver=resolver)` (`:520`); the shell callers `resolve_action_context`,
  `mission_context_for`, `resolve_placement_only` all add `resolver: MissionResolver | None`
  and thread it down through `_resolve_mission_slug` / `_resolve_mission_id` and the
  canonicalizer chain (`_canonicalize_primary_read_handle`, `resolve_handle_to_read_path`,
  `candidate_feature_dir_for_mission`). The 7 other free-`resolve_mission` callers correctly
  inherit the `FsMissionResolver` default at the free-fn site (`mission_resolver.py:386
  resolver or FsMissionResolver(repo_root)`) — that IS the trunk (D-08). No bypass found.
- **Injection at callers, not the assembler: PASS.** `build_execution_context(**fields)`
  takes no resolver and stays FS-free (C-006); no adapter on the frozen
  `MissionExecutionContext`. No `FsMissionResolver` constructed inside `mission_runtime`
  (only docstrings reference it).
- **FS-free identity test (NFR-001): PASS — genuine.** `test_builder_fs_free_identity.py`
  drives the real canonicalizer chain via `FakeMissionResolver` with **no `kitty-specs/`
  tree**. The `bare-mid8` and `full-mission-id` parametrizations can only resolve to the
  composed slug **through** the injected resolver — without threading they degrade to the
  literal handle name and the `.name == _COMPOSED_SLUG` assertion fails. Not trivially
  passing. This is the concrete #1619 unblock.
- **Sentinel carve-out (D-07): PASS.** `_resolve_mission_id`'s `legacy-<slug>` branch reads
  `meta.json` and falls back to the sentinel; it is never routed through fail-closed
  `resolve()`. Pinned by
  `test_resolve_mission_id_bootstrap_sentinel_not_routed_through_resolve`.
- **Topology preserved (C-007): PASS.** `primary_feature_dir_for_mission` stays
  topology-blind; canonicalization is not folded into it (separate
  `_canonicalize_primary_read_handle`). Coord/primary read anchoring unchanged.
- **`apply.py::apply_proposals` complexity: PASS.** `ruff check --select C901` clean (≤15).
- **T015 adopters: PASS.** `doctrine_synthesizer/apply.py` and `core/vcs/detection.py` route
  through `FsMissionResolver.all_missions()` (miss-tolerant), not fail-closed `resolve()` —
  exact success/miss behavior preserved.
- **Diff-scoped `ruff` + `mypy`: PASS** (clean on all 5 owned files).
- **Frozen surface: PASS.** `acceptance/__init__.py` (WP05's #2139 read) untouched.

### Anti-pattern checklist
1. Dead code — PASS  2. Synthetic fixture — PASS  3. Silent empty return — PASS
4. FR coverage — PASS  5. Frozen surface — PASS  6. Locked decision — PASS
7. Shared-file ownership — **FAIL** (Issue 1: arch-census desync, no coordination note)
8. Production fragility — PASS
