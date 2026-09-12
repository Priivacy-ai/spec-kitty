# Contract: inverted transition-gate hook

**Traces**: FR-004, FR-007, FR-008, FR-009, FR-013, FR-014, NFR-001, NFR-002, NFR-005, C-003
**Home**: `_mt_run_transition_gates(st)` — generalizes `_mt_run_pre_review_gate`
(`tasks_move_task.py:1160`), same `_do_move_task` slot.

The hook inverts the relationship: instead of a hardcoded call to
`evaluate_pre_review_gate`, it resolves **which** named handlers the repo's active doctrine binds
to the current lane edge, dispatches each with per-handler fail-open, and aggregates to a verdict.

## Behavioural pipeline

```
_mt_run_transition_gates(st):
  edge = (st.from_lane -> st.target_lane)                # e.g. in_progress->for_review
  mission = resolve_mission_type(st.mission_slug -> meta.json)   # FR-008 mission-type axis
  action = map_edge_to_owning_action(edge)               # FR-008 table (review action)
  pack = PackContext.from_config(repo_root)              # fail-CLOSED on env/escape (executor.py:275)
  graph = filter_graph_by_activation(load_validated_graph(repo_root), pack)   # NFR-005: 1 load
  contract = get_by_action(mission, action)               # review contract (+ owning URN)
                                                            # no contract / no for_review binding
                                                            #   -> distinguishable NO_COVERAGE warn
  active = resolve_active_gate_bindings(activated_msc_urns,                   # PURE fn
             owning_contract_urn=contract.urn, bindings=contract.gates, edge_key=edge_key(edge))
             #  retain iff on_transition == edge_key AND owning_contract_urn in activated_msc_urns
  verdicts = []
  for b in stable_sort(active, key=(decl_index, handler)):                    # FR-008 order
      try:
          verdicts.append(get_gate_handler(b.handler).run(ctx))              # FR-004 dispatch (dict lookup)
      except KeyboardInterrupt:
          verdicts.append(cancelled_verdict())                               # terminal (C-003 #2)
      except Exception:                                                       # FR-013 fail-open
          verdicts.append(unverified_warn_verdict(b.handler))                # NO_COVERAGE warn
  aggregate_verdicts(verdicts, block_enabled=..., force=st.force)             # PURE fn — FR-014 / §7
```

## Resolution invariants (FR-007, NFR-003, NFR-005)

- **Named loader is mandatory** — the DRG carries no binding payload (`drg/models.py:292-311`);
  `load_gate_bindings(repo_root, mission, action)` reads the review contract's `gates` via
  `MissionStepContractRepository.get_by_action(mission, action)` (`step_contracts.py:160`), the
  runtime-wired surface the executor already uses. The `mission` axis is resolved from
  `st.mission_slug` → `meta.json`; a `(mission, review)` with no contract or no `for_review`
  binding → a **distinguishable** `NO_COVERAGE` warn (worded separately from "handler not
  activated"), never a silent vanish (FR-008, FR-012).
- **Aggregation is a pure function** — `aggregate_verdicts(verdicts, *, block_enabled, force)` and
  `resolve_active_gate_bindings(...)` are standalone pure functions with their own outcome ×
  precedence unit tests; the hook only orchestrates (complexity ≤ 15, NFR-006). The multi-handler
  paths are a seam exercised by **synthetic handlers in tests only** — half A ships one real
  binding.
- **Bounded cost** — one graph load + one filter + one contract-bindings load per transition;
  survivors by set-membership, **no per-node re-resolution** (NFR-005).
- **Activation keys on the owning-contract URN, NOT the handler** — the retain predicate is
  `owning_contract_urn ∈ activated_msc_urns` (canonical `mission_step_contract:<mission-type>/<id>`,
  `drg.py:271`). The handler is a `GATE_REGISTRY` name resolved by dict lookup, never a DRG
  candidate — gating on it would return `None` from `_candidate_urn` and empty `active` permanently
  (a decorative gate).
- **Non-vacuous** — a binding on a contract whose URN is not activated is absent from `active` and
  detectable (negative control: contract-URN activated → fires; deactivated → does not), never
  silently invisible, and not greenable by a self-fulfilling mock (NFR-003).
- **Fail-CLOSED on pack-context misconfig** — an unset org-pack env var or subdir escape raises
  (copied `_resolve_pack_context` semantics, `executor.py:275-280`); this is distinct from the
  fail-**open** handler-execution rule.

## Dispatch + aggregation invariants (FR-013, FR-014, C-003)

- **Fail-open per handler** — every handler *execution* error degrades to exactly one visible
  "unverified" `NO_COVERAGE` warn; `KeyboardInterrupt` maps to the terminal `CANCELLED`
  (mirrors the incumbent three-catch, `tasks_move_task.py:1241/1248`).
- **Deterministic aggregation precedence** (highest first): terminal interruption
  (`TIMED_OUT`/`CANCELLED` → `transition_applied=False`, `Exit(1)`) > block (`block_enabled AND
  any NEW_FAILURES AND not force` → `Exit(1)`) > warn/pass. Terminal is checked before the block,
  preserving the incumbent order (`:1285` before `:1298`).
- **≤1 warning per handler**; **no cross-suppression** — a faulting handler never removes another
  handler's `NEW_FAILURES` from the block computation (US4 AS3).
- **Two hard-stops only** (C-003) — no new hard-stop may be introduced.

## CLI-observable invariants

1. **Spec-Kitty behaviour unchanged** (NFR-001, SC-002). On the Spec-Kitty repo, the refactored
   hook produces identical `(outcome, scope, transition metadata, block/exit, console)` to the
   pre-refactor path across all six `GateOutcome` members and both hard-stops — proven **through**
   `_mt_run_transition_gates` by a golden comparison, not against the engine in isolation.
   **Oracle provenance (anti-circular).** The golden's expected tuples MUST be captured from base
   commit `e4ef6e850` against the **incumbent** `_mt_run_pre_review_gate` **before** the refactor —
   a committed fixture, authored **red-first against the OLD function**. The oracle is NEVER
   regenerated from the new code (a self-referential oracle would prove nothing). The parity test
   is red until the refactored hook reproduces the base-captured tuples.
2. **Consumer never imports `_gate_coverage`** (FR-009, SC-001) — even under **erroneous
   activation** of the Spec-Kitty handler. When the handler is not activated, the import is
   structurally unreachable; when it is (erroneously) activated but the module is absent, the
   handler's own `GateAuthoritiesUnavailable` degrades to a `NO_COVERAGE` warn — the internal
   module import never succeeds.
3. **No gate bindings ⇒ no gate** — a repo whose active doctrine binds nothing to the edge
   transitions with no gate and no internal-path reference (US1 AS3).
4. **Doctrine toggle, no Python edit** (US3, SC-003) — activating/deactivating the binding's
   handler in doctrine flips whether the gate fires, with no code change between states.

## What the hook does NOT change

- FSM edge adjacency and the pre-existing move-task guard sequence (`tasks_transition_core.py`
  `_GUARDS`) — the hook remains purely additive, after the guard sequence, before emit
  (`_mt_run_pre_review_gate` docstring, `tasks_move_task.py:1163-1169`).
- The changed-files SSOT (`_mt_pre_review_changed_files`, `:927`) — reused, not re-derived.
- `StepContractExecutor.execute()` is **mirrored, not called** (D-09) — the executor resolves
  action-step delegations, a different call path.
