# Research: Single-Authority Tracker-Egress Verdict

Phase 0 output. The mission is a contained refactor on a well-understood seam, so "research" here resolves the design decisions the post-spec and post-plan squads flagged, each with rationale and rejected alternatives.

## Decision 1 — The single split-mapping lives in the registered resolver; `egress.py` never re-derives locally (post-plan M1)

**Decision**: The one `resolve_project_consent` + one routing resolution, **and** the `ConsentDecision → EgressConsent` split-mapping, live **once, in the registered resolver** (`sync/__init__.py`'s `_egress_consent_resolver`), which now returns the decision-carrying `EgressConsent` member. `egress.py`'s `_egress_decision` obtains that member **only** through the existing `resolve_egress_consent` seam and performs **no** local consent/routing resolution — it must not import `sync.consent`/`sync.routing`. `egress_verdict._resolve_channel1` then consumes `_egress_decision`'s `(permits, refusal_message, channel1_state, generic)` from that single evaluation.

**Rationale**: `egress.py`'s own load-bearing docstring (`egress.py:28-52`, C-004) forbids re-deriving the checkout→project→consent chain locally — *"the single derivation lives in `sync/__init__.py`'s `_egress_consent_resolver`."* And `propagator.py:127` calls `resolve_egress_consent` **directly**, so the resolver must return the split members regardless; if `_egress_decision` *also* mapped `ConsentDecision→member`, the split-mapping would exist in two drift-prone places (resolver-for-propagator vs decider-for-verdict) — the exact defect class FR-002 exists to kill. One mapping, in the resolver.

**Alternatives rejected**:
- *`_egress_decision` resolves consent/routing locally in `egress.py`* — violates C-004, and relocates (not removes) the two-authority split.
- *Change `project_egress_refusal`'s return type to carry both string and state* — hits its other consumer `saas_client/client.py:171` (wants a bare `str | None`); the thin-wrapper design (below) avoids this.

## Decision 2 — The consent authority and the enforcing-query replacement

**Decision**: `resolve_project_consent` (returning `ConsentDecision{granted, level, project_uuid}`) is the single consent authority. The registered resolver calls it **once** and maps to an `EgressConsent` member:
`granted → GRANTED`; not-granted + `ConsentLevel.ABSENT → NO_RECORD`; not-granted + a recorded-refusal level → `RECORDED_REFUSAL`; `ConsentLevel.UNDETERMINED` (record unreadable, FR-020) → `RECORDED_REFUSAL` **consciously** (matches today's behaviour, pinned in SC-005, not a silent catch-all — post-plan m2); no `project_uuid` → `NOT_CONSENTABLE`; resolver unregistered → `NO_RESOLVER`; unrecognized/malformed → `UNANSWERABLE`.

**Rationale**: Enforcement equivalence holds **by construction** — `uuid in consented_project_uuids([uuid], roots)` reduces exactly to `resolve_project_consent(uuid, roots).granted` (`consent.py:730-738`), the same call `_classify_channel1` already makes. Reading the full `ConsentDecision` once recovers both the grant verdict and the three refusal reasons. **`consented_project_uuids` is retained** — it has ~9 live sibling callers (drain/emit/commit: `delivery/selection.py`, `delivery/consent_gate.py`, `sync/emitter.py`, `sync/runtime.py`, `sync/background.py`, `sync/body_upload.py`, `sync/local_commit.py`) and is removed **only** from the egress resolver's own use (post-plan NOTE-4).

**Out of scope (siblings explicitly excluded)**: `delivery/status_report.py:865` (`build_per_project_store_report`, FR-015) is a *different* report, not the egress verdict — not folded (post-plan MINOR-2).

## Decision 3 — Degraded states carry a `generic` signal so the message composer stays total (post-plan M2 — the symmetric never-raise gap)

**Decision**: The degraded members (`NO_RESOLVER`, `UNANSWERABLE`, resolver-import-failure) map to a **named degraded `channel1_state`** that carries `generic = True`. The message/remedy composer (`_channel1_decided_message`, whose `_CHANNEL1_DESCRIPTIONS`/`_CHANNEL1_REMEDIES` dicts are keyed only on the three refusal states) already checks `generic` **before** indexing those dicts — so a degraded state renders generic wording and **cannot KeyError**. `_egress_decision`/`_resolve_channel1` absorb the `(state, generic)` production that `_channel1_report` did today; the generic-rendering path is **retained and re-sourced** (fed from the decider), while `_classify_channel1` (the raising *source* of the generic flag) is deleted. The import-failure branch preserves `_IMPORT_FAILURE_TEMPLATE`'s `{exc}` text as `refusal_message` (post-plan n2).

**Rationale**: Deleting `_classify_channel1` deletes the `try/except` that produced `generic=True` today; without re-sourcing it, a degraded `channel1_state` at the `OUTCOME_DEFER` branch would index a dict keyed only on the three refusal states → `KeyError` → a raise out of a gate NFR-003 says never raises. Carrying `generic` through the decider closes that symmetrically with the `egress.py`-side `_UNRECOGNISED_VERDICT_TEMPLATE` fall-through.

**Reported-state note (SC-005)**: today import-failure *masquerades* as `CHANNEL1_NO_RECORD` (`egress_verdict.py:424`). The new design reports it as the degraded state instead — an intended improvement (no longer a diagnostic lie), pinned with its own test row rather than under "unchanged".

## Decision 4 — Rebuilding the enforcement guarantee (C-003 of the spec)

**Decision**: `TestReportingSplitNeverFlipsEnforcement` is **rebuilt**, not re-pointed — once `_classify_channel1` is gone there is no second authority to force into disagreement. The replacement asserts structurally: exactly one `resolve_checkout_sync_routing_readonly` and one `resolve_project_consent` on the verdict path (NFR-004/SC-003); the `_classify_channel1` symbol-absence (SC-004); the full enforcement-equivalence matrix incl. the permit row + precedence levels (SC-001); **and a new pin that `egress.py` holds no `sync.consent`/`sync.routing` import** (the C-004 invariant that today has no test — post-plan M1).

## Open clarifications

None. The user-facing decisions (split the enum; fresh feat branch) were resolved at specify time; the design decisions above are engineering choices resolved here and hardened by the post-plan squad.
