# Data Model: Review-Cycle Verdict Seam Rebuild

Phase 1 output. Field lists below are the **measured** current shape; changes this
mission makes are marked.

## Entities

### Authoritative verdict — `ReviewResult` on `StatusEvent`

Authoritative for *which* verdict is current and where its content lives.

| Field | Type | Note |
|---|---|---|
| `reviewer` | `str` | |
| `verdict` | `str` | a bare `str` with a comment, **not** a `Literal` — measured. Vocabulary `"approved"` / `"changes_requested"` |
| `reference` | `str` | a `review-cycle://` URI. (`feedback://` is the **deprecated** legacy form — `cycle.py:264`) |
| `feedback_path` | `str` | pointer to the verdict record |

**No field is added here.** The override authority is the existing event-sourced
`ReviewOverride` on the reduced `review` slot — see below.

Lifecycle: append-only.

**`review_result` is NOT always populated.** `wp_state.py:183` short-circuits
`guard_for` entirely when `ctx.force` is set, so `--force` — exposed on both
`agent status transition` and `move-task` — produces `in_review → approved` events
with `review_result: null`. Reproduced. This is a **current, ongoing** production,
not legacy residue, and the FR-001 reader needs a defined behaviour for it.

**Events carry `verdict: "approved"` for decisions that were waivers — today, not
only historically.** 23 override-worded approved verdicts exist across this
repository's own logs; one from 2026-07-27 carries `force=false` and a reference
reading *"independent reviewer override"*. `_mt_plan_review_result` hard-codes
`verdict = "approved"` for any `in_review → {approved,done}`.

### Verdict record — `ReviewCycleArtifact`

Authoritative for *what the reviewer said*. Addressed by the event's pointer, not
derived from it.

| Field | Note |
|---|---|
| `cycle_number` | derivation changes: `max(parsed) + 1`, not `len() + 1` |
| `wp_id`, `mission_slug`, `reviewer_agent`, `reviewed_at` | |
| `verdict` | remains, but is no longer the authority for *current* verdict |
| `body` | reviewer prose — exists nowhere on the event |
| `affected_files`, `reproduction_command` | exist nowhere on the event |
| `override_actor`, `override_reason` | **read-only — no writer since 2026-07-01.** Owned by `wp-runtime-state-eviction-01KXWN13`'s deferred WP10, which is explicitly RETAINED as a migration-window safety net. Out of scope here; a cleanup pass would revert a landed operator decision |

Lifecycle: **not** "written once, never rewritten" — `arbiter._persist_in_artifact`
rewrites a persisted artifact's frontmatter in place today, and IC-09 keeps that
path until it is retired. **Not durably persisted until committed** — a record on
disk but absent from the git index is not authoritative for any read path.

### Arbiter override

A first-class outcome alongside approval and rejection. **The authority is the
existing event-sourced `ReviewOverride`** on the reduced `review` slot — a frozen
four-field record (`at`/`actor`/`wp_id`/`reason`) with a `complete` predicate,
already consumed by the merge gate. ADR 2026-07-19-1 pins this mechanism.

The four representations, with corrected membership:

| # | Representation | Disposition |
|---|---|---|
| 1 | `ReviewOverride` on the reduced `review` slot | **the authority** — retained |
| 2 | `arbiter_override` frontmatter block (`arbiter.py:437`) | retired into (1) by IC-09 |
| 3 | `arbiter-override-N.json` sidecars | retired into (1) by IC-09 |
| 4 | `review_artifact_override_*` artifact fields | read-only, no writer; another mission's deferred WP10 — **out of scope** |

Mandatory: a stated reason. The partition tension is **resolved** by ADR 2026-08-03-1:
review-cycle artifacts become their own `REVIEW_CYCLE` kind on the COORD partition
under coordination topologies, so (1) and the record it annotates share a surface.
Under `SINGLE_BRANCH` / `LANES` both resolve to PRIMARY, unchanged.

### Location resolution

The single derivation from work-package identity to verdict-record directory.
Includes **slug derivation**, which is where the divergence actually lives — see
research R5.

Invariant: for a given work package, every read, write, merge-gate and display path
resolves one identical directory, through the `REVIEW_CYCLE` kind — COORD under
coordination topologies, PRIMARY otherwise (ADR 2026-08-03-1). A caller-supplied
directory is not a substitute for kind resolution on any path. A filename that
cannot be resolved unambiguously is refused with a diagnostic, never degraded to the
bare work-package id.

**Migration behaviour**: a pre-ADR mission's records live on the primary surface. A
read that finds nothing at COORD falls back to PRIMARY and never reports "no
verdict".

## Invariants

| # | Invariant | Enforced by |
|---|---|---|
| I-1 | A durably recorded approval exists **iff** the approval transition completed | FR-001, FR-002 |
| I-2 | A verdict record is never overwritten by a new one | FR-006 (`max + 1` + collision refusal) |
| I-3 | Two concurrent distinct verdicts produce two records, or one explicit refusal — never silent loss | FR-005 |
| I-4 | An arbiter override is never recorded as an approval, in either store | FR-022, FR-011 |
| I-5 | Every reader resolves a damaged record to its declared polarity; no safety gate fails open | FR-012 |
| I-6 | A file that *is* a prior verdict record is refused as feedback, by path or by content | C-002 behaviour floor — this is the #990 control |
| I-7 | The event and the artifact never disagree about which verdict is current | FR-001 |

**I-7 needs a vocabulary mapping before it is checkable.** The event's vocabulary is
`"approved"` / `"changes_requested"`; the artifact's is `"approved"` / `"rejected"`.
Stated over two non-comparable value sets, the invariant cannot be evaluated. The
mapping is a deliverable of the concern that owns FR-001.

I-6 is called out because FR-004 (repeat feedback must be recordable) creates
pressure against it, and the shortest path to FR-004 is to delete it. That path is
a constraint violation, not an implementation choice.

## State transitions

```
    (no record)
         │  reviewer rejects
         ▼
   ┌──────────┐  reviewer approves        ┌──────────┐
   │ rejected │ ────────────────────────► │ approved │
   └──────────┘                           └──────────┘
         │                                      ▲
         │  arbiter overrides                   │
         ▼                                      │
   ┌────────────┐   NOT an approval ────────────┘
   │ overridden │   (I-4: distinct outcome, distinct record)
   └────────────┘
```

Each edge writes one verdict record and one status event, and the two either both
land or neither does (I-1). The `rejected → rejected` self-edge is legal — a
recurring defect re-reported — and is exactly the case FR-004 unblocks without
breaching I-6.

## Failure-state model

The states this mission makes unrepresentable, each currently reachable:

| Current reachable state | Closed by |
|---|---|
| Committed `approved` record for a work package that never transitioned | FR-002 |
| Orphan record after a failed commit, making the identical retry permanently refused | FR-003 |
| Approval transition succeeding on an uncommitted verdict after a process kill | FR-003 |
| One of two concurrent verdicts silently destroyed | FR-005 |
| A new record overwriting a live one across a numbering gap | FR-006 |
| Approval over a live rejection with no record written anywhere | FR-007 |
| Override recorded as an approval review | FR-022, FR-011 |
| Neither verdict recordable at all under protected-primary coord | FR-013 scope |
