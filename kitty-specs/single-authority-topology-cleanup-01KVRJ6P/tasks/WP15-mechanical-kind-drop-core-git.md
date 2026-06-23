---
work_package_id: WP15
title: 'Mechanical .kind drop (3/3: core/git/upgrade) (FR-001a)'
dependencies:
- WP14
requirement_refs:
- FR-001
- NFR-001
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T028
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1672573"
history:
- Created by sizing-squad re-slice 2026-06-23 (split 3/3 of WP03's 15-file mechanical drop; sequential lane B after WP14). Tail of the mechanical drop — unblocks WP04's enum deletion.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/core/mission_creation.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/git/commit_helpers.py
- src/specify_cli/cli/commands/upgrade.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-001a (mechanical drop, 3 of 3)** — the same mechanical `CommitTargetKind`
drop as WP03/WP14, on the **core / invocation / orchestrator / git / upgrade**
file group: drop every `kind=CommitTargetKind.PRIMARY` argument
(→ `CommitTarget(ref=…)`) and remove the now-unused `CommitTargetKind` imports in
this WP's 5 owned files. This is the **tail** of the mechanical drop — after this
WP, the only `.kind` surface remaining is the semantic set WP04/WP16 delete.
Behavior-neutral (PRIMARY ≡ default routing).

## Context
- Split 3/3 of the 15-file mechanical drop (sizing squad 2026-06-23):
  WP03 (CLI agent surface) → WP14 (coord/events/runtime) → **WP15 (this WP)**,
  sequential lane B. Same operation, disjoint file group.
- `git/commit_helpers.py` is also touched later by **WP07** (CommitResult JSON,
  disjoint `.kind`-free concern) — same lane B, sequential, shared ownership legal.
  Touch only the `kind=PRIMARY` constructions here.
- `upgrade.py` is also touched by **WP05** (FLATTENED producer cleanup, T-FR-002) —
  this WP drops only the PRIMARY `.kind` arg; leave any `FLATTENED` producer arm for
  WP05.
- Do NOT touch the `kind=COORDINATION` carriers (WP04) or the topology files
  (WP02/WP04/WP06).

## Subtasks
### T028 — Drop mechanical kind=PRIMARY + imports (core/git/upgrade group)
For each owned file: find `CommitTarget(... kind=CommitTargetKind.PRIMARY ...)`
constructions and `kind=CommitTargetKind.PRIMARY` keyword args, drop the `kind=`
argument; remove the `from ... import CommitTargetKind` references that become
unused. Run `grep -n CommitTargetKind <file>` per owned file to enumerate; convert
only the **PRIMARY** ones. If a site constructs `COORDINATION`/`FLATTENED` or reads
`.kind`, leave it and note it for WP04/WP05/WP16. Verify each converted site is
behavior-identical.

## Campsite (#1970)
In each touched file: remove dead imports exposed by the drop, fix lint/type debt
on touched lines, hoist S1192 literals if you introduce/expose any. Bounded to the
`.kind`-touch zone.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP15-specific test-DoD
- **CT1 re-key clause.** Drops only the `kind=PRIMARY` kwarg → the architectural
  ratchets stay green. A red ratchet entry is a **real change to investigate**, never
  a line-bump; no golden count of converted sites (CT5).
- **Enum-still-imports gate.** After this WP the enum still exists (WP16 deletes it);
  assert `from mission_runtime import CommitTargetKind` still imports — its deletion is
  WP16's, not this WP's. (Negative control against an over-eager deletion here.)

## Definition of Done
- All mechanical `kind=PRIMARY` sites in the 5 owned files converted to
  `CommitTarget(ref=…)`; unused imports removed.
- No `kind=COORDINATION`/`FLATTENED` site touched (left for WP04/WP05/WP16).
- `ruff`/`mypy` clean; full `tests/` green (behavior-neutral). The enum still
  imports cleanly (not yet deleted) — WP16 deletes it.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, after WP14). Worktree from `lanes.json`.

## Reviewer guidance
Confirm no `kind=COORDINATION`/`FLATTENED` site was silently dropped. Confirm imports
removed only where genuinely unused. The enum must still exist post-WP15 (WP16 owns
the deletion).

## Activity Log

- 2026-06-23T09:14:06Z – claude:sonnet:python-pedro:implementer – shell_pid=1639337 – Started implementation via action command
- 2026-06-23T09:26:01Z – claude:sonnet:python-pedro:implementer – shell_pid=1639337 – Ready: kind=PRIMARY dropped in core/git/upgrade (tail of mechanical drop); FLATTENED producer + COORDINATION left for WP05/WP04; enum still imports; ratchet baseline pruned (8 entries removed); ruff/mypy/pytest green
- 2026-06-23T09:26:34Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1672573 – Started review via action command
- 2026-06-23T09:29:23Z – user – shell_pid=1672573 – Review passed: 4 PRIMARY drops (mission_creation:189, executor:479, commands:1294, commit_helpers:923) clean; upgrade.py FLATTENED producer untouched + CommitTargetKind import retained; no COORDINATION site touched; enum still imports; ratchet shrank by exactly 8 entries (40 lines removed) with rationale comment; ruff clean; mypy 1 pre-existing error on commit_helpers.py:477 confirmed pre-existing via stash-check; 10/10 architectural ratchet tests pass; scope strictly 4 source files + ratchet test. Behavior-neutral.
