---
work_package_id: WP05
title: target_branch read primitive + thin adapters (fail-closed)
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: fix/reliability-papercut-sweep
merge_target_branch: fix/reliability-papercut-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/reliability-papercut-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reliability-papercut-sweep unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "711198"
history:
- at: '2026-06-30T20:12:14Z'
  actor: claude
  note: WP authored from IC-05; thin-adapter shape (C-005), ~18-20 call sites stable
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/paths.py
create_intent:
- tests/specify_cli/core/test_target_branch_primitive.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/paths.py
- src/specify_cli/core/git_ops.py
- tests/agent/test_orchestrator_merge_target.py
- tests/specify_cli/core/test_target_branch_primitive.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries before proceeding.

## Objective

Collapse `target_branch` resolution onto ONE canonical read primitive that distinguishes a
**field-absent** read (documented default) from a **read failure** (corrupt JSON / I/O → fail
closed, structured error — never a silent fallback to the default branch). Keep the three existing
readers as thin adapters so all ~18–20 call sites are behavior-stable. (FR-005 / #2139)

## Context

- Three readers, all carrying the identical silent fallback (`meta.get("target_branch", fallback)`
  conflating absent-with-failed):
  - `src/specify_cli/core/paths.py` — `get_feature_target_branch` (~:599, returns `str`) and
    `resolve_merge_target_branch` (~:643, returns `tuple[str,str]` with provenance).
  - `src/specify_cli/core/git_ops.py` — `resolve_target_branch` (~:331, returns `BranchResolution`;
    `except (JSONDecodeError, OSError): target = fallback` at ~:388 is the silent-failure path).
- The 2 higher-level resolvers (`orchestrator_api/commands.py:407`, `merge/resolve.py:249`)
  already DELEGATE to the primitives — no separate edit needed.
- ~18–20 genuine call sites across prompt_builder, dossier_pipeline, merge, implement, tasks ×2,
  record_analysis, accept_merge, worktree_topology, commit_router, resolution ×4, workflow, finalize.
- Sibling field-absent readers (`context/resolver.py`, `mission_branch_context.py`, retrospective)
  serve different concerns → OUT of scope (single-primitive follow-up).
- Precedent: **#2065** (merged, surface-resolver single-authority, fail-closed doctrine). Cite it.

## Subtasks

### T019 — Red-first: corrupt-meta fails closed; field-absent defaults  [P]
Add `tests/specify_cli/core/test_target_branch_primitive.py`: (a) meta present but corrupt JSON →
the reader raises a structured error (NOT a silent return of the default branch); (b) meta present,
`target_branch` field absent → returns the documented default. RED on pre-fix code (today both
return the default silently).

### T020 — Create the shared read primitive
In `core/paths.py`, add one canonical primitive that reads `target_branch` from primary meta and
distinguishes: field-absent → documented default; read-failure (JSONDecodeError/OSError) →
structured error (fail closed). This is the single source of the absent-vs-failed decision.

### T021 — Convert the two paths.py readers to thin adapters
Reimplement `get_feature_target_branch` (str) and `resolve_merge_target_branch` (tuple+provenance)
as thin adapters over the primitive — same signatures, same return types, call sites unchanged.

### T022 — Convert resolve_target_branch (git_ops) to a thin adapter
Reimplement `resolve_target_branch` (BranchResolution) over the primitive — **import the
`core/paths.py` primitive rather than keeping git_ops' own `try/except`** (else the absent-vs-failed
decision is duplicated across the two core modules). Replace the `except → fallback` silent path
with the fail-closed behavior; keep the BranchResolution shape.

> **Meta-read consistency (shared with WP04):** the new primitive's `meta.json` read should route
> through the canonical fail-closed meta loader `mission_metadata.load_meta_strict` /
> `load_meta_or_empty` (`mission_metadata.py:354/377`) — the same family WP04 uses — so this mission
> does not ship divergent meta-read corruption handling. Coordinate with WP04 (Lane B).

### T023 — Extend merge-target test + verify call-site stability
Extend `tests/agent/test_orchestrator_merge_target.py` (the real-git seam) with the
fail-closed-on-read-failure assertion. Verify the ~18–20 call sites compile and behave unchanged
(C-005 — this is NOT a bulk rename; signatures are stable). Note the verification scope in the PR.

## Branch Strategy

Planning/base + merge target: `fix/reliability-papercut-sweep`. Worktrees per `lanes.json`.
Run `spec-kitty agent action implement WP05 --agent claude`. Independent (Lane B).

## Definition of Done

- T019 RED pre-fix, GREEN after.
- One primitive owns the absent-vs-read-failure decision; the 3 readers are thin adapters with
  unchanged signatures/return types.
- A read failure surfaces a structured error (no silent default-branch); field-absent still defaults.
- ~18–20 call sites behavior-stable (no churn); the 2 delegating resolvers inherit the fix.
- ruff + mypy clean; complexity ≤ 15.

## Reviewer guidance

Confirm field-absent vs read-failure are genuinely distinguished (not both fail-closed, not both
default). Confirm signatures/return types are byte-identical so the ~18–20 call sites need no edit
(spot-check several). Confirm the `except → fallback` silent path in git_ops is gone. Confirm the
out-of-scope sibling readers were left alone.

## Activity Log

- 2026-06-30T21:22:04Z – claude:sonnet:python-pedro:implementer – shell_pid=590810 – Assigned agent via action command
- 2026-06-30T21:36:06Z – claude:sonnet:python-pedro:implementer – shell_pid=590810 – Ready: primitive + thin adapters, call sites stable, red-first green
- 2026-06-30T21:36:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=652127 – Started review via action command
- 2026-06-30T21:44:47Z – user – shell_pid=652127 – Moved to planned
- 2026-06-30T21:45:51Z – claude:sonnet:python-pedro:implementer – shell_pid=684432 – Started implementation via action command
- 2026-06-30T21:50:17Z – claude:sonnet:python-pedro:implementer – shell_pid=684432 – Cycle 2: re-pinned the 3 malformed-meta tests to fail-closed; field-absent siblings untouched; suite green
- 2026-06-30T21:50:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=711198 – Started review via action command
