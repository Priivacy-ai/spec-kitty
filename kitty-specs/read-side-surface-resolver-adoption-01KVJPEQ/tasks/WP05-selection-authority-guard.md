---
work_package_id: WP05
title: Selection-authority guard + drain the residual allowlist
dependencies:
- WP02
- WP03
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: feat/read-side-surface-resolver-adoption
merge_target_branch: feat/read-side-surface-resolver-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/read-side-surface-resolver-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-side-surface-resolver-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2458445"
history:
- at: '2026-06-20T14:30:00Z'
  actor: claude
  note: WP authored from plan IC-04+IC-05 (FR-006/FR-007). Extends 01KVGCE8 audit/guard machinery.
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- tests/architectural/surface_resolution_audit/audit.py
- tests/architectural/surface_resolution_audit/inventory.md
- tests/architectural/test_single_mission_surface_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Add the **selection-authority guard** (two halves) binding read SELECTION to the seam, and **drain the read-CLI residual allowlist entries BY FIX** (not by blinding): the **three** `#2046` entries + the **D-6 `decision.py:464`** entry (which drains as a consolidation consequence of WP02). Extends the 01KVGCE8 `surface_resolution_audit` machinery (C-002). (IC-04+IC-05; FR-006, FR-007)

## Context (squad-mandated, anti-vacuous + anti-blind)
- The existing guard checks raw-path-JOINS (path *shape*). FR-006 needs a NEW discriminator: read SELECTION (a direct `resolve_mission_read_path` call / bespoke `resolve_mid8` cascade) outside the seam. Reusing the raw-join guard alone is VACUOUS.
- After WP02+WP03 migrate every read path (8-caller enumeration; `acceptance` migrated too → **no acceptance allowlist entry needed**), `discover_rows()` re-discovers ZERO raw joins at the four allowlisted keys (`context.py:72`, `mission.py:1327/1378` = #2046; `decision.py:464` = D-6) → all four drain. **`audit.py`'s `SLUG_NAMES ⊇ {mission_slug, feature_slug, slug, raw_handle, handle}` MUST stay unchanged-or-widened** — narrowing it is the fake-green hole 01KVGCE8 closed.

## Subtasks
### T017 — AST selection-callsite ratchet (FR-006a)
- Extend `audit.py` (`discover_rows`/a new discriminator): a NEW direct `resolve_mission_read_path` call OR a NEW bespoke `resolve_mid8(slug, …)`/`KITTY_SPECS_DIR/<handle>` mid8-cascade in a read path OUTSIDE the seam allowlist FAILS. Allowlist the seam itself + any legitimate seam-internal call by `file:line` (the existing mechanism).
### T018 — Seam runtime empty-mid8 gate test (FR-006b)
- Test that the seam's fail-closed gate (WP01) raises on empty-mid8-against-declared-coord (mirroring `_resolve_mission_dir:336`). Mutation: remove the gate → test FAILS.
### T019 — Two-axis + pre/post discrimination
- (a) inject a NEW direct `resolve_mission_read_path(repo_root, slug, mid8_from_slug(slug))` call into a read CLI outside the seam → ratchet FAILS; revert → PASSES. (b) Assert the ratchet PASSES on the adopted tree but **would have FAILED on the pre-mission tree** (it actually discriminates — not vacuous). Record both mutation results.
### T020 — Drain the residual entries by re-derivation (FR-007)
- After WP02+WP03, re-run `discover_rows()`; the four read-CLI keys (three `#2046`: `context.py:72`, `mission.py:1327/1378`; one D-6: `decision.py:464`) no longer appear → remove all four from `_ALLOWLISTED_RAW_JOINS`; update `inventory.md` to the migrated state, labeling the `decision.py:464` removal as a **D-6 consolidation** drain (not a #2046 residual). `test_allowlist_entries_are_not_stale` passes (no stale keys). The drain is BECAUSE the joins are gone, NOT by editing the net.
### T021 — Frozen-net + re-injection mutation
- Assert `SLUG_NAMES ⊇ {raw_handle, handle}` (a guard/test that fails if either is removed). Mutation: re-inject a `repo_root / KITTY_SPECS_DIR / raw_handle` join into a read CLI on the adopted tree → the guard FAILS (proving the net was not silently narrowed).

## Branch Strategy
Planning/base + merge target: `feat/read-side-surface-resolver-adoption`. Worktree per lane. Depends **WP02 + WP03** (the allowlist drains after migrations).

## Definition of Done
- [ ] AST selection-callsite ratchet added (NEW discriminator, not the raw-join guard alone); two-axis mutation bites; pre/post-tree discrimination proven.
- [ ] Seam runtime empty-mid8 gate test (mutation-verified).
- [ ] The 4 read-CLI allowlist keys (3 #2046 + 1 D-6 `decision.py:464`) drained by re-derivation; inventory.md updated (D-6 drain labeled as consolidation); `python audit.py` exits 0. No NEW acceptance/tasks allowlist entry was added (both migrated, not allowlisted).
- [ ] `SLUG_NAMES ⊇ {raw_handle, handle}` frozen; re-injection mutation FAILS the guard.
- [ ] ruff + mypy --strict clean; `tests/architectural/` green.

## Risks / Reviewer guidance
- **Risk (vacuous guard)**: satisfying FR-006 with the existing raw-JOIN guard. Insist on the NEW selection-callsite discriminator + the pre/post-tree discrimination check.
- **Risk (fake-drain)**: draining by removing `raw_handle` from `SLUG_NAMES`. The re-injection mutation + the frozen-net assertion are the antidote — confirm both.
- **Reviewer**: independently inject a direct `resolve_mission_read_path` call into a read CLI and confirm the ratchet catches it; confirm `SLUG_NAMES` still has `{raw_handle, handle}`.

## Activity Log

- 2026-06-20T17:03:18Z – claude:opus:python-pedro:implementer – shell_pid=2403664 – Assigned agent via action command
- 2026-06-20T17:48:58Z – claude:opus:python-pedro:implementer – shell_pid=2403664 – selection-callsite AST discriminator (catches direct resolve_mission_read_path calls raw-JOIN guard misses) + seam empty-mid8 gate test + 4-key drain confirmed + SLUG_NAMES frozen; lane 397912771. FLAG: 5 tests/architectural/ failures claimed pre-existing (verify)
- 2026-06-20T17:48:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=2458445 – Started review via action command
- 2026-06-20T17:59:29Z – user – shell_pid=2458445 – reviewer-renata APPROVE: non-vacuous selection-callsite discriminator (catches direct calls raw-JOIN blind to), drain real, SLUG_NAMES frozen, mutations bite. Reviewer adjudicated the 5 arch failures: 1 pre-existing, 4 MISSION-INTRODUCED (pre-merge fix needed, not WP05's scope)
