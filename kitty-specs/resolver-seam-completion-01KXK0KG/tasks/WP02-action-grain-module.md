---
work_package_id: WP02
title: action-grain aggregation module (single canonical union)
dependencies: []
requirement_refs:
- C-002
- FR-005
- NFR-002
tracker_refs:
- '2651'
planning_base_branch: feat/2651-resolver-seam-completion
merge_target_branch: feat/2651-resolver-seam-completion
branch_strategy: Planning artifacts for this mission were generated on feat/2651-resolver-seam-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/2651-resolver-seam-completion unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2962569"
shell_pid_created_at: "1784130798.85"
history:
- at: '2026-07-15T12:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-07 + IC-11 spike, resolver-helper lane)
agent_profile: python-pedro
authoritative_surface: src/charter/action_grain.py
create_intent:
- src/charter/action_grain.py
- tests/charter/test_action_grain.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/action_grain.py
- tests/charter/test_action_grain.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [plan.md](../plan.md) §IC-07 (+ the
"single-source" rationale in §IC-04/IC-08), [research.md](../research.md) §R4/R5, and
[data-model.md](../data-model.md) (the `ActionIndex→Mapping` adapter + root-authority row). The
ADR/plan are the authority. Always `uv run`.

## Objective

Create **one** canonical, pure, tested module that computes a mission type's action-grain union —
`src/charter/action_grain.py`. This is the **foundational** WP: the resolver (WP03), the integrity gate
(WP04), and the reconciled tests (WP05) all import it, so the type⊕action reduction lives in exactly
one place (C-002 / kills the second-source the two enduring tests currently duplicate). This lane owns
a **new file only** and runs in parallel with WP01.

## Context (grounded by post-plan feasibility)

- `load_action_index(missions_root, mission, action) -> ActionIndex` (`src/doctrine/missions/action_index.py:26`)
  is **per-(mission, action)** and returns an `ActionIndex` dataclass (`action_index.py:12-23`) with 7
  fields: `directives / tactics / paradigms / styleguides / toolguides / procedures / agent_profiles`.
  These map **1:1** to `charter.mission_type_profiles._GOVERNANCE_KINDS` (`:100-108`).
- `load_action_index` returns an **empty** `ActionIndex` on missing/corrupt YAML (`action_index.py:42-43,67-68`)
  — so a real load must be asserted non-empty by consumers (WP04 relies on this).
- **Root authority:** the correct `missions_root` is `MissionTypeProfileRepository._default_built_in_dir()`
  (`src/charter/mission_type_profile_repository.py:94-102`) = `src/doctrine/missions`. It is **NOT** the
  resolver's `repo_root`. **SCOPE CAP:** builtin root only; project/org action-index overlay symmetry is a
  tracked follow-up (no project `actions/` override layout exists today) — do NOT build a multi-root/field-merge engine.
- `charter` MUST NOT import `specify_cli` (C-001 layer rule); importing from `doctrine` is fine.

**Circular-import guard (post-task squad):** `action_grain.py` needs `_GOVERNANCE_KINDS` (and T006 needs the
type-grain helper) — both in `mission_type_profiles.py`, which will import `aggregate_action_grain` back.
Keep `action_grain.py` **free of module-level `charter.mission_type_profiles` imports** — import
`_GOVERNANCE_KINDS` / the type-grain reader **lazily** inside the functions (the module already uses the
`# noqa: PLC0415` lazy-import convention). Do NOT re-declare the 7 kind keys (that duplicates a governance-kind list — C-002 smell).

### T004 — `action_index_to_mapping` pure adapter
- Add `action_index_to_mapping(index: ActionIndex) -> dict[str, list[str]]` projecting the 7 `ActionIndex`
  fields onto the `_GOVERNANCE_KINDS` keys (same key names). Pure, no I/O.
- Test round-trips: a populated `ActionIndex` → the expected mapping; an empty one → all-empty lists.

### T005 — `aggregate_action_grain(built_in_dir, mission_type)`
- Enumerate `<built_in_dir>/<mission_type>/actions/*/index.yaml`, `load_action_index` each, and union the
  per-action mappings into one `dict[str, list[str]]` per kind (concatenate; **de-dup is the caller's
  `from_grains._merge_disjoint_grain` job** — do not pre-dedup in a way that hides collisions).
- **NOTE (post-task squad):** all 4 built-in types HAVE an `actions/` dir. `plan`'s indexes are intentionally
  **empty-content** (lists `[]`), so `plan` aggregates to an **empty** mapping — that is empty *content*, NOT a
  missing dir. If you keep a defensive "missing `actions/` dir → empty" branch, it is **not** exercised by any
  real built-in type, so add a **synthetic temp-dir fixture** to cover it (NFR-002: every branch tested).
- Tests (real fixtures, `uv run`): `software-dev` yields a non-empty union; `plan` yields empty-content;
  the returned keys are exactly `_GOVERNANCE_KINDS`.

### T006 — IC-11 dup-scan helper (feeds WP04)
- Add a reusable **function in `action_grain.py`** (production, NOT a test module — WP04 imports it) that, for
  all 4 shipped types, unions the type-grain (`governance-profile.yaml selected_*`, read via a lazy import of
  the type-grain helper) with `aggregate_action_grain` and asserts **no cross-grain URN duplicate** —
  confirming the empirically-clean state before WP03 flips `_EMPTY_GRAIN`. Single scanner only (C-002).

## Branch Strategy

Base and merge target both `feat/2651-resolver-seam-completion`; land on the merge target via the lane worktree.

## Definition of Done

- `src/charter/action_grain.py` exposes `action_index_to_mapping` + `aggregate_action_grain` (builtin-root, pure/tested).
- Unit tests cover the adapter, the aggregation (populated + empty type), and the dup-scan helper.
- No import of `specify_cli`; `ruff` + `mypy --strict` clean. This module is the **only** home of the union logic.

## Risks / Reviewer guidance

- **Risk:** threading `repo_root` instead of the builtin missions dir → silent empty grains. Use `_default_built_in_dir()`.
- **Risk:** building overlay/multi-root plumbing — OUT of scope; cap to builtin root.
- **Reviewer:** confirm the module is pure + importable by both `charter` and test tiers; confirm it's the single union authority (WP04/WP05 will import it, not re-implement).

## Activity Log

- 2026-07-15T15:45:23Z – claude:sonnet:python-pedro:implementer – shell_pid=2940502 – Assigned agent via action command
- 2026-07-15T15:52:55Z – claude:sonnet:python-pedro:implementer – shell_pid=2940502 – WP02 done: action_grain.py single-union module; 9 tests pass, ruff/mypy clean, layer-rules OK (13929e231)
- 2026-07-15T15:53:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=2962569 – Started review via action command
- 2026-07-15T15:58:55Z – user – shell_pid=2962569 – Review PASS (reviewer-renata:opus): 9 AC verified, single union authority (C-002)
- 2026-07-15T17:11:01Z – user – shell_pid=2962569 – Done override: Mission merged to feat/2651-resolver-seam-completion (298d0d4)
