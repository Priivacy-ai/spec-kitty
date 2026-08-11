---
work_package_id: WP05
title: Census extension, governance gates, and closeout
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-008
- FR-009
- FR-010
- NFR-001
- NFR-003
planning_base_branch: feat/meta-json-l1-seam-routing-3259
merge_target_branch: feat/meta-json-l1-seam-routing-3259
branch_strategy: Planning artifacts for this mission were generated on feat/meta-json-l1-seam-routing-3259. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-json-l1-seam-routing-3259 unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
history:
- at: '2026-08-10'
  note: Authored by /spec-kitty.tasks (post-plan-squad model).
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_inline_meta_read_gate.py
create_intent:
- docs/development/inline-meta-read-allowlist-baseline-deviation.md
- tests/architectural/test_meta_decoder_comparator_singletons.py
execution_mode: code_change
owned_files:
- tests/architectural/test_inline_meta_read_gate.py
- tests/architectural/test_meta_decoder_comparator_singletons.py
- docs/development/inline-meta-read-allowlist-baseline-deviation.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Apply it, then read this WP, `spec.md` (FR-008/009/010, NFR-001/003, C-002/C-009, SC-001/003/004), `data-model.md` (gates table), and `research.md` (D3/D4/D5/D8). WP02+WP03+WP04 must all be merged first — this is the **only** WP that touches the floor.

## Objective

Perform the single census change now that all routing has landed: teach the routed-census gate to count the new decode family, re-pin the floor from a live measurement, add the FR-010 enumeration + completeness gates, record the #3240 governance deviation, and verify the whole gate set green. Until this WP, the routing was invisible to the census (routes onto `decode_meta`/`parse_meta_file`, not in `ROUTED_CALLEES`); this WP makes it countable and honest in one commit.

### Subtask T022 — Extend `ROUTED_CALLEES`

In `tests/architectural/test_inline_meta_read_gate.py`, add `decode_meta` and `parse_meta_file` to `ROUTED_CALLEES` (~:104). This makes the 5 routed sites AND every internal L1/L2/L3 call countable — the live census will jump well above 134.

### Subtask T023 — Re-pin the floor from a fresh live count (same commit)

- Measure the NEW live count: `python -c "from tests.architectural.test_inline_meta_read_gate import scan_routed_load_meta_calls, SRC_ROOT; print(len(scan_routed_load_meta_calls(SRC_ROOT)))"` (re-run AFTER T022).
- Set `ROUTED_LOAD_META_FLOOR = measured_live − 3` (the repo `live − 3` convention; must satisfy `live − MARGIN(4) <= floor < live`). **Do NOT copy a number from this plan — measure and derive.** Add a dated rationale comment matching the file's prior floor-regen entries.
- Confirm `test_routed_load_meta_floor` green: `len(routed) >= floor`, `> floor` (anti-vacuity), `len(routed) − floor <= 4`.

### Subtask T024 — FR-010 enumeration + completeness gates

Add to `tests/architectural/test_inline_meta_read_gate.py`:
- **Enumeration gate**: fails on any `json.loads`/`json.load` applied to **meta content** outside the kernel L1. Scope it by an argument/path allow-set so it does NOT false-positive on (a) `kernel.meta_decode` itself, or (b) `merge_driver._parse_json_document:337` (row-matrix, not meta). Assert the independent-meta-decoder set == 1 (kernel L1).
- **Completeness gate**: assert 0 un-routed `meta.json` bypass reads remain beyond the enumerated set — so a future 6th bypass can't hide behind the floor.
- **Anti-vacuity canary (renata post-tasks)**: add a self-test that plants a meta-`json.loads` snippet outside kernel L1 in a fixture and asserts the enumeration gate FLAGS it, plus one asserting the two allowed sites (`kernel.meta_decode`, `merge_driver._parse_json_document:337`) do NOT trip it. A gate that never fires is worthless — the canary proves it fires.

Create `tests/architectural/test_meta_decoder_comparator_singletons.py` (declare `pytestmark`):
- **NFR-002 comparator enumeration gate**: assert exactly **1** VCS-lock comparator symbol and exactly **1** *named* `VCS_LOCK_META_FIELDS` declaration exist tree-wide, and **0** inline `frozenset({"vcs", ...})` field-set literals. The spec (NFR-002/SC-003) promises "verified by enumeration" but no such gate exists today — this is it (a manual grep is not enough; a future re-introduced inline literal must red).

### Subtask T025 [P] — Record the #3240 deviation

Create `docs/development/inline-meta-read-allowlist-baseline-deviation.md`: record that the inline-meta-read allow-list is governed WITHOUT a `_baselines.yaml` §(a) count baseline because the existing `test_allowlist_matches_floor` (equality) + `test_allowlist_shrink_only` compensating controls are strictly stronger than a `<=` ratchet and add stale-entry eviction a count baseline lacks. This closes #3240 as a deviation record (C-006). (An issue comment on #3240 pointing at this doc is posted at mission merge, not here.)

### Subtask T026 — Verify the full gate set green

- The three named gates: `test_inline_meta_read_floor`, `test_routed_load_meta_floor`, `test_no_unaccounted_load_meta_call_sites`.
- The new FR-010 gates.
- Full `tests/architectural/` as the safety net, plus the marker/terminology gates touched earlier in the mission.
- Run: `PWHEADLESS=1 python -m pytest tests/architectural/ tests/specify_cli/test_meta_fail_closed_full_census_contract.py -q` → green. Confirm SC-001 (0 unrouted), SC-003 (1 decoder + 1 comparator), SC-004 (gates green, floor live-derived, #3240 recorded).

## Branch Strategy

Base + merge target: `feat/meta-json-l1-seam-routing-3259`. Worktree per computed lane. Depends on WP02+WP03+WP04 (all routing must be merged before the census can be finalized).

## Definition of Done

- `ROUTED_CALLEES` extended; `ROUTED_LOAD_META_FLOOR` re-pinned so `test_routed_load_meta_floor`'s margin+anti-vacuity band holds (`live − 4 <= floor < live`, `floor == live − 3`), with a dated rationale. The **control** is that band gate + a reviewer re-running the census one-liner and confirming `floor == live − 3` — not the unverifiable "measured not copied" prose.
- FR-010 enumeration + completeness gates added and green, scoped to meta content (exclude kernel L1 + `:337`), **with the anti-vacuity canary proving the gate actually fires**.
- NFR-002 comparator/field-set enumeration gate (`test_meta_decoder_comparator_singletons.py`) added and green: 1 comparator + 1 named field-set + 0 inline literals.
- `docs/development/inline-meta-read-allowlist-baseline-deviation.md` recorded (#3240 closed).
- All three named gates + the new gates + full `tests/architectural/` green (run with `-rs`, **0 unexpected skips**); SC-001/003/004 confirmed.

## Reviewer guidance

Verify: the floor was measured live (re-run the scan yourself and check `floor == live − 3`, in band); the FR-010 gate excludes the kernel L1 and the row-matrix decoder (no false positive) yet would catch a hand-rolled meta `json.loads`; the deviation record is present; no routing/src change sneaked into this closeout WP.
