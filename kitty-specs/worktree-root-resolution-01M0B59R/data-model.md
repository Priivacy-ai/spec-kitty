# Data Model: Worktree-Aware Root Resolution & Verdict Parity

Behavior-fixing mission — the "entities" are the value objects and invariants the fix introduces or hardens. No persistent schema changes; the append-only `status.events.jsonl` format is unchanged (only its audit registration and value round-trip are hardened).

> **Reframe (2026-08-18):** the discarded `CheckoutKind {PRIMARY, LINKED_WORKTREE, STANDALONE_CLONE}` classifier is replaced by a **checkout-identity guard**. A post-plan squad (empirical resolver run) established that clones already resolve to self and the clone/primary split is undecidable from local state. The decidable, load-bearing distinction is **invocation ownership** (does this invocation own the target checkout, or is it a foreign lane worktree?), with **read/write intent** so deliberate primary reads are preserved.

## Entities & Value Objects

### CheckoutIdentity (new value object)

The single source of truth for invocation ownership. Consulted by in-scope commands; carries intent so it does not flip deliberate primary reads.

| Field | Type | Meaning |
|-------|------|---------|
| `invoking_root` | Path | The checkout the command was invoked from (CWD's own checkout root). |
| `canonical_target` | Path | Where the command's canonical write/read deliberately lives (may be the primary for #2320/#3328 anchors). |
| `is_owner` | bool | True when `invoking_root` owns/equals `canonical_target` (or a worktree it legitimately owns); False for a foreign lane worktree. |
| `intent` | enum `{ WRITE, PRIMARY_READ }` | `WRITE` → ownership decides fail-closed vs proceed; `PRIMARY_READ` → deliberate primary anchor, never flipped to `invoking_root`. |

**Invariants**
- INV-1: For `intent == WRITE` and `is_owner == False`, the command fails closed (refuses) — it does not silently act on `canonical_target`. (spec FR-002, FR-003; SC-001)
- INV-2: For `intent == PRIMARY_READ`, the guard returns `canonical_target` unchanged regardless of `invoking_root` — the must-not-flip anchors (#2320/#3328) are preserved. (spec FR-008; SC-003)
- INV-3: The guard performs no re-anchoring *write* side effect; it is a decision unit.
- INV-4: Ownership is decided from local, decidable git state (worktree pointer topology + ownership claim), **not** from an undecidable clone/primary guess. (spec C-005)

### FailClosedRefusal (new value object)

The #3128 remediation shape emitted when `intent == WRITE` and `is_owner == False`.

| Field | Type | Meaning |
|-------|------|---------|
| `refusal_path` | Path | The `canonical_target` the command would otherwise have acted on — named in the message. (FR-002/003, NFR-003) |
| `channel` | single seam | All write-refusals route through this one constructor (architectural test forbids ad-hoc refusal strings). (NFR-003) |

**Invariants**
- INV-5: Every write-refusal carries a non-empty `refusal_path` present verbatim in the message. (NFR-003)
- INV-6: An owner invocation (primary checkout it owns) never triggers a refusal — behavior is unchanged from today. (spec Edge Cases)

### GuardVerdict (guards — false-green fixes)

The result of a cutover/branch guard.

**Invariants**
- INV-7: `setup-plan`'s `branch_matches_target` is computed from the invoking checkout / mission `meta.json`, never from the primary's HEAD via a redirected read. (spec FR-006; SC-002)
- INV-8: `backfill`'s cutover guard does not report success merely by verifying against the same redirected path it wrote; it is invoking-checkout-aware. (spec FR-005; SC-002)

### ReviewResult (existing — parity hardening)

Projection already correct (`407ea376c4`, C-001). This mission adds entry parity + audit registration + value round-trip.

**Invariants**
- INV-9: `_parse_review_result_json` (hoisted to `status`) is the single validator; both `agent status emit --review-result-json` and `orchestrator-api transition` route through it. (FR-010)
- INV-10: A WP reaches `done` (incl. the `in_review` exit) via `agent status emit` alone, carrying a `ReviewResult`. (FR-010, FR-013; SC-004)
- INV-11: **Value round-trip** — replaying a persisted snapshot's event log reproduces the snapshot's projected fields **by value** (not key-presence); the generator is guaranteed to emit ≥1 `review_result`-carrying event (non-vacuous). (FR-015; SC-005)
- INV-12: A `status_event_row` carrying `review_result` audits clean — the key is registered; 0 `UNKNOWN_SHAPE`. (FR-014; SC-005)

### ForReviewCommitGate (existing — unified, both directions)

Hoisted to a `lanes`-side leaf with a **surface-neutral error contract** (returns a decision; each surface renders its own failure — the orchestrator envelope is not dragged into the CLI).

**Invariants**
- INV-13: One shared implementation enforced identically on both CLI surfaces. (FR-011; SC-004)
- INV-14: Topology-aware: a clone is evaluated on **commit state** — passing with satisfied commits **and failing with unsatisfied commits** (both directions asserted). (FR-011)

### ShapeRegistry `status_event_row` (existing — hardened)

**Invariants**
- INV-15: `review_result` and the coordination-key shape are registered in `status_event_row`. (FR-014, FR-016)
- INV-16: A **new `status_event_row`-scoped** drift test fails when a persisted event shape is unregistered. (The existing `test_shape_registry_writer_parity.py` is `meta.json`-scoped and cannot cover this artifact.) (FR-016)
- INV-17: After the writer migration, persisted coordination-key rows carry the registered shape. (FR-018)

## State Transitions (verdict path — unchanged machine, unified entry)

```
in_progress -> for_review -> in_review -> approved -> done
                   ^              |
        (for_review gate,         | (ReviewResult path,
         shared + topology-aware, |  both surfaces — FR-013)
         both directions)         |
```

## Relationships

- `FailClosedRefusal` is produced by `CheckoutIdentity` when `intent==WRITE ∧ ¬is_owner` (INV-1/INV-5).
- In-scope write commands consume `CheckoutIdentity(intent=WRITE)`; deliberate primary anchors (#2320/#3328) are declared `intent=PRIMARY_READ` and appear in the FR-008 must-not-flip inventory.
- `ForReviewCommitGate` and `_parse_review_result_json` are shared dependencies of both CLI surfaces (no per-surface copy).
- `get_main_repo_root` (~130 callers) is unchanged as a primitive; only named commands adopt the identity guard (locality of change).
