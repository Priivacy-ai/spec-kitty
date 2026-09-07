# Mission Specification: FSM Write-Path Integrity

**Mission Branch**: `fsm-write-path-integrity-01M1TZV6`
**Created**: 2026-09-06
**Status**: Draft (proto-mission — sliced at spec level; no plan.md or tasks yet; open decisions carried explicitly below)
**Input**: User description: "Serialize and unify every writer of the mission status event log so no transition can be lost, phantom-announced, or dep-illegally claimed. P0 hardening of the mission-status write path. Parent epic #3893, milestone 3.2.7. Ground truth: research/28-missionA-research-dossier.md (settled decisions D1–D15, binding constraints C1–C10, open questions Q1–Q10, risk register R1–R12, verified against HEAD e721763759)."

The status event log (`status.events.jsonl`) is the FSM's sole authority for WP lane state, yet today it has 3 locked and 4 unlocked writer families plus a lockless batch door, THREE parallel emit orchestrations, a phantom fan-out defect (an event announced to the outside world before the coord commit that a rollback then truncates), dependency gating that lives outside the FSM guard, and a slug-keyed, non-atomic run-state store. This mission closes those defects by hardening and deletion — one locked, validated write door with dependency gating inside it, raw appends gated, and a crash-safe, identity-correct run-state store. **No redesign.**

## Ground-Truth Errata

This mission's citations were re-verified against `main` at `3b38073a32` during the 2026-09-07 landing pass (PR #3904). The dossier (`research/28-missionA-research-dossier.md`) carries the same drifted or imprecise values for every row below and is left unmodified — it is an immutable evidence snapshot anchored at `e721763759` — but **for the entries in this table, the spec (as corrected here) overrides the dossier**, notwithstanding the general "where this spec and the dossier disagree, the dossier wins" rule.

| Dossier/spec said | Actually true (verified `3b38073a32`) | Why it changed |
|---|---|---|
| `status/__init__.py:518-537` is the `append_event*` export block (US3-AS1, FR-010) | The seven `append_*` entries in `__all__` are at lines 394, 518, 533, 536, 537, 538, 539; lines 519-532 are 14 unrelated exports; `:394` (`append_annotations_atomic_verified`) — the exact symbol `migration/backfill_runtime_state.py:1535` calls — was missing entirely | Wrong from the start; never a contiguous block |
| `docs/architecture/status-model.md:393` carries the stale "single entry point" sentence (FR-009, Doc contention) | No such sentence exists there (the file is byte-identical to `e721763759`); the real site is `docs/architecture/04_implementation_mapping/README.md`'s Command-Surface Mapping table (Lifecycle Command Gateway row, currently line 223 — this file churns, re-verify before use) | Wrong from the start; `CLAUDE.md:409` was already correct as cited |
| `status/aggregate.py:623` is the coordination lazy-import precedent (C-006) | Line `:623` is a `status.models` import; the `coordination.status_transition` import is at `:624` | Off-by-one, wrong from the start |
| `_internal_runtime/engine.py:191-795` covers the four `emitter or NullEmitter()` sites (Interference Map) | The four sites are at `:198`, `:259`, `:522`, `:795` | Imprecise range, wrong from the start |
| `decision.py:194-235` covers the two dead DSL readers (Interference Map) | `derive_mission_state` spans ~187-210 and `evaluate_guards` spans ~218-273; `:194-235` starts mid-docstring and covers neither cleanly | Imprecise range, wrong from the start |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Serialized Out-of-Pipeline Writers (Priority: P1)

As an orchestrator running parallel WP agents alongside post-merge retrospectives and migrations, every append to `status.events.jsonl` is serialized under the mission status lock with atomic append semantics — no writer family can destroy or interleave-corrupt another writer's event, and a transaction rollback can never truncate away an event a concurrent writer legitimately landed.

**Why this priority**: This is one half of the defect-closing core (with User Story 2). The reproducible lost-write today is a raw retrospective append landing inside `BookkeepingTransaction._rollback`'s truncate-to-pre-emit-offset window (`coordination/transaction.py:944`) — the event is silently destroyed. The live post-merge retrospective path (`retrospective/lifecycle_events.py:250-256`, TOCTOU Lamport read at `:265`) is the highest-priority unlocked writer. Corresponds to proposed WP01.

**Independent Test**: Can be fully tested by exercising the four unlocked writer families (retrospective ×2, migration backfills ×2) concurrently with a rolling-back transaction and asserting event survival, lock-held invariants per writer family, and lock-key correctness — without touching the emit pipeline, guard, or run-state work.

**Acceptance Scenarios**:

1. **Given** a `BookkeepingTransaction` whose coord commit is forced to fail, **When** a raw retrospective lifecycle append (`_append_retro_lifecycle_event`) interleaves between the transaction's pre-emit size capture and its rollback truncate (`transaction.py:944`), **Then** the retrospective event survives in `status.events.jsonl` after the rollback completes. (RED on main — the truncate destroys it.)
2. **Given** the runtime-state backfill (`migration/backfill_runtime_state.py`), **When** it writes its transition append (`:1533`) and annotation append (`:1535`), **Then** the pair lands under one lock acquisition with the idempotency read (`:1497`) moved inside the lock — no two-append window and no TOCTOU re-read.
3. **Given** two missions whose slugs collide but whose `feature_dir.name`s differ, **When** each acquires the status lock, **Then** they acquire distinct lock files; **and Given** a bare/legacy slug directory, **When** its writers lock, **Then** they serialize against that mission's ordinary writers via the same lock file (lock key = `feature_dir.name` via `resolve_status_lock_root`, `workspace/root_resolver.py:36`).
4. **Given** each of the seven writer families, **When** it appends to `status.events.jsonl`, **Then** a lock-held assertion verifies `feature_status_lock` is held at the moment of the append.
5. **Given** the merge path's new retrospective L1 acquisition (under the L5 merge-global sentinel), **When** the status lock is contended, **Then** the acquisition uses a finite timeout and fails with a structured error rather than converting a slow status commit into a repo-wide merge refusal.

---

### User Story 2 - One Emit Pipeline, No Phantom Announcements (Priority: P1)

As an orchestrator running parallel WP agents, no status transition I emit is ever lost or announced-then-rolled-back: every emit path — single, batch, inner-state, aggregate, and the plain legacy door — converges on one status-owned validation/build pipeline, and external fan-out (SaaS/zeitgeist) fires only after the coord commit succeeds.

**Why this priority**: This is the mission's core (proposed WP02, sized 4–5 days, binding). Today `_fallback_emit_single._coord` (`coordination/status_transition.py:401-432`) calls the plain door, whose step-7 SaaS fan-out (`status/emit.py:794`) fires **before** `_commit_status_artifacts_to_coord`; on commit failure the event is truncated back but the outside world was already notified of an event that no longer exists. The three parallel orchestrations also breed intra-file whack-a-field divergence: the batch door lacks the single door's owned-mission check and `effective_root` handling entirely (`:1342-1345`/`:1362-1369` vs `:1605-1614`).

**Independent Test**: Can be fully tested by promoting `_prepare_event` (`status_transition.py:842-945`) into `status/` as one public, pure, I/O-parameterized pipeline with two thin composition shells (flat/primary: lock + atomic append + materialize + immediate fan-out; transactional: txn + post-commit-deferred fan-out), then asserting behavioral equivalence and the three pins below — independent of the WP01 writer serialization.

**Acceptance Scenarios**:

1. **Given** a coord-topology mission on the fallback emit path, **When** the coord commit is forced to fail and the event is truncated back, **Then** zero SaaS/zeitgeist fan-out occurred for the truncated event. (RED on main via `emit.py:794` firing pre-commit.)
2. **Given** an owned-mission (`effective_root`) request, **When** it is submitted through the batch door, **Then** it receives the same owned-mission refusal (`ActionContextError`) and `effective_root` acquisition the single door applies. (RED on main — the batch door silently skips both; a second pin covers the immediate-vs-deferred fan-out ordering divergence, `emit.py:794` vs `queue_saas_emission:1403/:1688`.)
3. **Given** a stored-`LANES` mission, **When** a plain-door caller (`contracts/anchoring.py`, `dossier/rebaseline.py`, `migration/verdict_provenance_backfill.py`, `runtime/next/runtime_bridge_composition.py` class) emits, **Then** the working tree gains no new commits — plain-door callers keep their uncommitted-write semantics (constraint C-008; guards against the rejected shim-over-coordination mechanism resurfacing).
4. **Given** the collapse is complete, **When** `MissionStatus.transition` (`status/aggregate.py:605-698`) emits, **Then** validation runs exactly once in the shared pipeline (its pre-duplicated from-lane derivation, gate inference, and `validate_transition` call at `:685` are deleted), and the transactional door no longer re-derives and re-validates a second time.
5. **Given** the three failure policies (single transactional fail-closed on unresolvable coord worktree; batch policy at `:1574`; inner-state deliberate degrade on `BookkeepingWorktreeMissing` per #3460; plus the alias-collapse no-op arm), **When** the unified pipeline handles each, **Then** each policy remains explicit per-shell/per-arm and its pinned named tests stay green (the plan phase must enumerate the #3460 pin tests by nodeid in the WP02 design note before implementation — they are not named here or in the dossier).

---

### User Story 3 - Gated Raw Appends (Priority: P2)

As a maintainer of the FSM authority, no code outside the status store can open `status.events.jsonl` for writing without tripping an architectural gate: the raw `append_event*` exports are stripped from the public facade into an unsafe module with a shrink-only caller allowlist, and an AST gate rejects any out-of-pipeline write.

**Why this priority**: The gates make User Stories 1–2 durable — without them the census decays back (this mission's census itself corrected a stale in-code claim and dropped a false positive). Depends on WP01's fixed census to be seeded green-ably; corresponds to proposed WP03, first instance of the census-gate rule (to be noted on #3895 — the PR body requests the post; no such note exists there yet).

**Independent Test**: Can be fully tested by the two gates themselves plus their non-vacuity floors: introduce a synthetic out-of-pipeline writer and assert the gate goes RED; shrink the allowlist and assert growth is refused.

**Acceptance Scenarios**:

1. **Given** the seven `append_*` entries in `status/__init__.py`'s `__all__` (lines 394, 518, 533, 536-539 — see Ground-Truth Errata) moved to `status/_unsafe.py`, **When** a caller outside the shrink-only allowlist imports them, **Then** the architectural gate fails the build.
2. **Given** the AST writes-gate, **When** a synthetic module performs `open(.., "a")` (or any write) on a path ending `status.events.jsonl` outside `status/store.py`, **Then** the gate goes RED.
3. **Given** either gate, **When** its scan matches zero writers (the vacuous-gate pattern), **Then** the gate goes RED — a gate that matches nothing is itself a failure (non-vacuity floor).

---

### User Story 4 - Dependency Gating Inside the FSM Guard (Priority: P2)

As an operator or agent team, a WP whose declared dependencies are not yet `approved` or `done` cannot be claimed or moved to `in_progress` through any durable write path routed through the emit orchestration — the dependency verdict is a `GuardContext` field enforced by `validate_transition` on the entry edges, resolved in-lock by the emit orchestration shells (the verdict supplier, per FR-013) against the transaction's event surface, with `force` retaining its actor+reason bypass.

**Why this priority**: Today `validate_transition` contains NO dependency logic and a direct emit claiming a dep-blocked WP succeeds; the six pre-flight caller checks are advisory UX with a TOCTOU window. Depends on the unified pipeline (User Story 2) as its enforcement chokepoint; corresponds to proposed WP04.

**Independent Test**: Can be fully tested by direct-emit attempts against dep-blocked WPs, probe-site regression pins, and force/chain-ordering cases — no changes to edges, force, or terminal rules (`wp_state.py` gains one guard field and clause via the established `subtasks_complete` shape only).

**Acceptance Scenarios**:

1. **Given** main's current signature (no readiness field exists anywhere yet), **When** `emit_status_transition` is invoked directly, verdict-less, for `planned→claimed` on a WP with an unsatisfied dependency, **Then** the claim succeeds — the genuinely-RED-on-main repro; after WP04 the same call is refused, because the emit orchestration shell resolves readiness in-lock (FR-013) and populates the guard field.
2. **Given** the post-WP04 pipeline, **When** a `GuardContext` carrying a not-ready readiness verdict reaches `validate_transition` for `planned→claimed` (or `claimed→in_progress`), **Then** the transition is refused (post-fix unit scenario — this case does not exist pre-change).
3. **Given** the guard field is `None` (no verdict supplied), **When** the crash-recovery progression probe (`lanes/recovery.py:78`) and the FR-015 force-free backward-edge probe (`src/specify_cli/cli/commands/agent/tasks_transition_core.py:337`) call `validate_transition` with self-built contexts, **Then** both still pass — the guard is tri-state and fail-OPEN on `None` (constraint C-004; do NOT copy `subtasks_complete`'s fail-closed polarity).
4. **Given** WP-B depends on WP-A within the same mission, **When** WP-A is `approved` (not yet `done`), **Then** WP-B's claim is allowed; **When** WP-A is `in_progress`, **Then** WP-B's claim is blocked; **When** `force` is supplied with actor+reason, **Then** the block is bypassed and recorded.
5. **Given** a coord-topology mission, **When** readiness is resolved, **Then** resolution happens inside the lock/transaction against `txn.feature_dir` (the coord surface) — never pre-lock (reproduces the TOCTOU) and never against the stale primary planning dir.
6. **Given** an `in_progress` WP, **When** `implement` is re-invoked on it, **Then** it remains a no-op resume — not re-gated.

---

### User Story 5 - Crash-Safe, Identity-Correct Run-State (Priority: P3)

As an operator resuming interrupted runs across missions that may share a slug, the runtime run-state store is keyed by `mission_id` (083 identity model), its cursor writes are atomic (tmp-then-`os.replace`), its progress reads are pure (never clobbering tracked `status.json`), and a missing `state.json` with a live index entry is a loud structured error, never a silent fresh run that orphans history.

**Why this priority**: Real defects but a narrower blast radius than the write door itself, and the WP shares all four contended runtime files with Mission B (see Interference Map and open decision Q10). Corresponds to proposed WP05.

**Independent Test**: Can be fully tested through the run-state store and read path alone: slug-collision resolution, crash-window recovery, read purity, and the missing-state error — independent of every other story.

**Acceptance Scenarios**:

1. **Given** two missions sharing a `mission_slug`, **When** each resolves its run in `feature-runs.json`, **Then** they resolve distinct runs keyed by `mission_id`. (RED on main — lookup is `if mission_slug in index`, `runtime_bridge_io.py:618`.)
2. **Given** `engine._write_snapshot` (`runtime/next/_internal_runtime/engine.py:128-130`), **When** the process is killed between truncate-of-old and write-of-new `state.json`, **Then** the state is recoverable (tmp file or old file intact), never a torn cursor; the journal `_append_event` (`:110-119`) hardens with the same discipline.
3. **Given** the progress-count query (`runtime/next/decision.py:369-377`), **When** it runs, **Then** tracked `status.json` is byte-identical afterward — the writing `materialize` call at `:373` is replaced by the pure `materialize_snapshot`.
4. **Given** a live index entry whose `state.json` is missing, **When** the run is resolved, **Then** a loud, structured error is raised — not a silent fall-through to a new run (`:617-627` today).

---

### Edge Cases

- What happens when a coord commit fails mid-emit under `COORD`/`LANES_WITH_COORD` topology? Truncate-rollback symmetry must hold AND no external fan-out may have fired for the truncated event (US2-1); the coord worktree resolution failure itself stays fail-loud via `FallbackCoordWorktreeUnresolved` (C-001).
- How does the guard behave when no readiness verdict is supplied (`None`)? Fail-OPEN — the two live probe sites depend on it (US4-2, C-004).
- What happens on a bare/legacy slug directory with no `mission_id`? Lock keying uses `feature_dir.name` so legacy writers still serialize (US1-3); the run-state index key for legacy missions is open decision Q9 (the `legacy-<slug>` precedent at `status_transition.py:1606`).
- What happens when a replay/audit pass encounters an event that would now fail the dependency guard? Nothing — replay never validates guards (C-005); the reducer stays a pure fold and `validate_transition_legality` re-checks edge legality only. A new guard must never retro-flag history.
- What happens when an L1 acquisition is reachable from an L3 verdict-save-queue scope? It must use the bounded `_in_queue_status_lock_timeout` pattern — L3→L1-unbounded against L1→git is the one constructible deadlock-shaped outage (the #3773 class).
- What happens when a plain-door caller emits for a stored-`LANES` mission? The legitimate primary-uncommitted write — no new commits, no identity-resolution git subprocesses (C-008).
- What happens if a gate's scan set drifts to zero matches? The gate itself goes RED (non-vacuity floor, US3-3).
- What happens when the `nullcontext()` no-git degrade in the lock pattern applies? It must be a conscious per-site choice during WP01, never an accidental default.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Complete writer census governed (D1) | As a maintainer, I want all seven writer families (3 locked: emit single + inner-state, lifecycle appender, `BookkeepingTransaction`; 4 unlocked: `retrospective/events.py:213`, `retrospective/lifecycle_events.py:250-256`, `migration/verdict_provenance_backfill.py:419`, `migration/backfill_runtime_state.py:1533/:1535`) plus the lockless batch door (`emit.py:808-960`) enumerated and brought under governance, so that no writer escapes serialization. `core/mission_creation.py` is excluded (routes through the locked lifecycle appender; its direct touch is a benign `touch(exist_ok=True)`). The stale "only 2 of 6" in-code comment (`orchestrator_api/commands.py:3568-3570`) is quoted only as historical. | High | Open |
| FR-002 | Lock + atomic-append the four unlocked writers (D2) | As an orchestrator, I want each raw writer routed through an atomic-append store primitive UNDER `feature_status_lock` (the `lifecycle_events.py:234-254` migration pattern, generalized), so that appends cannot be clobbered by an `os.replace` writer. Atomicity travels WITH the lock; sites lacking `repo_root` derive it via `resolve_status_lock_root`. The live post-merge retrospective writer is fixed first. (Note: this is `status/lifecycle_events.py`, not `retrospective/lifecycle_events.py` — two different files share the basename; see Ground-Truth Errata.) | High | Open |
| FR-003 | Three lock rules encoded (D3) | As a maintainer, I want the observed lock hierarchy (L5→L1; L3→L1 bounded; L1 re-entrant 3-deep; L1→L4→git only via `BookkeepingTransaction`) encoded in code and WP docs, with (a) L3-reachable L1 takes bounded, (b) the merge-path retrospective L1 take on a finite timeout, (c) one lock-key convention, so that adding L1 to the four unlocked writers creates no new deadlock. FR-003's testable surface is explicitly scoped to rules (a)–(c) (NFR-003's timeout tests + FR-004's lock-key test); the hierarchy statement itself is documentation carried in the WP docs. | High | Open |
| FR-004 | Uniform lock key via `feature_dir.name` (D4) | As an operator with colliding or legacy slugs, I want `feature_status_lock_path` keyed on `feature_dir.name` via `resolve_status_lock_root` instead of `mission_slug` (`locking.py:57-60`), so that slug collision no longer over-serializes and a bare/legacy slug no longer serializes against nobody. | High | Open |
| FR-005 | Layered pipeline extraction (D5) | As a maintainer, I want `_prepare_event` (`status_transition.py:842-945`) promoted into `status/` as ONE public, pure, I/O-parameterized pipeline (alias-resolve → infer gates → alias-collapse → build evidence → `validate_transition` → `build_status_event`) with two thin composition shells (flat/primary; transactional), so that the shared core stops reaching into five `_emit` privates. The shim-over-coordination alternative is REJECTED (inverts C-006; changes plain-door semantics, C-008). The layered cut is the future #2173 StatusWriter seam — but the port is NOT built here. | High | Open |
| FR-006 | Converge three orchestrations + aggregate de-duplication (D6) | As a maintainer, I want `MissionStatus.transition` (`aggregate.py:605-698`), the transactional door (`:1318`) with its batch (`:1574`) and inner-state (`:1446`) siblings, and the legacy plain door (`emit.py:508`) all converged on the one pipeline, with the aggregate's pre-duplicated derivation/validation deleted, so that validation runs exactly once per emit. | High | Open |
| FR-007 | Batch/single `effective_root` parity (D7) | As an operator of owned missions, I want the batch door to gain the single door's owned-mission check and `effective_root` acquisition (default per Q5: parity — no evidence the divergence was intentional), so that the intra-file whack-a-field divergence is structurally impossible in the unified pipeline. | High | Open |
| FR-008 | Fan-out unification, phantom fan-out closed (D8) | As an orchestrator, I want all external fan-out deferred behind commit success in the coord arm (unifying on post-commit-deferred), so that an event announced via `emit.py:794` can never be truncated away afterward by `_restore_coord_status_artifacts`. | High | Open |
| FR-009 | Minimal doc correction, Mission C owns final text (D9) | As a reader of the status docs, I want the stale "single entry point" sentence (CLAUDE.md status section, correct as cited; `docs/architecture/04_implementation_mapping/README.md`, not `status-model.md` — see Ground-Truth Errata) corrected in-WP as a minimal stale-sentence hunk only, so that docs follow the code — while Mission C WP01 keeps the final word on the contended paragraphs (three writers: A-WP02, PR #3885, C-WP01). | Medium | Open |
| FR-010 | Facade strip to `status/_unsafe.py` | As a maintainer, I want the seven `append_*` entries in `status/__init__.py`'s `__all__` (lines 394, 518, 533, 536, 537, 538, 539 — see Ground-Truth Errata) moved to `status/_unsafe.py` behind a shrink-only caller allowlist, so that raw append access is explicit, enumerated, and only ever shrinks. | Medium | Open |
| FR-011 | AST writes-gate with non-vacuity floor | As a maintainer, I want an architectural AST gate rejecting any `open(.., "a")`/write on paths ending `status.events.jsonl` outside `status/store.py`, seeded from WP01's fixed census and equipped with a non-vacuity floor (a gate matching zero writers goes RED), so that the census cannot silently decay. First instance of the census-gate rule — to be noted on #3895 (the PR body requests the post). | Medium | Open |
| FR-012 | Dependency readiness as tri-state guard field (D10) | As an operator, I want dependency readiness added to `GuardContext` as a tri-state field, fail-OPEN on `None`, enforced by `validate_transition` on `planned→claimed` and `claimed→in_progress`, with `force` bypassing under actor+reason, so that a dep-blocked WP cannot be durably claimed through any write path. | High | Open |
| FR-013 | In-lock resolution on the transaction's surface (D11) | As an orchestrator under coord topology, I want the readiness verdict resolved INSIDE the lock/transaction against `txn.feature_dir` (the coord surface), so that the guard does not reproduce the pre-flight TOCTOU it exists to close, nor read stale primary state. The emit orchestration shells are the verdict supplier: they resolve readiness in-lock and populate the `GuardContext` field; `None` reaches `validate_transition` only from direct guard-level callers (the two probe sites), which fail open (C-004). | High | Open |
| FR-014 | Reuse `dependency_readiness_for_wp`; demote pre-flight copies (D12) | As a maintainer, I want the existing `dependency_readiness_for_wp` (`core/dependency_graph.py:34`, approved-OR-done semantics) reused — not reimplemented — and the 6 existing caller sites demoted to pre-flight UX (left in place, re-commented), so that gating semantics stay single-sourced and same-mission chains cannot deadlock. | Medium | Open |
| FR-015 | Atomic run-cursor writes (D13) | As an operator, I want `engine._write_snapshot` converted from plain `open("w")+json.dump` to the tmp-then-`os.replace` shape (`reducer.materialize` precedent, ~6 lines) and the journal `_append_event` hardened with it, so that a crash can never tear the run's authoritative cursor. | Medium | Open |
| FR-016 | `feature-runs.json` keyed by `mission_id`; loud missing-state (D14) | As an operator of same-slug missions, I want the run index keyed by `mission_id` with slug demoted to display, and a missing `state.json` with a live index entry raised as a loud structured error instead of a silent fresh run, so that the 083 collision class stays closed and run history is never orphaned. | Medium | Open |
| FR-017 | Pure progress read path (D15) | As an operator, I want `decision.py:373`'s writing `materialize(lane_read_dir)` (inside `try/except: pass`) swapped to the pure `materialize_snapshot`, so that a progress query can never clobber tracked `status.json` during scans — matching the three sites that already refuse this call. | Medium | Open |
| FR-018 | Batch door takes the mission status lock (D1/Q1) | As an orchestrator, I want the batch emit door (`emit.py:808-960`, confirmed lockless) to acquire `feature_status_lock` around its appends — placement per Q1 (WP01 vs WP02 stays open; default WP02) — so that the batch door's locked end-state (SC-008) traces to an explicit requirement rather than census language. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No lock across git in new code | No NEW code introduced by this mission holds an inter-process lock across a git subprocess (the repo's NFR-006, stated verbatim at `review/cycle.py:845-851`). The standing `BookkeepingTransaction` violation (`transaction.py:290`) is documented on the risk register (R9), NOT fixed here. **Amendment (2026-09-07, PR #3922 landing fold):** this NFR is now known to be violated by a second, sibling site: `coordination/status_transition.py::_emit_on_coord_then_commit`'s L1 take (added by the coord-fallback isolation fix, after this NFR was originally written) holds `feature_status_lock` across `_commit_status_artifacts_to_coord`'s `safe_commit` git subprocesses. It is accepted rather than redesigned, for the same reason the flat shell keeps L1 held through commit/rollback in the first place — releasing early would let a rollback erase a concurrent writer's successful append — and it is now bounded at `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS` (`status/locking.py:55`) instead of the lock's unbounded `-1` default, so a stalled sibling git subprocess surfaces as a structured `FeatureStatusLockTimeoutError` (naming the holder) rather than wedging every status writer for the mission forever. Tracked on the risk register (R9) alongside the `BookkeepingTransaction` case; see `design-notes/WP01-lock-rules.md` §3 for the corrected hierarchy statement. | Reliability | High | Open |
| NFR-002 | Replay purity | The reducer remains a pure fold with zero guard evaluation (zero `validate_transition`/`GuardContext` references in `reducer.py`); historical audit re-checks edge legality only. Measurable: a history containing a now-dep-illegal claim replays and audits without a guard flag. | Correctness | High | Open |
| NFR-003 | Bounded lock waits on outage-shaped paths | Every L1 acquisition reachable from an L3 scope, and the merge-path retrospective L1 take, uses a finite timeout with a structured timeout error naming the holder — never the default `-1` unbounded wait. | Reliability | High | Open |
| NFR-004 | Emit cost preserved | The pipeline promotion does not worsen the per-emit cost — verified structurally, not by timing: `_derive_from_lane` is still invoked at most once per emit and still reads the full log exactly once (call-count assertion), and no additional full-log reduction is introduced on the emit path (Q7 default: preserve). Log compaction stays a non-goal (follow-up to be posted on #3893 with the O(n²)-per-mission-life evidence — the PR body requests the post). | Performance | Medium | Open |
| NFR-005 | Test discipline | `make test-fast` baseline plus blast radius (`tests/status/`, coordination tests, targeted `tests/runtime/`) green per change; the full architectural suite is never run locally; terminology guard (`tests/architectural/test_no_legacy_terminology.py`) passes before any doc push. Red-first repros are transitional per C-009. | Process | Medium | Open |

### Constraints

Binding constraints C1–C10 from the research dossier §0 — invariants the implementation must not trade away.

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Coord/primary partition preserved (dossier C1) | Stored `COORD`/`LANES_WITH_COORD` topology ⇒ status writes land on the coord worktree + `safe_commit`, with truncate-rollback symmetry on commit failure, fail-loud via `FallbackCoordWorktreeUnresolved` (`coordination/status_transition.py:176`, `:259`, `:382-435`); `SINGLE_BRANCH`/`LANES`/flat ⇒ the legitimate primary-uncommitted write. Any collapse must ENCODE this FR-004 rows-7/8 contract, never flatten it. | Technical | High | Open |
| C-002 | NFR-006 lock/git separation (dossier C2) | No inter-process lock held across a git subprocess in new code. The `BookkeepingTransaction` L1-across-git standing violation is NOT this mission's to fix — risk register (R9) + follow-up note only, because WP01 grows the victim population of a hung-git-under-L1 stall. | Technical | High | Open |
| C-003 | 083 identity model (dossier C3) | `mission_id` is the only runtime identity — never slug for lookup, locking, or routing. This mission closes the two live violations: the slug-keyed `feature-runs.json` (`runtime_bridge_io.py:618`) and the slug-keyed status lock file (`locking.py:57-60`). | Technical | High | Open |
| C-004 | Guard tri-state, fail-OPEN on `None` (dossier C4) | The dependency guard fires only when the orchestrator supplies a readiness verdict. Fail-closed-on-`None` silently kills the two live probe sites (`lanes/recovery.py:78`, `src/specify_cli/cli/commands/agent/tasks_transition_core.py:337`). Sound because after WP03 no durable write bypasses the orchestrator. Do NOT copy `subtasks_complete`'s fail-closed polarity (`wp_state.py:370`). | Technical | High | Open |
| C-005 | Replay never validates (dossier C5) | The reducer is a pure fold; audit re-checks edge legality only, never guards. A new guard cannot retro-flag history — no guard evaluation on any replay/audit path. | Technical | High | Open |
| C-006 | Layering: status never imports coordination (dossier C6) | `status` is the MM-owned OHS facade; `coordination/status_transition.py` + `transaction.py` are exempted plumbing ABOVE it (`tests/architectural/test_status_module_boundary.py`). The lazy reach at `status/aggregate.py:624` (the `coordination.status_transition` import; `:623` is a `status.models` import — see Ground-Truth Errata) is the existing precedent-violation that bred the triple-orchestration mess — do not add another. This constraint kills the shim-over-coordination mechanism. | Technical | High | Open |
| C-007 | Three failure policies preserved (dossier C7) | Single transactional: fail-closed on unresolvable coord worktree (#1848/SC-001). Batch: `status_transition.py:1574`. Inner-state: deliberately degrades on `BookkeepingWorktreeMissing` (#3460, pinned by named tests). Plus the alias-collapse no-op arm. All stay explicit in the unified pipeline. | Technical | High | Open |
| C-008 | Plain-door callers keep semantics (dossier C8) | `contracts/anchoring.py`, `dossier/rebaseline.py`, `migration/verdict_provenance_backfill.py`, `runtime/next/runtime_bridge_composition.py` call plain `emit_status_transition` today; routing them through identity resolution (git subprocesses) or into committing writes for stored-`LANES` missions is a semantic change, not a refactor. Pinned by the no-new-commits test. | Technical | High | Open |
| C-009 | Red-first repros are transitional (dossier C9) | After each fix, red-first regression repros are deleted/replaced by unit tests or relocated to functional homes — never left marked regression. | Process | Medium | Open |
| C-010 | Test policy (dossier C10) | `make test-fast` baseline + blast radius; never the full arch suite locally; terminology guard before any doc push. | Process | Medium | Open |

### Key Entities

- **Status event log (`status.events.jsonl`)**: append-only JSONL stream; the FSM's SOLE authority for WP lane state. Every durable lane fact is an event here; the mission's entire purpose is the integrity of writes to it.
- **Writer family**: a code path that appends to the event log. Census (FR-001): 3 locked, 4 unlocked, plus the lockless batch door. Target end-state: every family locked+atomic or deleted, with gates preventing regression.
- **Emit pipeline (new)**: the promoted, status-owned, pure, I/O-parameterized function (alias-resolve → gate inference → alias-collapse → evidence → validation → event build) that all orchestrations share.
- **Composition shells (new, ×2)**: flat/primary (lock + atomic append + materialize + immediate fan-out) and transactional (txn + post-commit-deferred fan-out); each carries its explicit failure policy (C-007).
- **`GuardContext`**: the guard-input record consumed by `validate_transition`; gains one tri-state dependency-readiness field (fail-OPEN on `None`).
- **`feature_status_lock`**: the inter-process mission status lock (L1); re-entrant; keyed after FR-004 by `feature_dir.name`.
- **`feature-runs.json` index + run cursor (`state.json`)**: the runtime run-state store; after FR-015/016 keyed by `mission_id` with atomic cursor writes and loud missing-state errors.
- **`status/_unsafe.py` (new)**: the explicit home for raw `append_event*` access with a shrink-only caller allowlist.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The rollback-truncate repro (raw retrospective append inside the `transaction.py:944` truncate window) is RED before WP01 and GREEN after — the interleaved event survives every forced-rollback run.
- **SC-002**: The phantom fan-out repro (coord fallback, forced commit failure) is RED before WP02 and GREEN after — zero external fan-out calls recorded for any truncated event.
- **SC-003**: The batch-door divergence pins (owned-mission refusal; fan-out ordering) are RED before WP02; after the collapse they are replaced by delegation-equivalence tests (per C-009) and the divergence is structurally unexpressible (one pipeline, two shells).
- **SC-004**: A synthetic out-of-pipeline append to `status.events.jsonl` reds the writes-gate; a gate scan matching zero writers also reds (non-vacuity floor); the `_unsafe` allowlist refuses growth.
- **SC-005**: A verdict-less direct emit claiming a dep-blocked WP succeeds on main (the RED repro) and is refused after WP04 — because the emit orchestration shells resolve readiness in-lock and populate the guard field (FR-013), not because bare `validate_transition` fails closed; both probe sites still pass with a `None` readiness field (fail-OPEN, C-004); the force + same-mission-chain matrix (approved⇒allowed, in_progress⇒blocked, force⇒bypassed-with-reason) is green.
- **SC-006**: Two missions with colliding slugs resolve distinct lock files AND distinct runs (RED before WP01/WP05 respectively); a kill between cursor truncate and rewrite leaves a recoverable state; the progress query leaves tracked `status.json` byte-identical; a missing `state.json` with a live index entry raises a structured error.
- **SC-007**: The no-new-commits plain-door pin (stored-`LANES` mission, plain door, zero new commits) is green on main BEFORE the collapse and stays green throughout and after it.
- **SC-008**: Writer census end-state: 0 unlocked writer families; the batch door takes the lock; a lock-held assertion passes for every family. All three pre-existing failure-policy test pins stay green.
- **SC-009**: `make test-fast` + the blast-radius suites (`tests/status/`, coordination, targeted `tests/runtime/`) green at every WP boundary; the terminology guard green before any doc push.

## Open Decisions (operator) *(proto-mission — carried explicitly, never silently resolved)*

These are the dossier's operator-pending questions (Q1–Q10). Each must be answered during spec refinement or the named gate; the spec records defaults where the dossier states them.

- **[NEEDS DECISION: Q4 — the NAMED orchestrator (operator decision B3). MUST be resolved BEFORE WP02 starts.]** Which surface is *named* the one orchestrator: `MissionStatus` (the aggregate, per the Accepted ADR chain #1667/C-004) composed over the promoted status-owned pipeline, or the pipeline itself with the aggregate as one caller? The debrief recommends the aggregate per the existing decision records; record the answer in the WP02 design note. The wrong choice re-inverts C-006 or silently changes commit semantics.
- **[NEEDS DECISION: Q1 — batch-door lock placement.]** Does the batch door get its lock (FR-018) in WP01 (at the emit/store layer, immediately) or as part of the WP02 shell composition (one change instead of two)? The WP slicing below assigns it to WP02 to keep files single-owner; answering "WP01" moves the batch-lock hunk and adds `emit.py` to a declared shared file. Planning proceeds on the default (WP02); the operator override window closes at tasks-finalize.
- **[NEEDS DECISION: Q2 — finite default L1 timeout.]** Is a finite DEFAULT L1 timeout (+ structured timeout error naming the holder) in scope, or a named cheap follow-up? (Dossier leans follow-up; the merge-path finite timeout of FR-003(b) is in scope either way.)
- **[NEEDS DECISION: Q3 — superseded retrospective writer.]** Harden `retrospective/events.py` (largely the superseded `run_terminus` path, "do not add new callers"), or fold its hardening into a deprecation/removal note and prioritize `retrospective/lifecycle_events.py`? (Default: harden both; the live one first.)
- **[NEEDS DECISION: Q5 — batch parity vs adjudicated intent.]** Does the batch shell gain the single shell's owned-mission/`effective_root` handling (FR-007's default: parity), or is any part of the divergence adjudicated as intentional? (No evidence of intent found.)
- **[NEEDS DECISION: Q6 — landing spot for the five `_emit` privates.]** Do `_derive_from_lane`, `_generate_ulid`, `_mirror_phase1_frontmatter_lane`, `build_status_event`, `_infer_subtasks_complete` become pipeline-internal privates or narrow public helpers? (Hard constraint: the phase-gated frontmatter `lane` mirror must remain the tree's ONLY `write_frontmatter` of `lane` — `test_2093_authority_invariant.py`.) Decider: the refining team, within that hard constraint — blocks implementation detail only, not planning.
- **[NEEDS DECISION: Q7 — emit cost.]** Does WP02 merely preserve the O(n) `_derive_from_lane` cost, or is the cheap snapshot-anchored read allowed in-scope? (Default: preserve; flag follow-up on #3893. Compaction stays a non-goal regardless.)
- **[NEEDS DECISION: Q8 — guard polarity, confirm explicitly.]** Fail-open-on-`None` (C-004, the default) vs updating both probe sites to supply verdicts and going fail-closed. The spec should confirm fail-open and record WHY (probe sites + no-bypass-after-WP03), so a future reader does not "fix" the polarity to match `subtasks_complete`.
- **[NEEDS DECISION: Q9 — run-index migration shape.]** In-place rekey on first touch vs a one-shot migrate step; and the key for legacy missions without `mission_id` (the transaction's `legacy-<slug>` fallback at `status_transition.py:1606` is the precedent — adopt it?). Decider: operator (the legacy-key choice) — blocks implementation detail only, not planning.
- **[NEEDS DECISION: Q10 — WP05 lane assignment vs Mission B.]** WP05 shares all four contended runtime files with Mission B: stay in Mission A behind an "A goes first" ordering (the debrief's answer, assumed by the interference map below), move to Mission B, or become the declared single-owner shared lane? Recorded default (planning proceeds on it): WP05 stays in Mission A, behind A-first ordering; the operator override window closes at tasks-finalize.

## Explicit Non-Goals

Stated verbatim from the research dossier §5:

1. **No port inversions** — StatusReader/StatusWriter (#2173) are NOT built here. A-WP02 only *shapes* the seam (the status-owned pipeline is the future StatusWriter cut). The StatusReader port is **de-serialized** from this mission (Renata correction C3 of report 23; to be recorded via a #2173 tracker note — the PR body requests the post; no such note exists there yet) — do not reintroduce the false dependency.
2. **No runtime facade work** — Mission D (`runtime-public-surface-seam`, queued behind PR #3888) owns the `_internal_runtime` promotion/facade and the `runtime` naming collision.
3. **No event-log compaction / snapshot-anchored reads** — flag as follow-up on #3893 with the O(n²) evidence: `_derive_from_lane` reduces the FULL log on every emit (O(n) per transition over an append-only log with no compaction story). Currently unowned.
4. **No `transaction.py` rollback-atomicity redesign** — the truncate/restore pair is two independently-guarded non-atomic steps (`transaction.py:922-971` — quoted as-is from `orchestrator_api/commands.py:3608`'s own in-code citation and not independently re-verified here; that citation is itself imprecise, `_rollback` actually starts at `:927`; live-reproduced per `orchestrator_api/commands.py:3600-3614` region). Document the crash window; defer (item 16 / R9). Same for the NFR-006 L1-across-git standing violation (C2) — risk register + follow-up note, not in-scope.
5. **No `status/adapters.py` fan-out registry redesign** — live and wired (the E3/zeitgeist seam); leave it. No zeitgeist/upstream work; no `RuntimeEventEmitter` disposition (Mission B WP01 [sic — B-WP03/P4 per B's own spec], with its own decision record per debrief B2).
6. **No `wp_state.py` edge/guard/force logic changes** — it is the healthy, ratified part; WP04 only adds one guard field + clause through the established `GuardContext` shape.
7. **No event schema changes**; no snapshot-drift-on-read chokepoint (accepted risk; follow-up home is the read-chokepoint drift check named in report 24 §6-6).

## Interference Map

### Mission B (`dead-port-disposition`) — NOT parallel-safe; **A goes first**

Four shared files (verified at HEAD; "A ∥ B disjoint" is FALSE):

| File | Mission A touch | Mission B touch |
|---|---|---|
| `runtime/next/runtime_bridge_io.py` | WP05 rekeys the index (`:611-660`) | B emitter slice (B-WP03/P4, ADR-gated): `NullEmitter` import (`:95`), constructions (`:592,:643`) |
| `runtime/next/_internal_runtime/engine.py` | WP05 `_write_snapshot` (`:128-130`) | B emitter slice (B-WP03/P4): four `emitter or NullEmitter()` entry defaults at `:198`, `:259`, `:522`, `:795` (not the loose range `:191-795` — see Ground-Truth Errata) |
| `runtime/next/decision.py` | WP05 `materialize`→`materialize_snapshot` (`:373`) | B routes the dead DSL readers — `derive_mission_state` (~187-210) and `evaluate_guards` (~218-273; not `:194-235`, which starts mid-docstring and covers neither cleanly — see Ground-Truth Errata) — via its Open Decision 9 (default: this mission's WP05 lane absorbs them); the `mission_v1.events` import (`:200`) stays a live consumer B preserves (its FR-003) |
| `runtime/next/runtime_bridge_engine.py` | adjacent to all WP05 bridge-satellite work | 16 of 29 production `sync_emitter` sites |

B's own spec does not assign WP labels to its user stories (it slices by priority P1-P4, not by WP number); it names only "WP03" once, for the emitter ADR gate check. `decision.py` dead-reader ownership is B's Open Decision 9.

Resolution: **Mission A first, Mission B after (or a declared single-owner shared lane for exactly these four files)** — the final choice is open decision Q10 (recorded default: A first, WP05 stays in A).

### PR #3888 (runtime governance ledger) — no source-file conflict, one binding mental model

- #3888 (tip `a86907a52d`) touches docs/ADRs, its kitty-specs, pyproject, `tests/architectural/*` — none of Mission A's status/coordination/retrospective/migration surfaces. A-WP05's runtime edits stay inside already-ledgered subpackages (`status`, `mission_metadata`, `mission_v1`, `retrospective`) — no ledger change for A.
- **Binding model: `test_runtime_ledger_has_no_stale_entries` REDS when a subpackage's last live edge is removed** — shrinking *forces* a same-PR ledger edit; it does not merely tolerate shrink. Any A/B refactor that removes a ledgered lazy reach budgets the ledger edit in the same PR. Likewise the widened doctrine scan pins `runtime_bridge_composition.py` / `runtime_bridge_io.py` in its baseline — removing those lazy reaches means updating that baseline in-PR. Whichever of B/#3888 lands second rebases.

### Doc contention

CLAUDE.md status section + `docs/architecture/04_implementation_mapping/README.md` (not `status-model.md` — see Ground-Truth Errata): three writers (A-WP02, PR #3885 docs alignment, Mission C WP01). **Mission C owns the final text** (FR-009); A-WP02's doc edit is the minimal stale-sentence correction only.

## Risk Register

Carried from the research dossier §8; all mitigations already folded into the requirements above.

| # | Risk | Mitigation home |
|---|---|---|
| R1 | WP02 shim direction inverts layering / misses batch+inner-state+aggregate | FR-005/FR-006 (layered extraction, full scope, resized 4–5 days) |
| R2 | Plain-door callers silently gain commit semantics | C-008 pin test (US2-3) |
| R3 | Phantom fan-out for rolled-back coord-fallback events | FR-008 red-first (US2-1) |
| R4 | Fail-closed `None` guard breaks recovery + FR-015 probe | C-004/FR-012 + probe tests (US4-2) |
| R5 | Readiness resolved outside lock / wrong surface | FR-013 (US4-4) |
| R6 | Census drift (mission_creation false positive; live retro writer missed) | FR-001 |
| R7 | New L1 takers under L3/L5 convert stalls into outages | FR-003 rules a+b, NFR-003 |
| R8 | Lock-key divergence ⇒ silent non-serialization | FR-004 (US1-3) |
| R9 | L1-across-git NFR-006 standing violation amplifies as acquirers grow | risk register + #3893 note; finite-timeout follow-up (Non-Goal 4) |
| R10 | WP01 red-first won't go red as originally drafted | corrected repro shapes (US1-1: rollback-truncate race, NOT concurrent appends — POSIX `O_APPEND` whole-line buffered writes land atomically) |
| R11 | A ∥ B collide on 4 runtime files | Interference map (A first / shared lane; Q10) |
| R12 | Three-way doc contention | FR-009 (Mission C final word) |

## Proposed Work-Package Slicing (indicative — proto-mission; tasks phase will finalize)

Dependency shape: WP01 → WP03 (gates need the fixed census to be green-able); WP02 → WP04 (guard lands in the unified pipeline); WP05 independent (subject to Q10). WP01 ∥ WP02 are separable: WP01 owns the *out-of-pipeline* writers; WP02 owns the pipeline modules. The batch-door lock is assigned to WP02 to keep files single-owner (see Q1).

| WP | Slice | Red-first target (defect anchor) | owned_files sketch |
|---|---|---|---|
| **WP01** — serialize the out-of-pipeline writers | Lock+atomic-append the 4 unlocked families (FR-001/002); encode the 3 lock rules (FR-003); lock key → `feature_dir.name` (FR-004) | Rollback-truncate race (`transaction.py:944` window; RED); backfill two-append + `:1497` TOCTOU; lock-key collision test | `retrospective/events.py`, `retrospective/lifecycle_events.py`, `migration/verdict_provenance_backfill.py`, `migration/backfill_runtime_state.py`, `status/locking.py`, (touch) `merge/executor.py` retro-path timeout, tests |
| **WP02** — layered pipeline extraction (**the mission's core; 4–5 days, binding**) | Promote `_prepare_event` into `status/` pure pipeline + two shells (FR-005); converge 3 orchestrations + aggregate (FR-006); batch-door lock (FR-018) + `effective_root` parity (FR-007); fan-out unification + phantom-fan-out fix (FR-008); minimal doc correction (FR-009) | Phantom fan-out pre-commit (`status_transition.py:401-432` + `emit.py:794`; RED); batch owned-mission divergence (`:1342-1345` vs `:1605+`; RED); no-new-commits plain-door pin (C-008) | `status/emit.py`, `status/aggregate.py`, new `status/<pipeline>.py`, `coordination/status_transition.py`, CLAUDE.md + `docs/architecture/04_implementation_mapping/README.md` (stale-sentence hunks only), tests |
| **WP03** — facade strip + write gates | `append_event*` → `status/_unsafe.py` shrink-only allowlist (FR-010); AST writes-gate with non-vacuity floors (FR-011); #3895 census-gate-rule note (to be posted via the PR body) | The two gates themselves, seeded from WP01's fixed census, with non-vacuity floors (a gate matching zero writers goes RED) | `status/__init__.py`, `status/_unsafe.py` (new), `tests/architectural/` (2 new gates) |
| **WP04** — dependency guard | Readiness → `GuardContext`, tri-state fail-open (FR-012/C-004); resolve in-txn on `txn.feature_dir` (FR-013); reuse + demote (FR-014) | Direct emit claims dep-blocked WP — succeeds today (RED); probe-site `None` regressions; force + chain-order tests | `status/models.py` (GuardContext), `status/wp_state.py` (guard clause only), pipeline touch-point from WP02 (single owner: WP02's new `status/<pipeline>.py`; WP04's edit is declared rationale-backed leeway — WP04 depends on WP02), comment-edits at the 6 caller sites, tests |
| **WP05** — run-state hardening | Atomic `_write_snapshot` (FR-015); `mission_id` key + loud missing-state (FR-016); pure read (FR-017). Conditional intake: MAY additionally absorb the two dead DSL readers in `decision.py` (`derive_mission_state`, `evaluate_guards`) if Mission B's Open Decision 9 routes them here — a pure-deletion rider, zero callers verified | Slug-collision distinct runs (RED, `runtime_bridge_io.py:618`); crash-window cursor; read-path purity; missing-state loud error | `runtime/next/_internal_runtime/engine.py`, `runtime/next/runtime_bridge_io.py`, `runtime/next/decision.py`, (maybe) `runtime_bridge.py` `_load_feature_runs`, tests |

Note on WP04's `wp_state.py` vs Non-Goal 6: WP04 adds the one guard field/clause via the established `subtasks_complete` shape (`emit.py:650-662` precedent) — it does not restructure edges, force, or terminal rules.

## References & Evidence Chain

- **Parent epic (to be wired)**: #3893. Nothing is posted on the tracker yet — the PR body requests: mint this mission's tracker issue under #3893; reconcile the milestone (#3893 is currently 4.0.0 while this mission targets 3.2.7 — one of them changes); post the event-log-compaction follow-up (Non-Goal 3, with the O(n²) evidence) and the NFR-006 finite-timeout follow-up (R9) on #3893; post the StatusReader de-serialization note on #2173.
- **Related issues**: #2173 (infra-logic port inversions — StatusReader de-serialized from this mission, StatusWriter seam shaped-not-built), #1666 / #1868 (status-authority lineage), #1667/C-004 (the Accepted ADR chain naming `MissionStatus` the authoritative write facade — bears on Q4), #1848 (fail-closed transactional policy), #3460 (inner-state degrade policy), #3773 (the L3→L1 deadlock class), #3895 (census-gate rule, first instance in WP03).
- **Adjacent work**: PR #3888 (runtime governance ledger — interference map above), PR #3885 (docs alignment — doc contention), Mission B `dead-port-disposition` (four shared runtime files, Q10), Mission C (final doc text), Mission D `runtime-public-surface-seam` (runtime facade, Non-Goal 2). Missions C and D are planned-but-unminted (no kitty-specs entry, no tracker issue yet); the obligations recorded here are self-contained regardless.
- **Ground truth**: `research/28-missionA-research-dossier.md` (this mission's dossier; consolidation of reports 21/22/23/24 + 27 §2/§4, including report 27's seven binding amendments; all anchors re-verified at HEAD `e721763759` on 2026-09-06). The in-mission dossier fully subsumes the `work/post-convergence/` session reports (19–27): those files are session-local provenance only (gitignored, machine-local, untracked) and are NOT required to plan or implement — refinement needs only the dossier.
- **Verification deltas recorded in the dossier §9** (e.g., truncate at `transaction.py:944` not `:943`; `resolve_status_lock_root` in `workspace/root_resolver.py`, not `status/`; the batch door confirmed lockless) are binding over the underlying reports.
