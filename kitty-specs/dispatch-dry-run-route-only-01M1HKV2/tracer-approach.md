# Tracer: Approach — `dispatch-dry-run-route-only-01M1HKV2`

Seeded at planning (2026-09-02). Append during implementation.

## Planning-phase entry

**Architecture chosen**: a new sibling method `ProfileInvocationExecutor.dry_run()` alongside
the existing `invoke()`, rather than a `dry_run: bool` flag threaded through `invoke()` itself.

**Why**: `invoke()` unconditionally mints a truthy `invocation_id = _new_ulid()` as its very
first statement, and that value is load-bearing for every subsequent write (the Op record
filename, the glossary chokepoint's `_build_event_context` gate, the SaaS propagator payload).
A boolean flag threaded through `invoke()` would require special-casing every one of those call
sites from inside one already-branchy method (`invoke()` spans executor.py:284-430 — 147 total
lines, 103 non-blank/non-comment lines). A sibling method instead mirrors only the
*read* half of `invoke()` — profile/route resolution, the advisory model-routing recommendation,
governance-context assembly (`build_charter_context(..., mark_loaded=False)`, already read-only),
and the glossary chokepoint scan — and structurally never reaches the write half at all
(`write_started`, `write_glossary_observation`, `propagator.submit`). This also satisfies FR-003's
non-obvious requirement (never mint or pass a truthy `invocation_id` into
`GlossaryChokepoint.run()`) by construction rather than by an `if` branch that a future edit
could silently break.

**WP sequencing**: WP1 (dry-run + payload shape) → WP2 (`alternatives` field, both paths) → WP3
(SK-08 rerank), strictly sequential — not parallelizable, since WP2 and WP3 both edit the same
two statements inside `router.py`'s `route()` (the single-candidate return and the
`routing_priority` tiebreaker block). This is the operator's own binding decision (spec.md
Clarifications #1), restated here so implementers don't have to re-derive it from spec.md.

**Payload shape**: two distinct JSON shapes on the dry-run path, not one — a success shape that
reuses `InvocationPayload`'s existing field set (minus `invocation_id`/`close_contract`, plus
`alternatives` and `status: "dry_run"`), and a separate minimal shape for the
`ROUTER_AMBIGUOUS`-on-dry-run branch (`profile_id: null, action: null, router_confidence:
"ambiguous", alternatives: [...]`) built by a small dedicated helper colocated in `executor.py`
beside `to_dry_run_dict()`, not in `dispatch.py`, and not by forcing `Optional` through
`InvocationPayload`'s non-Optional `profile_id`/`action` slots. See
plan.md's "Two JSON shapes on the dry-run path" section for the full rationale.

**No PR split**: single PR for the whole mission — Blast Radius is small (5 implementation
files, one of which — `chokepoint.py` — is verification-only with no expected diff; 1 generated
doc regeneration; 1 hand-edited contract doc; 1 CHANGELOG.md entry (WP3, per "Downstream/external
consumer impact"); 3 test files), and the WP1→WP2→WP3 commit
sequence (each with its own ATDD-then-implementation commit pair) keeps the diff legible
per-commit without needing a per-WP PR split.
