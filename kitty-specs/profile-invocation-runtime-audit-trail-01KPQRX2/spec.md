# Feature Specification: Profile Invocation Runtime and Audit Trail

| Field | Value |
|---|---|
| Mission ID | `01KPQRX2EVGMRVB4Q1JQBAZJV3` |
| Mission Slug | `profile-invocation-runtime-audit-trail-01KPQRX2` |
| Mission Type | `software-dev` |
| Target Branch | `main` |
| Created | 2026-04-21 |
| Status | Draft (specify) |

**Release target**: `3.2.0` — this is the major remaining product chunk for the `3.2.0` line, building on the already-landed `3.2.0a3` charter/doctrine baseline.
**Roadmap anchors**: Charter EPIC #461 · Phase 4 tracker #466 · WP4.6 event schema #495 · ADR-3 router design #519 · Minimal Viable Trail EPIC #701 · Workflow composition (out of scope) #682

---

## 1. Problem Statement

Phases 0–3 of the charter engineering EPIC are complete and merged. The charter synthesizer pipeline is operational: operators can synthesize project-local doctrine artifacts, and `charter context --action <x>` surfaces them during missions. The gap is that this governance machinery matters only at authoring time — it has no runtime effect. A host LLM that calls `spec-kitty implement WP03` receives no evidence that any profile was consulted, no governance context was injected for that action, and no record of the invocation exists anywhere.

The consequence is a system that is meticulous about building doctrine and careless about using it. Operators cannot see whether governance is actually applied. Auditors cannot verify which profile governed an action. The dashboard has no projection of what Spec Kitty was asked to do or by whom. Retrospective doctrine improvement has no data from which to learn.

Phase 4 closes this gap by introducing `ProfileInvocationExecutor` as a universal execution primitive, four CLI surfaces on top of it, a v1 invocation event schema, a local-first JSONL audit trail, and additive SaaS propagation. Together these make charter/doctrine visibly matter at every invocation. The smallest releaseable chunk is defined as: every Spec Kitty action that passes through the executor leaves one canonical invocation record; the host LLM gets the governance context it needs without Spec Kitty spawning a redundant LLM call; and the SaaS dashboard shows a coherent timeline of what happened and under which profile.

The central design question this mission answers is:

> **"What is the minimal viable trail that every Spec Kitty action should leave behind?"**

The answer is a three-tier model. Tier 1 (mandatory, every invocation): one `InvocationRecord` written locally before the host executes. Tier 2 (optional promotion, significant output): an `EvidenceArtifact` for invocations that produce checkable output. Tier 3 (optional promotion, durable project state): only invocations that change project-domain state (new spec, merged mission, accepted WP) promote to `kitty-specs/` or doctrine artifacts. The tiers are additive — every higher-tier promotion also has a Tier 1 record.

---

## 2. Scope

### In Scope

- `ProfileInvocationExecutor` as the single internal execution primitive for all profile-governed actions.
- Four CLI surfaces built on top of the executor:
  - `spec-kitty advise <request> [--profile <name>] [--json]`
  - `spec-kitty ask <profile> <request> [--json]`
  - `spec-kitty do <request> [--json]`
  - `spec-kitty profiles list [--json]`
- `spec-kitty profile-invocation complete --invocation-id <id>` to close an open invocation record.
- `spec-kitty invocations list [--profile <name>] [--limit N] [--json]` to surface recent records.
- The action-router decision seam: a defined interface that maps a request string to a `(profile_id, action)` pair, plus an ADR document (ADR-3, resolving issue #519) as a required deliverable.
- v1 `InvocationRecord` event schema with a ULID-keyed JSONL local writer.
- Additive SaaS propagation: background propagation using the existing CLI-SaaS contract, non-blocking, idempotency-keyed on `invocation_id`.
- The three-tier minimal viable trail policy, formally specified as a contract that all current and future Spec Kitty surfaces must honour.
- A governance context block injected into `advise`/`ask`/`do` responses, assembled via the existing `build_charter_context(action=...)` bootstrap path. In 3.2, context is action-scoped — the four bootstrap actions (`implement`, `review`, `plan`, `specify`) receive full DRG-backed doctrine; all other actions receive compact generic governance. Profile-specific context injection (where each profile's declared doctrine scope filters the DRG result differently) is explicitly deferred to a future phase. The `profile` parameter of `build_charter_context` is reserved but not yet consumed.

### Non-Goals (explicitly out of scope)

- **Reopening charter synthesis plumbing.** Phase 3 is the immutable baseline. The synthesizer pipeline, bundle manifest, DRG writer, and provenance store are fixed inputs to this phase.
- **Full Phase 5 glossary rollout.** Glossary as a first-class doctrine artifact (FR3 of EPIC #461) is deferred.
- **Profile-specific DRG context filtering.** In 3.2 the `profile` parameter of `build_charter_context` is unused (`_ = profile`). Making governance context genuinely profile-specific — where each profile's declared doctrine scope narrows or extends the DRG query — is deferred to a future phase after the bootstrap path proves stable.
- **Full Phase 6 mission rewrite / custom mission loader / retrospective contract.** FR4 of EPIC #461 and custom-mission-type loading are out of scope.
- **Workflow composition.** `.kittify/overrides/workflows/*.yaml` (issue #682) is explicitly deferred. The executor interface MUST document the extension seam for future workflow composition but MUST NOT implement it.
- **`intake` surface integration.** `spec-kitty intake` is temporarily outside the invocation audit trail. It remains a lightweight, harness-owned flow that does not route through `ProfileInvocationExecutor` in this phase. This is an explicit design decision, not an oversight. A future phase will define how intake events connect to the Tier 1 trail.
- **New `spec-kitty-events` or `spec-kitty-tracker` runtime primitives.** Downstream repos are consumers of the CLI-SaaS contract, not authors of new primitives in this chunk.
- **Retrospective doctrine update from invocation data.** Post-mission retrospective contract (FR4) is a Phase 6 concern.
- **Invocation-trail integration for existing pre-Phase-4 actions.** Actions taken before this phase is deployed produce no retroactive records.

---

## 3. User Scenarios & Acceptance

### Actors

- **Host LLM / Agent Harness**: a running AI agent (Claude Code, Codex, Cursor, etc.) that delegates routing and governance context to Spec Kitty rather than resolving them internally.
- **Operator**: a developer who invokes `spec-kitty ask <profile> <request>` or `spec-kitty do <request>` directly from a terminal.
- **Downstream Consumer**: any process that reads `.kittify/events/profile-invocations/` or queries the invocation list command.
- **SaaS Dashboard User**: a human reviewing the timeline of profile invocations from the web dashboard.
- **Profile Registry Owner**: the person (or automated process) that maintains the set of profiles available in `.kittify/profiles/`.

### Primary Flows

**US-1 — Host-LLM advise/complete cycle**
*Given* a project with at least one profile in the registry and a running charter context,
*when* a host-LLM agent calls `spec-kitty advise "implement WP03" --json`,
*then* Spec Kitty resolves the `(profile, action)` pair via the action router, assembles the governance context block from the DRG, writes an open `InvocationRecord` to the local event log, and returns a JSON payload containing `invocation_id`, the resolved profile, the resolved action, and the governance context block — without spawning any LLM call of its own.
*And when* the host LLM calls `spec-kitty profile-invocation complete --invocation-id <id> --outcome done`,
*then* the `InvocationRecord` is closed with `completed_at` and `outcome`, and if a SaaS token is configured, the closed record is propagated in the background.

**US-2 — Named-profile direct invocation**
*Given* a project with a profile named `pedro`,
*when* the operator calls `spec-kitty ask pedro "fix this authentication bug"`,
*then* Spec Kitty looks up Pedro's profile, resolves the action from the request, assembles Pedro's governance context, writes an open `InvocationRecord`, and returns the governance context block with the `invocation_id`. The operator (or their agent) uses the returned context to guide their work and may close the record with `profile-invocation complete`.

**US-3 — Anonymous dispatch via action router**
*Given* a project with multiple profiles,
*when* the operator calls `spec-kitty do "write a spec for the payment module"`,
*then* the action router determines which profile is most appropriate for that request (resolving ADR-3), assembles that profile's governance context, writes an open `InvocationRecord`, and returns the routing decision with the governance context block.

**US-4 — Profile discovery**
*Given* any project with profiles configured,
*when* the operator calls `spec-kitty profiles list --json`,
*then* the command returns a JSON array containing each profile's `profile_id`, `friendly_name`, and list of declared capabilities or action domains.

**US-5 — Invocation history review**
*Given* a project with at least three prior invocation records in the local event log,
*when* the operator calls `spec-kitty invocations list --json --limit 10`,
*then* the command returns the ten most recent `InvocationRecord` entries in descending `started_at` order, including closed and unclosed records, with all v1 schema fields present.

**US-6 — Offline invocation (no SaaS)**
*Given* a project with no SaaS token configured (or with the SaaS connection unavailable),
*when* the operator calls `spec-kitty ask pedro "review WP05"`,
*then* the invocation completes successfully, the local `InvocationRecord` is written, and no error or warning about SaaS is surfaced to the operator. When SaaS connectivity is later restored, no automatic retroactive propagation occurs (propagation is a per-invocation background action, not a backfill service).

**US-7 — SaaS propagation (online)**
*Given* a project with a valid SaaS token and connectivity,
*when* the operator calls `spec-kitty ask cleo "summarize the mission"` and then closes the record,
*then* both the `started` and `completed` invocation events are propagated to SaaS in the background within 10 seconds of the local write, using the `invocation_id` as the idempotency key. A subsequent repeat propagation of the same `invocation_id` produces no duplicate on the SaaS side.

**US-8 — SaaS propagation failure is non-blocking**
*Given* a project with a SaaS token that is currently returning 5xx errors,
*when* the operator calls `spec-kitty advise "plan WP02"`,
*then* the local `InvocationRecord` is written and the governance context block is returned within the normal latency window. The SaaS propagation failure is logged locally for operator diagnosis but does not surface as a CLI error, does not block the command, and does not affect the returned governance context.

**US-9 — Router ambiguity is transparent**
*Given* a project where the action router cannot unambiguously resolve a request to a `(profile, action)` pair,
*when* the operator calls `spec-kitty do "help me"`,
*then* the command returns a structured error naming the candidate profiles and actions, with guidance on using `spec-kitty ask <profile>` to be explicit. No `InvocationRecord` is written for an unrouted request.

### Edge Cases

- EC-1: A request is routed to a profile that no longer exists in the registry — the executor fails closed with a structured error naming the missing profile; no `InvocationRecord` is written.
- EC-2: Charter is not yet synthesized (no `.kittify/charter/charter.md`) — governance context assembly returns a minimal text indicating context is unavailable. The executor continues, writes the `InvocationRecord` with `governance_context_available=false`, and exits 0 with a warning. The record is auditable even without governance context. Operators are directed to run `spec-kitty charter interview` then `spec-kitty charter generate`. (Contrast with EC-1: missing profile always fails closed; missing charter degrades gracefully.)
- EC-3: `profile-invocation complete` is called with an `invocation_id` that has already been closed — the command returns a structured warning (already closed, exit 0); the original record is not mutated.
- EC-4: `profile-invocation complete` is called with an `invocation_id` that does not exist in the local log — the command returns a structured error (exit 1); no write occurs.
- EC-5: The local events directory (`.kittify/events/`) does not exist when a first invocation is attempted — the executor creates it, then writes the record.
- EC-6: Two concurrent invocations of `advise` for the same profile — each generates a distinct ULID `invocation_id` and writes to distinct JSONL files; no collision occurs.
- EC-7: An operator calls `spec-kitty advise` with `--profile <name>` but the profile does not match any registered profile — the command returns a structured error naming the missing profile and listing available profiles; no invocation is started.

---

## 4. Requirements

### 4.1 Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The `ProfileInvocationExecutor` SHALL be the single internal execution primitive through which all CLI surfaces (`advise`, `ask`, `do`) route profile-governed invocations. No CLI surface SHALL bypass the executor to write invocation records directly. | Accepted |
| FR-002 | `spec-kitty profiles list [--json]` SHALL enumerate all profiles available in the current project's profile registry, returning at minimum: `profile_id`, `friendly_name`, and the list of action domains or capabilities declared by each profile. | Accepted |
| FR-003 | `spec-kitty advise <request> [--profile <name>] [--json]` SHALL return: `invocation_id`, resolved `profile_id`, resolved `action`, and the assembled governance context block. The command SHALL NOT spawn any LLM call. | Accepted |
| FR-004 | `spec-kitty ask <profile> <request> [--json]` SHALL be a named-profile shorthand equivalent to `spec-kitty advise <request> --profile <profile>`. | Accepted |
| FR-005 | `spec-kitty do <request> [--json]` SHALL route the request through the action router (without a caller-supplied profile hint), resolve `(profile_id, action)`, and return the same payload as `advise`. | Accepted |
| FR-006 | `spec-kitty profile-invocation complete --invocation-id <id> [--outcome <status>] [--evidence <path>]` SHALL close the named open `InvocationRecord` with `completed_at`, `outcome`, and optional `evidence_ref`. | Accepted |
| FR-007 | `spec-kitty invocations list [--profile <name>] [--limit N] [--json]` SHALL return recent `InvocationRecord` entries from the local event log in descending `started_at` order, filtered by profile when `--profile` is supplied. | Accepted |
| FR-008 | Every invocation through `advise`, `ask`, or `do` SHALL write exactly one open `InvocationRecord` to the local event log before returning to the caller. The record SHALL be written even if `profile-invocation complete` is never called. | Accepted |
| FR-009 | An `InvocationRecord` event that fails to write locally SHALL cause the CLI command to return a non-zero exit code with a structured error. The governance context block SHALL NOT be returned if the local write fails. | Accepted |
| FR-010 | The action router SHALL expose a defined interface seam that accepts a request string and an optional profile hint, and returns a `(profile_id, action)` resolution or a structured ambiguity/no-match error. The router implementation choice SHALL be documented in ADR-3, which is a required deliverable artifact of this mission (resolving issue #519). | Accepted |
| FR-011 | When the action router cannot unambiguously resolve a request, it SHALL return a structured error listing candidate profiles and actions; it SHALL NOT silently fall back to any default profile. | Accepted |
| FR-012 | The governance context block returned by `advise`, `ask`, and `do` SHALL be assembled by calling `build_charter_context(repo_root, action=<canonical_action>, mark_loaded=False)`. In 3.2, the `profile` parameter is passed but not consumed by that function (it is reserved). Bootstrap actions (`implement`, `review`, `plan`, `specify`) return full DRG-backed context; all other canonical actions return compact generic governance. The governance context hash SHALL be recorded in the `InvocationRecord`. | Accepted |
| FR-013 | `InvocationRecord` events SHALL be written to `.kittify/events/profile-invocations/<invocation_id>.jsonl` as append-only JSONL. The filename is keyed solely on `invocation_id` so that `profile-invocation complete` requires only `--invocation-id` with no additional locator arguments. | Accepted |
| FR-014 | The v1 `InvocationRecord` schema SHALL include at minimum: `invocation_id` (ULID), `profile_id`, `action`, `request_text`, `governance_context_hash`, `actor`, `started_at` (ISO-8601), `completed_at` (ISO-8601 or null), `outcome` (null / done / failed / abandoned), `evidence_ref` (null or path). | Accepted |
| FR-015 | SaaS propagation SHALL be additive and non-blocking: when a SaaS token is configured and connectivity is available, invocation events SHALL be propagated in the background after local write. A propagation failure SHALL NOT block the CLI command or affect the returned payload. | Accepted |
| FR-016 | SaaS propagation SHALL use `invocation_id` as the idempotency key. Propagating the same record twice SHALL produce no duplicate on the SaaS side. | Accepted |
| FR-017 | The minimal viable trail policy SHALL be implemented as a formal contract with three tiers: Tier 1 (every invocation) — one `InvocationRecord` written locally before the executor returns; Tier 2 (significant output) — an optional `EvidenceArtifact` for invocations that produce checkable output; Tier 3 (durable project state) — promotion to `kitty-specs/` or doctrine artifacts only when the invocation changes project-domain state. Higher-tier promotions SHALL also have a Tier 1 record. | Accepted |
| FR-018 | `spec-kitty intake` SHALL NOT be connected to the `ProfileInvocationExecutor` or the invocation audit trail in this phase. This is an explicit design decision. The executor interface SHALL document the integration seam for a future phase without implementing it. | Accepted |
| FR-019 | The `ProfileInvocationExecutor` interface SHALL include documented extensibility hooks for future workflow composition (issue #682) without implementing them. The hooks SHALL be specified as no-op pass-throughs that a future workflow override can intercept. | Accepted |

### 4.2 Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | End-to-end latency from `spec-kitty advise <request>` invocation to returned governance context block (including local event write), measured with a warmed DRG and a minimal project. | < 500 ms on a developer workstation. | Accepted |
| NFR-002 | CLI exit-code reliability: `advise`, `ask`, and `do` SHALL return a non-zero exit code on any failure that prevents an `InvocationRecord` from being written or a governance context from being assembled. | 100% of failure paths produce non-zero exits. | Accepted |
| NFR-003 | SaaS propagation latency (background, online): time from local write to SaaS acknowledgment for a single invocation event. | < 10 seconds under normal connectivity. | Accepted |
| NFR-004 | Test coverage for all new executor, router seam, event-writer, and CLI surface code. | ≥ 90% line coverage, consistent with charter policy. | Accepted |
| NFR-005 | Static type-check conformance of all new modules. | `mypy --strict` passes with zero errors. | Accepted |
| NFR-006 | `InvocationRecord` entries SHALL be append-only and immutable after initial write. No code path SHALL overwrite or delete a written record except a well-defined close operation that appends the completion fields. | 0 in-place mutations, verified by writer tests. | Accepted |
| NFR-007 | Network calls from the automated test suite (excluding SaaS integration tests that are explicitly tagged and excluded from CI). | 0 untagged network calls in CI. | Accepted |
| NFR-008 | `invocations list` query latency for the 100 most recent records when the event log contains 10,000 entries. | < 200 ms. | Accepted |

### 4.3 Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The host LLM / agent harness owns reading governance context and generating work. Spec Kitty owns routing, governance context assembly, validation, event writing, provenance, DRG checks, staging/promotion, and runtime injection. No CLI surface SHALL embed a vendor-specific LLM client. | Accepted |
| C-002 | `invocation_id` SHALL use ULID format, consistent with the mission identity model (CLAUDE.md, mission 083). | Accepted |
| C-003 | SaaS propagation SHALL use the existing CLI-SaaS contract published in `spec-kitty-saas`. No new contract versions SHALL be introduced in this phase; the existing `ProfileInvocationStarted` and `ProfileInvocationCompleted` envelope types are the target. | Accepted |
| C-004 | Workflow composition (`.kittify/overrides/workflows/*.yaml`, issue #682) SHALL NOT be implemented. The executor SHALL document the extension seam only. | Accepted |
| C-005 | `spec-kitty intake` is explicitly out of scope for this phase's invocation trail. The executor MUST NOT attempt to instrument or intercept intake flows. | Accepted |
| C-006 | Phase 3 charter synthesis plumbing (synthesizer pipeline, bundle manifest, DRG writer, provenance store) is fixed baseline. This mission SHALL NOT modify those surfaces except to call them as consumers. | Accepted |
| C-007 | Phase 5 glossary rollout and Phase 6 mission rewrite / custom mission loader / retrospective contract are out of scope. | Accepted |
| C-008 | ADR-3 (issue #519) MUST be resolved and produced as a written artifact by this mission before the action router is implemented. Routing logic developed before the ADR is accepted is a violation of DIRECTIVE_003. | Accepted |
| C-009 | The bulk-edit occurrence-classification guardrail does not apply to this mission; it introduces new identifiers and new code paths, not cross-file renames of existing identifiers. | Accepted |
| C-010 | `InvocationRecord` events written to `.kittify/events/profile-invocations/` are local-first. No invocation event SHALL be written only to SaaS without a corresponding local record. | Accepted |

---

## 5. Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | An operator or host LLM calling `spec-kitty advise "implement WP03" --json` receives a JSON payload containing `invocation_id`, resolved profile, resolved action, and governance context block within 500 ms, and a corresponding `InvocationRecord` exists in `.kittify/events/profile-invocations/`. |
| SC-002 | `spec-kitty ask pedro "fix this bug" --json` returns an equivalent payload scoped to the `pedro` profile and a corresponding `InvocationRecord` exists locally. |
| SC-003 | `spec-kitty do "write a spec for the payment module" --json` routes via the action router (as specified in ADR-3) and returns a governance-context payload; routing choice is traceable to the ADR. |
| SC-004 | `spec-kitty profiles list --json` returns a valid JSON array for any project with at least one configured profile. |
| SC-005 | `spec-kitty profile-invocation complete --invocation-id <id>` closes an open record; a subsequent `invocations list` shows the record with a non-null `completed_at`. |
| SC-006 | An operator calling `spec-kitty advise` with no SaaS token configured receives no error, warning, or latency degradation related to SaaS absence. |
| SC-007 | With a valid SaaS token, both `started` and `completed` invocation events propagate to SaaS within 10 seconds of local write; duplicate propagation produces no duplicates on the SaaS side. |
| SC-008 | SaaS propagation failure (simulated 5xx) does not cause `advise` or `ask` to return a non-zero exit code or a degraded governance context block. |
| SC-009 | ADR-3 is produced as a written artifact in the mission's `kitty-specs/` directory before the action router WP is approved. |
| SC-010 | 100% of invocations through `advise`, `ask`, and `do` produce a Tier 1 `InvocationRecord` in the local event log, verified by integration tests covering the full executor path. |
| SC-011 | `spec-kitty intake` flows produce no `InvocationRecord` entries and no references to `ProfileInvocationExecutor` in this phase. |
| SC-012 | A fresh contributor can read the three-tier minimal viable trail policy from the spec and explain which tier applies to a given action type without consulting implementation code. |

---

## 6. Key Entities

- **ProfileInvocationExecutor** — the single internal execution primitive: accepts `(request, profile_hint?, governance_context_source)`, resolves `(profile_id, action)` via the action router, assembles the governance context block, writes the Tier 1 `InvocationRecord`, and returns the invocation payload to the caller. All CLI surfaces delegate to this.
- **InvocationRecord** — the v1 minimal audit record for every profile-governed invocation. Fields: `invocation_id` (ULID), `profile_id`, `action`, `request_text`, `governance_context_hash`, `actor`, `started_at`, `completed_at`, `outcome`, `evidence_ref`. Written as JSONL to `.kittify/events/profile-invocations/<profile_id>-<invocation_id>.jsonl`.
- **ActionRouter** — the component that maps `(request_text, profile_hint?)` to `(profile_id, action)`. Exposes a defined interface seam; the implementation choice is ADR-3's responsibility.
- **GovernanceContextBlock** — the assembled bundle of doctrine, tactics, directives, and constraints relevant to a specific `(profile_id, action)` pair. Assembled from the DRG; its SHA-256 hash is stored in the `InvocationRecord` for provenance.
- **Profile** — a named agent identity defined in `.kittify/profiles/`. Has a `profile_id`, `friendly_name`, declared action domains, and governance scope.
- **ProfileRegistry** — the index of profiles available in the current project (sourced from `.kittify/profiles/`). Read by `profiles list` and by the executor during profile resolution.
- **EvidenceArtifact** — a Tier 2 promoted record: a structured document (Markdown or YAML) written to `.kittify/evidence/<invocation_id>/` for invocations whose output is checkable by a reviewer. Not every invocation produces one.
- **InvocationSaaSPropagator** — the background component that picks up locally written `InvocationRecord` entries and propagates them to SaaS using the existing CLI-SaaS contract. Non-blocking; idempotency-keyed on `invocation_id`.
- **MinimalViableTrailPolicy** — the three-tier contract (Tier 1 mandatory, Tier 2–3 optional promotions) that governs what artifacts every Spec Kitty action must leave behind. A formal specification, not a convention.

---

## 7. Assumptions

- A-1 — The Phase 3 charter synthesis pipeline has run for the project; at least one profile exists in `.kittify/profiles/` and at least one DRG layer is present under `.kittify/doctrine/`. Projects with no profiles configured receive a structured error on `advise`/`ask`/`do` pointing to `spec-kitty charter synthesize`.
- A-2 — The existing `charter context --action <x>` mechanism (which reads `(profile, action)` from the DRG) can be called programmatically from the executor to assemble the governance context block, without a new context-loading seam.
- A-3 — The CLI-SaaS contract published in `spec-kitty-saas` already includes `ProfileInvocationStarted` and `ProfileInvocationCompleted` envelope types (confirmed in issue #495 as of April 13, 2026). This phase uses them as-is; any schema gap surfaces during plan and is treated as a blocking dependency.
- A-4 — The `intake` surface is implemented as a distinct code path that does not share entry points with `advise`/`ask`/`do`. No refactoring of intake is required to keep it outside the executor.
- A-5 — ADR-3 will be resolved during the plan phase by examining the three candidate approaches (deterministic table, LLM call, hybrid) and selecting one based on the smallest-viable-chunk criterion. The spec does not pre-empt this choice; the action router seam is defined independently of the implementation.
- A-6 — The `.kittify/events/` directory hierarchy is created on demand; no migration or pre-creation of the directory is needed for existing projects.
- A-7 — Concurrent invocations (multiple agents calling `advise` simultaneously) are safe by virtue of ULID-keyed files; no locking mechanism is needed for the Tier 1 JSONL write.

---

## 8. Dependencies

- **Phase 3 charter synthesis baseline** (PRs #677, #690, #694, now on `main`) — hard dependency; executor reads profiles and DRG from the synthesis outputs. If no synthesis has run, the executor must produce a clear actionable error, not a silent failure.
- **Existing `charter context --action <x>` mechanism** — hard dependency for governance context assembly. Extending or modifying this mechanism is out of scope; consuming it is in scope.
- **CLI-SaaS contract** (`spec-kitty-saas`, `ProfileInvocationStarted` / `ProfileInvocationCompleted`) — hard dependency for SaaS propagation. The plan phase must verify the exact schema fields; any mismatch is a blocking issue.
- **ADR-3 router design** (issue #519) — blocking dependency for the `do` command and the `advise` path when no `--profile` hint is supplied. The ADR must be written and accepted before the router WP can proceed.
- **ULID library** — same dependency already in use for mission identity (mission 083); no new package acquisition needed.
- **DIRECTIVE_003** (decision documentation) — governance dependency: material decisions (ADR-3, trail tier definitions) must be captured before implementation.

---

## 9. Work Package Scope Anchor

This is a scope anchor, not an implementation plan. Concrete module design, file layout, and sequencing are the job of `/spec-kitty.plan` and `/spec-kitty.tasks`.

| WP | Title | Scope summary |
|----|-------|---------------|
| WP4.1 | `ProfileInvocationExecutor` core + `profiles list` | Executor skeleton, profile registry reader, `profiles list` CLI. All subsequent WPs depend on the executor seam. |
| WP4.2 | ADR-3: action router decision + router implementation | Produce ADR-3 document, implement the decided router, integrate into executor's `do` path. Must land before WP4.5. |
| WP4.3 | `advise` + `profile-invocation complete` CLI surface | Named and anonymous advise flows, completion command, invocation payload shape. Depends on WP4.1. |
| WP4.4 | `ask <profile> <request>` CLI surface | Named-profile shorthand. Small WP; depends on WP4.3 seam. |
| WP4.5 | `do <request>` CLI surface | Anonymous dispatch via router. Depends on WP4.2 (router). |
| WP4.6 | v1 event schema + local JSONL writer | `InvocationRecord` Pydantic model, JSONL writer, minimal viable trail tier contract as code. Depends on WP4.1. |
| WP4.7 | SaaS propagation (additive, non-blocking) | Background propagator using existing CLI-SaaS contract, idempotency key, offline passthrough. Depends on WP4.6. |
| WP4.8 | `invocations list` CLI surface + skill pack updates | Query command over local event log, update harness skill packs to document `advise`/`ask`/`do`. Depends on WP4.6. |

Likely parallelism: WP4.3 / WP4.4 can proceed in parallel with WP4.2 once WP4.1 is stable. WP4.6 can proceed in parallel with WP4.2–4.5 once WP4.1 defines the invocation payload shape. WP4.7 depends only on WP4.6. WP4.8 depends only on WP4.6.

---

## 10. Validation Strategy

- **Executor and router seam (WP4.1 / WP4.2)** — unit tests against the executor with fixture profiles and a fixture router; shape/schema assertions on invocation payloads; verify no LLM call is made in any executor test path.
- **CLI surfaces (WP4.3–4.5 / WP4.8)** — integration tests using `typer` test runner; assert exit codes, JSON output shapes, and that each surface delegates to the executor (not a direct writer).
- **Event writer and schema (WP4.6)** — unit tests for `InvocationRecord` Pydantic validation, JSONL round-trip read/write, append-only invariant (no in-place mutation), and ULID uniqueness under concurrent fixture invocations.
- **Three-tier trail policy** — table-driven tests covering: (a) plain invocation → Tier 1 only; (b) invocation with evidence → Tier 1 + Tier 2; (c) spec-creating invocation → all three tiers. Negative: (d) completed intake flow → zero `InvocationRecord` entries.
- **SaaS propagation (WP4.7)** — unit tests with a mocked SaaS client; assert non-blocking behaviour when client returns 5xx; assert idempotency key is set on every propagation call; assert local write is NOT blocked if propagator is absent.
- **ADR-3 acceptance gate** — CI check that the ADR-3 document exists at the expected path in `kitty-specs/` before the action router WP can be merged. Enforced via pre-merge spec-kitty review gate.
- **Performance envelopes (NFR-001 / NFR-008)** — lightweight timing assertions in integration tests; CI-tolerant thresholds.
- **`intake` non-interference** — test that calls to `spec-kitty intake` produce no entries in `.kittify/events/profile-invocations/`.

---

## 11. Risks and Sequencing Constraints

- **R-1: ADR-3 router decision delays** — if ADR-3 takes longer than expected, WP4.5 (`do`) is blocked. Mitigation: WP4.1–4.4 / 4.6 / 4.8 can be completed independently of WP4.2. The `advise --profile <name>` path is fully functional without the router. Operators can use `ask` directly while the router decision is pending.
- **R-2: CLI-SaaS contract schema gap** — the plan phase must confirm that `ProfileInvocationStarted` and `ProfileInvocationCompleted` in the existing contract carry all `InvocationRecord` v1 fields. A mismatch discovered during WP4.7 would require a contract negotiation with `spec-kitty-saas`, which is out of scope. Mitigation: contract schema validation is a WP4.7 entry gate check; surface any gap as a plan-phase blocking issue, not a runtime surprise.
- **R-3: DRG availability at advise time** — if the DRG is not yet synthesized (fresh project, Phase 3 not yet run), `advise` fails. This is expected behaviour per A-1, but the error message must be actionable. Mitigation: executor's profile resolution path includes a clear "no profiles found — run `charter synthesize`" error.
- **R-4: Non-blocking propagation reliability** — background propagation that silently fails and never retries creates invisible drift between local and SaaS state. Mitigation: propagation failures are logged to `.kittify/events/propagation-errors.jsonl` for operator diagnosis; a future phase may add retry logic.
- **R-5: Intake scope creep** — pressure to instrument intake in this phase would delay and complicate the executor/trail contract. Mitigation: FR-018 and C-005 are hard constraints; any intake integration request is deferred to the explicitly-named future phase.
- **R-6: Trail tier policy ambiguity** — if Tier 2 and Tier 3 promotion criteria are left vague, implementors will make inconsistent choices. Mitigation: FR-017 specifies the tier definitions; WP4.6 produces a formal `MinimalViableTrailPolicy` code artifact (not just a doc) that all surfaces import.

Sequencing constraint (spec-level): WP4.1 must land first. WP4.2 (ADR-3 + router) must be accepted before WP4.5 (`do`) begins. WP4.6 (event schema) can proceed in parallel with WP4.2–4.5 but must land before WP4.7 or WP4.8. WP4.7 and WP4.8 are independent of each other and can proceed in parallel.

---

## 12. Recommended Mission Shape

Realistic implementation scale for this chunk:

- 8 work packages, roughly 4–5 parallelisable after WP4.1 lands.
- Scope spans: `src/specify_cli/invocation/` (new package — name is a plan-phase decision), `src/specify_cli/cli/commands/` (new commands: `advise`, `ask`, `do`, `profiles`, `invocations`), `src/specify_cli/events/` (event writer, SaaS propagator), and skill-pack docs under `.agents/skills/`.
- ADR-3 produced as `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-action-router.md` or equivalent.
- No changes required to Phase 3 synthesis, bundle manifest, or DRG writer.
- No migration of existing projects; new directory layout (`.kittify/events/profile-invocations/`) is created on demand.
- Expected review volume: moderate to high. WP4.1 and WP4.2 carry the highest review cost (executor shape, router decision); WP4.6 carries moderate cost (schema contract, trail tier policy). WP4.3–4.5 / 4.7–4.8 are largely mechanical once those two WPs are right.

---

## 13. Review & Acceptance

The specification is ready for `/spec-kitty.plan` when:

- Requirements quality checklist passes (see `checklists/requirements.md`).
- No `[NEEDS CLARIFICATION]` markers remain.
- The three-tier minimal viable trail policy (FR-017) is unambiguous.
- ADR-3 is noted as a required mission deliverable (not pre-empted in this spec).
- Scope, non-goals, and deferred items (`intake`, Phase 5, Phase 6, workflow composition) are unambiguous.
- Architecture boundary (host LLM owns generation; Spec Kitty owns routing, governance, eventing, provenance) is stated as a testable constraint (C-001).
