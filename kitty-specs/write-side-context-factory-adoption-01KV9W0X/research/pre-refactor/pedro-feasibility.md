# Pedro — Clean-Before-Touch Feasibility & Sequencing (Mission B)

**Author:** python-pedro (profile-loaded; pragmatic implementer, bounded, TDD-first, ruff/mypy ≤15;
DIR-024 locality, DIR-025 boy-scout, DIR-030 quality-gate, DIR-034 test-first)
**Date:** 2026-06-17
**Mission:** `write-side-context-factory-adoption-01KV9W0X` (HEAD `efb28158f`, stacked on Mission A)
**Lens:** *feasibility + sequencing of behaviour-preserving pre-refactors* — which clean-before-touch
moves are SAFE-NOW (bounded, equivalence-only), which order eases each subsequent adoption, which
balloon scope and stay OUT.

---

## 0. Input status (read before trusting the verdicts)

The operator brief points me at `research/pre-refactor/{randy-code-smells.md,paula-test-smells.md}`.
**Those two files do not exist yet on HEAD** — the `pre-refactor/` dir is empty. Present instead are
the *adoption* inventories: `research/reduction-census.md` (randy) and `research/write-site-inventory.md`
(alphonso). So this assessment derives the candidate pre-refactors **from the live surfaces + those two
inventories**, grounded by reading the actual code at each site. When randy's/paula's pre-refactor
smell census lands, re-check §1 rows against it — but the SAFE-NOW set below is verified against the
real bodies on HEAD, not a paraphrase.

**Code-grounded facts I verified by reading the surfaces (not just the inventory):**
- `status/emit.py::_feature_status_lock_root` (:388-424) and
  `status/work_package_lifecycle.py::_repo_root_for_lock` (:55-89) are **byte-identical bodies** — same
  topology classifier, same `resolve_canonical_root`, same 3 `.parent.parent` fallbacks; the docstrings
  even cross-reference each other. This is the highest-confidence duplication in the mission.
- `coordination/status_transition.py::_repo_root_for_feature` (:49-54) is a **different, simpler** walk
  (no topology classifier — bare `feature_dir.parent.parent`). It is NOT the same body as the
  emit/wpl pair. Do not assume "all five root walks are the same helper."
- A shared home already exists: `workspace/root_resolver.py` (`resolve_canonical_root`) — the
  emit/wpl pair already *delegates* to it for the coord/lane arm. The residual is only the
  primary/ad-hoc fallback shape.
- Each touched helper has an existing test module
  (`tests/status/test_emit.py`, `test_work_package_lifecycle.py`, `test_lifecycle_events.py`,
  `tests/specify_cli/coordination/test_worktree_topology.py`) — so characterization tests have a home;
  no new scaffolding seam needed.
- `lanes/persistence.py::resolve_lanes_dir` (:23) exists and is already the single lanes-dir seam.
- `status/aggregate.py` `surface=` param is at :199, dead branch downstream.

---

## 1. Feasibility verdict per candidate pre-refactor

Each row: the clean-before-touch move, my verdict, the concrete reason, and the **characterization
test** that pins behaviour so the refactor is provably equivalence-only (TDD red-before-touch).

| # | Candidate pre-refactor | Verdict | Reason | Characterization test (write FIRST, must stay green) |
|---|---|---|---|---|
| **PR-1** | **Extract the byte-identical lock-root resolver (emit W9 ≡ wpl W10) into one shared helper** in `workspace/root_resolver.py` (e.g. `resolve_status_lock_root(feature_dir, repo_root)`), both call sites delegate. | **SAFE-NOW** | Pure de-dup of two *literally identical* bodies into the module that already owns `resolve_canonical_root`. No behaviour change; no factory touch (C-001 untouched — this is a pre-existing-helper consolidation, not adoption). Removes ~25 LOC of duplication and means the later FR-001 adoption flips **one** helper, not two divergent copies. | Parameterize over the three topologies (primary / coord-worktree / lane-worktree) + the `repo_root is not None` short-circuit + the `WorktreeRegistryUnavailable`/`WorkspaceRootNotFound` fallback arms. Assert emit-result == wpl-result == new-helper-result for every input class. Lives in `test_emit.py` + `test_work_package_lifecycle.py`. |
| **PR-2** | **Add topology-true characterization tests** for all 5 root-walk sites (emit, wpl, lifecycle_events, store, status_transition `_repo_root_for_feature`) **before any adoption** — full 26-char ULID, real coord-worktree + submodule fixtures (NFR-002). | **SAFE-NOW** | Test-only, zero src risk, and it is the *gate* that makes every later deletion provable (NFR-003 verification-by-deletion needs a green behavioural net first). This is the single highest-ROI pre-move: it converts "the inventory says equivalent" into "the suite proves equivalent." | This IS the characterization net. Build the topology-true fixtures once (they're reused by the adoption WPs + the NFR-006 simple-case test). Assert current resolved root per site per topology; freeze as the before/after oracle. |
| **PR-3** | **Normalize the `store.py::_find_mission_specs_root` ancestor scan** (:119-130) to early-return form / extract the `candidate`-vs-`two_up` decision into a named predicate. | **SAFE-NOW (thin)** | Small, local, behaviour-preserving readability tidy in the file FR-001 will touch anyway. Low value alone, but if PR-2's net is in place it is free boy-scout (DIR-025). Keep it trivial — do not "improve" the best-effort fallback semantics. | Covered by PR-2's `store.py` characterization rows (slug-dir / deeper-nesting / non-kitty-specs fallback). |
| **PR-4** | **Retire `prompt_source` fragment + the `aggregate.py` `surface=` read-param** (FR-006) **as a standalone first deletion**. | **SAFE-NOW** | randy + alphonso both grep-proved **0 readers** on both paths; the two real `MissionStatus.load()` callers never pass `surface=`. Pure dead-code deletion, no behaviour change (SC-004). Doing it FIRST shrinks the surface every later WP reads and removes a misleading "second way to inject a surface" before the write-surface adoption lands. | A "no caller passes `surface=` / `prompt_source` has no consumer" guard test + the existing `MissionStatus.load()` callers' tests staying green. Deletion is its own proof when the suite is green. |
| **PR-5** | **Pre-extract a placement-compose helper** in `core/worktree.py` for the duplicated `worktree_path / KITTY_SPECS_DIR / branch_name` join (:384 reuse arm, :396 create arm) into one local function, *before* swapping it to the factory projection. | **SAFE-NOW (thin)** | The join is duplicated across two arms; collapsing to one local helper first is behaviour-preserving and makes the subsequent FR-002 swap a one-line change at one site instead of two. Bounded to one file. | Parameterized test: reuse-arm vs create-arm yield the same `feature_dir` for a given `(worktree_path, branch_name)`; assert against current output. |
| **PR-6** | **Pre-unify `status_transition.py::_repo_root_for_feature` toward the canonical resolver** (make the bare `.parent.parent` walk delegate to `resolve_canonical_root` like emit/wpl already do). | **RISKY** | This *looks* like "make the 3rd walk match the other two," but `_repo_root_for_feature` feeds `_identity_for_request` → `destination_ref` → the **write target** on the coord path. Changing what root it computes can shift `_current_branch(repo_root)` and the transaction-dir existence check — i.e. it touches the idempotency hotspot (randy §6) and the #1716-adjacent identity assembly. Not equivalence-only. | Would need the full topology-true write-target before/after on-disk-target test (FR-004/NFR-004) — which belongs to the **adoption** WP-COORD, not a pre-refactor. Leave it to IC-COORD under its own guard. |
| **PR-7** | **"Tidy" the `_identity_for_request` second-factory body** (re-order/extract the meta-read + mid8 + destination_ref assembly) before adoption. | **SKIP** | This is the second parallel factory and the entrance to the #1716 topology-authority root. Any pre-refactor here drifts into the deferred ~2094-LOC selection authority and risks coord on-disk churn (NFR-004). The adoption itself (IC-COORD) reduces this body by *consuming* the fragment — there is no behaviour-preserving pre-move that helps; pre-touching only enlarges the conflict surface on the highest-risk file. | n/a — out of bounds. |
| **PR-8** | **Refactor / unify `_read_contract_from_transaction_target`'s coord/primary selection ladder** (S2). | **SKIP** | This is the **#1716 topology-authority root** the operator parked (decision `01KV8Q49…`). Explicitly Out of Scope (spec C-003, plan D-1). Any "cleanup" here is scope-balloon by definition. See §3. | n/a — OUT. |

**Tally: 5 SAFE-NOW (PR-1, PR-2, PR-3, PR-4, PR-5), 1 RISKY (PR-6), 2 SKIP (PR-7, PR-8).**
Of the SAFE-NOW set, PR-3 and PR-5 are *thin* (free boy-scout once the net exists); PR-1, PR-2, PR-4
are the substantive ones.

---

## 2. Sequencing (clean first so each next step gets easier)

Recommended order — strictly increasing risk, each step lowering the cost of the next:

1. **PR-2 first (characterization net).** Test-only, zero risk, and it is the precondition that makes
   *every* later deletion provable. Build the topology-true fixtures (26-char ULID + real
   coord-worktree + submodule) here once; they are reused by the adoption WPs and the NFR-006
   simple-case test. **Nothing else should land before this.**
2. **PR-4 (dead-code retirement).** Independent of the root-walk work, 0 readers, pure deletion.
   Shrinks the surface (`prompt_source`, `surface=`) before anyone reads `aggregate.py`/`resolution.py`
   for adoption. Safe to run in parallel with PR-2 conceptually, but order it second so the green
   suite from PR-2 backs the deletion.
3. **PR-1 (collapse emit≡wpl into one shared lock-root helper).** With PR-2's net green, this de-dup is
   provably equivalence-only and means FR-001 later flips **one** helper, not two. Lands in
   `workspace/root_resolver.py` (the existing home).
4. **PR-5 (worktree placement-compose helper)** and **PR-3 (store ancestor-scan tidy)** — the two thin
   boy-scout tidies, each bounded to a single file FR-001/FR-002 will touch anyway. Either order.
5. *(then the adoption WPs proper — not pre-refactors).*
6. **PR-6 / PR-7 / PR-8 — do NOT pre-touch.** Their cleanup only happens *as* the adoption (IC-COORD)
   under the write-target idempotency guard, or stays deferred (#1716).

### Ownership / merge-hazard flag (parallel-lane model)

The plan's adoption partition is **one owned file per WP** (overlap-free). The pre-refactors must
respect the same partition or they become cross-lane merge hazards:

- **PR-1 is the one ownership hazard.** It edits **three** files —
  `status/emit.py` (WP-EMIT), `status/work_package_lifecycle.py` (WP-WPL), and
  `workspace/root_resolver.py` (un-owned by any adoption WP). If WP-EMIT and WP-WPL run as parallel
  lanes, PR-1 straddles both their owned files → merge conflict / split-brain risk. **Resolution:**
  land PR-1 as a **single pre-WP that completes and merges BEFORE WP-EMIT/WP-WPL fan out** (see §4),
  so by the time the adoption lanes open, both files already call one helper and each lane edits only
  its own call site. Do **not** let PR-1 run concurrently with the EMIT/WPL adoption lanes.
- **PR-2** touches only `tests/` — no src ownership overlap, but it seeds fixtures the adoption WPs
  import; land it first so lanes consume a stable fixture module.
- **PR-3, PR-4, PR-5** are each single-file (store / aggregate+resolution+context / worktree) and align
  with WP-STORE / WP-RETIRE / WP-WT owned files respectively — **no cross-lane hazard** if folded into
  (or sequenced just ahead of) those WPs.

---

## 3. Scope guard — what looks like good cleanup but stays OUT

These are the traps. They read as "while we're in here, let's unify the topology selection" — that is
exactly the deferred authority.

- **`coordination/status_transition.py::_read_contract_from_transaction_target` (S2, :439-475)** — the
  coord-worktree-vs-coord-branch-ref-vs-primary **selection ladder**. This IS the **#1716
  topology-authority root (~2094 LOC)** the operator parked (decision `01KV8Q49WEG9RRKCEZ3XYN5DWP`;
  spec C-003 / Out-of-Scope; plan D-1). Mission B may consume the *output field*
  (`status_surface.status_write_dir`) but MUST NOT rewrite the *selection*. **Any pre-refactor here = OUT.**
- **`_identity_for_request` write-target tidy (PR-7)** — even a "harmless reorder" of the meta-read /
  `destination_ref` assembly drifts into the same authority and risks coord on-disk churn (NFR-004).
  The adoption reduces this body by consuming the fragment; there is no safe pre-move. **OUT.**
- **`_repo_root_for_feature` "make it match emit/wpl" (PR-6)** — tempting symmetry, but it feeds the
  write target and is therefore not equivalence-only. Defer to IC-COORD under its idempotency guard.
  **Not a pre-refactor.**
- **The flattened-arm `destination_ref` divergence** (`_current_branch` HEAD vs `target_branch`,
  randy §6) — this is a **latent-bug-fix, not a no-op**. It is the *adoption's* job (FR-004) behind the
  NFR-006 simple-case + NFR-004 before/after tests. **Never** smuggle it into a "behaviour-preserving"
  pre-refactor — by definition it changes the write target on off-target-branch checkouts.
- **`branch_naming` / `mission_runtime/` factory internals** — C-001: consume, do not absorb or
  "clean." Out for both adoption and pre-refactor.

---

## 4. Mission-shape recommendation: how should the clean-before-touch land?

**Recommendation: (a) its own small pre-WPs that land FIRST in Mission B — NOT a separate pre-mission,
NOT blanket boy-scout-in-each-WP — but with PR-3/PR-5 folded as boy-scout into their owning adoption WP.**

Reasoning against each alternative:

- **(b) separate pre-mission — NO.** The SAFE-NOW set is ~25-40 LOC of de-dup + a fixture/test net +
  one dead-code deletion. That does not justify a mission's spec/plan/tasks/merge overhead, and a
  separate branch would have to stack on Mission A *and* be re-stacked under Mission B — pointless
  rebase churn. The work is intrinsic to Mission B's surface.
- **(c) fold everything into each adoption WP's boy-scout step — NO for the cross-file ones.** PR-1
  (emit≡wpl collapse) and PR-2 (shared fixtures) span multiple owned files / are consumed by multiple
  lanes. Folding them into individual WP boy-scout steps means two lanes independently editing the same
  shared helper / fixtures → the exact merge hazard §2 flags. Boy-scout is for *local* tidies only.

**Concrete shape:**

- **Pre-WP-NET (PR-2):** topology-true fixtures + characterization tests for all 5 root-walk sites.
  Test-only. Lands and merges first. Every adoption WP imports these fixtures.
- **Pre-WP-DEDUP (PR-1):** extract the byte-identical lock-root resolver into `workspace/root_resolver.py`;
  point emit + wpl at it. Lands and merges **before** WP-EMIT / WP-WPL fan out (the §2 ownership-hazard
  resolution). After this, WP-EMIT and WP-WPL each edit only their own single call site → partition
  stays clean.
- **Pre-WP-RETIRE (PR-4):** the FR-006 dead-code deletion — this is **already its own WP (WP-RETIRE)**
  in the plan; just sequence it early (it has no dependency on the adoption and shrinks the surface).
- **PR-3 (store tidy) and PR-5 (worktree placement helper):** **fold as boy-scout into WP-STORE and
  WP-WT** respectively — they are single-file, local, and land naturally inside the WP that already owns
  the file. No separate pre-WP.

Net: **two new tiny pre-WPs (NET, DEDUP) sequenced first**, PR-4 ridden by the existing WP-RETIRE
(early), and the two thin tidies as in-WP boy-scout. This keeps the parallel-lane partition overlap-free
and makes every adoption deletion provable against a pre-existing green net.

---

## Bottom line

**5 pre-refactors are SAFE-NOW** (PR-1 emit≡wpl de-dup, PR-2 topology-true characterization net,
PR-3 store-scan tidy, PR-4 FR-006 dead-code retirement, PR-5 worktree placement-compose helper);
**1 RISKY** (PR-6 unifying `_repo_root_for_feature` — feeds the write target, not equivalence-only);
**2 SKIP** (PR-7 `_identity_for_request` tidy, PR-8 the S2 selection ladder — both the deferred #1716
topology authority).

**Recommended sequence:** PR-2 (net) → PR-4 (dead-code) → PR-1 (emit≡wpl collapse, merged before
WP-EMIT/WP-WPL fan out) → PR-3 + PR-5 (thin boy-scout in their owning WPs). PR-1 is the **one
ownership/merge hazard** (straddles WP-EMIT + WP-WPL owned files) — land it as a pre-WP that completes
*before* those lanes open.

**Scope guard:** keep the entire S2 selection ladder and any `_identity_for_request`/`_repo_root_for_feature`
write-target touch OUT — that is the parked #1716 ~2094-LOC authority; the flattened-arm `destination_ref`
divergence is a latent-bug-fix owned by the adoption (FR-004), never by a "behaviour-preserving" pre-move.

**Mission shape:** land the clean-before-touch as **two tiny pre-WPs FIRST** (PR-2 net, PR-1 de-dup) +
PR-4 ridden by the existing WP-RETIRE, with PR-3/PR-5 as in-WP boy-scout — NOT a separate pre-mission,
NOT blanket per-WP boy-scout for the cross-file ones.
