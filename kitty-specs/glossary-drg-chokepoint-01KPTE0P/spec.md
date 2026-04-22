# Glossary DRG Residence and Executor Chokepoint

**Phase 5 Foundation — Issue #467**
**Mission ID:** `01KPTE0P5JVQFWESWV07R0XG4M`
**Mission Slug:** `glossary-drg-chokepoint-01KPTE0P`
**Target Branch:** `main`
**Baseline:** `spec-kitty` `origin/main` @ `2144544b` (3.2.0a5, 2026-04-22)

---

## Problem / Opportunity

Spec Kitty's governance system already validates terminology at mission-primitive time (the existing `execute_with_glossary` hook in `doctrine.missions.glossary_hook`). But the newer profile-invocation path — `spec-kitty advise`, `ask`, and `do` — bypasses this check entirely. When a host LLM issues an invocation, it receives governance context assembled from the Doctrine Reference Graph, but no signal about whether the request text itself contains terms that conflict with the project glossary.

This gap means:
- Term drift in agent requests goes undetected until a human reviewer catches it.
- The DRG has a `GLOSSARY_SCOPE` node kind and `VOCABULARY` relation already declared, but no individual glossary term nodes to back them — the DRG graph currently has scope-level placeholders, not per-term addressable nodes.
- Hosts have no standard contract for what glossary observations to surface inline versus log quietly.

Phase 5 establishes the foundation: stable URN-addressed term nodes in the DRG, typed edges from action and profile nodes to their applicable terms, and a deterministic chokepoint wired directly into `ProfileInvocationExecutor` that fires on every invocation.

---

## Goal

Make every active glossary term a stable, DRG-addressable node (`glossary:<id>` URN). Wire typed `vocabulary` edges from action and profile nodes to applicable term nodes. Integrate a deterministic, non-blocking glossary chokepoint into `ProfileInvocationExecutor.invoke()` that returns a structured observation bundle to the host on every `advise` / `ask` / `do` invocation.

---

## User Scenarios and Testing

### Scenario 1 — Invocation with no glossary conflict (golden path)

A project operator runs `spec-kitty advise "summarise the WP status"`. The executor resolves the profile, assembles governance context, and runs the chokepoint against the active glossary terms for the resolved action. No conflicts are found. The `InvocationPayload` is returned with an empty `glossary_observations.conflicts` list. The host renders governance context normally — no inline glossary text appears. The JSONL trail records a zero-conflict observation.

**Test:** Assert that `payload.glossary_observations.conflict_count == 0` and that `payload.glossary_observations` is present (not `None`).

### Scenario 2 — High-severity conflict surfaced inline

A project has a glossary term "lane" (Spec Kitty meaning: parallel execution slot) that conflicts with informal usage. An operator issues `spec-kitty do "move the WP to a new lane (channel)"`. The chokepoint detects `SemanticConflict(severity=HIGH, conflict_type=INCONSISTENT)` for "lane". The `InvocationPayload.glossary_observations.high_severity` list contains the conflict. The host (Codex or gstack) reads the bundle and prepends an inline warning before presenting governance context to the LLM.

**Test:** Assert that `payload.glossary_observations.high_severity` contains the conflict record, and that the JSONL trail entry also contains it.

### Scenario 3 — Low/medium conflict logged only

An operator issues `spec-kitty ask planner "what tasks are planned for the current sprint"`. The word "sprint" has a medium-severity ambiguity conflict (Agile sprint vs. casual use). The chokepoint classifies it as medium. The `InvocationPayload.glossary_observations.high_severity` is empty; the conflict appears only in the JSONL trail entry for this invocation.

**Test:** Assert `payload.glossary_observations.high_severity == []` and that the trail JSONL for the invocation contains the medium-severity conflict.

### Scenario 4 — Chokepoint failure does not block invocation

A bug in the index builder (e.g., corrupt DRG YAML) causes the chokepoint to raise an exception. The executor catches it, attaches `GlossaryObservationBundle(error_msg="<description>", high_severity=[], conflicts=[])` to the payload, logs a warning, and returns the payload normally. The invocation completes; the host receives governance context without glossary observations.

**Test:** Assert that the executor completes without propagating the exception, that `payload.glossary_observations.error_msg` is non-empty, and that `payload.invocation_id` is still valid.

### Scenario 5 — Term index is rebuilt from DRG, no operator step required

After a new term is added to a seed file and the DRG is regenerated, the chokepoint's lazy index loader picks up the new term on the next invocation without any manual cache invalidation command from the operator.

**Test:** Assert that after adding a `glossary:<id>` node and a `vocabulary` edge to a test DRG and invalidating the index, the next chokepoint call finds the new term.

---

## Actors

| Actor | Role |
|-------|------|
| **ProfileInvocationExecutor** | Runtime-internal actor that runs the chokepoint synchronously during every profile invocation |
| **Glossary term author** (operator) | Maintains the seed files that populate the glossary store; indirectly controls which terms appear in the DRG |
| **Host** (Codex, gstack) | External LLM harness that reads `InvocationPayload` and decides how to surface high-severity observations inline |
| **DRG graph** | Passive data artifact whose `glossary:<id>` nodes and `vocabulary` edges drive the chokepoint's term index |
| **Invocation trail** (JSONL) | Passive sink for all chokepoint observations, including low/medium conflicts |

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Every active glossary term in the glossary store must have a corresponding `glossary:<id>` URN node in the DRG. The `<id>` segment must be stable across DRG regenerations for the same canonical term surface. | Approved |
| FR-002 | Each `glossary:<id>` DRG node must carry the term's canonical surface form as its `label` and a `NodeKind` of `GLOSSARY_TERM`. | Approved |
| FR-003 | The DRG must carry `vocabulary` edges from action nodes to all applicable `glossary:<id>` nodes. For this tranche, applicability follows scope: `spec_kitty_core` and `team_domain` terms are applicable to every action; `mission_local` and `audience_domain` terms are excluded from the static graph and are resolved at runtime from active mission context. | Approved |
| FR-004 | The DRG must expose a query that accepts an action URN and returns the complete set of `glossary:<id>` nodes reachable via outbound `vocabulary` edges (the action-scoped term set). | Approved |
| FR-005 | `ProfileInvocationExecutor.invoke()` must run the glossary chokepoint synchronously after governance-context assembly and before returning `InvocationPayload`. | Approved |
| FR-006 | The chokepoint must tokenize the request text and match tokens against the action-scoped term set using deterministic string matching and lemmatization only. No LLM calls are permitted in the hot path. | Approved |
| FR-007 | For each matched term, the chokepoint must classify any drift using the existing `SemanticConflict` model (`conflict_type`, `severity`, `confidence`). | Approved |
| FR-008 | The chokepoint result must be encapsulated in a `GlossaryObservationBundle` and attached to the `InvocationPayload` returned from `invoke()`. The bundle must always be present (never `None`), even on a clean invocation. | Approved |
| FR-009 | `GlossaryObservationBundle` must include: the list of matched term URNs, the list of high-severity `SemanticConflict` findings (surfaced to hosts), the list of all other findings (for trail-only writing), the count of tokens checked, and the chokepoint execution duration in milliseconds. | Approved |
| FR-010 | If the chokepoint raises any exception, the executor must catch it, emit a warning-level log entry, attach a `GlossaryObservationBundle` with `error_msg` set and empty conflict lists, and return the payload normally. The invocation is never blocked or interrupted by chokepoint failure. | Approved |
| FR-011 | The host contract for high-severity conflicts is: the host must render the `high_severity` conflict list as inline text in agent output before presenting the governance context to the LLM. | Approved |
| FR-012 | Low- and medium-severity findings must be written to the local invocation JSONL trail under the invocation's trail entry, but must not appear in `InvocationPayload.glossary_observations.high_severity`. | Approved |
| FR-013 | The `GlossaryChokepoint` class must be instantiatable without triggering any filesystem I/O. The term index must be lazily loaded on first use and cached for the lifetime of the executor instance. | Approved |
| FR-014 | The Codex and gstack host guidance documents must be updated to describe the `glossary_observations` field, the `high_severity` rendering contract, and the expected behavior when `error_msg` is set. | Approved |
| FR-015 | The term index must be rebuildable on demand via a function that scans the DRG for `glossary:<id>` nodes and their outbound `vocabulary` edges. No manual operator step is required to populate the index after DRG regeneration. | Approved |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Chokepoint end-to-end latency on a request text up to 2,000 words with a term index of up to 500 terms. | p95 ≤ 50ms | Approved |
| NFR-002 | Chokepoint overhead on a one-liner request text (≤50 words). | p95 ≤ 2ms | Approved |
| NFR-003 | Term index initial load from a DRG containing up to 500 glossary term nodes. | ≤ 20ms | Approved |
| NFR-004 | Unit test coverage for the `GlossaryChokepoint` class and `GlossaryObservationBundle` model. | ≥ 90% line coverage | Approved |
| NFR-005 | Static type checking gate for all new source files. | `mypy --strict` zero errors | Approved |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The chokepoint must never block or propagate an exception from within `ProfileInvocationExecutor.invoke()`. All exceptions from the chokepoint code path must be caught by the executor and result in an empty-bundle payload. | Approved |
| C-002 | No LLM calls, HTTP requests, subprocess invocations, or blocking I/O operations are permitted inside the chokepoint hot path. Deterministic string matching and lemmatization only. | Approved |
| C-003 | The `NodeKind.GLOSSARY_TERM` extension must be additive to the DRG schema. Existing `graph.yaml` files that contain no `glossary_term` nodes must still load and validate successfully without migration. | Approved |
| C-004 | The existing `GlossaryStore`, `GlossaryScope`, `TermSense`, and `SemanticConflict` models must not be modified in a breaking way. Any new fields must be additive. | Approved |
| C-005 | `InvocationPayload.__slots__` must be extended without breaking existing callers of `to_dict()`. The new `glossary_observations` slot must appear in the dict output. | Approved |
| C-006 | WP5.4 (dashboard glossary tile), WP5.5 (glossary entity pages, #532), and WP5.6 (`spec-kitty charter lint`, #533) are out of scope for this tranche and must not be implemented. | Approved |
| C-007 | Host LLM and harness own reading and generation. Spec Kitty owns routing, governance context assembly, glossary drift detection, validation, trail writing, and additive propagation. | Approved |
| C-008 | `mark_loaded=False` must continue to be passed to `build_charter_context()` in `ProfileInvocationExecutor.invoke()`. The chokepoint must not alter this invariant. | Approved |

---

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A `spec-kitty advise` / `ask` / `do` invocation on a project with active glossary terms completes and returns an `InvocationPayload` that includes a non-null `glossary_observations` bundle within the p95 ≤ 50ms chokepoint budget. |
| SC-002 | A high-severity `SemanticConflict` detected by the chokepoint appears as inline text in agent output for the Codex host path and the gstack host path, with no user configuration required. |
| SC-003 | When the chokepoint raises a simulated exception in tests, the invocation completes with a valid `invocation_id` and an `error_msg`-populated bundle — no exception escapes to the caller. |
| SC-004 | After DRG regeneration with a new `glossary:<id>` node and `vocabulary` edge, the next invocation's chokepoint finds the new term without any manual operator action. |
| SC-005 | All new source files pass `mypy --strict` and `ruff check`. New lines achieve ≥ 90% test coverage in the unit suite. |
| SC-006 | The existing invocation e2e test suite passes unchanged after this tranche lands. |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `GlossaryObservationBundle` | New data model returned by the chokepoint: matched term URNs, high-severity conflicts (surfaced to hosts), all conflicts (for trail), token count, duration, optional `error_msg`. |
| `GlossaryChokepoint` | New service class: accepts an action-scoped term set, tokenizes request text, matches terms, classifies conflicts, returns a `GlossaryObservationBundle`. Stateless except for the lazily loaded term index. |
| `GlossaryTermIndex` | Internal index structure built by scanning DRG `glossary:<id>` nodes and `vocabulary` edges. Cached per executor instance. Rebuildable without operator action. |
| `NodeKind.GLOSSARY_TERM` | New enum value added to the existing `NodeKind` StrEnum in `doctrine.drg.models`. Governs the `glossary:` URN prefix in DRG nodes. |
| `glossary:<id>` node | A DRG node representing one canonical glossary term. The `<id>` is derived deterministically from the term's canonical surface form. |
| `vocabulary` edge | An existing `Relation.VOCABULARY` edge in the DRG, extended to connect action/profile nodes to `glossary:<id>` term nodes. |
| Action-scoped term set | The set of all `glossary:<id>` nodes reachable from a given action URN via outbound `vocabulary` edges. |
| Invocation trail entry | The per-invocation JSONL record that receives all chokepoint observations, including low/medium conflicts not surfaced inline. |

---

## Assumptions

| # | Assumption |
|---|------------|
| A-1 | The p95 ≤ 50ms performance target is achievable for request texts up to 2,000 words and term indexes up to 500 terms using pure Python string matching and lemmatization. This will be validated in WP02 benchmarks; if not achievable, ADR-5 will be opened to revise the threshold. |
| A-2 | `mission_local` and `audience_domain` scoped terms are excluded from static DRG `vocabulary` edges in this tranche; they may be injected at runtime in a follow-on. This is acceptable for the Phase 5 foundation. |
| A-3 | The `<id>` segment in `glossary:<id>` URNs will be derived as a short stable hash of the canonical surface form (lowercased, trimmed). Collision probability is negligible for realistic glossary sizes (< 10,000 terms). |
| A-4 | The Codex and gstack host guidance updates are lightweight doc changes only; no new commands or API surfaces are required in those host codebases for this tranche. |

---

## Non-Goals and Deferred Follow-Ons

| Item | Disposition |
|------|-------------|
| WP5.4: Dashboard glossary tile | Deferred — future tranche |
| WP5.5: Glossary entity pages with two-way backlinks (issue #532) | Deferred — future tranche |
| WP5.6: `spec-kitty charter lint` graph-native decay detection (issue #533) | Deferred — future tranche |
| `spec-kitty explain` (issue #534) | Explicitly excluded from Phase 5 scope |
| Mission rewrite / retrospective contract (issue #468) | Out of scope |
| Versioning + migration hardening beyond additive backward-compat (issue #469) | Out of scope |
| `mission_local` / `audience_domain` terms in static DRG edges | Deferred — follow-on; runtime injection pattern to be designed separately |
| SaaS projection of glossary observations | Deferred — Tier 2 / Tier 3 propagation patterns exist but glossary bundle projection not in scope here |
| Entity-level graph lint, orphan detection | Deferred — WP5.6 territory |
| ADR-5 (formal p95 measurement record) | To be drafted and published as part of WP02 benchmarking |

---

## Domain Language

| Canonical term | Definition | Avoid |
|---------------|------------|-------|
| **DRG** | Doctrine Reference Graph — the typed, URN-addressed graph of doctrine artifacts | "doctrine graph", "doctrine graph YAML", "graph.yaml" (as a concept) |
| **chokepoint** | The synchronous middleware step in `ProfileInvocationExecutor.invoke()` that runs glossary checking | "filter", "validator", "gate", "hook" (when referring specifically to the executor-level integration) |
| **observation bundle** / `GlossaryObservationBundle` | The structured result returned by the chokepoint to the executor | "report", "findings", "result dict" |
| **term node** / `glossary:<id>` node | A DRG node representing one canonical glossary term | "glossary entry", "vocabulary item", "term record" |
| **vocabulary edge** | A `Relation.VOCABULARY` typed DRG edge from an action or profile node to a term node | "link", "association", "connection", "glossary edge" |
| **action-scoped term set** | All `glossary:<id>` nodes reachable from a given action node via `vocabulary` edges | "relevant terms", "applicable glossary", "term list for action" |
| **host** | The external LLM harness (Codex, gstack) that reads `InvocationPayload` | "client", "caller", "LLM" (when referring to the harness specifically) |
| **invocation trail** | The local JSONL log of invocation events; receives all chokepoint observations | "audit log", "event log", "invocation log" (use "trail" per `docs/trail-model.md`) |

---

## Minimum Implementation Sequence

Once this spec is approved, the following WP sequence delivers the smallest complete slice:

1. **WP01 — DRG term node model and index builder**
   Extend `NodeKind` with `GLOSSARY_TERM`. Build the index builder that traverses DRG `glossary:<id>` nodes and `vocabulary` edges. Write the ID derivation function. Update DRG loader and validator for backward-compat (no `glossary_term` nodes in existing YAML = no error). Define seed-file-to-DRG-node translation. Unit tests + mypy.

2. **WP02 — Chokepoint class, observation bundle, and executor integration**
   Implement `GlossaryObservationBundle` model. Implement `GlossaryChokepoint` with lazy index load, deterministic tokenizer + matcher, conflict classification via existing `SemanticConflict`. Wire into `ProfileInvocationExecutor.invoke()` with try/except safety wrapper. Benchmark chokepoint latency against p95 targets; draft ADR-5 with measurement data. Extend `InvocationPayload.__slots__` with `glossary_observations`. Unit + integration tests + mypy.

3. **WP03 — Observation surface and host guidance**
   Define severity-routing contract in code (`high` → `high_severity` list in bundle; `low`/`medium` → trail JSONL only). Write chokepoint observation to the invocation trail entry. Update Codex host guidance doc. Update gstack host guidance doc. Invocation e2e tests to verify existing suite still passes. Verify SC-002 manually or via stub host test.
