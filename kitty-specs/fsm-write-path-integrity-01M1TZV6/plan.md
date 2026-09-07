# Implementation Plan: FSM Write-Path Integrity

**Branch**: `missions/coreloop-proto-missions` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)
**Input**: Mission specification from `kitty-specs/fsm-write-path-integrity-01M1TZV6/spec.md`; ground truth `research/28-missionA-research-dossier.md`; planning decisions in `decisions/` (DM-01M1V80R…, DM-01M1V8HS…, DM-01M1V8HV…, DM-01M1V8HX…, DM-01M1V8HZ…, DM-01M1V8J0…, DM-01M1V8J2…, DM-01M1V8J4…, DM-01M1V8J6…, DM-01M1V8J8…).

**Branch contract**: current branch at plan start `missions/coreloop-proto-missions`; planning/base branch `missions/coreloop-proto-missions`; completed changes merge into `missions/coreloop-proto-missions` (the PR #3904 branch, which itself targets `main`). `branch_matches_target: true`.

## Summary

Harden the mission status write path without redesign. Every writer of `status.events.jsonl` is serialized under the mission status lock with atomic appends (WP01). The three parallel emit orchestrations converge on ONE status-owned, pure, I/O-parameterized pipeline composed by exactly two shells, with all external fan-out deferred behind commit success (WP02). Raw append access moves behind a shrink-only allowlist and an AST writes-gate (WP03). Dependency readiness becomes a tri-state, fail-open `GuardContext` field resolved in-lock by the shells (WP04). The runtime run-state store becomes `mission_id`-keyed, crash-safe, and read-pure (WP05).

**Named authority (Q4, resolved)**: the promoted pipeline is the single validation-and-event-build authority. `MissionStatus` remains the intended domain facade for callers but is NOT the write chokepoint in this mission; its eight bypassing callers do not migrate. This is recorded as an amendment note to the #1667 / C-004 ADR chain (directive 003) in the WP02 design note. See `research.md` §1 for the full argument and the evidence (AST caller census).

## Technical Context

**Language/Version**: Python 3.11+ (repo floor; `pyproject.toml`)
**Primary Dependencies**: standard library only for the write path (`os.replace`, `fcntl`-backed `feature_status_lock`, `json`, `ast` for the gate); pydantic (existing, `GuardContext`/`StatusEvent` models); pytest + pytest-xdist (existing). **No dependency additions, upgrades, or removals** — supply-chain check records "no dependency change" (see `research.md` §7).
**Storage**: file-based — `kitty-specs/<mission>/status.events.jsonl` (append-only JSONL, FSM sole authority), `status.json` (materialized snapshot), `.git/<common-dir>/spec-kitty-locks/<key>.status.lock` (L1 lock files), `.kittify/runtime/feature-runs.json` (run index) + `.kittify/runtime/runs/<run_id>/state.json` (run cursor) + `run.events.jsonl` (run journal)
**Testing**: pytest; `make test-fast` baseline + blast radius `tests/status/`, `tests/specify_cli/status/`, `tests/specify_cli/coordination/`, `tests/specify_cli/retrospective/`, `tests/specify_cli/migration/`, `tests/specify_cli/merge/`, `tests/specify_cli/lanes/`, targeted `tests/runtime/` (`test_bridge_io.py`, `test_bridge_engine.py`, `next/`); `tests/architectural/test_status_module_boundary.py` + the two new gates; terminology guard `tests/architectural/test_no_legacy_terminology.py` before any doc push. Red-first repros are transitional (C-009).
**Target Platform**: macOS / Linux developer checkouts and CI (Blacksmith producer `ci.yml`); Windows CI (`ci-windows.yml`) for the atomic-write paths (`os.replace` semantics differ — see risk R13 in `research.md`)
**Project Type**: single Python package (`src/specify_cli`, `src/runtime`) — existing layout, no structural change
**Performance Goals**: emit cost preserved structurally (NFR-004): `_derive_from_lane` invoked at most once per emit, full log read exactly once; asserted by call-count, not timing. No compaction (non-goal 3).
**Constraints**: C-001..C-010 from the spec verbatim; NFR-001 no new lock-across-git; NFR-002 replay purity (zero `validate_transition`/`GuardContext` in `reducer.py`); NFR-003 bounded waits on L3-reachable and merge-path L1 takes; layering `status` never imports `coordination` (`test_status_module_boundary.py`); `test_2093_authority_invariant.py` — the phase-gated frontmatter `lane` mirror stays the tree's only `write_frontmatter` of `lane`; `test_runtime_ledger_has_no_stale_entries` reds if a ledgered lazy reach is removed (budget the ledger edit in-PR)
**Scale/Scope**: 5 WPs; WP02 is the core at 4–5 days (binding); ~12 source modules touched, 2 new modules (`status/<pipeline>.py`, `status/_unsafe.py`), 2 new architectural gates; every WP ships its red-first repro, its unit tests for new helpers, and deletes/relocates the repro on green (C-009)

**Deferred decisions**: Q6 and Q9 were resolved during implementation (WP02 / WP05 design notes; decision records `01M1V8J667A286GPHKTWYB1WCS`, `01M1V8J842E7CJR6MGZ0MW3DQF`).

## Charter Check

*GATE: evaluated against `.kittify/charter/charter.md` (loaded via `spec-kitty charter context --action plan`, mode `bootstrap`). Re-checked post-design in §Post-Design Charter Re-check.*

| Principle / standing order | Status | How this plan satisfies it |
|---|---|---|
| Single canonical authority | PASS | One pipeline is the named validation/build authority (Q4); one lock key convention (FR-004); one readiness source `dependency_readiness_for_wp` (FR-014); one raw-append home `status/_unsafe.py` (FR-010). |
| Architectural alignment (shared-package boundary, layer rules) | PASS | Pipeline lands in `status/` (direction `kernel ← charter ← {runtime, …} ← specify_cli` untouched); no new `status → coordination` reach; WP05 stays inside already-ledgered runtime subpackages (no `_RUNTIME_ALLOWED_SPECIFY_CLI` change). |
| DDD + tiered rigour | PASS | Mission Management owns the status aggregate; the pipeline is the domain's pure core; shells are the imperative edge; `GuardContext` gains one field via the established shape. |
| ATDD-first | PASS | Every WP is anchored on a RED-on-main repro named in the spec (SC-001..SC-008); `quickstart.md` gives the commands. |
| Terminology adherence | PASS | "Mission", "work package", "status commit", "lane"; no `feature*` aliases introduced; terminology guard runs before doc pushes (NFR-005). |
| Decision documentation (directive 003) | PASS | Ten decision records in `decisions/`; Q4 amends the #1667 chain via the WP02 design note. |
| Close defect class by construction (043) | PASS | Whack-a-field divergence becomes structurally unexpressible (one pipeline); gates (WP03) prevent census decay; non-vacuity floors prevent vacuous gates. |
| Locality of change (024) / smallest viable diff | PASS with justification | WP02 is large by necessity (three orchestrations + aggregate); scope is bounded by explicit non-goals 1–7. See Complexity Tracking. |
| Test-first (034) / red-first transitional (C-009) | PASS | Each WP: red repro → fix → unit tests for extracted helpers → repro deleted or relocated. |
| Mission tracer files / campsite cleaning | PASS | Stale "single entry point" sentence corrected minimally (FR-009); the stale "only 2 of 6" comment re-labelled historical (FR-001). |
| No lock across git (NFR-006 repo rule) | PASS (new code) | Standing `BookkeepingTransaction` violation documented on the risk register, not fixed (C-002). |
| Draft-PR-first, operator merges | PASS | Lands on the PR #3904 branch; operator merges. |

No violations requiring Complexity Tracking justification beyond WP02's size (below).

## Project Structure

### Documentation (this mission)

```
kitty-specs/fsm-write-path-integrity-01M1TZV6/
├── spec.md                              # mission spec (committed)
├── plan.md                              # this file
├── research.md                          # Phase 0: decisions, evidence, drift findings, risks
├── data-model.md                        # Phase 1: entities, invariants, state transitions
├── quickstart.md                        # Phase 1: red-first repro + verification commands
├── contracts/
│   ├── emit-pipeline.md                 # pure pipeline signature + shell contract
│   ├── dependency-guard.md              # GuardContext field, polarity, resolution site
│   ├── write-gates.md                   # _unsafe allowlist + AST writes-gate + non-vacuity
│   └── run-state-store.md               # mission_id-keyed index, atomic cursor, loud missing-state
├── decisions/                           # DM-*.md decision records (10)
├── research/28-missionA-research-dossier.md
└── tasks.md                             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── status/
│   ├── __init__.py                      # WP03: strip append_event* exports (:518-537)
│   ├── _unsafe.py                       # WP03 NEW: raw append_event* + shrink-only ALLOWED_CALLERS
│   ├── emit.py                          # WP02: flat/primary shell; batch door takes lock (FR-018); fan-out step
│   ├── <pipeline>.py                    # WP02 NEW: pure pipeline (name chosen in WP02; e.g. transition_pipeline.py)
│   ├── aggregate.py                     # WP02: delete duplicate derive/validate (:605-698); compose over shell
│   ├── models.py                        # WP04: GuardContext.dependency_ready: bool | None
│   ├── wp_state.py                      # WP04: one guard clause on planned→claimed / claimed→in_progress
│   ├── locking.py                       # WP01: feature_status_lock_path keyed by feature_dir.name (:57-60)
│   └── store.py                         # WP01: atomic-append primitive reused (no new writer here)
├── coordination/
│   └── status_transition.py             # WP02: transactional shell; _prepare_event (:842-945) promoted out;
│                                        #       batch parity (:1605-1614 ← :1342-1369); coord-arm deferred fan-out (:401-432)
├── retrospective/
│   ├── lifecycle_events.py              # WP01: _append_retro_lifecycle_event (:250-256) under lock + atomic; Lamport read in-lock (:265)
│   └── events.py                        # WP01: raw open("a") (:213) under lock + atomic
├── migration/
│   ├── backfill_runtime_state.py        # WP01: :1497 read + :1533/:1535 appends under one lock
│   └── verdict_provenance_backfill.py   # WP01: :419 append under lock
├── merge/executor.py                    # WP01 (touch): retrospective L1 take gets finite timeout (FR-003b)
└── core/dependency_graph.py             # WP04: reused as-is (dependency_readiness_for_wp:34)

src/runtime/next/
├── _internal_runtime/engine.py          # WP05: _write_snapshot (:128-130) tmp+os.replace; _append_event (:110-119) hardened
├── runtime_bridge_io.py                 # WP05: index lookup by mission_id (:611-660); loud missing state.json
└── decision.py                          # WP05: materialize → materialize_snapshot (:373)

tests/
├── architectural/
│   ├── test_status_unsafe_allowlist.py  # WP03 NEW gate + non-vacuity floor
│   └── test_status_events_writes_gate.py# WP03 NEW AST gate + non-vacuity floor
├── status/ + specify_cli/status/        # WP02/WP04 unit tests (pipeline, shells, guard)
├── specify_cli/coordination/            # WP02 shell tests; #3460 / #1848 pins stay green
├── specify_cli/retrospective/, specify_cli/migration/, specify_cli/merge/  # WP01
└── runtime/                             # WP05 (test_bridge_io.py, test_bridge_engine.py, next/)
```

**Structure Decision**: existing single-package layout; two new modules under `src/specify_cli/status/` and two new gate files under `tests/architectural/`. No new packages, no `pyproject.toml` change (so `tests/architectural/` full run is NOT triggered by the cross-cutting rule; the two new gates plus `test_status_module_boundary.py` and `test_no_legacy_terminology.py` run targeted).

## Design (Phase 1 summary — details in `data-model.md` and `contracts/`)

```mermaid
flowchart LR
  subgraph callers
    AGG[MissionStatus.transition<br/>1 caller]:::c
    TXC[8 direct transactional callers]:::c
    FLAT[fallback arms / tests]:::c
  end
  subgraph status/  (MM-owned facade)
    PIPE[[pure pipeline<br/>alias→gates→collapse→evidence→validate→build]]
    FSHELL[flat/primary shell<br/>lock · atomic append · materialize · immediate fan-out]
    UNSAFE[_unsafe.append_event*<br/>shrink-only allowlist]
  end
  subgraph coordination/ (exempt plumbing)
    TSHELL[transactional shell<br/>txn · append · commit · deferred fan-out]
  end
  AGG --> TSHELL
  TXC --> TSHELL
  FLAT --> FSHELL
  TSHELL -->|readiness verdict in-lock| PIPE
  FSHELL -->|readiness verdict in-lock| PIPE
  FSHELL --> UNSAFE
  TSHELL --> UNSAFE
  classDef c fill:#eee,stroke:#999
```

Direction of imports is downward only: `coordination → status`; `status/<pipeline>` imports nothing from `coordination`. Both shells are the **verdict supplier** for the dependency guard (FR-013).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| WP02 touches 4 modules + docs in one WP (4–5 days) | The three orchestrations and the aggregate must converge in one change or the divergence is re-created mid-flight | Shim-over-coordination (1 module) inverts C-006 and changes C-008 semantics; "shared kernel only" (no shells) leaves the P1 phantom fan-out and the lockless batch door unfixed (see `research.md` §1) |
| WP04 edits WP02's new pipeline module (shared-file leeway) | The guard clause must sit in the pipeline's `GuardContext` build | Duplicating the build in WP04 recreates the whack-a-field pattern the mission exists to close |

## Parallel Work Analysis

### Dependency Graph

```
WP05 (run-state; no deps) ──────────────────────────────┐  merge FIRST → frees 4 runtime files for Mission B
WP01 (out-of-pipeline writers) ──► WP03 (facade strip + gates)
WP02 (pipeline + shells; CORE) ──► WP04 (dependency guard)
```

Wave 0: WP05 ∥ WP01 ∥ WP02 (disjoint owned files — verified: WP01 owns retrospective/migration/locking/merge-touch; WP02 owns emit/aggregate/pipeline/status_transition; WP05 owns the runtime trio).
Wave 1: WP03 (after WP01) ∥ WP04 (after WP02).

### Work Distribution

- **Sequential**: WP01 → WP03 (gates are seeded from the fixed census); WP02 → WP04 (guard lands in the pipeline).
- **Parallel streams**: WP01, WP02, WP05 in wave 0; WP03, WP04 in wave 1.
- **Owned files**: as in §Project Structure per-line WP tags. Declared shared file: `status/<pipeline>.py` (owner WP02; WP04 leeway for the one guard field/clause). Declared touch: `merge/executor.py` (WP01, timeout kwarg only).

### Coordination Points

- **Sync schedule**: WP05 merges first (Q10 rider). WP01 and WP02 merge independently; WP03/WP04 rebase on their parent.
- **Integration tests**: SC-008 lock-held assertion across all seven families runs after WP01+WP02 both land; the delegation-equivalence tests replace the divergence pins after WP02 (C-009).
- **Ledger watch**: any WP that removes a ledgered lazy reach (e.g. `runtime_bridge_io.py` baseline in the doctrine scan) budgets the same-PR ledger/baseline edit (`test_runtime_ledger_has_no_stale_entries`).
- **Doc contention**: WP02's doc edit is the minimal stale-sentence hunk in CLAUDE.md status section + `docs/architecture/status-model.md:393`; Mission C owns final text (FR-009).

## Implementation Concern Map

| # | Concern | Spec anchors | WP | Red-first target | Contract |
|---|---|---|---|---|---|
| IC-1 | Serialize + atomic-append the four unlocked writers; lock rules a–c; lock key | FR-001..004, NFR-003, US1 | WP01 | rollback-truncate race at `transaction.py:944`; backfill two-append + `:1497` TOCTOU; lock-key collision | `contracts/emit-pipeline.md` §Lock rules |
| IC-2 | Promote `_prepare_event` to the pure pipeline; two shells; converge aggregate + 3 doors; batch lock + parity; deferred fan-out; doc hunk | FR-005..009, FR-018, NFR-004, US2, C-006..008 | WP02 | phantom fan-out (`status_transition.py:401-432`/`emit.py:794`); batch owned-mission divergence; no-new-commits pin | `contracts/emit-pipeline.md` |
| IC-3 | Facade strip to `_unsafe.py`; AST writes-gate; non-vacuity floors; #3895 note | FR-010, FR-011, US3 | WP03 | synthetic out-of-pipeline writer reds the gate; zero-match reds the gate; allowlist growth refused | `contracts/write-gates.md` |
| IC-4 | Readiness as tri-state guard field; in-lock resolution on `txn.feature_dir`; reuse + demote 6 call sites | FR-012..014, C-004, C-005, NFR-002, US4 | WP04 | verdict-less direct emit claims dep-blocked WP (succeeds on main); probe-site `None` pins; force + chain matrix | `contracts/dependency-guard.md` |
| IC-5 | Atomic cursor + journal; `mission_id`-keyed index; loud missing-state; pure progress read | FR-015..017, C-003, US5 | WP05 | slug-collision distinct runs (`runtime_bridge_io.py:618`); crash-window cursor; `status.json` byte-identical; missing `state.json` structured error | `contracts/run-state-store.md` |

## Post-Design Charter Re-check

Re-evaluated after Phase 1 artifacts: no new gaps. One item surfaced by research and carried as a plan-level correction rather than a violation: C-008's "four plain-door callers" are docstring references, not call sites (see `research.md` §3, drift D-1); the no-new-commits pin is retained with the fallback arm as its rationale. The ADR-amendment obligation from Q4 is a documentation task inside WP02, not a charter conflict.

## Verification at every WP boundary (NFR-005 / C-010)

```bash
make test-fast
.venv/bin/pytest tests/status tests/specify_cli/status tests/specify_cli/coordination -q
# plus the WP's own blast radius (see quickstart.md per WP)
.venv/bin/pytest tests/architectural/test_status_module_boundary.py tests/architectural/test_no_legacy_terminology.py -q
```

Never `make test-full` locally; never the full `tests/architectural/` (no cross-cutting file is touched).
