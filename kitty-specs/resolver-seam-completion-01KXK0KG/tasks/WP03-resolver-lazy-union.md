---
work_package_id: WP03
title: resolver lazy action-grain union + campsite + gating pins
dependencies:
- WP02
requirement_refs:
- C-001
- C-004
- FR-004
- FR-007
- NFR-001
- NFR-002
tracker_refs:
- '2651'
planning_base_branch: feat/2651-resolver-seam-completion
merge_target_branch: feat/2651-resolver-seam-completion
branch_strategy: Planning artifacts for this mission were generated on feat/2651-resolver-seam-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/2651-resolver-seam-completion unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3059399"
shell_pid_created_at: "1784133789.27"
history:
- at: '2026-07-15T12:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-06/IC-10/IC-12, resolver-core lane — serial after WP02)
agent_profile: python-pedro
authoritative_surface: src/charter/mission_type_profiles.py
create_intent:
- tests/architectural/test_no_parity_scaffold.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/mission_type_profiles.py
- tests/charter/test_resolved_mission_type_context.py
- tests/missions/test_mission_type_profile_resolution.py
- tests/architectural/test_no_parity_scaffold.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [plan.md](../plan.md) §IC-06/§IC-10/§IC-12
+ the Complexity Tracking note, [research.md](../research.md) §R2/R4, and
[ADR 2026-07-14-2](../../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md)
(grain union) + [ADR 2026-07-15-1](../../../docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md)
(NFR-001 lazy driver). **This is the multi-day core and the single owner of `mission_type_profiles.py`.**
It depends on WP02's `src/charter/action_grain.py`. Always `uv run`.

## Objective

Wire the **live** action-grain into `ResolvedGovernance` **lazily** (thunk), retiring `_EMPTY_GRAIN`, so
the FR-013 `CrossGrainDoubleDeclarationError` is a **lazy fast-fail on first `.governance` access** and the
hot `.action_sequence` path triggers **no** `load_action_index` I/O (NFR-001). Then campsite the seam and
pin activation gating byte-identical (C-001). The load-bearing FR-013 enforcer is WP04's gate, not this raise (C-004).

## Context (grounded by post-plan feasibility, python-pedro)

- Governance builds **eagerly** today: `resolve_mission_type_context:452 → _resolve_governance_slot:562 →
  from_grains:590`. The **sole** construction-time force is `:469` `provenance=governance.provenance`.
  **Provenance is already computed independently** at `:588` (`repo.get_provenance(mission_type) or "project"`).
- **Nothing in `src/` reads the `.governance` slot** (verified): `prompt_builder.py:353` reads
  `.governance_text` (a `str`, rendered from the profile via `_render_profile_payload:840` — NOT the union
  object); the hot FSM callers read `.action_sequence`. So `.governance_text` stays eager (single YAML, no I/O)
  and lazy `.governance` has **zero production blast radius**.
- The `UnknownMissionTypeError` **registration** guard (`:583-584`) is registration-based, NOT grain-based —
  it MUST stay eager. Only the `from_grains` union (`:590-594`) + FR-013 raise move lazy.
- `_expected_artifacts_thunk` / `_step_contracts_thunk` (`:334-354`, wired `:474-479`) are the exact pattern to mirror.

### T007 — Make `governance` a lazy `compare=False` thunk
- Add a `_governance_thunk` field + a `@cached_property governance` on `ResolvedMissionType`, mirroring the two
  existing thunks. Make the `governance` field `compare=False` (like them) — `__eq__` then ignores it; the
  determinism asserts (`tests/charter/test_resolved_mission_type_context.py`) still hold (the explicit
  `first.governance == second.governance` line is unaffected).

### T008 — Split `_resolve_governance_slot`; fix the `:469` force
- Change `_resolve_governance_slot` to return `(provenance, governance_text, governance_thunk)` — provenance
  and text computed eagerly (as today, from the profile + `repo.get_provenance`), the `from_grains` union
  deferred into the thunk. Set `provenance=provenance` at `:469` (no longer `governance.provenance`).

### T009 — Wire the live union into the thunk; retire `_EMPTY_GRAIN`
- Inside the thunk, call WP02's `aggregate_action_grain(built_in_dir, mission_type)` and pass it as
  `action_grain=` to `from_grains` (replacing the `_EMPTY_GRAIN` use at `:592`). The FR-013 raise now fires
  on first `.governance` access.
- **CORRECTION (post-task squad):** remove the `_EMPTY_GRAIN` **def** at `:684` and the `:592` use — but `:690`
  is a **LIVE** use: `_profile_type_grain` returns `_EMPTY_GRAIN` when `profile is None` (`:687-690`, reachable).
  Replace `:690` with `return {}` (a fresh empty mapping), do NOT delete the return.
- Fix the now-false `:311` docstring ("populated eagerly on the hot path").
- Fix the now-false `:311` docstring ("populated eagerly on the hot path").

### T010 — Campsite (FR-007)
- **Repoint, don't delete blindly:** `_load_mission_type_profile` (`:769`) has a live test asserting it exists
  (`tests/missions/test_mission_type_profile_resolution.py:74-98`). Remove the production-dead wrapper AND
  update that test (repoint to the real path or delete the now-obsolete assertion).
- Remove the dead `except ImportError → CANONICAL_MISSION_TYPES` fallback (`:388-395`). **Coordinate note:**
  #2657 also touches `existing_mission_types`'s all-built-in default — you remove only the ImportError branch;
  do not touch the default semantics.
- Tighten `expected_artifacts` typing at all **3** sites (`:334` thunk, `:343` property, `:637` resolver) to a
  `TypedDict`/type alias — **NOT** a pydantic model (would cross the charter→doctrine boundary, C-001).
- Fix the `tests/charter/test_resolved_mission_type_context.py:11-12` stale docstring.
- Add `tests/architectural/test_no_parity_scaffold.py`: a glob that fails if any `*parity_scaffold*` artifact
  survives in `src/`/`tests/` (enforces C-003 — the transitional scaffold, if you add one to prove the swap,
  must be deleted before landing).

### T011 — IC-12 regression pins (C-001)
- Pin that `existing_mission_types` / `activated_mission_types` / `.action_sequence` outputs are byte-identical
  pre/post change (they don't read the governance grain). Add/keep a test that a colliding-doctrine resolve now
  fails only on `.governance` access, NOT on `.action_sequence` (the thunk severs the coupling).

## Branch Strategy

Base = WP02's tip; final merge target `feat/2651-resolver-seam-completion`. **This WP is strictly serial after
WP02 and before WP06-equivalent work — it is the sole owner of `mission_type_profiles.py`.**

## Definition of Done

- `_EMPTY_GRAIN` retired; `.governance` is a lazy thunk; hot `.action_sequence` triggers no `load_action_index`.
- FR-013 fast-fail fires on `.governance`; campsite complete; `expected_artifacts` typed at 3 sites; parity guard added.
- Activation-gating outputs byte-identical; full `tests/charter` + `tests/next` green; `ruff` + `mypy --strict` clean.

## Risks / Reviewer guidance

- **Risk:** accidentally moving the `UnknownMissionTypeError` registration guard lazy — keep it eager.
- **Risk:** the `:469` provenance rework re-forcing the object — provenance must come from `:588`, not `.governance`.
- **Reviewer:** grep confirms no new `.governance` reader on the hot path; the spy (WP05) will prove no `load_action_index` on `.action_sequence`; confirm the pydantic-boundary line for typing.

## Activity Log

- 2026-07-15T15:59:29Z – claude:sonnet:python-pedro:implementer – shell_pid=2975764 – Assigned agent via action command
- 2026-07-15T16:42:58Z – claude:sonnet:python-pedro:implementer – shell_pid=2975764 – WP03 done: lazy thunk + _EMPTY_GRAIN retired + campsite + pins; 2652 passed, ruff/mypy clean (ba593907). Edited WP05-owned test_mission_type_governance_isolation.py (coupling); WP05 completes reconciliation.
- 2026-07-15T16:43:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=3059399 – Started review via action command
- 2026-07-15T16:51:57Z – user – shell_pid=3059399 – Review PASS (reviewer-renata:opus): lazy thunk (no eager load_action_index), reg-guard eager, gating byte-identical (C-001), expected_artifacts alias not pydantic, campsite clean; out-of-map WP05-test edit is minimal green-keeping (WP05 T014 intact); 2155 passed, ruff/mypy clean
- 2026-07-15T17:11:09Z – user – shell_pid=3059399 – Done override: Mission merged to feat/2651-resolver-seam-completion (298d0d4)
