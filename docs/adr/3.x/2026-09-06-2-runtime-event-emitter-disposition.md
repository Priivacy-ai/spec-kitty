---
title: 'ADR: RuntimeEventEmitter Seam Disposition — Rewire-Ready Consolidation, Not Retirement'
description: 'Adjudicates the permanently-no-op runtime.next.event_emitter seam: keep it as the reserved E3 producer seam, merge the duplicate-named concrete class into the _internal_runtime Protocol/NullEmitter, fix the buffer flush-target bug, and defer live producer wiring — bounding what Mission B dead-port-disposition may touch.'
status: Proposed
date: '2026-09-06'
---

## Context and Problem Statement

`src/runtime/next/event_emitter.py` defines a concrete class `RuntimeEventEmitter`
whose eight `emit_*` callbacks are permanently no-op (`pass` / `del payload`,
`event_emitter.py:65-88`) and whose `seed_from_snapshot` is an explicit no-op
(`:60-61`). It is the residue of the retired sync `EventEmitter` (issue #5): the
journal/outbox producer died with the sync transport, and what remained is the
*seam* — a call surface the `next` bridge already threads so a future producer
can register here without reshaping the bridge.

The dead-code census (report 25 §1a) flagged this class as **DORMANT with a stale
justification** and leaned toward retiring it — replacing the construction with
`_internal_runtime.events.NullEmitter`, retyping the signatures against the
Protocol of the same name, and deleting the file (~120 LOC including threading).
The design red-team (report 24 §4) challenged that lean as **wrong-headed** and
recommended REWIRE-or-explicit-defer instead.

This decision matters because the disposition is a prerequisite for the **Mission B
`dead-port-disposition`** work: WP01 of that mission acts on this seam, and it must
know whether it is deleting a dead port or consolidating a reserved one. Getting it
wrong in either direction is costly — a naive deletion throws away a designed last
mile and silently changes rollback behavior; leaving it untouched preserves a
name collision, a stale docstring, and a latent correctness bug.

The following facts were verified against `src/` at HEAD `e721763759` (3.2.7rc1)
and against the installed `spec_kitty_events` 9.1.6 package:

- **The hosted contract already exists and is waiting for a producer.** Installed
  `spec_kitty_events` 9.1.6 carries all six `mission_next` runtime moments —
  `MissionRunStarted`, `NextStepIssued`, `NextStepAutoCompleted`,
  `DecisionInputRequested`, `DecisionInputAnswered`, `MissionRunCompleted` — in
  `zeitgeist_attrs.VOLATILE_EVENT_TYPES` (verified: 6/6 present), with codec and
  per-type redaction entries. The seam is the designed last mile of that contract,
  not speculative 4.0.0 vocabulary.
- **The seam is explicitly reserved in-tree.** Two conformance tests name
  `runtime.next.event_emitter` as the reserved E3 producer seam and say its
  payloads "belong back in this file" when a real emitter is wired
  (`tests/status/test_producer_conformance.py`,
  `tests/contract/test_identity_contract_matrix.py`).
- **The retention docstring is stale.** `event_emitter.py:1-10` claims E3 will
  "register a real handler (the zeitgeist moment fan-out) at this seam." The
  zeitgeist moment fan-out already landed at a *different* seam —
  `src/specify_cli/status/adapters.py:364-365`
  (`ensure_zeitgeist_moment_handlers()`, gated by
  `SPEC_KITTY_SYNC_MINIMAL_IMPORT`). The docstring points E3 at a seam E3 already
  bypassed.
- **There is a name collision.** A *second, live* class named
  `RuntimeEventEmitter` — a `Protocol` — exists at
  `src/runtime/next/_internal_runtime/events.py:67-88`, alongside a concrete
  `NullEmitter` (`:95-123`) and real structural adapters (`DecisionGitLog`,
  `_BufferingRuntimeEmitter`). Two classes with one name in the same subtree is
  the duplication smell the census (report 25 §1f) named.
- **The concrete class carries surface the Protocol/NullEmitter lack.** The bridge
  binds the *concrete* class: it constructs it via `RuntimeEventEmitter.for_feature(...)`
  at `runtime_bridge.py:1552` and `:2739`, and calls `sync_emitter.seed_from_snapshot(...)`
  at `:1614` and `:2745`. Neither `for_feature` nor `seed_from_snapshot` exists on
  the `_internal_runtime` Protocol *or* on `NullEmitter`. A "just swap in NullEmitter"
  retirement is therefore **not a drop-in**.
- **A latent correctness bug lives on this chain.** Under the strict retrospective
  gate, `engine_emitter` is replaced by a `_BufferingRuntimeEmitter`
  (`runtime_bridge.py:2149-2150`) so a rolled-back terminal advance cannot fire an
  unretractable `MissionRunCompleted`. On gate-pass the buffer is flushed with
  `buffer.flush(ctx.sync_emitter)` (`:2187`) — into the **plain no-op**
  `sync_emitter`, **not** `ctx.emitter_for_engine`, the `DecisionGitLog`-wrapped
  emitter the non-gated path uses (`:2124-2126`, wrapped at `:1560`). Consequence:
  buffered decision events on a strict-gated terminal advance never reach the
  coordination-branch decision git log, whereas on the non-gated path they do
  (via `emitter_for_engine`). Today this is masked because `sync_emitter` is no-op
  and `DecisionGitLog` is the only real channel — but any disposition that touches
  this chain will either silently freeze or silently fix it, so it must be
  adjudicated explicitly.

## Decision Drivers

- **Do not discard a reserved, contract-backed seam.** The hosted vocabulary is
  provisioned and the seam is explicitly reserved by tests; retiring it means
  re-adding ~29 `sync_emitter` threading sites plus two construction sites when E3
  lands.
- **Do not overreach into feature work.** Wiring a *live* zeitgeist producer is E3
  work with hosted-egress and redaction implications; a disposition ADR (and a
  dead-port-disposition mission) must not smuggle that in.
- **Resolve the honest defects the census surfaced** — the name collision, the
  stale docstring, and the flush-target bug — rather than freezing them under a
  "leave it alone" decision.
- **Preserve behavior for every current caller.** The only live behavior on this
  chain is `DecisionGitLog` wrapping the no-op; a consolidation must keep decision
  events durably committed, and must not add commit semantics to plain-door callers.
- **Give Mission B a fail-closed boundary** so WP01 knows exactly what is safe to
  change and what is ADR-blocked.

## Considered Options

1. **Rewire-ready consolidation (chosen)** — keep the seam; merge the duplicate
   concrete class into the `_internal_runtime` Protocol/NullEmitter world (promote
   `for_feature` + `seed_from_snapshot` onto the seam surface, delete
   `event_emitter.py`, retype the bridge against the single Protocol); fix the
   flush target; correct the docstring. Do **not** wire a live producer — defer
   that to E3.
2. **Retire now** — delete the seam, collapse construction onto `NullEmitter`,
   drop `for_feature`/`seed_from_snapshot`, remove the threading.
3. **Status quo** — keep both classes, the stale docstring, and the latent bug
   as-is.
4. **Rewire fully now** — wire a live zeitgeist-moment producer at the seam
   immediately. *Out of scope* (this is E3 feature work); listed only to name it.

## Decision Outcome

**Chosen option: "Rewire-ready consolidation" (Option 1)**, because it is the only
option that (a) honors the reserved, contract-backed seam, (b) removes the name
collision and stale docstring the census flagged, (c) forces the latent flush-target
bug to be adjudicated rather than silently frozen, and (d) keeps live-producer
feature work (E3) cleanly deferred. It is a **rename-and-merge plus a bug fix**, not
a port deletion and not feature work.

Concretely, the ADR adjudicates the five questions Mission B WP01 must answer:

**(a) Rewire target + registry mechanism.** The canonical interface is the
`_internal_runtime/events.py` `RuntimeEventEmitter` **Protocol**; the seam's
null-object is `NullEmitter`. The construction sites (`runtime_bridge.py:1552,2739`)
become the *registry seam*: a factory that returns `NullEmitter` by default (and
under `SPEC_KITTY_SYNC_MINIMAL_IMPORT`) and, when E3 registers one, a real
Protocol-conforming producer — mirroring the env-gated import-tail registration
pattern proven at `status/adapters.py:364-365`
(`ensure_zeitgeist_moment_handlers()`). The bridge depends on the Protocol and a
factory, never on a concrete class import.

**(b) The Protocol's missing surface.** `for_feature` (mission-identity resolution,
the one thing a future adapter needs — `runtime_bridge.py:1552,2739`) and
`seed_from_snapshot` (`:1614,2745`) must be added to the seam before/as the
concrete class is deleted. Preferred shape: `for_feature` as a `NullEmitter`
classmethod (or a module-level factory) and `seed_from_snapshot` as a
no-op/​pass-through on `NullEmitter`, so the bridge's two construction sites and two
seed sites keep compiling against the consolidated seam.

**(c) The buffer flush-target bug.** It is real and must be **fixed, not frozen**.
`buffer.flush(...)` (`runtime_bridge.py:2187`) must target the durable decision
sink the non-gated path uses — `ctx.emitter_for_engine` (the `DecisionGitLog`
wrap, `:2124-2126`) — not the plain no-op `ctx.sync_emitter`. The fix is a coupled
correctness change and must land with a red-first test proving a strict-gated
terminal advance commits its buffered decision events to the decision git log.
(There is no double-emit risk: on the gated path the engine wrote only into the
buffer, so the flush is the first and only `DecisionGitLog` write.)

**(d) The name collision.** Resolve it by **removing the duplicate**: delete the
concrete `event_emitter.py::RuntimeEventEmitter` and keep the single canonical
`RuntimeEventEmitter` Protocol in `_internal_runtime/events.py`. (If a transitional
step must keep both classes momentarily, the concrete one is renamed
`NullRuntimeEventEmitter` — but the target state has one name.)

**(e) Mission B scoping.** See Consequences.

### Consequences

#### Positive

- The reserved E3 seam and its `for_feature`/`seed_from_snapshot` capability
  survive; a future producer registers an adapter without re-threading the bridge.
- One class named `RuntimeEventEmitter` remains; the duplication smell is gone.
- The stale docstring is corrected to point at `status/adapters.py` (the real
  zeitgeist seam), so the next agent is not misdirected.
- A latent correctness bug (strict-gated decision events skipping the git log) is
  fixed with a regression test instead of being silently frozen.
- Net LOC still drops (~88 LOC of concrete class + collapsed threading), so the
  census's simplification goal is largely met — just via merge, not deletion.

#### Negative

- More work than a straight `git rm`: the merge touches `runtime_bridge.py`,
  `runtime_bridge_engine.py`, `_internal_runtime/events.py`, and the two
  conformance tests' comments, and adds a red-first test for the flush fix.
- The flush-target fix is a behavior change (decision events now durably commit on
  the strict-gated path). It is a *correctness* change, but it must be called out
  and tested, not slipped in.
- The seam remains no-op end-to-end until E3; this ADR does not deliver a live
  producer, so the "waiting for a producer" state persists (by design).

#### Neutral

- The zeitgeist moment fan-out at `status/adapters.py:364` is unaffected — it is a
  separate, already-live seam; this decision only stops the emitter docstring from
  claiming to be it.

### Mission B (`dead-port-disposition`) scope boundary

**ADR-BLOCKED — Mission B must NOT:**

- Delete `event_emitter.py` as a *pure port deletion* / "collapse onto NullEmitter
  and drop the seam."
- Remove the `for_feature` / `seed_from_snapshot` capability.
- Change the buffer flush semantics without fixing the flush target (freezing the
  bug is prohibited).
- Wire a live zeitgeist producer (that is E3, out of scope).

**SAFE under this ADR — Mission B WP01 may:**

- Perform the rename-and-merge consolidation (behavior-preserving apart from the
  flush fix): promote `for_feature`/`seed_from_snapshot` onto the seam, delete the
  duplicate concrete class, retype the bridge against the Protocol + factory.
- Fix the flush target to `ctx.emitter_for_engine`, with a red-first regression
  test.
- Correct the `event_emitter.py` docstring (or its successor's) and update the two
  conformance tests' comments to point at the consolidated seam.

### Confirmation

This decision is validated when Mission B WP01 lands a change in which: (1) exactly
one class named `RuntimeEventEmitter` exists under `src/runtime/next/`; (2) the
bridge constructs the seam via a factory returning `NullEmitter` by default with
`for_feature`/`seed_from_snapshot` intact; (3) a new regression test proves a
strict-retrospective-gated terminal advance commits its buffered decision events to
the decision git log; and (4) the existing bridge-parity and producer-conformance
tests stay green. Confidence: **high** on the facts (all verified at
`e721763759` against installed `spec_kitty_events` 9.1.6); **medium** on the exact
consolidation mechanics, which are Mission B's to finalize within this boundary.

## Pros and Cons of the Options

### Option 1 — Rewire-ready consolidation (chosen)

Keep the seam, merge the duplicate class into the Protocol/NullEmitter, fix the
flush target, correct the docstring; defer the live producer.

**Pros:**

- Preserves a reserved, contract-backed seam and its identity-resolution surface.
- Eliminates the name collision and the stale docstring.
- Fixes the latent flush-target bug under test.
- Still achieves most of the census's LOC reduction.

**Cons:**

- More involved than a deletion; touches several bridge files and adds a test.
- Introduces a (correct, tested) behavior change on the strict-gated path.

### Option 2 — Retire now

Delete `event_emitter.py`, collapse onto `NullEmitter`, drop the threading.

**Pros:**

- Maximal immediate simplification; smallest diff to *count*.

**Cons:**

- Not a drop-in: `for_feature`/`seed_from_snapshot` are absent from the Protocol
  and `NullEmitter`, so the bridge would need surgery anyway.
- Throws away a reserved seam the hosted `spec_kitty_events` 9.1.6 contract is
  waiting on; E3 must re-thread ~29 sites + 2 construction sites later.
- Silently *freezes* the flush-target bug (or, if it re-points construction,
  silently changes it) without adjudication or a test.
- Contradicts two in-tree conformance tests that reserve the seam.

### Option 3 — Status quo

Leave both classes, the stale docstring, and the bug in place.

**Pros:**

- Zero immediate risk; no diff.

**Cons:**

- Preserves the two-classes-one-name collision the census flagged.
- Keeps a docstring that actively misdirects the next agent about the E3 seam.
- Leaves a real correctness bug (strict-gated decision events skipping the git
  log) latent and undocumented.

### Option 4 — Rewire fully now (out of scope)

Wire a live zeitgeist-moment producer at the seam immediately.

**Pros:**

- Delivers the end-to-end runtime-moment fan-out.

**Cons:**

- Feature work (E3) with hosted-egress, redaction, and ordering concerns — not a
  disposition, and outside a dead-port-disposition mission. Named only to exclude
  it.

## More Information

- Evidence: report 24 (`work/post-convergence/24-coreloop-design-redteam-alphonso.md`,
  §4 port dispositions) and report 25 (`25-dead-code-census-randy.md`, §1a/§1f/§4).
- Related decision: [`2026-04-25-1-shared-package-boundary.md`](2026-04-25-1-shared-package-boundary.md)
  (the `_internal_runtime` internalization that produced the second seam).
- Code anchors (HEAD `e721763759`): `src/runtime/next/event_emitter.py`;
  `src/runtime/next/_internal_runtime/events.py:67-123`;
  `src/runtime/next/runtime_bridge.py:195,1215,1472,1552,1560,1614,2124-2126,2149-2150,2187,2739,2745,2754`;
  `src/runtime/next/runtime_bridge_retrospective.py:69-149`;
  `src/specify_cli/status/adapters.py:364-365`; installed
  `spec_kitty_events/zeitgeist_attrs.py` (`VOLATILE_EVENT_TYPES`);
  `tests/status/test_producer_conformance.py`,
  `tests/contract/test_identity_contract_matrix.py`.
- Consumed by: Mission B `dead-port-disposition` (WP01). Sibling governance PR: #3888.
