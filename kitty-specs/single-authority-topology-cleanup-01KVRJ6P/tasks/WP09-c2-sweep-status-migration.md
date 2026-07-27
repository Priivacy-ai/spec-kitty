---
work_package_id: WP09
title: 'C2 sweep cluster 1: status/migration/coordination (FR-006b)'
dependencies:
- WP08
requirement_refs:
- FR-006
- NFR-001
- NFR-004
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T020
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1574774"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/status/emit.py
- src/specify_cli/status/lifecycle.py
- src/specify_cli/migration/mission_state.py
- src/specify_cli/migration/normalize_mission_lifecycle.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/task_utils/support.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-006b** — convert the status / migration / coordination meta-readers to the
canonical polymorphic `load_meta` (from WP08), choosing the `allow_missing` /
`on_malformed` arguments that reproduce each site's CURRENT behavior exactly.
Behavior-neutral per site.

## Context
- `task_utils/support.load_meta:363` is one of the 3 legacy contracts
  (raise-on-missing, utf-8-sig). Convert it to delegate to the canonical reader
  with the matching args (this also fixes the `task_helpers` re-export in WP11).
- EXCLUDE (owned by other lanes — do NOT touch): `resolution.py`,
  `surface_resolver.py`, `status_transition.py`, `_read_path_resolver.py`,
  `mission.py`, `tasks.py`, `commit_helpers.py` (Lane B); `acceptance/__init__.py`
  (Lane E); `merge.py` (Lane F); `task_helpers.py` (Lane D).

## Subtasks
### T020 — Convert cluster-1 sites
For each owned file, replace the inline `json.loads(meta_path…)` / local
`_load_meta` / `load_meta` calls with the canonical `load_meta(dir, allow_missing=…, on_malformed=…)`,
preserving exact current behavior (match the missing/malformed contract per site).
Add/keep a focused test per converted module proving the contract is unchanged
(esp. the missing + malformed branches). Remove the now-dead local readers.

## Campsite (#1970)
Remove dead local `_load_meta` helpers superseded by the canonical reader; hoist
S1192; fix lint/type debt on touched lines.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP09-specific test-DoD
- **Contract test per distinct (missing, malformed) behavior present in the owned file** — NOT one test per module. For each distinct contract a converted site carries, assert **both arms' observable RETURN value** (None / raise / `{}`), NOT the `load_meta` call args (CT4 — do not assert the canonical reader was called with particular kwargs; assert the site's behavior is unchanged).

## Definition of Done
- All cluster-1 sites use the canonical reader; local duplicate readers removed;
  behavior unchanged (one contract test per distinct missing/malformed behavior,
  asserting observable return — not call args). `ruff`/`mypy` clean; full `tests/`
  green. Net LOC down.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane C (after WP08). Worktree from `lanes.json`.

## Reviewer guidance
Spot-check 2-3 sites: does the chosen `allow_missing`/`on_malformed` reproduce the
exact pre-change behavior (missing → ? / malformed → ?)? Reject any silent
contract drift.

## Activity Log

- 2026-06-23T07:55:42Z – claude:sonnet:python-pedro:implementer – shell_pid=1366956 – Assigned agent via action command
- 2026-06-23T08:25:11Z – claude:sonnet:python-pedro:implementer – shell_pid=1366956 – Ready: cluster-1 sites (status/migration/coordination) on canonical load_meta with explicit error-contract kwargs; local load_meta duplicate removed from task_utils/support; contract tests assert observable return value (CT4) per distinct missing/malformed behavior per owned file
- 2026-06-23T08:25:53Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1524877 – Started review via action command
- 2026-06-23T08:35:26Z – user – shell_pid=1524877 – Moved to planned
- 2026-06-23T08:36:40Z – claude:sonnet:python-pedro:implementer – shell_pid=1557272 – Started implementation via action command
- 2026-06-23T08:41:51Z – claude:sonnet:python-pedro:implementer – shell_pid=1557272 – Cycle 2: support.load_meta now preserves missing→TaskCliError + malformed→raises (behavior-neutral); both arms tested
- 2026-06-23T08:43:35Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1574774 – Started review via action command
- 2026-06-23T08:48:25Z – user – shell_pid=1574774 – Cycle 2 passed: support.load_meta preserves missing→TaskCliError + malformed→raises; both arms tested; no caller relies on the removed {}
