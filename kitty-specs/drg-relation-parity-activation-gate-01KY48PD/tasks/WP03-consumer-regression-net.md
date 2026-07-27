---
work_package_id: WP03
title: Five-consumer regression net
dependencies:
- WP01
requirement_refs:
- NFR-002
- NFR-004
planning_base_branch: doctrine/drg-completeness-2843
merge_target_branch: doctrine/drg-completeness-2843
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-completeness-2843. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-completeness-2843 unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
history:
- timestamp: '2026-07-22T08:11:16Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/charter/
create_intent:
- tests/charter/test_activation_consumers.py
- tests/specify_cli/mission_step_contracts/test_executor_activation.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/charter/test_activation_consumers.py
- tests/specify_cli/mission_step_contracts/test_executor_activation.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `python-pedro` implementer profile via the
`/ad-hoc-profile-load` skill. TDD-first, type-safe, complexity ≤15, zero suppressions. Tests here
must assert **named observables**, never smoke ("doesn't crash") — reject fakeable assertions.

## Objective

Prove the WP01-corrected gate does not regress any of the five `filter_graph_by_activation`
consumers (NFR-002). Each consumer gets a before/after test: with `activated_directives` **`None`**
(the production shape) the output is **byte-identical to merge-base**; with a **populated** stem list
the consumer emits the **corrected** per-ID result (the whole point of the fix — do NOT assert
equality with the buggy baseline).

Read: `contracts/activation-gate-contract.md` ("Consumer observables"), `plan.md` IC-03. The five
consumers: `mission_step_contracts/executor.py:182`, `charter/reference_resolver.py:67`,
`charter/compiler.py:1037` (closure), `charter/consistency_check.py::_check_drg_cross_kind_refs`
(`:424`), `charter/context.py:928`.

## Subtasks

Each of T009–T013 adds one consumer's before/after test with a **named observable** — the specific
retained nodes / resolved references / report field that consumer produces. Place the executor test in
`tests/specify_cli/mission_step_contracts/test_executor_activation.py`; the four charter consumers in
`tests/charter/test_activation_consumers.py`.

- **T009 `executor.py:182`**: observable = the mission-step contract set resolved under a populated
  `activated_directives`; `None`-path identical to merge-base.
- **T010 `reference_resolver.py:67`**: observable = the resolved reference graph's directive nodes.
- **T011 `compiler.py:1037` closure**: observable = the closure-filtered graph membership (distinct
  from the `:88` `references.yaml` projection, which is NOT under test here).
- **T012 `_check_drg_cross_kind_refs:424`**: observable = the cross-kind-ref verdict / verification
  entries under a populated list.
- **T013 `context.py:928`**: observable = the resolved context's activated directive set.

For each consumer, the two assertions must be **non-fakeable in a single checkout** (do NOT snapshot
the current run and call it "merge-base"):
- **`None`-path → structural identity, not a hand-typed literal.** With `activated_directives=None`
  the gate is full passthrough (`drg.py:315-318`: `per_kind_set is None` ⇒ identity), so assert the
  consumer's output over `None` equals its output over an unfiltered graph — e.g.
  `set(filtered.nodes) == set(input.nodes)` at the gate, or the consumer's observable computed with no
  activation == with `None` activation. This needs no merge-base and cannot be self-fulfilling.
- **`populated`-path → demonstrably RED on merge-base.** Pick a stem whose directive node is **actually
  dropped by the unfixed gate** (verify: run the assertion on merge-base and see it FAIL). Assert the
  named directive node is **retained** in the consumer's observable. A stem whose node happens to
  survive on merge-base yields a test that passes on the buggy gate = a fake — reject it. Use
  production-shaped stems from the real corpus, not `id==stem` fixtures.

Build fixtures **inline** (as existing charter tests do); do NOT add shared fixtures to
`tests/charter/conftest.py` (unowned, shared with WP01/WP02 lanes — co-writing it is a collision).

### T014 — Whole-suite green (WP03)

Run `uv run pytest tests/charter/ tests/doctrine/ -q` and confirm **0 net failures vs the merge-base**
(classify any red per the baseline-red gotcha — pre-existing P0 reds like #1834 are not yours).
`uv run ruff check tests/charter tests/specify_cli/mission_step_contracts` clean.

## Branch Strategy

Generated on **`doctrine/drg-completeness-2843`**; merges back into it. Worktrees per lane from
`lanes.json`. Depends on WP01. (Soft interaction with WP02 for the `_check_graph_kind_parity`
consumer — if implemented before WP02 lands, characterize the gate consumer `_check_drg_cross_kind_refs`
only; the parity re-point is WP02's own test surface.)

## Definition of Done

- [ ] Five before/after tests, each asserting a **named observable** (not smoke).
- [ ] `None`-path uses a **structural identity** assertion (no merge-base literal); populated-path is
  **demonstrably RED on merge-base** (the named directive node is dropped by the unfixed gate) and GREEN after.
- [ ] Full `tests/charter/` + `tests/doctrine/` green — 0 net failures vs merge-base; ruff clean.

## Risks

- A non-discriminating fixture (where corrected == buggy) proves nothing — pick stems where the
  directive is actually dropped on merge-base. This is the anti-laziness crux (renata's HIGH).

## Reviewer Guidance (reviewer-renata / opus)

For each consumer test, confirm the assertion names a concrete observable and that the populated-path
expectation differs from the merge-base (buggy) output — a test that would pass on the unfixed gate is
a fake.
