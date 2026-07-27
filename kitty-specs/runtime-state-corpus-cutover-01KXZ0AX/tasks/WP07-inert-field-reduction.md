---
work_package_id: WP07
title: Inert-field reduction (optional post-cutover tail)
dependencies:
- WP06
requirement_refs:
- FR-011
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
agent: "claude"
shell_pid: "315401"
shell_pid_created_at: "1784569902.07"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/wp_metadata.py
create_intent:
- tests/specify_cli/status/test_inert_field_reduction.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/status/wp_metadata.py
- tests/specify_cli/status/test_inert_field_reduction.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP07 – Inert-field reduction (optional post-cutover tail)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the **`python-pedro`** agent profile (role: `implementer`)
**before doing any work**, and behave according to its guidance for the whole WP.

This WP is pure hygiene, but it sits on top of a load-bearing cutover: apply an implementer's rigour to
the **zero-readers proof** (T030) — never remove a field you have not first *proven* no live code reads.
Removing a field with a live reader would trade "inert cleanup" for a real regression.

## Objective

Reduce the now-**inert** `wp_metadata` runtime field definitions (and the matching cosmetic
`WP_FIELD_ORDER` slots) that fed the retired flag-OFF / dual-write legacy path, so the model carries no
dead runtime slots after the corpus cutover.

This is the deferred #2684 **"IC-08"** cleanup — this mission's **IC-06 / FR-011**, US5. It is
**Priority Low, optional, deferrable, and NOT a gate on mission completion** (the mission's Definition of
Done rests on US1–US4 + US6). Per the mission's **fold-everything** policy it is **folded in-mission**
here rather than split to a fresh follow-up issue.

Scope is **field-definition + slot removal only**. The six-way `wp_snapshot_state` accessor dedup
already shipped in #2817, so there is no accessor work in this WP.

## Context & grounding

- **Plan IC-06** (`plan.md`, "IC-06 — IC-08 inert-field reduction"): remove the now-inert `wp_metadata`
  fields and cosmetic `WP_FIELD_ORDER` slots that fed the retired legacy path — *pure hygiene, safe only
  post-cutover*; depends on IC-03; **deferrable** and non-gating; **confirm zero live readers before
  removal (`assert_zero_readers` proof)**.
- **FR-011** (`spec.md`): "reduce the now-inert `wp_metadata` fields and cosmetic `WP_FIELD_ORDER`
  slots, safe only post-cutover, so the model carries no dead runtime slots." Priority **Low
  (optional/deferrable)**. Independent test (US5): *with the reduction applied, the inert fields are gone
  and no reader references them; the full suite stays green.*
- **research D-02 (the correction) + D-14 (campsite reaffirmation) — `status_phase` is OUT OF BOUNDS.**
  D-02: after IC-03 deletes `_phase1_snapshot_authority_active`, `status_phase` does **not** become inert —
  the kept `_legacy_lane_mirror_enabled` (C-004) **still reads `status_phase`** via `_read_status_phase`
  (`status/emit.py:368-424`). D-14's per-IC campsite note repeats it verbatim: *"IC-06 keep `status_phase`
  out of bounds."* Retiring `status_phase` would **silently disable the lane mirror corpus-wide** — a real
  regression masquerading as cleanup. **Note:** `status_phase` is a `meta.json` marker read in
  `status/emit.py`; it is **not** a `WPMetadata` field, so it is already outside this WP's owned surface —
  the caution is here so the "inert cleanup" theme never tempts an out-of-scope retirement of it elsewhere.
- **data-model "Deleted / inert model surfaces"** table: the row *"inert `wp_metadata` fields +
  `WP_FIELD_ORDER` slots → removed (optional) → IC-06"* is this WP. The adjacent rows —
  `_legacy_lane_mirror_enabled` **kept** (C-004), and `status_phase` state transition with
  *"IC-06 must NOT retire this field"* — bound the scope from the other side.
- **Post-WP06 base (dependency WP06):** this WP branches from post-WP06 local main, so the cutover has
  already landed. `wp_metadata.py` had its phase-1 **flag branch** removed earlier by WP04 (IC-03) — the
  `_phase1_snapshot_authority_active` import and its `if not …: return metadata` guard in
  `_resolve_runtime_fields_from_snapshot` are **already gone**. WP07 is field/slot removal on top of that
  end-state, not a flag removal.

## Subtasks

- [ ] **T030 [FR-011] Prove `assert_zero_readers` FIRST (red-first, before any removal).**
  Author `tests/specify_cli/status/test_inert_field_reduction.py` as a durable guard that asserts **no
  live reader references** each field/slot proposed for removal — an attribute-access + textual/AST sweep
  across `src/` (and any consumer of `FrontmatterManager.WP_FIELD_ORDER`), NOT merely an
  `extract_scalar(...)` match. Run it **against the current tree first** to confirm the candidate set is
  genuinely reader-free post-cutover; anything with a surviving reader is **out of scope** and stays.
  This test is the removal's precondition and its regression lock (it must still pass after T029).
  - **Durable non-vacuity (mandatory — post-tasks gate fix).** The removed fields are already reader-free
    post-cutover, so the sweep is naturally GREEN and a transient manual "red-first" leaves no durable
    proof — a sweep bug that matches nothing then yields a permanent false green (DIR-041 "passes for the
    wrong reason"). Co-locate a **durable poison assertion** in `test_inert_field_reduction.py` mirroring
    WP06's SC-009: feed the sweep a **synthetic in-test source** that references a removed field/slot and
    assert it flags **RED**, plus a mirror case that stays GREEN. This proves the detector can emit a
    positive, so the zero-readers pass is meaningful rather than vacuous.

- [ ] **T029 [FR-011] Remove exactly the proven-inert fields + cosmetic slots.**
  Delete the now-inert `wp_metadata` runtime field **definitions** (the runtime/review slots that fed the
  retired flag-OFF legacy path and that T030 proved have zero live readers) and the corresponding
  **cosmetic `WP_FIELD_ORDER` slots**. Keep any field still carrying snapshot-sourced values — e.g.
  `shell_pid`/`shell_pid_created_at`/`agent`/`assignee` remain as the **carrier** for
  `_resolve_runtime_fields_from_snapshot`'s reduced-snapshot values and are **not** inert. **`status_phase`
  stays untouched** (C-004 lane mirror still reads it — see grounding). This is non-behavioural: keep the
  full suite green.

## Branch Strategy

- **Strategy:** Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; completed
  changes merge back into `feat/runtime-state-corpus-cutover`.
- **Planning base branch:** `feat/runtime-state-corpus-cutover`
- **Merge target branch:** `feat/runtime-state-corpus-cutover`
- **Depends on WP06** and branches from post-WP06 local main — the cutover (WP04/WP05) and its
  consequences are already landed before this WP runs.
- Per project policy: `spec-kitty merge` targets **local main only**; never `git push origin main`.
  Publishing is the operator's explicit, separate step.

## Test strategy

- **Zero-readers proof is the gate (T030).** The new `test_inert_field_reduction.py` must go **red-first**
  against a would-be reader and **green** once the field/slot set is genuinely reader-free — then stay
  green after T029's removal, locking the reduction against regression.
- **Full suite stays green (US5 independent test).** Removal is non-behavioural; the full
  `tests/architectural/` suite (per-file) and the `status` suite must remain green.
- **`uv run` discipline:** run tests per-file via
  `uv run --extra test python -m pytest -p no:cacheprovider <FILE>` — bare `python` resolves a sibling
  checkout and yields false greens. **Never run the whole `tests/architectural/` dir** (it hangs) — per
  file, with a timeout.
- `ruff` + `mypy` clean with **no** new blanket `# noqa` / `# type: ignore` / per-file ignores
  (NFR-004).

## Definition of Done

- [ ] **T030** `tests/specify_cli/status/test_inert_field_reduction.py` proves **zero live readers**
  reference every removed field/slot (attribute-access sweep, not just `extract_scalar`), and carries a
  **durable co-located poison assertion** (synthetic reader → RED; clean → GREEN) so the guard is
  non-vacuous (post-tasks gate fix, mirrors WP06 SC-009).
- [ ] **T029** the proven-inert `wp_metadata` runtime field **definitions** and the cosmetic
  `WP_FIELD_ORDER` slots are **removed** (FR-011); no live reader references them.
- [ ] Snapshot **carrier** fields (`shell_pid`/`shell_pid_created_at`/`agent`/`assignee`) are **retained**
  where they still carry reduced-snapshot values.
- [ ] **`status_phase` is untouched** — the kept `_legacy_lane_mirror_enabled` (C-004) still reads it; the
  lane mirror is not disabled by this WP.
- [ ] The full `tests/architectural/` suite (per-file) and the `status` suite are **green**; the reduction
  is non-behavioural.
- [ ] `ruff` + `mypy` clean with **no** new suppressions (NFR-004).
- [ ] No edits outside `owned_files` (`src/specify_cli/status/wp_metadata.py`,
  `tests/specify_cli/status/test_inert_field_reduction.py`).

## Risks & out-of-map edits

- **`status_phase` footgun (do NOT retire it).** The single biggest trap: `status_phase` looks inert once
  the phase-1 predicate is gone, but the kept `_legacy_lane_mirror_enabled` (C-004) still reads it
  (`status/emit.py:368-424`). Retiring it would silently disable the lane mirror corpus-wide. It is not a
  `WPMetadata` field and is entirely out of this WP's bounds — do not touch it here or in `emit.py`.
- **The flag branch is already gone (WP04 landed first).** `wp_metadata.py` had its
  `_phase1_snapshot_authority_active` flag branch removed by WP04 (IC-03); this WP branches from
  post-WP06 local main, so that removal is already in the base. Do **not** re-do flag work — this WP is
  field/slot removal only.
- **`WP_FIELD_ORDER` lives in `frontmatter.py`, not `wp_metadata.py`.** Verify before touching:
  `FrontmatterManager.WP_FIELD_ORDER` is defined in `src/specify_cli/frontmatter.py` (~lines 48-75), and a
  derived `WP_RUNTIME_FIELDS` reads from it (~lines 280-289). The `owned_files` surface for this WP is
  `wp_metadata.py` only. If the cosmetic-slot trim genuinely requires editing `frontmatter.py`, that is an
  **out-of-map edit** — surface it for an explicit `owned_files` boundary decision (fold-in vs a scoped
  follow-up) rather than silently editing an unowned file. The `wp_metadata.py` field-definition removal is
  squarely in scope regardless.
- **Prove, don't assume.** A field that "looks" legacy may still have a live reader (attribute access on
  the typed `WPMetadata`, not just `extract_scalar`). T030 is the arbiter; anything with a surviving
  reader stays. When uncertain, keep the field — this WP is optional and must not manufacture a regression.

## Reviewer guidance

- **`status_phase` untouched:** confirm no change to `status_phase` handling anywhere — the field, its
  `meta.json` marker, `_read_status_phase`, and the kept `_legacy_lane_mirror_enabled` are all unchanged;
  the lane mirror is not disabled.
- **Zero readers:** confirm each removed `wp_metadata` field / `WP_FIELD_ORDER` slot has **no live
  reader** — check the proof test actually sweeps attribute-access reads (`WPMetadata.<field>` /
  `read_wp_frontmatter().<field>`), not only `extract_scalar(...)`, and that it was demonstrated red-first.
- **Carriers retained:** confirm snapshot-carrier fields (`shell_pid`/`shell_pid_created_at`/`agent`/
  `assignee`) that still surface reduced-snapshot values were **not** removed.
- **Suite green + non-behavioural:** confirm the full `tests/architectural/` (per-file) and `status`
  suites are green and the diff is a pure reduction with no behavioural change; `ruff` + `mypy` clean,
  no new suppressions.
- **Boundary:** confirm no edits landed outside `owned_files`; if `frontmatter.py` was touched for the
  `WP_FIELD_ORDER` slots, confirm it was surfaced as an explicit boundary decision, not slipped in.

## Activity Log

- 2026-07-20T16:51:37Z – claude – shell_pid=182273 – Assigned agent via action command
- 2026-07-20T17:41:52Z – claude – shell_pid=182273 – Ready for review: IC-06 inert-field reduction (branch_strategy_override, proven zero-readers + parse-safe) with durable poison guard; + campsite fold of the 9-fn production-dead move-task write/commit closure orphaned by WP05. Per-file evidence: all affected tests green, ruff+mypy clean, test_no_dead_symbols shows no new offender. --skip-pre-review-gate: gate timed out >300s on scoped shards
- 2026-07-20T17:50:45Z – claude – shell_pid=182273 – Post-for_review campsite fold (b25292a02): reconciled the WP04-cutover straggler test_shell_pid_string_in_file in test_wp_metadata.py (a file WP07 edits) — converted the retired frontmatter-read assertion to the snapshot-authority end-state (test_shell_pid_is_snapshot_sourced_not_frontmatter, seeds a real claim carrying shell_pid=405597 on policy_metadata, stale frontmatter 111 ignored, string->int coercion preserved; not weakened). test_wp_metadata.py now fully green (87 passed) per-file; inert-reduction/FOLD work undisturbed (10 passed). WP07 stays in for_review.
- 2026-07-20T17:51:46Z – claude – shell_pid=315401 – Started review via action command
- 2026-07-20T17:58:18Z – user – shell_pid=315401 – Approved: inert reduction + 9-fn dead-closure fold + straggler reconciled stronger; Phase 1 complete (WP01-07)
