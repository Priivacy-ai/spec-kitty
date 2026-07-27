# Randy Reducer — WRITE-Path Re-Derivation Census

**Lens:** behavior-preserving reduction; single-factory adoption symmetry (read AND write
draw from one context object that encapsulates naming/identity/paths).
**Premise under test (operator clarification):** the doc-09 fragments are unread because the
WRITE path never adopted them. If write-symmetry is the goal, does the read-side
`RETIRE-WIDE` verdict reverse?

---

## Verdict (lead)

- **Does write-symmetry make the unread fragments load-bearing? PARTIALLY — and the reversal is
  uneven across the five.** The write path *already* does everything the fragments encode — it
  just does it via a **second, parallel factory** (`status_transition._identity_for_request` +
  `CoordinationWorkspace` + `branch_naming.*`), not the doc-09 `ExecutionContext`. So the
  fragments are not "aspirational ideas with no use case"; they are **the read-side projection of
  a write-side resolution that already exists and is load-bearing**. Three of the five fragments
  map cleanly onto real, currently-duplicated write derivations
  (`identity`→mid8, `branch_ref`→destination_ref/coordination_branch, `status_surface`→the
  read/write dir split). Two (`workspace`, `prompt_source`) have weaker write consumers.
- **Critically: the NAMING half of the factory already exists and is already adopted on BOTH
  paths.** `lanes.branch_naming` (mission 01KV6510/WP01, 01KV7SFD/WP01) is the single naming
  composer; coordination, worktree creation, lanes, and merge **all route through it**. The
  unconsolidated half is **placement / root-resolution** (`KITTY_SPECS_DIR / dir` joins +
  `.parent.parent` walks + read/write surface selection), which is split across an
  *identity/transaction* factory (write) and `_read_path_resolver`/`surface_resolver` (read).
- **The reversal is therefore NOT "build the fragments and route writes through them."** It is
  **"unify the two existing factories"** — `_identity_for_request` (write) and
  `resolve_action_context` (read) resolve the *same* tuple (repo_root, feature_dir, mid8,
  destination_ref, coordination_branch, read_dir, write_dir) twice. The fragment model becomes
  load-bearing only if it is the **shared return type of that one unified resolver**, not a
  passthrough bag bolted onto the read side alone.
- **Write-side reduction available via a single factory: ~10–13 collapsible derivation sites,
  est. ~90–130 LOC** (see §3), almost entirely in *placement + surface-selection*, NOT naming
  (naming is already done).
- **Routable NOW (no #1716/#1878): a bounded subset of ~3–4 sites.** The deep write-side coord
  topology authority (the read/write surface *selection* logic in `status_transition` and
  `surface_resolver`) requires #1716 and stays on the #1878 strangler — the operator already
  parked it (D-1, decision `01KV8Q49WEG9RRKCEZ3XYN5DWP`).

---

## 1. Write-Path Re-Derivation Census (src/, tests excluded)

What each WRITE site independently re-derives, and which single-factory field would serve it.
"Served by factory field" uses the doc-09 fragment names. now/defer per §4.

| # | Write site (file:line) | What it re-derives | Factory field that would serve it | now/defer |
|---|---|---|---|---|
| W1 | `core/mission_creation.py:322-328` | `mission_id = ULID()` → `mid8` via `resolve_mid8` → `mission_dir_name` → `feature_dir = root / KITTY_SPECS_DIR / dir` | `identity` (mid8 + mission_slug) + `artifact_placement` (feature_dir) | **defer-mint** (mint site; it *produces* the identity — it is the factory's own source, not a consumer) |
| W2 | `core/mission_creation.py:407-416` | coord branch via `ensure_coordination_branch(slug, mission_id, target)` | `branch_ref.coordination_branch` | now-adjacent (already routes `branch_naming.coord_branch_name`) |
| W3 | `core/worktree.py:364-376,384,396` | `resolve_mid8` → `mission_dir_name` → `branch_name` → `worktree_path = root/WORKTREES/dir` → `feature_dir = wt/KITTY_SPECS/dir` (×2 same compose) | `identity` + `workspace.execution_workspace` + `artifact_placement` | **now** (naming already via seam; placement join is the inline residual) |
| W4 | `coordination/status_transition.py:234-295` `_identity_for_request` | THE write-side factory: canonicalizes feature_dir, resolves repo_root, reads meta → `mid8`/`mission_id`/`coord_branch`, `resolve_transaction_mid8`, `destination_ref = coord_branch or current_branch` | This **IS** `identity` + `branch_ref` assembled — it is the parallel factory | defer (#1716 — write topology authority root) |
| W5 | `coordination/status_transition.py:439-475` `_read_contract_from_transaction_target` | selects write target: `CoordinationWorkspace.worktree_path` → `worktree_root/KITTY_SPECS/_transaction_dir_name` vs primary | `status_surface.status_write_dir` (+ branch_ref) | defer (#1716) |
| W6 | `coordination/status_transition.py:52-53,458` | `feature_dir.parent.parent` root walk + `worktree_root/KITTY_SPECS/dir` join | `workspace.primary_root` + `artifact_placement` | **now** (the walk; selection stays #1716) |
| W7 | `coordination/workspace.py:161-167` `CoordinationWorkspace.worktree_path` | `repo_root/.worktrees/coord_dir_name(slug,mid8)` | `workspace.coord_worktree` | now-adjacent (already via `coord_dir_name` seam) |
| W8 | `coordination/transaction.py:222,242,788` | `repo_root/KITTY_SPECS/kitty_dir_name/meta.json` (×2) + `worktree_root/KITTY_SPECS/kitty_dir_name` | `status_surface.status_write_dir` + `artifact_placement` | defer (#1716 — transaction write target) |
| W9 | `status/emit.py:388-424` `_feature_status_lock_root` | lock-root selection: `repo_root` arg, else `feature_dir.parent.parent` / `classify_worktree_topology` / `resolve_canonical_root` | `workspace.primary_root` (the lock root the write needs) | **now** (the seam comment at :392 literally says "the topology seam exists to kill `feature_dir.parent.parent`") |
| W10 | `status/work_package_lifecycle.py:77-89` | `feature_dir.parent.name != KITTY_SPECS_DIR` guard + 3× `feature_dir.parent.parent` | `workspace.primary_root` | **now** |
| W11 | `status/lifecycle_events.py:234-239` | `.parent.parent` / `.parent.parent.parent` root walk keyed on `KITTY_SPECS_DIR` | `workspace.primary_root` | **now** |
| W12 | `status/store.py:123-127` | `KITTY_SPECS_DIR` ancestor scan to find root for event append | `workspace.primary_root` | **now** |
| W13 | `retrospective/generator.py:89,1015` | `repo_root/KITTY_SPECS` enumerate + write retro under mission dir | `artifact_placement` | now-adjacent |
| W14 | `doctrine_synthesizer/apply.py:583,774` | `repo_root/KITTY_SPECS` enumerate for adoption writes | `artifact_placement` | now-adjacent |
| W15 | `lanes/recovery.py:135,250` | `f"kitty/mission-{slug}*"` branch-glob + legacy `f"kitty/mission-{slug}"` fallback | `branch_ref` / naming seam | now-adjacent (recovery; partially already on `coord_reconstruct_branch`) |
| W16 | `lanes/compute.py:349,452,539,678` | `mission_branch_name(slug, mission_id)` + `lane_id = f"lane-{chr(...)}"` + writes `lanes.json` | naming seam (already) + `branch_ref` | already-adopted (naming via seam); lanes.json placement is the residual |
| W17 | `cli/commands/agent/mission.py` finalize/merge (#1878 ff-advance: :1202,:2291,:2342,:3766) | branch ref + checkout target for ff-advance bookkeeping | `branch_ref` | defer (#1878 strangler) |

**Naming composition is NOT in the residual.** Every branch/worktree/coord NAME site (W2, W3,
W7, W15, W16) already routes through `lanes.branch_naming` — that consolidation shipped
(01KV6510/01KV7SFD). The live write-path residual is **placement joins + root walks + surface
selection** (W3, W6, W8–W14), i.e. exactly the `artifact_placement` / `workspace` /
`status_surface` fragments.

---

## 2. Fragment → Write-Consumer Mapping (does it reverse RETIRE-WIDE?)

Read-side census found 0 live readers for `identity`, `branch_ref`, `workspace`,
`status_surface`, `prompt_source`. Mapping each to the WRITE consumer that *already does the
same derivation by hand*:

| Fragment | Fields | Write consumer that re-derives it today | Reverses RETIRE-WIDE? |
|---|---|---|---|
| `identity` (mission_id, mid8, mission_slug) | mid8 = "single derivation point" per docstring | `_identity_for_request` reads meta → `resolve_transaction_mid8` (W4); `mission_creation` mints + `resolve_mid8` (W1); `worktree` `resolve_mid8` (W3) | **YES, partially.** The mid8 *is* re-derived at ≥3 write sites. But it is **already funneled through `resolve_mid8`/`resolve_transaction_mid8`** — a function-level single point, not the fragment. The fragment adds value only if it *carries* the resolved mid8 so W3/W4 stop re-reading meta. Mild reversal. |
| `branch_ref` (target_branch, coordination_branch) | `_identity_for_request` reads `meta.coordination_branch`, computes `destination_ref` (W4); `mission_creation` `ensure_coordination_branch` (W2); merge ff-advance (W17) | **YES.** `destination_ref = coord_branch or current_branch` is a real, load-bearing write derivation duplicated against the read-side's silent assembly. Read-side called it "internal-only"; on the write side it is the **write-target ref selector**. Reversal holds — but it's owned by #1716/#1878. |
| `workspace` (primary_root, coord_worktree, execution_workspace, allowed_command_cwd) | `.parent.parent` root walks at W6, W9, W10, W11, W12; `CoordinationWorkspace.worktree_path` (W7) | **YES — strongest reversal.** `primary_root` is re-derived by hand at **≥5 write sites** via `feature_dir.parent.parent`. `emit.py:392` *explicitly names the seam* ("the topology seam exists to kill `feature_dir.parent.parent`"). This fragment is the most load-bearing-once-written. |
| `status_surface` (status_read_dir, **status_write_dir**) | `_read_contract_from_transaction_target` selects the write target (W5); `transaction.py` write-dir joins (W8) | **YES — this is the decisive reversal.** The fragment carries a `status_write_dir` field. The read-side census found it dead because `MissionStatus.load(surface=...)` only consumes `status_read_dir`. The **write** consumer (`status_transition`) is the one that needs `status_write_dir` — and it builds it via its own parallel selector. The unused half of the fragment is exactly the write half. **Write-symmetry makes `status_surface` load-bearing.** (Owned by #1716.) |
| `prompt_source` (prompt_source_dir) | No write site re-derives a prompt-source dir; prompts are read-only template lookups | **NO.** No write consumer. `prompt_source` stays vestigial on both paths. |

**Net on the RETIRE-WIDE verdict:** it **reverses for 3 of 5** (`workspace`, `status_surface`,
`branch_ref`), **softens for 1** (`identity` — already function-funneled), and **holds (still
retire) for 1** (`prompt_source`). The read-side verdict "all 5 are dead scaffolding" was correct
*as observed from the read side*, but it mistook **write-path non-adoption** for **no use case**.
The fragments encode a real write-side resolution that currently lives in a duplicate factory.

---

## 3. Reduction Available via a Single Factory

If both paths drew from one factory returning the (identity, branch_ref, workspace,
status_surface) tuple:

**Sites that collapse:**

- **Root resolution (`primary_root`):** W6, W9, W10, W11, W12 + the read-side `root_resolver`
  consumers — **5 write sites + the read seam** collapse to one `workspace.primary_root` read.
  Each is a 1–6 line `.parent.parent`/`classify_worktree_topology`/`resolve_canonical_root`
  block. **Est. ~40–55 LOC.**
- **mid8 derivation (`identity`):** W1, W3, W4 each re-read meta / re-call `resolve_mid8`.
  Carrying it on the context removes the per-site meta read (W3, W4). **Est. ~10–15 LOC.**
- **Write-target / surface selection (`status_surface.status_write_dir`):** W5, W8 — the
  `_read_contract_from_transaction_target` branch ladder + `transaction.py` joins. This is the
  largest single block (~60 LOC in `status_transition`) but it is **also the part #1716 owns** —
  only its *output field* can be consumed early; the *selection logic* stays. **Est. ~20–30 LOC
  consumable now, the rest deferred.**
- **Placement joins (`artifact_placement`):** W3, W8, W13, W14, W16 inline `… / KITTY_SPECS_DIR
  / dir` — already partially served by the read-side `CommitTarget`/`artifact_home_for` (the ONE
  adopted fragment). Extending that single placement authority to the write joins. **Est. ~15–25
  LOC.**

**Total write-side reduction: ~10–13 collapsible sites, est. ~90–130 LOC** — but note **none of
it is naming** (naming already collapsed via `branch_naming`). The reduction is concentrated in
**root-resolution** and **placement**, with surface-selection mostly deferred.

**Irreducible minimum the factory must encapsulate** (what genuinely cannot be inlined without
re-creating drift):

1. **Naming composition** — DONE; `lanes.branch_naming` is the single composer. The factory must
   *delegate* here, not re-implement.
2. **Root resolution** — `feature_dir → primary_root` via `classify_worktree_topology` /
   `resolve_canonical_root` (the `.parent.parent` killer). This is the highest-ROI, lowest-risk
   encapsulation and the one the codebase explicitly flagged (`emit.py:392`).
3. **Placement** — `root + KITTY_SPECS_DIR + dir_name` → `CommitTarget`/feature_dir. The ONE
   already-load-bearing fragment; extend it to write joins.
4. **Surface selection (read_dir vs write_dir, coord vs primary)** — the deepest grain;
   **#1716-owned**, must NOT be pulled into this factory now.

---

## 4. Strangler Sequencing — Now-Routable vs #1716/#1878-Deferred

**Routable NOW (no write-side topology authority; pure root-walk/placement consolidation):**

- **W9** `status/emit.py:_feature_status_lock_root` — the code comment already declares the seam;
  replace `feature_dir.parent.parent` with `workspace.primary_root`. Self-contained, has the
  topology classifier already inlined.
- **W10** `status/work_package_lifecycle.py` — 3× `.parent.parent` → `primary_root`.
- **W11** `status/lifecycle_events.py` — `.parent.parent[.parent]` root walk → `primary_root`.
- **W12** `status/store.py` — `KITTY_SPECS_DIR` ancestor scan → `primary_root`.
- **W3 (placement half only)** `core/worktree.py` — the duplicated `wt / KITTY_SPECS / dir` join
  (×2) → one placement call; naming is already on the seam.

These 4–5 sites form the **bounded now-routable subset**: they consolidate `workspace.primary_root`
(root resolution), which is the strongest-reversing fragment and has **no dependency on the
read/write surface-selection topology**. Risk is low (pure equivalence over an already-existing
classifier), matching the mission's #1993-minimal grain.

**DEFERRED (require #1716 write-side coord topology authority root, decision
`01KV8Q49WEG9RRKCEZ3XYN5DWP` — DEFER #1716 entirely):**

- **W4** `_identity_for_request`, **W5** `_read_contract_from_transaction_target`, **W8**
  `transaction.py` write-target joins — these *select* between coordination-worktree /
  coordination-branch-ref / primary-checkout write surfaces. That selection logic IS the #1716
  authority root (~2094 LOC surface per research D-1). Consuming `status_surface.status_write_dir`
  presupposes that selector is unified. **Stays on #1878 strangler.**

**DEFERRED (#1878 entry-side / merge-bookkeeping strangler):**

- **W17** finalize/merge ff-advance branch bookkeeping in `cli/commands/agent/mission.py` — these
  are #1878 ff-merge treadmill sites, explicitly tagged in-code. Out of this mission's grain.

**Mint sites (not consumers, leave alone):**

- **W1** `mission_creation` and the `resolve_mid8` calls *produce* identity; they are the factory's
  source, not duplication to collapse.

---

## Bottom line

The read-side `RETIRE-WIDE` was right about what it could see and **wrong about why** — the
fragments are unread because the write path runs a **parallel factory** (`_identity_for_request`
+ `CoordinationWorkspace`), not because the derivations don't exist. Write-symmetry makes
**3 of 5 fragments load-bearing** (`workspace`, `status_surface.status_write_dir`, `branch_ref`),
**softens `identity`** (already funneled through `resolve_mid8`), and **leaves `prompt_source`
genuinely vestigial**. The single-factory reduction is **~90–130 LOC across ~10–13 sites**,
concentrated in **root-resolution and placement** — NOT naming, which already collapsed into
`lanes.branch_naming`. **Routable now without #1716/#1878: a bounded ~4–5-site subset** that
consolidates `workspace.primary_root` (the `.parent.parent` killer the codebase already flagged
at `emit.py:392`). The deep read/write surface-*selection* (W4/W5/W8) is the #1716 authority root
the operator deliberately parked, and the merge ff-advance bookkeeping (W17) is #1878 — both stay
deferred. The correct mission framing is **"unify the two existing factories' root/placement
output,"** not "build fragments and route writes through a passthrough bag."
