# Data Model — Lifecycle Gate Execution Context and Tool-Artifact Ownership

**Phase 1 output.** Entities, invariants, and state transitions. Field names are indicative;
the binding contracts are in `contracts/`.

---

## GateExecutionContext (value object)

The bundle a gate is **handed** and cannot derive. Immutable for the duration of one gate
invocation.

| Field | Type | Meaning |
|---|---|---|
| `surface` | path | The concrete tree/directory the fact is judged from |
| `surface_kind` | `TopologySurface` | Which physical tree this is (see below) |
| `ref` | git sha or symbolic ref | The reference point `surface` is expected to be at |
| `phase` | `LifecyclePhase` | Where in the mission lifecycle the judgement is happening |
| `mission_slug` | str | Owning mission |

**Invariants**

- **GEC-1 — Not derivable.** A gate must receive this; it may not construct one from ambient
  state (`repo_root`, `os.getcwd()`, a caller-supplied bare dir). Enforced by an architectural
  test pinning a single construction site per entry point.
- **GEC-2 — Ref agreement.** `surface` must actually be at `ref` when the gate runs. A mismatch
  raises rather than proceeding, mirroring the existing `safe_commit` HEAD-vs-destination assert.
- **GEC-3 — Total resolution over the REAL state set.** The context is built by consuming the
  **existing** `probe_coord_state` / `CoordState` classifier
  (`missions/_read_path_resolver.py:256`) — never a new one written beside it. Each state has one
  declared answer: `DELETED` raises `CoordinationBranchDeleted`; `EMPTY` and `UNMATERIALIZED`
  resolve primary and **stamp** `surface_kind = PRIMARY`; `MATERIALIZED` resolves coord.
  *Corrected 2026-07-23*: an earlier form said "an unresolvable declared home raises", which
  contradicted a landed green test and omitted `EMPTY` entirely.
- **GEC-5 — A stamp is not permission.** Stamping a substituted surface makes it visible; it does
  not make it authoritative. A gate asked to judge a kind whose declared home is COORD, against a
  surface resolved as PRIMARY, must return the cannot-evaluate outcome (GEC/C2) — **not** a
  verdict. Without this the create-window reproduces #2885's exact failure (empty surface → every
  work package skipped → pass by default), only with an honest label attached.
- **GEC-4 — Topology-neutral.** No field, name, or branch of this type may be conditioned on
  coordination topology (C-004), and none may read the `flattened` flag (R-005).

---

## TopologySurface (enum)

Live today: `PRIMARY` · `COORD`. Landing with the surface→filesystem translation seam:
`LANE` · `CONSOLIDATED` · `TEMP`.

The canonical vocabulary for *which physical tree* — `surface` Sense 2, renamed from `Surface`
in `mission_runtime/artifacts.py` (ADR 2026-07-23-1; the rename landed on this branch — a bare commit SHA is intentionally not cited, since rebases rewrite it). A recorded judgement
states where it came from (NFR-003) using these names. `CONSOLIDATED` exists only from
`LifecyclePhase.POST_CONSOLIDATION` onward.

The three planned members are declared **with** the translation seam, never before it: a member
no caller can resolve to a location is a phantom, and the seam's totality test exists to catch
exactly that.

---

## LifecyclePhase (enum, ordered)

`REVIEW` < `ACCEPT` < `POST_CONSOLIDATION`

Ordering is meaningful: a gate declares the minimum phase at which its subject *can* exist.

**Invariant PH-1** — A gate invoked below its declared minimum phase returns
`NOT_APPLICABLE_IN_PHASE`. It does **not** return a pass or a fail. This is the single rule
that converts #1834 from a site fix into a property.

> Whether `IMPLEMENT` needs representation is deferred to IC-01's findings (see research.md).

---

## NegativeInvariant (extended)

Existing entity. New fields carry provenance.

| Field | Type | Status | Meaning |
|---|---|---|---|
| `description` | str | existing | What must be absent |
| `verification_method` | `grep_absence` \| `custom_command` | existing | How to check |
| `verification_command` | str | existing | The check |
| `scope` | str \| null | existing | Directory scope for `grep_absence` |
| `result` | `Result` | existing, **extended** | Outcome — see state machine |
| `verified_ref` | git sha \| null | **new** | The ref the outcome was established against |
| `verified_surface_kind` | `TopologySurface` \| null | **new** | Which surface established it |
| `deferred_reason` | str \| null | **new** | Why judgement was postponed |
| `deferred_to_phase` | `LifecyclePhase` \| null | **new** | Phase at which it will be judged |
| `provenance_origin` | `recorded` \| `legacy_unrecorded` | **new** | `legacy_unrecorded` (FR-014) permits null provenance for pre-schema results; `recorded` requires it |

**Result** — `pending` · `confirmed_absent` · `still_present` · `verification_error` ·
**`deferred_to_consolidation`** (new)

**Invariants**

- **NI-1 — Provenance required, with one typed legacy escape.** Any `result` other than
  `pending` must carry `verified_ref` **and** `verified_surface_kind` — **unless** its
  `provenance_origin` is `legacy_unrecorded` (FR-014), the sentinel the migration writes for
  results recorded before provenance existed. That origin means the surface is genuinely
  unknowable, so both fields stay null and `validate_matrix_evidence` accepts their absence for
  that origin only. `legacy_unrecorded` is a `provenance_origin` value, **not** a
  `TopologySurface` member — the surface enum's anti-phantom rule forbids an unresolvable member,
  so the sentinel cannot live there. Every other origin (`recorded`) requires full provenance.
- **NI-2 — Never overwrite a TERMINAL result.** A recorded **terminal** result
  (`confirmed_absent` / `still_present` / `verification_error`) is preserved verbatim; re-running
  never replaces it. *Corrected 2026-07-23*: the landed guard predicates on
  `result != "pending"` (`matrix.py:351`). Once `deferred_to_consolidation` exists as a
  non-`pending` value, that predicate would **freeze it**, making NI-4 and provenance C6
  impossible. The guard must move from "not pending" to "member of the terminal set" — a code
  change that belongs to the same work package as the fourth result value, not a later one.
- **NI-3 — Refuse, don't guess.** A `pending` invariant whose subject cannot exist in the
  current `GateExecutionContext.surface` transitions to `deferred_to_consolidation` with a
  `deferred_reason` — never to `still_present` (FR-003).
- **NI-4 — Deferral is not skipping.** `deferred_to_consolidation` is not terminal. It must be judged
  at `LifecyclePhase.POST_CONSOLIDATION` (FR-004).
- **NI-5 — Verdict neutrality, via a fourth value.** `deferred_to_consolidation` contributes
  neither a failure nor a silent pass at `ACCEPT`. The existing three-value vocabulary
  (`pass` / `fail` / `pending`) has **no assignment that satisfies both**: allowing the value
  yields `pass` (silent), disallowing it yields `fail`, and grouping it with `pending`
  reproduces the very block being removed. `overall_verdict` therefore gains a fourth value,
  **`pass_pending_consolidation`** — acceptance is not blocked, and the mission cannot reach the
  `done` terminal state while any invariant remains deferred. (`canceled` is reachable regardless:
  cancellation resolves outstanding deferrals to a `canceled` disposition — see AM-5 — so
  abandonment is never a deadlock.)
- **NI-6 — Deferral is scheduled, not unknown, and its enforcer is EXTERNAL.** The fourth value
  is honest because deferral names a *required follow-up*, not an absence of information.
  **Operator decision (2026-07-23): the mission loop does not and will not enforce it.** The
  acceptance matrix has exactly one reader (`gates_core.py:311`, inside the accept gate, which
  runs pre-consolidation), so no loop guardrail can fire at the moment enforcement is needed.
  Pretending otherwise would be the convention-dressed-as-constraint this mission exists to
  remove.
  Enforcement therefore lives in **CI, on the pull request** — a consistency check that fails
  when any invariant is left `deferred_to_consolidation`. That is where the consolidated tree
  and the artifact are both available.
- **NI-7 — The contract is disclosed at assignment time.** Because Spec Kitty runs in other
  people's repositories, where this project's CI check does not exist, assigning
  `deferred_to_consolidation` must **tell the operator** that the loop will not verify it and
  what gate they need. Silent reliance on an enforcer that exists only upstream would export the
  exact failure mode being fixed.

### Result state machine

```
                    ┌──────────────────────────────────────────┐
                    │                pending                    │
                    └───┬───────────────┬──────────────────┬────┘
      judgeable here     │               │ not judgeable    │ check errored
                         ▼               ▼                  ▼
              confirmed_absent /   deferred_to_consolidation   verification_error
                still_present            │
                    │                    │ at LifecyclePhase.POST_CONSOLIDATION
                    │                    ▼
                    │          confirmed_absent / still_present
                    │                    │   (verified_surface_kind = CONSOLIDATED)
                    ▼                    ▼
                  ── terminal; never re-judged (NI-2) ──
```

`still_present` reached at `POST_CONSOLIDATION` fails the **post-consolidation verification op**
and names the invariant (FR-005). It does NOT fail the consolidation itself — see the
provenance contract C7 for why that separation matters.

---

## ToolArtifactOwner

Generalisation of `coordination/transaction.py::BookkeepingTransaction` from *owner of writes
targeting the coordination branch* to *owner of bytes spec-kitty generates, on any surface*.

**Already present** (reused, not rebuilt): policy pre-flight with stable allow/refuse codes,
byte-snapshot `write_artifact`, `stage_path`, `defer_outbound`, `commit_idempotent` with a
no-op receipt for an already-clean tree, and a surgical `_rollback` that truncates and restores
from byte snapshots rather than running `git checkout --`.

**To add**

| Capability | Why |
|---|---|
| Non-coord destination | Today it can only target the coordination branch; primary-surface generated writes (e.g. the VCS lock) have no owner |
| Subprocess byproduct enrolment | Bytes created by a child process (a gate's pytest run) are currently detected, warned about, and abandoned |
| Merge-executor adoption | Collapses the duplicate compensator in `merge/bookkeeping_projection.py` |

**Invariants**

- **TAO-1 — Exactly one owner.** Every path classified as a generated artifact, and every path
  a spec-kitty-spawned subprocess creates, is enrolled in exactly one transaction.
- **TAO-2 — Committed or reverted.** On completion the enrolled write is committed to its
  declared home; on failure it is restored to its pre-transaction bytes. No third state is
  observable (NFR-002).
- **TAO-3 — One compensator.** There is exactly one rollback implementation. Adding a third
  is a regression (Directive: canonical sources).
- **TAO-4 — Zero exemptions.** With TAO-1 satisfied, the correct number of filename-based gate
  exemption lists is zero (NFR-006).

---

## GeneratedArtifact

A file spec-kitty writes as part of running the workflow, as distinct from work authored by the
operator. This distinction is precisely what the registry of exemption mechanisms was approximating
by filename.

| Field | Type | Meaning |
|---|---|---|
| `path` | path | Location on some surface |
| `kind` | `MissionArtifactKind` \| null | Declared kind, when it has one |
| `home` | `ArtifactHome` | Where it authoritatively belongs |
| `origin` | `TOOL_WRITE` \| `SUBPROCESS_BYPRODUCT` | How it came to exist |

**Invariant GA-1** — Classification is by declared kind and origin, **not** by filename
matching. A retirement that replaces one filename list with another has not closed the class.

---

## ArtifactHome

The declared authoritative location for an artifact kind under a mission's stored topology.
Reads and writes both resolve to it — a fact is judged where it lives.

**Invariants**

- **AH-1 — Read/write symmetry.** `read_surface == write_surface` for every kind. (Established
  by #2874; this mission consumes and must not break it.)
- **AH-2 — Totality.** Resolution returns a home for every topology and every coordination
  state. Flat/`SINGLE_BRANCH`/`LANES` resolve affirmatively to the primary mission dir — their
  declared home, not a fallback. Among coord states only `DELETED` raises; `EMPTY` and
  `UNMATERIALIZED` resolve primary **with a stamp** (GEC-3/GEC-5). *Corrected 2026-07-23*: an
  earlier form made `None` mean "declared but unresolvable → raise", which contradicted
  `test_unmaterialized_coord_resolves_via_branch_ref` — a test NFR-004 forbids modifying.
- **AH-3 — Single copy.** An artifact has one authoritative home and no scaffolded second copy
  (FR-010 / #2882), so schema additions cannot diverge across copies.

---

## ArchivedMission

The record produced when an operator archives a completed or abandoned mission (FR-015 / US6). An
archive is an immutable, explicitly-legacy snapshot excluded from live validation but kept
enumerable, so retiring a mission never hides unresolved state.

| Field | Type | Meaning |
|---|---|---|
| `mission_id` | ULID | The archived mission |
| `archived_by` | str | Operator identity — archiving is operator-invoked only, never reachable from the FR-014 migration's failure path |
| `archived_at` | timestamp | When |
| `reason` | str | Why (e.g. the migration outcome that prompted it) |
| `terminal_state_at_archive` | `merged` \| `canceled` | The terminal state that made archiving permissible |

**Invariants**

- **AM-1 — Terminal only.** Archiving is refused unless the mission is already terminal
  (`merged` or `canceled`). A live mission cannot be archived.
- **AM-2 — No violation may be filed away.** Archiving is refused while any invariant is recorded
  `still_present`. A violation must be resolved, not archived past.
- **AM-3 — Visible, not deleted.** An archived mission is excluded from live validation but remains
  enumerable (e.g. via `doctor`), so the debt stays discoverable.
- **AM-4 — Never automatic.** No lifecycle step, including the FR-014 migration, may auto-archive.
- **AM-5 — Cancellation clears deferrals; abandonment is not a deadlock.** NI-5 blocks a mission
  from reaching a *terminal-by-completion* state (`done`) while any invariant is
  `deferred_to_consolidation`. But `canceled` is terminal-by-abandonment, and cancelling a mission
  **resolves** its outstanding deferrals to a `canceled` disposition (they were never going to be
  judged — the mission is being abandoned, not completed). So an abandoned mission with a dangling
  deferral is `canceled` (AM-1 satisfied) with no live deferral (NI-5 not engaged, since NI-5
  gates `done`, not `canceled`) and no `still_present` (AM-2 satisfied) — it is archivable. The
  deadlock the second independent review flagged (non-terminal per AM-1 ∧ terminal-blocked per
  NI-5) does not arise, because cancellation is the terminal transition that clears the deferral
  rather than waiting on it.

---

## Relationships

```
GateExecutionContext ──has──> TopologySurface, LifecyclePhase
          │
          │ is handed to
          ▼
        Gate ──judges──> NegativeInvariant ──records──> verified_ref + verified_surface_kind
          │                      │
          │                      └──defers to──> LifecyclePhase.POST_CONSOLIDATION
          │
          └──any write it makes──> GeneratedArtifact ──enrolled in──> ToolArtifactOwner
                                            │                              │
                                            └──belongs to──> ArtifactHome <┘
                                                              (commit target)
```

---

## What this model deletes

Retiring the registry of exemptions removes, rather than relocates, these concepts:

- filename/suffix sets used to decide whether a gate should ignore a path
- "residue" as a category distinct from "an artifact with a home"
- the second compensating-transaction implementation
- `None`-as-fallback in home resolution

If any of these survives implementation under a new name, the class has not been closed.
