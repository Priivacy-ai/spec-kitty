# Mission Specification: Single-Authority Tracker-Egress Verdict

**Mission Branch**: `feat/egress-single-authority`
**Created**: 2026-08-10
**Status**: Draft
**Input**: Retire the tracker-egress two-authority diagnostics split (#3287); remove the redundant per-verdict consent lookup (#3291-item2).

## User Scenarios & Testing *(mandatory)*

The tracker egress gate decides whether a project's mission/engagement identifiers may leave the machine. It already **enforces** that decision from one authority (`project_egress_refusal`). But it re-derives the human-readable *reason* for a refusal — and the remedy shown to the operator — from a **second, independent** consent lookup (`egress_verdict._classify_channel1`). Two evaluations of the same consent chain can drift, and the second one repeats work (a full checkout-routing / git-identity resolution) on every gated verdict. This mission collapses the two into one, sourcing the diagnostic from the same `ConsentDecision` that enforces the outcome — without changing what the gate allows or denies.

### User Story 1 - The refusal reason comes from the deciding authority (Priority: P1)

A maintainer of the confidentiality seam wants the "why refused" and its remedy to come from the *same* evaluation that decided refuse-vs-permit, so what an operator is told can never disagree with what the gate enforced.

**Why this priority**: This is the mission's core value and its correctness guarantee — a diagnostic that can contradict enforcement is the defect #3287 names.

**Independent Test**: Compute the verdict for a project in each consent state and assert the reported `channel1_state`/remedy is derived from the single enforcing `ConsentDecision`, with no second consent or routing lookup on the path.

**Acceptance Scenarios**:

1. **Given** a project with no resolvable identity (`not_consentable`), **When** the egress verdict is computed, **Then** the reported state and remedy (run `spec-kitty init` first) are derived from the single enforcing evaluation, not a second lookup.
2. **Given** a project whose Channel 1 permits, **When** the verdict is computed, **Then** no refusal-diagnostic derivation runs and the reported state is `granted`.
3. **Given** the sync internals cannot be imported, or the resolver returns a stale/malformed value, **When** the verdict is computed, **Then** it refuses (fails closed), maps to a named degraded state, and never raises — including at the `permits_egress` sinks.

### User Story 2 - A gated sync resolves consent once (Priority: P2)

An operator running a gated tracker sync wants the gate to resolve their project's consent a single time, so the command does not spawn a second, redundant batch of git-identity subprocesses.

**Why this priority**: Removes measurable dead work (#3291-item2) — it falls out of Story 1's single-authority change, so it ships together but is not the correctness driver.

**Independent Test**: Count `resolve_checkout_sync_routing_readonly` and `resolve_project_consent` calls (or the git subprocesses they issue) during one gated verdict; assert exactly one of each, down from two.

**Acceptance Scenarios**:

1. **Given** a gated tracker sync on a hosted binding, **When** the verdict is computed, **Then** checkout routing and project consent are each resolved exactly once.

### Edge Cases

- **Degraded resolver** (`NO_RESOLVER`, `UNANSWERABLE`, or resolver-import-failure — the last never reaches `resolve_egress_consent`): the verdict refuses, maps to a **named** degraded diagnostic state (distinct from `undetermined`, which means only `root is None`), and never raises (NFR-003).
- **Mid-migration resolver** still answering a bare `bool`/`None`: the `resolve_egress_consent` mapping must refuse it (never permit) and never let a raw value reach `permits_egress` (which would raise `AttributeError` at the `propagator` sink).
- **Permitting path**: the enforced permit is byte-for-byte unchanged; no diagnostic re-derivation executes.
- **Hosted destination**: the Channel-1 refusal message stays byte-identical across all three refusal states (NFR-002); the `not_consentable` remedy is deliberately carried on the verdict but **not** rendered in the raised hosted message (it resurfaces in `sync doctor`).
- **Concurrent consent mutation**: with one evaluation there is no window in which enforcement and the reported reason can disagree — a structural guarantee, not a behavioural test.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Decision-carrying resolver return | As the seam owner, I want the egress-consent resolver's return to distinguish a grant from the refusal reasons the diagnostic needs (`no_record`, `recorded_refusal`, `not_consentable`) **and** the degraded outcomes (`no_resolver`, `unanswerable`, import-failure), every value derived from the single enforcing evaluation with no second lookup; a malformed/unrecognized return refuses (never permits) and never raises. | High | Open |
| FR-002 | Single consent authority + threading | As the seam owner, I want `channel1_state` sourced from the same `ConsentDecision` (`resolve_project_consent`) that enforces the grant/refuse outcome — replacing the enforcing path's level-erasing `consented_project_uuids` flattening — and the decision value to reach `egress_verdict._resolve_channel1` without adding a second routing/consent resolution and without perturbing `project_egress_refusal`'s byte-identical refusal string. | High | Open |
| FR-003 | Delete the second evaluation | As the seam owner, I want `egress_verdict._classify_channel1`, its independent routing/consent resolution, and its two non-authoritativeness pins removed, with `channel1_state` coming from FR-002's shared decision. | High | Open |
| FR-004 | Audit and re-point every consumer of the changed contract | As the seam owner, I want every consumer enumerated with a required disposition: `egress.py::_refusal_for_verdict`'s `DENIED` branch re-pointed so all refusal states still render `_DENIED_TEMPLATE`; the `resolve_egress_consent` mapping (`invocation/adapters.py`) updated to keep "only a recognized grant permits, anything else refuses, never raises"; the widen-mode SaaS transport (`saas_client/client.py`) refusal string verified unchanged; `propagator.py` (uses `permits_egress` only) verified unaffected; `sync doctor` renders the same per-destination state/remedy. | High | Open |
| FR-005 | Preserve per-state remedies, incl. the hosted carve-out | As an operator, I want the refusal remedy for each state preserved and sourced from the single evaluation — including the deliberate `HOSTED_SERVICE` carve-out where the `not_consentable` "run `spec-kitty init`" remedy is carried on the verdict but not rendered in the raised message. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Enforcement unchanged (full matrix) | For every Channel-1 outcome — **including `granted` and each consent precedence level (project-local / machine-index / env)** — × Channel-2 value × destination, the enforced `refused`/`refusing_channels` is identical before and after (0 differences); no combination that previously refused now permits. | Security | High | Open |
| NFR-002 | Hosted byte-identity | The `HOSTED_SERVICE` Channel-1 refusal message (composed in `egress.py::_render_denied_refusal`) is byte-identical for all three refusal states — 0-byte diff. | Compatibility | High | Open |
| NFR-003 | Never raises / fail-closed | The resolver, the `resolve_egress_consent` mapping, and the verdict never raise; a malformed / stale / `None` / bare-`bool` return or an unimportable resolver degrades to a refusal, with no `AttributeError` at any `permits_egress` sink. | Reliability | High | Open |
| NFR-004 | One resolution each | A gated verdict resolves checkout routing (`resolve_checkout_sync_routing_readonly`) and project consent (`resolve_project_consent`) exactly once each (down from two), verified by call/subprocess count. | Efficiency | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Seam must not widen (mechanism-pinned) | Every `EgressConsent` member except `GRANTED` answers `permits_egress is False`, certified by the iterate-all-members guard; no consumer positively grant-checks by member identity — all go through `permits_egress`. | Technical | High | Open |
| C-002 | Delete, not migrate | `_classify_channel1` and its two non-authoritativeness pins are deleted per the module's documented retirement condition — not carried forward. | Technical | Medium | Open |
| C-003 | Rebuild (not re-point) the enforcement guarantee | `TestReportingSplitNeverFlipsEnforcement` cannot be re-pointed — its premise (a second authority to force into disagreement) is deleted with `_classify_channel1`. It is rebuilt as the "exactly one routing/consent resolution on the verdict path" assertion (NFR-004) plus the `_classify_channel1` symbol-absence pin. | Technical | Medium | Open |
| C-004 | Single derivation locus (no relocation) | The one consent+routing resolution and the `ConsentDecision → EgressConsent` split-mapping live **once, in the registered resolver** (`sync/__init__.py`). `egress.py` holds **no** `sync.consent`/`sync.routing` import and re-derives nothing locally (its existing no-local-derivation invariant — the `egress.py` module docstring, from mission `#3030` — now test-pinned); `consented_project_uuids` is retained for its ~9 sibling drain/emit/commit callers and removed only from the egress resolver. | Technical | High | Open |

### Key Entities

- **EgressConsent**: the port enum (today `GRANTED` / `DENIED` / `NO_RESOLVER` / `UNANSWERABLE`). `DENIED` is split into the three refusal reasons; every non-`GRANTED` member answers `permits_egress is False`.
- **ConsentDecision** (`resolve_project_consent`): the single consent authority carrying `granted` + `level` + `project_uuid`; both the enforced boolean and the diagnostic state derive from it, so `consented_project_uuids`' level-erasing wrapper is no longer the enforcing query.
- **Channel-1 state**: the reported diagnostic, derived from the decision above rather than a second lookup.

## Non-Goals *(scope boundary)*

- **Cross-call caching across multiple verdict computations within one command** (e.g., a CLI pre-flight and the transport each computing the verdict) is out of scope. This mission collapses the two resolutions **within one verdict**, not across verdicts.
- Other consent/routing resolutions serving **different** gates (emit-time `is_sync_enabled_for_checkout`, body-upload, drain) are out of scope and must not be altered.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across the full matrix — **including the `granted` row and each consent precedence level** × the Channel-2 value set × 2 destinations — the enforced refuse/permit outcome and `refusing_channels` are identical before and after (0 differences); no previously-refused combination permits.
- **SC-002**: The `HOSTED_SERVICE` Channel-1 refusal message is byte-identical for all three refusal states and to the pre-change output (0-byte diff).
- **SC-003**: A gated tracker sync verdict performs exactly one `resolve_checkout_sync_routing_readonly` and one `resolve_project_consent` (each down from two).
- **SC-004**: `egress_verdict._classify_channel1` and its two non-authoritativeness pins no longer exist; the egress-consent boundary guard and the iterate-all-members `permits_egress` guard remain green.
- **SC-005**: `spec-kitty sync doctor` renders the same per-destination Channel-1 state and remedy for `granted` and the three refusal states. The degraded states (`no_resolver` / `unanswerable` / import-failure) are an **intended improvement** — import-failure no longer masquerades as `no_record` — pinned against the captured pre-change golden reference rather than asserted "unchanged".
