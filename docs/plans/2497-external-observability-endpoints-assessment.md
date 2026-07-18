---
title: 'RFC #2497 — External Observability Endpoints: Squad Assessment'
description: 'Decision-support assessment of the five additive CLI endpoints proposed in RFC #2497 (external observability + attestation side-car), across architecture, duplication, and doctrine lenses — with a per-endpoint retain/create/decline recommendation. Does not decide; RFC #2497 stays open.'
doc_status: active
updated: '2026-07-18'
related:
- docs/plans/index.md
- docs/api/cli-commands.md
---

# RFC #2497 — External Observability Endpoints: Squad Assessment

*Assessment synthesis, 2026-07-09 (design-alignment corrections applied 2026-07-18). Three profile-loaded lenses — architecture (architect-alphonso), duplication/consolidation (paula-patterns), doctrine/governance (doctrine-daphne) — evaluated the five endpoints proposed in [RFC #2497](https://github.com/Priivacy-ai/spec-kitty/issues/2497) (author: @OriPekelman) against the current codebase, then a second scrutiny pass re-verified every claim against `main` and against the [#645 Stable Application API Surface](https://github.com/Priivacy-ai/spec-kitty/issues/645) epic's scope.*

> **Status: decision-support only.** This document captures the ideas and the squad's evidence so a retain/create/decline decision can be made deliberately. **RFC #2497 stays OPEN** — it should be closed only after the operator decides which endpoints to retain and which issues to create.

## Context

@OriPekelman is building an external **observability + attestation side-car** that wraps the coding agents Spec Kitty orchestrates and produces *signed, verifiable* records of each run. Its self-imposed constraint: work **entirely outside-in** — shell out to `spec-kitty`, read documented on-disk artifacts (`status.events.jsonl`, `lanes.json`, `meta.json`), import nothing from `specify_cli`, change nothing in core. The RFC surfaces five places where a small **additive** endpoint would make outside-in integration cleaner *for any third-party tool*. None is blocking — each has a working fallback today.

The RFC's three principles (generally useful, additive/optional, no private surface) are sound and align with the **#645 Stable Application API Surface** epic. The squad's job was to check each endpoint against reality: what already exists, what consolidates duplication, and what governance guards are non-negotiable.

## Headline findings

1. **The RFC under-counts what already ships.** E1 (`charter context --json`) is **already implemented**; E4's `proof` primitive **already exists** as a first-class, fully-modeled event schema (though presently *dormant* — see below). So the real question for those two is *contract stabilization and trust boundary*, not *build a feature*.
2. **Two distinct keystones are missing — keep them separate.** The side-car's premise is *signed, verifiable* records, but **no *keyed* cryptographic signature/seal exists anywhere on the proof, event-journal, or `status.events.jsonl` surfaces today** (only unkeyed content hashes and an idempotency digest, which give no forgery resistance). That gap bounds the *authenticity* value of E3/E4. It is **not**, however, what protects governance authority: the authority boundary is enforced **architecturally, not cryptographically** — the transition gate does not read proof events at all (see finding 3). Signing makes external records *verifiable to journal consumers*; it does **not** make an external assertion *admissible* to any gate. Sequence the signing keystone first for attestation value, but do not conflate it with the authority guard.
3. **One non-negotiable governance line: proofs/exports are *observations*, never *authority*.** Lane/lifecycle authority is `status.events.jsonl` reduced by the status FSM, and the approval gate in `status/wp_state.py` (`_check_reviewer_approval`) requires structured reviewer evidence carried on the `TransitionContext`. Proof events are **fully decoupled** from that gate today (`status/` imports `proof/` zero times; `emit_proof_event` has no production caller yet). An external write must **never** be wired to satisfy that gate or mint a `HumanApprovalRecorded` — the load-bearing guard is *reject external approvals at ingress*, independent of signing.

## Per-endpoint assessment

Two rankings — separate near-term leverage-to-cost from ultimate value, because E4's value is gated on a whole signing subsystem:

- **Near-term leverage-to-cost:** **E1 > E2 > E3 (cursor) > E4 > E5.**
- **Ultimate value (once the signing keystone exists):** **E1 > E2 > E4 > E3 > E5.**

**Cross-cutting adopt-constraint (all three "adopt" endpoints, E1/E2/E3):** each new read endpoint MUST be a projection of #645's canonical **service-layer** interface (`MissionRegistry`, [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956)), not a new standalone filesystem reader. #645 forbids per-request filesystem walks from transport/CLI-side modules via an architectural test; a `lanes write-scope` / `charter context` reader that re-walks disk would reintroduce exactly the drift #645 exists to kill.

### E1 — `charter context --action <a> --json` → **ALREADY SHIPS; formalize the contract**

- **Current state:** implemented today in `src/specify_cli/cli/commands/charter/context.py` (`--action` **and** `--json`), backed by `charter.context.build_charter_context_json`; action vocabulary in `src/doctrine/missions/action_index.py`. Emits action-scoped `directives`, `all_directives`, `tactics`, `styleguides`, `toolguides`, `governance_references`, `project_charter`, and an `org_charter` block with per-artifact provenance. The RFC's "parse the text output" fallback is stale — the JSON path is canonical.
- **All three lenses agree:** nothing to build; this is a discoverability + contract-stability gap.
- **The real gap (doctrine lens):** the top-level payload carries **no `schema_version`**. An external attestor pinning to this shape breaks silently on any doctrine-layer reshape.
- **Recommendation:** small hardening issue under #645 — stamp the payload with a top-level `context_schema_version` (named distinctly to avoid confusion with the **existing nested** `org_charter.schema_version` at `doctrine/org_charter.py`), document it as a stable external contract with a deprecation policy, and emit resolved artifact ids + provenance (never raw pack internals). Route the reader through the #645 service layer. **Not a new endpoint.**

### E2 — `lanes write-scope --wp <id> --json` → **ADOPT (highest-leverage new work)**

- **Current state:** no `lanes` CLI group exists, but the state is fully computed and persisted: `LanesManifest.lane_for_wp(wp_id)` is the canonical WP→lane lookup, `ExecutionLane.write_scope` / `to_dict()` are serialized into `lanes.json`, and the collapse math lives only in `lanes/compute.py` (`src/specify_cli/lanes/models.py`, `lanes/persistence.py`, `lanes/compute.py`).
- **Duplication lens (corrected):** this is **not** a present-duplication cleanup — the internal tree is *already consolidated*: all internal WP→lane callers funnel through `lane_for_wp()`, `lanes.json` reads go through one loader, and there are no bypass sites (the surface already satisfies DIR-044 `044-canonical-sources-and-unification`). The value is a **net-new external-contract projection**: it prevents *future* re-derivation by outside-in tools that cannot import `lane_for_wp`, giving them one stable read model instead of each re-implementing the collapse semantics as core evolves.
- **Guards (architecture + doctrine):** read-only projection of the #645 service layer; it must *reflect, never redefine*, allocator ownership. Expose the **resolved globs** (`write_scope` already *is* the resolved glob union), not the internal collapse-rule vocabulary (an implementation detail, not a contract).
- **Recommendation:** **create an issue** under #645. Smallest, safest, highest-leverage of the five.

### E3 — `event_journal subscribe` → **DECLINE the daemon; use #645's planned async transport instead**

- **Current state:** no streaming/subscribe primitive today. `spec_kitty_events` is a pure schema/reducer library (no I/O); the dashboard server is request/response only (no websocket/SSE); `status/store.py` is a batch JSONL reader with no tail/follow.
- **Architecture + duplication lenses:** a bespoke `subscribe` **daemon** (its own lifecycle, connection state, backpressure, resume cursors) is the heaviest boundary edge in the set and consolidates nothing (one legit reader today). `status.events.jsonl` is an append-only, documented log; **polling it is already a correct decoupled contract**. Crucially, an async push transport is **already a planned #645 deliverable** — Sequencing step 6 is *"async update transport (WebSocket / SSE)"* on the migrated FastAPI transport (mission `frontend-api-fastapi-openapi-migration`). E3 should ride that, not a second long-running process and not the legacy stdlib `server.py`.
- **Doctrine lens:** any export must be strictly one-way read-only (no ack/cursor-mutation that could rewrite producer state), and its attestation value is bounded by the missing signing seal.
- **Recommendation:** **decline** `subscribe` as a standalone push daemon. Near-term, publish a documented **cursor read-contract** (`--since <event_id>`) on the existing reader. Longer-term, fold the streaming need into **#645's planned SSE-on-FastAPI transport** rather than tracking it as a novel endpoint. Gate any attestation framing on the signing keystone.

### E4 — `proof emit --from-file <f>` → **DO NOT add a new verb; fence an external-evidence ingress (with signing) — under a dedicated attestation epic, not #645**

- **Current state:** the `proof` concept is **already a first-class primitive** — `src/specify_cli/proof/events.py` defines a strict (`extra="forbid"`) schema, `PROOF_SCHEMA_VERSION = "1.0.0"`, **7** event types (`ProofItemRecorded`, `ReviewProofRecorded`, `TestEvidenceCaptured`, `BenchmarkEvidenceAttached`, `SecurityScanCompleted`, `PullRequestLineageRecorded`, `HumanApprovalRecorded`), `ProofActor`/`ProofSubject` (whose `actor_type` Literal already includes `"service"`), idempotency keys, bounded envelopes — with an emitter method `sync/emitter.py::emit_proof_event` into the append-only `event_journal`. **Maturity caveat:** the primitive is **modeled but not yet wired** — `emit_proof_event` has no production call site today, so proof events are a designed-but-dormant stream, not an actively-populated store.
- **Duplication lens (corrected seam):** a governed external proof ingress maps to the **proof-event path** (`emit_proof_event` → `event_journal`, mission/WP-scoped, aggregate inferred by `proof/events.py::infer_proof_aggregate`) — **not** to `profile-invocation complete --evidence`, which is an *Op-scoped file promotion* (`invocation/record.py::promote_to_evidence`, requires an active invocation). Those are two different seams; the RFC's own "keep it in your own store" fallback is a step backward from the richer canonical primitive. Because proof events are themselves already a store, a bare `proof emit` is best understood as an **unauthenticated external writer into the existing proof store**, not a "4th parallel evidence store." (For completeness, the evidence surfaces in the codebase are more than three — invocation Tier-2 evidence, `status/emit.py` done-evidence, issue-matrix `evidence_ref`, retrospective `evidence_refs`, acceptance-matrix `evidence` — but they are **distinct-by-design** across different tiers/lifecycles/authority semantics and should **not** be collapsed. Only `status/emit.py` done-evidence and the issue-matrix `evidence_ref` feed the approval gate.)
- **Doctrine lens (the sharp risk):** today the actor is **self-declared and unauthenticated**, and there is no keyed signature. An external emit is an unauthenticated write of a self-attesting record. Note the risk is precise: because proof events are decoupled from the transition gate (finding 3), a forged `HumanApprovalRecorded{approved}` cannot *today* unlock `approved`/`done` — the live exposure is to **attestation-record consumers** (the side-car and journal readers), and to any *future* wiring that reads proofs into authority. **Required guards:** (1) external-origin proofs stamped `actor_type: "service"` with a distinct source, **never wired** as admissible reviewer `evidence`; (2) reject `HumanApprovalRecorded` / approving verdicts from the external ingress entirely; (3) add a signature/integrity seal so external emits are *verifiable* rather than *forgeable* — which is also exactly the RFC's own value prop. Guard (2) is load-bearing on its own; guard (3) adds authenticity, not authority.
- **Recommendation:** the genuinely valuable net-new surface, but **not as `proof emit`** and **not under #645** (which is a stable *read/query* surface — E4 is a *write* ingress plus a *cryptographic attestation* subsystem, a security/attestation concern; cf. proof-events epic #920). Create, under a **dedicated attestation/security epic**: (a) an **attestation-signing keystone** issue (prerequisite, unblocks the authenticity value of E3+E4), and (b) a **governance-fenced external-evidence ingress** design issue on the proof-event path (external-origin guard; observations-not-authority).

### E5 — `session hooks register` → **DECLINE as framed (commands-only, via the existing registrar)**

- **Current state:** a hook-registration seam already exists — `HookRegistrar` Protocol + `ClaudeCodeHookRegistrar.register/unregister` own idempotent mutation of `.claude/settings.json` (`src/specify_cli/session_presence/hooks/`), invoked internally at `init`/`upgrade` to register spec-kitty's own `session-start`/`session-stop` **commands**. spec-kitty is the hook *callee*, not an instruction *injector*.
- **Architecture + doctrine lenses:** a `hooks register` that injects **standing instructions** inverts a bounded context (DIR-031) and, worse, **bypasses charter authority** — standing instructions *are* doctrine, and the charter is the single canonical authority for them (resolved through `charter context`). An external, per-harness instruction channel is a split-brain doctrine source that no `charter context` resolution knows about and no terminology/doctrine gate audits.
- **Recommendation:** **decline** the "external tool injects standing instructions" framing. If a side-car needs its shim present at session start, permit registering a **command** (the side-car's own hook binary) via a public extension of `ClaudeCodeHookRegistrar` — and route any *instruction content* through doctrine (a directive/paradigm) so the charter stays the single source. Optional narrow issue only if the commands-only extension is wanted.

## Summary & recommended tracker actions

| # | Endpoint | Verdict | Recommended action |
|---|----------|---------|--------------------|
| **E1** | `charter context --json` | Already ships | Small hardening issue: add top-level `context_schema_version` (distinct from nested `org_charter.schema_version`), document as external contract, project via #645 service layer (#645) |
| **E2** | `lanes write-scope --json` | **Adopt** | **Create issue** — net-new external-contract projection of `lane_for_wp()`/`write_scope` via the #645 service layer (#645). Highest near-term leverage |
| **E3** | `event_journal subscribe` | Decline daemon | No push daemon. Near-term: `--since <cursor>` read-contract. Longer-term: fold into #645's planned SSE-on-FastAPI transport (Sequencing step 6). Gated on signing for attestation |
| **E4** | `proof emit` | Adopt-with-guards | **Create 2 issues under a dedicated attestation/security epic (not #645):** attestation-signing keystone (prereq) + governance-fenced external-evidence ingress on the **proof-event path** (`emit_proof_event`; external-origin guard; observations-not-authority) |
| **E5** | `session hooks register` | Decline as framed | No instruction-injection API. Optional narrow issue: commands-only `HookRegistrar` public extension |

**Cross-cutting:** the **attestation-signing seal** is the true keystone for *authenticity* — the missing prerequisite that gives E3 and E4 their verifiable-attestation value, and it should be sequenced first. It is separate from the *authority* guard (observations-≠-authority), which is enforced by the gate not reading external writes and must hold regardless of signing.

**Next step (operator):** decide which of the above issues to create (E1/E2/E3 under #645 with the service-layer-projection constraint; E4's keystone + ingress under a dedicated attestation/security epic), then close RFC #2497 with a summary of what was retained. This assessment does not close it.
