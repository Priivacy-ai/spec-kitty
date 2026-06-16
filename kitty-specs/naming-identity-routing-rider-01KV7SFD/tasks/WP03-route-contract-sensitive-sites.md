---
work_package_id: WP03
title: Route the contract-sensitive mid8 sites
dependencies: []
requirement_refs:
- FR-001
- FR-003
- FR-008
- FR-009
tracker_refs: []
planning_base_branch: feat/naming-rider-3-2-1
merge_target_branch: feat/naming-rider-3-2-1
branch_strategy: Planning artifacts for this mission were generated on feat/naming-rider-3-2-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/naming-rider-3-2-1 unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1918055"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/test_mid8_contract_sensitive_routing.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/aggregate.py
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/lanes/worktree_allocator.py
- tests/specify_cli/test_mid8_contract_sensitive_routing.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read `spec.md` (FR-008 contract table), `plan.md` (IC-02), `research.md`, and
`scope-review/pedro-refute-already-done.md` (the byte-parity landmine analysis).

## Objective

Route the **4 byte-parity-landmine sites** through the failover-aware `resolve_mid8` (NOT bare `_mid8`),
**preserving each site's exact `""`/`None`/short-id contract**, then delete the inline shadows. Depends on
WP01 (the public door is `resolve_mid8`). **TDD-first: characterization tests before each change.**

## Context — two seam contracts (the whole point of this WP)

`_mid8()` **raises** on short/None; `resolve_mid8()` **declines → `""`**. Naive "delete the slice, call
`_mid8`" breaks byte-parity at these sites. Per `scope-review/pedro-refute-already-done.md`:

| Site | Current contract | Route to |
|------|------------------|----------|
| `status/aggregate.py:250` | `mid8 = mission_id[:8] if mission_id else ""` | `resolve_mid8(slug, mission_id=mission_id)` (returns `""` when absent) |
| `dashboard/scanner.py:438` | returns `None` (not `""`), short-circuits pseudo keys | `resolve_mid8(...) or None` (preserve `mid8 is None` registry contract) |
| `doctor.py:3070` & `:3162` | already `try/except ValueError: mission_id[:8]` | **conscious decision** (T007) |
| `implement.py:386` | prefers `meta["mid8"]` then guarded slice, returns `None` | preserve `meta["mid8"]` preference, then `resolve_mid8(...) or None` |

## Subtasks

### T009 — Characterization tests FIRST (TDD)
Create `tests/specify_cli/test_mid8_contract_sensitive_routing.py` pinning the **current** output of all
four sites across: full id, missing/None id, short id, pseudo key (scanner). These must pass before AND
after routing — they are the byte-parity proof (NFR-001).

### T005 — `status/aggregate.py:250`
Replace the inline `mission_id[:8] if mission_id else ""` with `resolve_mid8(<slug>, mission_id=mission_id)`.
Confirm the empty-string contract is preserved (resolve_mid8 declines to `""`).

### T006 — `dashboard/scanner.py:438`
Replace with `resolve_mid8(<slug>, mission_id=mission_id) or None`, preserving the `is_pseudo` short-circuit
and the `mid8 is None` registry contract. This is the dashboard consumer (#2007-adjacent surface) — be
precise about `None` vs `""`.

### T007 — `doctor.py:3070` and `:3162` (conscious decision)
These already wrap `_mid8()` (was `mid8()`) in `try/except ValueError: mission_id[:8]` — a deliberate
short-id tolerance. Routing to `resolve_mid8` makes the `except` dead (resolve_mid8 doesn't raise).
**Decision:** route to `resolve_mid8` and remove the now-dead `try/except`, preserving the tolerant
output (short ids → resolve_mid8 declines → keep the existing fallback display value). Document the
behavior decision in a code comment + the WP handoff note.

### T008 — `implement.py:386`
Preserve the `meta["mid8"]` preference, then fall back to `resolve_mid8(...) or None` (NOT `mission_id[:8]`).

### T010 — Delete shadows + verification-by-deletion
Remove the inline derivations at all four sites. Run the full suite (incl. T009 characterization tests) —
green proves the seam is the only path for these sites.

## ⚠️ Post-tasks remediation (binding — see tasks-review/POST-TASKS-SYNTHESIS.md)

- **Lands BEFORE WP01.** Route to `resolve_mid8`, which **already exists and is public** — do not wait for
  or reference `_mid8` (that rename is WP01, later).
- **NEW site — `src/specify_cli/lanes/worktree_allocator.py` (the F-1 build-breaker, now owned here):**
  route `:169` (`short_id = mid8(lanes_manifest.mission_id)`) through `resolve_mid8`, preserving the
  "when we have a mid8" behavior, **and remove `mid8` from the import at `:28`** (`from
  …branch_naming import lane_branch_name, mid8, worktree_path as _worktree_path`). This module builds
  every lane worktree — if its `mid8` import survives WP01's de-export, the whole package fails to import.
- **T007 expanded:** `doctor.py:3066` and `:3158` already do `from …branch_naming import mid8 as _mid8` —
  repoint **both import lines** to `resolve_mid8` (and route the call sites), so WP01's de-export doesn't
  break the import. Keep the short-id tolerance behavior and add a test proving it survived the dead-`except`
  removal.
- **Byte-parity (anti-gaming):** the T009 characterization tests assert against **literals captured from
  HEAD before any edit** (hard-coded `""`/`None`/string RHS) — never a re-call of `resolve_mid8`.

## Branch Strategy
Base/merge target: `feat/naming-rider-3-2-1`. Worktree allocated from `lanes.json`.

## Definition of Done
- [ ] Characterization tests written first and green before & after (byte-parity).
- [ ] All 4 sites consume `resolve_mid8` (with `or None` where the contract is `None`); zero inline slices remain.
- [ ] `doctor.py` dead `try/except` removed with the decision documented.
- [ ] Full suite green with shadows deleted (verification-by-deletion).
- [ ] `ruff`/`mypy` clean on diff; complexity ≤ 15; no suppressions.

## Risks / reviewer guidance
- **Reviewer:** verify the `None` vs `""` contracts are exactly preserved (the dashboard registry and
  aggregate both matter); confirm characterization tests assert the value, not the internal call.
- Do NOT edit the ratchet test (`test_no_worktree_name_guess.py`) — WP02 owns it and lands after you.

## Activity Log

- 2026-06-16T12:19:15Z – claude:opus:python-pedro:implementer – shell_pid=1865387 – Assigned agent via action command
- 2026-06-16T12:19:43Z – claude:opus:python-pedro:implementer – shell_pid=1866620 – Assigned agent via action command
- 2026-06-16T12:21:11Z – claude:opus:python-pedro:implementer – shell_pid=1868945 – Assigned agent via action command
- 2026-06-16T12:30:44Z – claude:opus:python-pedro:implementer – shell_pid=1868945 – Routed 4 landmines + worktree_allocator F-1 fix + doctor import repoint; characterization tests (HEAD literals) green before/after; verification-by-deletion clean; ruff+mypy clean.
- 2026-06-16T12:31:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=1918055 – Started review via action command
- 2026-06-16T12:37:20Z – user – shell_pid=1918055 – Review passed: 5 sites routed contract-faithfully (aggregate '', scanner None+pseudo short-circuit, doctor short-id tolerance via or mission_id[:8], implement meta[mid8]-pref+None); F-1 worktree_allocator import now resolve_mid8 (no bare mid8) + call fixed, package imports clean; doctor imports repointed, dead try/except removed; 22 HEAD-literal tests (non-gameable) + deletion-guard PROVEN red-before/green-after; 105 consuming-module regression tests pass; mypy 3 errors confirmed pre-existing on base (none at routed lines); ruff clean; scope=6 owned files, branch_naming(WP01)+ratchet(WP02) untouched. FLAG for WP02: doctor.py retains deliberate 'or mission_id[:8]' short-id tolerance fallback (2 sites) — allow-list in ratchet, it is conscious tolerance not a missed route.
