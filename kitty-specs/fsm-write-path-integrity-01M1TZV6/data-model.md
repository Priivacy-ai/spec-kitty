# Data Model: FSM Write-Path Integrity

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **Date**: 2026-09-06
**Scope**: entities the mission creates or changes, their invariants, and the state transitions it touches. No event schema changes (non-goal 7). No new persistent formats except a rekeyed run index.

---

## 1. Status event log — `status.events.jsonl` (existing; write discipline changes)

| Field | Type | Notes |
|---|---|---|
| (row) | one JSON object per line, `StatusEvent` | unchanged schema |

**Invariants (after this mission)**
- I-1 Every append is performed while `feature_status_lock(<key>)` is held by the appending process (SC-008 lock-held assertion, all seven writer families + batch door).
- I-2 Every append is atomic at the store primitive (`append_*_atomic_verified` family or the transaction's append) — never a bare `open(path, "a")` outside `status/store.py` (WP03 AST gate).
- I-3 A rollback truncate (`transaction.py:944`, `fh.truncate(self._pre_emit_size)`) can only run while the same lock is held, so no concurrent legitimate append can land inside the window (SC-001).
- I-4 The log is the sole authority; replay (`reducer.reduce`) is a pure fold with zero guard evaluation (NFR-002).

---

## 2. Writer family (concept; census governed by FR-001)

| # | Family | Module:line (HEAD) | Lock today | After |
|---|---|---|---|---|
| ① | emit single + inner-state | `status/emit.py:634`, `:1013` | L1 | L1 (flat shell) |
| ② | lifecycle appender | `status/lifecycle_events.py:538` → `_lifecycle_write_lock:234-254` | L1 | L1 |
| ③ | `BookkeepingTransaction` | `coordination/transaction.py:290` | L1 (txn lifetime) | L1 |
| ④ | retrospective run-terminus | `retrospective/events.py:213` raw `open("a")` | none | L1 + atomic (WP01) |
| ⑤ | retrospective lifecycle | `retrospective/lifecycle_events.py:250-256`; Lamport read `:265` | none | L1 + atomic; read in-lock (WP01) |
| ⑥ | verdict-provenance backfill | `migration/verdict_provenance_backfill.py:419` | none (atomic) | L1 (WP01) |
| ⑦ | runtime-state backfill | `migration/backfill_runtime_state.py:1533`, `:1535`; idempotency read `:1497` | none (atomic ×2) | one L1 acquisition covering read + both appends (WP01) |
| — | batch door | `status/emit.py:808-960` | **none** | L1 (WP02, FR-018) |

Excluded: `core/mission_creation.py` (routes via ②; direct touch is `touch(exist_ok=True)`).

---

## 3. Mission status lock — L1 (existing; key changes)

| Attribute | Today | After (WP01, FR-004) |
|---|---|---|
| Path | `<git common dir>/<LOCK_DIRECTORY>/<mission_slug>.status.lock` (`locking.py:57-60`) | `<git common dir>/<LOCK_DIRECTORY>/<feature_dir.name>.status.lock`, root via `resolve_status_lock_root(feature_dir, repo_root)` |
| Re-entrancy | yes (3 deep in production) | unchanged |
| Default timeout | `-1` (unbounded) | unchanged by default (Q2 follow-up); **finite** on L3-reachable takes and the merge-path retrospective take (NFR-003) |
| Timeout error | — | structured error naming the holder (new, on the finite-timeout sites) |

**Invariants**
- L-1 Two missions with distinct `feature_dir.name` never share a lock file, even with equal `mission_slug`.
- L-2 A bare/legacy slug directory's writers use the same lock file as that mission's pipeline writers.
- L-3 No new code path acquires L1 and then spawns a git subprocess while holding it (NFR-001); the standing `BookkeepingTransaction` case is documented, not changed.
- L-4 Hierarchy has no inverse edges: L5 → L1; L3 → L1 (bounded); L1 → L4 → git (transaction only).

---

## 4. Transition pipeline (NEW, WP02) — value-level contract in `contracts/emit-pipeline.md`

**Type**: pure function; inputs are values + injected readers; output is a value.

| Input | Type | Source |
|---|---|---|
| `request` | `TransitionRequest` | caller |
| `from_lane` | `str` | shell derives in-lock (`_derive_from_lane`, ≤1 call, one full read — NFR-004) |
| `mission_slug`, `mission_id` | `str`, `str \| None` | shell identity |
| `feature_dir` | `Path` | the shell's write surface (`txn.feature_dir` for transactional) |
| `readiness` | `DependencyReadiness \| None` | shell resolves in-lock against `feature_dir` (WP04, FR-013) |
| `subtasks_dir_resolver`, `evidence_reader` | callables | injected I/O (default = today's helpers) |

| Output | Type | Meaning |
|---|---|---|
| `PreparedTransition` | frozen dataclass | `event: StatusEvent \| None` (None = alias-collapse no-op arm), `resolved_lane: str`, `annotation: StatusEvent \| None`, `mirror_lane: bool` |

**Invariants**
- P-1 Contains no lock acquisition, no file writes, no git, no fan-out. (Enforced by `test_status_module_boundary.py` plus a unit test that runs it against an in-memory feature dir.)
- P-2 `validate_transition` is called exactly once per emit across the whole tree (the aggregate's duplicate at `aggregate.py:685` is deleted).
- P-3 Imports nothing from `coordination` (C-006).

---

## 5. Composition shells (NEW as named concepts, WP02)

| Shell | Module | Steps (in order) | Failure policy (C-007) |
|---|---|---|---|
| flat/primary | `status/emit.py` (`emit_status_transition`, batch) | lock → derive from-lane → readiness → pipeline → atomic append → materialize → mirror → **release** → fan-out | flat/`LANES`/`SINGLE_BRANCH`: uncommitted primary write; alias-collapse arm: mirror only, no append |
| transactional | `coordination/status_transition.py` (single `:1318`, batch `:1574`, inner-state `:1446`) | txn.acquire (L1) → derive → readiness → pipeline → txn.append → `defer_outbound(fan-out)` → commit → release → deferred fan-out fires | single: fail-closed on unresolvable coord worktree (#1848); batch: `:1574` policy; inner-state: degrade on `BookkeepingWorktreeMissing` (#3460) |
| coord fallback arm | `status_transition.py:401-432` (calls flat shell on the coord fd) | flat shell **with fan-out suppressed** → commit → on success fan-out; on failure truncate-restore, no fan-out | fail-loud `FallbackCoordWorktreeUnresolved` |

**Invariants**
- S-1 External fan-out fires only after the durable commit succeeds in any coord arm (SC-002).
- S-2 The batch shell applies the owned-mission `ActionContextError` check and `effective_root` acquisition identically to the single shell (Q5 parity).
- S-3 Exactly two shell kinds exist; a third composition of lock + append is a gate violation (R14).

---

## 6. `GuardContext` (existing; +1 field, WP04)

| Field | Type | Default | Semantics |
|---|---|---|---|
| … existing 10 fields … | | | unchanged |
| `dependency_ready` | `bool \| None` | `None` | `None` = no verdict supplied ⇒ guard passes (C-004); `False` ⇒ refuse `planned→claimed` and `claimed→in_progress` unless `force` with actor+reason; `True` ⇒ pass |

**State transitions touched** (9-lane machine unchanged):
```
planned ──claim──▶ claimed ──start──▶ in_progress
        [dependency_ready is not False, or force]   [same]
```
All other edges, `force`, terminal rules: unchanged (non-goal 6).

**Readiness source**: `dependency_readiness_for_wp(wp_id, dependencies, wp_lanes, provenance)` (`core/dependency_graph.py:34`); `satisfied` iff every dependency is `approved` | `done` | `canceled`-with-operator-provenance.

---

## 7. `status/_unsafe.py` (NEW, WP03)

| Symbol | Type | Notes |
|---|---|---|
| `append_event`, `append_event_verified`, `append_event_stream_atomic_verified`, `append_events_atomic_verified`, `append_primary_checkout_event_verified`, `append_primary_checkout_events_atomic_verified` | re-exports from `status/store.py` | removed from `status/__init__.__all__` (`:518-537`) |
| `ALLOWED_CALLERS` | `frozenset[str]` of module paths | seeded from WP01's fixed census (families ②③⑤⑥⑦ + both shells); **shrink-only** — a test asserts the set is a subset of the committed baseline |

---

## 8. Run-state store (existing; rekeyed + hardened, WP05)

### 8.1 `feature-runs.json` index

| Today | After |
|---|---|
| `{ "<mission_slug>": { "run_id", "run_dir", "mission_type"\|"mission_key" } }` (`runtime_bridge_io.py:611-660`) | `{ "<mission_id>": { "run_id", "run_dir", "mission_type", "mission_slug" (display) } }`; legacy missions keyed per Q9 (precedent `legacy-<slug>`) |

**Invariants**
- RS-1 Two missions with equal `mission_slug` and distinct `mission_id` resolve distinct runs (SC-006).
- RS-2 A live index entry whose `run_dir/state.json` is absent raises a structured error (loud), never falls through to "start a new run" (`:617-627` today).

### 8.2 Run cursor `state.json` and journal `run.events.jsonl` (`_internal_runtime/engine.py`)

| Write | Today | After |
|---|---|---|
| `_write_snapshot` (`:128-130`) | `open("w")` + `json.dump` (torn-write window) | write `state.json.tmp` → `os.replace` (the `reducer.materialize` shape) |
| `_append_event` (`:110-119`) | bare `open("a")` | same tmp/replace or atomic-append discipline (journal is local; no L1 involved) |

**Invariant** RS-3: a process kill at any instruction boundary leaves either the previous `state.json` or the complete new one; never a partial file.

### 8.3 Progress read (`runtime/next/decision.py:369-377`)

| Today | After |
|---|---|
| `materialize(lane_read_dir)` (writes `status.json`) inside `try/except: pass` | `materialize_snapshot(lane_read_dir)` (pure) |

**Invariant** RS-4: tracked `status.json` is byte-identical before and after the progress query.

---

## 9. Externally visible events

Unchanged payloads: SaaS transition emission (`queue_saas_emission` / `_saas_fan_out`), resolved-binding fan-out, zeitgeist via `status/adapters.py`. **Only timing changes**: in every coord arm, fan-out is deferred until after the coord commit succeeds; on commit failure, zero fan-out (SC-002).
