---
work_package_id: WP04
title: Canonical fail-closed mission-identity contract
dependencies: []
requirement_refs:
- FR-004
- FR-006
tracker_refs: []
planning_base_branch: fix/reliability-papercut-sweep
merge_target_branch: fix/reliability-papercut-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/reliability-papercut-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reliability-papercut-sweep unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T031
- T032
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "732107"
history:
- at: '2026-06-30T20:12:14Z'
  actor: claude
  note: WP authored from merged IC-04+IC-06 (one identity contract; post-plan squad)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/events/decision_log.py
create_intent:
- tests/runtime/test_runtime_bridge_identity.py
execution_mode: code_change
owned_files:
- src/specify_cli/events/decision_log.py
- src/specify_cli/review/prompt_metadata.py
- src/runtime/next/runtime_bridge.py
- src/specify_cli/lanes/compute.py
- src/specify_cli/merge/executor.py
- src/specify_cli/coordination/status_transition.py
- tests/specify_cli/events/test_decision_log.py
- tests/runtime/test_runtime_bridge_identity.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries before proceeding.

## Objective

Establish ONE canonical, fail-closed mission-identity contract: `mission_id` persisted anywhere
is always a ULID (never a slug); an absent ULID fails closed; the coordination-branch identity is
minted once at the canonical boundary (no empty-mid8). This WP merges the two contract-coupled
concerns #2138 and #2091 — they share `runtime_bridge.py` and the same slug-sentinel idiom, so
splitting them would recreate the define-here/consume-there split this mission fights.
(FR-004 + FR-006 / #2138 + #2091)

## Context

- `src/specify_cli/events/decision_log.py:98` — `self._mission_id = mission_id or mission_slug`
  (fallback site #1).
- `src/runtime/next/runtime_bridge.py` — `_resolve_mission_ulid` ends `return mission_slug`
  (~:153); line ~:224 `mission_id if mission_id != mission_slug else None` **encodes the
  slug-as-sentinel contract** this WP removes; the mint boundary (`_wrap_with_decision_git_log`,
  ~:215) calls `_resolve_mission_ulid`. The coord-routing path already fails closed
  (`DecisionGitLogUnavailable`, ~:234) — **the leak is flat/coord-less only**.
- `src/specify_cli/review/prompt_metadata.py:149` — `mission_id=str(mission_id or mission_slug)`
  (fallback site #3, found by the post-plan squad).
- `tests/specify_cli/events/test_decision_log.py` — `test_slug_fallback_when_no_mission_id` (~:464)
  asserts the bug as correct; a correct sibling (`mission_id == ulid`) coexists at ~:459.
- **Canonical identity SSOT to CONSUME (do not hand-roll a 4th meta read):**
  `mission_metadata.resolve_mission_identity(feature_dir) -> MissionIdentity` (`mission_metadata.py:223`;
  `MissionIdentity.mission_id` is `None`-when-absent → fail-closed-ready). `runtime_bridge._resolve_mission_ulid`
  currently hand-rolls `json.loads(meta)/meta.get("mission_id")` with `except: meta={}` (silently
  swallows corruption — the same anti-pattern WP05 removes). Route it through `resolve_mission_identity`.
- **ALL slug→mission_id sites (fold every one — operator decision):** `events/decision_log.py:98`;
  `review/prompt_metadata.py:149`; `runtime/next/runtime_bridge.py:153/:224`; **`lanes/compute.py:313`**
  (`resolved_mission_id = mission_id or mission_slug` → persists slug into `LanesManifest.mission_id`)
  **+ `:673`** (same slug-sentinel idiom); **`merge/executor.py:1020/1032`** + **`coordination/status_transition.py:389`**
  (legacy-commented but same field — bring under the fail-closed contract). FR-004 says `mission_id`
  persisted ANYWHERE is a ULID — the lanes manifest site is a live violation.
- Precedent: **#2136** (closed, canonical handle at resolve entry); mid8/branch composition
  fails closed via `BranchIdentityUnresolved`. Sibling identity work: #2091, #1868-WS2.

## Subtasks

### T014 — Red-first: flat-path persists ULID; empty-mid8 fails closed  [P]
Add `tests/runtime/test_runtime_bridge_identity.py`: (a) a flat/coord-less mission with a ULID in
meta but no explicit `mission_id` arg → the persisted decision-event `mission_id` is that ULID,
NOT the slug; (b) a composition with no resolvable mid8 → fails closed (no empty-mid8 branch).
RED on pre-fix code via the real entry point.

### T015 — INVERT the stale slug test
Rewrite `test_slug_fallback_when_no_mission_id` to assert the corrected contract (ULID persisted,
or fail-closed when none available) — it must no longer certify slug-as-`mission_id`. Keep the
correct sibling at ~:459. (C-003)

### T016 — decision_log.py:98 — fail closed
Remove the `or mission_slug` fallback; require a ULID. If absent, fail closed with a structured
error rather than substituting the slug.

### T017 — runtime_bridge — delegate to the identity SSOT; empty-mid8 guard
Make `_resolve_mission_ulid` source the ULID via `mission_metadata.resolve_mission_identity(feature_dir).mission_id`
(fail closed when `None`; mint once at the canonical boundary only when legitimately absent) instead
of the hand-rolled `json.loads`/`return mission_slug`; rewrite the `:224` slug-sentinel idiom
accordingly; ensure the mint-once boundary never emits an empty mid8 (fail closed). Do NOT regress
the coord path that already fails closed correctly. (Consider converging the sibling inline readers
`_default_coord_branch`/`_resolve_mission_id_for_terminus` onto the same SSOT.)

### T018 — prompt_metadata.py:149 — remove slug-into-mission_id
Apply the same contract: never write a slug into the `mission_id` field; source the ULID via the
SSOT or fail closed.

### T031 — lanes/compute.py — collapse the duplicated slug-sentinel
`lanes/compute.py:313` (`resolved_mission_id = mission_id or mission_slug`) persists a slug into
`LanesManifest.mission_id`, and `:673` repeats the `mission_id if mission_id != mission_slug else None`
idiom. Source the ULID via the identity SSOT / fail closed; remove the duplicated sentinel so the
lanes manifest never carries a slug as `mission_id` (FR-004).

### T032 — merge/executor.py + status_transition.py — bring legacy sites under the contract
`merge/executor.py:1020/1032` and `coordination/status_transition.py:389` carry legacy-commented
`or mission_slug` / `legacy-{slug}` writes into a `mission_id` field. Bring each under the
fail-closed contract (source a ULID or fail closed); where a legacy on-disk artifact genuinely has
no ULID, handle it explicitly (documented), not via a silent slug substitution.

## Branch Strategy

Planning/base + merge target: `fix/reliability-papercut-sweep`. Worktrees per `lanes.json`.
Run `spec-kitty agent action implement WP04 --agent claude`. Independent (Lane B).

## Definition of Done

- T014 RED pre-fix, GREEN after; inverted slug test green.
- No code path persists a slug into a `mission_id` field (decision_log, runtime_bridge,
  prompt_metadata, lanes/compute, merge/executor, status_transition) — verified by grep.
- ULID sourcing routes through `mission_metadata.resolve_mission_identity` (no new hand-rolled meta read).
- Flat path sources a real ULID (meta/mint); absent ULID fails closed; empty-mid8 impossible.
- Coord path behavior unchanged (already fail-closed).
- ruff + mypy clean; complexity ≤ 15.

## Reviewer guidance

Confirm the fix SOURCES a ULID on the flat path (not merely deletes the fallback — that would break
flat missions with a legitimate ULID via legacy callers). Confirm `:224` slug-sentinel is gone and
nothing downstream still relies on `mission_id == slug` to mean "no ULID". Confirm the inverted
test genuinely asserts the new contract. Verify empty-mid8 is unreachable.

## Activity Log

- 2026-06-30T21:21:57Z – claude:sonnet:python-pedro:implementer – shell_pid=590810 – Assigned agent via action command
- 2026-06-30T21:54:06Z – claude:sonnet:python-pedro:implementer – shell_pid=590810 – Ready: all slug-as-mission_id sites fail-closed via SSOT (resolve_mission_identity), stale test inverted (T015), mandatory grep clean, 9 files changed, commit d17d064da
- 2026-06-30T21:56:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=732107 – Started review via action command
