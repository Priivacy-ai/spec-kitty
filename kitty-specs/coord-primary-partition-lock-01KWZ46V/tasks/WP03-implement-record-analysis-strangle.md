---
work_package_id: WP03
title: implement.py + record_analysis strangle (fail-closed)
dependencies:
- WP01
requirement_refs:
- C-001
- C-005
- C-006
- FR-004
- FR-005
- FR-011
- NFR-004
tracker_refs: []
planning_base_branch: design/coord-primary-partition-lock
merge_target_branch: design/coord-primary-partition-lock
branch_strategy: Planning artifacts for this mission were generated on design/coord-primary-partition-lock. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-primary-partition-lock unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1722045"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/implement.py
create_intent:
- tests/specify_cli/cli/commands/test_implement_placement_routing.py
- tests/specify_cli/cli/commands/agent/test_record_analysis_placement.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/mission_record_analysis.py
- tests/specify_cli/cli/commands/test_implement_placement_routing.py
- tests/specify_cli/cli/commands/agent/test_record_analysis_placement.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` (implementer) via `/ad-hoc-profile-load`. Read `spec.md`, `plan.md` (IC-03),
`research.md` (D6, **D11**), and `contracts/seam-api.md`. **Authoritative over sibling missions
(C-005)** on these surfaces. Depends on **WP01**. Implement via
`spec-kitty agent action implement WP03 --agent claude`.

## Objective

Route the `implement.py` planning-artifact write sites and `mission_record_analysis.py`
(ANALYSIS_REPORT) through the seam, and **resolve the two forbidden `None → CommitTarget(ref=<checkout>)`
legacy fallbacks fail-closed** (require-canonical, per D11). Red-first (C-006).

## Context

- `implement.py:886` (`str(coord_branch) if coord_branch else planning_branch`) and `:1462`
  (`_get_cur_branch() or planning_branch`) derive placement from the checkout. (Line numbers are indicative — symbol-anchor them; post-rebase drift.)
- `implement.py:672` `_resolve_placement_ref` returns `None` → legacy `CommitTarget(ref=_cur_branch)` at `:1467`.
- `mission_record_analysis.py:80` `_resolve_record_analysis_placement_ref` returns `None` → conservative legacy preflight. This is the **second CommitTarget producer** the earlier squad missed — SC-001 requires it.
- D11: the inline "C-004 never break the lifecycle" comment does NOT license a silent shadow path.
- **Squad M3 (red-first must resolve):** `implement.py:886`'s value may be non-load-bearing — the comment at `implement.py:880-884` says it "is never persisted; the legacy fallback in `BookkeepingTransaction` overrides `destination_ref` from HEAD" (`transaction.py:751-771`). T010's red-first MUST establish whether `:886` is the live bypass or a placeholder. If the `transaction.py` legacy HEAD override is the real derivation, it is **#1878 commit-durability territory → tracked in #2453**, NOT routed here. Likewise the **third D11 fallback** `orchestrator_api/commands.py:1451` is **#2453**, not routed here (both flagged VISIBLE by WP07's grammar).

## Subtasks

### T010 — Red-first
- Failing tests proving `implement.py` planning commit + record-analysis derive placement from the checkout / None-fallback (red against pre-fix code).

### T011 — Route implement.py write sites
- Route `:886` and `:1462` through `seam.write_target(kind)` (kind = the artifact being committed). If T010 proves `:886` is a non-persisted placeholder (see M3), route the load-bearing site the transaction actually consumes; the `transaction.py` legacy HEAD override itself is #2453, not here.

### T012 — Fail-closed the implement.py fallback (D11)
- Replace `_resolve_placement_ref:672` → `:1467` `None → CommitTarget(ref=_cur_branch)` with a
  **structured require-canonical error** when the seam cannot resolve. If a genuinely-legacy mission
  needs support, route it via migration/backfill — NOT a silent runtime checkout fallback.

### T013 — Route + fail-close record_analysis
- Route `mission_record_analysis.py:80` (ANALYSIS_REPORT → coord partition) through `seam.write_target(ANALYSIS_REPORT)`; remove its `None → legacy` preflight fallback (require-canonical).

### T014 — Tests + regression
- Cover both sites: routed placement lands partition-correct; fail-closed raises the structured error (not a checkout commit); ANALYSIS_REPORT lands on the coord surface for coord missions.

### T015 — Campsite (Sonar)
- See table. Hoist the rich-markup error prefixes (`'[red]Error:[/red] '`, `'[bold yellow]'`/`'[/bold yellow]'`) to constants where you touch those functions.

## Campsite (Sonar issues in owned files)

| File | Rule | Location | Class | Action |
|------|------|----------|-------|--------|
| `mission_record_analysis.py` | S1192 | `'[red]Error:[/red] '` ×5, `'success'`/`'error'` ×6 | SAFE | Hoist markup + status constants |
| `mission_record_analysis.py` | S3776 | `record_analysis` cyclomatic 11 | SAFE | Keep ≤15 as you edit |
| `implement.py` | S1192 | `'[bold yellow]'`/`'[/bold yellow]'` ×4, `'[/cyan]'` ×3 | SAFE | Hoist markup constants if in a touched function |
| `implement.py` | S1192 | `'status'`/`'meta.json'`/`'validate'`/`'create'` ×6-7 | ADJACENT | Hoist only inside functions you edit |
| `implement.py` | empty-except | `except Exception: pass` l.102 — already `# noqa: S110` justified | LEAVE | Not a finding |

## Branch Strategy

Base / merge target `design/coord-primary-partition-lock`. Worktree per computed lane; enter via the
implement command. **Authoritative (C-005):** if the sibling `coord-authority-gate-hardening` /
`implement-loop-coord-authority` missions collide on these files, our routing is canonical — they rebase.

## Definition of Done

- Both `implement.py` sites + `record_analysis` route through `seam.write_target`.
- Both forbidden fallbacks are fail-closed (structured error), not checkout commits.
- Red-first tests green; regression for coord + non-coord + fail-closed path.
- `ruff` + `mypy` clean; ≤15 complexity; markup/status constants hoisted.

## Risks & Reviewer guidance

- **D11 is binding** — reviewer must reject any residual `if …is None: CommitTarget(ref=<checkout>)`.
- Confirm the fail-closed error is actionable (names the mission + missing canonical input) and does not break legitimate lifecycle flows (test a real implement claim end-to-end).
- These are exactly the sites WP07's grammar locks — leave them seam-routed.

## Activity Log

- 2026-07-07T22:45:09Z – claude:sonnet:python-pedro:implementer – shell_pid=1503078 – Assigned agent via action command
- 2026-07-07T23:22:28Z – claude:sonnet:python-pedro:implementer – shell_pid=1503078 – Ready; D11 fail-closed; ruff exit 0
- 2026-07-07T23:23:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=1722045 – Started review via action command
- 2026-07-07T23:29:53Z – user – shell_pid=1722045 – Review passed (reviewer-renata): both implement.py sites routed through seam-resolved placement_ref (:886 uses placement_ref.ref; :1462 claim-commit via _resolve_claim_commit_target); D11 fail-closed CONFIRMED not-swallowed (except PlacementResolutionRequired:raise ordered BEFORE broad except Exception, call sits in outer try not inner safe_commit try); record_analysis fails closed at consumption (_require_record_analysis_placement, preflight_calls==[] proven); no residual None->CommitTarget(checkout) fallback; #2453 (transaction.py, orchestrator_api:1451) UNTOUCHED and :886 non-load-bearing claim sound (transaction._resolve_legacy_lane_destination derives from HEAD); red-first non-vacuous (static grammar guards + behavioral sentinel/preflight tests); ratchet green (28 passed); ruff clean; mypy clean under CI whole-tree invocation (per-file cannot-subclass is a known artifact identical to passing precedent); campsite S1192 constants hoisted.
