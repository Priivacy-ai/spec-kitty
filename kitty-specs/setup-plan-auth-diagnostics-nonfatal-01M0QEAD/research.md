# Research: Authoritative local setup-plan with safe hosted refusal

## Decision 1: Preserve session-assessment provenance inside TokenManager

**Decision**: Add a typed canonical session assessment to `TokenManager` and retain the
outcome of initial storage load and later hot-summary materialization. The assessment
records completion separately from usable-session presence; it does not add a third
authentication state.

**Rationale**: `load_from_storage_sync()` currently catches storage errors and clears
the session. Readiness therefore receives the same Boolean for “no session” and “could
not read session.” Information must be preserved at the authority that first observes
it. This aligns with the accepted encrypted file-only auth ADR and keeps token handling
centralized.

**Alternatives considered**:

- Catch `is_authenticated` errors only in readiness: rejected because the storage
  failure has already been swallowed.
- Read the encrypted store directly from setup-plan: rejected as a duplicate auth
  authority and credential-boundary violation.
- Use queue scope as a fallback: rejected because it is delivery-routing metadata.

## Decision 2: Keep Boolean compatibility and the existing readiness taxonomy

**Decision**: Existing `is_authenticated` callers retain a Boolean projection while new
readiness/setup-plan code consumes `SessionAssessment`. The existing readiness
`AuthStatus.UNKNOWN` remains an assessment/probe failure category; it is not promoted to
a canonical authentication state.

**Rationale**: The mission needs richer truth without forcing unrelated auth callers to
change. A usable refresh token remains authenticated even if the access token is
expired; no refresh or network request occurs during classification.

**Alternatives considered**:

- Change `is_authenticated` to return an enum: rejected as an unnecessary breaking
  change.
- Treat expired access tokens as logged out: rejected because refreshability is the
  supported session criterion.

## Decision 3: Add a setup-plan-only no-raise boundary adapter

**Decision**: Call canonical `run_preflight(repo_root, require_auth=False)` behind a
narrow adapter that converts both returned unsafe results and exceptions into a typed
boundary evaluation.

**Rationale**: The detector remains authoritative and strict for hosted-only commands.
`setup-plan` needs different command severity because structural readiness governs only
its hosted effects. Unknown safety still refuses delivery.

**Alternatives considered**:

- Make `run_preflight()` globally no-raise: rejected because it could weaken hosted-only
  commands.
- Ignore structural exceptions: rejected because unknown cannot authorize egress.
- Reimplement preflight fields in setup-plan: rejected as a second authority.

## Decision 4: Compose one hosted-delivery decision

**Decision**: Session assessment, boundary safety, canonical read-only route availability,
and the SaaS-enable flag produce one immutable decision and ordered diagnostic tuple.
Route availability comes only from `resolve_checkout_sync_routing_readonly()` and requires
a non-empty project UUID plus effective sync consent.

**Rationale**: Every hosted sink needs the same permission. Central composition avoids
per-call-site drift and keeps command severity (`warning`) distinct from hosted
disposition (`refused`).

**Alternatives considered**:

- Independent guards at each sink: rejected because the issue is a repeated authority
  and sequencing defect.
- One generic warning: rejected because logged out, auth assessment failure, structural
  unsafe, and route unavailable require different remediation.

## Decision 5: Split lifecycle persistence from hosted fan-out

**Decision**: Provide explicit local persistence and hosted fan-out operations. Retain
the existing composed append API for unaffected callers.

**Rationale**: Current lifecycle append writes JSONL and then invokes registered SaaS
adapters. Treating it as “local-only” leaves an outbox bypass. Explicit operations make
the invariant enforceable and allow setup-plan to persist local evidence before the
hosted decision.

**Alternatives considered**:

- Suppress all lifecycle events when unsafe: rejected because local history is part of
  verification evidence.
- Unregister adapters globally: rejected because it is ambient, process-wide, and
  unsafe for other callers.
- Guard only dossier sync: rejected because lifecycle fan-out is a second hosted sink.

## Decision 6: Freeze local outcomes before orchestration

**Decision**: Capture exact baseline payloads and exits for complete, scaffold,
insufficient, spec-gate, missing-spec, template, generic error, and pre-root failures.
Only an additive warnings collection may vary after the change.

**Rationale**: “Keep existing behavior” is too vague when current paths use different
result classifications and exits. A typed local outcome and one reporter make
compatibility testable.

**Alternatives considered**:

- Test only complete/incomplete: rejected because independent error emitters could lose
  diagnostics or change exits.
- Normalize all blocked cases to nonzero: rejected as unauthorized product change.

## Decision 7: Require production-chain and non-vacuous safety evidence

**Decision**: Use real isolated encrypted storage for the original auth regression and
add an architectural hosted-effect gate with a synthetic mutation test.

**Rationale**: Boolean fakes cannot reproduce storage information loss, and call-site
comments cannot prevent a future hosted sink bypass. The charter requires ATDD-first and
bug-class closure by construction.

**Alternatives considered**:

- Unit mocks only: rejected as fakeable.
- A static allowlist without negative control: rejected as vacuous.

## Decision 8: Keep issue #3127 out of the code DAG

**Decision**: Track #3127 with a terminal fixed or deferred-with-followup verdict at
Mission acceptance. An unresolved verdict blocks release-readiness declaration only.

**Rationale**: It is an open P0 release gate, not a source dependency for issue #3621.
Implementation and Mission completion can proceed with an honest deferred follow-up, but
release readiness cannot be declared while it remains unresolved or mainline CI is red.

**Alternatives considered**:

- Make every WP depend on #3127: rejected because the runtime cannot express an external
  issue as a code-lane dependency and doing so blocks useful work.
- Omit it from tasks: rejected because it could be forgotten at closeout.
