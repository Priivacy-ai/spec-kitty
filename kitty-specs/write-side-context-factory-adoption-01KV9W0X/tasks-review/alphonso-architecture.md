# Alphonso — Architecture / Scope-Boundary / Ownership Review (Mission B WP decomposition, PRE-implementation)

**Reviewer:** architect-alphonso (profile-loaded: DIR-001 architectural integrity / one-owning-module,
DIR-003 decision-documented, DIR-031 bounded-context translation, DIR-032 conceptual alignment).
**Date:** 2026-06-17. **Mission:** `write-side-context-factory-adoption-01KV9W0X`.
**Branch:** `feat/write-side-context-factory-adoption`. **HEAD verified:** `eba2448d8`
(inventory pinned `efb28158f`; the only commits between the two are the planning/`chore` commits — **no
source drift**, so every line ref in the inventory/prompts is still valid; verified per-site below).

**Lens:** ownership partition · C-001 no-new-authority / scope creep into #1716 · C-007 per-diff-type routing ·
factory-projects-what-prompts-consume · sequencing/dependency soundness. Every claim below was checked
against the code on HEAD, not the planning prose.

---

## What is SOUND (verified, so the implementers can trust it)

- **Fragment fields exist and resolve as claimed.** `context.py:130 destination_ref`, `:144 primary_root`,
  `:162 status_write_dir` all present. `resolution.py:698 primary_root = get_main_repo_root(repo_root)`;
  `:724-728 status_write_dir = _resolve_status_surface_dir(...)`; `:705-722 destination_ref` =
  `CommitTarget(coord, COORDINATION)` else `CommitTarget(target_branch, FLATTENED)`. **C-007 surface
  correctness CONFIRMED**: `_resolve_status_surface_dir` (`:586-616`) delegates to `resolve_status_surface`
  and **fails closed via `ActionContextError`** (`:604-611`) rather than degrading to `primary_root` — the
  read-primary/write-coord pattern is real, not aspirational. The inventory's pivotal Q3 verdict is accurate.
- **D-4 byte-identity CONFIRMED.** `emit.py::_feature_status_lock_root` (`:412-424`) and
  `wpl::_repo_root_for_lock` (`:75-89`) are character-for-character identical bodies. Merging IC-EMIT+IC-WPL
  into WP02 and extracting one helper FIRST is the architecturally correct move (avoids the one real
  cross-file ownership hazard).
- **`_repo_root_for_feature` (R5) is correctly flagged as a DIFFERENT, simpler walk.** Verified at `:49-54`:
  a bare `.parent.parent`, NOT the topology-aware emit/wpl body. WP05 T021 explicitly warns "do not assume
  it shares their helper" — accurate, and the reason pedro's PR-6 was held back into the guarded IC-COORD.
- **Ownership partition is overlap-free at the file level.** No two WPs list the same `owned_files`.
  `implement.py` is owned ONLY by WP06 (verified). `mission_runtime/{resolution,context}.py` appear ONLY
  under WP07 (deletion). `status_transition.py` (R5+S1) is solely WP05. Clean.
- **FR-006 retirement is safe.** `prompt_source` has 0 consumers repo-wide (verified). No `MissionStatus.load`
  caller passes `surface=` (verified across all callsites). WP07 atomically retiring the S-2/S-3
  contract-encoding tests is the right call.

---

## BLOCKER

### B-1 (WP02/WP03/WP05 — the ownership partition is file-clean but the *adoption mechanism* is undecided, and it is the whole mission)

**The plan asserts the adoption is "an import, not a shared edit" (plan §Sequencing, §Implementation Concern
Map). That is architecturally false as written, and the gap is load-bearing.** Verified on HEAD:

- **None** of the five write-site files (`status/emit.py`, `work_package_lifecycle.py`, `lifecycle_events.py`,
  `store.py`, `coordination/status_transition.py`) import `mission_runtime`, hold an `ExecutionContext`, or
  carry an `action` token. `grep` for `mission_runtime|ExecutionContext|resolve_action_context|build_execution_context`
  across all five = **empty**.
- `build_execution_context(**fields)` is a pure assembly door (`resolution.py:91`) — it does NOT resolve
  fragments. The fragment *resolution* lives behind `resolve_action_context(repo_root, *, action: ActionName, ...)`
  (`:864`), which **requires an `action` from a fixed 11-token vocabulary** (`specify/plan/.../status`) and
  **raises `ActionContextError` with no silent fallback** on unresolvable context (`:879-883`).
- The deepest write site, `emit_status_transition`, is a 20-parameter orchestration hub
  (`emit.py:427`) called with `(feature_dir, repo_root, ...)` — no context, no action.

So "consume `workspace.primary_root` from the factory context" (WP02 T008, WP03 T013, WP05 T021) has **two
materially different implementations the plan never chooses between**:

- **Reading A (thread a context):** plumb a resolved `ExecutionContext` from the CLI boundary down through
  `emit_status_transition` and the transaction layer to these helpers. This is a **cross-file, cross-WP, into-
  the-CLI-layer refactor** — it would touch `cli/commands/agent/status.py`, the `transaction.py` plumbing, and
  the 20-param hub signature. That is emphatically NOT "an import," and it **breaks the stated owned_files
  partition** (WP02 would need to edit callers it does not own).
- **Reading B (narrow projection):** route each site to call the same underlying authority directly. Note
  `workspace.primary_root` **is literally `get_main_repo_root(repo_root)`** (`resolution.py:698`) — and the
  write sites *already import* `resolve_canonical_root`. So Reading B is `get_main_repo_root(repo_root)` at the
  callsite. This is clean and file-local — **but the fragment field stays 0-readers, so SC-002
  ("`workspace.primary_root` … 0 readers to load-bearing") is NOT met.** The verification-by-deletion is then
  vacuous w.r.t. the *fragment* (you proved value-equivalence to `get_main_repo_root`, not fragment adoption).

**There is exactly ONE precedent for a clean resolution:** `resolve_placement_only(repo_root, mission_slug)`
(`resolution.py:781`) — a narrow, WP-less, action-less projection entry point over the **same**
`_assemble_core_fragments` builder, explicitly documented as "NOT a parallel resolver (C-CTX-1)." It returns
only a `CommitTarget`. **There is NO equivalent narrow projection for `primary_root` or `status_write_dir`.**

The mission therefore almost certainly needs a `resolve_workspace_only` / `resolve_status_surface_only`
projection (same pattern as `resolve_placement_only`) so the deep helpers can read the fragment value without
the full `action` ceremony or a deep context-threading refactor. **That projection-entry decision is the
architectural keystone of the entire mission, and it is absent from plan.md, the inventory, and every WP
prompt.** Until it is made:
- the owned_files partition cannot be trusted (Reading A blows it up);
- SC-002 cannot be claimed (Reading B leaves the fragment unread);
- the "no new authority / C-001" boundary is ambiguous — a `resolve_*_only` projection is C-001-safe ONLY if
  it follows the `resolve_placement_only` "narrower entry over the same builder" pattern, and that must be
  stated, or an implementer will either (a) build a genuine second resolver, or (b) skip the fragment and
  call `get_main_repo_root` raw.

**Remediation (BLOCKER — resolve in plan before implement):** Add a decision (D-12) that pins the adoption
mechanism. Recommended: mirror `resolve_placement_only` with `resolve_workspace_only(repo_root, mission_slug)`
(returns `WorkspaceFragment` or `primary_root`) and a `resolve_status_surface_only(...)` if the surface write
needs it — both as **narrow projections over `_assemble_core_fragments`, explicitly not new resolvers**
(C-001). Then **the projection helpers live in `mission_runtime/resolution.py`, which is owned ONLY by WP07
(deletion).** This is a second ownership collision (see B-2). The plan must either (i) give the projection a
home WP, or (ii) confirm the projection already exists and I missed it (I did not find it). Every adoption WP
prompt must then say *which* entry point it calls and assert the fragment is genuinely read (SC-002).

### B-2 (WP07 / unassigned — `mission_runtime/resolution.py` is owned only for DELETION, but B-1's projection ADDS to it)

WP07 owns `mission_runtime/resolution.py` + `context.py` **for FR-006 deletion only** (correct per C-001).
But the B-1 fix (adding `resolve_workspace_only` / a workspace projection) would also land in
`resolution.py`. **No WP is authorized to ADD to `mission_runtime/`.** As written, if an implementer needs the
projection, they have nowhere to put it without violating the partition — they will improvise (likely inlining
`get_main_repo_root` at the callsite, i.e. silently choosing Reading B and failing SC-002).

**Remediation:** Once B-1's mechanism is chosen, assign the projection-entry addition to a specific WP (a new
WP00 "projection entry points," or fold into WP01 since it is the gate, or extend WP07's scope from
"deletion-only" to "FR-006 deletion + the C-001-safe projection adds"). The `owned_files` for that WP must
include `mission_runtime/resolution.py` for *addition*, and the C-001 rationale (narrow-projection-not-new-
resolver) must be in the prompt verbatim.

---

## SHOULD-FIX

### S-1 (contracts/behavioral-contracts.md — C-SURFACE contradicts the reversed D-2; stale write-target-OUT language)

`behavioral-contracts.md:28` (inside **C-SURFACE**) states: *"the write-**target** branch selection is OUT
(D-2)."* But D-2 was **reversed** (plan.md:51-58, commit `1447efdce`) to put FR-004 write-target **IN** scope,
and C-TARGET (`:40-47`) now governs it. C-SURFACE still carries the pre-reversal text. An implementer reading
C-SURFACE for WP05 gets a directly contradictory instruction vs C-TARGET + the WP05 prompt. This is exactly
the kind of stale-snapshot drift DIR-032 (conceptual alignment) exists to catch.

**Remediation:** Edit C-SURFACE line 28 to remove "the write-target branch selection is OUT (D-2)" and instead
cross-reference C-TARGET ("the write-**target** selection is governed by C-TARGET, FR-004, now IN scope"). The
idempotency clause ("MUST NOT change which on-disk directory a status event is written to") should stay but be
reconciled with C-TARGET's "the flat case writes to `target_branch` … the latent-bug-fix … is the intended
correction, proven, not silent churn." As written the two contracts disagree on whether the write target may
change.

### S-2 (WP05 — R5 `primary_root` adoption is a behavior change, not an equivalence swap; the prompt under-warns)

`_repo_root_for_feature` (`:49-54`) currently returns `feature_dir.parent.parent` for the coord/lane case —
a **non-canonical** root. `workspace.primary_root` is the **CWD-invariant canonical** root. For coord/lane
topology these can differ (that is the whole point of the canonical resolver). So routing R5 to `primary_root`
is a **value change under coord topology**, in the same risk class as the FR-004 `destination_ref` change —
yet the WP05 prompt frames R5 (T021) as a plain walk-deletion and reserves the "latent-bug / proven-not-churn"
framing only for the write-target (T023). randy's census (§6) explicitly says the *root* swaps are
idempotency-clean "for the now-routable subset" because they anchor locks/logs not write-targets — but R5
specifically feeds `_identity_for_request` → `destination_ref` selection, so its root value is **not** purely
a lock anchor.

**Remediation:** In WP05's T021, add the same equivalence obligation R5 carries that R1-R4 carry, AND a note
that under coord topology `_repo_root_for_feature`'s old `.parent.parent` value may differ from
`primary_root` — the WP01 coord-parity oracle (T003) must witness that the *downstream* identity/target is
unchanged, not just that the root resolves. If it does change, that is a second latent-bug-fix and needs the
same before/after idempotency proof as the write-target.

### S-3 (WP06 — the lanes adoption hinges on `status_surface` being *in scope at the callsite*, which it is not, and B-1 applies here too)

WP06 T027 says: "source the coord feature dir from the context's `status_surface`." But `implement.py:984`
(`_lanes_feature_dir = feature_dir`) sits in a function that resolves `feature_dir`/`repo_root`/`mission_slug`
by hand (verified `:970-1010`). There is **no `status_surface` fragment in scope** there. The same B-1
mechanism gap applies: WP06 either threads a context (it can — `implement.py` already calls
`resolve_action_context` at `:554`, so a context may be available in the broader command) or needs the narrow
projection. The prompt's "prefer deriving from the existing `status_surface` + the `resolve_lanes_dir` seam"
(D-6) is sound *intent*, but the implementer needs to be told **where `status_surface` comes from** at that
specific callsite.

**Remediation:** WP06 prompt should point at the existing `resolve_action_context(...)` call already in
`implement.py` (`:554`) and instruct the implementer to reuse that resolved context's `status_surface` rather
than the hand-resolved `_lanes_feature_dir`. If that context is not in scope at `:984`, this WP inherits the
B-1 projection dependency and must be sequenced after B-1's mechanism lands. Confirm before implement.

### S-4 (WP07 — census under-counts `MissionStatus.load` callsites: "the two callers" is actually three)

WP07 prompt (T032) and the reduction census (§5) say *"the only two real `MissionStatus.load()` call sites are
`status.py:163` and `:199`."* There is a **third** at `status.py:343` (`type(ms).load(...)`). It also passes
only `repo_root`+`mission_slug` (verified), so **the retirement is still safe** — but the "two callers" claim
is factually wrong and an implementer doing the C-006 "re-grep first, STOP if a reader appeared" check will
hit a third callsite the prompt told them not to expect, and may pause or mis-handle it.

**Remediation:** Correct WP07 T032 (and reduction-census §5) to "the three `MissionStatus.load()` call sites
(`status.py:163`, `:199`, `:343`) — none pass `surface=`." Cheap, prevents a false alarm.

---

## NIT

### N-1 (WP08 dependency on WP07 missing — minor sequencing)

WP08 (keystone + ratchet) depends on WP02-WP06 but **not WP07**. The FR-005 boundary ratchet (T037) flags
"write-side re-derivation in the adopted modules." FR-006 retirement (WP07) deletes dead scaffolding in
`mission_runtime`/`aggregate.py` that the ratchet does not scan, so functionally the missing edge is harmless.
But if the ratchet's allow-list or the keystone's "zero coord paths" assertion ever touches the retired
`surface=`/`prompt_source` paths, ordering matters. Low risk; note for completeness. **The mission's own
question 5 (should WP07 RETIRE depend on WP05?) — answer: NO.** Retirement is genuinely independent (0-reader
deletion); it does not become "superseded" by the write-half adoption in any code-coupling sense — the
`surface=` param is already dead today, not "dead once WP05 lands." The plan's parallel placement of WP07 is
correct. WP08-depends-on-WP07 is the only arguably-missing edge, and it is a nit.

### N-2 (WP04 — `resolve_placement_only` is the right primitive; confirm the projection returns enough)

WP04 T018 routes placement to `resolve_placement_only` / `CommitTarget`. Verified that primitive exists and is
C-001-safe (`:781`, narrow entry over the same builder). But it returns a `CommitTarget` (ref+kind), whereas
the join being replaced is `worktree_path / KITTY_SPECS_DIR / branch_name` — a **filesystem path under a
worktree**, not a branch ref. The `CommitTarget` does not obviously carry the worktree-relative dir. WP04 may
need `ArtifactPlacementFragment` (which the prompt also names) rather than the bare `CommitTarget`. Confirm the
projection actually yields the placement *path* the join needs, or WP04 will discover mid-implementation that
the primitive is insufficient and improvise. Low risk (it is named as an option), but worth pinning in the
prompt.

### N-3 (scope-creep guard into #1716 is CRISP — credit where due)

Question 2 (C-001 / #1716 creep): the S2 deferral boundary **is** crisp. WP05 T024 + the prompt's reviewer
guidance #4 explicitly name `_read_contract_from_transaction_target` (`:439-475`) as the deferred ~2094-LOC
authority and forbid pulling it in; the inventory §2 and randy §3 both pin S2 as "computes the same value the
factory already does — reduction-not-symmetry, cleanly deferrable." No WP smuggles in a new resolver/factory
field *as written* (the only new-authority risk is the B-1 projection, which is a different, legitimate
concern). WP06's "thin lanes projection … only if needed" escape hatch (T028) is appropriately fenced with
"prefer `status_surface` + the existing seam (C-001)" and a reviewer check. **This dimension is clean.**

---

## Verdict

The mission's *intent* is architecturally sound and the C-001/C-007/#1716-deferral discipline is genuinely
crisp (N-3). The fragment fields exist and resolve correctly (verified). The file-level ownership partition is
overlap-free. **But the central mechanism — how a resolved fragment reaches the deep, context-less write
helpers — is undecided, and the plan's "an import, not a shared edit" framing is contradicted by the code
(B-1).** That gap cascades into an ownership hole in `mission_runtime/` (B-2), under-warns the R5 behavior
change (S-2), and leaves WP06 without an in-scope `status_surface` (S-3). The stale C-SURFACE/D-2 contradiction
(S-1) and the miscounted `load` callsites (S-4) are smaller but real.

These are resolvable in the plan without re-slicing the mission: add the projection-entry decision (D-12),
give it a home WP, reconcile C-SURFACE with C-TARGET, and correct the two factual drifts. Then the WPs are
implementable as partitioned.

NEEDS-REMEDIATION
