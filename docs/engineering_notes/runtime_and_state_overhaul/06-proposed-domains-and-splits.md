# 06 — Proposed Domains & Splits (for discussion)

> **Refined by [07](./07-existing-pattern-and-domain-extraction.md).** After mapping the existing
> infra-context pattern, several proposals here are sharpened in `07`: the context family (§2/§6) is
> updated to reflect that `OperationalContext` **already exists** (with different semantics — a
> naming collision to resolve), and the MissionStatus/MissionFlow extractions are assessed in detail.
> Read `06` for the conceptual frame, `07` for the evidence-grounded refinement.

This is the **design-forward** grounding artefact. It proposes a candidate bounded-context
decomposition and an execution-topology model, then frames the **open questions** we will resolve
together. It deliberately does **not** pick a final option — that is the next conversation.

Everything here is vetted against the hard-constraint checklist in `04` §"hard-constraint checklist".

---

## 1. Naming first (DIRECTIVE_032 gate)

Before structure, the vocabulary. Per the Mission Type/Mission/Mission Run ontology (ADR
`2026-04-04-2`, `03` A6), the object #1619 calls `MissionExecutionContext` is a **Mission Run**
concern. Proposed canonical terms (to confirm in session, then glossary + ADR):

| Term | Proposed meaning | Distinct from |
|------|------------------|---------------|
| **Mission Run** | one persisted runtime/session instance (`.kittify/runtime/`, `mission_run_id`) | Mission (`mission_id`), Mission Type (blueprint) |
| **Execution Topology** | the physical layout for a mission: primary checkout, coord worktree/branch, lane worktrees/branches, integration branch | the *logical* WP/lane state in `status/` |
| **Operation Context** | the resolved-once value handed to a single command invocation: which dirs/branches/cwd this operation reads, writes, commits to, and prompts from | the long-lived Mission Run |

> The split between **Execution Topology** (the durable physical facts) and **Operation Context**
> (the per-invocation projection of those facts for *this* command) is, I think, the key modeling
> insight — and the first thing to pressure-test together. #1619's flat field list mixes both.

---

## 2. Proposed bounded contexts

Boundaries drawn by **ubiquitous language** (DIRECTIVE_031), not lifecycle stage. Target a **small**
number of contexts (over-splitting is a named failure mode, `04`).

```
                 ┌──────────────────────────────────────────────────────┐
                 │  doctrine  ◄────────────  charter   (governance)      │  unchanged, clean
                 └──────────────────────────────────────────────────────┘
                                      ▲ consumed by
 ┌───────────────────────────────────────────────────────────────────────────────────┐
 │ specify_cli (control plane)                                                         │
 │                                                                                     │
 │  ┌─────────────────────┐  resolves   ┌──────────────────────────────┐              │
 │  │ Mission Identity     │───────────►│ Execution Topology            │  (NEW home)  │
 │  │ mission_id / mid8 /  │            │  - primary / coord / lane /   │              │
 │  │ slug / run_id        │            │    integration roots+branches │              │
 │  └─────────────────────┘            │  - CoordinationWorkspace prim. │              │
 │            │                         │  - lanes.json (fail-closed)    │              │
 │            │                         └──────────────┬───────────────┘              │
 │            │                                        │ projects per-operation        │
 │            ▼                                        ▼                                │
 │  ┌─────────────────────┐               ┌──────────────────────────────┐            │
 │  │ Status (kanban)      │◄──consumes────│ Operation Context (value obj) │            │
 │  │ event log + State    │   where?      │  read_dir / write_dir /       │            │
 │  │ Pattern + lifecycle  │               │  destination_ref / cwd /      │            │
 │  │ service  [BOUNDED]   │               │  prompt_source_dir            │            │
 │  └─────────────────────┘               └──────────────┬───────────────┘            │
 │            ▲                                           │ consumed by                 │
 │            │ commits via                               ▼                             │
 │  ┌─────────────────────┐               ┌──────────────────────────────┐            │
 │  │ Git Transaction      │◄──────────────│ Command surfaces             │            │
 │  │ safe_commit / Book-  │  one atomic   │ implement / review / move-   │            │
 │  │ keepingTransaction   │  domain       │ task / next / orchestrator   │            │
 │  └─────────────────────┘               └──────────────────────────────┘            │
 └───────────────────────────────────────────────────────────────────────────────────┘
```

### Context catalogue

| # | Context | Owns | Today (scattered across) | Boundary status target |
|---|---------|------|--------------------------|------------------------|
| C1 | **Mission Identity** | `mission_id`, `mid8`, `mission_slug`, `mission_run_id` resolution + meta.json read | `_identity_for_request`, `_resolve_mission_ulid`, `resolve_mission_identity`, `mid8_from_slug` (≥6 sites) | small deep module; **identity-only** outputs |
| C2 | **Execution Topology** *(NEW)* | the 4 roots (primary/coord/lane/integration) + their branches; `CoordinationWorkspace`; `lanes.json` ingestion; sparse rules | `CoordinationWorkspace`, `resolve_mission_read_path`, `BookkeepingTransaction` acquire, 4 duplicated path-builders, `core/worktree.py` | the missing owner; wraps the primitive |
| C3 | **Operation Context** *(NEW, value object)* | per-invocation projection: `read_dir`, `write_dir`, `destination_ref`, `allowed_command_cwd`, `prompt_source_dir`, `execution_workspace` | nothing — these are recomputed everywhere | the #1619 object; deep + small interface |
| C4 | **Status / Kanban** | lane state machine, event log, reducer, atomic lifecycle service | `status/` | **already bounded — preserve & consume** |
| C5 | **Git Transaction** | `safe_commit`, `BookkeepingTransaction`, one-atomicity-domain commits | `git/commit_helpers.py`, `coordination/transaction.py` | tighten to single chokepoint |
| C6 | **Agent Contract** | prompt/help rendering **from** C3 | inline strings in `agent/workflow.py` etc. | rendered, not authored |

C1, C4, C5 mostly **exist**; the work is C2 + C3 (the missing owner and its per-operation
projection) plus rerouting C6 to render from C3 and collapsing the duplicated resolvers into C2.

---

## 3. Context map (relationship classification, per `04` Context-Mapping tactic)

| Pair | Pattern | Note |
|------|---------|------|
| Operation Context (C3) → Status (C4) | **Conformist / OHS** | C3 consumes `status/`'s public API; status is upstream and stable |
| Operation Context (C3) → Git Transaction (C5) | **Customer/Supplier** | C3 hands C5 a resolved `(worktree_root, destination_ref)`; C5 enforces the invariant |
| Execution Topology (C2) → Mission Identity (C1) | **Shared Kernel (tiny)** | both touch `meta.json` identity fields; co-own a minimal identity model |
| Command surfaces → Operation Context (C3) | **OHS** | one published way to get an operation's context |
| Agent Contract (C6) → Operation Context (C3) | **Conformist** | prompts render from C3 fields verbatim |
| Execution Topology (C2) → `lanes.json` | **Published Language** | lanes.json is the planner↔runtime interchange format; fail-closed |

No pair should be **Big Ball of Mud** in the target; several are today (C2↔C4↔C5 temporal coupling, `03` C).

---

## 4. Where it lives (package placement)

Per the deep-dive's **moratorium on new top-level `specify_cli/*/` packages** and the `mission_runtime/`
suggestion (`03` B) + epic #992:

**Proposed:** a single new umbrella package, e.g. `src/specify_cli/mission_runtime/`, housing C2 + C3
(and absorbing the duplicated resolvers), with C1 either inside it or as a thin `mission_runtime/identity.py`.
`status/` (C4), `git/`+`coordination/transaction.py` (C5) stay where they are and are *consumed*.

This keeps `doctrine ← charter ← specify_cli` intact and avoids adding 3–4 sibling packages (the
charter-split anti-pattern).

---

## 5. Candidate design options (to weigh together — NOT yet chosen)

The synthesis (`05` §6) argues *some* context owner is necessary. The real choice is its **shape**.
Three coherent options, with the trade space:

### Option A — Pure value object + resolver factory
`MissionExecutionContext` is an immutable dataclass; `resolve_operation_context(cwd, mission, op_kind)`
builds it; commands receive it as a parameter.
- ➕ Simplest; trivially testable; no lifecycle; matches "resolved once, passed through".
- ➖ Doesn't *enforce* the atomicity domain (I-4) — a caller can still commit out-of-band.
- ➖ "op_kind" branching (read vs write vs review) may bloat the resolver.

### Option B — Context object + operation service (context manager)
A `MissionOperation` service wraps the value object and owns the commit seam: `with mission_operation(...)
as op:` → `op.read_dir`, `op.emit_transition(...)`, `op.commit()` all bound to one atomicity domain.
- ➕ Enforces I-4 (one atomicity domain) structurally; natural home to *extend* the atomic lifecycle service (ADR A3).
- ➕ Prompts render from `op`; transactional + companion writes can't desync.
- ➖ Bigger surface; migration touches more call sites; risk in the hottest cluster.

### Option C — Strangler façade over today's two resolvers
Introduce C3 as a **read-through façade** that delegates to the existing `resolve_mission_read_path`
(reads) and `BookkeepingTransaction` identity (writes), unifying the *interface* first and the
*implementation* later.
- ➕ Lowest immediate risk; honors DIRECTIVE_024 + bus-factor; ships the e2e regression early as the ratchet.
- ➕ Lets us delete duplicated path-builders incrementally behind a stable interface.
- ➖ Doesn't fix I-4 or #1602-class issues until a later phase; interim double-maintenance.

> My provisional lean (for debate): **C as the migration vehicle, converging on B as the target
> shape** — i.e., introduce the façade + e2e ratchet now (Strangler), and grow the commit-owning
> operation service underneath it so the atomicity domain (I-4) and the agent-contract rendering
> (I-6) land without a big-bang. Option A is the fallback if B's service proves too invasive for the cluster's test debt.

---

## 6. Open design questions for our session

1. **Topology vs Operation split (§1):** do we model durable **Execution Topology** separately from
   the per-invocation **Operation Context**, or is one flat object (#1619's field list) enough?
2. **Object vs service (§5):** value object (A), operation service (B), or façade-now/service-later (C)?
3. **Atomicity domain (I-4):** is "one commit per operation, `worktree_root == destination_ref`" a
   hard rule we enforce in the seam, or a guideline? (Decides whether #1618/#1348/#1602 are *closed*
   or merely *avoided*.)
4. **Scope of C2's authority:** does Execution Topology also own **workspace creation** (closing F-02
   lane-dependency inheritance) and the **merge→`done`** seam (closing F-03), or do those stay in
   `merge.py`/`implement.py` and merely *consume* C2?
5. **`mission_run_id` materialization:** do we make Mission Run a first-class persisted object now
   (`.kittify/runtime/`, ADR A6), or defer and let the Operation Context be ephemeral?
6. **Migration ratchet:** is the #1619 e2e regression (main+lane CWD parity) the *gate* we build
   first, before any refactor? (I strongly recommend yes — it's the only thing that proves a
   surface was actually unified rather than re-masked.)
7. **Blast-radius sequencing:** which surface goes first? Candidate order by isolation/value:
   `agent/status.py` (pure read, untouched by #1627, low risk) → `runtime_bridge` query-mode →
   `workflow.py` fix-mode → the commit seam (#1618). Confirm or reorder.
8. **Naming ratification (DIRECTIVE_032):** lock `Mission Run` / `Execution Topology` / `Operation
   Context` (or alternatives) into the glossary + an ADR *before* code.

---

## 7. Proposed path to a decided design

1. **This session:** answer §6 Q1–Q3 and Q8 → choose target shape + vocabulary.
2. **Draft ADR(s)** under `architecture/3.x/adr/`: (a) Mission Run / Operation Context model; (b)
   one-atomicity-domain commit rule. Record confirmed terms (DIRECTIVE_032).
3. **Build the e2e ratchet** (Q6) as a failing test that asserts main/lane CWD parity.
4. **Strangler increment 1**: introduce C3 interface; route the lowest-risk surface (Q7) through it.
5. **Iterate** surface-by-surface, deleting duplicated resolvers as each is absorbed; grow C2/C5
   commit ownership; reroute C6 prompts.
6. **Close** #1619 when the AC-3 invariant (no raw reads outside the resolver, except documented
   fallbacks) holds and the e2e regression is green from both CWDs.

> Alignment note: this is the same target as team epic **#992 "centralize domain invariants"** (`03`
> C). We should reconcile #1619 and #992 explicitly — likely #1619 *is* the execution-topology slice of #992.
