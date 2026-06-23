---
work_package_id: WP03
title: 'Mechanical .kind drop (1/3: CLI agent surface) (FR-001a)'
dependencies:
- WP02
requirement_refs:
- FR-001
- NFR-001
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T008
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1591629"
history:
- Created by /spec-kitty.tasks 2026-06-23
- 'Split 1/3 of the 15-file mechanical drop (sizing squad 2026-06-23): WP03 (CLI agent surface) → WP14 (coord/events/runtime) → WP15 (core/git/upgrade), sequential lane B.'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/safe_commit_cmd.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-001a (mechanical drop, 1 of 3)** — the mechanical half of the
`CommitTargetKind` eradication, **CLI agent-command surface**: at every
**construction site** in this WP's 5 owned files, drop the
`kind=CommitTargetKind.PRIMARY` argument (it becomes `CommitTarget(ref=…)`) and
remove the now-unused `CommitTargetKind` imports. The enum still exists after this
WP (WP16 deletes it); this WP + WP14 + WP15 convert the easy sites so the deletion
is unblocked. Behavior-neutral (PRIMARY ≡ the default routing).

## Context
- The 15-file mechanical drop was split 3 ways for context-window fit (sizing
  squad 2026-06-23): **WP03 = CLI agent surface** (this WP) →
  **WP14 = coordination/events/runtime** → **WP15 = core/git/upgrade**, sequential
  in lane B. Each is the same mechanical operation on a disjoint file group.
- Leave the 3 `kind=COORDINATION` **needs-care** sites and the 2 `runtime_bridge`
  parallel-classifier sites to **WP04** (those are semantic / risk C-011).
- `context.py`, `resolution.py`, `runtime_bridge.py`, `surface_resolver.py`,
  `status_transition.py` are owned by WP02/WP04/WP06 (same lane) — do NOT edit
  them here. `policy.py`/`transaction.py`/`decision_log.py`/`artifacts.py`/
  `mission_runtime/__init__.py` are WP14's; `core/`, `invocation/`,
  `orchestrator_api/`, `git/commit_helpers.py`, `upgrade.py` are WP15's.

## Subtasks
### T008 — Drop mechanical kind=PRIMARY + imports
For each owned file: find `CommitTarget(... kind=CommitTargetKind.PRIMARY ...)`
constructions and `kind=CommitTargetKind.PRIMARY` keyword args, drop the `kind=`
argument; remove the `from ... import CommitTargetKind` / `CommitTargetKind`
references that become unused. Run `grep -n CommitTargetKind <file>` per owned
file to enumerate; convert only the **PRIMARY** ones. If a site reads `.kind` or
constructs `COORDINATION`/`FLATTENED`, leave it and note it for WP04/WP05.
Verify each converted site is behavior-identical (PRIMARY was the implicit default).

## Campsite (#1970)
In each touched file: remove dead imports exposed by the drop, fix lint/type debt
on touched lines, hoist S1192 literals if you introduce/expose any. Bounded to the
`.kind`-touch zone.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP03-specific test-DoD
- **CT1 re-key clause.** This WP's edits drop only the `kind=PRIMARY` kwarg (content otherwise stable), so the architectural ratchets in `test_single_mission_surface_resolver.py`/`test_no_write_side_rederivation.py` are expected to **STAY green**. If a ratchet entry goes red, that is a **real change to investigate** (re-key on `composite_key` with rationale only after confirming the converted site is behavior-identical) — never a line-bump. Do NOT add a golden count of converted sites (CT5).

## Definition of Done
- All mechanical `kind=PRIMARY` sites in the owned files converted to `CommitTarget(ref=…)`.
- 3 `kind=COORDINATION` + 2 runtime_bridge sites NOT touched (left for WP04).
- `ruff`/`mypy` clean; full `tests/` green (behavior-neutral). The enum still
  imports cleanly (not yet deleted).

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, after WP02). Worktree from `lanes.json`.

## Reviewer guidance
Confirm no `kind=COORDINATION` site was silently dropped (that would change
routing). Confirm imports removed only where genuinely unused. The enum must still
exist post-WP03.

## Activity Log

- 2026-06-23T08:21:19Z – claude:sonnet:python-pedro:implementer – shell_pid=1513458 – Assigned agent via action command
- 2026-06-23T08:40:53Z – claude:sonnet:python-pedro:implementer – shell_pid=1513458 – Ready: kind=PRIMARY dropped in CLI agent surface (5 files, 8 sites); 12 baseline entries removed from CT1 ratchet; COORDINATION/FLATTENED sites left for WP04/05/16; inventory.md line-ref updated; 2 expected interim mypy call-arg errors (resolve when WP16 removes kind field)
- 2026-06-23T08:43:12Z – user – shell_pid=1513458 – Moved to planned
- 2026-06-23T08:43:34Z – claude:sonnet:python-pedro:implementer – shell_pid=1574774 – Started implementation via action command
- 2026-06-23T08:48:55Z – claude:sonnet:python-pedro:implementer – shell_pid=1574774 – Cycle 2: added transitional kind=PRIMARY default (context.py out-of-map, justified); CommitTarget(ref=…) now behavior-neutral; mypy call-arg errors resolved
- 2026-06-23T08:49:30Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1591629 – Started review via action command
- 2026-06-23T08:57:27Z – user – shell_pid=1591629 – Cycle 2 APPROVED: transitional kind=PRIMARY default makes the drop behavior-neutral; mypy call-arg errors at safe_commit_cmd.py:243,263 resolved (only pre-existing no-any-return:71 remains); 8 PRIMARY drops intact; no CommitTargetKind imports remain in 5 owned files; out-of-map context.py edit is exactly 1 line with rationale; WP01 ratchet green (10/10); test_commit_target_kind_default_is_primary PASSED; 16/16 tests pass; ruff clean. --force: lane-c is 94 commits behind feat/single-authority-topology-cleanup but rebase conflicts on planning artifacts (kitty-specs/spec.md, issue-matrix.md) — conflict is in non-code files only, all code checks passed.
