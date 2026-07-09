---
title: 'RFC #2497 — External Observability Endpoints: Squad Assessment'
description: 'Decision-support assessment of the five additive CLI endpoints proposed in RFC #2497 (external observability + attestation side-car), across architecture, duplication, and doctrine lenses — with a per-endpoint retain/create/decline recommendation. Does not decide; RFC #2497 stays open.'
doc_status: active
updated: '2026-07-09'
related:
- docs/plans/index.md
- docs/api/cli-commands.md
---

# RFC #2497 — External Observability Endpoints: Squad Assessment

*Assessment synthesis, 2026-07-09. Three profile-loaded lenses — architecture (architect-alphonso), duplication/consolidation (paula-patterns), doctrine/governance (doctrine-daphne) — evaluated the five endpoints proposed in [RFC #2497](https://github.com/Priivacy-ai/spec-kitty/issues/2497) (author: @OriPekelman) against the current codebase.*

> **Status: decision-support only.** This document captures the ideas and the squad's evidence so a retain/create/decline decision can be made deliberately. **RFC #2497 stays OPEN** — it should be closed only after the operator decides which endpoints to retain and which issues to create.

## Context

@OriPekelman is building an external **observability + attestation side-car** that wraps the coding agents Spec Kitty orchestrates and produces *signed, verifiable* records of each run. Its self-imposed constraint: work **entirely outside-in** — shell out to `spec-kitty`, read documented on-disk artifacts (`status.events.jsonl`, `lanes.json`, `meta.json`), import nothing from `specify_cli`, change nothing in core. The RFC surfaces five places where a small **additive** endpoint would make outside-in integration cleaner *for any third-party tool*. None is blocking — each has a working fallback today.

The RFC's three principles (generally useful, additive/optional, no private surface) are sound and align with the **#645 Stable Application API Surface** epic. The squad's job was to check each endpoint against reality: what already exists, what consolidates duplication, and what governance guards are non-negotiable.

## Headline findings

1. **The RFC under-counts what already ships.** E1 (`charter context --json`) is **already implemented**; E4's `proof` primitive **already exists** as a first-class, fully-modeled event schema. So the real question for those two is *contract stabilization and trust boundary*, not *build a feature*.
2. **The keystone is missing everywhere.** The side-car's whole premise is *signed, verifiable* records, but **there is no cryptographic signing / integrity seal anywhere in the codebase today** (proof path, event journal, or `status.events.jsonl`). The attestation value of E3 and E4 is bounded by this gap — the signing seal is the true prerequisite, and once it exists the trust boundary largely enforces itself.
3. **One non-negotiable governance line: proofs/exports are *observations*, never *authority*.** Lane/lifecycle authority is `status.events.jsonl` reduced by `status.reducer`, and the approval gate in `status/wp_state.py` requires reviewer evidence. An external write must **never** satisfy that gate or mint a `HumanApprovalRecorded`.

## Per-endpoint assessment

Leverage-to-cost ranking (all three lenses converge): **E1 > E2 > E4 > E3 > E5.**

### E1 — `charter context --action <a> --json` → **ALREADY SHIPS; formalize the contract**

- **Current state:** implemented today in `src/specify_cli/cli/commands/charter/context.py` (`--action` **and** `--json`), backed by `charter.context.build_charter_context_json`; action vocabulary in `src/doctrine/missions/action_index.py`. Emits action-scoped `directives`, `all_directives`, `tactics`, `styleguides`, `toolguides`, `governance_references`, `project_charter`, and an `org_charter` block with per-artifact provenance. The RFC's "parse the text output" fallback is stale — the JSON path is canonical.
- **All three lenses agree:** nothing to build; this is a discoverability + contract-stability gap.
- **The real gap (doctrine lens):** the payload carries **no `schema_version`**. An external attestor pinning to this shape breaks silently on any doctrine-layer reshape.
- **Recommendation:** small hardening issue under #645 — stamp the payload with a `context_schema_version`, document it as a stable external contract with a deprecation policy, and emit resolved artifact ids + provenance (never raw pack internals). **Not a new endpoint.**

### E2 — `lanes write-scope --wp <id> --json` → **ADOPT (highest-leverage new work)**

- **Current state:** no `lanes` CLI group exists, but the state is fully computed and persisted: `LanesManifest.lane_for_wp(wp_id)` is the canonical WP→lane lookup and `ExecutionLane.write_scope` / `to_dict()` are already serialized into `lanes.json` (`src/specify_cli/lanes/models.py`, `lanes/compute.py`).
- **Duplication lens:** a **pure de-duplication win** — today every consumer re-implements the `lanes.json` lookup and the lane-collapse semantics, which drifts as core evolves (a DIR-044 violation by construction). The endpoint is a thin read-only projection of an existing pure function.
- **Guards (architecture + doctrine):** read-only projection only; it must *reflect, never redefine*, allocator ownership. Expose the **resolved globs**, not the internal collapse-rule vocabulary (that's an implementation detail, not a contract).
- **Recommendation:** **create an issue** under #645. Smallest, safest, highest-leverage of the five.

### E3 — `event_journal subscribe` → **DECLINE the daemon; offer a cursor read-contract instead**

- **Current state:** no streaming/subscribe primitive anywhere. `spec_kitty_events` is a pure schema/reducer library (no I/O); the dashboard server is request/response only (no websocket/SSE); `status/store.py` is a batch JSONL reader with no tail/follow.
- **Architecture + duplication lenses:** `subscribe` is a **net-new transport subsystem** (daemon lifecycle, connection state, backpressure, resume cursors) — the heaviest boundary edge in the set, and it consolidates nothing (there is only one legit reader today). `status.events.jsonl` is an append-only, documented log; **polling it is already the correct decoupled contract**.
- **Doctrine lens:** any export must be strictly one-way read-only (no ack/cursor-mutation that could rewrite producer state), and its attestation value is bounded by the missing signing seal.
- **Recommendation:** **decline** `subscribe` as a push daemon. If a smoother read is wanted, publish a documented **cursor read-contract** (`--since <event_id>`) on the existing reader, or SSE on the *existing* `dashboard/server.py` — never a second long-running process. Gate any attestation framing on the signing keystone.

### E4 — `proof emit --from-file <f>` → **DO NOT add a new verb; fence an external-evidence ingress (with signing)**

- **Current state:** the `proof` concept is **already a first-class primitive** — `src/specify_cli/proof/events.py` defines a strict (`extra="forbid"`) schema, `PROOF_SCHEMA_VERSION = "1.0.0"`, 7 event types (`ProofItemRecorded`, `ReviewProofRecorded`, `TestEvidenceCaptured`, `SecurityScanCompleted`, `PullRequestLineageRecorded`, `HumanApprovalRecorded`), `ProofActor`/`ProofSubject`, idempotency keys, bounded envelopes — emitted internally via `sync/emitter.py::emit_proof_event` into the append-only `event_journal`. **Additionally**, a near-exact CLI ingress already exists: `spec-kitty profile-invocation complete --evidence <path>` promotes a file to a Tier-2 evidence artifact (`invocation/record.py::promote_to_evidence`), and two more evidence surfaces exist (`status/emit.py` done-evidence, the issue-matrix `evidence_ref`).
- **Duplication lens:** a bare `proof emit` risks a **4th parallel evidence store**. It should be an alias/thin extension of `profile-invocation complete --evidence`, not a new verb; the RFC's "keep it in your own store" fallback is itself a step backward from the richer canonical primitive.
- **Doctrine lens (the sharp risk):** today the actor is **self-declared and unauthenticated**, and there is **no signing**. An external emit is an unauthenticated write of a self-attesting record into governed state — it could forge a `HumanApprovalRecorded{approved}` or an approving `ReviewProofRecorded`. **Required guards:** (1) external-origin proofs stamped `actor_type: "service"` with a distinct source, **never admissible** as the reviewer `evidence` that unlocks `approved`/`done`; (2) reject `HumanApprovalRecorded` / approving verdicts from the external ingress entirely; (3) add a signature/integrity seal so external emits are *verifiable* rather than *forgeable* — which is also exactly the RFC's own value prop.
- **Recommendation:** the genuinely valuable net-new surface, but **not as `proof emit`**. Create (a) an **attestation-signing keystone** issue (prerequisite, unblocks E3+E4 value), and (b) a **governance-fenced external-evidence ingress** design issue (extend `profile-invocation complete --evidence`; observations-not-authority). Both under #645 / attestation.

### E5 — `session hooks register` → **DECLINE as framed (commands-only, via the existing registrar)**

- **Current state:** a hook-registration seam already exists — `HookRegistrar` Protocol + `ClaudeCodeHookRegistrar.register/unregister` own idempotent mutation of `.claude/settings.json` (`src/specify_cli/session_presence/hooks/`), invoked internally at `init`/`upgrade` to register spec-kitty's own `session-start`/`session-stop` **commands**. spec-kitty is the hook *callee*, not an instruction *injector*.
- **Architecture + doctrine lenses:** a `hooks register` that injects **standing instructions** inverts a bounded context (DIR-031) and, worse, **bypasses charter authority** — standing instructions *are* doctrine, and the charter is the single canonical authority for them (resolved through `charter context`). An external, per-harness instruction channel is a split-brain doctrine source that no `charter context` resolution knows about and no terminology/doctrine gate audits.
- **Recommendation:** **decline** the "external tool injects standing instructions" framing. If a side-car needs its shim present at session start, permit registering a **command** (the side-car's own hook binary) via a public extension of `ClaudeCodeHookRegistrar` — and route any *instruction content* through doctrine (a directive/paradigm) so the charter stays the single source. Optional narrow issue only if the commands-only extension is wanted.

## Summary & recommended tracker actions

| # | Endpoint | Verdict | Recommended action |
|---|----------|---------|--------------------|
| **E1** | `charter context --json` | Already ships | Small hardening issue: add `context_schema_version`, document as external contract (#645) |
| **E2** | `lanes write-scope --json` | **Adopt** | **Create issue** — thin read-only projection of `lane_for_wp()`/`write_scope` (#645). Highest leverage |
| **E4** | `proof emit` | Adopt-with-guards | **Create 2 issues:** attestation-signing keystone (prereq) + governance-fenced evidence ingress (extend `profile-invocation complete --evidence`; observations-not-authority) |
| **E3** | `event_journal subscribe` | Decline daemon | No push daemon. Optional small issue: `--since <cursor>` read-contract / SSE-on-dashboard. Gated on signing |
| **E5** | `session hooks register` | Decline as framed | No instruction-injection API. Optional narrow issue: commands-only `HookRegistrar` public extension |

**Cross-cutting:** the **attestation-signing seal** is the true keystone — it is the missing prerequisite that gives E3 and E4 their attestation value, and it should be sequenced first.

**Next step (operator):** decide which of the above issues to create, then close RFC #2497 with a summary of what was retained. This assessment does not close it.
