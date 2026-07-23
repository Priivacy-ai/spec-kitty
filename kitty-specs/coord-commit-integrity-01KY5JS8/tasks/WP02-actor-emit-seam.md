---
work_package_id: WP02
title: Actor identity on the emit seam
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
planning_base_branch: remediation/coord-trust-2841
merge_target_branch: remediation/coord-trust-2841
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-trust-2841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-trust-2841 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
history:
- at: '2026-07-22T19:33:57Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- tests/status/test_actor_boundary_normalize.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/status/emit.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/status/test_actor_boundary_normalize.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

(Or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`.) Adopt its directives/tactics; state which you applied.

## Objective

Fix the #2861 actor identity on the emit seam: a manually-orchestrated claim records a valid **parsed** actor,
and the SaaS fanout stops rejecting dict actors. Read `research.md` (Decision F), `contracts/gate-and-doctor-contracts.md`
(Actor identity section), `data-model.md` (actor payload). **This is actor correctness + SaaS-fanout fidelity —
it is NOT the commit blocker (WP01/FR-002 is). Do NOT claim it satisfies US2 AC-3 unless WP01's NFR-002 repro
verdict says so.**

## Branch Strategy

Planning base + merge target **`remediation/coord-trust-2841`** (coord). Per `lanes.json` you are in **lane-b**,
WP01 is in **lane-a**, `depends_on_lanes:["lane-a"]` — these are SEPARATE worktrees (correction: NOT "same
worktree"). Your out-of-map edit to `workflow_executor.py` (`:648`/`:1465`, WP01-owned) is nonetheless SAFE
via the **#1684 dependency-tip merge**: `allocate_lane_worktree` (`lanes/worktree_allocator.py:99-159`) merges
WP01's approved lane-a tip (incl. its restructured `workflow_executor.py`) into your lane-b base BEFORE you
edit, so lane-a is an ancestor of lane-b and your actor-seam edit lands on top with no double-application or
merge collision. Record THAT (#1684, not "same worktree") as the out-of-map rationale in your handoff.

## Subtasks

### T006 — FR-005 widen `build_resolved_actor` (no synthetic defaults, no fake binding)

`status/emit.py:~1077` `build_resolved_actor` is currently `(*, role, tool, binding)`. Add self-asserted
`self_profile: str|None = None`, `self_model: str|None = None`. Emit
`profile = binding.agent_profile or self_profile`, `model = binding.model or self_model` — absent stays
`None` (NO synthetic `"unknown-model"`/`"{tool}-default"`). Do NOT synthesize a `ResolvedBinding` from
`--agent` (C-002/C-007 — the `_resolve_dispatch_binding` `--model`-without-`--invocation-id` RAISE stays).
Keep `tests/specify_cli/status/test_resolved_binding_linkage.py` + `test_saas_resolved_binding_fanout.py` green.

### T007 — FR-005 parse `--agent` at the 3 claim seams → bare tool

The live claim path does NO boundary parse today (the whole compact string leaks into `actor.tool`). Parse
`--agent tool:model:profile:role` at the boundary into `(tool, model, profile, role)` (a small helper; do NOT
reuse the frontmatter parser's synthetic-defaulting `_resolve_agent_from_colon_string`) and pass the bare
`tool` + self-asserted profile/model to `build_resolved_actor` at:
- `workflow_executor.py:~648` (`_implement_start_claim`) and `:~1465` (`review_claim_transition`) — **out-of-map
  edits** (WP01 owns this file; you are same-lane-sequential, so this is safe; record the rationale in the handoff);
- `tasks_move_task.py:~1542` (`_mt_emit_transitions`, move-task).
Campsite in `tasks_move_task.py`: extract `_binding_role_for_lane(lane)` (dup role map at `:1533`/`:1623`).

### T008 — FR-006 dict-actor validator (SaaS fanout)

`sync/emitter.py`: widen `WPStatusChanged.actor` (`:434`) and `WPCreated.actor` (`:452`) to accept
`Union[str, Dict]`. Campsite: introduce ONE `_is_actor_field` (nonempty-str OR `_is_actor_payload`) so the
relaxed predicate isn't duplicated twice, and collapse the byte-identical `_is_proof_actor` (`:244`) ↔
`_is_actor_payload` (`:224`) clone. `WPAssigned` has NO actor field — leave it. NOTE in your handoff: this
path warns-and-skips (never raises); the local JSONL append is already dict-safe — so this fixes fidelity, not the block.

## Definition of Done

- [ ] `build_resolved_actor` accepts self-asserted profile/model; absent segments stay `None` (no synthetic defaults); no `ResolvedBinding` synthesized.
- [ ] `--agent` is parsed to a bare `tool` at all 3 seams; the compact string never lands whole in `actor.tool`.
- [ ] `WPStatusChanged`/`WPCreated` accept dict actors via one `_is_actor_field`; `_is_proof_actor`↔`_is_actor_payload` collapsed.
- [ ] Existing `test_resolved_binding_linkage` + `test_saas_resolved_binding_fanout` green; new `test_actor_boundary_normalize.py` covers the parse + no-synthetic-default + dict-accept cases.
- [ ] `uv run --extra test ruff check` + `mypy` clean; complexity ≤15 (do NOT inflate `emit.py:495`/`:789`).
- [ ] **US2 AC-3 defaults to NOT-closed (renata).** Mark AC-3 satisfied ONLY if `test_2861_causation_repro.py` asserts the actor-shape (FR-006) path is the blocking cause. If that assertion says FR-002 (misroute — the expected verdict), the handoff MUST state "AC-3 NOT satisfied by this WP — owned by WP01" and leave #2861 open on this WP.
- [ ] Handoff records the #1684 dependency-tip-merge rationale for the out-of-map `workflow_executor.py` edit (NOT "same worktree").

## Reviewer guidance

Verify: NO synthetic `unknown-model`/`{tool}-default` reaches the actor; NO `ResolvedBinding` is minted from
`--agent`; the validators accept dict but still reject empties; the US2 AC-3 claim is gated on WP01's verdict,
not assumed.

## Risks

- Reusing the frontmatter parser verbatim would fabricate synthetic identity — write a thin boundary parser.
- Over-claiming this unblocks manual review when WP01/FR-002 is the actual fix.
