# Contract: Transition Pipeline and Composition Shells (WP01 / WP02)

**Owner**: Mission Management (`src/specify_cli/status/`) · **Consumers**: `coordination/status_transition.py` shells, `status/emit.py` shells, `status/aggregate.py`
**Binding decisions**: Q4 (`01M1V80R6F6RTMR7Y3C2WBKR32`), Q1, Q5, Q7 · **Constraints**: C-001, C-006, C-007, C-008, NFR-001, NFR-004

## 1. Pure pipeline (status-owned; the named validation/build authority)

```python
# src/specify_cli/status/<pipeline>.py   (module name chosen in WP02; must not import coordination)

@dataclass(frozen=True)
class PreparedTransition:
    event: StatusEvent | None        # None ⇒ alias-collapse no-op arm (mirror only)
    resolved_lane: str
    annotation: StatusEvent | None   # resolved-binding annotation, if any
    mirror_frontmatter_lane: bool    # True when the phase-gated frontmatter mirror must run

def prepare_transition(
    *,
    request: TransitionRequest,
    feature_dir: Path,                       # the shell's WRITE surface (txn.feature_dir under coord)
    mission_slug: str,
    mission_id: str | None,
    from_lane: str,                          # derived by the shell, in-lock, exactly once
    readiness: DependencyReadiness | None,   # WP04: resolved by the shell, in-lock, against feature_dir
    at: str | None = None,
    # injected I/O (defaults = today's helpers; tests pass fakes)
    resolve_subtasks_dir: Callable[..., Path] = resolve_subtasks_gate_dir,
    infer_subtasks_complete: Callable[..., bool | None] = _infer_subtasks_complete,
    infer_implementation_evidence: Callable[..., bool | None] = _infer_implementation_evidence,
) -> PreparedTransition: ...
```

Steps, in order (promoted verbatim from `_prepare_event`, `coordination/status_transition.py:842-945`):
1. alias-resolve `to_lane`;
2. infer review gates (`subtasks_complete`, `implementation_evidence_present`) only for `in_progress→for_review` without `force`;
3. alias-collapse check → return `PreparedTransition(event=None, mirror_frontmatter_lane=True)`;
4. build done-evidence;
5. build `GuardContext` (incl. `dependency_ready = readiness.satisfied if readiness is not None else None`);
6. `validate_transition(from_lane, resolved_lane, ctx)` — **the only call in the tree per emit**; raise `TransitionError` on refusal;
7. `build_status_event(...)`; attach annotation.

**Guarantees**
- G-1 No file writes, no lock, no git, no network. Unit-testable with an in-memory `feature_dir` + fakes.
- G-2 Idempotent for equal inputs except `event_id`/`at` generation (ULID + clock are injectable in tests).
- G-3 Imports: `status.models`, `status.transitions`, `status.wp_state`, `status.emit` helpers per Q6 — never `coordination`.

## 2. Shell contract (exactly two kinds)

Every shell MUST perform, in this order, with L1 held from step 1 through step 6:

| Step | Flat/primary shell (`status/emit.py`) | Transactional shell (`coordination/status_transition.py`) |
|---|---|---|
| 1 acquire | `feature_status_lock(resolve_status_lock_root(feature_dir, repo_root), feature_dir.name)` | `BookkeepingTransaction.acquire(...)` (holds L1) |
| 2 derive | `_derive_from_lane(feature_dir, wp_id)` — once | `_derive_from_lane(txn.feature_dir, wp_id)` — once |
| 3 readiness | `dependency_readiness_for_wp(...)` read from `feature_dir` | same, read from `txn.feature_dir` |
| 4 prepare | `prepare_transition(...)` | `prepare_transition(...)` |
| 5 persist | atomic append (`store.append_*_atomic_verified`) → `materialize` → mirror | `txn.append_events([...])` |
| 6 release | lock released | `txn` commits (coord) then releases |
| 7 fan-out | immediately after release (flat/LANES: no commit exists) | `txn.defer_outbound(...)` / `queue_saas_emission(txn, …)` — fires **only after commit success** |

**Batch variants** run steps 2–5 per request under ONE acquisition (FR-018) and apply the owned-mission check + `effective_root` exactly as the single variant (Q5).

**Coord fallback arm** (`_fallback_emit_single._coord`, `:404-432`): invokes the flat shell with `fan_out=False`, commits, then fans out; on commit failure `_restore_coord_status_artifacts` truncates and **no fan-out occurs** (SC-002). The flat shell therefore exposes a `fan_out: bool = True` keyword (or an equivalent deferred-callable return) — the exact shape is WP02's choice; the observable contract is "zero fan-out for a truncated event".

**Prohibited**
- A third composition of lock + append anywhere outside these two modules (WP03 gate, R14).
- Any shell resolving readiness before acquiring L1, or against a directory other than its write surface (FR-013).
- Any shell calling `validate_transition` itself (P-2).

## 3. Lock rules encoded (WP01, FR-003)

| Rule | Where | Test |
|---|---|---|
| (a) L1 takes reachable from an L3 verdict-save-queue scope are bounded | `cli/commands/agent/tasks_verdict_persistence.py` ~`:546-561`, `review/cycle.py:804,881` pattern reused | NFR-003 timeout test: contended lock ⇒ structured timeout error naming holder |
| (b) merge-path retrospective L1 take is finite | `merge/executor.py` retro path (touch) | contended ⇒ structured error, merge not refused repo-wide |
| (c) one lock key | `status/locking.py:feature_status_lock_path` keyed on `feature_dir.name` via `resolve_status_lock_root` | two colliding slugs ⇒ distinct files; bare legacy slug ⇒ same file as its ordinary writers |

## 4. Writer hardening pattern (WP01, FR-002)

For each of families ④⑤⑥⑦ (`data-model.md` §2):
```python
root = resolve_status_lock_root(feature_dir, repo_root)   # repo_root may be None
with feature_status_lock(root, feature_dir.name, timeout=<finite where rule (a)/(b) applies>):
    <any idempotency / Lamport read>                        # moved INSIDE the lock
    append_events_atomic_verified(feature_dir, rows)        # atomic primitive, one call for paired appends
```
The `nullcontext()` no-git degrade is a **per-site conscious choice** documented in a one-line comment at each site.

## 5. Plain-door semantics pin (C-008, SC-007)

`test_plain_door_lanes_mission_gains_no_commits`: a stored-`LANES` mission emitted through `emit_status_transition` (as the fallback arm does) leaves `git rev-list --count HEAD` unchanged and spawns no identity-resolution git subprocess. Rationale cites `_fallback_emit_single._primary` (`status_transition.py:392`), not the four docstring mentions (`research.md` §3 D-1).

## 6. Cost pin (NFR-004, Q7)

`test_emit_reads_log_once`: with `_derive_from_lane` and `read_events` wrapped by call counters, one emit through each shell ⇒ `_derive_from_lane` count == 1, full-log read count == 1.
