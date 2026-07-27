---
work_package_id: WP08
title: Load-bearing architectural guard
dependencies:
- WP01
- WP06
- WP07
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2146042"
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: WP authored from plan IC-07 (FR-004); clone 01KVFTFV guard.
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_single_mission_surface_resolver.py
create_intent:
- tests/architectural/test_single_mission_surface_resolver.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- tests/architectural/test_single_mission_surface_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Clone the 01KVFTFV load-bearing guard for surface resolution: a `tests/architectural/` test, anchored on WP01's audited-surface inventory, that FAILS when a new `raw-bypass` join (`repo_root/KITTY_SPECS_DIR/<slug>` outside the canonical resolver/delegator set) is introduced — proven load-bearing. (IC-07; FR-004, SC-002)

## Context
- WP01 produced `tests/architectural/surface_resolution_audit/audited-surfaces.md` + `audit.py` — anchor on THAT inventory (not a blanket `Path /` matcher).
- Runs on the **final** collapsed tree: WP06 (collapse) **and WP07 (shim deleted)** both done, so `feature_dir_resolver.py` no longer exists and the audited surface set is final. The existing `tests/architectural/test_topology_resolution_boundary.py` is a sibling pattern.

## Subtasks
### T030 — Implement the guard
- `tests/architectural/test_single_mission_surface_resolver.py`: import/reuse the WP01 `audit.py`; assert every audited surface routes the canonical resolver/delegator; zero `raw-bypass` rows remain. Anchor strictly on the inventory.
### T031 — Load-bearing self-test (≥2 real-code mutations + independent floor)
- (a) Real-code mutation at **two distinct sites** — inject a `repo_root / KITTY_SPECS_DIR / mission_slug` raw join into one resolver file AND one consumer file → the guard FLAGS both; revert → clears. (b) Coverage assertion: the inspected surface set is non-empty AND equals the WP01 inventory. (c) **Independent floor** (guards against a circular thin-inventory): assert the inventory's `raw-bypass`+`routed-through-resolver` row count ≥ the count of `rg -l 'KITTY_SPECS_DIR' src/` minus the named topology-blind set — so an under-tracing WP01 walker can't yield a small-but-self-consistent baseline the guard then rubber-stamps. Record all mutation results in the WP history.
### T032 — Gate placement + full run
- Confirm the guard is collected by the architectural suite (CI core-misc); `PWHEADLESS=1 python -m pytest tests/architectural/ -p no:cacheprovider -q` green on the collapsed tree; ruff + mypy --strict clean.

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends **WP01** (inventory) + **WP06** (collapsed state) + **WP07** (shim deleted — final surface set).

## Definition of Done
- [ ] Guard anchored on WP01's inventory (not a blanket heuristic); zero raw-bypass on the collapsed tree.
- [ ] Load-bearing proven: raw-bypass mutation at ≥2 distinct real files flags; coverage assertion non-empty == inventory; independent floor (KITTY_SPECS_DIR file count minus topology-blind) holds.
- [ ] Green in the architectural suite; ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk**: a vacuous guard (matches nothing) — the coverage assertion + real-code mutation are the antidote; insist the self-test bites.
- **Reviewer**: independently inject a raw-bypass join into a real audited file and confirm the guard catches it.

## Activity Log

- 2026-06-20T12:06:21Z – claude:sonnet:python-pedro:implementer – shell_pid=2127747 – Assigned agent via action command
- 2026-06-20T12:25:36Z – claude:sonnet:python-pedro:implementer – shell_pid=2127747 – Load-bearing guard (44c17868b): fresh audit 27 rows (aggregate:430 bypass GONE), discover_rows()-based (bypasses stale inventory), 6 tests, ≥2-site mutation flags+clears both, coverage floor holds, ruff+mypy clean. CRUX: 6 raw-joins allowlisted (2 DIAG + 4 TBYD incl decision.py:464 reclassified WP01-raw-bypass→TBYD). Reviewer rule allowlist legit vs vacuous. Both static inventories stale (sweep).
- 2026-06-20T12:25:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=2146042 – Started review via action command
- 2026-06-20T12:38:32Z – user – shell_pid=2146042 – reviewer-renata APPROVED: guard bites (2 real injections caught+reverted), all 6 allowlist entries honest in source (decision.py:464 = genuine primary-meta bootstrap, _SAFE_SLUG_RE-guarded, TBYD honest), floor/non-vacuity real, anchored on live discover_rows(). Followups (non-blocking): route decision.py:464 thru primitive; walker SyntaxError→empty false-negative.
