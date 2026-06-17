# SSOT Intent Verdict — `resolve_action_context` / `ExecutionContext` central API

**Author:** architect-alphonso (profile-loaded; DIR-001 one-owning-module, DIR-003
decision-documented, DIR-031 bounded-context translation, DIR-032 conceptual alignment)
**Date:** 2026-06-16
**Mission:** `read-path-error-fidelity-adoption-01KV8NPC`
**HEAD:** `87697e5e4` (`v3.2.0-108-g87697e5e4`)
**Keystone doubt resolved:** *"Do we even intend to USE the Context-passthrough + central API as
the read-path SSOT, or is it vestigial?"*

---

## VERDICT: **KEEP-AND-ADOPT** (with two scoped caveats)

The central API `resolve_action_context → ExecutionContext / ActionContextError`
(`src/mission_runtime/resolution.py:689`, `context.py:184/85`) is the **explicitly designed,
ADR-ratified, operator-decided single door** for read-path/mission-context resolution. It is
**load-bearing and coherent**, not aspirational or half-built. The mission's C-001 ("adopt, do not
build") is correct: the failures are at the **adoption boundary** (commands that bypass it) and the
**error boundary** (commands that flatten its typed error) — never in the API's core resolution
logic. **The operator's worry is NOT founded** — the doubt mistakes *incomplete adoption* for
*non-intent*; the design intent to make this the SSOT is unambiguous and triple-ratified.

The two caveats (both already absorbed by the plan) refine, they do not weaken, the verdict:
- **Caveat A (immutability gap):** the SSOT spine is intended to be an *immutable* context but is
  shipped as a mutable `@dataclass` — a genuine in-authority residual (FR-009/IC-01). Adoption must
  finish by freezing it, not by replacing it.
- **Caveat B (spec wording correction):** the spec's FR-009 "`branch_name == branch_ref.target_branch`"
  is a semantic conflation; the real invariant is `context.target_branch == branch_ref.target_branch`.
  The plan's D-2 already supersedes the spec wording correctly.

---

## 1. Design intent — what the API was DESIGNED to be (triple-ratified)

Three Accepted ADRs and one operator decision establish that this API is the *intended* read-path
authority. The intent is not implied — it is the literal decision text.

**(i) ADR `2026-03-09-1-prompts-do-not-discover-context-commands-do.md` (the "Commands do" ADR).**
Core decision (`:71`): **"Prompts do not discover context. Commands do."** Chosen Option 3 (`:67`):
*"Introduce a canonical action-context resolver command and make prompts consume it."* Decision
drivers `:39-44` name *"Single source of truth for feature, WP, dependency, and branch context"* and
*"Testable action resolution without depending on LLM prompt interpretation."* Consequence `:78`:
*"`next` … MUST share the same context-resolution backend as legacy slash commands."* This ADR
**designs a single shared resolver door**; it explicitly rejects per-prompt rediscovery (Rejected
Approaches `:147-149`). The very failures the mission fixes are this ADR's named Observed-failures
(`:26-28`: `FEATURE_CONTEXT_UNRESOLVED`, auto-select-then-fail, review/done conflation).

**(ii) ADR `2026-06-03-2-executioncontext-owner-and-committarget.md` — Decision 1 (`:32-46`):**
*"`resolve_action_context` … is the **single canonical resolver** for `ExecutionContext`."* Rules
(`:39-46`): *"Execution context is resolved **once per operation**… The resolved context is **passed
down to all callees as a value object**. **No callee may independently re-derive** workspace path,
branch, or feature directory from CWD after context has been resolved. New surfaces **must call
`resolve_action_context` first**."* The migration is declared a **Strangler Fig** (`:48-60`): *"the
existing OHS entry point is structurally correct; **it needs consumers, not replacement**"* (`:59-60`).
This is the decisive sentence for the operator's doubt — the design says the API is correct and
*under-consumed*, exactly the mission's thesis.

**(iii) ADR `2026-06-07-1-execution-state-canonical-surface.md` — §3 "Lean public API expressed over
context objects" (`:71-97`):** the package exposes exactly four symbols
(`ExecutionContext`, `ExecutionMode`, `resolve_action_context`, `ActionContextError`). *"The API is
expressed over **this context object**, never over path fragments. Consumers receive a resolved
context; **they do not reconstruct `main_repo_root / "kitty-specs" / mission_slug` themselves**
(FR-009)"* (`:79-83`). `resolve_action_context` is *"the **single resolution entry point**. CWD-invariant,
topology-aware … raises `ActionContextError` … with **no silent fallback**"* (`:86-89`).
`ActionContextError` is *"the **only** error type consumers catch"* (`:90`). The Context-passthrough
is the literal contract.

**Operator decision of record:** ADR 2026-06-07-1 §Context (`:26-31`) cites *"the operator decision
(Stijn, 2026-06-03) to create a net-new top-level `mission_runtime/` umbrella package."* The SSOT was
not an engineer's aspiration — the operator personally decided to give it a screaming-architecture
home. **An aspirational/vestigial surface does not get a net-new top-level package by operator decree.**

> **Was the Context meant to be threaded/passed-through, and the central API the single door?**
> **Yes — verbatim.** "passed down to all callees as a value object" (ADR-06-03-2 :41); "no callee may
> independently re-derive" (:42); "single resolution entry point … the only error type consumers
> catch" (ADR-06-07-1 :86/:90). Pass-through is the *design*, not an optional optimization.

---

## 2. Code-as-built vs intent — does the API realize it?

**It realizes the intent; the divergence is incomplete consumer adoption + one immutability gap — not
a broken or leaky core.**

**Coherent and load-bearing (the API works):**
- `resolve_action_context` (`resolution.py:689-822`) is a real fused resolver: it resolves mission
  slug + `feature_dir` (`:717`), resolves `target_branch` **exactly once** (`:721`, FR-012 single-
  derivation), assembles the doc-09 fragments (`:723-737`), and returns a fully-populated
  `ExecutionContext`. Mission-lifecycle actions return early with the resolved context (`:754-767`);
  WP-bearing actions thread lane/workspace/dependency state onto it (`:769-822`). This is the
  designed fuse-planning-with-execution behavior, present and exercised.
- It is **the door the good citizens already use**: `agent context resolve`
  (`agent/context.py:135/158`) routes it AND preserves `error_code=exc.code` to JSON — the reference
  pattern. Four of the six #2007 commands already route through it (spec Purpose; call-site-inventory
  §3). A vestigial API would have *zero* correct consumers; this one has the majority.
- The typed error is intact **at the resolver boundary**: `ActionContextError(code, message)` is raised
  with a precise code at every failure site (`:668` boundary-translated `STATUS_READ_PATH_NOT_FOUND`,
  `:705` `INVALID_ACTION`, `:771/:779` `WORK_PACKAGE_UNRESOLVED`, `:794` `CANONICAL_STATUS_UNREADABLE`).
  Debbie's live trace confirms it: on the #15 P0 topology the resolver produced
  `COORDINATION_BRANCH_DELETED` with the correct repair remediation (live-repro.md :49-55). **The
  fidelity exists; consumers throw it away.**
- The fragment model (`context.py:84-180`) is a genuine deep-module: `IdentityFragment` single-derives
  `mid8` with a `__post_init__` guard (`:98-105`); `BranchRefFragment` carries the one `target_branch`
  + `destination_ref` `CommitTarget`; fragments are `frozen=True`. This is real domain modeling, not a
  thin wrapper.

**The divergences from intent (and they are exactly the mission's scope):**
1. **Consumer bypass / error-flatten** — the design's "no callee may re-derive / the only error type
   consumers catch" is violated at exactly **three** `next`-family catch-sites that collapse
   `ActionContextError.code` into `MISSION_NOT_FOUND` (`runtime_bridge.py:3128-3130`, `:3265-3274`,
   `next_cmd.py:355-361`; call-site-inventory §2). This is *under-adoption of a correct API*, the
   Strangler residue ADR-06-03-2 :48-60 predicted.
2. **Immutability gap (Caveat A)** — ADR-06-07-1 :79 calls `ExecutionContext` *"the **immutable**,
   complete resolved context"*; the **as-built class is a mutable `@dataclass`** (`context.py:184`)
   whose WP fields are assigned post-construction (`resolution.py:800-808`) while every fragment is
   `frozen=True`. This is a **real** in-authority defect: a consumer can mutate `target_branch`
   post-build and diverge it from the frozen `branch_ref.target_branch`. **This is a "finish the
   adoption" item, not evidence the API is vestigial** — the design *intended* immutability; the build
   under-delivered it. FR-009/IC-01 finishes it.

**Net:** the central API is **coherent and load-bearing** (not a leaky abstraction). The flat
substrate (`context.py:19-23,194-220`) is a *deliberate Strangler compatibility shim* (NFR-001), not
vestigial cruft — it preserves the historical serialized shape while fragments are attached. The
"two resolvers" smell people fear is **not** in this API: the only true second authority is the
`decision.py` escape-check + the `resolve_canonical_root` root-walk, both of which the mission deletes/
aligns *onto* this SSOT, not away from it.

---

## 3. Architectural alignment of our plan — does any IC fight the design?

**No IC fights the design; every IC drives a consumer *onto* the SSOT or hardens the SSOT itself.**
Mapping each IC to the design intent it discharges:

| IC | Action | Aligns to design intent | Verdict |
|----|--------|--------------------------|---------|
| IC-01 | Freeze `ExecutionContext`, assert `target_branch == branch_ref.target_branch` at build | ADR-06-07-1 :79 "immutable … resolved context" — finishes the unmet immutability promise | **ALIGNED** (closes Caveat A) |
| IC-02 | Preserve `ActionContextError.code`+paths across `next` catch-sites | ADR-06-07-1 :90 "the only error type consumers catch"; copies the `agent context resolve` reference | **ALIGNED** (the cheapest cut) |
| IC-03 | setup-plan exact-one; finalize read on primary root; `is_committed` target-branch leg; commit hash | ADR-06-03-2 :42 "no callee may re-derive"; removes per-command second authority | **ALIGNED** |
| IC-04 | Delete `decision` escape-walk for resolved paths; root from canonical authority | ADR-06-03-2 :43-46 "new surfaces must call resolve first" — removes the only real second authority | **ALIGNED** (single-door enforcement) |
| IC-05 | `implement` consumes the claim's resolved context; carry #1993 lanes-dir seam | ADR-06-03-2 :40-41 "resolved once per operation … passed down as a value object" | **ALIGNED** |
| IC-06 | `resolve_canonical_root` stops at submodule, agrees with `locate_project_root` | NFR-001 behavioral equivalence; root authority must be single | **ALIGNED** (root-authority unification) |
| IC-07 | Charter status side-effect-free + JSON-safe | #2007 §2 fix direction; orthogonal but on the read-path no-op slice | **ALIGNED** (scoped) |

**The one wording mis-alignment to correct (Caveat B — already corrected by the plan):** spec FR-009
says *"`branch_name` MUST equal `branch_ref.target_branch`"* (spec.md :88). This **conflates two
semantically distinct fields**: `branch_name` (`context.py:212`, set at `resolution.py:804` from
`wp_workspace.branch_name`) is the **WP LANE branch** (`kitty/mission-…-lane-a`) — it is *designed*
to differ from the mission target branch. Demanding their equality would be wrong. The real invariant
is `context.target_branch == branch_ref.target_branch` (both already assigned from the single
`target_branch` at `:721`/`:744`/via-fragment-`:723`, so equal at build). **The plan's D-2 already
supersedes the spec wording** ("The spec's `branch_name == branch_ref.target_branch` wording is
superseded — `branch_name` is the WP lane branch and is expected to differ.", plan.md :48). **Action:
none beyond confirming the spec text is annotated as superseded by D-2** — the correction is sound and
the chosen rule (reject-on-mismatch, not normalize) is the architecturally correct one (normalizing
would hide a builder bug).

**Two correct deferrals confirmed against the design (no IC fights them):**
- **#1716 DEFER (D-1):** ~2094 LOC write-side coord topology. ADR-06-07-1 §4 (`:99-107`) explicitly
  scopes the surface to **Stage-C** (read-side façade) and puts the Stage-B operation service / commit
  seam **out of scope (C-008)**. Pulling #1716 would re-open Stage-B and violate C-001. DEFER is
  design-consistent.
- **#1993 CARRY-minimal (D-1):** the lanes-dir seam pairs with #1832 per #2007's binding "must not
  land alone" rule. Read-side, ~20 LOC. Consistent.

---

## 4. Robert's normative input (#2007) — corroborate or redirect?

**Robert's #2007 alignment rules emphatically CORROBORATE the adopt-the-central-API thesis. They do
not redirect.** Direct quotes from the issue body:

- **Expected outcome (§ "Architectural Diagnosis"):** *"The main expected architectural outcome is
  **adoption of the existing typed context/read-path authority** (`resolve_action_context` /
  `ExecutionContext`, `resolve_mission_read_path`, and the relevant status/lanes projections) by
  `next`, `agent context resolve`, `setup-plan`, `finalize-tasks`, `decision open`, and `agent action
  implement/review`. This must preserve #2004's architecture: operation-scoped contexts, distinct
  artifact surfaces (meta/primary, status/coord, lanes/coord), and **no new shadow paths**."*
- **Architectural Plan Alignment rule 1:** *"**Do not build a new monolithic resolver.** Finish/adopt
  the existing typed context/read-path surfaces from #1619/#1666/#1878, preserving the three artifact
  families."* — verbatim C-001.
- **Rule 2:** *"**C3 is the center of mass.** Start with **typed-error preservation** across `next`,
  `agent context resolve`, `setup-plan`, `finalize-tasks`, `decision open`, and `agent action
  implement/review`."* — verbatim IC-02 priority.
- **Rule 3:** *"**#1993 sequencing is binding.** A lanes-dir extraction without adoption creates a new
  shadow path. **Pair it with #1832** or include minimal callsite adoption."* — verbatim D-1 CARRY-minimal.
- **#1619/#1666 disposition:** *"#2007 C3 should **consume these, not fork them**."* — verbatim
  KEEP-AND-ADOPT.
- **#1827:** *"Not directly witnessed in #2007; **retest** as #2004 says."* — verbatim D-3 re-test-first
  (Debbie's live-repro then found DOES-NOT-REPRODUCE → test-only).
- **#1716/#1832:** *"#2010 is the witnessed-operator evidence and concrete entry slice; **#1832 remains
  the safest first repro/fix point**."* — supports IC-05 as the safe lead, and supports DEFER-#1716
  (write-side stays on #1878).
- **#1971 vs #2011:** *"#2011 pins a different resolver (`resolve_canonical_root`) so #1971 alone is
  not sufficient."* — verbatim IC-06 / FR-007 framing.

Robert does flag **non-overlap tracks that must stay separate** (#2008 command-surface drift, #2009
charter, #1890 repair UX, #1888 ownership, #1891 JSON contract) — and the plan's "Out of Scope" +
cross-ref section honors every one. **There is no redirect toward #1832/#1716/#1878 as a *substitute*
for adopting the central API — those are named as the *entry slice and the deferred write-side*, both
exactly as the plan sequences them.**

---

## 5. Is the operator's worry founded?

**No — but the worry is *diagnostic*, not idle.** What likely triggered it: the API ships with a
**Strangler compatibility flat substrate** (`context.py:19-23`) AND a **mutable** dataclass that does
not yet honor its ADR-stated immutability — so a reader who opens `context.py` cold sees a flat field
bag with attached fragments and a mutable shape, and could mistake an *unfinished Strangler* for an
*abandoned* one. The evidence says the opposite: three Accepted ADRs, an operator package decree, a
correct reference consumer (`agent context resolve`), and the majority of #2007 commands already
routing through it. **It is mid-Strangler, not vestigial.** The right response is the mission's:
finish the adoption (route the bypassers), finish the immutability (freeze the composite), and delete
the shadow authorities — *onto* this SSOT.

---

## Executive Summary (8 lines)

1. **VERDICT: KEEP-AND-ADOPT (with two scoped caveats).** `resolve_action_context`/`ExecutionContext`
   is the explicitly designed, triple-ADR-ratified, operator-decreed single read-path door — the
   mission's C-001 "adopt, do not build" is correct.
2. **The operator's worry is NOT founded:** the API is mid-Strangler (correct + under-consumed), not
   vestigial — ADR-06-03-2 :59 literally says *"it needs consumers, not replacement."*
3. **Design intent is verbatim pass-through:** context "resolved once per operation … passed down to
   all callees as a value object; no callee may re-derive" (ADR-06-03-2 :40-46); "the only error type
   consumers catch" (ADR-06-07-1 :90).
4. **Code-as-built realizes the intent:** the resolver is coherent and load-bearing, the typed error is
   intact at the boundary (Debbie traced `COORDINATION_BRANCH_DELETED` live) — three `next`-family
   catch-sites flatten it; that is under-adoption, not a broken core.
5. **Caveat A (real residual):** `ExecutionContext` is shipped mutable though ADR-06-07-1 :79 says
   "immutable" — IC-01 freezes it (reject-on-mismatch). This *finishes* adoption, not replaces it.
6. **Caveat B (spec wording):** FR-009's `branch_name == branch_ref.target_branch` conflates the WP
   lane branch with the target branch; the real invariant is `target_branch == branch_ref.target_branch`.
   **Plan D-2 already supersedes the spec wording correctly — confirm the spec text is annotated.**
7. **No IC fights the design:** all seven ICs drive a consumer onto the SSOT or harden the SSOT;
   #1716 DEFER (Stage-B out-of-scope per ADR-06-07-1 §4/C-008) and #1993 CARRY-minimal are
   design-consistent.
8. **Robert's #2007 rules corroborate, not redirect:** "main expected outcome is adoption of the
   existing typed context/read-path authority … do not build a new monolithic resolver … C3 [typed-error
   preservation] is the center of mass … consume #1619/#1666, not fork them." Proceed with the mission
   as planned.
