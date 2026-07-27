# Tasks: Event sync — preserve local events & track per-target drains

**Mission**: `event-sync-retention-delivery-01KVYWRG` (#2124)
**Branch**: `mission/event-sync-retention-delivery` (single_branch topology)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contract**: [contracts/event-sync-delivery-contract.md](./contracts/event-sync-delivery-contract.md)

> **How this maps to the plan.** The plan's Implementation Concerns (IC-00 … IC-09) are *concerns, not work packages*. This file translates them into 12 work packages whose `owned_files` are **disjoint** (the finalize-tasks ownership rule). The deferred "a" concerns (IC-02a coalescing, IC-05a terminal-failed) are folded so they don't collide on a shared module — see the per-WP notes. **IC-09 (SaaS `/health` metadata) is intentionally out of MVP scope** (cross-repo, gated on a `spec-kitty-saas` change, advisory per C-004).

## Concern → Work Package map

| Plan concern | Work package(s) |
|---|---|
| IC-00 target authority | WP01 (resolver), WP02 (rewire surfaces) |
| IC-01 domain scaffolding | folded into WP03 (event_journal) + WP04 (delivery interfaces) |
| IC-02 event journal | WP03 |
| IC-02a coalescing | WP08 (seam built in WP03) |
| IC-03 target registry | WP04 |
| IC-04 delivery ledger | WP05 |
| IC-04a DeliveryReceiver | WP06 |
| IC-05 dispatcher | WP07 |
| IC-05a terminal-failed | folded into WP05 (state) + WP07 (selection) |
| IC-06 EventSyncConfig | WP09 |
| IC-07 migration | WP10 |
| IC-08 status / gc / archive | WP11 (logic) + WP12 (CLI) |
| IC-09 SaaS /health metadata | **out of scope** (follow-on) |

## Subtask Index *(reference only — not a tracking surface; `[P]` = parallel-safe)*

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | `ResolvedSyncTarget` model (8 contract fields) | WP01 | [P] | [D] |
| T002 | Resolve config.toml + `SPEC_KITTY_SAAS_URL`; compute `override_mode` | WP01 | | [D] |
| T003 | Derive `derived_queue_scope` + `queue_db_path` (derived, never a selector) | WP01 | | [D] |
| T004 | `active_queue_scope_status` = absent/matches/stale_non_authoritative | WP01 | | [D] |
| T005 | Split-brain guard: env vs config → whole-process override or fail/warn pre-network | WP01 | | [D] |
| T006 | Resolver unit tests (fields, disagreement, stale) | WP01 | | [D] |
| T007 | Rewire `sync/config.py` + `sync/runtime.py` onto resolver | WP02 | | [D] |
| T008 | Rewire `auth/config.py` + `saas/readiness.py` | WP02 | | [D] |
| T009 | Rewire `sync/preflight.py` + `sync/owner.py` (scope derived) | WP02 | | [D] |
| T010 | Rewire `sync/tracker_client_glue.py` to the resolved URL | WP02 | | [D] |
| T011 | One resolved target across WebSocket/tracker/scope/status | WP02 | | [D] |
| T012 | Wiring tests (no split-brain; stale scope ignored) | WP02 | | [D] |
| T013 | Journal schema + Event record model | WP03 | [D] |
| T014 | Append-only journal store (producer-scoped, never deletes) | WP03 | | [D] |
| T015 | Coalescing **seam** (default no-op; filled by WP08) | WP03 | | [D] |
| T016 | Capture-first gating at emit layer (write before gates) | WP03 | | [D] |
| T017 | Record `drain_blocked_reason`/audit when a gate blocks delivery | WP03 | | [D] |
| T018 | Never silently drop Teamspace-bound facts (journal-side guard) | WP03 | | [D] |
| T019 | Tests: durable under disabled-sync/missing-auth; no-coalescing invariant | WP03 | | [D] |
| T020 | Stand up `delivery/` package + `interfaces.py` protocols | WP04 | [D] |
| T021 | Target identity: canonical URL + `UNIQUE(url_hash, team_slug, user_email)` | WP04 | | [D] |
| T022 | Canonicalize endpoint URL deterministically | WP04 | | [D] |
| T023 | Record (not key on) deployment metadata as provenance | WP04 | | [D] |
| T024 | Advisory reset-detection on metadata change (no identity fork) | WP04 | | [D] |
| T025 | Tests: identity uniqueness; deployment_id churn; reset-detection | WP04 | | [D] |
| T026 | Ledger schema (event×target; grow-to-many-targets, no schema break) | WP05 | [P] |
| T027 | success/duplicate → terminal-success rows (never delete journal) | WP05 | |
| T028 | pending/rejected/failed_transient ledger states | WP05 | |
| T029 | Terminal-failed state (FR-015 storage; payload retained) | WP05 | |
| T030 | Selection query: undelivered-for-target, excluding terminal-failed | WP05 | |
| T031 | Delivered-anywhere query (consumed by WP08) | WP05 | |
| T032 | Index design + state-transition + idempotent-redelivery tests | WP05 | |
| T033 | `DeliveryReceiver` protocol (endpoint/auth/result-map/retry/gates) | WP06 | [P] |
| T034 | TeamspaceReceiver (`/api/v1/events/batch/`, Bearer, SaaS+PrivateTeamspace gates) | WP06 | |
| T035 | ExternalReceiver (operator URL/auth, no Teamspace gating) | WP06 | |
| T036 | StubReceiver (localhost, no creds — a real receiver, not a test fork) | WP06 | |
| T037 | Additive `batch-api-contract.md` update (ledger-on-success; body-upload untouched) | WP06 | |
| T038 | Tests: fork-CI on stub (no creds); stub≡Teamspace ledger state | WP06 | |
| T039 | Dispatcher select phase (active target; exclude terminal-failed) | WP07 | [P] |
| T040 | Post phase via the active target's DeliveryReceiver | WP07 | |
| T041 | Record phase → ledger (success/dup terminal; pending/rejected/transient state); never delete | WP07 | |
| T042 | `failed_permanent` → terminal-failed (excluded from future selection) | WP07 | |
| T043 | Re-drain to a new target (FR-005) | WP07 | |
| T044 | Complexity discipline: select/post/record each ≤15 | WP07 | |
| T045 | Tests: A→B replay; re-sync skips; oversized progresses + inspectable | WP07 | |
| T046 | Coalesce only events with no terminal delivery (uses T031) | WP08 | [P] |
| T047 | Delivered → immutable; new event = new row + mark prior superseded | WP08 | |
| T048 | Register coalesce strategy into the WP03 journal seam | WP08 | |
| T049 | **REQUIRED DB test**: coalesce vs delivered event → bytes unchanged (NFR-002) | WP08 | |
| T050 | Tests: undelivered collapse; superseded marker; no mutation of delivered | WP08 | |
| T051 | `EventSyncConfig`: retention × delivery axes | WP09 | [P] |
| T052 | Four presets (TEAMSPACE / EXTERNAL_RECEIVER / LOCAL_RETENTION / OPT_OUT) | WP09 | |
| T053 | Mode → (receiver, retention) resolution wired to WP06 | WP09 | |
| T054 | OPT_OUT discards only local-only/discardable; refuse/audit Teamspace-bound (C-008) | WP09 | |
| T055 | Tests: per-mode observable on-disk + network behavior | WP09 | |
| T056 | Discover ALL `queue-<digest>.db` + legacy `queue.db` | WP10 | [P] |
| T057 | Best-effort or `unknown` target; never fabricate identity from a one-way digest | WP10 | |
| T058 | Transactional per source DB + idempotent re-run (NFR-005) | WP10 | |
| T059 | Identical dup `event_id` imports once with all provenance | WP10 | |
| T060 | Divergent dup → conflict/audit row; source untouched; cleanup blocked; non-zero | WP10 | |
| T061 | Never rewrite event IDs; only currently-queued payloads survive | WP10 | |
| T062 | Retire event-queueing from `queue.py`; keep body-upload tables (C-006) | WP10 | |
| T063 | Tests: multi-DB; unknown digest; identical dup; divergent dup | WP10 | |
| T064 | Assemble additive JSON sections (7 sections) | WP11 | [P] |
| T065 | Distinct counts: retained / current-target / previous-target / terminal-failed / body-upload + oldest ts | WP11 | |
| T066 | gc/archive logic (explicit-only; preserve ledger history) | WP11 | |
| T067 | GC suggestion only when large AND fully delivered (NFR-004) | WP11 | |
| T068 | Preserve existing counts; no field implies body-upload == journal (NFR-006) | WP11 | |
| T069 | Additive `sync-status-output.md` contract update (old fields preserved) | WP11 | |
| T070 | Tests: JSON has new sections + old fields; counts distinguished; GC gating | WP11 | |
| T071 | Wire `sync now` → dispatcher; `sync server` → target authority | WP12 | [P] |
| T072 | Wire `sync status` + `--check --json` → status_report | WP12 | |
| T073 | Wire `sync gc` / `sync archive` → retention (explicit destructive only) | WP12 | |
| T074 | Wire EventSyncConfig mode selection → WP09 | WP12 | |
| T075 | Preserve backward-compatible behavior of existing flags (NFR-006) | WP12 | |
| T076 | Terminology Canon: no `feature*` aliases in new flags/commands | WP12 | |
| T077 | Tests: observable CLI output (not call order, NFR-001) | WP12 | |

---

## Phase 1 — Target Authority (IC-00 · must land first)

### WP01 — Target Authority resolver
- **Goal**: Build `sync/target_authority.py` — the single `ResolvedSyncTarget` that every hosted/sync surface keys off. **Priority**: P1 (foundational; everything depends on it).
- **Independent test**: construct a resolver under env/config agreement and disagreement; assert all 8 fields and that queue scope cannot be derived for one target while the resolved URL points at another.
- **Subtasks**: T001 [P], T002, T003, T004, T005, T006
- **Dependencies**: none
- **Requirements**: FR-016, C-002, C-007, SC-008
- **Risks**: ambiguous env/config precedence; keep `active_queue_scope` a diagnostic, never an input.
- **Prompt**: `tasks/WP01-target-authority-resolver.md` (~320 lines)

### WP02 — Wire runtime surfaces onto Target Authority
- **Goal**: Make config/auth/readiness/preflight/owner/tracker/runtime consume the resolver; queue scope becomes derived. **Priority**: P1.
- **Independent test**: env/config disagreement cannot split target vs queue scope; stale `active_queue_scope` is reported and ignored.
- **Subtasks**: T007, T008, T009, T010, T011, T012
- **Dependencies**: WP01
- **Requirements**: FR-016, SC-008
- **Risks**: wide surface (sync/, auth/, saas/). `queue.py` scope-consumption is **owned by WP10** (it owns `queue.py`); coordinate, do not edit `queue.py` here.
- **Prompt**: `tasks/WP02-wire-surfaces-target-authority.md` (~300 lines)

## Phase 2 — Event Journal (IC-01 partial + IC-02)

### WP03 — Event Journal (append-only) + capture-first
- **Goal**: Stand up `event_journal/` — durable, producer-scoped, append-only payload store that does not know delivery state; integrate capture-first at the emit layer. **Build a no-op coalescing seam** (WP08 fills it). **Priority**: P1.
- **Independent test**: with `SPEC_KITTY_ENABLE_SAAS_SYNC=0` / missing auth, produce Teamspace-bound events → they are journaled with a blocked-drain reason and deliverable later; every event is a distinct row (no coalescing yet).
- **Subtasks**: T013 [P], T014, T015, T016, T017, T018, T019
- **Dependencies**: WP01
- **Requirements**: FR-001, FR-003, FR-017, C-008, SC-009
- **Risks**: must NOT re-introduce in-place mutation; capture-first must precede all gates.
- **Prompt**: `tasks/WP03-event-journal-capture-first.md` (~420 lines)

## Phase 3 — Delivery domain (IC-03, IC-04, IC-04a)

### WP04 — Delivery Target Registry & identity
- **Goal**: `delivery/` package + interfaces + `delivery/targets.py` (URL+scope identity; deployment metadata as provenance; advisory reset-detection). **Priority**: P1.
- **Independent test**: two URLs → two targets; same URL with a new `deployment_id` does NOT fork identity but flags a reset.
- **Subtasks**: T020 [P], T021, T022, T023, T024, T025
- **Dependencies**: WP01
- **Requirements**: FR-002, FR-012, C-002
- **Risks**: deployment_id churn forking identity; reset-detection stays advisory.
- **Prompt**: `tasks/WP04-delivery-target-registry.md` (~330 lines)

### WP05 — Delivery Ledger
- **Goal**: `delivery/ledger.py` — per-event/per-target state (incl. terminal-failed state and the delivered-anywhere query), shaped to grow to many targets. **Priority**: P1.
- **Independent test**: record each outcome; assert selection returns undelivered-for-target and excludes terminal-failed; idempotent re-delivery → duplicate.
- **Subtasks**: T026 [P], T027, T028, T029, T030, T031, T032
- **Dependencies**: WP04
- **Requirements**: FR-002, FR-004, FR-015, C-003, NFR-003
- **Risks**: index design drives dispatcher performance; many-targets shape must not require a later schema break.
- **Prompt**: `tasks/WP05-delivery-ledger.md` (~400 lines)

### WP06 — DeliveryReceiver contract + receivers
- **Goal**: `delivery/receivers.py` — one `DeliveryReceiver` contract with Teamspace / external / stub implementations; additive batch-API contract. **Priority**: P1.
- **Independent test**: run a delivery against the stub with no Teamspace creds; assert the stub recorded events and ledger state matches a Teamspace delivery for equivalent payloads.
- **Subtasks**: T033 [P], T034, T035, T036, T037, T038
- **Dependencies**: WP04, WP05
- **Requirements**: FR-007, FR-008, FR-014, SC-005, SC-007
- **Risks**: the stub must be a real receiver, not a test-only dispatch fork; gates per-receiver, not in the dispatcher.
- **Prompt**: `tasks/WP06-delivery-receiver-contract.md` (~380 lines)

## Phase 4 — Dispatch & coalescing (IC-05, IC-05a, IC-02a)

### WP07 — Sync Dispatcher
- **Goal**: `delivery/dispatcher.py` — select-undelivered → post via receiver → record to ledger; never deletes; terminal-failed excluded. **Priority**: P1.
- **Independent test**: deliver N events to A; switch to B; same N delivered to B and still retained; re-sync to A skips; an oversized event becomes terminal-failed and the drain still progresses.
- **Subtasks**: T039 [P], T040, T041, T042, T043, T044, T045
- **Dependencies**: WP03, WP05, WP06
- **Requirements**: FR-001, FR-004, FR-005, FR-015
- **Risks**: complexity ceiling — split select/post/record; forgetting to exclude terminal-failed loops the drain.
- **Prompt**: `tasks/WP07-sync-dispatcher.md` (~420 lines)

### WP08 — Coalescing with delivered-event immutability
- **Goal**: `event_journal/coalesce.py` — coalesce only undelivered events; delivered events immutable; register into WP03's seam. **Priority**: P2.
- **Independent test**: **required DB test** — a coalesce attempt against an event with any terminal delivery leaves its bytes byte-for-byte unchanged.
- **Subtasks**: T046 [P], T047, T048, T049, T050
- **Dependencies**: WP03, WP05
- **Requirements**: FR-011, NFR-002
- **Risks**: the correctness trap — delivered-event immutability is a hard DB assertion, not prose.
- **Prompt**: `tasks/WP08-coalescing-immutability.md` (~260 lines)

## Phase 5 — Policy, migration, status, CLI

### WP09 — EventSyncConfig policy & modes
- **Goal**: `delivery/config.py` — retention × delivery axes with four presets; opt-out safety. **Priority**: P2.
- **Independent test**: for each mode, assert observable on-disk + network behavior matches.
- **Subtasks**: T051 [P], T052, T053, T054, T055
- **Dependencies**: WP05, WP06
- **Requirements**: FR-006, FR-007
- **Risks**: OPT_OUT must refuse/audit Teamspace-bound discard, never silently drop.
- **Prompt**: `tasks/WP09-event-sync-config.md` (~280 lines)

### WP10 — Migration off hash-scoped queues
- **Goal**: `sync/migrate_journal.py` — discover all scoped DBs, migrate into journal+ledger with unknown-provenance + duplicate handling; retire event-queueing from `queue.py` while keeping body-upload tables. **Priority**: P1 (blocks safe rollout).
- **Independent test**: migrate multiple `queue-<digest>.db` (incl. unknown digest); identical dup dedupes; divergent dup creates a conflict and preserves the source DB.
- **Subtasks**: T056 [P], T057, T058, T059, T060, T061, T062, T063
- **Dependencies**: WP01, WP03, WP05
- **Requirements**: FR-013, FR-018, NFR-005, SC-006, SC-011
- **Risks**: atomicity per DB; plural-source coverage (single-DB happy path is insufficient); must not break `body_upload_queue`/`body_upload_failure_log` (C-006).
- **Prompt**: `tasks/WP10-migrate-hash-scoped-queues.md` (~460 lines)

### WP11 — Status report assembly + GC/archive
- **Goal**: `delivery/status_report.py` (additive JSON) + `delivery/retention.py` (explicit gc/archive); additive status contract. **Priority**: P2.
- **Independent test**: `--check --json` includes all 7 new sections + old top-level fields; retained vs per-target delivered counts are distinct; GC suggested only when large AND fully delivered.
- **Subtasks**: T064 [P], T065, T066, T067, T068, T069, T070
- **Dependencies**: WP03, WP05, WP10
- **Requirements**: FR-009, FR-010, FR-019, NFR-004, NFR-006
- **Risks**: status back-compat for existing consumers; never imply body-upload rows are journal rows.
- **Prompt**: `tasks/WP11-status-gc-archive.md` (~380 lines)

### WP12 — Sync CLI wiring
- **Goal**: wire all `sync` subcommands (now/server/status/gc/archive/config) to the new domains; keep the CLI thin and backward-compatible. **Priority**: P2.
- **Independent test**: observable CLI output for each subcommand; existing flags still work; no `feature*` aliases introduced.
- **Subtasks**: T071 [P], T072, T073, T074, T075, T076, T077
- **Dependencies**: WP07, WP09, WP10, WP11
- **Requirements**: FR-005, FR-009, FR-010, FR-019, NFR-001, NFR-006
- **Risks**: single-owner of `cli/commands/sync.py` — keep logic in domain modules, wiring only here.
- **Prompt**: `tasks/WP12-sync-cli-wiring.md` (~360 lines)

---

## Execution notes

- **MVP / first package**: WP01 (target authority resolver) is the foundation; the full critical path WP01→WP02→WP03→WP04→WP05→WP06→WP07→WP10→WP11→WP12 constitutes the MVP. WP08/WP09 are P2 enrichers on the same spine.
- **Parallelism after WP01**: WP02, WP03, WP04 run in parallel. After WP05: WP06 and (with WP03) WP08, WP10. WP12 is the join point.
- **Tests**: observable CLI + on-disk/ledger state, not call order (NFR-001). Stub receiver removes the `teamspace_key` fork-CI dependency (SC-005). Real-port/daemon sync tests run serially (`-n0`).
- **Out of scope**: IC-09 SaaS `/health` deployment metadata (cross-repo follow-on, C-004).

---

## Analysis remediation addenda (findings A1–A7)

> From `/spec-kitty.analyze` (initial verdict *blocked*). **A1** (ATDD-First) and **A2** (Identifier Safety) are encoded directly in the affected WP prompts; **A3** is a charter note in WP06. These addenda close **A4–A7**.

### NFR → WP coverage (A4)

| NFR | Covered by | Notes |
|-----|-----------|-------|
| NFR-001 observable-state tests | WP12 + every WP's Test Strategy | assert CLI output + on-disk/ledger state, not call order |
| NFR-002 outcome coverage incl. immutability + multi-DB | WP08 (immutability DB test), WP10 (multi-DB migration) | |
| NFR-003 idempotent re-delivery | WP05 (T032) | `duplicate` handling, unchanged event IDs |
| NFR-004 bounded growth visibility | WP11 (T067) | journal size + GC-suggestion gating |
| NFR-005 migration safety/atomicity | WP10 (T058) | transactional per-DB, idempotent |
| NFR-006 additive contracts | WP06 (T037), WP11 (T068/T069), WP12 (T075) | back-compat preserved |

### FR-012 status (A5)

FR-012 (target-reset detection) is **Partial (advisory) in this mission**: WP04 records deployment metadata + advisory change-detection only. Full reset-detection consumes SaaS `/api/v1/sync/health/` metadata, deferred to the IC-09 follow-on (C-004) — out of scope. SC-004's deployment-identity clause is likewise deferred.

### Module refinement beyond plan.md (A6)

tasks introduces three modules not named in plan.md's Project Structure, to keep the CLI thin and the domain seam explicit: `delivery/status_report.py` (additive JSON assembly, WP11), `delivery/retention.py` (gc/archive logic, WP11), `delivery/interfaces.py` (domain protocols, WP04).

### Operator CLI surface (A7)

EventSyncConfig mode selection is pinned to `spec-kitty sync mode <TEAMSPACE|EXTERNAL_RECEIVER|LOCAL_RETENTION|OPT_OUT>` (`sync mode` with no argument prints the current mode); wired in WP12, policy resolved in WP09. Terminology Canon: no `feature*` aliases.

### C-008 runtime enforcement deferred (A8, post-merge mission review)

T054's discard-safety machinery (`discard_decision`/`FamilyClassification`/`JsonlAuditSink`, WP09) is implemented + unit-tested but its **live capture-time wiring is deferred** to the legacy-`queue.py`-drain retirement follow-up (DRIFT-1/RISK-1); see `issue-matrix.md` → Deferred follow-ups.
