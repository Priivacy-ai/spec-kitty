# Tracer: Design Decisions — `dispatch-dry-run-route-only-01M1HKV2`

Seeded at planning (2026-09-02). These restate the operator's binding decisions from spec.md's
"Clarifications / Decision Records" section so implementers don't have to re-derive them from
spec.md while heads-down in a WP. **spec.md remains the authority; this file is a convenience
index, not a second source of truth.** Do not re-litigate any of these during implementation.

## Decision 1: SK-08 rerank ships as WP3, landing after WP1/WP2

The additive, lower-risk dry-run + `alternatives` work (WP1/WP2) must not stall on the riskier
behavioral fix to `ActionRouter.route()`'s selection logic (WP3/SK-08), because that fix changes
selection behavior on every real (Op-opening) dispatch call, not just the new dry-run path. WP3
lands as its own commit, distinct from WP1/WP2's commits — but it is NOT guaranteed to be a
conflict-free independent `git revert <wp3-sha>` target, since WP2 and WP3 both edit the single-
candidate return and the `routing_priority` tiebreaker block inside `route()` (spec.md C-002).
The achievable property is "own commit, auditable and cherry-pickable in isolation," not
"independently, cleanly revertible regardless of WP2."

## Decision 2: `alternatives` ships in v1, on both dry-run and real dispatch

Not deferred, not restricted to dry-run-only. The router already computes the full candidate
list internally (`candidates`/`sorted_candidates`/`top_candidates` in `route()`) before
discarding all but the winner — exposing it is threading an already-computed list out through a
new field, additive on both paths. Restricting it to dry-run-only would add branching complexity
in `InvocationPayload`/`RouterDecision` for no benefit; the field is equally useful for a
consumer inspecting a real dispatch's confidence after the fact.

## Decision 3: naming is `--dry-run`, not `route-only`, not a subcommand

Matches the repo's established convention: `agent_retrospect.py`'s `--dry-run`/`--apply`
pattern, `_cutover_doctor.py`'s `dry_run=True` "writes nothing" convention. Output shape reuses
`InvocationPayload`'s existing JSON shape with a new terminal `"status": "dry_run"` value
(mirroring the existing `"status": "open"` pattern), dropping `close_contract` (nothing to
close). **No `contract_version`/semver envelope discipline is introduced** — that is
orchestrator-api's separate, larger unification effort, explicitly out of scope here (C-003).

## Decision 4: `tk-watch`'s `--profile` pin workaround is out of scope to modify

`tk-watch`'s existing `TK_WATCH_PROFILE`/`--profile` pin workaround for SK-08 continues to
function unmodified after this mission — it uses the explicit-hint router path, which WP3's fix
does not touch. It becomes unnecessary as an SK-08-specific workaround once FR-006/FR-007 land,
but this mission does not edit `tk-watch`'s code (C-004).

## Decision 5: in-mission auto-routed calls carry an accepted routing-consistency risk when WP3 lands mid-mission

`route()` is a pure, stateless function re-evaluated on every call; a spec-kitty mission whose
WP subagents dispatch across the span of time during which WP3 merges to main could see two
auto-routed calls for similar request text resolve to different profiles before and after the
rerank lands. This is accepted as inherent to any bug fix to `router.py`'s selection logic — not
novel to this mission — and is not mitigated further (no mid-mission routing-version pin is
introduced). A caller wanting a stable profile across a mission's lifetime should pass an
explicit `--profile` hint, which this fix does not affect.
