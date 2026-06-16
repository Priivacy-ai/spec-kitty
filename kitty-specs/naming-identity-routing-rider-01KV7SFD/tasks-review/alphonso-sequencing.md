# Alphonso — Post-tasks sequencing/ownership/flatten adversarial review

**Mission:** `naming-identity-routing-rider-01KV7SFD` · branch `feat/naming-rider-3-2-1`
**Reviewer:** architect-alphonso (profile-loaded) · adversarial, attacking sequencing + ownership + flatten
**Date:** 2026-06-16
**Verdict:** **NEEDS-ADJUSTMENT** — one merge-blocker residual (`worktree_allocator.py` orphaned from the
WP01 rename) and one over-claim to soften (WP02 "empty allow-list"). Sequencing topology and ownership are
otherwise sound; flatten is safe.

---

## 1. Ratchet-last soundness — the "empty allow-list" claim does NOT hold as stated

WP02 (lane-b) depends on WP03/WP04/WP05 and lands last, with the stated DoD "Allow-list empty/minimal".
Attacking that claim against the live seam and the live ratchet:

### 1a. The detector WP02 builds is genuinely NEW — confirmed, not a tweak
`tests/architectural/test_no_worktree_name_guess.py` today (463 lines) detects only **f-string composes**
(idiom 1 `.worktrees/` join, idiom 2 `kitty/mission-` literal, idiom 3 `f"{slug}-{mid8}"` + `endswith`
dedup). **There is no `[:8]` / `[0:8]` slice detector at all.** WP02's T018 slice detector is net-new AST
code. The plan's framing here is correct and the scope-review's "undersized ratchet" finding is upheld.

### 1b. What MUST be allow-listed (the claim's blind spots)
The "empty allow-list" claim is **only true for the compose idioms after WP05 routes them**, and is
**false for the slice + bypass rule** the new detector adds, on three independent grounds:

1. **The seam primitive keeps `mission_id[:8]` by design.** `branch_naming.py:139` (`_mid8` body) and
   `:182/:192/:408` (`resolve_mid8`/`resolve_transaction_mid8`) all legitimately slice `mission_id[:8]`.
   WP02 correctly sanctions `branch_naming.py` as the seam home (the detector already skips `_SEAM_REL`),
   so these are covered by the *home exemption*, not an allow-list entry. **OK — but only because the home
   exemption exists; "empty allow-list" must not be read as "zero sanctioned slices".**

2. **`mission_runtime/context.py` is a SECOND sanctioned slice home, and it is real.**
   `context.py:99/102/112` slice `mission_id[:8]` inside `IdentityFragment` ("computed here and nowhere
   else"). WP02-T019 explicitly names `branch_naming.py` **and** `mission_runtime/context.py` as the two
   sanctioned single-derivation homes. So the bypass rule's home set is **two files, not one** — this is
   correct in the WP, but it means the detector carries a permanent structural carve-out for `context.py`.
   The "empty allow-list" headline hides this; the honesty note must state both homes.

3. **`resolution.py:171` is the load-bearing case the claim breaks on.**
   `_mid8_from_primary_meta` (`resolution.py:146-172`) ends in `return str(raw_mission_id)[:8]`. This is a
   WP04-owned site (T012). **If WP04 routes it through `resolve_mid8`, the slice is gone and the
   allow-list stays empty for it.** But the WP04 prompt says "route via `resolve_mid8`, *preserving its
   decline/empty behavior*". `resolve_mid8(slug, mission_id=...)` returns `""` on decline — which matches
   `resolution.py`'s own `return ""` fall-throughs — so routing is contract-compatible and the slice can
   be deleted. **No residual slice is forced here IF WP04 fully substitutes.** The risk is a WP04
   implementer who keeps the slice "to preserve the `len(...) >= 8` guard" — that would force a WP02
   allow-list entry and break the empty claim. **Mitigation: WP02 must land after WP04 is *approved*, and
   the WP04 DoD already requires shadow deletion (T014). The gate handles this.**

### 1c. Does WP04 leave a slice at `resolution.py:171`?
Inspected: the function has three `return ""` paths and one `return str(raw_mission_id)[:8]`. A faithful
route replaces only the last with `resolve_mid8("", mission_id=str(raw_mission_id))` (which, per WP01-T002
equivalence, returns `mission_id[:8]` for a full id and `""` otherwise — **byte-identical to the current
`len>=8 ? [:8] : ""` two-branch logic**). So the route is clean and leaves **zero** residual slice. The
empty-allow-list claim survives *only if WP04 does this substitution faithfully*. Reviewer must verify.

### 1d. Verdict on ratchet-last
**Sound as a topology** (WP02 last is correct — it lets verification-by-deletion be the proof and avoids
per-WP allow-list churn). **The "empty allow-list" wording is an over-claim** and must be corrected to:
"allow-list empty of *route-sites*; two permanent sanctioned slice **homes** (`branch_naming.py`,
`mission_runtime/context.py`) are file-level carve-outs, not allow-list entries; `invocation_id[:8]` is
excluded by name; the deferred `feature_dir.parent.parent` repo-root class is out of scope." WP02-T020
already drafts most of this honesty note — it just must not be summarized as "zero sanctioned slices".

**MUST be allow-listed / carved out (binding list for the WP02 implementer):**
- `branch_naming.py` — whole-file home (already `_SEAM_REL`).
- `mission_runtime/context.py` — `IdentityFragment` home (T019 names it; must be in the bypass-rule home set).
- `invocation/executor.py:469` (`invocation_id[:8]`) — foreign identity domain, excluded by name (T020).
- **NOT** `worktree_allocator.py` — see §2c/§4: it is an *un-owned* live `mid8()` caller that, if WP01
  lands without it being routed, becomes either an ImportError (best case, loud) or a bypass-rule finding
  (if "fixed" with an inline slice). This is the real hole.

---

## 2. Ownership disjointness — VERIFIED disjoint, with one out-of-band hazard

### 2a. No two WPs share an `owned_files` path — CONFIRMED
Full extraction of all seven WPs' `owned_files` and `create_intent`: **every path is unique.** No source
file or test file is double-claimed. `lanes.json` write_scopes mirror this exactly (lane-a..g disjoint).
The "only WP01 edits `branch_naming.py`" invariant is **real** — `branch_naming.py` appears in WP01 only;
no other WP lists it. WP02's bypass rule *references* `branch_naming.py`/`context.py` as sanctioned homes
but does not *edit* them, so no ownership conflict. Disjointness holds.

### 2b. The `agent/mission.py` god-module — single-owner, OK
WP04 owns the whole 3k-line `cli/commands/agent/mission.py` for a one-line change at `:772`. No other WP
touches it. The WP04 prompt explicitly fences it ("change ONLY line ~772; do not refactor"). This is the
documented #1623-class no-expand rule. **Disjoint and correctly fenced** — the whole-file ownership is the
only way to grant the one-line edit under the lane model; acceptable.

### 2c. The disjointness HOLE: `worktree_allocator.py` is a live `mid8()` caller owned by NOBODY
This is the headline ownership/sequencing defect. Three external modules import the soon-to-be-private
`mid8` from the seam:
- `core/worktree.py:364,367` → **owned by WP05** (lane-e) — WP05 removes the call. ✓
- `core/mission_creation.py:28,321` → **owned by WP05** (lane-e) — WP05 removes the call. ✓
- `lanes/worktree_allocator.py:28,169` → **owned by NO WP.** ✗

The plan's IC-05 blast-radius analysis *names* this third consumer ("1 consumer
`lanes/worktree_allocator.py:169` — routed to `resolve_mid8` by IC-02"), but the IC-02 → WP03/WP04
decomposition **dropped it**: it is in neither WP03's nor WP04's `owned_files`, and in no `lanes.json`
write_scope. After WP01 renames `mid8`→`_mid8` and removes it from the importable surface,
`from specify_cli.lanes.branch_naming import lane_branch_name, mid8, ...` at `worktree_allocator.py:28`
becomes an **ImportError at module import time** — and the allocator is *the module that builds every lane
worktree*. This is a self-referential failure: the broken import can wedge `spec-kitty implement` for
*later* lanes of this very mission.

**Severity:** merge-blocker for the mission's internal coherence (the seam rename is incomplete) and a
latent runtime break. **Fix options (pick one before implement):**
- (a) Add `src/specify_cli/lanes/worktree_allocator.py` to **WP04** `owned_files` + `lanes.json` lane-d
  write_scope, with a T-task: route `:169` `mid8(...)` → `resolve_mid8("", mission_id=lanes_manifest.mission_id)`
  and drop `mid8` from the `:28` import. (WP04 is the "direct sites" WP and already depends on WP01 — the
  natural home.) **Recommended.**
- (b) Fold it into WP01 itself (WP01 is the only WP that *knows* the rename); but that crosses WP01's
  authoritative-surface (`lanes/branch_naming.py` only) and would make WP01 edit a consumer — less clean.
- (c) Leave it and let WP01 keep a thin public `mid8` alias — rejected: it defeats FR-010's single-door SSOT.

Until this is owned, the empty-allow-list claim (§1) is *also* at risk: if an implementer "fixes" the
ImportError by inlining `lanes_manifest.mission_id[:8]` at `:169`, that is exactly the bypass-rule finding
WP02 forbids → WP02 would have to allow-list it → claim broken. **Route it, don't inline it.**

---

## 3. Flatten safety for the implement loop — SAFE

`meta.json` has **no `coordination_branch` key** (flatten confirmed; HEAD commit "Flatten mission topology
(coord split-brain)"). The allocator handles both topologies explicitly:
- `worktree_allocator.py:157` `coordination_branch = _read_coordination_branch(...)` → `None` for this
  mission → falls to the **legacy branch** (`:174-178`): parents each lane on `lanes_manifest.mission_branch`
  (`kitty/mission-naming-identity-routing-rider-01KV7SFD`) ensured from `target_branch`
  (`feat/naming-rider-3-2-1`). This is the documented, tested legacy path.
- `implement.py:677,711,731` also branch on the missing `coordination_branch` and take the legacy
  transaction path with an explicit "(legacy path -- mission has no coordination_branch)" notice.

So `spec-kitty implement WP##` will allocate per-lane worktrees from `lanes.json` correctly without a coord
branch. **No flatten-induced break of the implement/merge loop for the normal case.**

**One flatten-adjacent caveat (not a blocker):** the sparse-checkout registration at `:165-173` calls
`mid8(lanes_manifest.mission_id)` — the *same* orphaned caller as §2c. On the legacy path it is guarded by
`try/except ValueError`, but it is **not** guarded against the `ImportError` that the WP01 rename
introduces (the import is module-level at `:28`). So the §2c fix is *also* what keeps the flatten legacy
path working. The "new atomicity invariants" warning refers to `_current_head`/rollback (#1915) at
`:230+` — that machinery is topology-agnostic and unaffected by the flatten.

---

## 4. Dependency-merge for WP02 (3-lane dependent) — HANDLED by the allocator, with the §2c rider

WP02 (lane-b) `depends_on_lanes: [lane-c, lane-d, lane-e]` (WP03/WP04/WP05). Two distinct mechanisms,
both present:

1. **Status gate (claim-time):** `dependency_readiness_for_wp` (`core/dependency_graph.py:50`) blocks
   claiming/implementing WP02 until every dependency is `approved` or `done`. So WP02 **cannot start before
   WP03+WP04+WP05 are approved** — exactly the ordering the plan wants. The gate is independent of the
   merge mechanic and is not weakened by the flatten.

2. **Cross-lane code propagation (#1684 class):** `_merge_dependency_lane_tips` (`worktree_allocator.py:183`
   fresh-path, `:143` reuse-path) merges each `depends_on_lanes` tip into WP02's worktree, ordered by
   `(parallel_group, lane_id)`. So WP02's worktree base **does contain all three lanes' changes** — the
   #1684 hazard is *already mitigated* in current code (both fresh and reuse paths). `DependencyLaneMerge
   ConflictError` is raised (not silently skipped) if a tip can't auto-merge — loud, recoverable.

   **Conflict-surface check:** WP03/WP04/WP05 own **disjoint** files (§2a), so the three dep tips merge
   into lane-b without content overlap among themselves. WP02 itself edits only
   `tests/architectural/test_no_worktree_name_guess.py`, which none of the deps touch. So the 3-way
   dependency merge into lane-b is **conflict-free by construction.** This is the well-behaved case for
   #1684, not the pathological one.

**WP02 dependency-merge verdict: handled, low-risk** — *provided* §2c is fixed. If `worktree_allocator.py`
is left orphaned, every lane allocation (including lane-b's own and its dep-tip merges, which run inside the
allocator) imports the broken module → the dependency merge can't even execute. §2c is the lever for both.

---

## 5. Summary of required adjustments (before `/spec-kitty.implement`)

| # | Finding | Severity | Fix |
|---|---------|----------|-----|
| F-1 | `lanes/worktree_allocator.py:28,169` (`mid8` import + call) orphaned from the WP01 rename — owned by no WP | **BLOCKER** | Add file to WP04 `owned_files` + lane-d write_scope; route `:169`→`resolve_mid8`, drop `:28` import alias |
| F-2 | WP02 "empty allow-list" DoD over-claims; two permanent slice **homes** (`branch_naming.py`, `mission_runtime/context.py`) exist | Medium | Reword DoD/honesty note: empty of *route-sites*; two file-level home carve-outs; not "zero sanctioned slices" |
| F-3 | `resolution.py:171` slice must be *fully* substituted by WP04 (not preserved alongside the guard) or it forces a WP02 allow-list entry | Low (gate-caught) | WP04 reviewer verifies the slice is deleted, relying on `resolve_mid8` `""`/`[:8]` equivalence |

Sequencing topology (WP01 → {WP03,WP04,WP05} → WP02; WP06/WP07 independent), ownership disjointness, the
flatten legacy path, and the WP02 3-lane dependency merge are all **sound**. The single structural defect is
F-1 (a dropped consumer the plan itself named), which also underpins the F-2/F-3 risk and the flatten
sparse-checkout path.

**One-line verdict: sequencing NEEDS-ADJUSTMENT** — fix F-1 (orphaned `worktree_allocator.py` consumer) and
soften the WP02 empty-allow-list wording (F-2); topology/ownership/flatten/dependency-merge are otherwise SOUND.
