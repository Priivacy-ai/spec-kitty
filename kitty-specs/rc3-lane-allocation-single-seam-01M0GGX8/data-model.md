# Phase 1 Data Model — M8 Lane-allocation single-seam

Value objects introduced by the seam family. All immutable (`@dataclass(frozen=True)`), no I/O in the
type itself (I/O lives in the resolver functions, mirroring `write_target_degrade`).

## `LaneBaseDecision` (WP2 — the allocation seam return)

The single return of `resolve_lane_base_or_refuse` on the **honor / no-override** paths. Refusal is
**not** a field — an unhonorable route raises `UnhonorableBaseError` and never returns this object.

| Field | Type | Meaning |
|-------|------|---------|
| `parent_ref` | `str` | The ref a freshly-created lane branches from. `base` when honored; else the topology-derived parent (`coordination_branch`, or legacy `mission_branch`). |
| `base_honored` | `bool` | `True` iff an explicit `base` was supplied AND this route applied it; `False` when `base is None`. (Near-redundant with `base is None` because unhonorable routes raise — retained for logging + the anti-bypass guard's assertions, **not** as the anti-drop guarantee, which is the raise.) |
| `route` | `LaneAllocationRoute` (enum) | The allocation route that produced the decision (see enum below). Enum, not `str`, for mypy-checked dispatch parity with `topology`. |
| `topology` | `LaneTopology` (enum) | `COORD` or `LEGACY` — the derived-parent source, for the anti-bypass guard and logging. |

> **No `refusal` field** (post-plan squad, architect MED). An earlier draft (research D2) proposed an
> optional `refusal` field; it is structurally unreachable since unhonorable routes raise before
> returning. Refusal == the `UnhonorableBaseError` exception, full stop.

**Invariants:**
- `base_honored` ⇒ `parent_ref == base` (an honored base fully REPLACES the topology parent — D1/C-005,
  never layered on top; matches M1's `_resolve_lane_parent`).
- `not base_honored` ⇒ `base is None` AND `parent_ref` is byte-identical to the pre-M8 topology-derived
  parent (NFR-001 backward-compat).
- A route that cannot honor a supplied `base` never returns a `LaneBaseDecision` — it raises
  `UnhonorableBaseError` (fail-loud, FR-003).

## `LaneAllocationRoute` (enum, WP2)

`FRESH_COORD` | `FRESH_LEGACY` | `REUSE` | `CRASH_RECOVERY` — the closed set of allocation routes, threaded
as the seam's `route` dispatch key. Enum (not a bare `str`) so a typo fails mypy rather than silently
mis-dispatching (post-plan squad, architect LOW — parity with `LaneTopology`). The four
`UnhonorableBaseError` *triggers* (reuse, crash_recovery, dependency_lane, detached_base) are a distinct,
finer axis M1 already models inside `_guard_base_honorable`; the seam maps route → applicable trigger(s).

**State transition (per allocation call):**
```
base supplied? ──no──> parent = topology parent (COORD coord_branch | LEGACY mission_branch); base_honored=False
      │yes
      ▼
route can honor base? ──no──> raise UnhonorableBaseError(route, wp_id, base)   [reuse|crash_recovery|
      │yes                                                                       dependency_lane|detached_base]
      ▼
parent = base; base_honored=True
```

## `ReadDirDecision` + `ReadDegradeStrategy` (WP4 — the read companion)

Return + strategy enum for `resolve_read_dir_or_degrade`, companion to the write-side `CommitTarget`.

> **Right-sized to genuine demand (post-plan squad, architect+reviewer MED — rule-of-three).** Only
> **two** sites are genuine resolve-then-degrade consumers: `retrospective/generator.py:264` (ZERO_EVIDENCE)
> and `core/worktree_topology.py:173` (DEGRADE_TO_FEATURE_DIR). The `FAIL_CLOSED` sites
> (`agent/status.py:154/:195`) only re-raise then `typer.Exit` at the caller — routing them through a
> helper that merely re-raises removes no hand-rolled `try/except`, so they are **parked on the WP3
> allowlist**, not forced through the seam. `status/aggregate.py:351` (re-wrap + #1848 re-raise ordering)
> and `_review_cycle_reconcile_doctor.py` (absorb-before-read, likely not a degrade shape) are **bespoke**,
> also allowlisted with a stated reason. So the helper ships for the two real degrade consumers and is
> designed for growth; the "single read seam" is honestly "two seam consumers + a reasoned allowlist".

`ReadDegradeStrategy` (enum) — the caller's declared fallback contract:

| Value | Behavior on the declared exception set | Genuine consumer(s) |
|-------|----------------------------------------|---------------------|
| `DEGRADE_TO_FEATURE_DIR` | Return the primary `feature_dir`. | `worktree_topology.py:173` |
| `ZERO_EVIDENCE` | Return the caller's sentinel (e.g. empty-trace dir) — degraded read, not an error. | `retrospective/generator.py:264` |
| `FAIL_CLOSED` | Re-raise the typed error verbatim (e.g. #1848 `CoordinationBranchDeleted` data-loss). | pass-through — parked on the WP3 allowlist, not migrated |

`ReadDirDecision`:

| Field | Type | Meaning |
|-------|------|---------|
| `read_dir` | `Path` | The directory to read from (resolved surface, or the strategy's degrade target). |
| `degraded` | `bool` | `True` iff resolution failed and the strategy's fallback was applied. |
| `strategy` | `ReadDegradeStrategy` | The contract the caller declared (for logging/telemetry). |

**Invariant (US-4.2 / #1848):** `FAIL_CLOSED` never returns a `ReadDirDecision` for a data-loss error —
it re-raises. The helper's per-caller `caught` exception set determines which exceptions the strategy
even sees; a `CoordinationBranchDeleted` at a `FAIL_CLOSED` (or exclude-subclass) site propagates verbatim.

## `LaneTopology` (enum, shared vocabulary)

`COORD` | `LEGACY` — derived from the authoritative `_transaction_topology_available` /
`coordination_branch` value, NOT re-inferred at each site (#3460). Used by the anti-bypass guard to
assert every route's topology decision flows from the one predicate.
