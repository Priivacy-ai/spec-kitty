# Tasks: Profile Invocation Runtime and Audit Trail

**Mission**: `profile-invocation-runtime-audit-trail-01KPQRX2`
**Release target**: 3.2.0
**Branch**: `main` → `main`
**Generated**: 2026-04-21

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Package scaffold: `invocation/__init__.py`, fixture profiles, `errors.py` | WP01 | — | [D] |
| T002 | `record.py` — InvocationRecord Pydantic v2 model + MinimalViableTrailPolicy stub | WP01 | — | [D] |
| T003 | `registry.py` — ProfileRegistry wrapping AgentProfileRepository | WP01 | [D] |
| T004 | `writer.py` — InvocationWriter (write_started, write_completed, append-only) | WP01 | [D] |
| T005 | `executor.py` — ProfileInvocationExecutor (invoke + governance context assembly) | WP01 | — | [D] |
| T006 | `profiles_cmd.py` — `spec-kitty profiles list [--json]` + main.py registration | WP01 | [D] |
| T007 | Tests: test_record, test_registry, test_writer, test_executor, test_profiles CLI | WP01 | — | [D] |
| T008 | `router.py` — ActionRouter with CANONICAL_VERB_MAP, token normalization, domain_keyword match | WP02 | — | [D] |
| T009 | Wire router into executor.py invoke() (no-hint path); add ActionRouterPlugin stub | WP02 | — | [D] |
| T010 | `test_router.py` — 7 table-driven cases; confirm ADR-3 doc as review gate | WP02 | [D] |
| T011 | `advise.py` — `spec-kitty advise <request> [--profile <name>] [--json]` | WP03 | — |
| T012 | Add `spec-kitty ask <profile> <request>` shim in advise.py | WP03 | [P] |
| T013 | Add `spec-kitty profile-invocation complete --invocation-id <id>` in advise.py | WP03 | [P] |
| T014 | Register advise / ask / profile-invocation groups in main.py | WP03 | — |
| T015 | Integration tests: cli/test_advise.py (happy path, profile missing, no charter, --json) | WP03 | [P] |
| T016 | `do_cmd.py` — `spec-kitty do <request> [--json]` (router always invoked) | WP04 | — |
| T017 | Register do command in main.py | WP04 | — |
| T018 | Integration tests: cli/test_do.py (happy path, ambiguity error, no-match error) | WP04 | [P] |
| T019 | Finalize MinimalViableTrailPolicy frozen dataclass (all 3 tiers fully specified) | WP05 | — |
| T020 | Implement `tier_eligible(record)` and `promote_to_evidence(record, dir, content)` | WP05 | — |
| T021 | Export MinimalViableTrailPolicy from `__init__.py`; extend test_record.py | WP05 | [P] |
| T022 | `invocations_cmd.py` — `invocations list [--profile] [--limit N] [--json]` | WP06 | — |
| T023 | Register invocations group in main.py | WP06 | — |
| T024 | Benchmark list perf at 10K entries; implement invocation-index if > 200ms | WP06 | — |
| T025 | Integration tests: cli/test_invocations.py (query, filter, empty log, limit) | WP06 | [P] |
| T026 | Skill pack: `.agents/skills/spec-kitty.advise/SKILL.md` | WP06 | [P] |
| T027 | Entry gate: verify CLI-SaaS contract field coverage for InvocationRecord v1 | WP07 | — |
| T028 | `propagator.py` — InvocationSaaSPropagator (background thread, atexit, error log) | WP07 | — |
| T029 | Wire propagator into executor.py post write_completed | WP07 | — |
| T030 | `test_propagator.py` — mock SaaS client, non-blocking, error log, idempotency, no-op | WP07 | [P] |

---

## Work Package Summary

### WP01 — Executor Core: Package Foundation + `profiles list`

**Goal**: Stand up the new `src/specify_cli/invocation/` package with its core primitives: `ProfileInvocationExecutor`, `InvocationRecord`, `ProfileRegistry`, `InvocationWriter`, error types, and the `spec-kitty profiles list` command. This WP is the dependency root for all other WPs.

**Priority**: P1 — blocks everything
**Estimated prompt size**: ~460 lines
**Entry gate**: ADR-3 doc (`adr-3-deterministic-action-router.md`) already committed
**Prompt file**: [tasks/WP01-executor-core-profiles-list.md](tasks/WP01-executor-core-profiles-list.md)

Included subtasks:
- [x] T001 Package scaffold: `invocation/__init__.py`, fixture profiles, `errors.py` (WP01)
- [x] T002 `record.py` — InvocationRecord Pydantic v2 model + MinimalViableTrailPolicy stub (WP01)
- [x] T003 `registry.py` — ProfileRegistry wrapping AgentProfileRepository (WP01)
- [x] T004 `writer.py` — InvocationWriter (write_started, write_completed, append-only) (WP01)
- [x] T005 `executor.py` — ProfileInvocationExecutor (invoke + governance context assembly) (WP01)
- [x] T006 `profiles_cmd.py` — `spec-kitty profiles list [--json]` + main.py registration (WP01)
- [x] T007 Tests: test_record, test_registry, test_writer, test_executor, test_profiles CLI (WP01)

**Dependencies**: none (root WP)
**Blocks**: WP02, WP03, WP04, WP05, WP06, WP07

---

### WP02 — Deterministic Action Router

**Goal**: Implement the `ActionRouter` (ADR-3, Option A — deterministic, no LLM). Wire it into the executor's no-hint path. The ADR-3 document must be reviewed and accepted before this WP merges.

**Priority**: P1 — blocks WP03 (advise router path), WP04 (do command)
**Estimated prompt size**: ~280 lines
**Entry gate**: ADR-3 doc reviewed and accepted (exists at `adr-3-deterministic-action-router.md`)
**Prompt file**: [tasks/WP02-deterministic-action-router.md](tasks/WP02-deterministic-action-router.md)

Included subtasks:
- [x] T008 `router.py` — ActionRouter with CANONICAL_VERB_MAP, token normalization, domain_keyword match (WP02)
- [x] T009 Wire router into executor.py invoke() (no-hint path); add ActionRouterPlugin stub (WP02)
- [x] T010 `test_router.py` — 7 table-driven cases; confirm ADR-3 doc as review gate (WP02)

**Dependencies**: WP01
**Blocks**: WP03, WP04

---

### WP03 — `advise` + `ask` + `profile-invocation complete` CLI

**Goal**: Implement the three primary CLI surfaces for profile-governed invocations: `advise`, `ask` (thin shim), and `profile-invocation complete`. These are the surfaces host-LLM agents use to open and close invocation records.

**Priority**: P1 — primary user-facing CLI
**Estimated prompt size**: ~350 lines
**Prompt file**: [tasks/WP03-advise-ask-complete-cli.md](tasks/WP03-advise-ask-complete-cli.md)

Included subtasks:
- [ ] T011 `advise.py` — `spec-kitty advise <request> [--profile <name>] [--json]` (WP03)
- [ ] T012 Add `spec-kitty ask <profile> <request>` shim in advise.py (WP03)
- [ ] T013 Add `spec-kitty profile-invocation complete --invocation-id <id>` in advise.py (WP03)
- [ ] T014 Register advise / ask / profile-invocation groups in main.py (WP03)
- [ ] T015 Integration tests: cli/test_advise.py (WP03)

**Dependencies**: WP02
**Blocks**: none (parallel with WP04–WP07)

---

### WP04 — `do` Command

**Goal**: Implement `spec-kitty do <request>` — the anonymous dispatch surface that always routes through the ActionRouter (no explicit profile hint from caller). This is the simplest entry point for operators who don't know which profile to use.

**Priority**: P2 — depends on router (WP02)
**Estimated prompt size**: ~220 lines
**Prompt file**: [tasks/WP04-do-command.md](tasks/WP04-do-command.md)

Included subtasks:
- [ ] T016 `do_cmd.py` — `spec-kitty do <request> [--json]` (WP04)
- [ ] T017 Register do command in main.py (WP04)
- [ ] T018 Integration tests: cli/test_do.py (WP04)

**Dependencies**: WP02
**Blocks**: none

---

### WP05 — MinimalViableTrailPolicy + Tier Promotion API

**Goal**: Finalize the `MinimalViableTrailPolicy` as a frozen dataclass with all three tiers fully specified, implement `tier_eligible()` and `promote_to_evidence()` helpers, and export them from the package's public API.

**Priority**: P2 — can run in parallel with WP02–WP04
**Estimated prompt size**: ~240 lines
**Prompt file**: [tasks/WP05-minimal-viable-trail-policy.md](tasks/WP05-minimal-viable-trail-policy.md)

Included subtasks:
- [ ] T019 Finalize MinimalViableTrailPolicy frozen dataclass (all 3 tiers fully specified) (WP05)
- [ ] T020 Implement `tier_eligible(record)` and `promote_to_evidence(record, dir, content)` (WP05)
- [ ] T021 Export from `__init__.py`; extend test_record.py (WP05)

**Dependencies**: WP01
**Blocks**: none

---

### WP06 — `invocations list` + Skill Pack Updates

**Goal**: Implement `spec-kitty invocations list` — the operator's view into the local JSONL audit log — and update agent skill packs to document the new advise/ask/do/profiles surfaces.

**Priority**: P2 — can run in parallel with WP02–WP05
**Estimated prompt size**: ~320 lines
**Prompt file**: [tasks/WP06-invocations-list-skill-packs.md](tasks/WP06-invocations-list-skill-packs.md)

Included subtasks:
- [ ] T022 `invocations_cmd.py` — `invocations list [--profile] [--limit N] [--json]` (WP06)
- [ ] T023 Register invocations group in main.py (WP06)
- [ ] T024 Benchmark list perf at 10K entries; implement index if > 200ms (WP06)
- [ ] T025 Integration tests: cli/test_invocations.py (WP06)
- [ ] T026 Skill pack: `.agents/skills/spec-kitty.advise/SKILL.md` (WP06)

**Dependencies**: WP01
**Blocks**: WP07 (propagation relies on writer being stable)

---

### WP07 — SaaS Propagation

**Goal**: Implement `InvocationSaaSPropagator` — background-thread, non-blocking SaaS event propagation using the existing CLI-SaaS contract. The entry gate for this WP is a mandatory contract field coverage check.

**Priority**: P3 — last WP; depends on stable record + writer
**Estimated prompt size**: ~290 lines
**Prompt file**: [tasks/WP07-saas-propagation.md](tasks/WP07-saas-propagation.md)

Included subtasks:
- [ ] T027 Entry gate: verify CLI-SaaS contract field coverage for InvocationRecord v1 (WP07)
- [ ] T028 `propagator.py` — InvocationSaaSPropagator (background thread, atexit, error log) (WP07)
- [ ] T029 Wire propagator into executor.py post write_completed (WP07)
- [ ] T030 `test_propagator.py` — mock SaaS, non-blocking, error log, idempotency, no-op (WP07)

**Dependencies**: WP01 (executor), WP06 (stable writer)
**Blocks**: none

---

## Dependency Graph

```
WP01 (root)
 ├─→ WP02 ─→ WP03
 │    └─→ WP04
 ├─→ WP05   (parallel with WP02)
 └─→ WP06 ─→ WP07
```

## Parallelization Opportunities

After WP01 lands:
- **WP02 ∥ WP05 ∥ WP06**: All three are independent after WP01
- **WP03 ∥ WP04**: Both depend on WP02 but are independent of each other
- **WP07**: Starts after WP06 (and WP01)

Expected critical path: WP01 → WP02 → WP03 (5 subtasks on the sequential path)
