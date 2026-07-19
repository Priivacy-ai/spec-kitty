---
title: 'ADR: Evict runtime-mutable WP state into the event log via a single generic InnerStateChanged annotation event'
status: Accepted
date: '2026-07-19'
---

**Status:** Accepted

**Date:** 2026-07-19

**Deciders:** Operator / HiC (Stijn Dejongh); four-lane research squad (2026-07-19); building on prior-art ADR `wp-op-schema-design/docs/adr/3.x/2026-07-16-1-wp-runtime-state-authority-event-log-eviction.md`.

**Technical Story:** [#2684](https://github.com/Priivacy-ai/spec-kitty/issues/2684) (P0) — the execution vehicle for the [#2093](https://github.com/Priivacy-ai/spec-kitty/issues/2093) authority ruling. Full grounding: `docs/plans/investigations/2684-task-move-cluster-scoping.md`.

---

## Context and Problem Statement

`tasks/WP##.md` (and the `tasks.md` subtask surface) is **two authorities glued into one YAML
block**: static design-intent authored once, and runtime-mutable state written on every lifecycle
event. This split is load-bearing and actively harmful:

- Runtime writes into the dossier-hashed files (`dossier/indexer.py:242` hashes both `tasks.md` and
  `tasks/WP##.md`) churn `content_hash_sha256` on every transition → false drift (**AC-5**).
- Subtask-completion truth lives in `tasks.md` markdown bytes (`core/subtask_rows.py:39`), which the
  review gate (`_guard_subtasks`, `tasks_transition_core.py:384`) and done-inference
  (`_infer_subtasks_complete`, `status/emit.py:279`) read — while the append-only event log, the
  declared authority for lane/status, carries **no subtask state at all** (`reducer.py:48-65`). A WP
  whose work is complete is refused `move-task --to for_review` until an operator hand-ticks N
  checkboxes (the merged P0 red test `tests/regression/test_issue_2684_subtask_completion_event_sourced.py`).
- Claim-liveness reads `shell_pid` from frontmatter (`stale_detection.py:402-403`); evicting it
  naively corrupts the allocator.

The hard constraint: `StatusEvent` is a **transition ledger** — it mandates `from_lane`/`to_lane`
(`status/models.py:248-249`) and `validate_transition` rejects any edge outside the 9-lane FSM
(`wp_state.py:162,351`). But three of the evicted mutations are **off-axis** (no lane change):
(a) `shell_pid` refresh on *resume* of an already-`in_progress` WP, (b) mid-`in_progress` subtask
marks, (c) activity-log notes. They cannot be clean transition events. **How off-axis runtime state
enters the append-only log is the decision everything else rests on.**

## Decision Drivers

- **One authority per datum** — runtime state has exactly one read path (the reduced snapshot); no
  frontmatter field is ever read as authority; static fields are never mirrored into events.
- **Preserve every gate** — claim-liveness (AC-2), done-inference (AC-3), review gating — through the
  cutover, not after it.
- **AC-5 stable content hash** across a full lifecycle — the churn/false-drift fix.
- **Reusability** — prefer one extensible mechanism over per-field special cases.
- **No split-brain regression** — a generic sidecar must stay *typed*, or it re-creates the very
  ambiguity being removed.
- **Writer ownership** — this mission **owns** the `implement.py:1730` shell_pid-writer restructuring
  (the former #2160 co-sequence is resolved: #2160's writer work is `pr:deferred` and yields to this
  mission). Every new emit site must resolve its write target from stored topology, never `Path.cwd()`,
  or it reopens #2647.
- **Migration safety** — readers keep a frontmatter fallback until backfill is verified (the "B3
  clobber window").

## Considered Options

- **Option A — a non-transition annotation event class** in the same append-only log, distinguished
  by the absence of `from_lane`/`to_lane`, bypassing `validate_transition`, folded by the reducer.
- **Option B — fold onto existing transitions + `policy_metadata`.** Carry `(shell_pid, baseline)` on
  the next real transition; no FSM/reducer change.
- **Option C — self-edges (`X→X`) legalised in the FSM matrix.** (Weighed and rejected in the
  prior-art ADR: redefines the "a transition changes lane" invariant; ripples into rendering, drift,
  done-inference; zero capture benefit over A.)

## Decision Outcome

**Chosen option: Option A, realised as a *single generic* `InnerStateChanged` event carrying a typed
partial delta.** Rather than per-kind annotation variants, there is **one** off-axis event whose
payload is a **typed** `WPInnerStateDelta` (optional typed fields — *not* a free `dict[str, Any]`),
folded by the reducer with a per-field merge rule and **no `force_count` increment**. This is the
reusable realisation of the annotation class and it is what gives the reduced snapshot the
gate-queryable projection the subtask gates need.

The seven cluster decisions (HiC, 2026-07-19) that this ADR ratifies:

1. **Off-axis events → Option A as one generic `InnerStateChanged` event** with a typed delta,
   bypassing `validate_transition`, reducer-folded, no `force_count`.
2. **Subtask granularity → subsumed by the delta** (`subtasks: Mapping[str, Status]`) — a single mark
   and a batch mark are the same event; the same generic event also carries the PID refresh.
3. **Activity notes → a `note` delta field with append semantics** (reducer keeps a `notes` list;
   AC-4 renders the Activity Log from it). One event class for pid + subtasks + notes.
4. **`tracker_refs` → evict** (runtime, event-sourced): `map-requirements` and `move-task` emit an
   `InnerStateChanged` delta with **union/append** merge; FR-011 runtime append preserved.
5. **Review-cycle → evict all in this mission**: delete the dead verdict-field read fallbacks
   (`workflow_cores.py:340-341`, `done_bookkeeping.py:104-105`) **and** evict the actively-written
   `review_artifact_override_*`. **#2684 is the authoritative owner of the WP-metadata surface;**
   deferred PRs (#2641, #2766, #2612, and #2160's writer work) yield to the mission and rebase onto
   it — their file-collision risk is moot. Consequently this mission **owns** the `implement.py:1730`
   shell_pid-writer restructuring outright (no external co-sequence gate).
6. **Static-model election → deferred** to a follow-up (blocker B4: `WPMetadata` cannot become a
   clean static-only projection until its runtime half is stripped; coordinates with #1619).
7. **`progress` field → retired explicitly** (removed from `MUTABLE_FIELDS`/schema; backfill no-op).

The initial claim's `(shell_pid, baseline)` still rides the **real** `planned→claimed` transition via
the existing generic `policy_metadata` sidecar (`status/models.py:258`) — no wire-schema change there;
only the resume/mid-work/notes mutations use `InnerStateChanged`.

### Consequences

#### Positive

- The append-only log becomes a **true SSOT** for all off-axis runtime state; the reduced snapshot
  gains typed slots (`shell_pid`, `shell_pid_created_at`, `subtasks`, `notes`, `tracker_refs`).
- `tasks/WP##.md` and `tasks.md` become **static design-intent only** → stable content hash (AC-5),
  the long-homeless dossier/sync churn fix.
- Re-pointing `_guard_subtasks` and `_infer_subtasks_complete` at the snapshot turns the merged P0
  red test green (AC-3) and removes the manual N-tick friction.
- One extensible event + typed delta: future runtime fields ride free without new event kinds.

#### Negative

- Highest-blast-radius option: touches the FSM authority (a sanctioned self-edge / `annotate()`
  primitive), the wire model (an event discriminator round-tripped in `to_dict`/`from_dict`), and the
  reducer precedence core (fold-after-transition, last-writer-wins per field).
- Adds a reducer fold on the hot path (additive, but real).
- Requires disciplined migration ordering (backfill → verify → reader → writer → delete fallbacks) to
  keep the B3 clobber window closed.

#### Neutral

- `WPInnerStateDelta` is generic in shape but typed per field — deliberately not a free bag.
- The static-model election (enrich `WPMetadata` vs elect `WorkPackageEntry`) is unblocked by this
  work but intentionally out of scope.

### Confirmation

- **AC-1** no `implement`/`mark-status`/`move-task`/review action writes `tasks/WP##.md`.
- **AC-2** claim-liveness resolves from the snapshot; a claimed WP with empty frontmatter is live.
- **AC-3** done-inference resolves from `InnerStateChanged` subtask deltas — the **merged red test
  `test_issue_2684_subtask_completion_event_sourced.py` flips green**.
- **AC-4** Activity Log / History / review sections render from events with no content loss.
- **AC-5** a full lifecycle produces a **stable content hash** (headline proof).
- **AC-6** migration backfills idempotently (deterministic namespaced ULID seed-ids), with an honest
  timestamp-reconstruction contract for checkbox marks (clamp to `claimed`).
- A **refactor-stable architectural test** asserts no consumer reads a dynamic frontmatter field as
  authority (the #2093 invariant, generalising the shipped phase-2 lane-authority guard).

## Pros and Cons of the Options

### Option A — generic `InnerStateChanged` annotation event (chosen)

**Pros:** true SSOT for (a)+(b)+(c); delivers the subtask projection the gates need; one reusable,
extensible mechanism; typed delta avoids a new split-brain.
**Cons:** touches FSM + wire model + reducer precedence; additive hot-path fold; migration discipline.

### Option B — fold onto transitions + `policy_metadata`

**Pros:** near-zero FSM/reducer change.
**Cons:** complete only for `shell_pid`; resume emits nothing → stale PID → claim-liveness degrades to
the git-timestamp heuristic (a false-stale window on the exact path AC-2 protects); subtasks and notes
still need a home; gate re-sourcing is *still* required. **Rejected** — partial SSOT for more net work.

### Option C — self-edges in the FSM matrix

**Pros:** reuses the transition path.
**Cons:** redefines the "a transition changes lane" invariant; ripples into rendering, drift, and
done-inference for no capture benefit over A. **Rejected.**
