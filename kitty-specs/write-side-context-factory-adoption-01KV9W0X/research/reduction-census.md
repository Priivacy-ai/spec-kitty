# Randy Reducer — Write-Side Reduction Census (Mission B, re-verified on HEAD)

**Branch:** `feat/write-side-context-factory-adoption` (HEAD `efb28158f`, stacked on merged Mission A).
**Factory:** `build_execution_context` at `src/mission_runtime/resolution.py:91` (relocated from
`specify_cli.next._internal_runtime` → `src/mission_runtime/` since the prior census; the read side
now assembles **all 6 fragments**, see `_assemble_core_fragments` `resolution.py:664-738`).
**Lens:** behavior-preserving reduction; single-factory adoption symmetry; C-001 (adopt, build no
new authority); NFR-003 (verification-by-deletion); NFR-004 (idempotency).

> **Re-verification verdict:** the prior `randy-writepath-census.md` holds on HEAD with **only line
> drift**, plus **two material strengthening facts that the prior census did not yet have:**
> (1) all four adoption-target fragment fields now exist on the read side and have **literally zero
> live readers** (grep-proven below) — so adoption genuinely flips them 0→load-bearing; and
> (2) **W9 (`emit.py`) and W10 (`work_package_lifecycle.py`) are now byte-identical logical
> duplicates** of the same topology-aware lock-root resolver (both already inline
> `classify_worktree_topology` + `resolve_canonical_root`), i.e. the `.parent.parent` walk is
> already *half-killed* and the residual is a **consolidation to one helper**, not a from-scratch
> seam adoption. (3) A real **idempotency divergence** exists at the write-target selector
> (`destination_ref`) under flattened topology — §6.

---

## 1. Re-verified write-side re-derivation census (HEAD line:numbers, tests excluded)

| # | Site (current file:line) | Re-derives | Factory fragment field | now/defer |
|---|---|---|---|---|
| W1 | `core/mission_creation.py:322-328` | `mission_id = ULID()` → `resolve_mid8` → `mission_dir_name` → `feature_dir = root / KITTY_SPECS_DIR / dir` | `identity` + `artifact_placement` | **defer-mint** (mint source, not a consumer) |
| W2 | `core/mission_creation.py:407-409` | `ensure_coordination_branch(slug, mission_id, target)` | `branch_ref.coordination_branch` | now-adjacent (already via naming seam) |
| W3 | `core/worktree.py:364-396` | `resolve_mid8` → `mission_dir_name` → `branch_name` → `worktree_path = root/WORKTREES_DIR/dir` → `feature_dir = wt/KITTY_SPECS_DIR/dir` (**×2**, lines 384 & 396, same compose) | `identity` + `workspace.execution_workspace` + `artifact_placement` | **now** (placement-join residual; naming already on seam) |
| W4 | `coordination/status_transition.py:234-296` `_identity_for_request` | THE write-side parallel factory: canonicalize feature_dir, resolve repo_root, read meta → `mid8`/`mission_id`/`coord_branch`, `resolve_transaction_mid8`, **`destination_ref = coord_branch or _current_branch(repo_root)`** (`:291`) | this IS `identity` + `branch_ref` assembled by hand | defer (#1716 topology root) — **but `destination_ref` is the idempotency hotspot, §6** |
| W5 | `coordination/status_transition.py:439-472` `_read_contract_from_transaction_target` | write-target select: `CoordinationWorkspace.worktree_path` (`:453`) → `worktree_root/KITTY_SPECS_DIR/_transaction_dir_name` (`:458`) vs primary | `status_surface.status_write_dir` (+ `branch_ref`) | defer (#1716) |
| W6 | `coordination/status_transition.py:50-54,52-53` `_repo_root_for_feature` | `feature_dir.parent.name == KITTY_SPECS_DIR` guard → `feature_dir.parent.parent` root walk | `workspace.primary_root` | **now** (the walk; surface-selection stays #1716) |
| W7 | `coordination/workspace.py:161-167` `CoordinationWorkspace.worktree_path` | `repo_root/.worktrees/coord_dir_name(slug,mid8)` | `workspace.coord_worktree` | now-adjacent (already via `coord_dir_name` seam) |
| W8 | `coordination/transaction.py:221-222,241-242,~280-286` | `repo_root/KITTY_SPECS_DIR/kitty_dir_name/meta.json` (×2) + KITTY_SPECS ancestor walk for `worktree_root` | `status_surface.status_write_dir` + `artifact_placement` | defer (#1716 transaction write target) |
| W9 | `status/emit.py:388-424` `_feature_status_lock_root` | lock-root: `repo_root` arg, else `classify_worktree_topology` / `resolve_canonical_root` / `feature_dir.parent.parent` fallbacks | `workspace.primary_root` | **now** (comment `:392` literally: *"the topology seam exists to kill `feature_dir.parent.parent`"*) |
| W10 | `status/work_package_lifecycle.py:60-89` | **byte-identical** to W9 (same topology classifier + `resolve_canonical_root` + 3× `.parent.parent` fallbacks) | `workspace.primary_root` | **now** (consolidate W9↔W10 → one helper) |
| W11 | `status/lifecycle_events.py:230-240` `_repo_root_for_lifecycle_log` | `.parent.parent` / `.parent.parent.parent` root walk keyed on `KITTY_SPECS_DIR` (+ `.kittify` arm) | `workspace.primary_root` | **now** |
| W12 | `status/store.py:119-130` `_find_mission_specs_root` | `KITTY_SPECS_DIR` ancestor scan (`candidate` / `two_up`) | `workspace.primary_root` | **now** |
| W13 | `retrospective/generator.py:89,1015` | `repo_root/KITTY_SPECS_DIR` enumerate + retro write under mission dir | `artifact_placement` | now-adjacent |
| W16 | `lanes/compute.py:349,452,539,678` | `mission_branch_name(slug, mission_id)` + `lane_id = f"lane-{chr(...)}"` + write `lanes.json` | naming seam (already) + `branch_ref` | already-adopted (naming); `lanes.json` placement residual |
| W17 | `cli/commands/agent/mission.py` finalize/merge ff-advance | branch ref + checkout target | `branch_ref` | defer (#1878 strangler) |

**`.parent.parent` count on HEAD:** 11 occurrences across the status/coordination write surfaces
(`grep -rn '\.parent\.parent' src/specify_cli/{status,coordination}` minus tests), spread over 4
files: `lifecycle_events.py`, `emit.py`, `work_package_lifecycle.py`, `status_transition.py`.
This matches the prior census's "≥5 sites" claim (the 11 raw occurrences collapse to **5 logical
root-walk seams**: W6, W9, W10, W11, W12 — W9/W10 share one logical body).

**Naming is NOT in the residual.** Every NAME site (W2, W3, W7, W16) already routes through
`lanes.branch_naming` (`mission_dir_name` / `resolve_mid8` / `coord_dir_name` / `mission_branch_name`).
The live residual is **root walks + placement joins + surface selection** = exactly the
`workspace` / `artifact_placement` / `status_surface` fragments. Confirmed unchanged on HEAD.

---

## 2. 0→load-bearing confirmation (per adoption-target fragment)

Grep over `src/` (tests + the definition/assembly sites excluded) for any **consumer** of each
fragment attribute:

| Fragment field | Definition / assembled at | **Live readers today** | Read-side resolves it correctly? |
|---|---|---|---|
| `workspace.primary_root` | `WorkspaceFragment` `context.py:144`; assembled `resolution.py:655-661` via `get_main_repo_root` (the single worktree-pointer parser, IC-04) | **0** (`grep '\.primary_root'` outside context/resolution = none) | **YES** — `get_main_repo_root` → `resolve_canonical_root`, CWD-invariant by construction (`_assemble_workspace_fragment` docstring; parity ratchet asserts primary-CWD == lane-CWD) |
| `status_surface.status_write_dir` | `StatusSurfaceFragment` `context.py:162`; assembled `resolution.py:724-728` | **0** (`grep '\.status_write_dir'` outside context = none) | **YES, with a caveat** — read side assembles `status_write_dir == status_read_dir == surface_dir` (`resolution.py:727`), i.e. the write half currently mirrors the read surface (`resolve_status_surface`). Correct value for *read-primary*; the coord write-target *selection* (W5) is the #1716-owned slice that must feed the real write dir (FR-003 / C-007) |
| `branch_ref.destination_ref` | `BranchRefFragment` `context.py:130`; assembled `resolution.py:705-717` | **0** (`grep 'branch_ref\.destination_ref'` outside context/resolution = none; the `.destination_ref` reads that exist are on the **separate** `_TransactionIdentity` dataclass, not the fragment) | **YES for coordination topology**, **DIVERGES for flattened** — see §6 |
| `prompt_source.prompt_source_dir` | `PromptSourceFragment` `context.py:181`; assembled `resolution.py:761-778` | **0** (`grep '\.prompt_source'` consumer = none) | n/a — genuinely dead, §5 |

**All four adoption targets confirmed 0 live readers on HEAD.** Adoption therefore *is* the act
that makes them load-bearing (SC-002). The read side already resolves `primary_root` correctly
(the strongest, lowest-risk target); `status_write_dir`/`destination_ref` are correct for the
read-primary/coordination case and carry a bounded #1716 / idempotency caveat noted below.

---

## 3. Reduction quantification

**Now-routable subset (no #1716/#1878 dependency):** the `workspace.primary_root` root-walk seams.

| Seam | Site | Logical body | Est. LOC removed |
|---|---|---|---|
| W6 | `status_transition.py:50-54` | guard + `.parent.parent` | ~4 |
| W9 | `emit.py:388-424` | topology classifier + canonical-root + 3 fallbacks | ~25 (collapses to one delegated call) |
| W10 | `work_package_lifecycle.py:60-89` | **byte-identical to W9** | ~25 (deleted outright — W9 and W10 become one shared helper or both consume `primary_root`) |
| W11 | `lifecycle_events.py:230-240` | `.parent.parent[.parent]` walk | ~8 |
| W12 | `store.py:119-130` | `candidate`/`two_up` ancestor scan | ~10 |
| W3 (placement half) | `worktree.py:384,396` | duplicate `wt / KITTY_SPECS_DIR / dir` join (×2) | ~4 |

- **Inline re-derivations collapsing now:** **6 logical seams** (W3-placement, W6, W9, W10, W11, W12).
- **LOC delta now:** **~75-90 LOC removed**, of which **~25 LOC is pure logical-duplication
  deletion (W9≡W10)** — the highest-confidence reduction in the mission.
- **Deferred (#1716/#1878):** W4 `destination_ref`/`_identity_for_request`, W5/W8 write-surface
  selection, W17 ff-advance. Adds the prior census's ~20-40 LOC when #1716 lands. **Full ceiling
  ≈ 90-130 LOC** matches prior census and spec C-003.

**Irreducible minimum the factory must own (cannot be inlined without re-creating drift):**
1. **Naming** — DONE (`lanes.branch_naming`); the factory delegates, never re-implements.
2. **Root resolution** — `feature_dir → primary_root` via `resolve_canonical_root` (the
   `.parent.parent` killer). Highest-ROI, lowest-risk, codebase-flagged (`emit.py:392`).
3. **Placement** — `root + KITTY_SPECS_DIR + dir_name` → `CommitTarget`; extend the one
   already-load-bearing placement projection to the write joins.
4. **Surface selection** (read_dir vs write_dir, coord vs primary) — **#1716-owned; MUST NOT be
   pulled into this factory now** (C-003 / C-007).

---

## 4. Verification-by-deletion plan (the deletions whose green-suite-after IS the proof)

Per FR/site, the concrete inline re-derivation removed; the behavioral suite staying green is the
adoption proof (NFR-003). All deletions route the removed body to a factory fragment value.

| FR | Site | Delete | Replace with |
|---|---|---|---|
| FR-001 | W9 `emit.py:_feature_status_lock_root` (388-424) | the whole topology-classifier+`.parent.parent` body | `workspace.primary_root` (carried) |
| FR-001 | W10 `work_package_lifecycle.py` (60-89) | **delete the entire byte-duplicate body** | `workspace.primary_root` (carried) — W9≡W10 consolidate |
| FR-001 | W11 `lifecycle_events.py:_repo_root_for_lifecycle_log` (230-240) | `.parent.parent[.parent]` walk | `workspace.primary_root` |
| FR-001 | W12 `store.py:_find_mission_specs_root` (119-130) | `candidate`/`two_up` ancestor scan | `workspace.primary_root` (→ its `/KITTY_SPECS_DIR` child) |
| FR-001 | W6 `status_transition.py:_repo_root_for_feature` (50-54) | `.parent.parent` walk arm | `workspace.primary_root` |
| FR-002 | W3 `worktree.py:384,396` | the duplicated `wt / KITTY_SPECS_DIR / dir` placement join (×2) | factory placement projection (`CommitTarget`/`resolve_placement_only` shape) |
| FR-006 | `aggregate.py` `surface=` param chain | the `surface: StatusSurfaceFragment \| None` param + the `if surface is not None:` branch in `_resolve_read_dir` (`:329-332`) — dead read-param wiring | nothing (delete; the canonical `resolve_status_surface` path is the only live arm) |
| FR-006 | `prompt_source` fragment | `PromptSourceFragment` + `_assemble_prompt_source_fragment` (`resolution.py:761-778`) + the `prompt_source=` build field (`:929`) + the `context.py` field/exports | nothing (0 readers both paths) |
| FR-003/FR-004/FR-007 (**deferred**, #1716) | W4/W5/W8 | `destination_ref`/write-surface selection in `_identity_for_request` + `_read_contract_from_transaction_target` | `branch_ref.destination_ref` / `status_surface.status_write_dir` — **only once #1716 unifies the selector; NOT in the now-cut** (C-003) |

The green suite must run on **topology-true fixtures** (NFR-002): full 26-char ULID `mission_id`,
real coord-worktree + submodule topology. A single-repo stand-in cannot witness the W9/W11/W12
coord-vs-primary divergence the deletions preserve.

---

## 5. Fragment-retirement targets (FR-006), pinned

**`prompt_source` — genuinely dead, 0 readers both paths. RETIRE.**
- Definition: `mission_runtime/context.py:177-181` (`PromptSourceFragment`).
- Assembly: `mission_runtime/resolution.py:761-778` (`_assemble_prompt_source_fragment`) + build
  field `resolution.py:908,929`.
- Exports: `mission_runtime/__init__.py:36,63`; `context.py:246,254,288`.
- **Readers: none** (`grep '\.prompt_source'` consumer = ∅). Confirmed dead on the write side AND
  the read side. No write consumer re-derives a prompt-source dir (prompts are read-only template
  lookups). Safe to delete with no behavioral change (SC-004).

**`StatusSurfaceFragment.surface=` read-param wiring — dead, retireable. RETIRE.**
- Param declared: `status/aggregate.py:199` (`MissionStatus.load(..., surface=...)`) and threaded
  to `_resolve_read_dir` `aggregate.py:266,308-309`.
- Dead branch: `aggregate.py:329-332` (`if surface is not None: return surface.status_read_dir`).
- **Callers: the only two real `MissionStatus.load()` call sites are
  `cli/commands/agent/status.py:163` and `:199` — both pass `repo_root` + `mission_slug` ONLY,
  never `surface=`.** No other caller in `src/` passes it (the other `surface=` grep hits are
  unrelated glossary/ownership/decisions/artifacts kwargs). The param + its branch are dead read-
  param wiring; superseded once the **write** half of the surface fragment is adopted (FR-003).
  Retire the param and the `if surface is not None` arm.

---

## 6. Idempotency (NFR-004): does a fragment value ≠ the hand-rolled value?

**One divergence found — at the write-target selector — and it is the decisive NFR-004 finding.**

| Topology | Write-side hand-rolled (`_identity_for_request:291`) | Factory `branch_ref.destination_ref` (`resolution.py:705-717`) | Match? | Class |
|---|---|---|---|---|
| **Coordination** (meta `coordination_branch` set) | `coord_branch` | `CommitTarget(ref=coord_branch, kind=COORDINATION)` | **byte-equal ref** | idempotent ✓ |
| **Flattened** (no coord_branch) | `_current_branch(repo_root)` = **`git rev-parse --abbrev-ref HEAD`** (whatever branch is checked out, else `"HEAD"`) | `CommitTarget(ref=target_branch, kind=FLATTENED)` where `target_branch = meta.target_branch` (fallback primary branch) | **CAN DIFFER** | **latent-bug-fix (primary) / churn-risk (must verify)** |

**Detail.** `identity.destination_ref` is the git ref the transaction actually commits status events
to (consumed at `status_transition.py:464,472,550,625` → normalized + used as the contract write
target in `transaction.py`). On the **flattened** path:

- The **write side** routes status writes to **`HEAD`** — the operator's *currently checked-out
  branch*. If the operator is sitting on a lane/feature branch (not the mission's `target_branch`),
  status events land on the **wrong, CWD/checkout-dependent ref**. This is exactly the split-brain
  class the factory's CWD-invariant `destination_ref` was built to kill.
- The **factory** routes to the declared `meta.target_branch` (CWD-invariant).

**Classification:** this is a **latent-bug-fix the adoption delivers** (the factory value is the
*correct*, CWD-invariant one; the hand-rolled `_current_branch` is the bug), **NOT** a benign
no-op — so it is **not** a free idempotency-preserving swap. It carries **churn risk under NFR-004**:
on a repo where the operator habitually runs status emits from the target branch, `_current_branch`
== `target_branch` and there is no on-disk change; but where they don't, adoption *changes the write
target* (status events move from HEAD to target_branch). That is a *correctness* change, and the
spec's FR-004 (single `destination_ref` selector) wants it — but it **must NOT be bundled into the
NFR-004 "no on-disk churn" now-cut**. It belongs to the **#1716-deferred W4 slice** (C-003), gated
behind topology-true parameterized tests over flattened/coord/submodule (NFR-001), with an explicit
before/after on-disk-target assertion so the change is witnessed, not assumed.

**All other now-cut sites are idempotency-clean:** W6/W9/W10/W11/W12 resolve a **root for
locking/log-anchoring/specs-root discovery**, not a write *target* — replacing `.parent.parent`
with `primary_root` changes *which root the lock/anchor computes*, and the read side already proves
`primary_root` is the CWD-invariant canonical root the coord/lane arms *should* have been using
(the W9/W10 bodies already do this for coord/lane topology; the swap only makes the primary/ad-hoc
fallback arms consistent). No write *destination* flips. **No extra writes, no surface flip** for
the now-routable subset → NFR-004 satisfied for the bounded cut.

---

## Bottom line

Prior census **re-verified on HEAD** (line drift only). **14 write sites** confirmed (W1-W17 minus
the W14/W15 doctrine/recovery now-adjacents folded as out-of-grain), **5 logical root-walk seams**
(11 raw `.parent.parent`), naming already collapsed. **Four adoption-target fragment fields
(`workspace.primary_root`, `status_surface.status_write_dir`, `branch_ref.destination_ref`,
`prompt_source`) confirmed 0 live readers** — adoption flips them load-bearing. **Now-routable
reduction ≈ 75-90 LOC over 6 seams, ~25 of it pure W9≡W10 byte-duplicate deletion**; full ceiling
≈ 90-130 LOC with the #1716 slice. **`prompt_source` and the `aggregate.py` `surface=` read-param
are dead and retireable** (pinned: `resolution.py:761-778`, `context.py:177-181`,
`aggregate.py:199,329-332`). **One idempotency divergence:** flattened-topology
`destination_ref` — write side targets `git HEAD`, factory targets `meta.target_branch`; this is a
**latent-bug-fix (not a no-op)** and must stay in the **#1716-deferred** slice with before/after
on-disk-target verification, NOT in the idempotency-preserving now-cut.
