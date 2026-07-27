# Write-Side Context-Factory Adoption (Mission B)

**Mission**: `write-side-context-factory-adoption-01KV9W0X`
**Type**: software-dev
**Target branch**: `feat/write-side-context-factory-adoption` (stacked on `feat/read-path-error-fidelity` / Mission A, PR #2015 — the frozen factory seam is there, not yet on upstream/main)
**Advances**: epic #1716 (coordination topology authority), epic #1878 (coordination placement/identity strangler), epic #1619 (runtime/state SSOT)

---

## Purpose

Mission A (`read-path-error-fidelity-adoption`) adopted the **read** path onto the existing single
context factory `build_execution_context`, **froze** the `ExecutionContext` composite, and **declared a
write-projection boundary contract** (D-6). This mission **finalizes the Lane-based branch-target context
object** — the object that decides *where each diff type lands* (planning/status → coordination, lanes →
coordination, code → lane, shared docs → base, **merge target → base**) — by adopting the **write** path
onto the factory's projected fragments, so read AND write both draw their root/identity/write-surface/
write-target from the **single** factory. The keystone invariant: when every target is the base branch, the
object collapses to the historical flat behavior (NFR-006 — "the simple case still works"). This is **ADOPTION,
not construction** (construction is already single-sited at `build_execution_context`; naming is already
consolidated in `branch_naming.py`). **C-001 holds: adopt the existing factory, build no new authority.**

## Background — the write-side asymmetry (the disease)

The write path runs a **second, parallel factory**
(`coordination/status_transition.py::_identity_for_request` + `CoordinationWorkspace` +
`lanes.branch_naming`) that re-derives identity / root / placement **by hand**, instead of consuming the
factory-projected fragments the read path already resolves once. Concretely (randy's write-path census,
`research/investigation-3-readwrite/randy-writepath-census.md`):

- **Root-resolution:** `feature_dir.parent.parent` walks at **≥5 write sites** (`status/emit.py:392`
  literally comments *"the topology seam exists to kill `feature_dir.parent.parent`"*).
- **Placement:** ad-hoc joins (e.g. the `core/worktree.py` placement composition).
- **Write-surface selection:** `coord_branch or current_branch` write-target selection + the coord/primary
  write-surface choice (`_identity_for_request`, `transaction.py` write-target joins) — the deepest grain
  (#1716 topology authority root, ~2094 LOC).

These re-derivations are exactly why the read-side context **fragments are unread today** (Mission A's
randy census: 5 of 6 fragments have 0 readers). Adopting the write path turns them **load-bearing**:
`workspace.primary_root` (the root-walk killer), `status_surface.status_write_dir` (the write half of the
surface fragment), and `branch_ref.destination_ref` (the write-target selector). **The real residual is
root-resolution + placement (+ a bounded slice of write-surface selection), NOT naming** — naming is
already the single composer.

## Boundary contract (declared by Mission A's IC-01, ENFORCED here)

> Write surfaces compose names/paths/identity from a factory-projected `IdentityFragment` +
> `BranchRefFragment` (+ `WorkspaceFragment` / `StatusSurfaceFragment`); they **MUST NOT re-derive**
> `mission_id` / `mid8` / `primary_root` independently.

Honored via the **primitive pattern** (read the real `mission_id` → `resolve_mid8(slug, mission_id=<real>)`);
the contract is a documented MUST-NOT-re-derive rule, **not** a new callable API. `build_execution_context`
stays the package-private single construction door; `branch_naming` stays a collaborator.

> **Mechanism note (D-12, binding for every FR/contract below).** Where this spec names a context **fragment
> field** (`workspace.primary_root`, `status_surface.status_write_dir`, `branch_ref.destination_ref`), it
> denotes **the value via that fragment's existing public resolver** — adoption calls the resolver, it does
> NOT thread an `ExecutionContext` or read the composite object: `primary_root` → `core.paths.resolve_canonical_root`
> / `get_main_repo_root`; `status_write_dir` → `coordination.surface_resolver.resolve_status_surface`;
> `destination_ref` / placement → `mission_runtime.resolution.resolve_placement_only`; lanes →
> `lanes.persistence.resolve_lanes_dir`. These resolvers already exist and are public (C-001 — no new
> authority; no adoption edit to `build_execution_context`/`resolution.py`). Read and write calling the **same**
> resolver IS the symmetry proof (SC-002).

---

## User Scenarios

### US-1 — write root from the factory, not a `.parent.parent` walk
**As** a runtime write operation (status emission, lifecycle event, lane store) that needs the mission's
primary root, **I want** it to consume `workspace.primary_root` from the factory-projected context **so
that** the `feature_dir.parent.parent` re-derivation (≥5 sites) is deleted and the root is resolved once,
consistently, across primary/coord/submodule topologies.

### US-2 — write-surface from the surface fragment
**As** the status-transition write path, **I want** the write directory to come from
`status_surface.status_write_dir` (the fragment's write half) **so that** the coord/primary write-surface
selection is no longer hand-rolled and stays consistent with the read surface.

### US-3 — write-target from the branch-ref fragment
**As** a write operation choosing where to commit (coord branch vs current), **I want**
`branch_ref.destination_ref` to be the single write-target selector **so that** the duplicated
`coord_branch or current_branch` derivation is retired.

### US-4 — placement from the factory seam
**As** worktree/placement creation, **I want** the placement path composed from the factory's
`CommitTarget`/placement projection **so that** the ad-hoc placement join is removed.

### US-5 — the unread fragments become load-bearing (verification-by-deletion)
**As** a maintainer, **I want** deleting the inline write-side re-derivations to keep the behavioral suite
green — the fragments going from 0 readers to load-bearing **is** the proof of adoption.

### US-6 — symmetry without churn
**As** an operator, **I want** the write-side adoption to be idempotency-preserving — it MUST NOT churn
on-disk worktree/coord state — and behavior-equivalent across input classes.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | **Root adoption (the bounded core).** The write-side `feature_dir.parent.parent` root-walk sites (`status/emit.py::_feature_status_lock_root`, `work_package_lifecycle.py`, `lifecycle_events.py`, `store.py`, and any peer confirmed in Phase 0) MUST consume the **correct factory fragment for their artifact family** (C-007) — `workspace.primary_root` for primary reads; the status/coord surface for status writes — instead of walking. Phase 0 classifies each site by artifact family before routing. Verification-by-deletion: removing the walks keeps the behavioral suite green. | Approved |
| FR-002 | **Placement adoption.** The `core/worktree.py` placement join (and any peer) MUST compose from the factory's placement projection (`CommitTarget`/`resolve_placement_only`), not an ad-hoc join. | Approved |
| FR-003 | **Write-surface adoption.** The status-transition write path MUST consume `status_surface.status_write_dir` for the write directory — which MUST resolve to the **status/coord** authority (C-007), preserving the read-primary/write-coord pattern (Robert's #2007 rule #1; "finalizer reads primary planning artifacts, writes status/task artifacts to the resolved placement/coord authority"); the hand-rolled coord/primary write-surface selection is retired (the fragment's write half becomes load-bearing). | Approved |
| FR-004 | **Write-target adoption (the branch-target object's core).** The write-target selection (`coord_branch or _current_branch`) MUST be sourced from `branch_ref.destination_ref` (single selector), not re-derived. randy's idempotency divergence (flattened arm `destination_ref`=`target_branch` CWD-invariant vs inline `_current_branch`=git HEAD) is the **latent bug the adoption fixes** — guarded by the simple-case test (NFR-006) + a before/after on-disk-target idempotency test (NFR-004). | Approved |
| FR-009 | **User-facing branch-target documentation (demystify lane behavior).** Add a user-documentation Explanation page (Divio "Explanation") presenting the **branch-target routing table** — "this is where everything goes": planning + status → coordination, lanes → coordination, code → lane, shared docs → base, merge target → base — plus the **simple case** (all → base ⇒ flat, no lanes/coordination, as it used to be). It must demystify the entire lane-based behaviour for users (operator requirement). Edit SOURCE docs (`docs/`), inventory it in the docs-freshness page-inventory. | Approved |
| FR-008 | **Lanes/coord adoption (the third artifact family).** The lanes-dir write (`lanes.json`, committed to the COORDINATION branch per C-LANES-1/#1991) MUST resolve from the context's coord surface — `resolve_lanes_dir(<coord feature dir from `status_surface`>)` (a thin lanes projection; prefer deriving from the existing `status_surface` + the `resolve_lanes_dir` seam over adding a raw factory field — minimal/no new authority, C-001). Completes #1993's deeper grain. | Approved |
| FR-005 | **Boundary-contract enforcement.** No write surface in the adopted scope re-derives `mission_id`/`mid8`/`primary_root` independently; identity flows via the primitive pattern (real `mission_id` → `resolve_mid8`). A guard/ratchet MAY extend the existing architectural test to flag write-side re-derivation in the adopted modules. | Approved |
| FR-006 | **Fragment retirement.** Retire the genuinely-dead `prompt_source` fragment and the dead `StatusSurfaceFragment.surface=` read-param wiring (`status/aggregate.py`) — superseded once the write half is adopted. | Approved |
| FR-007 | **Second-factory reduction.** The bounded write-side re-derivations in `coordination/status_transition.py::_identity_for_request` that the adopted fragments now cover MUST be reduced to consume the factory projection; the un-adopted remainder (the topology-authority root) is explicitly deferred (C-003). | Approved |

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | **Read/write symmetry (behavioral equivalence).** Adopted write operations resolve the same root/surface/target as the read path for the same logical mission across primary/coord/submodule input classes. | Parameterized tests over the three real topologies; zero divergence read-vs-write. |
| NFR-002 | **Topology-true fixtures.** Production-shaped data only: full 26-char ULID `mission_id`, REAL coord-worktree + submodule git topology — NO fabricated short ids/slugs, NO single-repo stand-in. | 100% topology-true; write-side bugs are surface-specific. |
| NFR-003 | **Function-over-form + verification-by-deletion.** Adoption proven by deleting the inline re-derivations with the behavioral suite green + the previously-unread fragments now exercised. | No new form-coupled test beyond the optional FR-005 ratchet. |
| NFR-004 | **Idempotency-preserving.** Write adoption MUST NOT churn on-disk worktree/coord state (no extra writes, no surface flips). | Before/after on-disk topology identical; status events unchanged in shape. |
| NFR-005 | **Quality gates.** `ruff` + `mypy` clean, complexity ≤ 15, no suppressions. | CI-enforced; no `# noqa`/`# type: ignore` additions. |
| NFR-006 | **The simple case still works (BINDING — operator requirement, the keystone guard).** When every diff-type target resolves to the **base** branch (planning/status→base, lanes→base, code→base, docs→base, merge-target→base — i.e. no coordination branch declared, no lane worktree), spec-kitty MUST run exactly as it did before lanes/coordination existed: every adopted fragment resolves to the base, and **zero** coord/lane paths are touched. This is the flattened-topology collapse — the all-base case proves the branch-target context object degrades cleanly to the historical flat behavior. | A dedicated "all-targets-base → flat" test on a real single-branch repo (full ULID, no coord, no lanes): every fragment == base; no `.worktrees/`/coord surface read or written; behavior byte-identical to the pre-lane flat path. |

## Constraints

| ID | Constraint |
|----|-----------|
| C-001 | **No new authority.** Adopt the EXISTING `build_execution_context` factory + its projected fragments. No new factory, no new resolver, no new public symbol. `branch_naming` stays a collaborator (not absorbed). |
| C-002 | **Stacked on Mission A.** This mission depends on Mission A's frozen factory + boundary contract (`feat/read-path-error-fidelity` / PR #2015). It MUST stack on that branch; the seam is not yet on upstream/main. |
| C-003 | **Scope cut decided in plan (like Mission A's C-005).** Phase 0 + plan decide whether Mission B takes ONLY the bounded root/placement/surface/target adoption (the safe first cut, ~90–130 LOC, proves symmetry end-to-end) OR also a bounded slice of the write-surface-SELECTION authority. The full #1716 topology authority root (~2094 LOC) + #1878 finalize/merge ff-advance bookkeeping default to a later focus. |
| C-004 | **No patch-version prescription.** Versioning is a PO/release call. |
| C-005 | **Edit canonical sources only.** `src/` runtime; doctrine/prose edits touch SOURCE templates in `src/doctrine/`, never generated agent copies. |
| C-006 | **Live-evidence + TDD-first.** Behavioral changes land test-first with topology-true repro; no claim closed on static reading. |
| C-008 | **Fix, don't litigate (campsite-cleaning is the DEFAULT — #1970 / DIRECTIVE_025, BINDING).** When a Mission B change touches code that already has a failing test, a lint/type issue, or a clear smell, the default is to **fix it outright** — do NOT spend effort litigating pre-existing-vs-introduced (proving innocence costs more than fixing) and do NOT leave adjacent breakage in place under "minimal diff." Leave the campground cleaner. This mission operationalizes it two ways: (1) the **clean-before-touch pre-refactors** (the byte-identical lock-root de-dup, the FR-006 dead-code, the characterization net) land FIRST so the adoption is mechanical; (2) any adjacent breakage an implementer hits is fixed in the same change, not deferred-with-blame. (Carries forward to the running guard/smell trace + #2017.) |
| C-007 | **The branch-target context object: per-diff-type routing (Robert's #2007 rule #1, BINDING).** The context object decides where each diff type lands — **planning + status → coordination**, **lanes → coordination**, **code → lane**, **shared docs → base**, **merge target → base**. Each write site routes to the **correct** factory fragment for its diff type (status→`status_surface` coord authority, lanes→the lanes projection coord authority, root/docs reads→`workspace.primary_root`/base, merge-target→`branch_ref.destination_ref`) — and MUST NOT collapse a coord write to `primary_root` (a flatten/new shadow path #2004/#2007 forbid). **The simple-case collapse is the invariant (NFR-006):** when all targets resolve to base, the object degrades to the historical flat behavior (no coord/lane). Phase 0 classifies every adopted write site by diff type; the read-primary/write-coord pattern is preserved, the simple case stays flat. |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | The `feature_dir.parent.parent` write-side root-walks in the adopted scope are **deleted**; root comes from `workspace.primary_root`; the behavioral suite is green (FR-001/NFR-003). |
| SC-002 | Read and write resolve their root/surface/target via the **same existing public pure resolver** (`resolve_canonical_root`/`get_main_repo_root`, `resolve_status_surface`, `resolve_placement_only`, `resolve_lanes_dir` — D-12), not via parallel hand-rolled re-derivations. The proof of symmetry is the **shared single sourced path** (the resolver becomes the one route read and write both call), demonstrated by deleting the inline write-side re-derivation with the suite green — NOT by threading the composite fragment object. |
| SC-003 | Read and write resolve the **same** root/surface/target for the same mission across primary/coord/submodule (NFR-001). |
| SC-004 | `prompt_source` + the dead `surface=` read-param are retired with no behavioral change (FR-006). |
| SC-005 | On-disk worktree/coord topology is **identical** before/after an adopted write operation (NFR-004, idempotency). |
| SC-006 | `ruff`/`mypy` clean, complexity ≤ 15, no suppressions (NFR-005). |
| SC-007 | **Simple case:** with all diff-type targets set to the base branch, spec-kitty resolves every fragment to base and runs flat (no coord/lane paths touched), byte-identical to the historical pre-lane behavior (NFR-006). |
| SC-008 | The write/merge-**target** comes from `branch_ref.destination_ref`; the inline `coord_branch or _current_branch` derivation is deleted; the all-base case yields `target_branch` (flat) and the coord case yields the coord branch — proven by the idempotency before/after test (FR-004). |
| SC-009 | A user-doc Explanation page presents the branch-target routing table + the simple case, demystifying lane behaviour; it is inventoried (docs-freshness green) (FR-009). |

---

## Key Entities

- **`build_execution_context`** — the single package-private factory (Mission A). Produces the frozen
  `ExecutionContext` composite with its fragments. Unchanged here (C-001).
- **`WorkspaceFragment.primary_root`** — the root-walk killer; the write-side root source (FR-001).
- **`StatusSurfaceFragment.status_write_dir`** — the write half of the surface fragment (FR-003);
  `surface=` read-param retired (FR-006).
- **`BranchRefFragment.destination_ref`** — the single write-target selector (FR-004).
- **The second parallel factory** — `coordination/status_transition.py::_identity_for_request` +
  `CoordinationWorkspace`; the bounded covered portion is reduced (FR-007), the topology-authority
  remainder deferred (C-003).

---

## Tracker / Issue Matrix

| Issue | Title | Relation | Disposition |
|-------|-------|----------|-------------|
| #1716 | coordination topology authority (write-side) | the keystone this mission advances — the bounded root/placement/surface adoption is the first cut; the topology-authority root is the deferred remainder (C-003) | in-mission (bounded slice) |
| #1878 | complete the coordination placement/identity strangler (post-3.2.0) | finalize/merge ff-advance bookkeeping = later focus | deferred-with-followup |
| #1619 | unify execution context / runtime-state SSOT (epic) | the fragment adoption makes the unread fragments load-bearing — a concrete #1619 increment | in-mission (increment) |
| #2016 | orchestrator coord-read identity bootstrap (coord-only, no primary meta) | read-path; **already fixed by Mission A WP09** (`d4f0cf581`) — cross-ref, verify-don't-redo | verified-already-fixed |
| #1993 | extract `resolve_lanes_dir()` pure seam + lanes/coord adoption | the pure seam is **already done by Mission A** (`persistence.py:23`); the **lanes/coord fragment adoption** (FR-008) is the deeper grain folded into Mission B (operator decision 2026-06-17) | in-mission (FR-008) |
| #2000 | route remaining `<slug>-<mid8>` composes through the canonical seam | **already routed** by the naming-rider #2012 (`worktree.py`/`mission_creation.py` use `mission_dir_name`/`resolve_mid8`; ratchet flags zero offenders) | verified-already-fixed (close on #2015 merge) |

**#2007 alignment (revisited 2026-06-17 — confirmed on-direction):** Robert's #2007 architecture-alignment
rules sequence exactly this trajectory — rule #2: *"C3 is the center of mass — start there, then fix the
single-resolution adoption gaps behind #1832/#1716."* Mission A delivered C3 (#2010) + C6 (#2011) + #1832;
**Mission B is the #1716/#1878 step Robert names.** His #2004 CI-hardening note pre-validates the write-side
direction (*"merge/finalize/status code must consume the shared mission path authority instead of rebuilding
primary/coord paths inline"*). Rule #1 (*"do not build a new monolithic resolver; preserve the three
artifact families; no new shadow paths"*) is captured as **C-007** (binding). **Tracker hygiene:** the
#2007 children Mission A fixed (#2010 read-path / #2011 submodule / #1832 single-resolution) are still OPEN
on the tracker and should be closed when PR #2015 merges — not by this mission.

Tickets the mission works on are claimed (claim-before-working) via planner-priti, with a tracker comment
naming this mission. A Phase-0 planner-priti related-issues sweep enumerates net-new write-side/topology
tickets and folds them here before tasks.

## Assumptions

- Mission A's factory + boundary contract are sound and on `feat/read-path-error-fidelity`; this mission
  consumes them unchanged.
- The bounded write-side root/placement/surface/target sites are genuinely routable without the full
  topology-authority rewrite (randy's census; confirmed in Phase 0 with an exact site inventory).
- Real coord-worktree + submodule fixtures are constructible (these write-side behaviors are
  topology-specific; fabricated fixtures mask them — the trap prior missions hit).

## Out of Scope

- The full #1716 write-surface-selection topology authority root (~2094 LOC) — only a bounded slice may be
  pulled in, decided in plan (C-003).
- #1878 finalize/merge ff-advance bookkeeping (later focus).
- Any change to `build_execution_context`/`branch_naming` beyond consuming the projection (C-001).
- Patch-version assignment (C-004).
