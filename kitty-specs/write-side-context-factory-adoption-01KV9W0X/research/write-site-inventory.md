# Write-Site Inventory — Mission B (write-side context-factory adoption)

**Author:** architect-alphonso (profile-loaded; DIR-001 one-owning-module, DIR-003
decision-documented, DIR-031 bounded-context translation, DIR-032 conceptual alignment)
**Date:** 2026-06-17
**Mission:** `write-side-context-factory-adoption-01KV9W0X`
**Branch:** `feat/write-side-context-factory-adoption` (stacked on `feat/read-path-error-fidelity` /
Mission A — the frozen factory seam is merged here)
**HEAD:** `efb28158f` (Mission A's WP01–WP09 present; line numbers re-pinned against this HEAD)
**Inputs:** spec FR-001..007 / C-007; randy-writepath-census.md; alphonso-symmetry-design.md;
00-SYNTHESIS.md

---

## 0. Q3 VERDICT (the pivotal question, lead) — VERIFIED ON HEAD

**Do the write-half fragment fields EXIST and RESOLVE CORRECTLY on HEAD? YES for all three — Mission B
is PURE CONSUMER-ROUTING, not consumer-routing + factory-fragment-completion.** Verified by reading
the merged factory (`src/mission_runtime/{context.py,resolution.py}`):

1. **`WorkspaceFragment.primary_root` — EXISTS + RESOLVES to the primary root.**
   `context.py:144` declares `primary_root: Path`; `resolution.py:698`
   `primary_root = get_main_repo_root(repo_root)` resolves it via the single canonical
   worktree-pointer parser (`resolve_canonical_root`, IC-04), CWD-invariant by construction
   (`_assemble_workspace_fragment`, `resolution.py:619-661`). This is the `.parent.parent` killer,
   correct and load-bearing-ready. **No completion needed.**

2. **`StatusSurfaceFragment.status_write_dir` — EXISTS + RESOLVES to the COORD/status authority
   (C-007-correct).** `context.py:162` declares `status_write_dir: Path`; `resolution.py:724-728`
   sets BOTH `status_read_dir` and `status_write_dir` to `_resolve_status_surface_dir(primary_root,
   mission_slug)`. **The critical correctness check passes:** that helper (`resolution.py:586-616`)
   delegates to `coordination.surface_resolver.resolve_status_surface`, which IS the coord-aware
   authority — it returns the coord-worktree feature dir when the coord topology is materialized, and
   **fails closed (`StatusReadPathNotFound` → `ActionContextError`) rather than degrading to the
   primary surface** (`surface_resolver.py:433-475`, the #1589/#1821 split-brain guard). So
   `status_write_dir` resolves to the **status/coord authority, NOT to `primary_root`** — exactly the
   C-007 read-primary/write-coord pattern (#2007 rule #1). **No completion needed.** Nuance: under
   flattened topology `status_read_dir == status_write_dir` (single branch, by design, C-001); under
   coord topology both already point at the coord surface. The two fields are intentionally equal
   *values* today because the surface resolver is the single coord-aware authority for both directions
   — this is NOT a stub; it is the correct collapse. Mission A's "built-but-unused" flag was about
   **0 consumers**, not about a wrong/missing value. The write half is **correct and unread**, which
   is precisely the adoption gap Mission B closes.

3. **`BranchRefFragment.destination_ref` — EXISTS as the write-target selector + RESOLVES.**
   `context.py:130` declares `destination_ref: CommitTarget`; `resolution.py:705-722` sets it to a
   `CommitTarget(ref=coordination_branch, kind=COORDINATION)` when a coord branch is declared, else
   `CommitTarget(ref=target_branch, kind=FLATTENED)`. This is the single typed write-target selector
   that the inline `coord_branch or _current_branch(repo_root)` derivation
   (`status_transition.py:291`) duplicates. **No completion needed** — though note a SEMANTIC GAP in
   the fallback arm (§4): the factory's flattened arm carries `target_branch`, whereas the inline write
   site carries `_current_branch(repo_root)`. These coincide under normal flattened topology but the
   plan must assert behavioral equivalence (NFR-001) before flipping the consumer.

**Conclusion:** the factory needs **NO bounded fragment-completion**. All three write-half fields are
present and resolve to the *correct* authority on HEAD. Mission B is **pure consumer-routing**: flip
the hand-rolled write sites to read `workspace.primary_root` / `status_surface.status_write_dir` /
`branch_ref.destination_ref` from a factory projection. The `mission_runtime/` files are therefore
**NOT owned** by any Mission B WP (C-001 honored — consume, do not modify the seam). The one residual
factory touch is the FR-006 *retirement* of dead scaffolding (`prompt_source` + the dead `surface=`
read-param), which is deletion, not authority-building.

---

## 1. Write-Site Inventory — classified by artifact family (C-007 BINDING)

Line numbers re-pinned against HEAD `efb28158f` (drift from randy's pre-merge census corrected in the
last column). "Family" per C-007: **meta/primary** (a READ → `workspace.primary_root`),
**status/coord** (a status WRITE → must resolve to the COORD authority), **lanes/coord** (lanes →
lanes-dir). A status/lanes WRITE site **MUST NOT** route to `primary_root`.

| # | Write site | file:line (HEAD) | Re-derives | Artifact family (C-007) | Fragment consumed | Owning file (WP partition) | Line-drift vs census |
|---|---|---|---|---|---|---|---|
| **R1** | `status/emit.py::_feature_status_lock_root` | `status/emit.py:388-424` (walk at :417,:422,:424; call at :545) | lock-root: `repo_root` arg else `feature_dir.parent.parent` + `classify_worktree_topology` / `resolve_canonical_root` | **meta/primary** (the lock root anchors the primary checkout) | `workspace.primary_root` | `status/emit.py` (WP-EMIT) | census said `:388-424`/`:392` — **stable** (comment at :392 still names the seam) |
| **R2** | `status/work_package_lifecycle.py` root walk | `work_package_lifecycle.py:77-89` (guard :77; walks :82,:87,:89) | `feature_dir.parent.name != KITTY_SPECS_DIR` guard + 3× `.parent.parent` | **meta/primary** | `workspace.primary_root` | `status/work_package_lifecycle.py` (WP-WPL) | census `:77-89` — **stable** |
| **R3** | `status/lifecycle_events.py` root walk | `lifecycle_events.py:234-239` | `.parent.parent` / `.parent.parent.parent` keyed on `KITTY_SPECS_DIR` | **meta/primary** | `workspace.primary_root` | `status/lifecycle_events.py` (WP-LE) | census `:234-239` — **stable** |
| **R4** | `status/store.py` ancestor scan | `store.py:123-127` | `KITTY_SPECS_DIR` ancestor scan to find root for event append | **meta/primary** | `workspace.primary_root` | `status/store.py` (WP-STORE) | census `:123-127` — **stable** |
| **R5** | `coordination/status_transition.py::_repo_root_for_feature` | `status_transition.py:49-54` (walk at :53) | `feature_dir.parent.parent` root walk | **meta/primary** | `workspace.primary_root` | `coordination/status_transition.py` (WP-COORD) | census cited `:52-53,:458` — **re-pinned to the named helper `:49-54`** |
| **P1** | `core/worktree.py` placement join (×2) | `core/worktree.py:384` AND `:396` | `feature_dir = worktree_path / KITTY_SPECS_DIR / branch_name` (duplicate across the reuse + create arms) | **meta/primary** (planning-artifact placement under the worktree) | factory placement projection (`CommitTarget` / `ArtifactPlacementFragment`); naming already via `mission_dir_name` seam | `core/worktree.py` (WP-WT) | census `:364-376,384,396` — **re-pinned: the two `feature_dir` joins are :384 and :396** |
| **S1** | `status_transition.py::_identity_for_request` write-surface + write-target selection | `status_transition.py:234-295` (target select :291) | reads meta → `mid8`/`mission_id`/`coord_branch`; `resolve_transaction_mid8`; `destination_ref = coord_branch or _current_branch` | **status/coord** (status WRITE — MUST stay coord) | `branch_ref.destination_ref` (target) + `status_surface.status_write_dir` (surface) | `coordination/status_transition.py` (WP-COORD) | census `:234-295` — **stable** |
| **S2** | `status_transition.py::_read_contract_from_transaction_target` write-surface SELECTION | `status_transition.py:439-475` (coord/primary ladder :444-475) | selects coord-worktree vs coord-branch-ref vs primary write target; `CoordinationWorkspace.worktree_path` + `worktree_root/KITTY_SPECS/_transaction_dir_name` join | **status/coord** (the #1716 topology-authority ROOT) | `status_surface.status_write_dir` (output field only; the SELECTION logic is #1716) | `coordination/status_transition.py` (WP-COORD) | census cited `:439-475` — **stable** |

**Family-routing assertion (C-007):** every status/coord site (S1, S2) routes to
`status_surface.status_write_dir` / `branch_ref.destination_ref`, **never to `primary_root`** — the
write-coord authority is preserved. The meta/primary sites (R1–R5, P1) route to
`workspace.primary_root` — these are READS of the root, not status writes, so `primary_root` is the
*correct* family target (they resolve the anchor; the actual status write still flows through the
status surface). There are **no lanes/coord sites in scope** (lanes.json placement, randy's W16, is
already on the naming seam and is the #1878/#1716 remainder, deferred).

**Naming is NOT in the residual.** Every branch/worktree/coord NAME (P1's `mission_dir_name`, S1/S2's
`CoordinationWorkspace`, recovery globs) already routes through `lanes/branch_naming` (#2012 /
01KV6510 / 01KV7SFD). C-001 holds: `branch_naming` stays a collaborator, not absorbed.

---

## 2. The bounded-now subset vs the deferred topology-authority root

- **Routable NOW (the safe first cut, C-003 recommended):** R1, R2, R3, R4, R5, P1, and the S1
  *target/surface consumption* (replace the inline `_repo_root_for_feature` walk + the
  `coord_branch or _current_branch` selector with the factory projection). These are root-walk /
  placement-join / write-target consolidations over an **already-correct** factory authority.
- **DEFERRED (#1716 topology-authority root, ~2094 LOC):** S2's `_read_contract_from_transaction_target`
  branch ladder — the coord-worktree-vs-coord-branch-ref-vs-primary *selection* logic. Consuming
  `status_surface.status_write_dir` presupposes that selector is unified; the selection itself is the
  #1716 authority root the operator parked (decision `01KV8Q49WEG9RRKCEZ3XYN5DWP`). Mission B may
  consume the *output field* but MUST NOT rewrite the *selection*.

---

## 3. Ownership partition for WP decomposition (NO two WPs share owned_files)

| WP | Owned file | Sites | Family | Risk |
|----|-----------|-------|--------|------|
| **WP-EMIT** | `src/specify_cli/status/emit.py` | R1 | meta/primary | low |
| **WP-WPL** | `src/specify_cli/status/work_package_lifecycle.py` | R2 | meta/primary | low |
| **WP-LE** | `src/specify_cli/status/lifecycle_events.py` | R3 | meta/primary | low |
| **WP-STORE** | `src/specify_cli/status/store.py` | R4 | meta/primary | low |
| **WP-WT** | `src/specify_cli/core/worktree.py` | P1 | meta/primary | low-med (placement projection wiring) |
| **WP-COORD** | `src/specify_cli/coordination/status_transition.py` | R5, S1 (+ S2 deferred) | meta/primary + status/coord | med-high (write-surface; touches the second factory) |
| **WP-RETIRE** | `src/mission_runtime/resolution.py` + `src/mission_runtime/context.py` + `src/specify_cli/status/aggregate.py` | FR-006: retire `prompt_source` fragment + dead `surface=` read-param (`aggregate.py:199,266,309`) | n/a (deletion) | low |

**Partition is clean — no owned_files overlap.** Each status root-walk site is its own module
(R1–R4 → four distinct files). The coord write-surface (R5+S1) is a single module (WP-COORD). The
FR-005 architectural-guard *extension* (ratchet flagging write-side re-derivation) lands in
`tests/architectural/` (e.g. alongside `test_mission_runtime_surface.py` /
`test_topology_resolution_boundary.py`) — test-only, owned by whichever WP adds it, no src overlap.
The `mission_runtime/` files appear **only** under WP-RETIRE (deletion of dead scaffolding) — Q3
confirmed no fragment *completion* is needed, so the factory authority modules are otherwise untouched
(C-001).

**Note — `core/constants.py` shared-import hazard:** R1–R4 each currently import `KITTY_SPECS_DIR`
from `core/constants.py`. Routing them to `workspace.primary_root` *removes* those imports rather than
adding a shared write — no overlap is introduced. The factory projection each WP consumes
(`build_execution_context` / a WP-less projection) is an *import*, not an owned edit.

---

## 4. C-003 scope recommendation (LOC / risk)

| Option | Scope | Est. LOC | Risk | Recommendation |
|--------|-------|---------|------|----------------|
| **A — bounded root/placement/surface/target adoption (RECOMMENDED)** | R1–R5 + P1 + S1 target/surface consumption + FR-006 retirement | ~90–130 LOC (randy's est. holds; root-walk ~40–55, placement ~15–25, target/surface consumption ~20–30, retirement ~10–15 deletion) | **low-medium** — pure equivalence over an already-correct factory; the only medium site is WP-COORD (write-surface, topology-true fixtures mandatory per NFR-002) | **TAKE THIS.** Proves read/write symmetry end-to-end (SC-002/SC-003), turns all three write-half fields load-bearing, stays inside C-001. |
| **B — A + bounded write-surface-SELECTION slice (S2)** | + rewrite part of `_read_contract_from_transaction_target` to unify the coord/primary selector | +~60–90 LOC into the #1716 authority root | **high** — touches the ~2094-LOC topology authority the operator deliberately parked; on-disk coord-state churn risk (violates NFR-004 idempotency); re-opens #1716's bounded context (DIR-031) | **DEFER.** |

**Is the S2 selection slice REQUIRED for read/write symmetry, or cleanly deferrable?** **Cleanly
deferrable.** Symmetry (NFR-001: read and write resolve the *same* root/surface/target) is achieved by
Option A: both paths consume `status_surface.status_write_dir` (= the coord authority), `primary_root`,
and `destination_ref` from the *same* `build_execution_context`. The S2 *selection* logic computes the
**same value** the factory's `_resolve_status_surface_dir` already computes (both bottom out in
`resolve_status_surface`) — so once S1 consumes the fragment, read and write are symmetric **without**
touching S2's ladder. S2 is an internal duplication of the *resolution*, not a divergence of the
*result*; collapsing it is a reduction win, not a symmetry prerequisite. It belongs to the #1716
topology-authority root (~2094 LOC) and defaults to a later focus.

**One equivalence assertion the plan MUST carry (NFR-001 gate before flipping S1's target):** the
factory's flattened-arm `destination_ref` carries `target_branch` (`resolution.py:716`), whereas the
inline write site carries `_current_branch(repo_root)` (`status_transition.py:291`). Under normal
flattened topology these coincide, but the plan must add a topology-true parameterized test
(primary/coord/submodule) proving zero divergence read-vs-write before the consumer flip — else a
detached-HEAD / off-target-branch edge could silently change the write target. This is a *test*
obligation, not a factory change.

---

## 5. #2016 fold recommendation — CROSS-REF, do not fold

**#2016 (orchestrator coord-read identity bootstrap, coord-only, no primary meta) is a READ-path
concern and is ALREADY ADDRESSED by Mission A — recommend CROSS-REF, NOT fold.** Evidence on HEAD:

- The orchestrator site (`orchestrator_api/commands.py:278-311`) is a **read resolver**
  (`_coord_worktree_path_for_mission` → `resolve_mission_read_path`), not a write site. It reads the
  real `mission_id` from primary meta and threads it into `resolve_mid8` so the coord-aware
  `bool(mid8)` fail-closed guard arms (the M3 defect's fix).
- That fix **already landed in Mission A** (commit `d4f0cf581` "fix(WP09): orchestrator typed-error
  pass-through + fail-closed identity (M2/M3)"; the code at `:282-311` documents it as FR-011/M3). It
  is on this stacked branch.
- #2016 therefore is **not reachable via Mission B's adopted write fragments** (it does not re-derive
  root/placement/write-surface/write-target) and is **not an open write-side defect** — it is a
  read-path bootstrap already closed upstream of Mission B.

**Recommendation:** cross-reference #2016 in the plan as "read-path, resolved by Mission A WP09
(d4f0cf581); verify-don't-redo." Do NOT pull it into Mission B's write-side WPs — folding a closed
read-path concern into a write-adoption mission would violate the bounded-scope discipline (C-003) and
the three-artifact-family routing (C-007: #2016 is a coord READ, Mission B's S1/S2 are status WRITES).

---

## 6. Line-drift corrections (census → HEAD `efb28158f`)

| Census ref (pre-merge) | HEAD ref | Correction |
|---|---|---|
| `status/emit.py:392` (seam comment) / `:388-424` | `status/emit.py:388-424`; walks at `:417,:422,:424`; comment at `:392`; call at `:545` | stable; explicit walk lines pinned |
| `work_package_lifecycle.py:77-89` | `:77` (guard), `:82,:87,:89` (walks) | stable |
| `lifecycle_events.py:234-239` | `:234,:237,:239` | stable |
| `store.py:123-127` | `:123,:127` | stable |
| `status_transition.py:52-53,:458` (root walk) | `_repo_root_for_feature` at `:49-54` (walk `:53`) | **re-pinned to the named helper** |
| `core/worktree.py:364-376,384,396` | placement joins at `:384` (reuse arm) AND `:396` (create arm); naming compose `:364-376` | **the two `feature_dir` joins are :384 and :396** |
| `status_transition.py:234-295` (`_identity_for_request`) | `:234-295`; target select `:291`; `resolve_transaction_mid8` `:279` | stable |
| `status_transition.py:439-475` (`_read_contract_from_transaction_target`) | `:439-475` | stable |
| factory write-half fields | `context.py:144` (`primary_root`), `:162` (`status_write_dir`), `:130` (`destination_ref`); `resolution.py:698,724-728,705-722` | **NEW — Mission A merged; fields verified present + correct** |

---

## Bottom line

The factory's three write-half fields (`workspace.primary_root`,
`status_surface.status_write_dir`, `branch_ref.destination_ref`) **exist and resolve to the correct
authority on HEAD** — `status_write_dir` in particular routes to the **coord/status authority** (via
`resolve_status_surface`, fail-closed, NOT `primary_root`), satisfying C-007. **Mission B is pure
consumer-routing; no factory fragment-completion is required** (only FR-006 deletion of dead
scaffolding). Take **C-003 Option A** (~90–130 LOC, low-medium risk) — the bounded
root/placement/surface/target adoption; defer the S2 write-surface-SELECTION slice to the #1716
topology authority root (~2094 LOC, cleanly deferrable — it computes the same value the factory
already does). **Cross-ref #2016** (read-path, already fixed by Mission A WP09), do not fold. The
seven-WP ownership partition is overlap-free.
