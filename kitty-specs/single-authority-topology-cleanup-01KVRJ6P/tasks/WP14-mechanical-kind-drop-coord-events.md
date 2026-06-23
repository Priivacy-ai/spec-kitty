---
work_package_id: WP14
title: 'Mechanical .kind drop (2/3: coordination/events/runtime) (FR-001a)'
dependencies:
- WP03
requirement_refs:
- FR-001
- NFR-001
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T027
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1629782"
history:
- Created by sizing-squad re-slice 2026-06-23 (split 2/3 of WP03's 15-file mechanical drop; sequential lane B after WP03).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/policy.py
- src/specify_cli/coordination/transaction.py
- src/specify_cli/events/decision_log.py
- src/mission_runtime/artifacts.py
- src/mission_runtime/__init__.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-001a (mechanical drop, 2 of 3)** — the same mechanical `CommitTargetKind`
drop as WP03, on the **coordination / events / runtime** file group: drop every
`kind=CommitTargetKind.PRIMARY` argument (→ `CommitTarget(ref=…)`) and remove the
now-unused `CommitTargetKind` imports in this WP's 5 owned files. The enum still
exists after this WP (WP16 deletes it). Behavior-neutral (PRIMARY ≡ default routing).

## Context
- Split 2/3 of the 15-file mechanical drop (sizing squad 2026-06-23):
  WP03 (CLI agent surface) → **WP14 (this WP)** → WP15 (core/git/upgrade),
  sequential lane B. Same operation, disjoint file group.
- **Leave the COORDINATION carriers for WP04.** `policy.py:215`,
  `decision_log.py:95`, and the synthetic `artifacts.py:127`
  `CommitTarget(ref="", kind=COORDINATION)` residue carrier are **needs-care**
  semantic sites converted in **WP04** (T009) — do NOT convert them here. This WP
  drops only the **PRIMARY** constructions + unused imports in these files. If a
  file has no PRIMARY site (only the COORDINATION carrier), limit this WP's touch
  to genuinely-unused-import cleanup and leave the carrier for WP04.
- `mission_runtime/__init__.py`: drop a `CommitTargetKind` re-export only if it is
  unused after this group's drops; if WP04/WP16 still need the export, leave it
  (WP16 finalizes the export removal when the enum is deleted).

## Subtasks
### T027 — Drop mechanical kind=PRIMARY + imports (coord/events/runtime group)
For each owned file: find `CommitTarget(... kind=CommitTargetKind.PRIMARY ...)`
constructions and `kind=CommitTargetKind.PRIMARY` keyword args, drop the `kind=`
argument; remove the `from ... import CommitTargetKind` references that become
unused. Run `grep -n CommitTargetKind <file>` per owned file to enumerate; convert
only the **PRIMARY** ones. If a site reads `.kind` or constructs
`COORDINATION`/`FLATTENED`, leave it and note it for WP04/WP05/WP16. Verify each
converted site is behavior-identical (PRIMARY was the implicit default).

## Campsite (#1970)
In each touched file: remove dead imports exposed by the drop, fix lint/type debt
on touched lines, hoist S1192 literals if you introduce/expose any. Bounded to the
`.kind`-touch zone.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP14-specific test-DoD
- **CT1 re-key clause.** This WP's edits drop only the `kind=PRIMARY` kwarg (content
  otherwise stable), so the architectural ratchets in
  `test_single_mission_surface_resolver.py`/`test_no_write_side_rederivation.py` are
  expected to **STAY green**. If a ratchet entry goes red, that is a **real change to
  investigate** (re-key on `composite_key` with rationale only after confirming the
  converted site is behavior-identical) — never a line-bump. Do NOT add a golden
  count of converted sites (CT5).
- **COORDINATION-carrier untouched assertion.** Confirm (by the existing residue /
  routing tests staying green) that the `artifacts.py:127` COORDINATION carrier and
  the `policy.py`/`decision_log.py` COORDINATION sites are **unchanged** by this WP —
  they are WP04's to convert; a silent drop here would change routing.

## Definition of Done
- All mechanical `kind=PRIMARY` sites in the 5 owned files converted to
  `CommitTarget(ref=…)`; unused imports removed.
- The COORDINATION carriers (`policy.py:215`, `decision_log.py:95`,
  `artifacts.py:127`) NOT touched (left for WP04).
- `ruff`/`mypy` clean; full `tests/` green (behavior-neutral). The enum still
  imports cleanly (not yet deleted).

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, after WP03). Worktree from `lanes.json`.

## Reviewer guidance
Confirm no `kind=COORDINATION` site was silently dropped (that would change
routing). Confirm imports removed only where genuinely unused. The enum must still
exist post-WP14.

## Activity Log

- 2026-06-23T08:58:26Z – claude:sonnet:python-pedro:implementer – shell_pid=1606207 – Started implementation via action command
- 2026-06-23T09:09:14Z – claude:sonnet:python-pedro:implementer – shell_pid=1606207 – Ready: kind=PRIMARY dropped in coord/events/runtime; COORDINATION carriers (policy:215/decision_log:95/artifacts:127) left for WP04; ratchet shrunk by 2 entries (10/10 pass); 354 tests pass
- 2026-06-23T09:10:06Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1629782 – Started review via action command
- 2026-06-23T09:13:26Z – user – shell_pid=1629782 – Review passed: COORDINATION carriers (policy.py:215, decision_log.py:95, artifacts.py:127) confirmed untouched; single PRIMARY drop in transaction.py (BookkeepingTransaction.commit) behavior-neutral with transitional default; ratchet shrunk by real composite-key removal (2 entries); CommitTargetKind re-export retained in mission_runtime/__init__.py; 364 tests green; ruff clean; 2 pre-existing mypy no-any-return errors in transaction.py:164/175 confirmed pre-existing before WP14. Guard friction overridden: 102-commit gap is all coordination-branch status churn from other lanes, not code drift.
