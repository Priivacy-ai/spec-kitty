# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

**Decisions already recorded elsewhere**: three formal decision records live in
`../decisions/` (`01KY7AKX…` hook site, `01KY7AKY…` resolver shape, `01KY7AKZ…` retirement
strategy) and eleven research findings in `../research.md`. This file captures the rationale
that has no other home, and appends as implementation proceeds.

---

## Entries

2026-07-23 — WP01 / IC-01 (#2795) — Decision: fix the claim-time consolidation blocker on the
**consolidation side** (`git/ref_advance.py::_dirty_entries`) by classifying a vcs-lock-only
`meta.json` change as non-destructive churn — the fix **DROPS** the lock at the resync
`reset --hard`, it does **not** commit it. Alternatives considered: (a) commit the VCS lock at
claim time in `implement.py::_ensure_vcs_in_meta`; (b) extend the claim-side
`_drop_vcs_lock_only_meta` family in `implement_cores.py`. Rationale: the reproduced mechanism
(below) is a *consolidation* refusal, so the robust, topology-agnostic fix (C-004 — the write
lands on the PRIMARY partition, not coord) belongs where the block fires. Dropping rather than
committing keeps the existing "the lock stays uncommitted, is regenerated on the next claim"
semantics (C-010, behaviour-preserving) and — decisively — means **this fix does NOT pre-empt
IC-07(d)/WP14**: `implement_cores.py`'s `_drop_*` sibling dedup is untouched, and no VCS lock is
committed anywhere. WP14 can slice IC-07(d) exactly as planned. `implement.py` and
`merge/preflight.py` (both owned by this WP) were left unmodified: the reproduction proved the
block is entirely in the ref-advance dirty scan; touching the other two would have been
speculative scope.

- **Reproduced mechanism (FR-011, live, not the reported cause).** The issue reported a *dirty
  coordination `meta.json`*; **REFUTED**. Real symbols: the claim's `_ensure_vcs_in_meta` →
  `mission_metadata.set_vcs_lock` writes the VCS-type lock into the `feature_dir` that
  `_detect_wp_context` resolves via `placement_seam(repo_root, mission_slug).read_dir(SPEC)` — a
  **PRIMARY-partition** kind — so the lock lands in the *primary* checkout's
  `kitty-specs/<slug>/meta.json` (`implement.py:1166` write-target, `:1760` call site;
  `mission_metadata.py:512` writer). Consolidation's `advance_branch_ref`
  (`git/ref_advance.py`, called from `merge/ordering.py:467` and
  `coordination/commit_router.py:935`) then refuses in `_dirty_entries` because the tracked
  ` M …/meta.json` is misclassified as destructive local state. Live RED evidence: the repro
  raised `RefAdvanceDirtyWorktreeError` naming ` M kitty-specs/issue-2795-coord/meta.json` (a
  PRIMARY path, not a coord-worktree path) with `→ VCS locked to git in meta.json` on stdout.
  Regression: `tests/regression/test_issue_2795_claim_blocker.py` (RED→green through the real
  `_ensure_vcs_in_meta` + `advance_branch_ref` symbols; DIRECTIVE_041).
- **C-002 fallback NOT taken.** A real reproduction + fix was found within the timebox, so
  neither fallback (a) pin `auto_commit=True` nor (b) self-flatten was needed.

2026-07-23 — Decision: retire all eight exemption mechanisms rather than prove the seam on two
or three. Alternatives: owner + 2–3 provable retirements behind a ratchet; owner + ratchet with
no retirements. Rationale: operator chose full class closure; a partial retirement leaves the
pattern alive and the next contributor still finds "add to the list" as the path of least
resistance. Accepted cost: a materially wider blast radius, mitigated by the strangler
decomposition and constraint C-010.

2026-07-23 — Decision: resolvers become **total**, not fallback-based. Alternatives: scope
NFR-001 to coord-resolved paths and bless the flat `feature_dir` fallback as a legitimate leg;
or convert to fail-loud unconditionally. Rationale: operator directive that `flattened` is
pre-topology residue to be steadily removed, not reinforced — *do not strengthen ducttape*. The
fallback conflated "flat topology, primary dir IS the home" with "coord home declared but not
materialised". Making resolution total separates them with no special case, and collapses
`None` to one meaning that raises.

2026-07-23 — Decision: run the mission on coord topology despite the risk. Alternatives:
flat/`LANES` with coord evidence from the shared test fixture (the pre-spec squad's
recommendation). Rationale: operator chose live field evidence over fixture-only evidence.
Mitigation is structural rather than argumentative — C-002 requires IC-01 (#2795) to be fixed
before any WP reaches its terminal step, since the mission would otherwise be blocked at merge
by the defect it is fixing.

2026-07-23 — Decision: place merge-phase re-verification in a new `acceptance/merge_phase.py`
rather than inline in `merge/executor.py`. Alternatives: inline. Rationale: keeps invariant
logic in the acceptance package, minimises footprint on a 1433-LOC module that is already the
duplicate-compensator crime scene, and — decisively — lets IC-04 and IC-07 own disjoint files,
which they must, since IC-07 rewrites merge-surface exemptions.

2026-07-23 — Decision: drop `review/pre_review_gate.py` from scope entirely after discovering a
concurrent sibling mission (`scopesource-gate-followup-01KY6S9P`) deleting ~450 LoC from it.
Alternatives: sequence our edits after theirs; negotiate a shared branch. Rationale: none of
this mission's live defects lives in that file — it was on the list only because the seam should
*eventually* cover every gate. Deferring the pre-review-gate migration took the overlap on the
sibling's highest-risk file to zero and made our remaining work cheaper, since their port
decoupling is a better substrate.

2026-07-23 — Decision: the deferred-invariant check is named **post-consolidation**, not
"deferred to merge". Alternatives: keep the merge wording; name it post-merge. Rationale: `merge`
already spends three senses here (lane consolidation / branch integration / publish), so
"deferred to merge" never said which one it waited for. The first tree on which a mission-wide
fact can be true is the mission branch after lane consolidation — that is the `CONSOLIDATED`
surface. Same disambiguation discipline that produced `CONSOLIDATED` over `MERGED`.

2026-07-23 — Decision: a violated deferred invariant fails the **verification Op**, not the
consolidation. Alternatives: fold the check into `spec-kitty merge` as an abort trigger.
Rationale: adding a new abort path to the consolidation transaction while IC-06 is collapsing its
two compensators into one is asking for trouble. Running after consolidation means nothing is
half-applied and there is no interaction with the rollback rework. Blast radius is bounded — the
consolidated tree is the mission/PR branch, not the primary branch, so a violation blocks the PR.

2026-07-23 — Decision (operator): the verification needs **no dedicated CLI verb**. It is
dispatched as an ordinary governed Op through the canonical surface (`spec-kitty dispatch`,
closed via `profile-invocation complete`), single-agent or squad-based like any other. What makes
it distinctive is *when* it runs and *what* it checks, not bespoke command surface. Corrects an
earlier framing of mine that treated "new CLI verb vs fold into wrap-up" as an open question —
it was a false dichotomy.

2026-07-23 — Decision (operator): post-consolidation verification is **not** enforced by the
mission loop. Alternatives: block the matrix from reaching a terminal verdict while deferrals
remain; fire it from the post-merge retrospective terminus. Rationale: the acceptance matrix has
exactly one reader (`gates_core.py:311`) and it runs pre-consolidation, so the recommended
enforcer was circular — it would block at the gate that created the deferral and which by design
must not block on it. Enforcement moves to a CI consistency check on the PR, where the
consolidated tree and the artifact are both readable. Accepted trade-off: between assignment and
the PR check the invariant is genuinely unverified — honest and visible, rather than false and
invisible.

2026-07-23 — Decision (operator): the deferral **discloses its own contract** at assignment time.
Rationale: Spec Kitty runs in other people's repositories where this project's CI check does not
exist. Shipping an enforcement model that only works upstream, silently, would export the exact
failure this mission removes — a gate that looks authoritative and verifies nothing. The tool must
say, at the moment it assigns the status: the loop will not verify this; here is the gate you need.
