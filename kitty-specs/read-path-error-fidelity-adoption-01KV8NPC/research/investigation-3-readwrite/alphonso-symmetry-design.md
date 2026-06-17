# Read/Write Symmetry — Single-Factory Context Design

**Author:** architect-alphonso (profile-loaded; DIR-001 one-owning-module, DIR-003
decision-documented, DIR-031 bounded-context translation, DIR-032 conceptual alignment)
**Date:** 2026-06-16
**Mission:** `read-path-error-fidelity-adoption-01KV8NPC`
**HEAD:** `bb3d74399` (editable 3.2.1)
**Operator design question (verbatim):** *"Assuming we route the READ path through the new SSOT
(the context-object API), how do we ensure the WRITE path follows the same logic? … context objects
being built from a SINGLE SOURCE/FACTORY that encapsulates the logic (naming, etc.)."*

---

## Executive Summary

**Does write-symmetry require write-side scope NOW? NO. A read-side factory seam suffices — and the
write side has *already partially adopted it* through a different door.**

The single factory the operator wants **already exists in two halves that share one grammar
module**: `resolve_action_context` (the read factory) and the write side both compose names/topology
from the *same* `lanes/branch_naming.py` seam (`resolve_mid8`, `mission_dir_name`,
`worktree_dir_name`, `coord_*`, `resolve_transaction_mid8`) that the just-merged naming-rider
consolidated. The asymmetry is **not** "two grammars" — the naming-rider already collapsed grammar to
one module. The asymmetry is **at what altitude each path consumes it**:

- **Read path** consumes naming *through fragment assembly* — `_assemble_core_fragments` resolves
  `mission_id`/`mid8`/`coordination_branch`/`target_branch` *once* and hands callees a value object.
- **Write path** consumes the naming *primitives directly* — mission-create, the lane allocator
  (`workspace/context.py`), merge, and the coordination transaction each independently re-read
  `meta.json` for `mission_id`/`mid8` and call `mission_dir_name(...)` / `lane_branch_name(...)` /
  `resolve_transaction_mid8(...)` at their own call sites.

So write-symmetry is **"raise the write side to consume the factory's fragments instead of calling
the grammar primitives with locally re-derived identity"** — that is the #1716/#1878 follow-on, and
it is genuinely deferrable (D-1 holds). It does **not** require write-side scope in THIS mission, for
two reasons grounded in the just-completed investigation-2:

1. **The fragments the write side needs already exist and are CWD-invariant** (`IdentityFragment`,
   `BranchRefFragment`, `WorkspaceFragment`, `ArtifactPlacementFragment`). Randy's census found them
   *assembled-but-unread* — they are unread **precisely because the write path never adopted them.**
   The seam is built; it is the consumer that is missing. A write-side follow-on can adopt without a
   factory rewrite.
2. **The naming-rider already centralized the grammar** (#2012). The factory does not need to *own*
   mid8/dir-name composition — it needs to *encapsulate the identity resolution that feeds it* so no
   consumer (read or write) re-derives `mission_id` from meta independently.

**The ONE concrete change to this mission's plan:** re-scope IC-01 from "freeze + assert" to
**"freeze + assert + declare the factory boundary"** — i.e. add a single explicit, importable WP-less
identity/topology projection (`resolve_identity_only` / formalize the existing `resolve_placement_only`
as the *named* write-adoption seam) and a one-line `__all__`/docstring contract stating "write
surfaces compose names from a factory-projected `IdentityFragment` + `BranchRefFragment`, never from a
locally re-derived `mission_id`." This is ~15–25 LOC of surface declaration, **零 write-call-site
edits**, stays inside `mission_runtime/{context,resolution}.py` (NFR-005 honored), and guarantees the
#1716/#1878 follow-on adopts the factory **without a later rewrite** of either the factory or the
naming module. **D-1 stays. C-001 honored (no new authority — formalize the existing one).**

---

## 1. The single factory/source — does one exist, or are read & write built differently?

**One factory exists for the READ path; the WRITE path is built by direct primitive calls that share
the SAME grammar module but re-derive identity independently.** Concretely:

### 1a. The read factory (present, load-bearing)

`resolve_action_context` (`mission_runtime/resolution.py:689`) is the read factory. Its private
collaborator `_assemble_core_fragments` (`:489`) is the *true* single source: it resolves, **exactly
once**,
- `primary_root` via the canonical root authority (`get_main_repo_root` → `resolve_canonical_root`),
- `mission_id` via `_resolve_mission_id` (primary-anchored meta read, `:380`),
- `mid8` via `IdentityFragment.derive` (`mission_id[:8]`, the single derivation point, `:526`),
- `coordination_branch` via `_resolve_coordination_branch` (primary-anchored, `:340`),
- `target_branch` (passed in, resolved once at `:721`),
- the `CommitTarget destination_ref` with topology `kind` (`:531-547`).

It returns these as **frozen fragments** attached to the `ExecutionContext`. `resolve_placement_only`
(`:606`) is a *narrower projection over the same builder* (WP-less, for the planning phase). This is
the factory.

### 1b. The naming seam — already ONE module (the rider's contribution)

`lanes/branch_naming.py` is the single grammar module. The naming-rider (#2012) made it the sole
public mid8 door: `resolve_mid8` ("name proposes, authority disposes"), `mission_dir_name`,
`worktree_dir_name`, `coord_branch_name`/`coord_reconstruct_branch`/`coord_mission_dir_name`,
`resolve_transaction_mid8`, and the fail-closed `BranchIdentityUnresolved`. **There is no second
grammar.** The factory's `_assemble_core_fragments` and the write call-sites both bottom out here.

### 1c. The asymmetry (the operator's actual concern)

The write side calls the **grammar primitives directly with locally-resolved identity**:

| Write surface | file:line | Calls | Re-derives identity how |
|---|---|---|---|
| mission create | `core/mission_creation.py:323`, `core/worktree.py:370` | `mission_dir_name(...)` | local (creation-time, authoritative) |
| lane allocator | `workspace/context.py:314,820,833,882` | `worktree_dir_name(...)`, `lane_branch_name(...)` | local read |
| merge bookkeeping | `merge.py:2412,2884`, `merge/preflight.py:97` | `lane_branch_name(...)`, `mission_branch_name_required(...)` | local read |
| coord transaction | `coordination/status_transition.py:279`, `implement.py:407` | `resolve_transaction_mid8(...)` | local meta read at call site |
| status dest-ref | `status/aggregate.py:697` | `mission_branch_name_required(...)` | local |
| coord workspace read | `coordination/workspace.py:111,167,179` | `coord_*` reconstruct | local mid8 |

Each of these resolves `mission_id`/`mid8`/`coordination_branch` for itself, then composes a name.
That is **N independent identity resolutions feeding one grammar** — vs. the read path's **one
identity resolution (the factory) feeding the same grammar**. That is the symmetry the operator wants
closed: not "one grammar" (already true) but "one *identity/topology resolution* feeding both read and
write composition."

> **Definition — "one factory encapsulating naming":** the factory does NOT absorb `branch_naming.py`.
> `branch_naming` stays a **collaborator** the factory calls. What the factory encapsulates is the
> **identity+topology resolution** (`mission_id` → `mid8`, `coordination_branch`, `target_branch`,
> topology `kind`) that *both* read and write composition consume. The factory projects an
> `IdentityFragment` + `BranchRefFragment`; read AND write compose names *from those fragments* rather
> than each re-reading meta and calling `resolve_mid8` for itself. The grammar is shared today; the
> *resolved identity that drives the grammar* is what must become single-sourced.

---

## 2. Target architecture (one factory → context objects → consumed by read AND write)

```
                          meta.json (PRIMARY checkout, authoritative)
                                        │  (read ONCE)
                                        ▼
        ┌───────────────────────────────────────────────────────────────┐
        │   mission_runtime  —  THE SINGLE FACTORY (identity+topology)    │
        │                                                                 │
        │   _assemble_core_fragments(repo_root, mission_slug, …)          │
        │     • primary_root  ← resolve_canonical_root  (one root auth)   │
        │     • mission_id    ← _resolve_mission_id     (one meta read)   │
        │     • mid8          ← IdentityFragment.derive (mission_id[:8])  │
        │     • coordination_branch ← _resolve_coordination_branch        │
        │     • target_branch (resolved once)                            │
        │     • CommitTarget(ref, kind)  ← topology classification        │
        │            │  calls (collaborator, NOT absorbed)                │
        │            ▼                                                     │
        │   lanes/branch_naming.py  (the ONE grammar module, #2012)       │
        │     mission_dir_name / worktree_dir_name / lane_branch_name /   │
        │     coord_* / resolve_transaction_mid8 / resolve_mid8           │
        └───────────────────────────────────────────────────────────────┘
                 │                                          │
   projects ─────┤                                          ├───── projects
                 ▼                                          ▼
   ExecutionContext (full)                   resolve_placement_only / resolve_identity_only
   identity, branch_ref, workspace,          (WP-less projections over the SAME builder)
   status_surface, artifact_placement                     │
                 │                                          │
     ┌───────────┴───────────┐                ┌─────────────┴──────────────┐
     ▼  READ consumers        ▼                ▼  WRITE consumers (#1716/#1878 adopt)
   next / agent context     decision        mission-create │ lane-allocator │ merge
   resolve / setup-plan     verify          coord-transaction │ status dest-ref
   (consume fragments)                       (TODAY: re-derive id + call grammar;
                                              FUTURE: consume branch_ref/identity fragment)
```

The factory is **one builder with two projection widths**: full (`resolve_action_context`, for a
resolved WP context) and WP-less (`resolve_placement_only` today, `resolve_identity_only` proposed —
for write surfaces that exist *before* a WP, e.g. mission-create / allocation). Both widths run the
*same* `_assemble_core_fragments`, so the topology classification (PRIMARY/COORDINATION/FLATTENED) and
the mid8 are **byte-identical** across read and write — which is exactly the split-brain class
`_resolve_coordination_branch`'s docstring (`:347-360`) describes (setup-plan resolving COORDINATION
while finalize-tasks resolved FLATTENED). Symmetry kills that class structurally.

---

## 3. Write-op → context-field mapping table

Each write operation, the names/paths/identity it needs, the factory fragment that already carries
the same value, and how it draws it today vs. under symmetry.

| Write op | Needs | Factory fragment/field (SSOT) | Today (re-derives) | Under symmetry (#1716/#1878) | Issue |
|---|---|---|---|---|---|
| **mission create** | canonical `<slug>-<mid8>` dir + coord branch | `IdentityFragment.mid8`, `BranchRefFragment.coordination_branch` | local `mission_dir_name` at creation (authoritative — this is the *mint* site) | **STAYS local** — mission-create *is* the identity origin; it seeds meta the factory later reads. No adoption needed. | #1899 |
| **lane/worktree allocation** | `worktree_dir_name`, `lane_branch_name` per lane | `WorkspaceFragment` (lane paths) + `IdentityFragment.mid8` | `workspace/context.py:314,833` re-reads, composes | consume `IdentityFragment.mid8` from a factory projection; compose via grammar with the *factory-resolved* mid8 | #1716 |
| **coord-branch creation** | `coord_branch_name` / coord worktree path | `BranchRefFragment.coordination_branch`, `WorkspaceFragment.coord_worktree` | `coordination/workspace.py` reconstructs from local mid8 | consume `branch_ref.coordination_branch` + `workspace.coord_worktree` | #1878 |
| **status writes** | status write dir + dest-ref | `StatusSurfaceFragment.status_write_dir`, `BranchRefFragment.destination_ref` | `status/aggregate.py:697` composes dest-ref locally; transaction re-derives mid8 (`resolve_transaction_mid8`) | consume `status_surface.status_write_dir` + `branch_ref.destination_ref` (the SAME `CommitTarget` reads use) | #1878 |
| **finalize (tasks→lanes)** | lanes-dir, target branch, placement | `feature_dir`, `BranchRefFragment.target_branch`, `ArtifactPlacementFragment.placement_ref` | already partially routed (`resolve_placement_only`); IC-05 extracts `resolve_lanes_dir` | finalize consumes the placement projection (already does) | #1993 |
| **merge bookkeeping** | lane branches, mission branch, primary status paths | `BranchRefFragment` (target/lane via grammar), `WorkspaceFragment.primary_root` | `merge.py` composes lane branches locally; #1956/#1972 re-anchor to `primary_feature_dir_for_mission` | consume `branch_ref` + `workspace.primary_root`; the #1956/#1972 fix is *already the adoption pattern* (Debbie §2) | #1716 |

**Reading of the table:** every write field has a factory fragment that **already holds the
identical value resolved by the single builder**. mission-create is the lone "stays local" row because
it is the identity *origin* (it writes the meta the factory reads). Everything else is a *consumer*
that can be flipped to read `branch_ref`/`identity`/`workspace`/`status_surface` from a factory
projection — which is **adoption, not construction**. That is `#1716` (allocation/merge topology
authority) + `#1878` (coordination strangler), and it is exactly the deferred write-side.

---

## 4. Scope impact on THIS mission

### What THIS mission builds — the factory *seam*, not the write adoption

The mission already hardens the factory's spine (IC-01 freeze + `target_branch ==
branch_ref.target_branch` assert). The **single addition** that guarantees future write-symmetry
without scope explosion:

**Re-scope IC-01: "freeze + assert" → "freeze + assert + declare the factory boundary".** Add to
`mission_runtime`:

1. A **named, importable WP-less projection for write-side identity/topology** — either formalize the
   existing `resolve_placement_only` as the *declared* write-adoption door, or add a sibling
   `resolve_identity_only(repo_root, mission_slug) -> (IdentityFragment, BranchRefFragment)` that runs
   `_assemble_core_fragments` and projects the two fragments write surfaces need. ~15–25 LOC, **inside
   `resolution.py`** (NFR-005: no new owned files; `mission_runtime/{context,resolution}.py` are
   already IC-01's surface).
2. A **one-paragraph contract** in `context.py`'s module docstring + `__all__` stating the boundary:
   *"Write surfaces compose mission/lane/coord names by consuming a factory-projected
   `IdentityFragment` + `BranchRefFragment`; they MUST NOT re-derive `mission_id`/`mid8` from meta or
   call `resolve_mid8` independently. `lanes/branch_naming` is the grammar collaborator; the factory is
   the identity authority that feeds it."*

This is the minimal seam that (a) makes the factory's write-side projection a **declared public
surface** (so the #1716/#1878 follow-on imports it rather than inventing a new entry), and (b) records
the architectural contract so the follow-on is *adoption against a frozen seam*, not a redesign.

### Why IC-01 should be re-scoped (not a new IC)

The operator's intent reframes IC-01's purpose: it is not merely "make the read context trustworthy"
— it is **"establish the single context factory both paths consume."** Freezing without declaring the
write-projection boundary leaves the factory looking read-only (the trap Randy fell into:
fragments-assembled-but-unread reads as *dead* rather than *awaiting-the-write-consumer*). Declaring
the boundary in the same WP that freezes the spine costs ~one paragraph + one projection function and
**prevents a later rewrite** by fixing the import surface now. A *new* IC would imply new owned files
and risk pulling write-call-site edits in — exactly the C-001/NFR-005 line we must not cross.

### Why the write-side does NOT come in now (D-1 stays)

- **Behavioral equivalence is the mission's contract (NFR-001).** Flipping allocation/merge/transaction
  to consume fragments is a *write-path behavior change* with on-disk worktree/coord implications —
  the precise churn NFR-005 forbids ("no on-disk worktree/coord churn, idempotency-preserving").
- **~2094 LOC write-side topology (D-1 estimate)** is the #1716 grain; pulling it violates C-001
  ("adopt the EXISTING SSOT; introducing a new … root authority … is out of scope").
- **The fragments are already built** (Randy's census). The follow-on is consumption, not
  construction — there is **no later rewrite** induced by deferring, *provided* the projection seam +
  contract land now. That proviso is the IC-01 re-scope above.
- **Robert's #2007 rule 1 is binding:** "Do not build a new monolithic resolver. Finish/adopt the
  existing typed context/read-path surfaces." The write-side projection is *finishing the existing
  surface's declaration*, not building a resolver.

### D-1 verdict

**D-1 STAYS (DEFER #1716 write-side topology).** The symmetry goal is satisfied by laying the
factory's write-projection seam + boundary contract in IC-01; the actual write-call-site adoption is
the #1716/#1878 follow-on, which can proceed against a frozen, declared seam with no rework.

---

## 5. Naming-encapsulation decision

**The factory encapsulates IDENTITY+TOPOLOGY resolution; `lanes/branch_naming` stays the grammar
collaborator.** Concretely:

- **Do NOT absorb `branch_naming.py` into `mission_runtime`.** It is the #2012-consolidated single
  grammar module with a tested dual-era contract (legacy `NNN-` vs. mid8-era), a fail-closed
  `BranchIdentityUnresolved`, and a verbatim-vs-canonical split (`coord_reconstruct_branch` vs.
  `mission_dir_name`) that exists for on-disk reconstruction fidelity (#1589). Absorbing it would
  re-open #2012's bounded context (DIR-031 violation) and is explicitly out of scope (plan line 92:
  "`branch_naming.py` is OUT (prior mission #2012)").
- **The factory OWNS the single `mission_id`/`mid8`/`coordination_branch`/`target_branch` resolution**
  (`_assemble_core_fragments`). Neither read nor write should re-derive these. The factory calls the
  grammar with the *resolved* identity; consumers receive the *composed* names on fragments.
- **This closes the naming-rider's two named residuals** the operator flagged:
  1. **Remaining inline `resolve_mid8` / `resolve_transaction_mid8` sites** (`implement.py:407`,
     `status_transition.py:279`, orchestrator `commands.py:261` — Debbie's M3, the *live-confirmed*
     `resolve_mid8(..., mission_id=None)→''` stale-read bug). Under symmetry these consume
     `IdentityFragment.mid8` from the factory (resolved from the authoritative primary-meta
     `mission_id`), so the empty-mid8 fail-closed-suppression class (M3) cannot recur. **NOTE: this is
     the write-side follow-on's payoff — it is *enabled* by the IC-01 seam but *adopted* in #1716/#1878.**
     M3 itself is already separately tracked by this mission's missed-surface census as a NEW WP
     candidate; the symmetry seam is what lets that WP consume the factory rather than re-fix
     `resolve_mid8` locally.
  2. **The deferred `feature_dir.parent.parent` root-derivation class.** Root authority is already
     single-sourced *inside the factory* (`WorkspaceFragment.primary_root` via `resolve_canonical_root`,
     `:456`). IC-06 (in THIS mission) unifies `resolve_canonical_root` with `locate_project_root` at the
     submodule boundary. Once write surfaces consume `WorkspaceFragment.primary_root` (follow-on), the
     `.parent.parent` root walks (Randy: 55 occurrences) lose their reason to exist — they become
     `workspace.primary_root` reads. **THIS mission fixes the root *authority* (IC-06); the follow-on
     retires the *walks* by consuming the fragment.** Deferring the walk-retirement is correct (it is
     the broader #1619 grain, plan line 185).

**Decision:** factory = identity/topology authority (single meta read, single mid8 derivation, single
root resolution); `branch_naming` = grammar collaborator (composition only, fed the resolved
identity). Both read and write compose names by handing the factory-resolved identity to the grammar —
never by re-resolving identity at the call site. THIS mission declares that boundary (IC-01 re-scope);
the follow-on enforces it at the write call sites (#1716/#1878).

---

## Appendix — alignment with prior investigation findings

- **vs. Alphonso investigation-2 (KEEP-AND-ADOPT):** consistent. Inv-2 settled *that* the read SSOT is
  intended and load-bearing; this design answers *how write follows*. The "mid-Strangler not vestigial"
  finding is the same: the fragments are unread because the *write consumer* is the unfinished Strangler
  step, not because the model is aspirational.
- **vs. Randy (ADOPT-NARROW + RETIRE-WIDE):** **partial divergence, reconciled by the operator's
  intent.** Randy reads the 5 unread fragments as *vestigial* and proposes retiring them. The operator's
  read/write-symmetry intent reframes them as **the write-side adoption surface** — `IdentityFragment`,
  `BranchRefFragment`, `WorkspaceFragment` are exactly what the write follow-on consumes (table §3).
  **Reconciliation:** Randy is right that they are unread *today* and right to flag `StatusSurfaceFragment`'s
  dead `surface=` parameter; he is measuring against the *current* (read-only-adopted) tree. The
  decisive question is the operator's: *is the write-side adoption intended?* If yes (it is — verbatim
  intent), the fragments are pre-built seam, and retiring them would force the #1716/#1878 follow-on to
  rebuild them — the "later rewrite" we are explicitly avoiding. **Recommendation: do NOT retire the
  fragment model; retire only the genuinely-dead `StatusSurfaceFragment.surface=` parameter wiring Randy
  found (aggregate.py:262/309), which is a real dead branch independent of write adoption.** Keep
  `identity`/`branch_ref`/`workspace`/`artifact_placement` as the declared write-adoption surface.
- **vs. Debbie (re-verify + missed surfaces):** M3 (orchestrator `resolve_mid8(...,None)→''` stale
  read) is the canonical live witness that **independent write-side identity re-derivation is
  actively buggy** — the strongest empirical case for routing write-side mid8 through the factory's
  `IdentityFragment`. It corroborates §5.1.
