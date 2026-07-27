---
work_package_id: WP02
title: WP-REKEY-A — re-key 394 + classifier consumption + categories (single-owner 1/2)
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-010
- FR-013
- FR-014
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "2446012"
history:
- created at planning (tasks) — re-key A (chain 1/2)
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_dead_symbols.py
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/test_no_dead_symbols.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Read [spec.md](../spec.md)
FR-005/006/007/009/010/013/014 + DoD (a,c,e,f,h,i,k), [plan.md](../plan.md) §IC-REKEY
(esp. the impl notes: `_compute_offenders` at L1327, 4 in-file call sites; extend `_walk_modules`),
and the WP01 resolver contract. **SINGLE-OWNER of `test_no_dead_symbols.py` (C-003) — you are
chain 1/2; WP03 follows sequentially. NEVER run concurrently with WP03.**

## Objective
Re-key the 394-entry `_SYMBOL_ALLOWLIST` off `module::Name` onto the WP01 `SymbolKey`, threading
source/AST into the gate, consuming the live collision classifier (without it the re-key re-blinds
T004), and auto-deriving symbol-granular exempt categories. Bite battery a,c,e,f,h,i,k through the
PRODUCTION `_compute_offenders`/stale path (C-007 — a standalone-key test self-validates green).

## Subtasks

### T008 — extend `_walk_modules` to retain source
`code_tokens_by_line(source)` needs the source STRING; `_walk_modules` currently keeps only the
parsed tree (`path_to_tree`, L1201-1227). Extend it to also retain source text and invert the map
to `dotted → (tree, source)` (`_compute_offenders` iterates `decls` by dotted name). `_walk_modules`
is NOT in the C-005 byte-frozen set — safe to edit.

### T009 — thread source/AST + collision index into `_compute_offenders` (FR-013 substrate)
Current signature (L1327): `_compute_offenders(decls, per_symbol, star_targets, allowlist)`. Thread
BOTH the dotted→(tree, source) map (to compute each decl's `SymbolKey`) **AND the collision index**
(post-tasks squad DEFECT 3 — `key_tier(key, index)` needs it at the exemption site; don't forget it).
**All 4 call sites are in this file** (L1368 prod + L1568/1575/1581 teeth test) — update all four.
Change is contained; do NOT touch `known_modules`/`_record_*_edges`/`_imports_by_target` (C-005
byte-frozen). Import `SymbolKey`/`classify_collisions`/`key_tier` **top-level from `_symbol_key`**
(safe — WP01 defers its helper import, so no cycle).

### T010 — re-key all 394 entries onto SymbolKey (FR-007)
Across the 19 category frozensets, replace each `module::Name` string with its `SymbolKey`
(via WP01's resolver). The gate's exemption check (`if qualified in allowlist`) becomes a
`SymbolKey`-based membership. Preserve every rationale/category grouping.

### T011 — drop 2 stale (FR-006) + baseline doc-count
Remove `charter_activate_app` / `charter_deactivate_app` (no longer exist) from
`_CATEGORY_B_GRANDFATHERED_LEGACY`. Update the human-maintained `_baselines.yaml`
`test_no_dead_symbols.category_b_grandfathered_legacy` 215→213 (**doc hygiene only — NOT
machine-enforced**; `test_ratchet_baselines` maps only `test_no_dead_modules` CATEGORY_1..7 +
fixed single-ratchets, verified — dropping these trips NO shrink-warn).

### T012 — consume the live classifier + ≥2-escalation (FR-005/FR-009)
Wire WP01's `classify_collisions` + `key_tier` into the gate so tier assignment is recomputed
LIVE each run; a content key resolving to ≥2 live locations escalates to module_path OR
fail-closes. **This is load-bearing: without it the single-tier re-key re-blinds T004 on the
ArtifactKind trio.** A `None`-key entry fail-closes (flag, never silent-exempt).

### T013 — symbol-granular categories (FR-010) + disjointness meta-test
Auto-derive exemptions per-SYMBOL (never per-module): registered `@MigrationRegistry.register`
CLASS only (a dead helper/constant in an `m_*.py` is still caught); re-export shims by
definition-shape; Typer sub-apps by call/decorator. Add a meta-test asserting
`auto_exempt ∩ hand_allowlist = ∅`.

### T014 — bite battery (a,c,e,f,h,i,k) + meta-guard green (FR-013/FR-014)
Through the PRODUCTION `_compute_offenders`/stale path: (a) genuinely-dead caught; (c) same-name
fan-out dead sibling caught (T004); (e) dead migration-file helper caught despite FR-010;
(f) undecidable/None-key fail-closed; (h) `known_modules` + 4 T004 detector tests byte-unchanged +
green; (i) **live-collision regression guard** — plant a NEW byte-identical same-name pair (the
GateDecision-collapse vector) → gate escalates/fail-closes → unsanctioned sibling STILL caught;
(k) all 394 entries resolve to a SymbolKey (0 un-keyable). Assert the merged meta-guard
`test_ratchet_positional_anchor_ban.py` stays green (FR-014 — the new key is all-strings).

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json` via
`spec-kitty agent action implement WP02 --agent <you>` (branches from WP01's approved base).

## Definition of Done
- 394 entries re-keyed; 2 stale dropped + baseline doc updated; classifier consumed (≥2→escalate/
  fail-close); symbol-granular categories + disjointness meta-test; bite (a,c,e,f,h,i,k) through the
  production path; meta-guard green; full `tests/architectural/` 0-failed (baseline 887); ruff+mypy clean.
- `known_modules`/`_record_*_edges`/`_imports_by_target` BYTE-UNCHANGED; `_find_facade_lazy_dict_name`/
  `_resolve_relative_module` signatures unchanged (WP01 imports them).

## Reviewer guidance (reviewer-renata, opus)
The make-or-break: confirm the classifier is CONSUMED (not just present) so the re-key does NOT
re-blind T004 — verify the (i) GateDecision-collapse fixture reds through the production path.
Confirm the bite battery hits `_compute_offenders`/stale, not a standalone key fn (C-007). Confirm
the C-005 byte-frozen set is untouched. Confirm 0 un-keyable entries (k).

## Activity Log
- 2026-07-11T19:24:26Z – claude:sonnet:python-pedro:implementer – shell_pid=2183795 – Assigned agent via action command
- 2026-07-11T20:29:14Z – claude:sonnet:python-pedro:implementer – shell_pid=2183795 – Ready: 394 re-keyed onto SymbolKey (resolve_symbol_key); live classifier CONSUMED (classify_collisions+key_tier, >=2->escalate/fail-close, T004 preserved, not frozen); 2 stale dropped + baseline 215->194 (honest live count after FR-010 auto-exemption); symbol-granular categories + disjointness meta-test; bite (a,c,e,f,h,i,k) through production path incl (i) GateDecision-collapse; meta-guard GREEN; full arch 896/0. FLAGS FOR REVIEWER: (1) OUT-OF-MAP missions/__init__.py facade-dict hoist to module-level (behavior-preserving, to make FR-003 shape keyable) — scrutinize vs module_path-tier/fail-close; (2) baseline 215->194 is 21 fewer not 2 — verify the 19 are legit FR-010 auto-exempted registered-migration entries.
- 2026-07-11T20:29:57Z – claude:opus:reviewer-renata:reviewer – shell_pid=2375593 – Started review via action command
- 2026-07-11T20:44:59Z – user – shell_pid=2375593 – Moved to planned
- 2026-07-11T20:48:49Z – claude:sonnet:python-pedro:implementer – shell_pid=2446012 – Started implementation via action command
